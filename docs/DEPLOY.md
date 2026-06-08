# DEPLOY.md — Mission Control AI

> Guia de deploy em produção (Railway) + execução local. A troca de ambiente
> (SQLite ↔ PostgreSQL) acontece **somente por variável de ambiente**.

---

## 1. Visão geral

| Item | Local (dev) | Produção (Railway) |
|------|-------------|--------------------|
| Servidor | `python app.py` (Flask dev) | `gunicorn app:app` (via `Procfile`) |
| Banco | SQLite `missao.db` (default) | PostgreSQL (`DATABASE_URL`) |
| IA | `GROQ_API_KEY` no `.env` | `GROQ_API_KEY` nas Variables |
| Debug | `FLASK_DEBUG=true` | desligado (gunicorn não usa `app.run`) |

A seleção do banco é feita em `src/__init__.py` → `_database_uri()`:
- Se `DATABASE_URL` existir, usa-a (normalizando `postgres://` → `postgresql://`).
- Caso contrário, cai no SQLite local. **Sem alterar código para trocar de ambiente.**

---

## 2. Arquivos relevantes

| Arquivo | Papel no deploy |
|---------|-----------------|
| `Procfile` | `web: gunicorn app:app` — comando de start em produção |
| `requirements.txt` | dependências pinadas (inclui `gunicorn` e `psycopg2-binary`) |
| `.python-version` | fixa o Python em `3.11` para o builder (nixpacks) |
| `.env.example` | modelo das variáveis (não versionar o `.env` real) |
| `app.py` | `app = create_app()` — alvo do gunicorn; lê `PORT` no modo local |

---

## 3. Passo a passo — Railway

1. **Subir o código para um repositório GitHub** (público ou privado).
2. No [railway.app](https://railway.app): **New Project → Deploy from GitHub repo** e selecione o repositório.
3. **Adicionar o banco**: no projeto, **New → Database → PostgreSQL**. O Railway cria a variável **`DATABASE_URL`** automaticamente e a injeta no serviço web (referencie-a se necessário).
4. **Configurar variáveis** (aba *Variables* do serviço web):
   - `GROQ_API_KEY` = sua chave Groq
   - `SECRET_KEY` = um valor forte e aleatório
   - (`DATABASE_URL` já vem do plugin Postgres)
5. **Deploy**: o Railway detecta o `Procfile` e roda `gunicorn app:app`. As tabelas são criadas no startup (`db.create_all()`), incluindo a migração idempotente da coluna `classificacao`.
6. **Acessar** a URL pública gerada pelo Railway.

> 💡 Sem o plugin Postgres, a app ainda sobe usando SQLite — porém o disco do
> Railway é **efémero** e o `missao.db` é perdido a cada deploy. Para persistência
> real, **use o PostgreSQL** (passo 3).

---

## 4. Execução local

```bash
python -m venv venv
venv\Scripts\Activate.ps1            # Windows  (source venv/bin/activate no Unix)
pip install -r requirements.txt
copy .env.example .env               # e preencha GROQ_API_KEY
python app.py                        # http://localhost:5000
```

Para testar Postgres localmente, basta exportar `DATABASE_URL=postgresql://...`
antes de iniciar — nada no código muda.

---

## 5. Checklist de produção

- [ ] `GROQ_API_KEY` configurada (sem ela, IA cai no modo de contingência)
- [ ] `SECRET_KEY` forte definida (não usar o fallback de dev)
- [ ] Plugin PostgreSQL ativo e `DATABASE_URL` disponível
- [ ] `gunicorn` e `psycopg2-binary` presentes no `requirements.txt`
- [ ] `.env` e `*.db` **não** versionados (ver `.gitignore`)
- [ ] Deploy concluído e URL respondendo em `/`

---

## 6. Problemas comuns

| Sintoma | Causa provável | Correção |
|---------|----------------|----------|
| `Can't load plugin: sqlalchemy.dialects:postgres` | `DATABASE_URL` com prefixo `postgres://` | já tratado em `_database_uri()` (normaliza para `postgresql://`) |
| Dados somem após deploy | usando SQLite efémero | adicionar plugin PostgreSQL |
| IA retorna "Modo de Contingência" | `GROQ_API_KEY` ausente/inválida | configurar a variável |
| `psycopg2` build error | driver ausente | já incluso `psycopg2-binary` no requirements |
