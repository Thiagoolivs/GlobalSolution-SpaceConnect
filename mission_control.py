"""Mission Control AI — Versão Terminal (PCP / SERS).

Análise rule-based de telemetria de missão espacial em Python puro
(somente biblioteca padrão — sem Flask, sem IA, sem dependências externas).

Esta é a versão "modo terminal" exigida pela disciplina PCP. A versão web
(Flask + Groq/Llama 3.1) vive no pacote `src/` e atende a disciplina PIA.
O relatório segue o mesmo formato do export .txt do dashboard.

Execução:  python mission_control.py
"""

import os

# Habilita sequências ANSI (cores) também no console legado do Windows.
if os.name == "nt":
    os.system("")

# ─────────────────────────────────────────────────────────────
# IDENTIFICAÇÃO DA MISSÃO
# ─────────────────────────────────────────────────────────────
NOME_MISSAO = "Orion Test Alpha"
NOME_EQUIPE = "Equipe Apollo"

# Áreas monitoradas (alinhadas às 5 colunas de dados_missao)
areas_monitoradas = [
    "Temperatura interna",
    "Comunicação com a base",
    "Sistema de energia",
    "Suporte de oxigênio",
    "Estabilidade operacional",
]

# Matriz de telemetria: cada linha = [temp(°C), comunic(%), bateria(%), oxigenio(L/min), estabilidade(%)]
dados_missao = [
    [24, 92, 88, 8.2, 90],
    [27, 80, 72, 8.8, 85],
    [31, 65, 58, 9.5, 70],
    [36, 42, 38, 10.8, 55],
    [39, 28, 19, 11.5, 35],
    [29, 75, 65, 8.5, 82],
]

# Pontuação de severidade por classificação (referência PCP)
PONTOS_NORMAL, PONTOS_ATENCAO, PONTOS_CRITICO = 0, 1, 2

# Parâmetros físicos do subsistema energético (SERS)
TENSAO_NOMINAL_V = 28.0
POTENCIA_BASE_W = 250.0
GERACAO_PICO_W = 720.0
DURACAO_CICLO_H = 1.0

# Cores ANSI (degradam para vazio em terminais sem suporte)
C_RESET, C_DIM = "\033[0m", "\033[2m"
C_OK, C_WARN, C_CRIT = "\033[92m", "\033[93m", "\033[91m"
C_TITLE, C_ACCENT = "\033[96m", "\033[95m"

SEP = "=" * 60
SUB = "-" * 60


# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE ANÁLISE — retornam (status, mensagem, pontos)
# ─────────────────────────────────────────────────────────────
def analisar_temperatura(v):
    """Classifica a temperatura interna (°C)."""
    if v <= 30:
        return "NORMAL", "Temperatura estável", PONTOS_NORMAL
    if v <= 38:
        return "ATENÇÃO", "Temperatura elevada", PONTOS_ATENCAO
    return "CRÍTICO", "Risco de superaquecimento", PONTOS_CRITICO


def analisar_comunicacao(v):
    """Classifica o sinal de comunicação com a base (%)."""
    if v >= 70:
        return "NORMAL", "Comunicação estável", PONTOS_NORMAL
    if v >= 40:
        return "ATENÇÃO", "Comunicação instável", PONTOS_ATENCAO
    return "CRÍTICO", "Comunicação com a base em nível crítico", PONTOS_CRITICO


def analisar_energia(v):
    """Classifica a carga da bateria solar (%)."""
    if v >= 60:
        return "NORMAL", "Energia estável", PONTOS_NORMAL
    if v >= 25:
        return "ATENÇÃO", "Bateria abaixo do recomendado", PONTOS_ATENCAO
    return "CRÍTICO", "Bateria em nível crítico", PONTOS_CRITICO


def analisar_oxigenio(v):
    """Classifica o consumo de oxigênio (L/min)."""
    if v <= 9.0:
        return "NORMAL", "Oxigênio adequado", PONTOS_NORMAL
    if v <= 11.0:
        return "ATENÇÃO", "Consumo de O2 acima do ideal", PONTOS_ATENCAO
    return "CRÍTICO", "Consumo de O2 em nível crítico", PONTOS_CRITICO


def analisar_estabilidade(v):
    """Classifica a estabilidade da matriz energética (%)."""
    if v >= 80:
        return "NORMAL", "Estabilidade operacional adequada", PONTOS_NORMAL
    if v >= 50:
        return "ATENÇÃO", "Estabilidade operacional reduzida", PONTOS_ATENCAO
    return "CRÍTICO", "Estabilidade operacional crítica", PONTOS_CRITICO


