/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forest: {
          deep: '#123524',
          hover: '#1A4731',
          900: '#0C2418',
        },
        emerald: {
          leaf: '#2D6A4F',
          sprout: '#52B788',
          mist: '#EDF4EF',
          border: '#D0E0D5',
        },
        parchment: {
          DEFAULT: '#FAF9F5',
          muted: '#F3F2EC',
        },
        gold: {
          harvest: '#C9972C',
          soft: '#F7EFE0',
          bright: '#E0B44A',
        },
        soil: {
          charcoal: '#1B241E',
          muted: '#5A665E',
          border: '#E4E8E1',
        },
      },
      fontFamily: {
        display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(18, 53, 36, 0.05), 0 1px 2px -1px rgba(18, 53, 36, 0.04)',
        elevated: '0 10px 30px -10px rgba(18, 53, 36, 0.12)',
      },
    },
  },
  plugins: [],
};
