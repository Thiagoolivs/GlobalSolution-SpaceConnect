# PROJECT_STATE.md — Mission Control AI

> Estado atual do projeto: o que funciona, o que está incompleto, métricas e saúde do código.

---

## Estado Geral

| Dimensão | Status | Nota |
|----------|--------|------|
| **Funcionamento local (web)** | ✅ Operacional | `python app.py` na porta 5000 |
| **Versão terminal (PCP)** | ✅ Operacional | `python mission_control.py` (Python puro, sem deps) |
| **Deploy Railway** | ✅ Pronto | Procfile + `DATABASE_URL` + `docs/DEPLOY.md` |
| **Banco de dados** | ✅ Por ambiente | SQLite (dev) / PostgreSQL (prod) via `DATABASE_URL`; migração idempotente |
| **Persistência produção** | ✅ Resolvida (GS2) | PostgreSQL via plugin Railway (TASK-006) |
| **Respostas de IA** | ✅ Completas (GS2) | sem `max_tokens`; tamanho via system prompt |
| **IA (Groq)** | ✅ Integrada | Requer `GROQ_API_KEY` no `.env` |
| **Simulação parametrizável** | ✅ Implementada | perfis + seed + eventos (Fases 1, 6) |
| **Dashboards + energia (SERS)** | ✅ Implementados | 5 gráficos + métricas energéticas (Fases 3, 5) |
| **Testes** | 🟡 Manuais | Smoke tests descartáveis usados na validação; sem suíte pytest persistente |
| **Migrações** | ❌ Ausentes | Apenas `db.create_all()` |
| **Autenticação** | ❌ Ausente | API pública sem auth |

---

## Funcionalidades Implementadas ✅

### Backend
- [x] App factory com Flask (`create_app`)
- [x] 2 modelos SQLAlchemy (`CicloTelemetria`, `MensagemChat`)
- [x] Seed automático com 6 ciclos iniciais no primeiro run
- [x] 10 endpoints REST (/, /api/telemetria/novo, /api/telemetria/manual, /api/copiloto, /api/chat, /api/chat/historico, /api/estatisticas, /api/simulacao/gerar, /api/energetico, /api/alertas)
- [x] **Gerador parametrizável** `gerar_dados_missao(n, perfil, seed, eventos)` — perfis estável/degradação/recuperação/caótica, ruído AR(1), correlação física, eventos pontuais (Fase 1)
- [x] **Alertas expandidos** + classificação de ciclos: `gerar_alertas_avancados`, `classificar_ciclos`, `detectar_outliers`, `calcular_risco` (Fase 2)
- [x] **Métricas energéticas (SERS)**: `calcular_metricas_energeticas`, `resumo_energetico` — P=V·I, balanço, eficiência, recomendação (Fase 3)
- [x] **Geração em lote** sem IA por ciclo + narrativa única `gerar_narrativa_missao` (Fase 6)
- [x] Numeração robusta `MAX(ciclo)+1` (TASK-001) · GET removido de /novo (TASK-002)
- [x] **`mission_control.py`** — versão terminal rule-based em Python puro (PCP), com relatório + seção energética

### Backend — adições GS2
- [x] **Banco por ambiente** (`DATABASE_URL`): SQLite (dev) / PostgreSQL (prod), normaliza `postgres://` (`_database_uri`)
- [x] **Migração idempotente** (`_migrate`): adiciona coluna `classificacao` e faz backfill sem quebrar bancos existentes
- [x] **Classificação da missão persistida** (`classificar_missao`, bandas 0 / 1–5 / 6+) + **justificativa** (`justificar_classificacao`)
- [x] **Leitura inteligente** (`tipo_evento_serie`): Estável/Atenção/Crítico/Recuperação/Outlier/Correlacionado
- [x] **Diagnóstico por variável** (`diagnostico_variaveis`): valor/status/faixa/impacto/recomendação
- [x] **Relatório TXT** fiel ao modelo (`gerar_relatorio_txt`) + **conclusão dinâmica** (`gerar_conclusao_missao`)
- [x] **IA sem truncamento**: removidos os 3 `max_tokens` (resposta completa, salva inteira)
- [x] Endpoints novos: `GET /api/diagnostico`, `GET /api/relatorio`; `/api/alertas` com tipo de evento

