interface BrandLogoProps {
  compact?: boolean;
  darkSurface?: boolean;
}

export function BrandLogo({ compact = false, darkSurface = false }: BrandLogoProps) {
  return (
    <div className="inline-flex items-center gap-2.5 select-none">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 64 64"
        className="h-9 w-9 shrink-0"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="tqMarkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#123524" />
            <stop offset="100%" stopColor="#1D4D35" />
          </linearGradient>
        </defs>
        <rect
          x="2"
          y="2"
          width="60"
          height="60"
          rx="16"
          fill={darkSurface ? '#1C4B34' : 'url(#tqMarkGrad)'}
          stroke={darkSurface ? '#52B788' : '#2D6A4F'}
          strokeWidth="1.5"
        />
        <path
          d="M12 43.5C21 37.5 32 37.5 52 43.5"
          fill="none"
          stroke="#52B788"
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity="0.75"
        />
        <path
          d="M14 49.5C24 44.5 36 44.5 50 49.5"
          fill="none"
          stroke="#95D5B2"
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.45"
        />
        <path
          d="M32 45V23"
          stroke="#FAF9F5"
          strokeWidth="2.75"
          strokeLinecap="round"
        />
        <path
          d="M32 35C22 35 17 28 18 19C26.5 19 32 24.5 32 35Z"
          fill="#52B788"
        />
        <path
          d="M32 30C39 30 45 25 46 17C38.5 17 32 21.5 32 30Z"
          fill="#FAF9F5"
        />
        <circle cx="32" cy="15.5" r="4.2" fill="#D4A338" />
        <circle cx="32" cy="15.5" r="1.6" fill="#123524" />
      </svg>

      {!compact && (
        <div className="leading-tight">
          <span
            className={`font-display text-lg font-bold tracking-tight ${
              darkSurface ? 'text-parchment' : 'text-forest-deep'
            }`}
          >
            TerraQora <span className="text-gold-harvest">AI</span>
          </span>
          <p
            className={`text-[10px] font-medium uppercase tracking-wider ${
              darkSurface ? 'text-emerald-mist/75' : 'text-soil-muted'
            }`}
          >
            Intelligence for Every Acre
          </p>
        </div>
      )}
    </div>
  );
}
