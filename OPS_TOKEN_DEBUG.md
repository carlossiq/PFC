# OPS Token - Verificação e Debug

## 🔑 Verificar Status do Token

**Rota:**
```bash
curl -X GET "http://localhost:8000/api/v1/chat/ops-token-status"
```

**Resposta com Token Válido:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "is_valid": true,
    "is_expired": false,
    "access_token": "LOglAmD9xWqbumFVpKfS...",
    "created_at": "2026-04-24T20:57:07.551349",
    "expiration_time": "2026-04-24T21:17:06.551349",
    "time_until_expiration_seconds": 1199,
    "expires_in_seconds": 1199
  },
  "message": "OPS token is valid"
}
```

---

## 📋 Campos do Token

| Campo | Significado | Exemplo |
|-------|------------|---------|
| **is_valid** | Token é válido e não expirou | `true` / `false` |
| **is_expired** | Token expirou | `false` / `true` |
| **access_token** | Token OAuth2 (primeiros 20 chars) | `LOglAmD9xWqbumFVpKfS...` |
| **created_at** | Data/hora de criação | `2026-04-24T20:57:07` |
| **expiration_time** | Data/hora de expiração | `2026-04-24T21:17:06` |
| **time_until_expiration_seconds** | Segundos até expiração | `1199` (≈20 min) |
| **expires_in_seconds** | Duração total do token | `1199` (≈20 min) |

---

## ⚠️ Problemas Comuns

### 1. Credenciais Inválidas

**Erro:**
```json
{
  "success": false,
  "error": "OPS credentials error: ...",
  "hint": "Check OPS_CONSUMER_KEY and OPS_CONSUMER_SECRET in .env"
}
```

**Solução:**
Verifique no `.env`:
```bash
grep -E "OPS_CONSUMER|OPS_SECRET" .env
```

Se estiver vazio ou inválido, obtenha novas credenciais em:
- https://www.epo.org/searching-for-patents/data/web-services/ops.html

### 2. Token Expirado

**Resposta:**
```json
{
  "is_valid": false,
  "is_expired": true,
  "time_until_expiration_seconds": -50
}
```

**O que acontece automaticamente:**
- Quando faz uma requisição de busca, o sistema **detecta automaticamente** que o token expirou
- Chama `_ensure_valid_token()` que **renova o token automaticamente**
- Retry a busca com o novo token

**Você NÃO precisa fazer nada manualmente!**

### 3. Conexão Recusada no OPS

**Erro ao renovar:**
```json
{
  "success": false,
  "error": "Connection refused..."
}
```

**Causa:** OPS API está offline ou URL está errada

**Verificar:**
```bash
curl -I "https://ops.epo.org/auth/accesstoken"
```

---

## 🔄 Fluxo Automático de Renovação

```
┌─────────────────────────────────────────────────┐
│ 1. User chama /chat/probe/search com query OPS  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. OPSService.search() inicia                   │
│    Chama: await self._ensure_valid_token()      │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
      ▼  Token OK     ▼  Token Expirado/Ausente
    (continua)      await self._get_new_token()
         │                │
         │          ┌─────┴──────────┐
         │          │                │
         │          ▼                ▼
         │      POST /auth/        Erro ao
         │      accesstoken        renovar
         │          │                │
         │          ▼                ▼
         │    Novo token         Erro HTTP 404
         │    armazenado
         │          │
         └──────────┴──────────┐
                      ▼
          Continuar com busca
          (retry automático)
```

---

## 🧪 Teste: Simular Busca com Verificação de Token

**Passo 1:** Verificar token
```bash
curl -s -X GET "http://localhost:8000/api/v1/chat/ops-token-status" | python -m json.tool
```

**Passo 2:** Se token válido, fazer busca
```bash
curl -X POST "http://localhost:8000/api/v1/chat/probe/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "query": "ti = (\"machine learning\") AND (pd within \"20100101 20261231\")",
      "range": "1-10",
      "format": "json"
    },
    "api": "ops"
  }' | python -m json.tool | head -50
```

**Passo 3:** Ver logs
```bash
tail -f /var/log/app.log | grep -i "ops_token"
```

---

## 📊 Tempo de Expiração

O OPS retorna um token válido por **~20 minutos** (1199 segundos):

```
Token criado em:    20:57:07
Token expira em:    21:17:06
Duração:            ~20 minutos
```

**Para evitar timeouts:**
- O sistema renova automaticamente **60 segundos ANTES** da expiração real
- Isso garante que nunca use um token expirado

---

## 🔍 Configuração no .env

```bash
# OPS OAuth2 Credentials
OPS_CONSUMER_KEY=your_consumer_key
OPS_CONSUMER_SECRET=your_consumer_secret

# OPS API Configuration
OPS_ENABLED=true
```

Se os valores estão vazios, a requisição retornará erro ao tentar renovar o token.

---

## 💡 Resumo

✅ **Token Válido:**
- Busca funciona normalmente
- Sem renovação necessária

❌ **Token Expirado:**
- Sistema renova automaticamente
- Retry da busca com novo token
- Usuário não precisa fazer nada

❌ **Credenciais Inválidas:**
- Erro persistente
- Precisa atualizar `.env` com credenciais corretas

