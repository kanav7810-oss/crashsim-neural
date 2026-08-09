export const EASE = 'cubic-bezier(0.16, 1, 0.3, 1)'
export const EASE_QUINT = 'cubic-bezier(0.33, 1, 0.68, 1)'
export const DUR = {
  fast: 140,
  base: 200,
  slow: 320,
  xl: 560
}

export const easeOutQuart = (t) => 1 - Math.pow(1 - t, 4)
export const easeOutQuint = (t) => 1 - Math.pow(1 - t, 5)
export const easeOutExpo = (t) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t))

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
