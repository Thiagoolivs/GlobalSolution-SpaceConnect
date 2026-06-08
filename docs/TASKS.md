# TASKS.md — Mission Control AI

> Lista de tarefas pendentes, melhorias identificadas e dívidas técnicas a resolver.
> Organizado por prioridade e categoria.

---

## Legenda

| Ícone | Significado |
|-------|-------------|
| 🔴 | Crítico — afeta funcionamento ou segurança |
| 🟠 | Alto — afeta qualidade ou corretude |
| 🟡 | Médio — melhoria significativa |
| 🟢 | Baixo — nice-to-have |

---

## 🔴 Crítico

### TASK-001 — Corrigir numeração de ciclos (race condition) — ✅ CONCLUÍDA
**Problema:** `CicloTelemetria.query.count() + 1` é incorreto se registros forem deletados e inseguro em multi-thread.  
**Solução:** Helper `_proximo_ciclo()` com `MAX(ciclo)+1`, usado em `nova_telemetria()`, `telemetria_manual()` e `gerar_simulacao()`.  
**Ficheiro:** `src/routes.py`

### TASK-002 — Remover método GET de `/api/telemetria/novo` — ✅ CONCLUÍDA
**Problema:** Endpoint aceitava `GET`, o que viola semântica REST (GET não deve ter efeitos colaterais).  
**Solução:** `methods=["POST"]` apenas (GET agora retorna 405). Frontend já usava POST.  
**Ficheiro:** `src/routes.py`

### TASK-003 — Validação server-side nos inputs manuais — ✅ CONCLUÍDA
**Solução aplicada:** helper `_num(x, default, lo, hi)` em `routes.py` faz parse seguro + clamp de range em `telemetria_manual()` (ex.: temp limitada a 0–60, % a 0–100, O₂ a 0–25). Valores absurdos/inválidos são corrigidos, não causam erro.
**Problema original:** Valores enviados pelo formulário manual não tinham validação de range no servidor — um usuário podia enviar temperatura de 9999°C.  
**Solução:** Adicionar clamp/validação após `float(d.get(...))`:
```python
v[0] = max(0, min(100, v[0]))   # temperatura
v[1] = max(0, min(100, v[1]))   # comunicacao
# etc.
```
**Ficheiro:** `src/routes.py` — função `telemetria_manual()`

### TASK-004 — SECRET_KEY hardcoded como fallback
**Problema:** `SECRET_KEY` tem fallback `"mission-control-secret"` hardcoded — inseguro em produção.  
**Solução:** Gerar via `secrets.token_hex(32)` e exigir variável de ambiente em produção, ou levantar erro se não definida.  
**Ficheiro:** `src/__init__.py`

### TASK-005 — GROQ_API_KEY pode ser None silenciosamente
**Problema:** Se `GROQ_API_KEY` não estiver definida, `Groq(api_key=None)` não levanta erro imediato — falha apenas na primeira chamada API com mensagem obscura.  
**Solução:** Validar no startup:
```python
if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY não definida")
```
**Ficheiro:** `src/services.py`

---

## 🟠 Alto

### TASK-006 — Persistência do banco de dados no Railway — ✅ CONCLUÍDA (GS2)
**Solução aplicada (Opção A):** `_database_uri()` lê `DATABASE_URL` (normaliza `postgres://`→`postgresql://`); `psycopg2-binary` no `requirements.txt`; guia em `docs/DEPLOY.md`. Basta adicionar o plugin PostgreSQL no Railway — sem alterar código.
**Ficheiro:** `src/__init__.py`, `requirements.txt`, `docs/DEPLOY.md`

### TASK-007 — `_seed_inicial()` chamado em cada requisição a `/`
**Problema:** A função faz uma query `COUNT(*)` a cada carregamento do dashboard — desnecessário após o primeiro seed.  
**Solução:** Usar uma flag de aplicação ou checar apenas uma vez com `before_first_request` / `g`:
```python
_seeded = False
def _seed_inicial():
    global _seeded
    if _seeded: return
    if CicloTelemetria.query.count() == 0:
        # ... seed
    _seeded = True
```
**Ficheiro:** `src/routes.py`

### TASK-008 — Médias e cards de resumo não atualizam dinamicamente — ✅ CONCLUÍDA
**Problema:** Ao adicionar ciclos via JS, as secções de médias/tendência/módulo permaneciam com dados do SSR inicial.  
**Solução:** `atualizarResumo()` recalcula médias/tendência/módulo/risco médio/críticos a partir de `CICLOS_DATA`, chamada por `sincronizar()` a cada mudança.  
**Ficheiro:** `templates/index.html`

### TASK-009 — Histórico de chat ilimitado enviado ao Groq — 🔺 PRIORIDADE (GS2)
**Nota GS2:** com a remoção do `max_tokens` (ADR-021), respostas podem ser maiores; limitar o histórico enviado passou a ser mais relevante para conter custo/latência.  
**Problema:** `obter_resposta_chat()` envia todo o histórico em cada mensagem — sem limite de tokens.  
**Solução:** Implementar janela deslizante (ex: últimas 20 mensagens) ou sumarização:
```python
historico = historico[-20:]  # últimas 20 mensagens
```
**Ficheiro:** `src/services.py` — `obter_resposta_chat()`