### Frontend — adições GS2
- [x] **Diagnóstico Operacional**: cards por variável (status colorido, faixa ideal, impacto, recomendação)
- [x] **Timeline interativa**: cards clicáveis → **modal** de detalhe; só ciclos relevantes + "Ver todos"; **filtros** por tipo sem refresh
- [x] **Export de relatório** server-side (`/api/relatorio`)
- [x] Sumário com **classificação + justificativa** e HUD com STATUS
- [x] Análise por 5 funções validadoras (temperatura, comunicação, energia, O2, estabilidade)
- [x] Cálculo de risco (score 0–10, soma dos scores individuais)
- [x] Detecção de evacuação por regra AND (`temp > 35 AND bat < 30`)
- [x] Tendência da missão (comparação primeiro vs. último ciclo)
- [x] Área mais afetada (acumulado de pontuações por variável)
- [x] Geração de telemetria aleatória realista (`random.uniform`)
- [x] Integração Groq Llama 3.1-8b-instant — insights por ciclo (max 60 tokens)
- [x] Integração Groq Llama 3.1-8b-instant — chat com histórico completo (max 200 tokens)
- [x] Sugestão do copiloto (lógica de prioridade por threshold)
- [x] Estatísticas descritivas completas (média, mediana, mín, máx, amplitude, variância, desvio padrão, CV%, Q1, Q3)
- [x] Fallback de texto em caso de erro Groq
- [x] Banner de evacuação reflete apenas o ciclo mais recente
- [x] Suporte a Railway (PORT env var, host 0.0.0.0, gunicorn no Procfile)

### Frontend
- [x] Dashboard SSR completo com Jinja2
- [x] Banner de evacuação animado (animate-pulse), ativado/desativado dinamicamente
- [x] Header sticky com nome da missão e equipa
- [x] Navbar secundária sticky com 6 links e botão "↑ Topo"
- [x] Scroll-spy com IntersectionObserver (link ativo realçado)
- [x] Smooth scroll global (CSS `scroll-behavior: smooth`)
- [x] `scroll-margin-top` em todas as secções para compensar headers sticky
- [x] 3 summary cards (tendência, módulo crítico, NEXUS-7 status)
- [x] 5 médias cards (SSR)
- [x] Gráfico Chart.js multi-linha com 2 eixos Y (Risco/Bateria/Temperatura)
- [x] Timeline de ciclos em ordem inversa (mais recente no topo)
- [x] Badges coloridos de risco (verde/âmbar/vermelho) por threshold
- [x] Indicadores visuais de alerta por variável (pulsing dot)
- [x] Tag de evacuação por ciclo na timeline
- [x] Painel de Comando: botão de simulação automática
- [x] Painel de Comando: 5 sliders + inputs numéricos sincronizados (injeção manual)
- [x] Feedback NEXUS-7 durante processamento (`setStatus`/`clearStatus`)
- [x] Mensagem `NEXUS-7 — O engenheiro de IA está coletando os dados...`
- [x] Mensagem `NEXUS-7 gerou os dados para o Ciclo X` após sucesso
- [x] `adicionarCiclo()` — atualiza gráfico + prepend card + banner + copiloto sem reload
- [x] Toast notifications (3 tipos: success verde / warning âmbar / error vermelho)
- [x] Toasts apenas para risco ≥ 5 (warning) ou risco ≥ 8 ou evacuação (error)
- [x] Tabela de estatísticas descritivas com cor por CV%
- [x] Chat NEXUS-7 com renderização Markdown (bold, listas, código, etc.)
- [x] Histórico do chat carregado ao iniciar a página
- [x] Enter envia mensagem no chat
- [x] Widget copiloto flutuante (fixed bottom-right, animate-pulse)
- [x] Sugestão do copiloto baseada no último ciclo
- [x] Clique em "Enviar ao Chat de IA" → copia sugestão + scroll + auto-envia
- [x] HTML escaping manual (`escHtml`) para prevenir XSS nas cards geradas por JS
- [x] `syncSlider()` — sincronização bidirecional slider ↔ input numérico

### Frontend — adições (Fases 4/5/6 + redesign)
- [x] **Redesign visual** "console de missão" sóbrio: paleta índigo/slate (acento único), fontes **Sora + JetBrains Mono**, mais respiro/espaçamento, sem grid/scanline
- [x] **Resumo em tempo real** (Fase 4): HUD de vitais (relógio MET, ciclos, risco médio, evac, balanço) + cards e médias recalculados via `sincronizar()` a cada ciclo
- [x] **Dashboards** (Fase 5.1): linha de 5 parâmetros, barras de risco por classificação, doughnut acumulado por área
- [x] **Painel energético** (Fase 5.2): indicadores + consumo×geração×balanço + potência×corrente + recomendação
- [x] **Timeline** com tags (BOM/RUIM/OUTLIER/DESTAQUE) + mural de alertas analíticos
- [x] **Gerador de simulação** (Fase 6): perfil/ciclos/seed/evento, repetir seed, narrativa única da IA, filtro "só críticos", exportar relatório `.txt`

---

## Funcionalidades NÃO Implementadas ❌

