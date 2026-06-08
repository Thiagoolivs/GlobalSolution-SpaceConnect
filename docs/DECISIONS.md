# DECISIONS.md — Mission Control AI

> Registo de decisões técnicas tomadas durante o desenvolvimento, com contexto e trade-offs.

---

## ADR-001 — Flask como framework backend

**Decisão:** Usar Flask em vez de Django ou FastAPI.

**Contexto:** Projeto acadêmico de prazo curto, equipe familiarizada com Flask, sem necessidade de ORM avançado ou framework assíncrono.

**Motivo:** Flask é mínimo, fácil de aprender e suficiente para um monolito pequeno com SSR + JSON API. O ecossistema `flask-sqlalchemy` resolve o ORM sem boilerplate excessivo.

**Trade-offs:**
- ✅ Setup rápido, curva de aprendizado baixa
- ✅ Flask-SQLAlchemy integrado
- ❌ Sem suporte nativo a async (endpoints bloqueantes nas chamadas Groq)
- ❌ Sem validação de dados automática (FastAPI teria Pydantic)

---

## ADR-002 — Application Factory Pattern (`create_app`)

**Decisão:** Usar factory function em vez de instanciar `app = Flask(__name__)` no nível do módulo.

**Contexto:** A separação `src/__init__.py` + `app.py` permite importar o pacote sem criar a app (útil para testes e Gunicorn).

**Motivo:** Gunicorn precisa de `app:app` onde o segundo `app` é a instância. A factory é chamada uma vez em `app.py`, Gunicorn acessa a variável `app` exportada.

**Trade-offs:**
- ✅ Separação clara entre configuração e inicialização
- ✅ Testável sem efeitos colaterais
- ❌ Ligeiramente mais verboso para projetos muito pequenos

---

## ADR-003 — SQLite como banco de dados

**Decisão:** Usar SQLite em vez de PostgreSQL ou MySQL.

**Contexto:** Projeto acadêmico, zero configuração de servidor, funciona localmente e no Railway (com limitação de efemeridade).

**Motivo:** SQLite não requer nenhum serviço externo. `db.create_all()` cria as tabelas automaticamente na primeira execução.

**Trade-offs:**
- ✅ Zero configuração
- ✅ Funciona em qualquer ambiente
- ❌ Não persiste no Railway (storage efémero)
- ❌ Sem suporte a múltiplos writers concorrentes
- ❌ Sem migrations formais (Alembic não está configurado)

**Nota futura:** Para produção real, migrar para PostgreSQL via `DATABASE_URL` no Railway.

---

## ADR-004 — Groq API (Llama 3.1-8b-instant) em vez de OpenAI

**Decisão:** Usar Groq com modelo Llama 3.1-8b-instant.

**Contexto:** O brief acadêmico sugeria Llama via Ollama local ou qualquer API. Groq oferece Llama 3.1 via API com latência muito baixa e tier gratuito generoso.

**Motivo:** Groq tem latência de inferência ~10x menor que OpenAI para modelos equivalentes. O tier gratuito suporta desenvolvimento sem custo.

**Trade-offs:**
- ✅ Latência muito baixa (~0.5–1.5s por chamada)
- ✅ Gratuito para volumes acadêmicos
- ✅ Modelo open-source (Llama 3.1)
- ❌ Dependência de serviço externo (falha de rede = fallback de texto hardcoded)
- ❌ `max_tokens=60` nas recomendações de ciclo pode truncar respostas longas

---

## ADR-005 — Template único Jinja2 (não SPA separada)

**Decisão:** Uma única `index.html` com SSR + JavaScript inline em vez de React/Vue ou Flask + API pura.

**Contexto:** Prazo curto, sem build step, equipe sem experiência em frameworks JS modernos.

**Motivo:** Jinja2 renderiza o estado inicial completo (sem flash de conteúdo, bom SEO). JavaScript adiciona interatividade incremental sem recarregar a página.

**Trade-offs:**
- ✅ Sem build step (npm, webpack, etc.)
- ✅ Estado inicial renderizado no servidor (sem loading state)
- ✅ Funciona mesmo sem JavaScript para a leitura estática
- ❌ Arquivo HTML cresceu para ~720 linhas (difícil manutenção)
- ❌ Médias e cards de resumo não se atualizam dinamicamente com novos ciclos
- ❌ Duplicação de lógica: `gerar_sugestao_copiloto` (Python) ≈ `gerarSugestao` (JS)

---

## ADR-006 — Tailwind CSS via CDN (sem build)