### TASK-010 — Adicionar Alembic para migrações de banco
**Problema:** `db.create_all()` não suporta migrações incrementais — qualquer mudança de schema requer resetar o banco.  
**Solução:** `pip install flask-migrate` + `flask db init` + workflows de migração  
**Ficheiros:** `src/__init__.py`, novo `migrations/`

### TASK-011 — `.gitignore` incompleto — ✅ CONCLUÍDA
**Solução aplicada:** `.gitignore` expandido com `venv/`, `*.db`, `missao.db`, `.DS_Store`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `.claude/launch.json` e mais.
**Problema original:** Faltavam entradas críticas:
```
venv/
missao.db
*.db
.DS_Store
*.egg-info/
dist/
.pytest_cache/
```
**Ficheiro:** `.gitignore`

### TASK-012 — `to_dict()` definido mas nunca usado — ✅ CONCLUÍDA
**Solução aplicada:** método `to_dict()` morto removido de `CicloTelemetria`; serialização permanece centralizada em `_fmt_ciclo()` (`routes.py`).
**Ficheiro:** `src/models.py`

---

## 🟡 Médio

### TASK-013 — Rate limiting nas rotas de IA
**Problema:** Nenhum limite de requisições — possível abuso da GROQ_API_KEY.  
**Solução:** `pip install flask-limiter` + decorador `@limiter.limit("10/minute")` nas rotas de telemetria e chat.

### TASK-014 — Sem tratamento de erros HTTP (404, 500)
**Problema:** Erros do Flask retornam HTML padrão sem estilo.  
**Solução:** Adicionar `@app.errorhandler(404)` e `@app.errorhandler(500)` com templates próprios.

### TASK-015 — Duplicação: `gerar_sugestao_copiloto` (Python) ≈ `gerarSugestao` (JS)
**Problema:** A lógica de sugestão do copiloto está duplicada — backend em `services.py` e frontend em `index.html`.  
**Solução:** O frontend deve chamar `/api/copiloto` em vez de recalcular localmente, ou manter apenas uma das versões.

### TASK-016 — Adicionar índices ao banco de dados
**Problema:** Consultas `ORDER BY id`, `ORDER BY id DESC` não têm índice explícito (SQLite cria índice no PK automaticamente, mas timestamp e ciclo não têm).  
**Solução:** Adicionar `db.Index` em campos frequentemente filtrados.

### TASK-017 — Secção "Médias" sem ID de navegação — ✅ CONCLUÍDA
**Problema:** A secção de médias de sustentabilidade não tinha `id` para ser atingida pela navbar.  
**Solução:** `id="section-medias"` + link na navbar (scroll-spy cobre a secção).

### TASK-018 — Sliders reset após injeção manual
**Problema:** Ao submeter o formulário manual, os sliders voltam ao valor padrão no próximo uso.  
**Solução:** Manter os valores dos sliders como estado no JS ou usar `localStorage` para persistir entre sessões.

### TASK-019 — Nenhum teste automatizado
**Problema:** Zero testes — nenhum unitário, integração ou end-to-end.  
**Solução:** `pip install pytest flask-testing` + testes para `services.py` e rotas da API.

### TASK-020 — Adicionar página de exportação de dados
**Solução:** Endpoint `GET /api/export/csv` que retorna `missao.db` em CSV, com download via `flask.send_file`.

---

## 🟢 Baixo / Nice-to-have

### TASK-021 — Substituir CDNs por self-hosting
**Problema:** Tailwind, Chart.js, Marked.js e Google Fonts via CDN — dependência de terceiros, sem SRI, não funciona offline.  
**Solução:** `npm install` + servir via `static/` com Flask, adicionar SRI hashes.

### TASK-022 — Hamburguer menu para mobile
**Problema:** A navbar horizontal não é otimizada para telas pequenas (< 375px).  
**Solução:** Adicionar menu colapsável para mobile com botão hamburguer.

### TASK-023 — Dark/Light mode toggle
**Solução:** Adicionar botão de toggle e classes condicionais com `localStorage`.

### TASK-024 — Reset / Limpeza do banco
**Solução:** Endpoint `POST /api/reset` (autenticado) que trunca `CicloTelemetria` e `MensagemChat`, e retorna o seed inicial.

### TASK-025 — WebSockets para push real-time
**Problema:** Ciclos são apenas adicionados manualmente (botões). Não há push server-side.  
**Solução:** `pip install flask-socketio` + emitir evento ao criar novo ciclo.

### TASK-026 — Configurar missão dinamicamente
**Problema:** `NOME_MISSAO` e `EQUIPE` estão hardcoded em `routes.py`.  
**Solução:** Mover para `app.config` ou para variáveis de ambiente.

### TASK-027 — Gráfico de distribuição de frequências
**Solução:** Adicionar um segundo chart (histograma/bar) para complementar a tabela de estatísticas — cumpriria melhor o requisito de Modelagem Linear.

### TASK-028 — Adicionar CORS headers
**Solução:** `pip install flask-cors` para permitir que a API seja consumida por outros clientes (mobile, Postman, etc.).
