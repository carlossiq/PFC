# Manual de Instalação — AGIA (Prospecção Tecnológica)

*Atualizado em 26/10/2026.*

Este manual leva uma máquina sem o sistema até a aplicação funcionando. Depois da
instalação, os parâmetros são ajustados na tela Configurações (manual de configuração) e o
uso está no manual do usuário.

---

## 1. Pré-requisitos

### 1.1 Ferramentas

| Ferramenta | Versão | Como instalar | Verificar |
|---|---|---|---|
| Git | Qualquer recente | <https://git-scm.com/downloads> | `git --version` |
| Python | 3.12 | <https://www.python.org/downloads/> (marque **Add python.exe to PATH**) | `python --version` (mostra `3.12.x`) |
| Node.js | 20.19 ou 22.12 e superior (LTS) | <https://nodejs.org/> | `node --version` |
| Docker Desktop | Recente | <https://www.docker.com/products/docker-desktop/> | `docker compose version` |

Para instalar o Docker Desktop pelo terminal, use o winget:

```powershell
winget install -e --id Docker.DockerDesktop
```

No Windows, o Docker Desktop exige o WSL 2. Em um PowerShell como administrador, rode
`wsl --install`, reinicie o computador e abra o Docker Desktop. Aguarde até ele indicar que
está em execução antes de seguir.

Os comandos `docker compose` do passo 2.3 só funcionam com o Docker Desktop em execução. Com
ele fechado, o terminal mostra um erro de conexão com o engine do Docker.

### 1.2 PowerShell

Uma vez, libere a execução de scripts locais, para que a venv possa ser ativada:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Confirme se o Windows pedir. Os exemplos deste manual usam `curl.exe`, o curl do Windows.
No PowerShell, `curl` sem `.exe` é um alias de outro comando e não mostra a mesma saída.

### 1.3 Outros requisitos

- **Internet**: necessária na primeira instalação, para baixar imagens Docker, pacotes
  Python e npm, o modelo do Ollama e o modelo de embeddings.
- **GPU NVIDIA (opcional)**: acelera a geração de texto. Ver a seção 2.3.
- **Credenciais de busca**: sem uma credencial de patentes (OPS ou Lens) e uma de artigos
  (Scopus ou Lens), a busca retorna vazia. Ver a seção 2.2.

---

## 2. Passo a passo

Os comandos são para PowerShell no Windows. Para Linux ou macOS, troque `.venv\Scripts\activate`
por `source .venv/bin/activate`.

### 2.1 Obter o código

```powershell
git clone https://github.com/carlossiq/PFC.git
cd PFC
```

### 2.2 Criar o arquivo `.env`

