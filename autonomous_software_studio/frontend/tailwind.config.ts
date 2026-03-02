import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: 'var(--background)',
          secondary: 'var(--background-secondary)',
          tertiary: 'var(--background-tertiary)',
          card: 'var(--background-card)',
        },
        foreground: {
          DEFAULT: 'var(--foreground)',
          muted: 'var(--foreground-muted)',
          subtle: 'var(--foreground-subtle)',
        },
        // Professional semantic palette — class names kept for backward-compat
        neon: {
          cyan: '#6366f1',          // indigo-500  (primary accent)
          magenta: '#8b5cf6',       // violet-500  (secondary)
          green: '#10b981',         // emerald-500 (success)
          orange: '#f59e0b',        // amber-500   (warning)
          purple: '#a855f7',        // purple-500
          blue: '#3b82f6',          // blue-500
          pink: '#ec4899',          // pink-500
          yellow: '#eab308',        // yellow-500
        },
        status: {
          pending: '#f59e0b',
          running: '#6366f1',
          awaiting: '#8b5cf6',
          completed: '#10b981',
          failed: '#ef4444',
          expired: '#52525b',
        },
        border: {
          DEFAULT: 'var(--border)',
          glow: 'rgba(99, 102, 241, 0.25)',
        },
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'neon-cyan':
          '0 0 0 1px rgba(99, 102, 241, 0.25), 0 4px 12px rgba(0, 0, 0, 0.4)',
        'neon-magenta':
          '0 0 0 1px rgba(139, 92, 246, 0.25), 0 4px 12px rgba(0, 0, 0, 0.4)',
        'neon-green':
          '0 0 0 1px rgba(16, 185, 129, 0.25), 0 4px 12px rgba(0, 0, 0, 0.4)',
        'neon-orange':
          '0 0 0 1px rgba(245, 158, 11, 0.25), 0 4px 12px rgba(0, 0, 0, 0.4)',
        glass:
          '0 8px 32px rgba(0, 0, 0, 0.4), 0 1px 0 rgba(255, 255, 255, 0.04) inset',
        glow: '0 0 0 1px rgba(99, 102, 241, 0.2), 0 4px 20px rgba(99, 102, 241, 0.1)',
        card: '0 1px 3px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.03) inset',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        // subtle ambient gradient for page background
        'ambient':
          'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.08), transparent)',
      },
      animation: {
        'fade-in': 'fadeIn 0.15s ease-out',
        'slide-up': 'slideUp 0.15s ease-out',
        'pulse-glow': 'pulseSubtle 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}

export default config
