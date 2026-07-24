"""Provider implementations — real provider adapters.

Contains concrete implementations of IProvider for Claude, ChatGPT,
and Gemini. All implementations support multiple transports and
declare capabilities through manifests.

No provider-specific logic leaks into upper layers.
"""

from __future__ import annotations

from workflow_orchestrator.providers.implementations.claude_provider import ClaudeProvider
from workflow_orchestrator.providers.implementations.chatgpt_provider import ChatGPTProvider
from workflow_orchestrator.providers.implementations.gemini_provider import GeminiProvider
from workflow_orchestrator.providers.implementations.openrouter_provider import OpenRouterProvider
from workflow_orchestrator.providers.implementations.ollama_provider import OllamaProvider
from workflow_orchestrator.providers.implementations.azure_openai_provider import AzureOpenAIProvider

__all__ = [
    "ClaudeProvider",
    "ChatGPTProvider",
    "GeminiProvider",
    "OpenRouterProvider",
    "OllamaProvider",
    "AzureOpenAIProvider",
]
