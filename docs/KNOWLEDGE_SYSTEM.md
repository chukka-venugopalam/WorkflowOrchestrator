# Knowledge System

## Overview

The Knowledge System provides deterministic knowledge storage and retrieval. It uses simple keyword-based indexing — no vector databases, no embeddings, no AI.

## Knowledge Categories

| Category | Description |
|---|---|
| ARCHITECTURE_DECISION | Architecture decision records |
| RFC | Request for comments documents |
| CODING_STANDARD | Coding style and quality standards |
| TEMPLATE | Reusable templates |
| WORKFLOW_TEMPLATE | Workflow definition templates |
| PROMPT_TEMPLATE | Prompt formatting templates |
| PROVIDER_DOCUMENTATION | Provider API documentation |
| FIX_HISTORY | Historical bug fixes |
| COMMON_SOLUTION | Common problem solutions |
| ERROR_SIGNATURE | Error pattern signatures |
| GENERAL | Uncategorized knowledge |

## Key Components

| Component | Description |
|---|---|
| KnowledgeBase | Main interface for adding, searching, managing entries |
| KnowledgeStore | In-memory storage with optional file persistence |
| KnowledgeIndex | Keyword-based inverted index |
| KnowledgeSearch | Combined keyword/tag/category search with ranking |
| KnowledgeLoader | Load entries from YAML, JSON, Markdown files |

## Search Capabilities

- Keyword search with stop word filtering
- Tag-based search (AND/OR)
- Category filtering
- Combined queries
- Relevance scoring by term frequency

All search is deterministic — same query always returns same results.
