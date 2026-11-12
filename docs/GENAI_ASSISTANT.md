# TerraQora AI — Phase 6: GenAI Farming Assistant (`ai/` + `backend/` + `frontend/`)

**Product:** TerraQora AI — *Intelligence for Every Acre.*  
**Scope:** Grounded, multilingual agricultural advisor backed by Google Gemini (`google-genai`), curated agronomy RAG chunks, prompt-injection protection, and optional read-only farm & TerraQora ML context.

---

## 1. Architecture Overview

```text
ai/
├── chatbot/
│   └── providers.py         # LLMProvider ABC + GeminiProvider (google-genai) + OpenAIProvider adapter
├── prompts/
│   └── agronomy_prompts.py  # Language metadata, Unicode script auto-detection, safety guardrails, injection filter
└── rag/
    └── knowledge_base.py    # Grounded agricultural knowledge base + deterministic bilingual retriever

backend/app/
├── api/v1/chat.py           # Authenticated REST endpoints + SlowAPI AI rate limit
├── schemas/chat.py          # Strict Pydantic v2 request/response contracts (extra="forbid")
└── services/chat_service.py # Session CRUD, ownership checks, RAG + Farm + ML grounding, turn persistence
```

### Key Design Decisions
- **Isolated Provider Abstraction (`LLMProvider`):** FastAPI endpoints talk to `chat_service.py`, which consumes the abstract `LLMProvider` interface. `GeminiProvider` uses the official `google-genai` SDK (`gemini-2.5-flash` configurable via `GEMINI_MODEL`) and `OpenAIProvider` provides a drop-in swappable backend via `LLM_PROVIDER`.
- **Environment-Only Secret Configuration:** `GEMINI_API_KEY` (and optional `OPENAI_API_KEY`) are read solely from environment configuration (`backend/app/core/config.py`, `.env` / `.env.example`), excluded from `Settings` `repr`, scrubbed from error strings, and never exposed to the React frontend. Placeholder values (such as `your-gemini-api-key-here`) are treated as unconfigured (`503 Service Unavailable`).
- **Real Live Failures — Zero Fake Fallbacks in Live Mode:** If `GEMINI_API_KEY` is missing, invalid, rate-limited, or times out in live mode, the backend returns explicit `503` / `429` / `504` HTTP errors and never saves or returns fabricated AI text. The browser `Demo Preview` mode remains strictly labeled as synthetic preview.

---

## 2. Multilingual Support & Auto-Detection

Supported languages matching PostgreSQL `ck_cs_lang` (`chat_sessions.language`):
- `en` — English
- `ta` — Tamil (`தமிழ்`, script `\u0B80-\u0BFF`)
- `ml` — Malayalam (`മലയാളം`, script `\u0D00-\u0D7F`)
- `hi` — Hindi (`हिन्दी`, Devanagari script `\u0900-\u097F`)
- `te` — Telugu (`తెలుగు`, script `\u0C00-\u0C7F`)

When `language="auto"` is sent on `POST /api/v1/chat/sessions/{session_id}/messages`, `detect_language(...)` inspects Indic Unicode script ranges in the user message to infer `ta`, `ml`, `hi`, or `te`, falling back cleanly to the session's active language (`en` by default) for Latin script queries. The resolved language is stored on the `ChatSession` and instructed natively in the system prompt (no mechanical word-for-word translation).

---

## 3. Agricultural Grounding, ML Integration & Guardrails

1. **Deterministic RAG (`ai/rag/knowledge_base.py`):** Matches English and native Indic agronomy keywords across curated Soil pH, NPK Split Stewardship, Kharif Paddy, Disease Non-Diagnosis Hygiene, Weather/ET₀ Irrigation, and Crop Rotation documents, emitting exact `ChatCitationOut` (`source_title`, `section`) metadata per assistant message.
2. **Read-Only Farm & ML Grounding:** When `include_farm_context=true`, `chat_service.py` attaches:
   - The user's owned `Farm` plot summary (crop, soil type, pH, district, state, irrigation type — no user email/passwords).
   - Latest persisted Phase 5/5B predictions owned by that user (`CropPrediction`, `CropRecommendation`, `FertilizerRecommendation`).
   - Live TerraQora ML registry availability (degrading cleanly if any `.joblib` artifact is absent).
   - **No Unsafe Auto-Actions:** Chat never mutates farm plots or executes unrequested ML/DB writes.
3. **Anti-Hallucination & Prompt-Injection Protection:**
   - System instructions enforce separating `[Knowledge Base]`, `[Saved Farm]`, `[TerraQora ML]`, and `[Verify Locally]`.
   - Prohibits fabricating chemical dosage rates (`kg/ha`, `g/plant`, `ml/L`), synthetic citations/URLs, soil-sensor telemetry, or definitive disease diagnoses from text alone.
   - `detect_prompt_injection(...)` intercepts attempts to extract `GEMINI_API_KEY`, `.env`, system instructions, or bypass guardrails before invoking external LLM APIs.

---

## 4. API Endpoints Summary

| Method | Endpoint | Auth & Limits | Notes |
| --- | --- | --- | --- |
| `GET` | `/api/v1/chat/sessions` | Bearer JWT | Lists user-owned sessions (`updated_at DESC`, with `message_count`) |
| `POST` | `/api/v1/chat/sessions` | Bearer JWT | Creates session (`{ language, title?, farm_id? }`, checks farm ownership) |
| `PATCH` | `/api/v1/chat/sessions/{id}` | Bearer JWT | Renames title, updates language, or links/unlinks owned `farm_id` |
| `DELETE` | `/api/v1/chat/sessions/{id}` | Bearer JWT | Deletes owned session and cascades messages |
| `GET` | `/api/v1/chat/sessions/{id}/messages` | Bearer JWT | Returns chronological message thread (`created_at ASC`) |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | Bearer JWT + `RATE_LIMIT_AI` (`20/minute`) | Sends turn (`1..2000` chars), runs RAG + Farm/ML context + Gemini |
| `DELETE` | `/api/v1/chat/sessions/{id}/messages` | Bearer JWT | Clears messages in owned session |

---

## 5. Verification Status & Local Live Testing

- **Automated Verification:** `tests/test_phase6_genai_assistant.py` validates configuration security, mocked `google-genai` SDK payload & error mapping (`401/403 -> 503`, `429 -> 429`, timeout -> `504`, empty -> `502`), missing key `503` fail-closed persistence, Tamil/Malayalam/Hindi/Telugu script detection, RAG citations, prompt-injection defense, Farm + ML grounding + missing `.joblib` resilience, ownership isolation (`403`), Pydantic `422` validation, and SlowAPI `429` rate limiting.
- **Live Gemini Connectivity Note:** Live calls to Google Gemini require setting a real `GEMINI_API_KEY` in a local `.env` file (excluded from Git). Without a configured key in `.env`, the backend intentionally returns `503 Service Unavailable`.
