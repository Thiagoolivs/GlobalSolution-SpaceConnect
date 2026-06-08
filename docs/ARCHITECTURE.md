# ARCHITECTURE.md — Mission Control AI

> Arquitetura técnica completa: camadas, módulos, banco de dados, endpoints e frontend.

---

## Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER (Cliente)                   │
│  Tailwind CSS · Chart.js 4.4 · Marked.js 9.1           │
│  JavaScript vanilla (SPA-like) · Fetch API             │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (JSON / HTML)
┌────────────────────────▼────────────────────────────────┐
│              FLASK APPLICATION (Servidor)                │
│  app.py → create_app() → Blueprint → routes.py         │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  __init__.py│  │   routes.py  │  │  services.py  │  │
│  │ Factory+DB  │  │ 12 Endpoints │  │  Groq + Logic │  │
│  └─────────────┘  └──────┬───────┘  └───────┬───────┘  │
│                           │                  │          │
│  ┌────────────────────────▼──────────────────▼───────┐  │
│  │              models.py (SQLAlchemy ORM)           │  │
│  │  CicloTelemetria · MensagemChat                   │  │
│  └────────────────────────┬──────────────────────────┘  │
│                            │                            │
│  ┌─────────────────────────▼────────────────────────┐   │
│  │   SQLite (dev) / PostgreSQL (prod) via DATABASE_URL│  │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  GROQ CLOUD API                         │
│           Llama 3.1-8b-instant (LLM)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Estrutura de Ficheiros

```
Mission Control AI/
│
├── app.py                  # Entry point; lê PORT do ambiente para Railway
├── Procfile                # web: gunicorn app:app
├── requirements.txt        # dependências fixadas (inclui psycopg2-binary)
├── mission_control.py      # versão terminal (PCP, Python puro)
├── .env / .env.example     # GROQ_API_KEY, DATABASE_URL (real não versionado)
├── .python-version         # 3.11 (builder Railway)
├── .gitignore              # categorizado (segredos, db, venv, .claude, logs)
├── README.md               # Documentação pública do projeto
├── missao.db               # SQLite gerado em runtime (dev)
│
├── src/                    # Pacote Python principal
│   ├── __init__.py         # App factory + DB por env + migração idempotente
│   ├── models.py           # 2 modelos ORM (CicloTelemetria com `classificacao`)
│   ├── routes.py           # Blueprint "main" com 12 rotas
│   └── services.py         # Lógica de negócio + cliente Groq
│
├── templates/
│   └── index.html          # Template único (~928 linhas): SSR + JS
│
└── docs/                   # Documentação técnica interna
    ├── PROJECT.md
    ├── ARCHITECTURE.md
    ├── DECISIONS.md
    ├── TASKS.md
    └── PROJECT_STATE.md
```

---

## Módulos Backend

### `app.py`
Entry point mínimo. Cria a aplicação via factory e lê `PORT` do ambiente.
- Compatível com Railway (host `0.0.0.0`, porta via `$PORT`)
- `FLASK_DEBUG=false` desativa debug em produção

### `src/__init__.py` — App Factory
- `create_app()` inicializa Flask, SQLAlchemy, Blueprint, executa `db.create_all()` e `_migrate()`
- `_database_uri()` resolve o banco por `DATABASE_URL` (SQLite dev / PostgreSQL prod; normaliza `postgres://`)
- `_migrate()` adiciona a coluna `classificacao` de forma idempotente (preserva dados)
- `SECRET_KEY` lido do ambiente com fallback (dívida técnica)

### `src/models.py` — ORM

#### `CicloTelemetria`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer PK | Auto-increment |
| `ciclo` | Integer | Número sequencial do ciclo |
| `temperatura` | Float | °C interno |
| `comunicacao` | Float | % de sinal |
| `bateria_solar` | Float | % de carga |
| `consumo_o2` | Float | L/min |
| `matriz` | Float | % de estabilidade |
| `risco` | Integer | Score 0–10 |
| `classificacao` | String(20) | MISSÃO ESTÁVEL / EM ATENÇÃO / CRÍTICA (GS2) |
| `alerta_evacuacao` | Boolean | `temp > 35 AND bat < 30` |
| `ia_insight` | Text | Resposta do Groq (sem truncamento) |
| `timestamp` | DateTime | UTC auto |