ANALISADORES = [
    analisar_temperatura, analisar_comunicacao, analisar_energia,
    analisar_oxigenio, analisar_estabilidade,
]
ROTULOS = ["Temperatura", "Comunicação", "Bateria", "Oxigênio", "Estabilidade"]
UNIDADES = ["°C", "%", "%", "L/min", "%"]


# ─────────────────────────────────────────────────────────────
# CLASSIFICAÇÃO E ANÁLISE AGREGADA
# ─────────────────────────────────────────────────────────────
def classificar_ciclo(risco):
    """Classificação a partir da pontuação: 0 / 1–5 / 6+."""
    if risco == 0:
        return "MISSÃO ESTÁVEL"
    if risco <= 5:
        return "MISSÃO EM ATENÇÃO"
    return "MISSÃO CRÍTICA"


def detectar_evacuacao(temperatura, bateria):
    """Regra combinada de evacuação: temp > 35 E bateria < 30."""
    return temperatura > 35 and bateria < 30


def recomendar_ciclo(valores):
    """Recomendação operacional do ciclo (heurística PCP)."""
    scores = [ANALISADORES[i](valores[i])[2] for i in range(5)]
    risco = sum(scores)
    if risco == 0:
        return "Manter operação normal e continuar monitoramento."
    if scores.count(PONTOS_CRITICO) >= 3:
        return "Ativar modo de segurança e priorizar suporte à vida, energia e comunicação."
    maxs = max(scores)
    if scores[0] == maxs and scores.count(maxs) == 1:
        return "Verificar controle térmico da missão."
    return "Monitorar sistemas em atenção e preparar plano de contingência."


def analisar_tendencia(riscos):
    """Compara o risco do primeiro e do último ciclo."""
    if riscos[-1] > riscos[0]:
        return "A missão apresentou tendência de piora."
    if riscos[-1] < riscos[0]:
        return "A missão apresentou tendência de melhora."
    return "A missão manteve-se estável."


def identificar_area_mais_afetada(matriz):
    """Soma os pontos por COLUNA (área) e retorna (índice, lista acumulada)."""
    acumulado = [0] * 5
    for linha in matriz:
        for i, valor in enumerate(linha):
            acumulado[i] += ANALISADORES[i](valor)[2]
    return acumulado.index(max(acumulado)), acumulado


def gerar_conclusao(matriz, riscos):
    """Conclusão narrativa dinâmica baseada no comportamento dos ciclos."""
    pico, ultimo = max(riscos), riscos[-1]
    n_crit = sum(1 for r in riscos if r >= 6)
    area = areas_monitoradas[identificar_area_mais_afetada(matriz)[0]]
    f = []
    if n_crit > 0:
        f.append(f"A missão atravessou {n_crit} ciclo(s) em estado crítico, com pico de risco {pico}/10.")
    elif pico >= 3:
        f.append("A missão apresentou instabilidades pontuais, sem entrar em estado crítico.")
    else:
        f.append("A missão manteve-se predominantemente estável ao longo da operação.")
    if ultimo <= 2 and pico >= 6:
        f.append("Houve recuperação consistente e retorno gradual à estabilidade operacional nos ciclos finais.")
    elif ultimo < pico and ultimo >= 1:
        f.append("Apesar da tentativa de recuperação, ainda existem sistemas exigindo atenção e a equipe deve manter o plano de contingência ativo.")
    elif ultimo >= pico and ultimo >= 6:
        f.append("A deterioração progrediu até os ciclos finais, exigindo intervenção imediata.")
    f.append(f"A área mais exigida foi {area}.")
    return " ".join(f)


def calcular_metricas_energeticas(valores):
    """Métricas SERS de um ciclo: potência, corrente, energia, geração, balanço, eficiência."""
    temp, com, _bat, o2, matriz = valores
    pot = POTENCIA_BASE_W
    pot += max(0.0, o2 - 8.0) * 60.0
    pot += max(0.0, temp - 25.0) * 18.0
    pot += (100.0 - com) * 1.5
    pot += (100.0 - matriz) * 1.2
    pot = max(120.0, pot)
    corrente = pot / TENSAO_NOMINAL_V
    energia = pot * DURACAO_CICLO_H
    derate = 1.0 - min(0.4, max(0.0, temp - 25.0) * 0.012)
    geracao = max(0.0, GERACAO_PICO_W * (0.4 + 0.6 * matriz / 100.0) * derate * DURACAO_CICLO_H)
    return {
        "potencia": round(pot, 1), "corrente": round(corrente, 2),
        "energia": round(energia, 1), "geracao": round(geracao, 1),
        "balanco": round(geracao - energia, 1),
        "eficiencia": round((1.0 - (100.0 - matriz) / 100.0 * 0.5) * 100.0, 1),
    }


def cor_risco(risco):
    return C_CRIT if risco >= 6 else C_WARN if risco >= 1 else C_OK


