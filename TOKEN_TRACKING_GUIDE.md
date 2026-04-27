# Guia de Rastreamento de Tokens

## Visão Geral

O sistema agora rastreia **todos os tokens consumidos** em cada chamada LLM durante o workflow de prospecção tecnológica. Isso permite:

- **Análise de custos**: Quanto cada pesquisa custou
- **Otimização**: Identificar quais fases consomem mais tokens
- **Faturamento**: Cobrar clientes com precisão
- **Histórico**: Visualizar cada chamada LLM feita

## Estrutura de Dados

### Tabela `research_token_usage`

```sql
research_token_usage
├── research_id (FK -> research.id)
├── phase_name (refine, probe, extract, final, search)
├── llm_call_type (generate_candidate_topics, probe_search, etc)
├── call_number (1ª, 2ª, 3ª chamada na mesma fase)
├── model (gemini, gpt-4, claude)
├── model_variant (gemini-1.5-pro, gpt-4-turbo, etc)
├── input_tokens
├── output_tokens
├── total_tokens
├── input_cost_usd
├── output_cost_usd
├── total_cost_usd
├── api_latency_ms
├── status (success, failed, timeout)
└── created_at
```

### Campos na tabela `research`

```python
research
├── total_tokens_used (INT) - Total acumulativo
├── total_cost_usd (FLOAT) - Custo total da pesquisa
└── token_usage (RELATIONSHIP) -> ResearchTokenUsage[]
```

## Uso na ResearchWorkflow

### 1. Após cada chamada LLM, registre os tokens

```python
from services.research_service import ResearchService
from services.token_cost_calculator import calculate_token_cost

# Depois de chamar pipeline.generate_candidate_topics()
input_tokens = 1200  # Tokens enviados
output_tokens = 800  # Tokens recebidos
model = "gemini"
variant = "gemini-1.5-pro"

# Calcular custo
input_cost, output_cost, total_cost = calculate_token_cost(
    model=model,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    variant=variant,
)

# Registrar no banco de dados
await ResearchService.add_token_usage(
    session=session,
    research_id=research.id,
    phase_name="refine",
    llm_call_type="generate_candidate_topics",
    model=model,
    model_variant=variant,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    input_cost_usd=input_cost,
    output_cost_usd=output_cost,
    api_latency_ms=1250,  # Tempo de resposta
    call_number=1,
    status="success",
    metadata={
        "prompt_size": 1200,
        "response_size": 800,
        "temperature": 0.7,
    }
)
```

### 2. Integração com ResearchWorkflow

```python
class ResearchWorkflow:
    async def refine_topic(self, theme, description, area_of_study, keywords):
        """Refinar tema com rastreamento de tokens."""
        start_time = time.time()
        
        # Chamar pipeline
        result = await pipeline.generate_candidate_topics(...)
        
        # Registrar tokens
        await ResearchService.add_token_usage(
            session=self.session,
            research_id=self.research_id,
            phase_name="refine",
            llm_call_type="generate_candidate_topics",
            model="gemini",
            model_variant="gemini-1.5-pro",
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
            input_cost_usd=result.get("input_cost_usd", 0),
            output_cost_usd=result.get("output_cost_usd", 0),
            api_latency_ms=int((time.time() - start_time) * 1000),
        )
        
        return result
```

## Endpoints da API

### 1. Obter histórico completo de tokens

```bash
GET /research/{research_id}/token-usage
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total_tokens": 15000,
    "total_cost_usd": 0.05,
    "call_count": 4,
    "call_history": [
      {
        "timestamp": "2024-04-27T12:00:00.000Z",
        "phase": "refine",
        "call_type": "generate_candidate_topics",
        "call_number": 1,
        "model": "gemini",
        "input_tokens": 1200,
        "output_tokens": 800,
        "total_tokens": 2000,
        "total_cost_usd": 0.0015,
        "api_latency_ms": 1250,
        "status": "success"
      },
      ...
    ]
  }
}
```

### 2. Obter resumo agregado por fase e modelo