Na raiz do projeto, crie o arquivo `.env` com o conteúdo abaixo. Ele traz só infraestrutura,
flags e credenciais; os valores já funcionam com os serviços do Docker.

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pfc_db
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
API_PREFIX=/api/v1
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8000"]
LENS_PATENT_ENABLED=True
LENS_SCHOLARLY_ENABLED=True
OPS_ENABLED=True
SCOPUS_ENABLED=True
LENS_ENABLED=True
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=session-charts
MINIO_SECURE=False
CHROMA_HOST=localhost
CHROMA_PORT=8001
LATEX_COMPILER_URL=http://localhost:8090
LANGUAGETOOL_URL=http://localhost:8010
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_API_KEY=
LLM_GEMINI_API_KEY=
LLM_ANTHROPIC_API_KEY=
LENS_API_TOKEN=
OPS_CONSUMER_KEY=
OPS_CONSUMER_SECRET=
SCOPUS_API_KEY=
```

- `ALLOWED_ORIGINS` deve estar em **formato JSON**, como no exemplo. Lista separada por
  vírgula impede o backend de subir.
- Os parâmetros de comportamento (busca, IA, extração de termos, relatório) não entram no
  `.env`. Eles são gravados no banco na primeira subida e ajustados na tela Configurações.
- As credenciais são copiadas para o banco na primeira subida. Depois disso, altere-as pela
  tela Configurações e **reinicie o backend**.

**Credenciais de busca** (as chaves são pessoais; não as envie a repositórios):

- **OPS** (patentes): `OPS_CONSUMER_KEY` e `OPS_CONSUMER_SECRET`, no portal de
  desenvolvedores do Escritório Europeu de Patentes.
- **Scopus** (artigos): `SCOPUS_API_KEY`, no portal de desenvolvedores da Elsevier.
- **Lens** (patentes e artigos, alternativa às anteriores): `LENS_API_TOKEN`, em lens.org.

Sem credencial, o backend sobe com aviso (`container_patent_api_skipped` ou
`container_scholarly_api_skipped`, com `missing_credentials`), mas a busca daquela família
fica vazia.

### 2.3 Subir os serviços de apoio

```powershell
docker compose up -d --build
```

Na primeira execução, o serviço `latex-compiler` é construído e instala o TeX Live e os
pacotes LaTeX. Isso leva alguns minutos e precisa de internet. Execuções seguintes não
reconstroem nada, a menos que o Dockerfile mude.

**Com GPU NVIDIA**, use o override, que é o que repassa a placa ao Ollama:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Use o override **apenas** com GPU NVIDIA. Sem a placa, o container `ollama` não sobe.
Sem o override, o Ollama roda em CPU, sem erro, mas bem mais lento.

Confira o estado:

```powershell
docker compose ps
```

Todos os containers devem estar `running`. `postgres` e `minio` também ficam `healthy`.

### 2.4 Baixar o modelo do Ollama

O container do Ollama sobe sem modelos. Sem o modelo, a geração de texto do relatório e as
queries da IA falham.

```powershell
docker exec -it pfc_ollama ollama pull qwen2.5:3b-instruct
curl.exe http://localhost:11434/api/tags
```

A segunda linha deve listar `qwen2.5:3b-instruct`.

Com GPU, confira se ela foi reconhecida:

```powershell
docker logs pfc_ollama 2>&1 | Select-String "inference compute"
# esperado: library=CUDA. Se aparecer library=cpu, revise o driver NVIDIA e o WSL 2.
```

### 2.5 Ambiente Python do backend

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

O último comando instala o modelo do spaCy, que não vem com os pacotes Python. Sem ele, o
log registra `spacy_model_not_found` e a extração de termos é afetada.

### 2.6 Aplicar as migrações do banco

Com o `postgres` saudável:

```powershell
alembic upgrade head
alembic current
```

A saída de `alembic current` deve ser `9b3d5e7f1a2c (head)`. Este passo é obrigatório antes
do backend: as tabelas de sessão só são criadas pelas migrações.

Para conferir o banco de ponta a ponta, rode o script de verificação, que aplica migrações e
inicialização duas vezes e confere o resultado. Use um banco de teste ou vazio, porque ele
grava o seed:

```powershell
python scripts/verify_fresh_setup.py
```

Saída esperada na última linha: `alembic em 9b3d5e7f1a2c, app_settings com 36 linhas`.

### 2.7 Subir o backend

```powershell
uvicorn app.main:app --reload --port 8000
```

Na primeira subida, o backend cria as demais tabelas, grava as configurações padrão e envia a
capa padrão do relatório ao MinIO, se ainda não houver uma. Ele também carrega o modelo de
embeddings (`distiluse-base-multilingual-cased-v2`), que é baixado do Hugging Face se não
estiver em cache.

- Documentação interativa da API: <http://localhost:8000/docs>.
- Se o MinIO ou o ChromaDB estiverem fora do ar, o backend espera cerca de 30 s por serviço,
  emite um aviso e continua a subida.

### 2.8 Subir o frontend

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Acesse <http://localhost:5173>. O frontend não precisa de configuração quando o backend roda
em `http://localhost:8000`. Para outro endereço, crie `frontend/.env` com
`VITE_API_BASE_URL=<endereço da API>`, a partir de `frontend/.env.example`.

### 2.9 Teste rápido

1. Abra <http://localhost:5173> e clique em **Start**.
2. Digite um tema e clique em **Refinar parâmetros**. A IA deve devolver quatro variações.
3. Volte e clique em **Gerar Query**. Se a busca trouxer resultados, as APIs estão
   configuradas. Se voltar vazia, confira as credenciais.

---

## 3. Verificação