def _fmt_valor(v, unidade):
    txt = f"{v:g}"
    return f"{txt}%" if unidade == "%" else f"{txt} {unidade}"


# ─────────────────────────────────────────────────────────────
# RELATÓRIO
# ─────────────────────────────────────────────────────────────
def main():
    """Ponto de entrada: processa os ciclos e imprime o relatório no formato GS2."""
    n = len(dados_missao)
    riscos, evacuacoes = [], 0
    soma = [0.0] * 5
    energia_total = geracao_total = 0.0

    print(f"\n{C_TITLE}MISSION CONTROL AI{C_RESET}")
    print(SEP)
    print(f"Missão: {NOME_MISSAO}")
    print(f"Equipe: {NOME_EQUIPE}")
    print(f"Quantidade de ciclos analisados: {n}")
    print(SEP)

    for indice, valores in enumerate(dados_missao, start=1):
        risco = 0
        cor = None
        print(f"\nCICLO {indice}")
        print(SUB)
        for i, valor in enumerate(valores):
            status, mensagem, pontos = ANALISADORES[i](valor)
            risco += pontos
            soma[i] += valor
        cor = cor_risco(risco)
        for i, valor in enumerate(valores):
            status, mensagem, _ = ANALISADORES[i](valor)
            print(f"{ROTULOS[i]}: {_fmt_valor(valor, UNIDADES[i])} | {status} | {mensagem}")
        riscos.append(risco)
        if detectar_evacuacao(valores[0], valores[2]):
            evacuacoes += 1
        en = calcular_metricas_energeticas(valores)
        energia_total += en["energia"]
        geracao_total += en["geracao"]
        print(f"Pontuação de risco do ciclo: {cor}{risco}{C_RESET}")
        print(f"Classificação do ciclo: {cor}{classificar_ciclo(risco)}{C_RESET}")
        print(f"Recomendação: {recomendar_ciclo(valores)}")
        print(f"{C_DIM}Energia: consumo {en['energia']}Wh | geração {en['geracao']}Wh | "
              f"balanço {en['balanco']}Wh | eficiência {en['eficiencia']}%{C_RESET}")

    # ── Relatório final ──
    medias = [soma[i] / n for i in range(5)]
    risco_medio = sum(riscos) / n
    ciclo_pior = riscos.index(max(riscos)) + 1
    n_crit = sum(1 for r in riscos if r >= 6)
    pior_idx, acumulado = identificar_area_mais_afetada(dados_missao)
    balanco_total = round(geracao_total - energia_total, 1)

    print(f"\n{SEP}")
    print(f"{C_ACCENT}RELATÓRIO FINAL DA MISSÃO{C_RESET}")
    print(SEP)
    print(f"Missão: {NOME_MISSAO}")
    print(f"Equipe: {NOME_EQUIPE}\n")
    print(f"Quantidade de ciclos analisados: {n}\n")
    print(f"Média de temperatura: {medias[0]:.2f} °C")
    print(f"Média de comunicação: {medias[1]:.2f}%")
    print(f"Média de bateria: {medias[2]:.2f}%")
    print(f"Média de oxigênio: {medias[3]:.2f} L/min")
    print(f"Média de estabilidade: {medias[4]:.2f}%\n")
    print(f"Ciclo mais crítico: Ciclo {ciclo_pior}")
    print(f"Maior pontuação de risco: {max(riscos)}")
    print(f"Risco médio da missão: {risco_medio:.2f}")
    print(f"Quantidade de ciclos críticos: {n_crit}\n")
    print("Tendência da missão:")
    print(f"{analisar_tendencia(riscos)}\n")
    print("Pontuação acumulada por área:")
    for i, area in enumerate(areas_monitoradas):
        print(f"{area}: {acumulado[i]} pontos")
    print("\nÁrea mais afetada:")
    print(f"{areas_monitoradas[pior_idx]}\n")
    print("Subsistema energético (SERS):")
    cor_bal = C_OK if balanco_total >= 0 else C_CRIT
    print(f"Energia consumida total: {round(energia_total, 1)} Wh")
    print(f"Energia gerada total: {round(geracao_total, 1)} Wh")
    print(f"Balanço energético: {cor_bal}{balanco_total} Wh{C_RESET}\n")
    print("Classificação final da missão:")
    print(f"{C_ACCENT}{classificar_ciclo(round(risco_medio))}{C_RESET}\n")
    print("Conclusão:")
    print(gerar_conclusao(dados_missao, riscos))
    print(f"\n\n{C_DIM}NORMAL = 0 ponto | ATENÇÃO = 1 ponto | CRÍTICO = 2 pontos{C_RESET}")


if __name__ == "__main__":
    main()
