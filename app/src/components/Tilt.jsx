import { useRef } from 'react'
import { EASE, prefersReducedMotion } from '../motion'

export default function Tilt({ children, max = 5, className = '', style, ...rest }) {
  const ref = useRef(null)
  const frame = useRef(null)

  const apply = (transform, transition) => {
    const el = ref.current
    if (!el) return
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      el.style.transition = transition
      el.style.transform = transform
    })
  }

  const onMove = (e) => {
    if (prefersReducedMotion()) return
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const px = (e.clientX - r.left) / r.width
    const py = (e.clientY - r.top) / r.height
    const rx = (0.5 - py) * max
    const ry = (px - 0.5) * max
    apply(`perspective(1000px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg)`, 'transform 70ms ease-out')
  }

  const onLeave = () => {
    apply('perspective(1000px) rotateX(0deg) rotateY(0deg)', `transform ${280}ms ${EASE}`)
  }

  return (
    <div
      ref={ref}
      className={`tilt ${className}`}
      style={{ transform: 'perspective(1000px) rotateX(0deg) rotateY(0deg)', willChange: 'transform', ...style }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      {...rest}
    >
      {children}
    </div>
  )
}
