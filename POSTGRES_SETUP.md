# PostgreSQL Setup Guide

## 🚀 Quick Start

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Verificar Docker instalado

```bash
docker --version
docker-compose --version
```

Se não tiver, [instale Docker Desktop](https://www.docker.com/products/docker-desktop)

### 3. Iniciar PostgreSQL com Docker

```bash
docker-compose up -d
```

**Resultado esperado:**
```
✓ Container postgres iniciado em localhost:5432
✓ PgAdmin disponível em http://localhost:5050
```

### 4. Copiar configuração do banco

```bash
# Copiar o arquivo de exemplo
cp .env.example .env
```

Seu `.env` já está configurado com:
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pfc_db
```

### 5. Executar migrações

```bash
# Se usar Alembic
alembic upgrade head

# Ou se tiver script init_db.py
python -m db.init_db
```

### 6. Iniciar a API

```bash
uvicorn app.main:app --reload
```

API rodará em: `http://localhost:8000`

---

## 📊 Visualizar o Banco

### Opção A: PgAdmin (Interface Web)

**URL:** http://localhost:5050  
**Email:** admin@example.com  
**Senha:** admin

#### Conexão com PostgreSQL:
1. Clique em "Add New Server"
2. **Name:** PostgreSQL
3. **Host:** postgres (ou localhost)
4. **Port:** 5432
5. **Username:** postgres
6. **Password:** postgres
6. **Database:** pfc_db
7. Save

### Opção B: Ferramenta Desktop

Instale [DBeaver Community](https://dbeaver.io/) e conecte em:
- Host: localhost
- Port: 5432
- User: postgres
- Password: postgres
- Database: pfc_db

### Opção C: Terminal

```bash
# Conectar ao banco
docker exec -it pfc_postgres psql -U postgres -d pfc_db

# Alguns comandos úteis:
\dt                    # Listar tabelas
\d research           # Descrever tabela "research"
SELECT * FROM research LIMIT 10;  # Mostrar dados
\q                    # Sair
```

---

## 🛠️ Gerenciar Containers

```bash
# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f postgres

# Parar containers
docker-compose down

# Parar E remover dados
docker-compose down -v

# Reiniciar
docker-compose restart
```

---

## 🔄 Migrar dados (se tiver SQLite antigo)

Se tinha dados no SQLite antigo (`app.db`), pode fazer export:

```bash
# 1. Conectar ao SQLite antigo
sqlite3 app.db

# 2. Exportar como SQL
.output dump.sql
.dump
.exit

# 3. Importar no PostgreSQL
psql -U postgres -d pfc_db < dump.sql
```

---

## ⚠️ Troubleshooting

### Porta 5432 já em uso

```bash
# Encontrar processo
lsof -i :5432

# Matar processo
kill -9 <PID>

# Ou usar porta diferente no docker-compose.yml
# Mudar: "5432:5432" para "5433:5432"
```

### Connection refused

```bash
# Verificar se container está rodando
docker ps | grep postgres

# Se não estiver, iniciar
docker-compose up -d
```

### Banco não foi criado

```bash
# Criar manualmente
docker exec -it pfc_postgres psql -U postgres -c "CREATE DATABASE pfc_db;"
```

---

## ✅ Checklist Final

- [ ] Docker instalado e rodando
- [ ] `docker-compose up -d` executado
- [ ] `pip install -r requirements.txt` executado
- [ ] `.env` configurado com DATABASE_URL correto
- [ ] Migrações rodadas (`alembic upgrade head`)
- [ ] API iniciada com sucesso
- [ ] Consegue acessar http://localhost:5050 (PgAdmin)
- [ ] Consegue visualizar tabelas no PgAdmin

**Pronto! Você tem PostgreSQL rodando! 🎉**
