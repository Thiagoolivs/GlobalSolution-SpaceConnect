# PROJECT.md — Mission Control AI

> Visão geral, contexto acadêmico e descrição funcional completa do projeto.

---

## Identificação

| Campo | Valor |
|-------|-------|
| **Nome** | Mission Control AI |
| **Missão simulada** | Orion Test Alpha |
| **Equipe** | Equipe Apollo |
| **Contexto** | Global Solution 2026.1 — FIAP / Ciência da Computação |
| **Entrega** | 09/06/2026 até 23h55 |
| **Peso** | 6 pontos (Prompt & AI) |

---

## Descrição

Plataforma web de monitoramento inteligente de missão espacial experimental. O sistema integra IA generativa (Groq / Llama 3.1) com análise de telemetria em tempo real, persistência em banco de dados e interface interativa construída como SPA-like sobre um único template Jinja2.

O sistema monitora 5 variáveis operacionais em ciclos discretos, calcula pontuações de risco, emite alertas automáticos, detecta condições críticas combinadas (evacuação) e fornece recomendações técnicas via IA.

---

## Disciplinas Atendidas

| Disciplina | Requisito Central | Implementação |
|-----------|-------------------|--------------|
| **Prompt & AI / PIA** | IA generativa integrada, dashboard web, chatbot | Groq Llama 3.1, chat com memória, NEXUS-7, narrativa de missão |
| **PCP (Python)** | Matriz dados_missao, cálculo de risco, alertas | `mission_control.py` (terminal, Python puro) + `services.py` (web) |
| **SERS** | Monitoramento energético, alertas, visualização | Métricas energéticas (P=V·I, balanço, eficiência) + painel/gráficos de energia |
| **Modelagem Linear** | Estatística descritiva | Endpoint `/api/estatisticas` + tabela UI |

---

## Variáveis Monitoradas

| Índice | Campo | Unidade | Nominal | Atenção | Crítico |
|--------|-------|---------|---------|---------|---------|
| 0 | Temperatura interna | °C | ≤ 30 | 31–38 | > 38 |
| 1 | Comunicação com a base | % | ≥ 70 | 40–69 | < 40 |
| 2 | Sistema de energia (bateria solar) | % | ≥ 60 | 25–59 | < 25 |
| 3 | Suporte de oxigênio (consumo O₂) | L/min | ≤ 9 | 9.1–11 | > 11 |
| 4 | Estabilidade operacional (matriz) | % | ≥ 80 | 50–79 | < 50 |

---

## Dados Iniciais (Seed)

Carregados automaticamente na primeira execução caso o banco esteja vazio:

| Ciclo | Temp | Sinal | Bateria | O₂ | Matriz | Cenário |
|-------|------|-------|---------|-----|--------|---------|
| 1 | 24 | 92 | 88 | 8.2 | 90 | Nominal |
| 2 | 27 | 80 | 72 | 8.8 | 85 | Nominal leve |
| 3 | 31 | 65 | 58 | 9.5 | 70 | Alerta moderado |
| 4 | 36 | 42 | 38 | 10.8 | 55 | Degradação severa |
| 5 | 39 | 28 | 19 | 11.5 | 35 | **Crítico / Evacuação** |
| 6 | 29 | 75 | 65 | 8.5 | 82 | Recuperação |

---

## Fluxo Principal de Uso

```
Usuário acessa /
  └─ _seed_inicial() → popula DB se vazio
  └─ _consolidado() → calcula médias, tendência, área mais afetada
  └─ render_template() → SSR completo com Jinja2

Usuário clica "Simular Ciclo"
  └─ POST /api/telemetria/novo
  └─ gerar_telemetria_simulada() → valores aleatórios
  └─ processar_linha() → análise + IA (Groq)
  └─ salva no SQLite
  └─ retorna JSON → JS atualiza gráfico + timeline

Usuário digita no chat
  └─ POST /api/chat
  └─ carrega histórico completo do SQLite
  └─ envia para Groq com contexto completo
  └─ salva pergunta + resposta no SQLite
  └─ retorna JSON → marked.js renderiza Markdown

Usuário clica "Gerar Simulação" (Fase 6)
  └─ POST /api/simulacao/gerar {n_ciclos, perfil, seed, eventos}
  └─ gerar_dados_missao() → matriz parametrizável (perfil + seed)
  └─ persiste em lote (rule-based, sem IA por ciclo)
  └─ gerar_narrativa_missao() → 1 análise da IA da missão inteira
  └─ retorna ciclos + energético + alertas + classificações + narrativa
```

---

## Fluxo Alternativo — Modo Terminal (PCP)

```
python mission_control.py        # Python puro, sem Flask/Groq/dependências
  └─ percorre dados_missao (6 ciclos)
  └─ analisa 5 parâmetros por ciclo (classificação, mensagem, pontos)
  └─ calcula métricas energéticas (SERS) por ciclo
  └─ imprime relatório final: médias, tendência, área mais afetada,
     balanço energético e conclusão narrativa rule-based
```

---

## Entregáveis Acadêmicos

- [ ] Repositório GitHub público com este README
- [ ] Vídeo não listado no YouTube (máx. 3 min)
- [ ] Arquivo `.txt` com nomes, RM, links GitHub e YouTube
