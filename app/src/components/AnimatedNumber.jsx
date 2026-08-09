import { useEffect, useRef, useState } from 'react'
import { easeOutQuart, prefersReducedMotion } from '../motion'

export default function AnimatedNumber({ value, format = (v) => String(v), duration = 520 }) {
  const fromRef = useRef(0)
  const rafRef = useRef(null)
  const [display, setDisplay] = useState(value ?? 0)

  useEffect(() => {
    if (prefersReducedMotion()) {
      setDisplay(value ?? 0)
      fromRef.current = value ?? 0
      return
    }
    const from = fromRef.current
    const to = value ?? 0
    if (from === to) {
      setDisplay(to)
      return
    }
    const start = performance.now()
    const step = (now) => {
      const t = Math.min((now - start) / duration, 1)
      setDisplay(from + (to - from) * easeOutQuart(t))
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step)
      } else {
        fromRef.current = to
        setDisplay(to)
      }
    }
    rafRef.current = requestAnimationFrame(step)
    return () => {
      cancelAnimationFrame(rafRef.current)
      fromRef.current = to
    }
  }, [value, duration])

  return format(display)
}
