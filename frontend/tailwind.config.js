module.exports = {
  content: [
    "./public/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#6366f1',
          dark: '#4f46e5'
        },
        secondary: {
          DEFAULT: '#8b5cf6',
          dark: '#7c3aed'
        },
        dark: {
          DEFAULT: '#1e293b',
          light: '#334155'
        },
        light: '#f8fafc'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif']
      },
      boxShadow: {
        'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.4)'
      }
    },
  },
  plugins: [],
}