**Decisão:** Usar o script CDN do Tailwind em vez de instalar via npm e fazer purge.

**Contexto:** Sem pipeline de build configurado. CDN suficiente para prototipagem acadêmica.

**Motivo:** Zero configuração. O script CDN carrega todo o Tailwind + JIT runtime no browser.

**Trade-offs:**
- ✅ Sem npm, sem build
- ✅ Funciona imediatamente
- ❌ ~300KB de CSS carregado (vs. ~5KB com purge)
- ❌ Sem Subresource Integrity (SRI) — risco de supply chain
- ❌ Não funciona offline

---

## ADR-007 — Persistência do histórico de chat no banco de dados

**Decisão:** Armazenar cada mensagem do chat na tabela `MensagemChat` e carregar o histórico completo a cada nova mensagem enviada ao Groq.

**Contexto:** O brief exigia "chat com memória". A abordagem mais simples é persistir tudo no banco e reconstruir o contexto a cada chamada.

**Motivo:** O Groq não tem estado entre chamadas — o contexto precisa ser enviado completo em cada requisição.

**Trade-offs:**
- ✅ Memória real e persistente entre sessões
- ✅ Implementação simples
- ❌ Crescimento ilimitado do contexto → custo crescente de tokens e latência
- ❌ Sem truncamento ou sumarização de histórico longo
- ❌ Sem separação de sessões por usuário (histórico global único)

---

## ADR-008 — Detecção de evacuação por regra AND combinada

**Decisão:** `alerta_evacuacao = temperatura > 35 AND bateria_solar < 30`

**Contexto:** O brief pedia uma regra de negócio que detectasse "Risco de Evacuação Iminente" a partir de combinação de variáveis críticas.

**Motivo:** A combinação alta temperatura + bateria baixa representa um cenário de dupla falha onde a capacidade de resfriamento é perdida simultaneamente com a energia de backup.

**Trade-offs:**
- ✅ Regra clara, explícita e testável
- ❌ Thresholds arbitrários (35°C e 30%) sem base em dados reais
- ❌ Não considera outras variáveis (O₂, comunicação, matriz) na decisão

---

## ADR-009 — Banner de evacuação reflete apenas o estado do ciclo mais recente

**Decisão:** `alerta_evacuacao_global = ciclos_db[-1].alerta_evacuacao` (não `any(...)`)

**Contexto:** Versão anterior mostrava o banner permanentemente se qualquer ciclo histórico havia acionado o alerta, mesmo após recuperação.

**Motivo:** Um dashboard operacional deve refletir o estado *atual* da missão, não eventos passados. A recuperação num ciclo posterior deve suprimir o alerta.

**Trade-offs:**
- ✅ Estado do banner é dinâmico e reflexo da situação atual
- ✅ Banner desaparece quando a missão se recupera
- ❌ Eventos críticos passados não ficam visivelmente marcados no header (apenas na timeline)

---

## ADR-010 — Notificações toast condicionais por nível de risco

**Decisão:** Toast apenas para `risco ≥ 5` (warning) ou `risco ≥ 8` ou `alerta_evacuacao` (error). Ciclos nominais não geram toast.

**Contexto:** Versão anterior mostrava toast em TODOS os ciclos adicionados, causando ruído.

**Motivo:** Notificações devem ser acionáveis e significativas. O feedback de sucesso da simulação já está no status do botão (`NEXUS-7 gerou os dados para o Ciclo X`).

---

## ADR-011 — Numeração de ciclos via `COUNT(*) + 1`

**Decisão:** `proximo = CicloTelemetria.query.count() + 1`

**Contexto:** Necessidade de atribuir um número sequencial ao próximo ciclo.

**Motivo:** Simples e sem dependência de `AUTOINCREMENT` do SQLite.

**Trade-offs:**
- ❌ **Dívida técnica**: Se qualquer ciclo for deletado, a numeração fica inconsistente
- ❌ Race condition em ambiente multi-thread (Gunicorn multi-worker)
- **Solução correta:** `SELECT MAX(ciclo) + 1 FROM ciclo_telemetria`

---

## ADR-012 — Groq client instanciado a nível de módulo

**Decisão:** `groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))` no topo de `services.py`.

**Contexto:** Instanciação única para reutilização de conexão HTTP.

**Trade-offs:**
- ✅ Reutiliza pool de conexões HTTP
- ❌ Se `GROQ_API_KEY` não estiver definida no momento do import, o cliente é criado com `api_key=None` e falha na primeira chamada (erro obscuro)
- ❌ Dificulta testes unitários (mock global)

---

