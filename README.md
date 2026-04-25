# Technology Prospecting API

A production-ready FastAPI application for technology prospecting and analysis.

---

## 🚀 Quick Start com Docker + Ollama + Open WebUI (Recomendado)

O stack completo com LLM local está pronto para rodar em **um comando**:

```bash
bash setup.sh
```

Isso irá:
1. ✅ Verificar Docker e recursos disponíveis
2. 🐳 Subir 3 containers: API, Ollama, Open WebUI
3. 📥 Fazer pull do modelo Qwen2.5 (~2-3GB, CPU-only)
4. 🎯 Aguardar todos os serviços ficarem prontos
5. 🌐 Exibir URLs de acesso

**Resultado:** Acesse http://localhost:3000 e comece a buscar patentes com IA!

### Pré-requisitos
- **Docker** e **Docker Compose**
- **RAM mínima**: 8GB (usa modelo 7b) ou 4GB (usa modelo 3b)
- **Espaço em disco**: ~3-4GB para modelo + dados

### Stack Architecture

```
┌─────────────────────────────────────────────────┐
│         Open WebUI (Chat Interface)             │
│            http://localhost:3000                │
│   - Gerenciar modelos, tools e prompts          │
│   - Chat com context e histórico                │
│   - Função calling via tools                    │
└────────────────────┬────────────────────────────┘
                     │ HTTP (internal)
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼─────────┐ ┌──▼──────────┐ ┌──▼──────────┐
│   Ollama      │ │ FastAPI     │ │ Docker Net  │
│  (LLM Local)  │ │  (REST API) │ │  (Bridge)   │
│:11434        │ │:8000        │ │             │
│ Qwen2.5:7b  │ │ PFC Tools   │ │             │
│ CPU-only    │ │ Endpoints   │ │             │
└──────────────┘ └─────────────┘ └─────────────┘
```

### Arquivos Importantes
- **docker-compose.yml** - Definição dos 3 containers
- **Dockerfile** - Build da API FastAPI
- **prompts/system_prompt.md** - Instruções para o modelo
- **tools/** - Tools (function calling) para o Open WebUI
  - `refine_topic.py` - Refinar temas em variações
  - `probe_search.py` - Busca exploratória (10-25 docs)
  - `final_search.py` - Busca final (até 500 docs)
  - `analyze_complexity.py` - Analisar complexidade de queries

### Troubleshooting Docker

```bash
# Ver logs
docker logs pfc-ollama
docker logs pfc-api
docker logs pfc-open-webui

# Parar containers
docker-compose down

# Limpar tudo (cuidado!)
docker-compose down -v

# Entrar em um container
docker exec -it pfc-ollama bash
docker exec -it pfc-api bash
```

---

## 💻 Desenvolvimento Local (sem Docker)

Se preferir rodar sem Docker:

## Project Structure

```
project/
├── app/
│   ├── __init__.py
│   └── main.py                 # FastAPI application factory
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       └── health.py           # Health check endpoints
├── core/
│   ├── __init__.py
│   ├── config.py               # Configuration management (Pydantic Settings)
│   └── logging.py              # Structured logging setup
├── middleware/
│   ├── __init__.py
│   └── request_logging.py      # HTTP request logging with run_id tracking
├── schemas/                    # Pydantic models for request/response validation
├── services/                   # Business logic layer
├── pipeline/                   # Data processing workflows
├── db/                         # Database layer and ORM
├── tests/                      # Unit and integration tests
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Requirements

- Python 3.12+
- pip or poetry (for dependency management)

## Setup Instructions

### 1. Clone and Navigate to Project

```bash
cd path/to/project
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate Virtual Environment

**On Linux/macOS:**
```bash
source .venv/bin/activate
```

**On Windows:**
```bash
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
APP_NAME=Technology Prospecting API
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### 6. Run Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

### 7. Access API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Health Check

Test application status:

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "message": "Application is running",
  "run_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Logging

The application uses structured logging with `structlog` for all operations:

- **Log Format**: JSON for easy parsing and aggregation
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Request Tracking**: Each request gets a unique `run_id` for traceability
- **Middleware**: Automatic request/response logging with duration tracking

Example log output:
```json
{
  "event": "request_started",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/api/v1/health",
  "timestamp": "2026-03-29T10:30:45.123Z"
}
```

## Architecture Principles

- **Modular**: Clear separation of concerns with dedicated packages
- **Typed**: Full type hints for improved IDE support and type safety
- **Configurable**: Environment-based configuration via Pydantic Settings
- **Observable**: Structured logging and request tracking throughout
- **Testable**: Clean dependencies and dependency injection ready
- **Scalable**: Foundation for async operations and async database drivers

## Configuration Management

All configuration is managed through environment variables and loaded via `core/config.py`:

- **Development**: Uses `.env` file
- **Production**: Uses environment variables
- **Settings**: Pydantic Settings with validation and type coercion

## Adding New Routes

1. Create a new router in `api/routes/`:

```python
from fastapi import APIRouter

router = APIRouter(tags=["feature"])

@router.get("/endpoint")
async def endpoint():
    """Implementação da funcionalidade."""
    return {"message": "success"}
```

2. Include router in `app/main.py`:

```python
from api.routes import feature
app.include_router(feature.router, prefix=settings.api_prefix)
```

## Adding New Services

1. Create service class in `services/`:

```python
from core.logging import get_logger

logger = get_logger(__name__)

class MyService:
    """Implementação da lógica de negócio."""

    def process(self, data: dict):
        """Processa dados de entrada."""
        return data
```

2. Use in route handlers:

```python
from services.my_service import MyService

@router.post("/action")
async def handle_action(data: dict):
    """Manipulador de requisição."""
    service = MyService()
    return service.process(data)
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

Ensure code follows Python best practices:
- Type hints on all functions
- Docstrings in Portuguese (functions) and English (modules)
- Clear variable and function names

### Adding Dependencies

```bash
pip install package-name
pip freeze > requirements.txt
```

## Deployment

### Docker Support

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

Set environment variables for production:

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
```

## Support

For issues or questions, refer to:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Structlog Documentation](https://www.structlog.org/)
