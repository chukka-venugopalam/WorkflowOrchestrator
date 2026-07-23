"""Context compressor — deterministic compression strategies for context layers.

Supports:
- Truncation: Keep first N chars
- Summarization hooks: Placeholder for future LLM-based summarization
- Priority-aware compression: Lower priority layers are compressed more
- Deterministic: Same input always produces same output

No AI reasoning is performed here — compression is always deterministic.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from workflow_orchestrator.context.context_models import (
    BudgetPriority,
    CompressorResult,
    ContextLayer,
    ContextLayerContent,
)

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Deterministic context compression for fitting within budget constraints.

    Compression strategies (applied deterministically):
    1. Truncation — Keep first N characters
    2. Section extraction — Keep headings and first line of each section
    3. Keyword extraction — Keep sentences containing key terms
    4. Summarization hook — Placeholder for future LLM-based summarization

    Usage:
        >>> compressor = ContextCompressor()
        >>> result = compressor.compress(
        ...     "Long text content...",
        ...     max_tokens=500,
        ... )
        >>> print(result.compression_ratio)
    """

    def compress(
        self,
        content: str,
        max_tokens: int,
        method: str = "auto",
    ) -> CompressorResult:
        """Compress content to fit within a token budget.

        Args:
            content: The content to compress.
            max_tokens: Maximum allowed tokens.
            method: Compression method (auto, truncate, sections, keywords).

        Returns:
            CompressorResult with compressed content and metadata.
        """
        original_tokens = len(content) // 4
        if original_tokens <= max_tokens:
            return CompressorResult(
                original_content=content,
                compressed_content=content,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=0.0,
                method="none",
            )

        if method == "truncate" or method == "auto":
            return self._truncate(content, max_tokens)
        elif method == "sections":
            return self._extract_sections(content, max_tokens)
        elif method == "keywords":
            return self._extract_keywords(content, max_tokens)
        else:
            return self._truncate(content, max_tokens)

    def compress_layer(
        self,
        layer: ContextLayerContent,
        max_tokens: int,
    ) -> tuple[ContextLayerContent, CompressorResult]:
        """Compress a context layer to fit within a token budget.

        Args:
            layer: The context layer to compress.
            max_tokens: Maximum allowed tokens.

        Returns:
            Tuple of (compressed layer, compressor result).
        """
        result = self.compress(layer.content, max_tokens)
        compressed_layer = ContextLayerContent(
            layer=layer.layer,
            content=result.compressed_content,
            priority=layer.priority,
            token_estimate=result.compressed_tokens,
            metadata={**layer.metadata, "compressed": True, "method": result.method},
        )
        return compressed_layer, result

    def _truncate(self, content: str, max_tokens: int) -> CompressorResult:
        """Truncate content to fit within max_tokens.

        Keeps the first portion of the content.

        Args:
            content: Content to truncate.
            max_tokens: Maximum allowed tokens.

        Returns:
            CompressorResult with truncated content.
        """
        max_chars = max_tokens * 4
        truncated = content[:max_chars]
        original_tokens = len(content) // 4
        compressed_tokens = len(truncated) // 4

        return CompressorResult(
            original_content=content,
            compressed_content=truncated,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=1.0 - (compressed_tokens / max(original_tokens, 1)),
            method="truncation",
        )

    def _extract_sections(self, content: str, max_tokens: int) -> CompressorResult:
        """Extract section headings and first line from each section.

        Args:
            content: Content with section-like structure.
            max_tokens: Maximum allowed tokens.

        Returns:
            CompressorResult with section-extracted content.
        """
        lines = content.split("\n")
        sections: list[str] = []
        current_section: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped and (stripped.isupper() or stripped.endswith(":") or stripped.startswith("#") or stripped.startswith("##")):
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
            elif current_section and len(current_section) < 3:
                current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section))

        extracted = "\n\n".join(sections)
        original_tokens = len(content) // 4

        if len(extracted) // 4 <= max_tokens:
            return CompressorResult(
                original_content=content,
                compressed_content=extracted,
                original_tokens=original_tokens,
                compressed_tokens=len(extracted) // 4,
                compression_ratio=1.0 - (len(extracted) // 4) / max(original_tokens, 1),
                method="sections",
            )

        return self._truncate(extracted, max_tokens)

    def _extract_keywords(self, content: str, max_tokens: int) -> CompressorResult:
        """Extract sentences containing key terms.

        Args:
            content: Content to extract from.
            max_tokens: Maximum allowed tokens.

        Returns:
            CompressorResult with keyword-extracted content.
        """
        sentences = re.split(r'(?<=[.!?])\s+', content)
        original_tokens = len(content) // 4

        # Score sentences by length (prefer medium-length informative ones)
        scored: list[tuple[float, str]] = []
        for s in sentences:
            words = s.split()
            score = len(words) / max(len(s), 1)
            if 5 <= len(words) <= 50:
                scored.append((score, s))

        scored.sort(key=lambda x: -x[0])

        # Select sentences until budget is reached
        selected: list[str] = []
        total_chars = 0
        max_chars = max_tokens * 4

        for _, sentence in scored:
            if total_chars + len(sentence) <= max_chars:
                selected.append(sentence)
                total_chars += len(sentence)
            else:
                break

        extracted = " ".join(selected)
        compressed_tokens = len(extracted) // 4

        return CompressorResult(
            original_content=content,
            compressed_content=extracted or content[:max_chars],
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens or max_tokens,
            compression_ratio=1.0 - compressed_tokens / max(original_tokens, 1),
            method="keywords",
        )