## ADR-013 — Estatísticas calculadas em Python puro (sem NumPy/Pandas)

**Decisão:** Implementar média, mediana, variância, desvio padrão, quartis com Python stdlib.

**Contexto:** O brief de Modelagem Linear exigia análise estatística descritiva. Evitou-se adicionar NumPy/Pandas ao requirements.txt.

**Motivo:** Reduz peso das dependências e complexidade do ambiente.

**Trade-offs:**
- ✅ Sem dependências pesadas adicionais
- ❌ Implementação manual de quartis usa índice simples (`n//4`) — não é o método padrão de quartis interpolados (Pandas usa interpolação linear por padrão)
- ❌ Variância calculada como variância *populacional* (÷N), não amostral (÷N-1)

---

## ADR-014 — Gerador de missão parametrizável (perfis + seed)

**Decisão:** `gerar_dados_missao(n_ciclos, perfil, seed=None)` em `services.py`, com perfis `estavel | degradacao | recuperacao | caotica`.

**Contexto:** O gerador antigo (`gerar_telemetria_simulada`) produzia 1 ciclo de ruído branco puro. A Fase 1 (PCP) pedia cenários controláveis e reprodutíveis.

**Motivo:** Cada perfil define uma trajetória de "saúde" `h ∈ [0,1]` por ciclo; os 5 parâmetros são interpolados entre valor crítico e nominal segundo `h`. `seed` via `random.Random(seed)` isolado garante reprodutibilidade sem afetar o RNG global.

**Trade-offs:**
- ✅ Cenários distintos, reprodutíveis e clampados (6–20 ciclos)
- ✅ Aditivo: `DADOS_INICIAIS` e `gerar_telemetria_simulada` mantidos (fallback PCP)
- ❌ Thresholds dos perfis são empíricos

---

## ADR-015 — Realismo: ruído AR(1) + acoplamento físico + eventos

**Decisão:** Ruído autocorrelacionado (momentum 0.65), acoplamento térmico (calor derruba matriz/bateria, eleva O₂) e eventos pontuais injetáveis (`eventos=[{ciclo,tipo}]`).

**Motivo:** Variação suave (sem saltos brancos), correlação entre variáveis e eventos discretos (pico térmico, falha de comms etc.) tornam a simulação fisicamente plausível e didática.

**Trade-offs:**
- ✅ Curvas suaves e correlacionadas (temp×matriz ≈ −0.99 nos testes)
- ✅ Eventos transitórios afetam só o ciclo-alvo e cascateiam via acoplamento
- ❌ Coeficientes de acoplamento são calibrados à mão

---

## ADR-016 — Geração em lote sem IA por ciclo + 1 narrativa única

**Decisão:** `POST /api/simulacao/gerar` persiste N ciclos com `processar_linha_sem_ia` (rule-based, sem Groq) e faz **uma única** chamada `gerar_narrativa_missao` ao final.

**Motivo:** Chamar o Groq por ciclo (até 20) seria lento e caro. O insight por ciclo passa a ser rule-based; a IA entra uma vez, com visão da missão inteira.

**Trade-offs:**
- ✅ Lote rápido; 1 chamada de IA; fallback de contingência testado
- ✅ `_salvar_ciclo(..., com_ia=False)` mantém o ponto único de persistência
- ❌ Insight por ciclo no lote é menos "inteligente" que o do ciclo único

---

## ADR-017 — Dashboards e energia no frontend sem novo framework

**Decisão:** As Fases 4/5/6 (resumo dinâmico, 5 gráficos Chart.js, painel energético, controles) foram implementadas no `index.html` existente + endpoints `GET /api/energetico` e `GET /api/alertas`.

**Motivo:** O `CLAUDE.md` proíbe build step / framework JS / novo template. Tudo foi feito com Chart.js + JS vanilla, mantendo SSR + progressive enhancement.

**Trade-offs:**
- ✅ Sem build; respeita as restrições do projeto
- ✅ `sincronizar()` centraliza redraw + fetch (1 fonte de verdade: `CICLOS_DATA`)
- ❌ Tags e médias recalculadas no cliente (duplicam thresholds do backend)

---

## ADR-018 — Identidade visual: de HUD neon para console sóbrio

**Decisão:** Reformulação visual em duas etapas — primeiro um "Mission Control HUD" (ciano/âmbar, Space Mono/Orbitron, grid+scanline), depois ajustado para um esquema **mais calmo**: acento índigo único, neutros slate, status só semântico, fontes **Sora + JetBrains Mono**, sem grid/scanline/colchetes e com mais espaçamento.

