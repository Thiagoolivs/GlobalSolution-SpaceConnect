# CLAUDE.md — Mission Control AI

> Ficheiro de contexto para sessões do Claude Code.
> Leia este ficheiro **antes** de qualquer modificação no projeto.

---

## Objetivo do Sistema

Dashboard web de monitoramento inteligente de missão espacial experimental.
Contexto académico: FIAP Global Solution 2026.1.

O sistema recebe, valida e persiste ciclos de telemetria com 5 variáveis operacionais,
calcula pontuações de risco, detecta condições críticas e fornece recomendações via
IA generativa (Groq / Llama 3.1). Toda a interação acontece num único template HTML
com SSR inicial (Jinja2) + comportamento dinâmico incremental (JavaScript vanilla).

**Missão:** Orion Test Alpha | **Equipe:** Equipe Apollo | **Assistente de IA:** NEXUS-7

---

## Mapa de Ficheiros

```
app.py                  # Entry point — NÃO adicionar lógica aqui
src/
  __init__.py           # App factory + SQLAlchemy init
  models.py             # 2 modelos ORM — CicloTelemetria, MensagemChat
  routes.py             # 7 endpoints via Blueprint "main"
  services.py           # TODA a lógica de negócio e chamadas Groq
templates/
  index.html            # Template único (~720 linhas) — SSR + JS
docs/                   # Documentação técnica (não alterar via código)
requirements.txt        # Dependências pinned — atualizar ao adicionar pacotes
Procfile                # web: gunicorn app:app
.env                    # GROQ_API_KEY (nunca versionar)
```

---

## Padrões Arquiteturais

### 1. Application Factory
Sempre usar `create_app()` de `src/__init__.py`. Nunca instanciar `Flask()` fora da factory.

### 2. Separação de camadas — regra absoluta

| Camada | Ficheiro | O que FAZ | O que NUNCA faz |
|--------|----------|-----------|-----------------|
| Entry point | `app.py` | Cria app, lê PORT | Lógica, rotas, modelos |
| Rotas | `routes.py` | HTTP I/O, serialização, persistência | Lógica de negócio, chamadas Groq diretas |
| Serviços | `services.py` | Validação, cálculo, Groq | `import flask`, acesso ao banco |
| Modelos | `models.py` | Schema ORM | Lógica de negócio |

**Toda chamada ao Groq passa EXCLUSIVAMENTE por `services.py`.**
**`routes.py` nunca importa `groq` diretamente.**

### 3. SSR + Progressive Enhancement
- O carregamento inicial da página é 100% renderizado pelo servidor (Jinja2).
- JavaScript adiciona interatividade **sem** substituir o conteúdo SSR.
- Novos ciclos são `prepend`ados na timeline via JS — o SSR original permanece.
- Cards de resumo e médias são SSR-only atualmente — não reprocessar no JS sem necessidade.

### 4. Blueprint único
Todas as rotas estão no Blueprint `"main"` em `routes.py`.
Não criar Blueprints adicionais sem motivo justificado.

### 5. Funções auxiliares privadas em routes.py
Helpers de rota têm prefixo `_`: `_seed_inicial`, `_fmt_ciclo`, `_consolidado`, `_salvar_ciclo`.
Toda persistência de ciclo passa por `_salvar_ciclo(v, proximo)`.

---

## Modelo de Dados

### `CicloTelemetria`
```
id            Integer PK auto
ciclo         Integer  — número do ciclo (sequencial)
temperatura   Float    — °C interno
comunicacao   Float    — % sinal
bateria_solar Float    — % carga
consumo_o2    Float    — L/min
matriz        Float    — % estabilidade energética
risco         Integer  — score 0–10 (soma dos 5 scores individuais)
alerta_evacuacao Boolean — temp > 35 AND bat < 30
ia_insight    Text     — resposta gerada pelo Groq
timestamp     DateTime — UTC, auto
```

### `MensagemChat`
```
id        Integer PK auto
role      String(10) — "user" | "assistant"
content   Text
timestamp DateTime — UTC, auto
```

> Todo novo modelo deve ter campo `timestamp = db.Column(db.DateTime, default=datetime.utcnow)`.

---

## Regras de Negócio Críticas

### Thresholds de validação (retornam `(score: int, texto: str)`)

| Variável | score=0 (nominal) | score=1 (atenção) | score=2 (crítico) |
|----------|-------------------|-------------------|-------------------|
| Temperatura | ≤ 30°C | 31–38°C | > 38°C |
| Comunicação | ≥ 70% | 40–69% | < 40% |
| Bateria Solar | ≥ 60% | 25–59% | < 25% |
| Consumo O₂ | ≤ 9 L/min | 9.1–11 | > 11 L/min |
| Matriz | ≥ 80% | 50–79% | < 50% |

