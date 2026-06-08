# CHANGELOG GS2 — Mission Control AI

> Relatório detalhado da rodada de melhorias "GS 2". Inclui alterações,
> arquivos modificados, decisões, impactos na arquitetura e sugestões para a GS final.

---

## 1. Alterações realizadas (por etapa)

### Etapa 1 — Backend base / infraestrutura
- **IA sem truncamento:** removidos os 3 `max_tokens` (`obter_insight_ia`, `obter_resposta_chat`, `gerar_narrativa_missao`). O tamanho passa a ser guiado apenas pelo *system prompt*. A resposta exibida é exatamente a retornada pela IA e é salva inteira (coluna `Text`, sem corte no front).
- **Banco por ambiente:** `_database_uri()` lê `DATABASE_URL` (default SQLite local), normalizando `postgres://` → `postgresql://`. Troca SQLite↔PostgreSQL **somente por env var**.
- **Deploy Railway:** `psycopg2-binary` adicionado, `.python-version` (3.11), `.env.example`, e `docs/DEPLOY.md` com guia + checklist + troubleshooting.
- **.gitignore:** reescrito por categorias e comentado (inclui `.claude/`, logs, temporários, `*.db`, `venv/`, IDEs).

### Etapa 2 — PCP: pontuação + classificação persistida
- Coluna **`classificacao`** em `CicloTelemetria` + **migração idempotente** (`_migrate()`: `ALTER TABLE ADD COLUMN` se faltar + backfill), preservando o `missao.db` existente.
- Bandas **0 → MISSÃO ESTÁVEL · 1–5 → MISSÃO EM ATENÇÃO · 6+ → MISSÃO CRÍTICA** (`classificar_missao`).
- **Justificativa** da classificação (`justificar_classificacao`) exposta na UI e no modal.

### Etapa 3 — Leitura inteligente dos ciclos
- `tipo_evento_serie()` classifica cada ciclo em **Estável / Atenção / Crítico / Recuperação / Outlier / Correlacionado** (prioridade: correlacionado → outlier → recuperação → crítico → atenção → estável). Alimenta timeline, filtros e relatório.

### Etapa 4 — Diagnóstico operacional (Energia visual)
- `diagnostico_variaveis()` retorna, por variável: **valor, status, faixa ideal, impacto e recomendação**. Nova seção "Diagnóstico Operacional" com cards coloridos por status (NORMAL/ATENÇÃO/CRÍTICO).

### Etapa 5 — Timeline inteligente
- Timeline reconstruída em **cards clicáveis** (ciclo, pontuação, classificação, nº de anomalias, tipo de evento).
- **Modal** de detalhe por ciclo (5 variáveis com status/mensagem, justificativa, recomendação NEXUS-7).
- Por padrão exibe **apenas ciclos relevantes** + botão **"Ver todos os ciclos"**.
- **Filtros** rápidos por tipo (Todos/Estáveis/Atenção/Críticos/Recuperação/Outliers/Correlacionados) sem refresh.

### Etapa 6 — Relatório TXT + conclusão dinâmica
- `gerar_relatorio_txt()` produz o `.txt` **fiel ao modelo GS2** (cabeçalho, blocos por ciclo `Variável: valor | STATUS | mensagem`, pontuação/classificação/recomendação, relatório final com médias/tendência/área mais afetada e legenda).
- **Conclusão dinâmica** (`gerar_conclusao_missao`) construída a partir de tendência, recuperação/degradação, ciclos críticos e área mais exigida.
- Endpoint `GET /api/relatorio` (download `text/plain`).

### Etapa 7 — Interface
- Hierarquia mais clara (sumário com classificação + justificativa, HUD com STATUS), contexto nas métricas (diagnóstico), alertas intuitivos (tipos/cores) e menos ruído.

### Etapa 2C — Versão terminal (PCP)
- `mission_control.py` alinhado: mesmas bandas/rótulos, mesmas mensagens curtas, recomendação por ciclo e conclusão dinâmica, no formato do modelo + seção SERS.

---

## 2. Arquivos modificados / criados

| Arquivo | Mudança |
|---------|---------|
| `src/services.py` | −3 `max_tokens`; + classificação, diagnóstico, eventos, conclusão e relatório TXT |
| `src/__init__.py` | `_database_uri()` (DB por env) + `_migrate()` idempotente |
| `src/models.py` | coluna `classificacao` |
| `src/routes.py` | persiste classificação; `_fmt_ciclo` enriquecido; endpoints `/api/diagnostico`, `/api/relatorio`; `/api/alertas` com tipo de evento |
| `templates/index.html` | Diagnóstico Operacional; timeline clicável + modal + filtros; export server-side; HUD/labels |
| `mission_control.py` | bandas/rótulos/mensagens/conclusão alinhados ao modelo |
| `requirements.txt` | `+ psycopg2-binary==2.9.9` |
| `.gitignore` | reescrito por categorias |
| `.env.example`, `.python-version`, `docs/DEPLOY.md` | **novos** (deploy) |
| `README.md`, `docs/*` | atualizados |

---

## 3. Decisões tomadas
- **IA sem `max_tokens`** — tamanho via prompt (ver ADR-021).
- **DB por `DATABASE_URL`** com normalização Postgres (ADR-022).
- **Classificação persistida + migração idempotente** em vez de Alembic, para não quebrar o `missao.db` (ADR-023).
- **Relatório fiel ao formato, com dados reais** — O₂ permanece em **L/min** (não % como no exemplo) e os scores seguem os thresholds do `CLAUDE.md`; portanto os números podem diferir do exemplo ilustrativo (ADR-024).
- **Diagnóstico e timeline** servidos por endpoints; timeline recalculada no cliente para reatividade (ADR-025).

---

## 4. Impactos na arquitetura
- **Schema** evoluiu (+1 coluna) com caminho de migração seguro; compatível com SQLite e PostgreSQL.
- **Camadas preservadas:** toda a lógica nova vive em `services.py` (funções puras); `routes.py` só faz I/O; `index.html` mantém SSR + *progressive enhancement*; contratos de API antigos intactos (campos adicionados, nenhum removido).
- **Produção:** app pronto para Railway com Postgres persistente (resolve a efemeridade do SQLite).
- **Custo/latência da IA:** sem `max_tokens`, respostas podem ficar maiores → ver sugestão de janela de contexto abaixo.

---

## 5. Sugestões para a GS final
1. **Janela de contexto do chat** (TASK-009): com a IA sem teto de tokens, limitar o histórico enviado (ex.: últimas 20 mensagens) evita crescimento de custo/latência.
2. **Validar `GROQ_API_KEY` no startup** (TASK-005) com mensagem clara.
3. **Suíte de testes pytest** persistente (hoje a validação é por smoke tests descartáveis) cobrindo `services.py` e os endpoints.
4. **Rate limiting** nas rotas de IA antes de expor publicamente.
5. **Confirmar com o professor** o uso de Groq/Llama 3.1 (web) vs. Ollama/notebook citado no checklist — funcionalmente equivalente, mas não literal.
6. **Prints + vídeo + nomes/RM**: preencher `assets/`, `README.md` e `ENTREGA.txt`.
