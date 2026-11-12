import React, { useEffect, useRef, useState } from 'react';
import {
  BookOpen,
  Bot,
  Check,
  Globe2,
  MapPin,
  MessageSquarePlus,
  Pencil,
  Send,
  ShieldAlert,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import { chatService, profileService } from '../api/services';
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
import type {
  ChatLanguageChoice,
  ChatMessage,
  ChatSession,
  Farm,
  SupportedLanguage,
} from '../types/api';

const MAX_PROMPT_CHARS = 2000;

const SUGGESTED_PROMPTS = [
  'How should I split Urea nitrogen top-dressing for Kharif Rice?',
  'What organic and preventive practices reduce Tomato Early Blight?',
  'When should I skip irrigation based on upcoming 3-day rainfall forecast?',
  'How do I correct acidic red loamy soil (pH 5.3) before sowing?',
];

function formatMessageTime(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function GenAIAssistantPage() {
  const { user, isDemoSession } = useAuth();
  const { notify } = useToast();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [language, setLanguage] = useState<ChatLanguageChoice>(
    user?.preferred_language || 'en'
  );
  const [includeFarmContext, setIncludeFarmContext] = useState(true);
  const [input, setInput] = useState('');
  const [failedPrompt, setFailedPrompt] = useState<string | null>(null);

  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const [loadingInit, setLoadingInit] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const threadEndRef = useRef<HTMLDivElement | null>(null);

  const resolvedSessionLanguage: SupportedLanguage =
    language === 'auto' ? user?.preferred_language || 'en' : language;

  const loadWorkspace = async () => {
    setLoadingInit(true);
    setError(null);
    try {
      const [sessionList, farmList] = await Promise.all([
        chatService.listSessions(),
        profileService.listFarms().catch(() => [] as Farm[]),
      ]);
      setFarms(farmList);

      let list = sessionList;
      if (list.length === 0) {
        const created = await chatService.createSession(
          resolvedSessionLanguage,
          'New Agronomy Consultation',
          farmList[0]?.id ?? null
        );
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
    loadWorkspace();
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSelectSession = async (session: ChatSession) => {
    setActiveSessionId(session.id);
    if (language !== 'auto') {
      setLanguage(session.language);
    }
    setError(null);
    setFailedPrompt(null);
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
    setFailedPrompt(null);
    const targetLang = resolvedSessionLanguage;
    try {
      const activeFarmId = activeSession?.farm_id ?? farms[0]?.id ?? null;
      const created = await chatService.createSession(
        targetLang,
        `Consultation (${targetLang.toUpperCase()})`,
        activeFarmId
      );
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setMessages([]);
      notify('Started new consultation session', 'info');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create session.');
    }
  };

  const handleStartRename = (sess: ChatSession) => {
    setEditingSessionId(sess.id);
    setEditingTitle(sess.title);
  };

  const handleSaveRename = async (sessionId: string) => {
    const trimmed = editingTitle.trim();
    if (!trimmed) {
      setError('Session title cannot be blank.');
      return;
    }
    setError(null);
    try {
      const updated = await chatService.updateSession(sessionId, { title: trimmed });
      setSessions((prev) => prev.map((s) => (s.id === sessionId ? updated : s)));
      setEditingSessionId(null);
      notify('Renamed consultation session', 'success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not rename session.');
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    setError(null);
    try {
      await chatService.deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      if (remaining.length === 0) {
        const created = await chatService.createSession(
          resolvedSessionLanguage,
          'New Agronomy Consultation',
          farms[0]?.id ?? null
        );
        setSessions([created]);
        setActiveSessionId(created.id);
        setMessages([]);
      } else {
        setSessions(remaining);
        if (activeSessionId === sessionId) {
          const nextActive = remaining[0];
          setActiveSessionId(nextActive.id);
          const msgs = await chatService.getMessages(nextActive.id);
          setMessages(msgs);
        }
      }
      notify('Deleted consultation session', 'info');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete session.');
    }
  };

  const handleLinkFarm = async (farmId: string) => {
    if (!activeSessionId) return;
    setError(null);
    try {
      const updated = await chatService.updateSession(activeSessionId, {
        farm_id: farmId || null,
      });
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? updated : s))
      );
      notify(
        farmId ? 'Linked farm plot context to session' : 'Unlinked farm plot from session',
        'info'
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update linked farm plot.');
    }
  };

  const handleClearChat = async () => {
    if (!activeSessionId) return;
    setError(null);
    setFailedPrompt(null);
    try {
      await chatService.clearSession(activeSessionId);
      setMessages([]);
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? { ...s, message_count: 0 } : s))
      );
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
    if (trimmed.length > MAX_PROMPT_CHARS) {
      setError(`Questions must be ${MAX_PROMPT_CHARS} characters or fewer.`);
      return;
    }
    if (!activeSessionId || sending) return;

    setError(null);
    setFailedPrompt(null);
    setSending(true);
    setInput('');
    try {
      const result = await chatService.sendMessage(
        activeSessionId,
        trimmed,
        language,
        includeFarmContext
      );
      setMessages((prev) => [...prev, result.userMsg, result.assistantMsg]);
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeSessionId) return s;
          return (
            result.session ?? {
              ...s,
              language: result.resolvedLanguage || s.language,
              updated_at: new Date().toISOString(),
            }
          );
        })
      );
      if (result.autoDetected && result.resolvedLanguage) {
        const matched = LANGUAGE_OPTIONS.find((l) => l.code === result.resolvedLanguage);
        if (matched) {
          notify(`Auto-detected ${matched.label} script`, 'info');
        }
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Assistant could not respond right now. Please retry.'
      );
      setFailedPrompt(trimmed);
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
  const linkedFarm = farms.find((f) => f.id === activeSession?.farm_id) || null;

  return (
    <AppShell
      title="GenAI Farming Assistant"
      subtitle="Grounded multilingual agronomy guidance powered by Gemini + TerraQora RAG across English, Tamil, Malayalam, Hindi, and Telugu."
    >
      {error && (
        <div className="mb-4">
          <ErrorAlert
            message={error}
            onRetry={
              loadingInit
                ? loadWorkspace
                : failedPrompt
                  ? () => submitPrompt(failedPrompt)
                  : undefined
            }
          />
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

            <div className="mt-2.5 space-y-2 overflow-y-auto max-h-[380px]">
              {sessions.map((sess) => {
                const isActive = sess.id === activeSessionId;
                const isEditing = editingSessionId === sess.id;
                return (
                  <div
                    key={sess.id}
                    className={`rounded-xl border p-3 transition-colors ${
                      isActive
                        ? 'border-emerald-border bg-emerald-mist/70'
                        : 'border-soil-border bg-parchment/50 hover:bg-parchment'
                    }`}
                  >
                    {isEditing ? (
                      <div className="flex items-center gap-1.5">
                        <input
                          type="text"
                          aria-label="Edit session title"
                          value={editingTitle}
                          maxLength={160}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(sess.id);
                            if (e.key === 'Escape') setEditingSessionId(null);
                          }}
                          className="min-w-0 flex-1 rounded-lg border border-emerald-border bg-white px-2 py-1 text-xs font-medium text-forest-deep focus:outline-none"
                        />
                        <button
                          type="button"
                          aria-label="Save session title"
                          onClick={() => handleSaveRename(sess.id)}
                          className="rounded-lg bg-forest-deep p-1 text-white hover:bg-forest-hover"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          aria-label="Cancel rename"
                          onClick={() => setEditingSessionId(null)}
                          className="rounded-lg border border-soil-border bg-white p-1 text-soil-muted hover:text-soil-charcoal"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => handleSelectSession(sess)}
                          className="min-w-0 flex-1 text-left"
                        >
                          <span className="block truncate text-sm font-semibold text-forest-deep">
                            {sess.title}
                          </span>
                          <span className="mt-1 block text-[11px] text-soil-muted">
                            Updated {new Date(sess.updated_at).toLocaleDateString()}
                            {typeof sess.message_count === 'number'
                              ? ` · ${sess.message_count} msgs`
                              : ''}
                          </span>
                        </button>
                        <div className="flex shrink-0 items-center gap-1">
                          <span className="rounded-md border border-soil-border bg-white px-2 py-0.5 font-mono text-[10px] font-bold uppercase text-emerald-leaf">
                            {sess.language}
                          </span>
                          <button
                            type="button"
                            aria-label={`Rename session ${sess.title}`}
                            onClick={() => handleStartRename(sess)}
                            className="rounded-md p-1 text-soil-muted transition-colors hover:bg-white hover:text-forest-deep"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete session ${sess.title}`}
                            onClick={() => handleDeleteSession(sess.id)}
                            className="rounded-md p-1 text-soil-muted transition-colors hover:bg-red-50 hover:text-red-700"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Grounded Context & Safety Card */}
            <div className="mt-auto space-y-3 pt-4">
              {farms.length > 0 && (
                <div className="rounded-xl border border-soil-border bg-parchment/50 p-3 text-xs">
                  <label
                    htmlFor="chat-farm-select"
                    className="flex items-center gap-1.5 font-bold text-forest-deep"
                  >
                    <MapPin className="h-3.5 w-3.5 text-emerald-leaf" />
                    Linked Farm Plot Context
                  </label>
                  <select
                    id="chat-farm-select"
                    aria-label="Linked Farm Plot"
                    value={activeSession?.farm_id || ''}
                    onChange={(e) => handleLinkFarm(e.target.value)}
                    className="mt-1.5 w-full rounded-lg border border-soil-border bg-white px-2.5 py-1.5 text-xs text-forest-deep focus:border-emerald-leaf focus:outline-none"
                  >
                    <option value="">All Saved Plots (General)</option>
                    {farms.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} — {f.soil_type} ({f.primary_crop || f.district})
                      </option>
                    ))}
                  </select>
                  <label className="mt-2 flex items-center gap-2 text-[11px] text-soil-muted cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeFarmContext}
                      onChange={(e) => setIncludeFarmContext(e.target.checked)}
                      className="rounded border-soil-border text-emerald-leaf focus:ring-emerald-leaf"
                    />
                    Include saved farm &amp; ML predictions in prompt
                  </label>
                </div>
              )}

              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
                <div className="flex items-center gap-1.5 font-bold">
                  <ShieldAlert className="h-3.5 w-3.5 text-amber-700" />
                  Grounded Guardrail Active
                </div>
                <p className="mt-1 leading-relaxed text-[11px]">
                  Zero invented chemical dosages or text-only disease diagnoses. Always verify
                  treatment and Soil Health Card targets with your local Krishi Vigyan Kendra (KVK).
                </p>
              </div>
            </div>
          </aside>

          {/* Main Chat Panel */}
          <section className="flex min-h-[580px] flex-col rounded-2xl border border-soil-border bg-white shadow-card lg:col-span-8">
            {/* Chat Header Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-soil-border px-5 py-3.5">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-mist text-forest-deep">
                  <Bot className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <h2 className="truncate font-display text-sm font-bold text-forest-deep">
                    {activeSession?.title || 'Agronomy Consultation'}
                  </h2>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2">
                    <SourceModeBadge mode={activeSourceMode} />
                    {linkedFarm && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-parchment px-2 py-0.5 text-[11px] font-medium text-soil-charcoal border border-soil-border">
                        <MapPin className="h-3 w-3 text-emerald-leaf" />
                        {linkedFarm.name}
                      </span>
                    )}
                  </div>
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
                    onChange={(e) => setLanguage(e.target.value as ChatLanguageChoice)}
                    className="bg-transparent text-xs font-semibold text-forest-deep focus:outline-none"
                  >
                    <option value="auto">Auto-detect Script</option>
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
            <div className="flex-1 space-y-4 overflow-y-auto bg-parchment/40 p-5 max-h-[450px]">
              {loadingMsgs ? (
                <LoadingSkeleton rows={4} />
              ) : messages.length === 0 ? (
                <EmptyState
                  title="Start a grounded agricultural conversation"
                  description="Choose your preferred language (or Auto-detect), link a saved farm plot if helpful, and ask about soil nutrition, crop selection, disease prevention, or irrigation."
                />
              ) : (
                messages.map((msg) => {
                  const isUser = msg.role === 'user';
                  const timeLabel = formatMessageTime(msg.created_at);
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
                        <div className="mb-1 flex flex-wrap items-center justify-between gap-3 text-[11px]">
                          <span
                            className={`font-semibold ${
                              isUser ? 'text-gold-bright' : 'text-emerald-leaf'
                            }`}
                          >
                            {isUser ? user?.full_name || 'Farmer' : 'TerraQora AI Advisor'}
                          </span>
                          <div className="flex items-center gap-2">
                            {!isUser && msg.model_name && (
                              <span className="font-mono text-[10px] text-soil-muted">
                                {msg.model_name}
                                {typeof msg.latency_ms === 'number' && msg.latency_ms > 0
                                  ? ` · ${msg.latency_ms}ms`
                                  : ''}
                              </span>
                            )}
                            {timeLabel && (
                              <time
                                dateTime={msg.created_at}
                                className={`text-[10px] tabular-nums ${
                                  isUser ? 'text-white/75' : 'text-soil-muted'
                                }`}
                              >
                                {timeLabel}
                              </time>
                            )}
                          </div>
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
                  maxLength={MAX_PROMPT_CHARS}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      submitPrompt(input);
                    }
                  }}
                  placeholder={
                    language === 'auto'
                      ? 'Ask in English, தமிழ், മലയാളം, हिन्दी, or తెలుగు... (Auto-detect enabled)'
                      : `Ask in ${
                          LANGUAGE_OPTIONS.find((l) => l.code === language)?.label || 'English'
                        }... (Press Enter to send)`
                  }
                  className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1 text-sm text-soil-charcoal focus:outline-none"
                />
                <div className="flex flex-col items-end gap-1">
                  <button
                    type="submit"
                    disabled={sending}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-forest-deep px-4 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5 text-gold-bright" />
                    Send
                  </button>
                  <span className="px-1 text-[10px] tabular-nums text-soil-muted">
                    {input.length} / {MAX_PROMPT_CHARS}
                  </span>
                </div>
              </div>
            </form>
          </section>
        </div>
      )}
    </AppShell>
  );
}
