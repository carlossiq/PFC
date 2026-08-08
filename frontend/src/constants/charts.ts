// Constantes visuais compartilhadas pelos gráficos do app (cores, dimensões).
// Cor de dado (verde da marca) separada das cores de "furniture" do gráfico
// (grid/eixo/texto), que seguem a mesma paleta neutra usada no resto da UI
// (gray-200/300/400/500/700 do Tailwind).
export const CHART_BRAND_GREEN = '#0f9448'
export const CHART_BRAND_GREEN_HOVER = '#0d843f'

// Cores de status (sessão concluída/pendente) - mesmo par já usado nos badges
// do SessionCard (text-[#0f9448]/bg-[#0f9448]/10 pra "Concluída",
// text-amber-600/bg-amber-100 pra "Pendente"), reaproveitado aqui pra manter
// o mesmo significado de cor em toda a UI. Validado como par categórico
// seguro (CVD/contraste) via scripts/validate_palette.js da skill de dataviz.
export const CHART_STATUS_COMPLETED = CHART_BRAND_GREEN
export const CHART_STATUS_COMPLETED_HOVER = CHART_BRAND_GREEN_HOVER
export const CHART_STATUS_PENDING = '#d97706'
export const CHART_STATUS_PENDING_HOVER = '#b45309'

export const CHART_GRID_LINE = '#e5e7eb'
export const CHART_BASELINE = '#d1d5db'
export const CHART_AXIS_TICK_TEXT = '#9ca3af'
export const CHART_AXIS_LABEL_TEXT = '#6b7280'
export const CHART_VALUE_LABEL_TEXT = '#374151'

// Laranja da linha "Sessões abertas" no gráfico de timeline. Não reaproveita
// CHART_STATUS_PENDING (amber) porque esse amber já significa "Pendente" em
// outros lugares da UI - usar a mesma cor aqui confundiria os dois significados.
export const CHART_SESSIONS_OPENED = '#ea580c'
export const CHART_SESSIONS_OPENED_HOVER = '#c2410c'

// Opacidade do preenchimento sob a linha nos gráficos de área ("sombreado").
export const CHART_AREA_FILL_OPACITY = 0.1

// Altura fixa padrão de um gráfico de card (a largura acompanha o container).
export const CHART_HEIGHT = 360

// Margem padrão de todo gráfico de card (grid + eixos + rótulos) - mesma em
// todo gráfico SVG da página de estatísticas.
export const CHART_MARGIN = { top: 28, right: 16, bottom: 44, left: 34 }

// Máximo de barras de um histograma antes de agrupar valores em faixas.
export const CHART_MAX_BUCKETS = 8

// Janela do gráfico de timeline (últimos N dias, incluindo hoje).
export const CHART_TIMESERIES_DAYS = 30
