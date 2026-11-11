# TerraQora AI — Generative AI & RAG (`ai/`)

Planned structure for **Phase 6**:
- `chatbot/`: `LLMProvider` interface (`GeminiProvider` via `google-genai` + pluggable `OpenAIProvider`)
- `rag/`: Grounded agricultural knowledge base & retrieval pipeline
- `prompts/`: Multilingual prompt templates (`en`, `ta`, `ml`, `hi`, `te`) with anti-hallucination and expert-consultation guardrails
