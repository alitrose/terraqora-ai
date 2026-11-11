import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Bot,
  CloudRain,
  FileText,
  FlaskConical,
  LayoutDashboard,
  Leaf,
  LogOut,
  Menu,
  ShieldCheck,
  Sprout,
  TrendingUp,
  UserCircle2,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BrandLogo } from './BrandLogo';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Farmer Dashboard', icon: <LayoutDashboard className="h-4 w-4" /> },
  { to: '/yield-prediction', label: 'Yield Prediction', icon: <TrendingUp className="h-4 w-4" /> },
  { to: '/disease-detection', label: 'Plant Disease CV', icon: <Leaf className="h-4 w-4" /> },
  { to: '/fertilizer', label: 'Smart Fertilizer', icon: <FlaskConical className="h-4 w-4" /> },
  { to: '/crop-recommendation', label: 'Crop Suitability', icon: <Sprout className="h-4 w-4" /> },
  { to: '/weather-irrigation', label: 'Weather & Irrigation', icon: <CloudRain className="h-4 w-4" /> },
  { to: '/assistant', label: 'GenAI Assistant', icon: <Bot className="h-4 w-4" /> },
  { to: '/analytics', label: 'Agri Analytics', icon: <BarChart3 className="h-4 w-4" /> },
  { to: '/reports', label: 'AI Reports', icon: <FileText className="h-4 w-4" /> },
  { to: '/profile', label: 'Profile & Farms', icon: <UserCircle2 className="h-4 w-4" /> },
  {
    to: '/admin',
    label: 'Admin Console',
    icon: <ShieldCheck className="h-4 w-4" />,
    adminOnly: true,
  },
];

export function AppShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const { user, isDemoSession, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const visibleNav = NAV_ITEMS.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  );

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  const sidebarContent = (
    <div className="flex h-full flex-col bg-forest-deep text-parchment">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <Link to="/" onClick={() => setMobileOpen(false)}>
          <BrandLogo darkSurface />
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation menu"
          className="rounded-lg p-1.5 text-parchment/70 hover:bg-white/10 lg:hidden"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav aria-label="Primary Sidebar" className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {visibleNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-leaf text-white shadow-sm'
                  : 'text-parchment/80 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="rounded-xl bg-white/5 p-3">
          <p className="truncate text-sm font-semibold text-white">
            {user?.full_name || 'Farmer Account'}
          </p>
          <p className="truncate text-xs text-parchment/70">{user?.email}</p>
          <div className="mt-2 flex items-center justify-between">
            <span className="rounded-md bg-gold-harvest/20 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-gold-bright">
              {user?.role || 'farmer'}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1 text-xs font-medium text-parchment/80 hover:text-white"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-parchment text-soil-charcoal">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 lg:block">{sidebarContent}</aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-xs"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative z-50 w-72 max-w-[85vw]">{sidebarContent}</aside>
        </div>
      )}

      {/* Main Column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-soil-border bg-white/90 px-4 py-3.5 backdrop-blur-md sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation menu"
                className="rounded-lg border border-soil-border p-2 text-forest-deep hover:bg-parchment lg:hidden"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <h1 className="font-display text-lg font-bold text-forest-deep sm:text-xl">
                  {title}
                </h1>
                {subtitle && <p className="text-xs text-soil-muted sm:text-sm">{subtitle}</p>}
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              {isDemoSession && (
                <span className="hidden items-center gap-1.5 rounded-full border border-amber-300 bg-gold-soft px-3 py-1 text-xs font-semibold text-amber-900 sm:inline-flex">
                  <FlaskConical className="h-3.5 w-3.5 text-gold-harvest" />
                  Phase 3 Preview Sandbox
                </span>
              )}
              <Link
                to="/assistant"
                className="inline-flex items-center gap-1.5 rounded-xl bg-forest-deep px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-forest-hover"
              >
                <Bot className="h-3.5 w-3.5 text-gold-bright" />
                Ask AI Advisor
              </Link>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
