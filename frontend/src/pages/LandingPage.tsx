import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BarChart3,
  Bot,
  CheckCircle2,
  CloudRain,
  FileText,
  FlaskConical,
  Globe2,
  Leaf,
  ShieldCheck,
  Sprout,
  TrendingUp,
} from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { useAuth } from '../context/AuthContext';

const CAPABILITIES = [
  {
    icon: <TrendingUp className="h-5 w-5" />,
    title: 'Leak-Free Crop Yield Forecasting',
    desc: 'Trained across 19,689 historical records with chronological validation and zero post-harvest production leakage.',
  },
  {
    icon: <Leaf className="h-5 w-5" />,
    title: 'Plant Disease Vision',
    desc: 'Upload leaf imagery for OpenCV quality checks, transfer-learning classification, and low-confidence safety alerts.',
  },
  {
    icon: <Bot className="h-5 w-5" />,
    title: 'Grounded Multilingual Gemini Advisor',
    desc: 'Ask farming questions in English, Tamil, Malayalam, Hindi, or Telugu with RAG citations and expert-check guardrails.',
  },
  {
    icon: <CloudRain className="h-5 w-5" />,
    title: 'Weather-Driven Irrigation ET₀',
    desc: 'Live 7-day forecast integration separating meteorological water estimates from physical soil moisture readings.',
  },
  {
    icon: <FlaskConical className="h-5 w-5" />,
    title: 'Smart Nutrient & Crop Suitability',
    desc: 'Data-backed NPK fertilizer recommendations and multi-class crop matching across 22 high-value crops.',
  },
  {
    icon: <FileText className="h-5 w-5" />,
    title: 'Executive Acreage Reports (PDF)',
    desc: 'Combine farm parameters, model drivers, and seasonal advisory summaries into shareable PDF reports.',
  },
];

