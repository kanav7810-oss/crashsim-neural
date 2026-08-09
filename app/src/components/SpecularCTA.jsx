import SpecularButton from './SpecularButton'
import { C } from '../theme'

export default function SpecularCTA({ children, ...rest }) {
  return (
    <SpecularButton
      size="sm"
      radius={6}
      tint={C.accent}
      tintOpacity={0.1}
      blur={10}
      textColor={C.text}
      lineColor={C.accent}
      baseColor={C.borderS}
      intensity={1}
      shineSize={10}
      shineFade={40}
      thickness={1}
      followMouse
      proximity={250}
      {...rest}
    >
      {children}
    </SpecularButton>
  )
}