**Motivo:** O HUD inicial ficou denso/"ruidoso". O pedido foi por respiro e organização, mantendo o caráter espacial.

**Trade-offs:**
- ✅ Hierarquia clara, menos poluição, leitura mais fácil
- ✅ Lógica JS intacta (apenas estilo/markup/cores mudaram)
- ❌ Menos "chamativo" que o HUD neon

---

## ADR-019 — `mission_control.py` standalone (PCP) separado da app web (PIA)

**Decisão:** Criar `mission_control.py` na raiz: análise rule-based em **Python puro stdlib** (sem Flask/Groq/deps), com relatório de terminal.

**Contexto:** O `REVIEW_CHECKLIST.md` (PCP) espera um script mínimo executável e SEM IA; a app web cobre PIA (com Groq).

**Trade-offs:**
- ✅ Atende o entregável PCP de forma autônoma e portável
- ✅ Inclui seção energética (SERS) no relatório
- ❌ Duplica os thresholds de `services.py` (intencional, para independência)

---

## ADR-020 — Numeração de ciclos via `MAX(ciclo)+1` (revoga ADR-011)

**Decisão:** `_proximo_ciclo()` usa `SELECT MAX(ciclo)+1`, substituindo o `COUNT(*)+1` da ADR-011 em todas as rotas (fecha TASK-001).

**Motivo:** `COUNT+1` quebra com deleções e é frágil em multi-worker. Necessário também para a geração em lote numerar corretamente.

**Trade-offs:**
- ✅ Correto sob deleções e concorrência
- ✅ Lote contínuo (`proximo + i`)
- ❌ Uma query de agregação por inserção (custo desprezível no SQLite)

---

## ADR-021 — IA sem `max_tokens` (tamanho via system prompt)

**Decisão:** Remover `max_tokens` das 3 chamadas Groq; controlar o tamanho apenas pelo *system prompt*.

**Contexto:** Respostas do chat/insights vinham cortadas por causa do teto de tokens (`200`/`60`/`140`).

**Trade-offs:**
- ✅ Resposta exibida = resposta da IA, completa; salva inteira (coluna `Text`)
- ❌ Respostas podem ficar longas → recomendável janela de contexto no chat (TASK-009)

---

## ADR-022 — Banco por `DATABASE_URL` (SQLite ⇄ PostgreSQL)

**Decisão:** `_database_uri()` resolve o banco por env var; default SQLite local; em produção `DATABASE_URL` (Postgres), normalizando `postgres://` → `postgresql://`.

**Motivo:** SQLite é efémero no Railway. Trocar de ambiente sem alterar código.

**Trade-offs:**
- ✅ Mesma base de código em dev e produção; persistência real com Postgres
- ❌ Requer `psycopg2-binary` e um plugin de banco no Railway

---

## ADR-023 — Classificação persistida + migração idempotente (sem Alembic)

**Decisão:** Adicionar coluna `classificacao` e migrar via `_migrate()` (`ALTER TABLE ADD COLUMN` guardado por *inspector* + backfill), em vez de adotar Alembic.

**Motivo:** Manter zero-config e **preservar o `missao.db`** existente; mudança de schema mínima.

**Trade-offs:**
- ✅ Não quebra bancos existentes; funciona em SQLite e Postgres
- ❌ Solução ad-hoc (uma coluna); para múltiplas migrações futuras, Alembic seria melhor

---

## ADR-024 — Relatório fiel ao formato, com dados reais do sistema

**Decisão:** `gerar_relatorio_txt()` segue o **formato/estrutura** do modelo GS2, porém com os **dados e thresholds reais** do sistema.

**Contexto:** No modelo enviado, o O₂ aparecia como `%` e alguns ciclos usavam thresholds mais brandos. O sistema modela O₂ como **consumo em L/min** e usa os limites do `CLAUDE.md`.

**Trade-offs:**
- ✅ Relatório consistente com o dashboard e com a regra de negócio documentada
- ❌ Os números podem diferir do exemplo ilustrativo (esperado)

---

## ADR-025 — Diagnóstico e eventos: backend + recomputação no cliente

**Decisão:** Diagnóstico por variável e tipo de evento por ciclo vivem em `services.py` (e endpoints `/api/diagnostico`, `/api/alertas`); a timeline recomputa o tipo de evento no cliente para reatividade imediata.

**Trade-offs:**
- ✅ UI reativa sem recarregar; backend é a fonte para relatório/SSR/terminal
- ❌ Duplicação dos thresholds (Python + JS) — já assumida na ADR-017
