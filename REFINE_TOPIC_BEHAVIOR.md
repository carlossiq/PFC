# Refine Topic - Comportamento Detalhado

## Princípios

1. **Retorna APENAS campos fornecidos pelo usuário**
2. **`area_of_study` é PRESERVADO** (não modificado, mesmo que gerado para tema)
3. **`keywords` são PRESERVADAS** (não modificadas, mesmo que tema seja refinado)
4. **`theme` é SEMPRE refinado** em 4 variações específicas
5. **`description` é gerada APENAS se fornecida como entrada**

---

## Cenários de Entrada/Saída

### Cenário 1: Apenas Theme

**Entrada:**
```json
{
  "theme": "Renewable Energy"
}
```

**Saída:**
```json
{
  "candidates": [
    {
      "theme": "Desenvolvimento de novas tecnologias de armazenamento de energia solar",
      "user_input": {
        "theme": "Renewable Energy",
        "description": null,
        "area_of_study": null,
        "keywords": null
      }
    },
    // ... 3 mais
  ]
}
```

**Comportamento:** Retorna APENAS `theme` (refinado). Nenhum outro campo incluído.

---

### Cenário 2: Theme + Description

**Entrada:**
```json
{
  "theme": "Blockchain",
  "description": "Applications of blockchain technology in supply chain management"
}
```

**Saída:**
```json
{
  "candidates": [
    {
      "theme": "Rastreabilidade de produtos via blockchain na cadeia de suprimentos",
      "description": "Explorando como a tecnologia blockchain...",
      "user_input": {
        "theme": "Blockchain",
        "description": "Applications of blockchain technology in supply chain management",
        "area_of_study": null,
        "keywords": null
      }
    },
    // ... 3 mais
  ]
}
```

**Comportamento:** Retorna `theme` (refinado) + `description` (gerado). Sem `area_of_study` nem `keywords`.

---

### Cenário 3: Theme + Area of Study + Keywords

**Entrada:**
```json
{
  "theme": "Machine Learning",
  "area_of_study": "Finance",
  "keywords": ["deep learning", "neural networks", "AI"]
}
```

**Saída:**
```json
{
  "candidates": [
    {
      "theme": "Modelos de Previsão de Preços de Ações com Machine Learning",
      "area_of_study": "Finance",
      "keywords": ["deep learning", "neural networks", "AI"],
      "user_input": {
        "theme": "Machine Learning",
        "description": null,
        "area_of_study": "Finance",
        "keywords": ["deep learning", "neural networks", "AI"]
      }
    },
    // ... 3 mais
  ]
}
```

**Comportamento:**
- `theme`: REFINADO em 4 variações
- `area_of_study`: **PRESERVADO** como "Finance" (não modificado)
- `keywords`: **PRESERVADAS** exatamente como fornecidas
- `description`: NÃO incluído (não foi entrada)

---

### Cenário 4: Todos os Campos

**Entrada:**
```json
{
  "theme": "Machine Learning in Healthcare",
  "description": "Identify emerging trends in diagnostic AI systems, focusing on deep learning applications",
  "area_of_study": "Healthcare",
  "keywords": ["deep learning", "medical imaging", "diagnostic AI"]
}
```

**Saída:**
```json
{
  "candidates": [
    {
      "theme": "Deep Learning for Early Cancer Detection in Medical Imaging",
      "description": "Applying deep learning algorithms for improved cancer detection...",
      "area_of_study": "Healthcare",
      "keywords": ["deep learning", "medical imaging", "diagnostic AI"],
      "user_input": {
        "theme": "Machine Learning in Healthcare",
        "description": "Identify emerging trends in diagnostic AI systems, focusing on deep learning applications",
        "area_of_study": "Healthcare",
        "keywords": ["deep learning", "medical imaging", "diagnostic AI"]
      }
    },
    // ... 3 mais
  ]
}
```

**Comportamento:** Retorna TODOS os campos fornecidos com:
- `theme`: REFINADO
- `description`: GERADO (respeitando contexto)
- `area_of_study`: PRESERVADO
- `keywords`: PRESERVADAS

---

## Implementação

### Fluxo na Função

```python
# 1. Detectar quais campos o usuário forneceu
user_provided_fields = {
    "theme": True,  # Sempre obrigatório
    "description": intake.description is not None,
    "area_of_study": intake.area_of_study is not None,
    "keywords": intake.keywords is not None,
}

# 2. Informar LLM sobre campos fornecidos
user_input += "\nCampos fornecidos pelo usuário (retorne APENAS estes):\n"
user_input += "- theme: SIM (sempre refine em 4 variações)\n"
if user_provided_fields["description"]:
    user_input += "- description: SIM (gere descrições para cada variação)\n"
if user_provided_fields["area_of_study"]:
    user_input += f"- area_of_study: SIM (PRESERVE exatamente: '{intake.area_of_study}')\n"
if user_provided_fields["keywords"]:
    user_input += f"- keywords: SIM (PRESERVE exatamente: {intake.keywords})\n"

# 3. Processar resposta da LLM
for candidate in candidates:
    processed = {"theme": candidate.get("theme")}
    
    # Incluir APENAS campos que foram entrada
    if user_provided_fields["description"]:
        processed["description"] = candidate.get("description")
    
    if user_provided_fields["area_of_study"]:
        processed["area_of_study"] = intake.area_of_study  # Preservar original
    
    if user_provided_fields["keywords"]:
        processed["keywords"] = intake.keywords  # Preservar originais
```

---

## Resumo

| Campo | Behavior | Exemplo |
|-------|----------|---------|
| **theme** | Sempre refinado em 4 variações | "ML" → "Deep Learning for Medical Imaging" |
| **description** | Gerado SE fornecido | Entrada + Saída = descrições específicas para cada tema |
| **area_of_study** | PRESERVADO (não modificado) | Entrada: "Finance" → Saída: "Finance" (igual em todos os 4) |
| **keywords** | PRESERVADAS (não modificadas) | Entrada: ["AI", "ML"] → Saída: ["AI", "ML"] (igual em todos os 4) |
| **Campos não fornecidos** | Omitidos da resposta | Não incluir no JSON se não foram entrada |