export function LandingPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-parchment text-soil-charcoal">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-soil-border bg-parchment/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
          <Link to="/">
            <BrandLogo />
          </Link>

          <nav className="hidden items-center gap-7 text-sm font-medium text-soil-muted md:flex">
            <a href="#modules" className="hover:text-forest-deep">
              Capabilities
            </a>
            <a href="#integrity" className="hover:text-forest-deep">
              Scientific Integrity
            </a>
            <a href="#languages" className="hover:text-forest-deep">
              Languages
            </a>
          </nav>

          <div className="flex items-center gap-2.5">
            {user ? (
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-xl bg-forest-deep px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-forest-hover"
              >
                Open Workspace
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link
                  to="/auth"
                  className="rounded-xl border border-soil-border bg-white px-4 py-2 text-sm font-semibold text-forest-deep transition-colors hover:bg-parchment-muted"
                >
                  Sign In
                </Link>
                <Link
                  to="/auth?mode=register"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-forest-deep px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-forest-hover"
                >
                  Get Started
                  <ArrowRight className="h-4 w-4 text-gold-bright" />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-soil-border">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-14 sm:px-6 lg:grid-cols-12 lg:px-8 lg:py-20">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-border bg-emerald-mist px-3.5 py-1 text-xs font-semibold text-emerald-leaf">
              <Sprout className="h-3.5 w-3.5" />
              Precision Agritech Intelligence Platform
            </div>

            <h1 className="mt-5 font-display text-4xl font-extrabold tracking-tight text-forest-deep sm:text-5xl lg:text-6xl">
              Intelligence for{' '}
              <span className="relative inline-block text-emerald-leaf">
                Every Acre.
                <span className="absolute bottom-1 left-0 -z-10 h-3 w-full bg-gold-soft" />
              </span>
            </h1>

            <p className="mt-5 max-w-2xl text-base leading-relaxed text-soil-muted sm:text-lg">
              TerraQora AI unites leak-free crop yield ML, deep-learning leaf diagnostics,
              live meteorological irrigation modeling, and grounded multilingual Gemini
              advisory into one farm-ready decision cockpit.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3.5">
              <Link
                to={user ? '/dashboard' : '/auth'}
                className="inline-flex items-center gap-2 rounded-xl bg-forest-deep px-6 py-3.5 text-sm font-semibold text-white shadow-card transition-all hover:bg-forest-hover"
              >
                Launch Farmer Platform
                <ArrowRight className="h-4 w-4 text-gold-bright" />
              </Link>
              <a
                href="#modules"
                className="inline-flex items-center gap-2 rounded-xl border border-soil-border bg-white px-6 py-3.5 text-sm font-semibold text-forest-deep transition-colors hover:bg-parchment-muted"
              >
                Explore 8 AI Modules
              </a>
            </div>

            <div className="mt-8 grid grid-cols-3 gap-4 border-t border-soil-border pt-6 sm:max-w-lg">
              <div>
                <p className="font-mono text-xl font-bold text-forest-deep">19,689</p>
                <p className="text-xs text-soil-muted">Historical Crop Records</p>
              </div>
              <div>
                <p className="font-mono text-xl font-bold text-forest-deep">55 / 30</p>
                <p className="text-xs text-soil-muted">Crops & Indian States</p>
              </div>
              <div>
                <p className="font-mono text-xl font-bold text-gold-harvest">5 Langs</p>
                <p className="text-xs text-soil-muted">EN · TA · ML · HI · TE</p>
              </div>
            </div>
          </div>

          {/* Right Executive Field Preview Card */}
          <div className="lg:col-span-5">
            <div className="rounded-3xl border border-soil-border bg-white p-6 shadow-elevated">
              <div className="flex items-center justify-between border-b border-soil-border pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-soil-muted">
                    Acreage Intelligence Snapshot
                  </p>
                  <p className="mt-0.5 font-display text-lg font-bold text-forest-deep">
                    Coimbatore Kharif Block
                  </p>
                </div>
                <span className="rounded-full bg-emerald-mist px-3 py-1 text-xs font-semibold text-emerald-leaf">
                  Illustrative Preview
                </span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3.5">
                <div className="rounded-2xl border border-soil-border bg-parchment p-4">
                  <p className="text-xs text-soil-muted">Leak-Free Yield Forecast</p>
                  <p className="mt-1 font-mono text-2xl font-bold text-forest-deep">3.84 t/ha</p>
                  <p className="mt-1 text-[11px] font-medium text-emerald-leaf">
                    Rice · Kharif Season
                  </p>
                </div>
                <div className="rounded-2xl border border-soil-border bg-parchment p-4">
                  <p className="text-xs text-soil-muted">7-Day ET₀ Irrigation</p>
                  <p className="mt-1 font-mono text-2xl font-bold text-gold-harvest">18.4 mm</p>
                  <p className="mt-1 text-[11px] font-medium text-soil-muted">
                    Weather-estimated advice
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-emerald-border bg-emerald-mist/60 p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-forest-deep">
                  <ShieldCheck className="h-4 w-4 text-emerald-leaf" />
                  Scientific & Agronomic Guardrails Enabled
                </div>
                <ul className="mt-2.5 space-y-1.5 text-xs text-soil-muted">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-leaf" />
                    Zero target leakage (`Production` excluded from yield inputs)
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-leaf" />
                    Automatic uncertainty alerts below 65% vision confidence
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-leaf" />
                    Grounded RAG answers without invented chemical dosages
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Capabilities Grid */}
      <section id="modules" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-leaf">
            Integrated Agritech Stack
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold text-forest-deep">
            Eight purpose-built intelligence modules
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-soil-muted sm:text-base">
            Designed for real agricultural workflows—connecting multi-year yield analytics,
            field nutrient balance, leaf health screening, and multilingual advisory.
          </p>
        </div>

        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((item) => (
            <div
              key={item.title}
              className="rounded-2xl border border-soil-border bg-white p-6 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-elevated"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-mist text-forest-deep">
                {item.icon}
              </div>
              <h3 className="mt-4 font-display text-lg font-bold text-forest-deep">
                {item.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-soil-muted">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Integrity & Multilingual Strip */}
      <section id="integrity" className="border-y border-soil-border bg-forest-deep text-parchment">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-gold-bright">
              <BarChart3 className="h-3.5 w-3.5" />
              Built with Production ML Discipline
            </div>
            <h2 className="mt-4 font-display text-2xl font-bold text-white sm:text-3xl">
              Honest diagnostics, never synthetic hype.
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-parchment/80">
              Every model surfaces real confidence boundaries, unit clarity (tonnes/hectare vs.
              nuts/hectare for Coconut), and soil-lab consultation reminders when inputs require
              field verification.
            </p>
          </div>

          <div id="languages" className="rounded-2xl border border-white/15 bg-white/5 p-6">
            <div className="flex items-center gap-2 text-sm font-semibold text-gold-bright">
              <Globe2 className="h-4 w-4" />
              Multilingual Farmer Support
            </div>
            <p className="mt-2 text-xs text-parchment/75">
              Converse naturally with the TerraQora GenAI Farming Assistant in five regional and
              global languages:
            </p>
            <div className="mt-4 flex flex-wrap gap-2.5">
              {[
                'English',
                'தமிழ் (Tamil)',
                'മലയാളം (Malayalam)',
                'हिन्दी (Hindi)',
                'తెలుగు (Telugu)',
              ].map((lang) => (
                <span
                  key={lang}
                  className="rounded-xl border border-white/15 bg-white/10 px-3.5 py-1.5 text-xs font-medium text-white"
                >
                  {lang}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 text-xs text-soil-muted sm:flex-row sm:px-6 lg:px-8">
        <BrandLogo />
        <p>TerraQora AI — Intelligence for Every Acre. Precision Smart Agriculture Platform.</p>
      </footer>
    </div>
  );
}