> ℹ️ Serialização centralizada em `_fmt_ciclo()` (`routes.py`). O antigo `to_dict()` morto foi removido (TASK-012).
> ℹ️ A coluna `classificacao` é adicionada por migração idempotente (`_migrate()` em `__init__.py`), preservando bancos existentes (SQLite e PostgreSQL).

#### `MensagemChat`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer PK | Auto-increment |
| `role` | String(10) | `"user"` ou `"assistant"` |
| `content` | Text | Conteúdo da mensagem |
| `timestamp` | DateTime | UTC auto |

### `src/services.py` — Camada de Serviço

| Função | Responsabilidade |
|--------|-----------------|
| `analisar_temperatura(v)` | Retorna `(score, texto)` — 0/1/2 |
| `analisar_comunicacao(v)` | Idem |
| `analisar_energia(v)` | Idem |
| `analisar_oxigenio(v)` | Idem |
| `analisar_estabilidade(v)` | Idem |
| `detectar_evacuacao(temp, bat)` | `bool` — regra AND combinada |
| `obter_insight_ia(idx, valores, risco)` | Chama Groq, retorna texto |
| `gerar_telemetria_simulada()` | `random.uniform` para 5 variáveis |
| `processar_linha(valores, idx)` | Orquestra análise + IA → `(risco, evac, ia, alertas)` |
| `gerar_sugestao_copiloto(ciclo)` | Regra de prioridade para sugestão do widget |
| `obter_resposta_chat(historico, pergunta)` | Monta contexto completo e chama Groq |

**Groq Client**: instanciado uma vez a nível de módulo (`groq_client = Groq(...)`). Sem retry, sem timeout configurado.

### `src/routes.py` — Blueprint "main"

#### Funções auxiliares (privadas)

| Função | Descrição |
|--------|-----------|
| `_seed_inicial()` | Insere 6 ciclos se DB vazio — chamado em cada requisição a `/` |
| `_fmt_ciclo(c)` | Serializa `CicloTelemetria` → `dict` para JSON/Jinja2 |
| `_consolidado(ciclos)` | Calcula médias, tendência, área mais afetada |
| `_salvar_ciclo(v, proximo)` | Processa + persiste um ciclo, retorna dados para a rota |

---

## Endpoints da API

| Método | Rota | Descrição | Resposta |
|--------|------|-----------|----------|
| `GET` | `/` | Dashboard SSR completo | HTML |
| `POST` | `/api/telemetria/novo` | Gera ciclo aleatório via NEXUS-7 | JSON |
| `POST` | `/api/telemetria/manual` | Injeta ciclo (valores validados/clampados) | JSON |
| `POST` | `/api/simulacao/gerar` | Gera missão parametrizável em lote + narrativa | JSON |
| `GET` | `/api/energetico` | Métricas energéticas (resumo + por ciclo) | JSON |
| `GET` | `/api/alertas` | Alertas analíticos + classificação/tipo por ciclo | JSON |
| `GET` | `/api/diagnostico` | Diagnóstico do último ciclo (status/faixa/impacto/ação) | JSON |
| `GET` | `/api/relatorio` | Relatório completo da missão | text/plain |
| `GET` | `/api/copiloto` | Sugestão proativa do último ciclo | JSON |
| `POST` | `/api/chat` | Mensagem ao NEXUS-7 (com histórico) | JSON |
| `GET` | `/api/chat/historico` | Todos os turnos do chat | JSON |
| `GET` | `/api/estatisticas` | Estatísticas descritivas de todos os ciclos | JSON |

> ⚠️ Nenhum endpoint tem autenticação ou rate limiting (aceitável para demo acadêmica).
> ✅ `/api/telemetria/novo` agora é `POST` apenas (TASK-002); numeração via `MAX(ciclo)+1` (TASK-001).

---

