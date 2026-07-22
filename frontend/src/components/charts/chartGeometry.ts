// Coluna com topo arredondado e base quadrada, nascendo da baseline - mesmo
// path em todos os gráficos de barra/coluna, pra manter a mesma "anatomia".
export function roundedTopBarPath(x: number, y: number, w: number, h: number, r: number): string {
  if (h <= 0) return ''
  const radius = Math.min(r, w / 2, h)
  if (radius <= 0) return `M${x},${y + h} L${x},${y} L${x + w},${y} L${x + w},${y + h} Z`
  return `M${x},${y + h} L${x},${y + radius} Q${x},${y} ${x + radius},${y} L${x + w - radius},${y} Q${x + w},${y} ${x + w},${y + radius} L${x + w},${y + h} Z`
}

// Passo "redondo" pro eixo Y (1/2/5/10 x potência de 10), dado um valor
// máximo e uma quantidade alvo de ticks.
export function niceStep(maxValue: number, targetTicks = 4): number {
  const rawStep = Math.max(maxValue, 1) / targetTicks
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const residual = rawStep / magnitude
  const niceResidual = residual <= 1 ? 1 : residual <= 2 ? 2 : residual <= 5 ? 5 : 10
  return Math.max(1, niceResidual * magnitude)
}

// Ticks do eixo Y a partir do maior valor plotado - mesmo par (step, axisMax,
// ticks[]) que os 3 gráficos numéricos calculavam cada um por conta própria.
export function buildNiceTicks(rawMax: number, targetTicks = 4): { axisMax: number; ticks: number[] } {
  const step = niceStep(rawMax, targetTicks)
  const axisMax = Math.max(step, Math.ceil(rawMax / step) * step)
  const ticks: number[] = []
  for (let t = 0; t <= axisMax + 1e-9; t += step) ticks.push(Math.round(t))
  return { axisMax, ticks }
}
