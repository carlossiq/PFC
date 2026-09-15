# AGIA — Prospecção Tecnológica

Backend (FastAPI, arquitetura hexagonal) + frontend (React/Vite) para prospecção
tecnológica: refino de tema, busca em bases de patentes/artigos, extração de termos,
geração de gráficos analíticos e, por fim, um relatório em LaTeX no padrão REPTEC/AGITEC
(RAG local + LLM).

Este README cobre só o **runbook de setup** (o que rodar, em que ordem). Para entender
a arquitetura, as decisões de design e o que está de fato implementado vs. planejado,
ver [`RELATORIO_TECNICO_SISTEMA.md`](./RELATORIO_TECNICO_SISTEMA.md) — é a fonte de
verdade técnica do projeto, mais detalhada que este arquivo.

---

## Primeira vez (setup do zero)

### 0. Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) rodando
- Python 3.12+
- Node 20+ e npm

### 1. Variáveis de ambiente

```bash
cp .env.example .env
```

O `.env` já tem defaults funcionais pra rodar tudo localmente (Postgres/MinIO/Ollama
apontando pros containers do passo 2, sem nenhuma credencial obrigatória). Só é preciso
editar algo se for:
- apontar `OLLAMA_BASE_URL`/`OLLAMA_API_KEY` pro LLM real da intranet (em vez do Ollama
  local) — **nunca commitar essas credenciais**, `.env` já está no `.gitignore`.
- habilitar buscas reais (Lens/OPS/Scopus) preenchendo os tokens/keys correspondentes —
  sem eles, os adapters dessas fontes ficam desabilitados e o app sobe normalmente assim
  mesmo (log de aviso, não erro).

O frontend já vem com `frontend/.env` configurado pra falar com
`http://localhost:8000/api/v1` (default do backend local) — só mexer se o backend rodar
em outra porta/host.

### 2. Subir os containers

```bash
docker compose up -d --build
```

| Serviço | Porta | Pra quê |
|---|---|---|
| `postgres` | 5432 | Banco principal |
| `pgadmin` | 5050 | UI opcional pra inspecionar o Postgres |
| `minio` | 9000 (API) / 9001 (console) | Armazena os PNGs dos gráficos e o `.tex`/PDF do relatório |
| `ollama` | 11434 | LLM local (teste do pipeline de relatório antes de apontar pra intranet) |
| `chromadb` | 8001 | Vector store do RAG do relatório (8001 no host - 8000 já é a porta do backend) |
| `latex-compiler` | 8090 | Compila o `.tex` em PDF sob demanda |

`--build` só afeta o `latex-compiler` (os demais são imagens prontas) — a primeira vez
demora alguns minutos (instala TeX Live + pacotes via `tlmgr`, precisa de internet só
nesse build). Rodadas seguintes de `docker compose up -d` não reconstroem nada, a menos
que o Dockerfile mude.

Conferir que subiu tudo:

```bash
docker compose ps
curl http://localhost:11434/api/tags          # Ollama
curl http://localhost:8001/api/v2/heartbeat   # ChromaDB
curl http://localhost:8090/health             # latex-compiler
```

Baixar o modelo default do Ollama (senão a geração de texto do relatório falha por
falta de modelo):

```bash
docker exec -it pfc_ollama ollama pull qwen2.5:3b-instruct
```

**GPU (opcional, mas recomendado)**: se você tem uma GPU NVIDIA, o `docker-compose.yml`
já pede o repasse dela pro container `ollama` (`deploy.resources.reservations.devices`).
Sem isso o Ollama roda em CPU silenciosamente — sem erro, só lento (uma geração de texto
que leva ~3s na GPU pode levar mais de 1 minuto na CPU). Pré-requisitos, só no Windows
com Docker Desktop: driver NVIDIA razoavelmente recente (qualquer um dos últimos anos já
serve — CUDA-on-WSL vem embutido) e backend WSL2 do Docker Desktop habilitado (é o
default hoje em dia). Conferir se pegou:

```bash
docker logs pfc_ollama 2>&1 | grep -i "inference compute"
# esperado: library=CUDA name="<sua GPU>" ...
# se vier library=cpu, a GPU não foi repassada - reveja o driver/WSL2
```

### 3. Ambiente Python (backend)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 4. Banco de dados — aplicar as migrações

Com o `postgres` do passo 2 já saudável:

```bash
alembic upgrade head
```

Isso cria/atualiza o schema ativo (`db/research_session_models.py` — `research_session`,
`session_input`, `session_probe_query`, `patent`/`article`, `session_chart`,
`session_report`/`session_report_section`, etc.). As demais tabelas legadas
(`db/models.py`, `db/research_models.py`) não precisam de migração — são criadas
automaticamente (`create_all`) no primeiro `await init_db()`, que já roda sozinho no
startup do backend (passo 5).

### 5. Iniciar o backend

```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger/OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 6. Iniciar o frontend

```bash
cd frontend
npm install
npm run dev
```

Abre em http://localhost:5173.

---

## No dia a dia (depois do setup inicial)

Só repetir o que muda de sessão pra sessão de trabalho:

```bash
docker compose up -d          # se os containers estiverem parados
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

## Criando uma nova migração (quando mexer em `db/research_session_models.py`)

```bash
alembic revision --autogenerate -m "descrição curta da mudança"
```

Sempre **revisar o arquivo gerado** em `alembic/versions/` antes de aplicar — o
autogenerate do Alembic é um ponto de partida, não é confiável pra tudo (ex.: não
detecta mudança de tipo de coluna em alguns bancos, nem renomeações). Depois de revisado:

```bash
alembic upgrade head
```

Pra reverter a última migração (raramente necessário):

```bash
alembic downgrade -1
```

## Rodando os testes

```bash
pytest
```

Seis falhas pré-existentes, sem relação com nada aqui - `test_intake.py` (falha na
coleção: `DocumentTypeEnum` não existe mais em `schemas/intake.py`), `test_llm.py`
(`TEST_MODE` não força mock mesmo com `provider="anthropic"` explícito - vale
investigar, pode estar deixando teste chamar API paga de verdade; e um normalizador
com assinatura desatualizada), `test_dedup.py` (expectativa de normalização de texto
desatualizada) e `test_chat_service_scopus_final_search.py` (3 falhas - estratégia de
busca final Scopus, `"year"` vs `"range"`, parece drift real de lógica, não só teste
velho). As de `test_routes.py` que testavam rotas mortas (`/intake`, `/test/llm`,
`/test/nlp`, `/test/query-builder`, `/test/field-schema`) já foram removidas.

## Saiba mais

- [`RELATORIO_TECNICO_SISTEMA.md`](./RELATORIO_TECNICO_SISTEMA.md) — arquitetura,
  módulos, rotas, decisões de design, o que está ✅ implementado vs. 🔜 planejado.
- `notes/REPTEC_001_2023_TETRA.pdf` — exemplo real de relatório REPTEC/AGITEC, usado
  como referência pra estrutura do relatório gerado pelo sistema.