**Risco total = soma dos 5 scores (0–10).**

### Regra de Evacuação
```python
alerta_evacuacao = temperatura > 35 and bateria_solar < 30
```

### Banner de Evacuação
Reflete **apenas o estado do ciclo mais recente** — não histórico acumulado:
```python
alerta_evacuacao_global = ciclos_db[-1].alerta_evacuacao if ciclos_db else False
```

### Toast Notifications (JavaScript)
```
alerta_evacuacao  → toast error (vermelho)
risco >= 8        → toast error (vermelho)
risco >= 5        → toast warning (âmbar)
risco < 5         → NENHUM toast (silêncio — o status do botão já confirma)
```

### Numeração de Ciclos
**NUNCA** usar `CicloTelemetria.query.count() + 1` (buggy se houver deleções).
**USAR:**
```python
proximo = (db.session.query(db.func.max(CicloTelemetria.ciclo)).scalar() or 0) + 1
```
> ⚠️ O código atual ainda usa `count() + 1` — TASK-001 pendente.

### Seed Inicial
`_seed_inicial()` só insere se `count() == 0`. É chamada a cada request de `/`.
Os 6 ciclos iniciais são: nominal → nominal → atenção → degradação → **crítico/evacuação** → recuperação.

---

## Contratos de API (não quebrar)

| Endpoint | Método | Resposta JSON (campos obrigatórios) |
|----------|--------|-------------------------------------|
| `/api/telemetria/novo` | POST | `{id, ciclo, valores[5], risco, alertas[5], ia_insight, timestamp, alerta_evacuacao}` |
| `/api/telemetria/manual` | POST | idem |
| `/api/copiloto` | GET | `{sugestao, risco, ciclo, alerta_evacuacao}` |
| `/api/chat` | POST | `{resposta}` ou `{erro}` |
| `/api/chat/historico` | GET | `[{role, content}, ...]` |
| `/api/estatisticas` | GET | `{campo: {label, media, mediana, minimo, maximo, amplitude, variancia, desvio_padrao, coef_variacao, q1, q3, n}}` |

**`valores` é sempre um array de 5 floats na ordem: `[temperatura, comunicacao, bateria_solar, consumo_o2, matriz]`.**

---

## Convenções de Código

### Python
- Funções de análise devem retornar `(int, str)` — score e mensagem.
- Sem classes desnecessárias em `services.py` — funções puras.
- Helpers privados em `routes.py` prefixados com `_`.
- `request.get_json(force=True)` nas rotas POST — não `request.json`.
- Acesso ao Groq sempre com `try/except` e retorno de fallback no `except`.

### JavaScript (Frontend)
- Sem frameworks — vanilla JS apenas.
- **Todo texto dinâmico inserido via `innerHTML` deve passar por `escHtml()`.**
- Novos ciclos adicionados via `adicionarCiclo(d)` — não duplicar essa lógica.
- Status de loading via `setStatus(id, msg, tipo)` e `clearStatus(id, delay)`.
- Sincronização slider↔input via `syncSlider(srcId, dstId)`.
- Cores de risco via helpers: `corBorda(r)`, `badgeRisco(r)`, `corPonto(texto)`.
- `CICLOS_DATA` é o array JS que espelha os ciclos — sempre atualizado via `adicionarCiclo`.

### HTML / Jinja2
- Dados Python → JS via `{{ variavel | tojson }}` — nunca concatenação de strings.
- IDs de secção seguem o padrão `section-{nome}`: `section-comando`, `section-grafico`, etc.
- Toda secção navegável deve ter `id` e `scroll-margin-top` via CSS.
- Classes condicionais Jinja2: `{{ 'classe-a' if condicao else 'classe-b' }}`.

### Nomes
- Assistente de IA: **NEXUS-7** (Neural EXecution & Understanding System)
- Referências no código e UI devem usar este nome consistentemente.

---

## Tecnologias Obrigatórias

| Tecnologia | Versão | Onde |
|-----------|--------|------|
| Python | 3.11+ | Runtime |
| Flask | 3.1.3 | Backend |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| SQLAlchemy | 2.0.50 | ORM core |
| Groq SDK | 1.4.0 | Cliente AI |
| Llama 3.1-8b-instant | — | Modelo Groq (insights + chat) |
| Gunicorn | 21.2.0 | Servidor produção |
| python-dotenv | 1.2.2 | Variáveis de ambiente |
| Tailwind CSS | CDN latest | Estilização |
| Chart.js | **4.4.0** (CDN) | Gráficos |
| Marked.js | **9.1.6** (CDN) | Markdown no chat |
| Google Fonts Inter | CDN | Tipografia |

