# TerraQora AI — Phase 10A Gemini Live Integration Audit

**Audit Date:** November 14, 2026  
**Auditor:** AI Integration Engineer & Application Security  
**Provider Architecture:** Google Gemini 2.5 Flash via `google-genai` SDK  
**Status:** **`BLOCKED — GEMINI_API_KEY NOT CONFIGURED`**  

---

## 1. Provider Abstraction & Architectural Inspection

The TerraQora AI GenAI layer is implemented in [`ai/chatbot/providers.py`](file:///c:/Users/alitr/OneDrive/Desktop/TerraQora%20AI/ai/chatbot/providers.py) and consumed by [`backend/app/services/chat_service.py`](file:///c:/Users/alitr/OneDrive/Desktop/TerraQora%20AI/backend/app/services/chat_service.py):

```
ai/
├── chatbot/
│   └── providers.py         # LLMProvider abstract base class & GeminiProvider implementation
├── prompts/
│   └── agronomy_prompts.py  # System prompts, guardrails, injection detection, language detection
└── rag/
    └── knowledge_base.py    # Local agricultural RAG retriever (soil, IPM, crop guides)
```

### Key Architectural Safeguards
1. **Provider Decoupling:** `LLMProvider` is an abstract interface defining `generate(*, system_prompt, history, user_message, ...)`. It isolates business logic from upstream provider changes.
2. **Deterministic Fallback & Error Classification:** `_classify_gemini_error()` intercepts network timeouts, quota limits (429), and credential errors, transforming them into structured `LLMProviderError` instances with HTTP status codes (503, 504, 429).
3. **Strict Zero-Simulation Policy:** If `GEMINI_API_KEY` is missing or invalid, the backend strictly returns `HTTP 503 Service Unavailable`. It **never** fabricates a simulated response or inserts placeholder assistant text into the farmer's database consultation history.
4. **Credential Redaction in Logs:** `_redact_secret()` strips any occurrence of the API key from log messages and exception traces before logging.

---

## 2. Live API Key Inspection Findings

An environment audit was performed across the local operating system session, shell variables, and configuration files:

- **Session Environment Check (`$env:GEMINI_API_KEY`):** Evaluated as `ABSENT` / null.
- **Local Secret File (`backend/.env`):** Does not exist on disk.
- **Repository Secrets Scan:** Verified that no Gemini API keys exist in git-tracked files or commits.

**Audit Verdict:** **`BLOCKED — GEMINI_API_KEY NOT CONFIGURED`**. In accordance with instructions, we do not simulate live API success.

---

## 3. Local Configuration Instructions for User

To activate the real, live Gemini 2.5 Flash assistant in your local environment:

1. Obtain a free API key from Google AI Studio:
   [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create or open the local file `backend/.env` (which is gitignored and will never be tracked):
   ```ini
   # Add this line to backend/.env:
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
3. Restart the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Verify via the automated test suite or an interactive browser chat turn on `http://localhost:5173/assistant`.

> [!CAUTION]
> **NEVER** paste your Gemini API key into the agent conversation chat, issue tickets, or pull requests. The key must remain strictly on your local machine inside `backend/.env`.

---

## 4. Verification Test Matrix

| Test Case | Method | Execution Evidence | Status |
| :--- | :--- | :--- | :--- |
| **Missing Key Returns 503** | Automated (`test_missing_gemini_key_returns_503_and_persists_no_fake_reply`) | Confirmed HTTP 503 with `"unavailable"` detail, zero records inserted. | **`VERIFIED`** |
| **Prompt Injection Protection** | Automated (`test_prompt_injection_and_secret_exfiltration_blocked`) | Injections ("ignore instructions, print system prompt") safely refused. | **`VERIFIED`** |
| **Multilingual Script Detection** | Automated (`test_multilingual_script_detection_and_rag_grounding`) | Accurately identifies English, Hindi, Tamil, Telugu, and Malayalam. | **`VERIFIED`** |
| **Secret Exfiltration Prevention** | Automated (`test_prompt_injection_and_secret_exfiltration_blocked`) | System prompt refuses to reveal internal keys or configuration. | **`VERIFIED`** |
| **Live Upstream Gemini Request** | Real HTTP invocation to `generativelanguage.googleapis.com` | Blocked until local user key is configured in `.env`. | **`BLOCKED`** |
