# PFC API

REST API desenvolvida com **FastAPI** para processamento de linguagem natural (NLP), integrando modelos de linguagem locais via Ollama, extração de palavras-chave, similaridade semântica e análise de texto em português e inglês.

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Framework web | FastAPI 0.135 + Uvicorn |
| Validação de dados | Pydantic v2 |
| NLP — parsing/NER | spaCy (`pt_core_news_sm`, `en_core_web_sm`) |
| NLP — embeddings | sentence-transformers |
| NLP — keywords | KeyBERT |
| NLP — modelos gerais | Transformers (HuggingFace) |
| LLM local | Ollama |
| Deep learning | PyTorch |
| ML utilitários | scikit-learn, NumPy, SciPy |
| Detecção de idioma | langdetect |
| Runtime | Python 3.12 |

---

## Estrutura do projeto

```
PFC/
├── api/
│   ├── main.py               # Entrypoint da aplicação
│   └── app/
│       ├── routers/          # Rotas organizadas por domínio
│       │   └── health.py
│       ├── models/           # Schemas Pydantic (request/response)
│       ├── services/         # Lógica de negócio e NLP
│       └── core/             # Configurações, dependências globais
├── .venv/                    # Ambiente virtual Python
└── README.md
```

---

## Pré-requisitos

- Python 3.12
- [Ollama](https://ollama.com) instalado e rodando localmente (se for usar LLM)

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/<seu-usuario>/PFC.git
cd PFC

# Ative o ambiente virtual
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

---

## Rodando a API

```bash
cd api
uvicorn main:app --reload
```

A API ficará disponível em `http://localhost:8000`.

Documentação interativa (Swagger UI): `http://localhost:8000/docs`

Documentação alternativa (ReDoc): `http://localhost:8000/redoc`

---

## Endpoints

### Health check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

---

## Variáveis de ambiente

Crie um arquivo `.env` na raiz de `api/` quando necessário:

```env
OLLAMA_HOST=http://localhost:11434
```

---

## Licença

Este projeto é desenvolvido como Projeto Final de Curso (PFC). Todos os direitos reservados ao autor.
