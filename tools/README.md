# Tools para Open WebUI

Este diretório contém as **Tools (Function Calling)** que o Open WebUI usa para integrar com a API PFC.

## Como Funciona

1. O modelo LLM (Qwen2.5 rodando no Ollama) recebe a definição das tools
2. Quando apropriado, o modelo solicita chamar uma tool específica
3. Open WebUI executa o código Python da tool
4. O resultado é retornado ao modelo para continuar a conversa

## Estrutura de uma Tool

Cada arquivo Python segue este padrão:

```python
import aiohttp
import asyncio

class Tools:
    """Descrição da ferramenta."""

    async def function_name(self, param1: str, param2: str = "default") -> str:
        """
        Docstring que será lida pelo Open WebUI como descrição da tool.
        
        Args:
            param1: Descrição do parâmetro 1
            param2: Descrição do parâmetro 2
            
        Returns:
            String com o resultado formatado para exibição
        """
        # Implementação aqui
        pass
```

## Tools Disponíveis

### 1. refine_topic.py
**Função:** `refine_topic(theme, description, area_of_study, keywords)`

Refina um tema genérico em 4 variações mais específicas.

**Uso típico:**
- Usuário: "Procuro patentes sobre IA para medicina"
- Tool: Gera 4 variações (Deep Learning Medical, IA Oncology, etc)

### 2. probe_search.py
**Função:** `probe_search(theme, description, area_of_study, keywords, api)`

Executa busca exploratória rápida (10-25 resultados).

**Uso típico:**
- Usuário: "Busca sobre a primeira variação"
- Tool: Constrói query, analisa complexidade, executa busca, mostra top 5 resultados

### 3. final_search.py
**Função:** `final_search(theme, description, area_of_study, keywords, api, max_results)`

Executa busca completa (até 500 resultados).

**Uso típico:**
- Usuário: "Faça uma busca final completa"
- Tool: Constrói query, executa busca, retorna estatísticas

### 4. analyze_complexity.py
**Função:** `analyze_query_complexity(query)`

Analisa a complexidade de uma query booleana.

**Usa típico:**
- Tool interna: Depois que probe_search ou final_search constroem query, chama isso
- Retorna: Score (0-100), nível, operadores, nesting, termos, warnings, recomendações

## Instalando Novas Tools

1. Crie um novo arquivo Python em `/tools/`
2. Defina uma classe `Tools` com método `async`
3. Adicione docstring clara (será usada pelo Open WebUI)
4. O arquivo é automaticamente detectado e carregado

```bash
# Copiar template
cp template_tool.py tools/minha_tool.py

# Editar e salvar
# Open WebUI carrega automaticamente!
```

## Convenções

### Timeout
- Use `timeout=aiohttp.ClientTimeout(total=60)` para operações rápidas
- Use `total=120` ou `total=300` para buscas que podem demorar
- Sempre capture `asyncio.TimeoutError`

### URLs Internas
- Use `http://api:8000` (hostname dentro da rede Docker)
- **NÃO** use `http://localhost:8000` (seria local do container)

### Formatação de Resposta
- Retorne **sempre** uma string formatada em Markdown
- Use `**negrito**`, `_itálico_`, `- bullets`
- Inclua emojis para visual: ✓, ✗, ⚠️, 🔍, etc
- **NÃO** retorne JSON cru

### Tratamento de Erro
```python
try:
    # código aqui
except asyncio.TimeoutError:
    return "❌ Timeout ao conectar com a API (>60s)"
except Exception as e:
    return f"❌ Erro: {str(e)}"
```

### Headers e Parâmetros
```python
# POST com JSON
async with session.post(
    "http://api:8000/api/v1/chat/probe/search",
    json={"query": ..., "api": ...},
    timeout=aiohttp.ClientTimeout(total=120),
) as response:
    result = await response.json()

# GET com parâmetros
async with session.get(
    "http://api:8000/api/v1/chat/apis",
    timeout=aiohttp.ClientTimeout(total=10),
) as response:
    result = await response.json()
```

## Debugging

Se uma tool falhar:

1. **Ver logs do Open WebUI:**
   ```bash
   docker logs pfc-open-webui | grep -i "error\|tool"
   ```

2. **Testar a tool manualmente:**
   ```python
   # Executar localmente
   import asyncio
   from tools.refine_topic import Tools
   
   async def test():
       tool = Tools()
       result = await tool.refine_topic("IA para medicina")
       print(result)
   
   asyncio.run(test())
   ```

3. **Verificar conectividade com API:**
   ```bash
   docker exec pfc-api curl http://localhost:8000/api/v1/health
   ```

## Exemplos de Output

### Sucesso - Probe Search
```
🔍 **Probe Search** - API: OPS

⏳ Construindo query...
✓ Query construída
  - **Complexidade:** 35.2/100 (Moderado)

⏳ Executando busca...
✓ Busca concluída
  - **Documentos encontrados:** 1,234
  - **Documentos retornados:** 10

**Primeiros 5 Resultados:**

1. **Reinforcement Learning for Personalized Cancer Treatment**
   Adaptive treatment planning using deep reinforcement learning for oncology...

2. **AI-Driven Radiotherapy Optimization**
   Computer-aided diagnosis and treatment planning using machine learning...

...

💡 **Próximos passos:**
1. Deseja extrair termos relevantes destes resultados?
2. Deseja refinar a query e fazer nova busca?
3. Deseja prosseguir para a busca final?
```

### Erro - Query Muito Complexa
```
❌ **ATENÇÃO:** Score > 70 - Query muito complexa!

A query gerada tem score 73.24/100 (Complexo).

**Problemas identificados:**
- Muitos operadores: 18 (limite recomendado: 10)
- Muitos ORs relativos a ANDs (OR: 14, AND: 4)
- Total de termos: 16 (recomendado: 5-8)

**Recomendações:**
- Reduzir numero de termos
- Usar campos mais genericos
- Remover termos duplicados

Deseja:
1. Tentar mesmo assim?
2. Simplificar o tema?
3. Voltar e refinar?
```

## Integração com System Prompt

O system prompt (`/prompts/system_prompt.md`) guia o modelo sobre **quando** chamar cada tool. Exemplos:

- "Quando o usuário descrever um tema genérico, use `refine_topic`"
- "Após gerar uma query, análise a complexidade com `analyze_query_complexity`"
- "Se a query passar na validação, execute com `probe_search` ou `final_search`"

---

**Dúvidas?** Ver: `prompts/system_prompt.md` e documentação do Open WebUI.
