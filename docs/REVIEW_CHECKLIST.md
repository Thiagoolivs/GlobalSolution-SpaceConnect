# CHECKLIST DE REVISÃO — MISSION CONTROL AI

## A. Estrutura Base (PCP)
- [ ] Variáveis `nome_missao` e `nome_equipe` definidas no topo
- [ ] Matriz `dados_missao` com ≥6 ciclos, formato [temp, com, bat, oxi, est]
- [ ] Lista `areas_monitoradas` com 5 itens alinhados às colunas
- [ ] ≥5 funções, todas chamadas em algum ponto do fluxo
- [ ] Loop `for` percorrendo `dados_missao`
- [ ] Condicionais (`if/elif/else`) para faixas de classificação
- [ ] Código roda sem erro até o relatório final

## B. Lógica de Análise
- [ ] Função para cada parâmetro retorna (classificacao, mensagem, pontos)
- [ ] Limites NORMAL/ATENÇÃO/CRÍTICO conferem com README
- [ ] Pontuação: NORMAL=0, ATENÇÃO=1, CRÍTICO=2
- [ ] Soma por ciclo nunca passa de 10
- [ ] `classificar_ciclo()` segue faixas 0-2 / 3-5 / 6-10

## C. Análise Agregada
- [ ] `analisar_tendencia()` compara risco do ciclo 1 vs último
- [ ] Retorna "melhorou" / "piorou" / "estável"
- [ ] `identificar_area_mais_afetada()` soma pontos por coluna, não por linha
- [ ] `gerar_recomendacao()` cobre os 5 parâmetros em estado crítico

## D. Relatório Final
- [ ] Cabeçalho com nome da missão e equipe
- [ ] Médias das 5 colunas (com 2 casas decimais)
- [ ] Ciclo mais crítico identificado
- [ ] Maior pontuação de risco
- [ ] Risco médio da missão
- [ ] Quantidade de ciclos críticos
- [ ] Tendência geral
- [ ] Pontuação acumulada por área
- [ ] Área mais afetada nominada
- [ ] Classificação final + conclusão narrativa

## E. Integração IA (só PIA)
- [ ] `ollama` instalado e modelo `llama3.2:1b` baixado
- [ ] System prompt específico de missão espacial (não genérico)
- [ ] Pelo menos 1 chamada da IA exibida no output
- [ ] Tratamento de exceção se o modelo falhar
- [ ] Resposta da IA legível, não truncada
- [ ] Notebook `.ipynb` salvo com saídas das células visíveis

## F. SERS — Aderência Energética
- [ ] Código ou README explica conceitos de energia/potência aplicados
- [ ] Pelo menos uma decisão lógica explicitamente sustentável
- [ ] Diferencial inovador presente (geração solar, eficiência, etc.)
- [ ] Framing energético claro no README

## G. README
- [ ] Título com nome do projeto
- [ ] Integrantes com RM
- [ ] Descrição 2–3 frases
- [ ] Stack listada
- [ ] Regras de alerta documentadas (limites)
- [ ] Como executar (link Colab para PIA)
- [ ] ≥2 prints reais (4 para nota máxima em PIA)
- [ ] Pasta `assets/` existe e tem as imagens referenciadas
- [ ] Link do vídeo presente

## H. Vídeo
- [ ] Máximo 3 minutos (medir!)
- [ ] Integrantes apresentados (nome ou rosto)
- [ ] Sistema rodando ao vivo, não slides
- [ ] Cenário de alerta/crítico demonstrado
- [ ] PIA: IA respondendo em tempo real
- [ ] PCP: SEM narração com IA, YouTube como não listado
- [ ] Áudio audível

## I. Repositório
- [ ] Público e acessível sem login
- [ ] Estrutura: `README.md` + `mission_control.py` (mínimo PCP)
- [ ] Sem arquivos sensíveis (.env, chaves)
- [ ] Commits com mensagens descritivas

## J. Arquivo .txt de Entrega
- [ ] Nome da missão (PCP/SERS)
- [ ] Nome da equipe
- [ ] Nomes completos + RM de todos
- [ ] Link GitHub
- [ ] Link YouTube/vídeo
- [ ] Sem links quebrados (testar antes de enviar)

## K. Qualidade do Código
- [ ] Sem prints de debug esquecidos
- [ ] Sem código comentado/morto
- [ ] Nomes de variáveis em pt-BR consistentes (sem mistura com en)
- [ ] Sem números mágicos (limites em constantes nomeadas)
- [ ] Funções com docstring curta