- [ ] Autenticação / sessões de usuário
- [ ] Rate limiting nas rotas de IA
- [ ] Alembic / migrações de banco de dados
- [ ] Suíte de testes automatizada persistente (pytest) — validação atual via smoke tests descartáveis
- [ ] Exportação server-side (CSV/PDF) — há export `.txt` client-side na timeline
- [ ] Deletar / resetar ciclos
- [ ] Limitar contexto do chat enviado ao Groq (janela deslizante)
- [ ] Hamburguer menu mobile
- [ ] Persistência do banco no Railway (PostgreSQL ou Volume)
- [ ] Validação de range dos inputs manuais no servidor (TASK-003)
- [ ] Páginas de erro 404/500 personalizadas
- [ ] Self-hosting das bibliotecas JS (Tailwind, Chart.js, Marked.js)

---

## Métricas do Código

| Métrica | Valor |
|---------|-------|
| Linhas — `src/__init__.py` | 53 |
| Linhas — `src/models.py` | 20 |
| Linhas — `src/services.py` | 567 |
| Linhas — `src/routes.py` | 290 |
| Linhas — `app.py` | 7 |
| Linhas — `mission_control.py` (terminal/PCP) | 254 |
| Linhas — `templates/index.html` | ~928 |
| **Total backend Python (web)** | **~937** |
| **Total frontend HTML+JS** | **~928** |
| Endpoints REST | 12 |
| Modelos de banco | 2 |
| Tabelas SQLite | 2 |
| Dependências JS (CDN) | 3 (Tailwind, Chart.js, Marked.js) |
| Fontes (Google Fonts) | Sora + JetBrains Mono |

---

## Dependências e Versões

### Python (requirements.txt)

| Pacote | Versão | Uso |
|--------|--------|-----|
| Flask | 3.1.3 | Framework web |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| SQLAlchemy | 2.0.50 | ORM core |
| groq | 1.4.0 | Cliente Groq API |
| gunicorn | 21.2.0 | Servidor WSGI produção |
| python-dotenv | 1.2.2 | Leitura de `.env` |
| pypdf | 5.4.0 | Leitura de PDFs (análise interna) |
| greenlet | 3.5.1 | Dependência do SQLAlchemy async |

### JavaScript (CDN)

| Biblioteca | Versão | Uso |
|-----------|--------|-----|
| Tailwind CSS | CDN latest | Estilização |
| Chart.js | 4.4.0 | Gráfico multi-linha |
| Marked.js | 9.1.6 | Render Markdown no chat |

---

## Saúde do Projeto por Área

### Segurança: 🟡 Moderada
- Sem autenticação (risco aceitável para demo acadêmica)
- SECRET_KEY tem fallback hardcoded (risco baixo localmente, problemático em produção)
- Sem SRI nos CDNs (risco teórico de supply chain)
- `escHtml()` protege contra XSS nas cards geradas por JS ✅

### Performance: 🟡 Moderada
- `_seed_inicial()` faz COUNT query em cada requisição ao `/` (mínimo impacto, mas desnecessário)
- `_consolidado()` carrega todos os ciclos em memória (escala linearmente)
- Histórico de chat enviado completo ao Groq em cada mensagem (pode crescer sem controle)
- Sem cache em nenhum endpoint

### Manutenibilidade: 🟡 Moderada
- Separação backend em 4 módulos (boa estrutura)
- `index.html` monolítico com ~720 linhas (difícil manutenção)
- Duplicação da lógica copiloto (Python + JS)
- Sem suíte de testes pytest persistente (validação por smoke tests descartáveis)

### Funcionalidade: 🟢 Boa
- Todos os requisitos académicos principais atendidos
- Dashboard interativo e responsivo
- IA integrada e funcional com fallback
- Persistência funcional localmente

### Deploy: 🟢 Bom
- Procfile correto (`gunicorn app:app`)
- PORT env var configurada
- `requirements.txt` completo e pinned
- ⚠️ SQLite não persiste no Railway (único bloqueio para produção real)

---

## Ambiente de Desenvolvimento

```
Sistema Operacional: Windows (PowerShell)
Python: via venv\ no diretório do projeto
Servidor local: flask --app app run (debug=True)
Porta: 5000
Banco: missao.db (SQLite, criado automaticamente)
```

### Como iniciar

```powershell
cd "C:\Users\user\Desktop\Mission Control AI"
.\venv\Scripts\Activate.ps1
python app.py
# Acesse: http://localhost:5000
```

### Versão terminal (PCP — Python puro, sem dependências)

```powershell
python mission_control.py
# Imprime a análise rule-based dos 6 ciclos + relatório final + seção energética
```

### Variáveis de ambiente necessárias

| Variável | Obrigatória | Default |
|---------|-------------|---------|
| `GROQ_API_KEY` | ✅ Sim | — (cai em modo de contingência sem ela) |
| `DATABASE_URL` | Apenas produção | — (sem ela usa SQLite local `missao.db`) |
| `PORT` | Apenas Railway | 5000 |
| `FLASK_DEBUG` | Não | `true` (ignorado sob gunicorn) |
| `SECRET_KEY` | Não (recomendado em prod) | `mission-control-secret` |
