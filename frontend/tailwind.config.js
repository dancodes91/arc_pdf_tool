/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: '1rem',
        sm: '1rem',
        lg: '1.5rem',
      },
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1280px', // Max width as per design guide
      },
    },
    extend: {
      // Color system from design tokens
      colors: {
        // Base colors
        border: 'var(--color-border-default)',
        input: 'var(--color-input-border)',
        ring: 'var(--color-focus-ring)',
        background: 'var(--color-bg-base)',
        foreground: 'var(--color-text-primary)',

        // Semantic colors
        primary: {
          DEFAULT: 'var(--color-brand-primary)',
          foreground: '#FFFFFF',
        },
        secondary: {
          DEFAULT: 'var(--color-brand-secondary)',
          foreground: '#FFFFFF',
        },
        destructive: {
          DEFAULT: 'var(--color-error)',
          foreground: '#FFFFFF',
        },
        muted: {
          DEFAULT: 'var(--color-bg-muted)',
          foreground: 'var(--color-text-secondary)',
        },
        accent: {
          DEFAULT: 'var(--color-brand-light)',
          foreground: 'var(--color-brand-dark)',
        },
        popover: {
          DEFAULT: 'var(--color-card-bg)',
          foreground: 'var(--color-text-primary)',
        },
        card: {
          DEFAULT: 'var(--color-card-bg)',
          foreground: 'var(--color-text-primary)',
        },

        // Status colors
        success: {
          DEFAULT: 'var(--color-success)',
          light: 'var(--color-success-light)',
          dark: 'var(--color-success-dark)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          light: 'var(--color-warning-light)',
          dark: 'var(--color-warning-dark)',
        },
        error: {
          DEFAULT: 'var(--color-error)',
          light: 'var(--color-error-light)',
          dark: 'var(--color-error-dark)',
        },
        info: {
          DEFAULT: 'var(--color-info)',
          light: 'var(--color-info-light)',
          dark: 'var(--color-info-dark)',
        },

        // Diff colors
        diff: {
          added: 'var(--color-diff-added)',
          'added-bg': 'var(--color-diff-added-bg)',
          removed: 'var(--color-diff-removed)',
          'removed-bg': 'var(--color-diff-removed-bg)',
          changed: 'var(--color-diff-changed)',
          'changed-bg': 'var(--color-diff-changed-bg)',
        },

        // Neutrals
        neutral: {
          50: 'var(--color-neutral-50)',
          100: 'var(--color-neutral-100)',
          200: 'var(--color-neutral-200)',
          300: 'var(--color-neutral-300)',
          400: 'var(--color-neutral-400)',
          500: 'var(--color-neutral-500)',
          600: 'var(--color-neutral-600)',
          700: 'var(--color-neutral-700)',
          800: 'var(--color-neutral-800)',
          900: 'var(--color-neutral-900)',
          950: 'var(--color-neutral-950)',
        },
      },

      // Border radius from tokens
      borderRadius: {
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-md)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        full: 'var(--radius-full)',
      },

      // Spacing (using default Tailwind + custom)
      spacing: {
        '1': 'var(--space-1)',
        '2': 'var(--space-2)',
        '3': 'var(--space-3)',
        '4': 'var(--space-4)',
        '5': 'var(--space-5)',
        '6': 'var(--space-6)',
        '8': 'var(--space-8)',
        '10': 'var(--space-10)',
        '12': 'var(--space-12)',
        '16': 'var(--space-16)',
      },

      // Typography
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      fontSize: {
        'display': ['var(--text-display-size)', { lineHeight: 'var(--text-display-line)', fontWeight: 'var(--text-display-weight)' }],
        'h1': ['var(--text-h1-size)', { lineHeight: 'var(--text-h1-line)', fontWeight: 'var(--text-h1-weight)' }],
        'h2': ['var(--text-h2-size)', { lineHeight: 'var(--text-h2-line)', fontWeight: 'var(--text-h2-weight)' }],
        'h3': ['var(--text-h3-size)', { lineHeight: 'var(--text-h3-line)', fontWeight: 'var(--text-h3-weight)' }],
        'body-16': ['var(--text-body-16-size)', { lineHeight: 'var(--text-body-16-line)' }],
        'body-14': ['var(--text-body-14-size)', { lineHeight: 'var(--text-body-14-line)' }],
        'mono-13': ['var(--text-mono-13-size)', { lineHeight: 'var(--text-mono-13-line)' }],
      },

      // Box shadows
      boxShadow: {
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-md)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },

      // Z-index
      zIndex: {
        'nav': 'var(--z-nav)',
        'popover': 'var(--z-popover)',
        'toast': 'var(--z-toast)',
        'modal': 'var(--z-modal)',
        'tooltip': 'var(--z-tooltip)',
      },

      // Animations
      keyframes: {
        "accordion-down": {
          from: { height: '0' },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: '0' },
        },
        "fade-in": {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        "slide-in-right": {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        "pulse-highlight": {
          '0%, 100%': { backgroundColor: 'transparent' },
          '50%': { backgroundColor: 'var(--color-brand-light)' },
        },
      },
      animation: {
        "accordion-down": "accordion-down var(--duration-standard) var(--ease-out)",
        "accordion-up": "accordion-up var(--duration-standard) var(--ease-in)",
        "fade-in": "fade-in var(--duration-fast) var(--ease-out)",
        "slide-in-right": "slide-in-right var(--duration-modal) var(--ease-out)",
        "pulse-highlight": "pulse-highlight var(--duration-modal) var(--ease-in-out)",
      },

      // Transition durations
      transitionDuration: {
        'micro': 'var(--duration-micro)',
        'fast': 'var(--duration-fast)',
        'standard': 'var(--duration-standard)',
        'modal': 'var(--duration-modal)',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
