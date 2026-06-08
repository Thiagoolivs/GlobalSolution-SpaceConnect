# MELHORIAS — MISSION CONTROL AI

Trabalhar nesta ordem. Não pular fases.

---

## STATUS DE EXECUÇÃO (atualizado)

| Fase | Descrição | Status |
|------|-----------|--------|
| 1.1 | Gerador parametrizável (`gerar_dados_missao`, perfis, seed) | ✅ feito + testado |
| 1.2 | Realismo (ruído AR(1), correlação, eventos pontuais) | ✅ feito + testado |
| 2 | Alertas expandidos + classificação de ciclos (tags) | ✅ feito + testado |
| 3 | Seção energética / SERS (P=V·I, balanço, eficiência) | ✅ feito + testado |
| 4 | Resumo em tempo real (cards/médias dinâmicos) | ✅ feito (frontend) |
| 5 | Dashboards (5 gráficos) + painel energético | ✅ feito (frontend) |
| 6 | Interatividade (gerar simulação, seed, eventos, narrativa, filtro, export) | ✅ feito (frontend) |
| 7.1 | `mission_control.py` standalone (terminal, Python puro) | ✅ feito + testado |
| 7.* | Checklist final, README com prints, vídeo | ⏳ pendente (precisa de dados da equipe) |

**Adaptações ao stack real (Flask + Groq, ver ADR-016/017/019):** IA permanece Groq (não Ollama); dashboards em Chart.js + JS vanilla (não Streamlit/Dash); a versão "terminal puro" é o `mission_control.py`.

**Bônus fechados:** TASK-001 (numeração MAX+1), TASK-002 (GET removido), TASK-008 (médias/cards dinâmicos), TASK-017 (seção médias com id na navbar).

---

## FASE 1 — Núcleo de simulação (PCP compliance)

### 1.1 Gerador de simulação parametrizável
- [ ] Função `gerar_dados_missao(n_ciclos, perfil, seed=None)`
- [ ] Parâmetros configuráveis pelo usuário:
  - quantidade de ciclos (mín 6, máx 20)
  - perfil da missão: "estável" | "degradação" | "recuperação" | "caótica"
  - seed opcional para reprodutibilidade
- [ ] Cada perfil gera curvas diferentes nos 5 parâmetros
- [ ] Manter compatibilidade com matriz fixa `dados_missao` para fallback PCP

### 1.2 Ciclos mais realistas
- [ ] Variação suave entre ciclos (não saltos aleatórios puros)
- [ ] Correlação entre parâmetros (ex.: temperatura alta tende a derrubar estabilidade)
- [ ] Eventos pontuais injetáveis (falha de comunicação, pico térmico)

---

## FASE 2 — Sistema de alertas expandido

### 2.1 Novos tipos de alerta (além de NORMAL/ATENÇÃO/CRÍTICO)
- [ ] OUTLIER — valor desvia >2σ da média da missão
- [ ] TENDÊNCIA NEGATIVA — 3 ciclos consecutivos piorando
- [ ] RECUPERAÇÃO — saída de estado crítico para atenção/normal
- [ ] CORRELACIONADO — dois ou mais parâmetros críticos no mesmo ciclo
- [ ] ANOMALIA ENERGÉTICA — consumo fora do padrão esperado

### 2.2 Classificação de ciclos (timeline organizada)
- [ ] Categorizar cada ciclo em uma das tags:
  - "BOM" (risco 0–1)
  - "RUIM" (risco 6+)
  - "OUTLIER" (qualquer parâmetro >2σ)
  - "DESTAQUE" (recuperação, queda brusca, evento notável)
- [ ] Cada ciclo pode ter múltiplas tags

---

## FASE 3 — Seção energética (SERS compliance)

### 3.1 Cálculos físicos por ciclo
- [ ] Tensão nominal do sistema: 28V (padrão spacecraft)
- [ ] Potência consumida: P = V × I (W)
- [ ] Corrente estimada: I = P / V (A)
- [ ] Energia consumida no ciclo: E = P × t (Wh), assumir t=1h por ciclo
- [ ] Energia gerada (painel solar simulado): variável por ciclo
- [ ] Balanço energético: E_gerada − E_consumida
- [ ] Eficiência: E_útil / E_total (%)

### 3.2 Função `calcular_metricas_energeticas(ciclo)`
- [ ] Retorna dict com: potencia_W, corrente_A, energia_Wh, geracao_Wh, balanco_Wh, eficiencia_pct

### 3.3 Exibir no relatório
- [ ] Tabela energética por ciclo
- [ ] Consumo médio, pico de consumo, ciclo de menor eficiência
- [ ] Recomendação energética automatizada

---

## FASE 4 — Resumo em tempo real

- [ ] Atualizar resumo a cada ciclo processado, não só no final
- [ ] Resumo incremental contém:
  - ciclo atual / total
  - risco acumulado
  - tendência parcial
  - última recomendação
  - balanço energético acumulado

---

## FASE 5 — Dashboards e visualização

### 5.1 Painel principal
- [ ] Gráfico de linhas: evolução dos 5 parâmetros ao longo dos ciclos
- [ ] Gráfico de barras: pontuação de risco por ciclo (cor por classificação)
- [ ] Gráfico de pizza/barras: pontuação acumulada por área

### 5.2 Painel energético separado
- [ ] Linha: potência ao longo do tempo
- [ ] Linha: corrente ao longo do tempo
- [ ] Área empilhada: energia consumida vs gerada
- [ ] Indicador: balanço energético total da missão

### 5.3 Timeline visual
- [ ] Cada ciclo como bloco/card com cor e tags
- [ ] Bons (verde), ruins (vermelho), outliers (amarelo), destaque (azul)
- [ ] Ao clicar/hover: detalhes daquele ciclo

### Stack sugerida
- Notebook: matplotlib + ipywidgets
- Web: Streamlit (rápido) ou Dash (mais controle)

---

## FASE 6 — Interatividade

### 6.1 Botão "Gerar Simulação"
- [ ] Usuário escolhe: n_ciclos, perfil, seed
- [ ] Ao clicar: gera nova matriz `dados_missao`
- [ ] Reprocessa toda análise
- [ ] Atualiza dashboards

### 6.2 Integração IA no clique
- [ ] Ao clicar em "Gerar Simulação", após processar localmente:
  - Enviar resumo dos ciclos gerados para o LLM
  - LLM retorna análise narrativa contextual
  - Exibir resposta da IA em área dedicada
- [ ] Não chamar IA em cada ciclo (custo/latência), apenas ao final da geração
- [ ] Tratamento de erro se Ollama estiver offline

### 6.3 Controles adicionais
- [ ] Botão "Re-rodar com mesma seed"
- [ ] Botão "Exportar relatório (.txt/.pdf)"
- [ ] Filtro de visualização: mostrar só ciclos críticos / outliers

---

## FASE 7 — Validação final

- [ ] Rodar checklist de revisão (`REVIEW_CHECKLIST.md`)
- [ ] Garantir que versão "modo terminal" continua funcionando puro Python (PCP exige)
- [ ] Garantir que versão Colab com Ollama está separada (PIA)
- [ ] README atualizado refletindo todas as funcionalidades novas
- [ ] Prints capturados para README