```bash
GET /research/{research_id}/token-summary
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total_tokens": 15000,
    "total_cost_usd": 0.05,
    "by_phase": {
      "refine": {
        "tokens": 3000,
        "input_tokens": 1800,
        "output_tokens": 1200,
        "cost_usd": 0.0025,
        "calls": 1
      },
      "probe": {
        "tokens": 5000,
        "input_tokens": 3000,
        "output_tokens": 2000,
        "cost_usd": 0.0042,
        "calls": 1
      },
      "extract": {
        "tokens": 4000,
        "cost_usd": 0.0028,
        "calls": 1
      },
      "final": {
        "tokens": 3000,
        "cost_usd": 0.0005,
        "calls": 1
      }
    },
    "by_model": {
      "gemini (gemini-1.5-pro)": {
        "tokens": 15000,
        "cost_usd": 0.05,
        "calls": 4
      }
    },
    "call_history": [...]
  }
}
```

## Casos de Uso

### 1. Refinar tema múltiplas vezes

Se o cliente quer refinar o tema 3 vezes:

```python
# 1ª chamada
await workflow.refine_topic(...)  # call_number=1

# 2ª chamada (mesma fase)
await workflow.refine_topic(...)  # call_number=2

# 3ª chamada (mesma fase)
await workflow.refine_topic(...)  # call_number=3
```

**Resultado no banco:**
```
research_token_usage
├── call_number=1, phase=refine, tokens=2000, cost=$0.0015
├── call_number=2, phase=refine, tokens=2000, cost=$0.0015
├── call_number=3, phase=refine, tokens=2000, cost=$0.0015
└── Total refine: tokens=6000, cost=$0.0045
```

### 2. Análise de custo por pesquisa

```python
# GET /research/123/token-summary
# Resposta mostra:
# - Total de tokens: 15,000
# - Total de custo: $0.05
# - Maior consumidor: probe (5,000 tokens)
# - Chamadas: 4 (1 refine, 1 probe, 1 extract, 1 final)
```

### 3. Comparar custo entre modelos

Se você quiser comparar o custo de usar Gemini vs GPT-4:

```python
# Com Gemini (atual):
# total_tokens: 15,000
# total_cost: $0.05

# Com GPT-4 seria:
# total_tokens: 15,000 (mesmos tokens)
# total_cost: $0.20 (4x mais caro)
```

## Cálculo de Custos

Os preços são atualizados em `services/token_cost_calculator.py`:

```python
PRICING = {
    "gemini": {
        "gemini-1.5-pro": {"input": 0.075, "output": 0.30},  # por 1M tokens
        "gemini-1.5-flash": {"input": 0.0375, "output": 0.15},
    },
    "gpt-4": {
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    },
    "claude": {
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    },
}
```

Para adicionar um novo modelo:
```python
PRICING["seu-modelo"] = {
    "seu-modelo-variant": {"input": X, "output": Y}
}
```

## Próximas Etapas

1. **Integrar no ResearchWorkflow**: Adicionar chamadas a `add_token_usage()` após cada LLM call
2. **Frontend**: Mostrar token usage no painel de pesquisa
3. **Relatório**: Incluir custo total no relatório LaTeX
4. **Alertas**: Notificar se custo exceder limite
5. **Analytics**: Dashboard de custos por cliente/período

## Exemplo de Fluxo Completo

```python
# 1. Criar pesquisa
research = await ResearchService.create_research(
    session=session,
    title="E-commerce Recommendation Systems",
    user_input={"theme": "recommendation", ...}
)

# 2. Refinar tema
await workflow.refine_topic(...)
# -> Registra: phase=refine, tokens=2000, cost=$0.0015

# 3. Probe search
await workflow.build_and_execute_probe_search(...)
# -> Registra: phase=probe, tokens=5000, cost=$0.0042

# 4. Extrair termos
await workflow.extract_terms(...)
# -> Registra: phase=extract, tokens=4000, cost=$0.0028

# 5. Gerar final queries
await workflow.build_final_queries(...)
# -> Registra: phase=final, tokens=3000, cost=$0.0005

# 6. Consultar resumo
summary = await ResearchService.get_token_summary(session, research.id)
# {
#   "total_tokens": 14000,
#   "total_cost_usd": 0.009,
#   "by_phase": {...},
#   "by_model": {...},
# }
```
