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
        // Risk levels
        'risk-critical': '#DC2626',
        'risk-high': '#F59E0B',
        'risk-medium': '#FCD34D',
        'risk-low': '#10B981',
        
        // Custom dark theme
        background: '#0A0E27',
        surface: '#141B3D',
        'surface-light': '#1E2A4A',
        border: '#2D3561',
        
        // Accents
        accent: {
          blue: '#3B82F6',
          purple: '#8B5CF6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