| Verificação | Comando | Resultado esperado |
|---|---|---|
| Containers | `docker compose ps` | Todos `running` |
| Postgres | `docker exec pfc_postgres pg_isready -U postgres` | `accepting connections` |
| Migrações | `alembic current` | `9b3d5e7f1a2c (head)` |
| Backend | `curl.exe http://localhost:8000/api/v1/health` | `{"status":"healthy",...}` |
| Sessões | `curl.exe http://localhost:8000/api/v1/research-session` | `{"success":true,"data":[...]}` |
| Configurações | `curl.exe http://localhost:8000/api/v1/config/settings` | Lista de configurações |
| Ollama | `curl.exe http://localhost:11434/api/tags` | Lista com `qwen2.5:3b-instruct` |
| ChromaDB | `curl.exe http://localhost:8001/api/v2/heartbeat` | Resposta JSON |
| Compilador LaTeX | `curl.exe http://localhost:8090/health` | Resposta de saúde |
| LanguageTool | Abrir <http://localhost:8010> | Página do LanguageTool |
| MinIO | Abrir <http://localhost:9001> | Console (login `minioadmin` / `minioadmin`) |
| Frontend | Abrir <http://localhost:5173> | Tela inicial com o menu lateral |

---

## 4. Operação do dia a dia

```powershell
docker compose up -d                       # containers parados
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000  # backend
```

Em outro terminal: `cd frontend` e `npm run dev`.

Para parar: `Ctrl+C` nos terminais do backend e do frontend, e `docker compose stop` para os
containers. Os dados são preservados.

---

## 5. Atualização

```powershell
git pull
.venv\Scripts\activate
pip install -r requirements.txt            # se a lista de dependências mudou
alembic upgrade head                       # sempre que houver migrações novas
docker compose up -d --build               # se a configuração dos serviços mudou
cd frontend; npm install; cd ..            # se as dependências do frontend mudaram
```

Não apague o banco para atualizar. Depois de atualizar, reinicie o backend.

---

## 6. Testes automatizados

```powershell
pip install -r requirements-dev.txt
pytest
```

---

## 7. Solução de problemas

| Sintoma | Solução |
|---|---|
| `docker compose up` falha com "WSL update required" | Abra um terminal como administrador, rode `wsl --update` e reinicie o Docker Desktop. |
| Porta em uso (5432, 8000, 8001, 9000, 11434…) | Descubra o processo com `netstat -ano \| findstr :PORTA`, pare-o ou troque a porta nos serviços do Docker e no `.env`. |
| Backend não sobe com erro `allowed_origins` | Use `ALLOWED_ORIGINS` em formato JSON (passo 2.2). |
| Log com `spacy_model_not_found` | `python -m spacy download en_core_web_sm` |
| Geração de texto ou queries da IA falha | Baixe o modelo: `docker exec -it pfc_ollama ollama pull qwen2.5:3b-instruct`. |
| Geração muito lenta | Ollama em CPU. Confira o log (`inference compute`) e o passo 2.3. |
| Busca retorna vazia | Preencha as credenciais no `.env` ou na tela Configurações e reinicie o backend. |
| Erro de CORS no navegador | Inclua `http://localhost:5173` em `ALLOWED_ORIGINS` (JSON) e reinicie o backend. |
| Build do `latex-compiler` falha no `tlmgr` | Rode de novo com internet. A imagem pronta compila sem internet. |
| Backend demora ~30 s na subida antes de avisar sobre MinIO ou ChromaDB | Suba os containers antes do backend. Se a porta estiver ocupada, libere-a. |

Para outros problemas, consulte os logs:

```powershell
docker compose logs --tail=100 <servico>   # ex.: postgres, ollama, latex-compiler
```

---

## 8. Desinstalação

```powershell
docker compose stop          # para os containers e preserva os dados
docker compose down          # remove os containers e preserva os volumes
docker compose down -v       # remove também os volumes
```

> `down -v` apaga **permanentemente** sessões, configurações, gráficos e o modelo do Ollama.

---

## 9. Portas e credenciais padrão

| Serviço | Endereço | Credenciais padrão |
|---|---|---|
| Frontend | <http://localhost:5173> | — |
| Backend (API) | <http://localhost:8000/api/v1> | — |
| Swagger | <http://localhost:8000/docs> | — |
| PostgreSQL | `localhost:5432` (banco `pfc_db`) | `postgres` / `postgres` |
| pgAdmin (opcional) | <http://localhost:5050> | `admin@example.com` / `admin` |
| MinIO (API / console) | `localhost:9000` / <http://localhost:9001> | `minioadmin` / `minioadmin` |
| Ollama | <http://localhost:11434> | — |
| ChromaDB | `localhost:8001` | — |
| Compilador LaTeX | <http://localhost:8090> | — |
| LanguageTool | <http://localhost:8010> | — |

Essas credenciais são de desenvolvimento. Troque-as antes de usar o sistema em rede
compartilhada e limite as portas publicadas à máquina local.
