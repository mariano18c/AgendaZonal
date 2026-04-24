/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: {
    files: [
      "./**/*.html",
      "./js/**/*.js"
    ]
  },
  theme: {
    extend: {
      colors: {
        'primary-hsl': 'var(--primary-hsl)',
        'success-soft': 'hsl(142, 70%, 95%)',
        'danger-vibrant': 'hsl(0, 84%, 60%)',
        'surface-900': 'hsl(222, 47%, 11%)',
      },
      backgroundImage: {
        'primary-gradient': 'linear-gradient(135deg, #2563eb, #1d4ed8)',
        'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.1))',
      },
      animation: {
        'pulse-subtle': 'pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'pulse-subtle': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: .7 },
        }
      }
    },
  },
  plugins: [],
}
