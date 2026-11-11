import React, { useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, FlaskConical, Lock, Mail, Shield, User as UserIcon } from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { ErrorAlert } from '../components/StatusState';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { LANGUAGE_OPTIONS } from '../data/agriCatalog';
import type { SupportedLanguage } from '../types/api';

export function AuthPage() {
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get('mode') === 'register' ? 'register' : 'login';
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [language, setLanguage] = useState<SupportedLanguage>('en');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { login, register } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as { from?: string } | null)?.from || '/dashboard';

  const validate = (): string | null => {
    if (mode === 'register' && fullName.trim().length < 2) {
      return 'Please enter your full name (at least 2 characters).';
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return 'Please enter a valid email address.';
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters long.';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    const validationErr = validate();
    if (validationErr) {
      setErrorMsg(validationErr);
      return;
    }

    setSubmitting(true);
    try {
      if (mode === 'login') {
        const user = await login({ email: email.trim(), password });
        notify(`Signed in as ${user.full_name}`, 'success');
      } else {
        const user = await register({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          preferred_language: language,
        });
        notify(`Account created for ${user.full_name}`, 'success');
      }
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSandboxDemo = async (role: 'farmer' | 'admin') => {
    setErrorMsg(null);
    setSubmitting(true);
    try {
      const demoEmail =
        role === 'admin' ? 'admin@terraqora.demo' : 'ananya.farmer@terraqora.demo';
      const user = await login(
        { email: demoEmail, password: 'DemoPreviewUser#2026' },
        role
      );
      notify(`Signed into ${role} preview sandbox (${user.full_name})`, 'info');
      navigate(role === 'admin' ? '/admin' : '/dashboard', { replace: true });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Preview sign-in failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-parchment lg:flex-row">
      {/* Left Brand Panel */}
      <div className="flex flex-col justify-between bg-forest-deep p-8 text-parchment lg:w-5/12 lg:p-12">
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-parchment/80 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to TerraQora Home
          </Link>
          <div className="mt-8">
            <BrandLogo darkSurface />
          </div>
          <h1 className="mt-8 font-display text-3xl font-bold leading-tight text-white">
            Precision intelligence for every growing season.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-parchment/80">
            Access crop yield forecasting, leaf disease detection, soil nutrient guidance,
            live weather irrigation advisory, and multilingual AI support.
          </p>
        </div>

        <div className="mt-10 rounded-2xl border border-white/15 bg-white/5 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gold-bright">
            Phase 3 Frontend Preview Notice
          </p>
          <p className="mt-1.5 text-xs leading-relaxed text-parchment/80">
            When the FastAPI backend is not running locally, TerraQora automatically enables
            Preview Sandbox mode with clearly labeled synthetic demonstration data.
          </p>
        </div>
      </div>

      {/* Right Auth Form Panel */}
      <div className="flex flex-1 items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md rounded-3xl border border-soil-border bg-white p-7 shadow-elevated sm:p-8">
          <div className="grid grid-cols-2 rounded-xl bg-parchment-muted p-1">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setErrorMsg(null);
              }}
              className={`rounded-lg py-2 text-sm font-semibold transition-colors ${
                mode === 'login'
                  ? 'bg-white text-forest-deep shadow-xs'
                  : 'text-soil-muted hover:text-soil-charcoal'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('register');
                setErrorMsg(null);
              }}
              className={`rounded-lg py-2 text-sm font-semibold transition-colors ${
                mode === 'register'
                  ? 'bg-white text-forest-deep shadow-xs'
                  : 'text-soil-muted hover:text-soil-charcoal'
              }`}
            >
              Create Account
            </button>
          </div>

          <h2 className="mt-6 font-display text-2xl font-bold text-forest-deep">
            {mode === 'login' ? 'Welcome back' : 'Register your farm workspace'}
          </h2>
          <p className="mt-1 text-sm text-soil-muted">
            {mode === 'login'
              ? 'Sign in with your TerraQora AI account credentials.'
              : 'Set up your profile and preferred consultation language.'}
          </p>

          {errorMsg && (
            <div className="mt-4">
              <ErrorAlert message={errorMsg} />
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
            {mode === 'register' && (
              <div>
                <label htmlFor="auth-name" className="block text-xs font-semibold text-soil-charcoal">
                  Full Name
                </label>
                <div className="relative mt-1.5">
                  <UserIcon className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-soil-muted" />
                  <input
                    id="auth-name"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g., Ananya Sundaram"
                    className="w-full rounded-xl border border-soil-border bg-parchment/50 py-2.5 pl-9 pr-3 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
                  />
                </div>
              </div>
            )}

            <div>
              <label htmlFor="auth-email" className="block text-xs font-semibold text-soil-charcoal">
                Email Address
              </label>
              <div className="relative mt-1.5">
                <Mail className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-soil-muted" />
                <input
                  id="auth-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="farmer@example.com"
                  className="w-full rounded-xl border border-soil-border bg-parchment/50 py-2.5 pl-9 pr-3 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="auth-password" className="block text-xs font-semibold text-soil-charcoal">
                Password
              </label>
              <div className="relative mt-1.5">
                <Lock className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-soil-muted" />
                <input
                  id="auth-password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="w-full rounded-xl border border-soil-border bg-parchment/50 py-2.5 pl-9 pr-3 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
                />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label htmlFor="auth-lang" className="block text-xs font-semibold text-soil-charcoal">
                  Preferred Assistant Language
                </label>
                <select
                  id="auth-lang"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
                  className="mt-1.5 w-full rounded-xl border border-soil-border bg-parchment/50 px-3 py-2.5 text-sm focus:border-emerald-leaf focus:bg-white focus:outline-none"
                >
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <option key={opt.code} value={opt.code}>
                      {opt.label} ({opt.nativeLabel})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-forest-deep py-2.5 text-sm font-semibold text-white transition-colors hover:bg-forest-hover disabled:opacity-60"
            >
              {submitting
                ? 'Authenticating...'
                : mode === 'login'
                  ? 'Sign In to TerraQora AI'
                  : 'Create Farmer Account'}
            </button>
          </form>

          {/* Sandbox quick-entry buttons */}
          <div className="mt-6 border-t border-soil-border pt-5">
            <p className="flex items-center gap-1.5 text-xs font-semibold text-soil-muted">
              <FlaskConical className="h-3.5 w-3.5 text-gold-harvest" />
              Instant UI Preview Sandbox (Synthetic Demo)
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2.5">
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleSandboxDemo('farmer')}
                className="rounded-xl border border-emerald-border bg-emerald-mist/70 px-3 py-2 text-xs font-semibold text-forest-deep hover:bg-emerald-mist"
              >
                Demo Farmer View
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleSandboxDemo('admin')}
                className="inline-flex items-center justify-center gap-1 rounded-xl border border-soil-border bg-parchment px-3 py-2 text-xs font-semibold text-soil-charcoal hover:bg-parchment-muted"
              >
                <Shield className="h-3.5 w-3.5 text-gold-harvest" />
                Demo Admin View
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