**Não alterar versões sem avaliar breaking changes.**
**Qualquer nova dependência Python deve ser adicionada ao `requirements.txt` com versão pinned.**

---

## Restrições Técnicas

```
❌ Proibido: npm, webpack, Vite, build pipeline de qualquer tipo
❌ Proibido: React, Vue, Angular, Svelte ou qualquer framework JS
❌ Proibido: autoimportar groq em routes.py (apenas em services.py)
❌ Proibido: criar novos ficheiros de template (usar index.html existente)
❌ Proibido: variáveis de ambiente hardcoded no código-fonte
❌ Proibido: alterar o schema do banco sem considerar migração dos dados existentes
❌ Proibido: quebrar contratos de API existentes (campos obrigatórios de resposta)
❌ Proibido: instanciar Flask() fora de create_app()
❌ Proibido: adicionar lógica de negócio em routes.py diretamente
❌ Proibido: acesso direto ao banco em services.py
❌ Proibido: versionar .env ou missao.db
```

---

## Práticas que Nunca Devem Ser Violadas

### 1. `escHtml()` é obrigatório em todo innerHTML dinâmico
Qualquer string proveniente de dados externos (ia_insight, alertas, timestamps) inserida
via `innerHTML` em JS **deve** ser sanitizada com `escHtml()`. Sem exceções.

### 2. Toda chamada Groq tem fallback
```python
try:
    # chamada Groq
except Exception as e:
    return f"Modo de Contingência: ... Erro: {str(e)}"
```
O sistema não pode quebrar por falha da API externa.

### 3. O banner de evacuação reflete o estado atual, nunca o histórico
Usar sempre `ciclos_db[-1].alerta_evacuacao` — não `any(c.alerta_evacuacao for c in ciclos_db)`.

### 4. `_salvar_ciclo()` é o único ponto de persistência de CicloTelemetria
Nunca fazer `db.session.add(CicloTelemetria(...))` diretamente nas rotas.
Toda criação de ciclo passa por `_salvar_ciclo(valores, proximo_ciclo)`.

### 5. Jinja2 → JS sempre via `tojson`
```html
<!-- CORRETO -->
const DATA = {{ variavel | tojson }};

<!-- PROIBIDO -->
const DATA = "{{ variavel }}";  // quebra com aspas e caracteres especiais
```

### 6. Toast nunca para ciclos nominais
`mostrarToast()` só é chamada para `risco >= 5` ou `alerta_evacuacao`.
Ciclos de risco 0–4 confirmam resultado apenas no status do botão.

### 7. Novos endpoints seguem a convenção de resposta
Todo endpoint de telemetria retorna o objeto completo com os 8 campos do contrato de API.
Nunca retornar um subconjunto que quebre o `adicionarCiclo(d)` no frontend.

### 8. `CICLOS_DATA` no frontend é a única fonte de verdade do estado JS
Ao adicionar ciclos, sempre dar `CICLOS_DATA.push(d)` antes de atualizar chart e timeline.
Lógicas que dependem de "quantos ciclos existem" usam `CICLOS_DATA.length`.

### 9. Respeitar o scroll-margin-top de 6.5rem em novas secções
Qualquer nova `<section id="...">` que seja linkada pela navbar precisa de
`scroll-margin-top: 6.5rem` (já definido no CSS global `section[id]`).

### 10. Não alterar os dados seed sem atualizar os docs
Os 6 ciclos em `DADOS_INICIAIS` (`routes.py`) estão documentados em `docs/PROJECT.md`.
Qualquer mudança deve ser refletida na documentação.

---

## Checklist antes de qualquer modificação

- [ ] A camada correta está sendo alterada? (negócio → services, HTTP → routes)
- [ ] Novos textos em `innerHTML` usam `escHtml()`?
- [ ] Novos endpoints retornam todos os campos do contrato de API?
- [ ] Novos modelos têm `timestamp`?
- [ ] Novas dependências Python estão no `requirements.txt`?
- [ ] O banner de evacuação ainda usa apenas o último ciclo?
- [ ] Chamadas Groq têm `try/except` com fallback?
- [ ] `CLAUDE.md` ou `docs/` precisam ser atualizados?
