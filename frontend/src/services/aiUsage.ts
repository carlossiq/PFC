// Espelha schemas/session_input.py:SessionAiCallInput - uma chamada de IA
// medida no backend (duração + tokens), ainda não persistida. Devolvida por
// cada endpoint /chat/* que consulta uma LLM (refine-topic, specify-topic,
// probe/queries-multi); acumulada no useFormStore (ver aiCallLog) e reenviada
// como `ai_calls` no próximo save de progresso/finalização (sessionInput.ts).
export interface AiUsage {
  step: string
  provider: string
  model: string
  duration_ms: number
  input_tokens: number | null
  output_tokens: number | null
  total_tokens: number | null
  attempts: number
}
