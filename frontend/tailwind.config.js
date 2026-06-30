/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // ============================================================
      // 颜色系统（Primary + Accent）
      // ============================================================
      colors: {
        space: {
          DEFAULT: '#FFFFFF',
          light: '#FAFAFA',
          card: '#FFFFFF',
          lighter: '#F5F5F5',
        },
        text: {
          primary: '#1F2937',
          secondary: '#6B7280',
          muted: '#9CA3AF',
        },
        border: {
          DEFAULT: '#E5E7EB',
        },
        // Primary 色系（主色 - 蓝色/靛蓝系）
        primary: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',    // 主色
          600: '#4f46e5',    // hover 主色
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        // Accent 色系（强调色 - 紫色/粉紫系）
        accent: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',    // 主强调色
          600: '#9333ea',    // hover 强调色
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
          950: '#3b0764',
        },
        // 成功色
        success: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        // 警告色
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        // 危险色
        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        // 灰色系（扩展）
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
          950: '#030712',
        },
        // 表面色
        surface: {
          DEFAULT: '#ffffff',
          secondary: '#fafafa',
          tertiary: '#f5f5f5',
          hover: '#f0f0f0',
        },
        // 文字色
        text: {
          primary: '#1f2937',
          secondary: '#6b7280',
          muted: '#9ca3af',
          light: '#d1d5db',
        },
        // 边框色
        border: {
          DEFAULT: '#e5e7eb',
          light: '#f3f4f6',
          hover: '#d1d5db',
        },
      },
      // ============================================================
      // 字体
      // ============================================================
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      // ============================================================
      // 边框半径
      // ============================================================
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
      // ============================================================
      // 阴影
      // ============================================================
      boxShadow: {
        'primary': '0 4px 14px 0 rgba(99, 102, 241, 0.4)',
        'primary-lg': '0 8px 30px 0 rgba(99, 102, 241, 0.3)',
        'accent': '0 4px 14px 0 rgba(168, 85, 247, 0.4)',
        'accent-lg': '0 8px 30px 0 rgba(168, 85, 247, 0.3)',
        'success': '0 4px 14px 0 rgba(16, 185, 129, 0.4)',
        'danger': '0 4px 14px 0 rgba(239, 68, 68, 0.4)',
      },
      // ============================================================
      // 动画
      // ============================================================
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-down': 'slideDown 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}