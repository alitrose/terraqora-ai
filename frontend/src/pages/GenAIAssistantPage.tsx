import React, { useEffect, useRef, useState } from 'react';
import {
  BookOpen,
  Bot,
  Globe2,
  MessageSquarePlus,
  Send,
  ShieldAlert,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { chatService } from '../api/services';
import { AppShell } from '../components/AppShell';
import {
  EmptyState,
  ErrorAlert,
  LoadingSkeleton,
  SourceModeBadge,
} from '../components/StatusState';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { LANGUAGE_OPTIONS } from '../data/agriCatalog';
import type { ChatMessage, ChatSession, SupportedLanguage } from '../types/api';

const SUGGESTED_PROMPTS = [
  'How should I split Urea nitrogen top-dressing for Kharif Rice?',
  'What organic and preventive practices reduce Tomato Early Blight?',
  'When should I skip irrigation based on upcoming 3-day rainfall forecast?',
  'How do I correct acidic red loamy soil (pH 5.3) before sowing?',
];

export function GenAIAssistantPage() {
  const { user, isDemoSession } = useAuth();
  const { notify } = useToast();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [language, setLanguage] = useState<SupportedLanguage>(
    user?.preferred_language || 'en'
  );
  const [input, setInput] = useState('');

  const [loadingInit, setLoadingInit] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const threadEndRef = useRef<HTMLDivElement | null>(null);

  const loadSessionsAndMessages = async () => {
    setLoadingInit(true);
    setError(null);
    try {
      let list = await chatService.listSessions();
      if (list.length === 0) {
        const created = await chatService.createSession(language, 'New Agronomy Consultation');
        list = [created];
      }
      setSessions(list);
      const first = list[0];
      setActiveSessionId(first.id);
      setLanguage(first.language);
      const msgs = await chatService.getMessages(first.id);
      setMessages(msgs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load chat workspace.');
    } finally {
      setLoadingInit(false);
    }
  };

  useEffect(() => {
    loadSessionsAndMessages();
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSelectSession = async (session: ChatSession) => {
    setActiveSessionId(session.id);
    setLanguage(session.language);
    setError(null);
    setLoadingMsgs(true);
    try {
      const msgs = await chatService.getMessages(session.id);
      setMessages(msgs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages.');
    } finally {
      setLoadingMsgs(false);
    }
  };

  const handleNewSession = async () => {
    setError(null);
    try {
      const created = await chatService.createSession(
        language,
        `Consultation (${language.toUpperCase()})`
      );
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setMessages([]);
      notify('Started new consultation session', 'info');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create session.');
    }
  };

  const handleClearChat = async () => {
    if (!activeSessionId) return;
    setError(null);
    try {
      await chatService.clearSession(activeSessionId);
      setMessages([]);
      notify('Cleared conversation history', 'info');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not clear messages.');
    }
  };

  const submitPrompt = async (promptText: string) => {
    const trimmed = promptText.trim();
    if (!trimmed) {
      setError('Please enter a farming question before sending.');
      return;
    }
    if (!activeSessionId || sending) return;

    setError(null);
    setSending(true);
    setInput('');
    try {
      const { userMsg, assistantMsg } = await chatService.sendMessage(
        activeSessionId,
        trimmed,
        language
      );
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, language, updated_at: new Date().toISOString() }
            : s
        )
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Assistant could not respond right now. Please retry.'
      );
      setInput(trimmed);
    } finally {
      setSending(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitPrompt(input);
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;
  const activeSourceMode = isDemoSession ? 'demo_preview' : 'live_api';

  return (
    <AppShell
      title="GenAI Farming Assistant"
      subtitle="Grounded multilingual agronomy guidance across English, Tamil, Malayalam, Hindi, and Telugu."
    >
      {error && (
        <div className="mb-4">
          <ErrorAlert message={error} onRetry={loadingInit ? loadSessionsAndMessages : undefined} />
        </div>
      )}

      {loadingInit ? (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <LoadingSkeleton rows={4} />
          </div>
          <div className="lg:col-span-8">
            <LoadingSkeleton rows={6} />
          </div>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Sessions Sidebar */}
          <aside className="flex flex-col rounded-2xl border border-soil-border bg-white p-4 shadow-card lg:col-span-4">
            <button
              type="button"
              onClick={handleNewSession}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-forest-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-forest-hover"
            >
              <MessageSquarePlus className="h-4 w-4 text-gold-bright" />
              New Consultation
            </button>

            <p className="mt-5 px-1 text-xs font-semibold uppercase tracking-wider text-soil-muted">
              Conversation History ({sessions.length})
            </p>

            <div className="mt-2.5 space-y-2 overflow-y-auto max-h-[420px]">
              {sessions.map((sess) => {
                const isActive = sess.id === activeSessionId;
                return (
                  <button
                    key={sess.id}
                    type="button"
                    onClick={() => handleSelectSession(sess)}
                    className={`w-full rounded-xl border p-3 text-left transition-colors ${
                      isActive
                        ? 'border-emerald-border bg-emerald-mist/70'
                        : 'border-soil-border bg-parchment/50 hover:bg-parchment'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold text-forest-deep">
                        {sess.title}
                      </span>
                      <span className="shrink-0 rounded-md bg-white px-2 py-0.5 font-mono text-[10px] font-bold uppercase text-emerald-leaf border border-soil-border">
                        {sess.language}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-soil-muted">
                      Updated {new Date(sess.updated_at).toLocaleDateString()}
                    </p>
                  </button>
                );
              })}
            </div>

            <div className="mt-auto pt-4">
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
                <div className="flex items-center gap-1.5 font-bold">
                  <ShieldAlert className="h-3.5 w-3.5 text-amber-700" />
                  Grounded Guardrail Active
                </div>
                <p className="mt-1 leading-relaxed text-[11px]">
                  Never apply unverified chemical dosages. Verify pesticide rates with your local
                  Krishi Vigyan Kendra (KVK) agronomist.
                </p>
              </div>
            </div>
          </aside>

          {/* Main Chat Panel */}
          <section className="flex min-h-[560px] flex-col rounded-2xl border border-soil-border bg-white shadow-card lg:col-span-8">
            {/* Chat Header Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-soil-border px-5 py-3.5">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-mist text-forest-deep">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-sm font-bold text-forest-deep">
                    {activeSession?.title || 'Agronomy Consultation'}
                  </h2>
                  <SourceModeBadge mode={activeSourceMode} />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <label htmlFor="chat-language" className="sr-only">
                  Response Language
                </label>
                <div className="inline-flex items-center gap-1.5 rounded-xl border border-soil-border bg-parchment/60 px-2.5 py-1.5">
                  <Globe2 className="h-3.5 w-3.5 text-emerald-leaf" />
                  <select
                    id="chat-language"
                    aria-label="Assistant Language"
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
                    className="bg-transparent text-xs font-semibold text-forest-deep focus:outline-none"
                  >
                    {LANGUAGE_OPTIONS.map((opt) => (
                      <option key={opt.code} value={opt.code}>
                        {opt.label} ({opt.nativeLabel})
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleClearChat}
                  disabled={messages.length === 0 || sending}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-soil-border px-3 py-1.5 text-xs font-semibold text-soil-muted transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 disabled:opacity-40"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Clear Chat
                </button>
              </div>
            </div>

            {/* Message Thread */}
            <div className="flex-1 space-y-4 overflow-y-auto bg-parchment/40 p-5 max-h-[430px]">
              {loadingMsgs ? (
                <LoadingSkeleton rows={4} />
              ) : messages.length === 0 ? (
                <EmptyState
                  title="Start a grounded agricultural conversation"
                  description="Select a suggested prompt below or ask about crop nutrition, leaf disease prevention, seasonal sowing, or weather irrigation timing."
                />
              ) : (
                messages.map((msg) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs ${
                          isUser
                            ? 'bg-forest-deep text-white'
                            : 'border border-soil-border bg-white text-soil-charcoal'
                        }`}
                      >
                        <div className="mb-1 flex items-center justify-between gap-4 text-[11px]">
                          <span
                            className={`font-semibold ${
                              isUser ? 'text-gold-bright' : 'text-emerald-leaf'
                            }`}
                          >
                            {isUser ? user?.full_name || 'Farmer' : 'TerraQora AI Advisor'}
                          </span>
                          {!isUser && msg.model_name && (
                            <span className="font-mono text-[10px] text-soil-muted">
                              {msg.model_name}
                            </span>
                          )}
                        </div>

                        <p className="whitespace-pre-line">{msg.content}</p>

                        {!isUser && msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-soil-border pt-2.5">
                            {msg.citations.map((cit, i) => (
                              <span
                                key={`${cit.source_title}-${i}`}
                                className="inline-flex items-center gap-1 rounded-lg border border-emerald-border bg-emerald-mist/60 px-2 py-0.5 text-[11px] font-medium text-forest-deep"
                              >
                                <BookOpen className="h-3 w-3 text-emerald-leaf" />
                                {cit.source_title} · {cit.section}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}

              {sending && (
                <div className="flex justify-start" role="status" aria-label="Advisor generating response">
                  <div className="inline-flex items-center gap-2 rounded-2xl border border-soil-border bg-white px-4 py-3 text-xs font-medium text-soil-muted shadow-xs">
                    <Sparkles className="h-4 w-4 animate-pulse text-gold-harvest" />
                    Consulting agronomy knowledge base...
                  </div>
                </div>
              )}

              <div ref={threadEndRef} />
            </div>

            {/* Suggested Prompts */}
            <div className="border-t border-soil-border bg-white px-5 pt-3">
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    disabled={sending}
                    onClick={() => submitPrompt(prompt)}
                    className="rounded-full border border-soil-border bg-parchment px-3 py-1 text-[11px] font-medium text-forest-deep transition-colors hover:border-emerald-border hover:bg-emerald-mist/60 disabled:opacity-50"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            {/* Input Form */}
            <form onSubmit={handleFormSubmit} className="p-4">
              <div className="flex items-end gap-2.5 rounded-2xl border border-soil-border bg-parchment/50 p-2 focus-within:border-emerald-leaf focus-within:bg-white">
                <label htmlFor="chat-input" className="sr-only">
                  Ask TerraQora AI Advisor
                </label>
                <textarea
                  id="chat-input"
                  rows={2}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      submitPrompt(input);
                    }
                  }}
                  placeholder={`Ask in ${
                    LANGUAGE_OPTIONS.find((l) => l.code === language)?.label || 'English'
                  }... (Press Enter to send)`}
                  className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1 text-sm text-soil-charcoal focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={sending}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-forest-deep px-4 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-50"
                >
                  <Send className="h-3.5 w-3.5 text-gold-bright" />
                  Send
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </AppShell>
  );
}