## Frontend — `templates/index.html`

Único ficheiro de template (~928 linhas). Combina SSR (Jinja2) com comportamento dinâmico (JavaScript vanilla). Tema "console de missão" sóbrio (índigo/slate, Sora + JetBrains Mono).

### Estrutura de blocos HTML

```
<head>          Tailwind CDN · Chart.js CDN · Marked.js CDN · Google Fonts · <style>
<body>
  #banner-evacuacao   Fixed top — aparece se último ciclo tem alerta
  <header>            Sticky — logo + missão/equipe + HUD de vitais (status, balanço)
  <nav>               Sticky — 9 links + scroll-spy
  <main>
    #section-comando      Gerador de missão (perfil/seed/evento) + auto + manual
    #section-resumo       6 cards: classificação+justificativa, tendência, módulo, risco médio, críticos, balanço
    #section-diagnostico  Cards por variável (status/faixa/impacto/recomendação) [GS2]
    #section-medias       5 cards de médias (id de navegação)
    #section-grafico      5 gráficos: telemetria, risco, área, energia, potência
    #section-energetico   Indicadores + gráficos SERS + recomendação
    #section-timeline     Cards clicáveis + modal + filtros + "ver todos" [GS2]
    #section-stats        Tabela de estatísticas descritivas
    #chat-section         Chat NEXUS-7
  <footer>
  #modal-ciclo        Modal de detalhe do ciclo (overlay) [GS2]
  #copilot-popup      Widget flutuante NEXUS-7 (fixed bottom-right)
<script>        JavaScript vanilla (sincronizar() centraliza redraw + fetch)
```

### Blocos JavaScript

| Bloco | Responsabilidade |
|-------|-----------------|
| `DATA` | `CICLOS_DATA` (Jinja2 → JS via `tojson`), `NOME_IA` |
| `CHART` | Inicializa Chart.js com 3 datasets e 2 eixos Y |
| `HELPERS` | `escHtml`, `syncSlider`, `corBorda`, `badgeRisco`, `corPonto`, `criarCardHTML` |
| `ADICIONAR CICLO` | Atualiza chart + prepend card + banner + copiloto + toast |
| `STATUS HELPER` | `setStatus`, `clearStatus` para feedback NEXUS-7 |
| `PAINEL DE COMANDO` | `simularCiclo()`, `injetarManual()` |
| `TOAST` | `mostrarToast(msg, type)` — 3 tipos: error/warning/success |
| `CHAT` | `addChatMsg`, `enviarChat`, listener Enter |
| `COPILOTO` | `gerarSugestao`, `atualizarSugestaoCopiloto`, `toggleCopiloto`, `enviarSugestaoParaChat` |
| `ESTATÍSTICAS` | `carregarEstatisticas()` — fetch + render tabela |
| `SCROLL-SPY` | `IntersectionObserver` — ativa link nav da secção visível |
| `INIT` | IIFE async — carrega histórico chat + init copiloto + carrega estatísticas |

---

## Stack de Produção (Railway)

```
GitHub push
    └─ Railway detecta Procfile
    └─ pip install -r requirements.txt
    └─ gunicorn app:app
    └─ PORT injetado via variável de ambiente
    └─ GROQ_API_KEY + DATABASE_URL (plugin PostgreSQL) configuradas no painel Railway
```

> ✅ **Persistência resolvida (GS2)**: em produção usa-se PostgreSQL via `DATABASE_URL` (plugin Railway), eliminando a efemeridade do SQLite. Ver `docs/DEPLOY.md`.

---

## Dependências Externas (CDN)

| Biblioteca | Versão | Propósito |
|-----------|--------|-----------|
| Tailwind CSS | latest (CDN) | Estilização |
| Chart.js | 4.4.0 | 5 gráficos (telemetria, risco, área, energia, potência) |
| Marked.js | 9.1.6 | Renderização Markdown no chat |
| Google Fonts (Sora + JetBrains Mono) | — | Tipografia (UI + dados) |

> ⚠️ Todas via CDN — sem self-hosting, sem SRI (Subresource Integrity).
