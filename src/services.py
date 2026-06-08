import os
import random
import unicodedata
from groq import Groq

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

AREAS = ["Temperatura interna", "Comunicação com a base", "Sistema de energia", "Suporte de oxigênio", "Estabilidade operacional"]


def analisar_temperatura(v):
    if v <= 30: return 0, "Temperatura nominal."
    if v <= 38: return 1, "Aquecimento moderado detectado. Monitorar resfriamento."
    return 2, "Superaquecimento crítico! Risco de colapso de hardware."

def analisar_comunicacao(v):
    if v >= 70: return 0, "Sinal de comunicação estável."
    if v >= 40: return 1, "Interferência na rede. Perda de pacotes ligeira."
    return 2, "Apagão de comunicação iminente! Alinhando antenas de emergência."

def analisar_energia(v):
    if v >= 60: return 0, "Bateria carregada via painéis solares."
    if v >= 25: return 1, "Subprodução fotovoltaica. Restringir sistemas secundários."
    return 2, "Dreno crítico! Ativar células de combustível de hidrogênio."

def analisar_oxigenio(v):
    if v <= 9.0: return 0, "Taxa de consumo de O2 estável."
    if v <= 11.0: return 1, "Consumo de O2 acima da média. Verificar atividade da tripulação."
    return 2, "Vazamento ou hiperventilação! Pressurizar módulo reserva."

def analisar_estabilidade(v):
    if v >= 80: return 0, "Matriz energética perfeitamente balanceada."
    if v >= 50: return 1, "Flutuação de potência harmónica detectada."
    return 2, "Instabilidade massiva na rede! Risco de blackout operacional."


def detectar_evacuacao(temp, bateria):
    return temp > 35 and bateria < 30


def obter_insight_ia(ciclo_idx, valores, risco):
    try:
        resp = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Atue como engenheiro de sistemas espaciais da Nasa. Forneça uma única recomendação direta (max 40 palavras) em português focada em eficiência energética, painéis solares ou baterias."},
                {"role": "user", "content": f"Ciclo {ciclo_idx} | Temp={valores[0]}°C, Sinal={valores[1]}%, Bateria Solar={valores[2]}%, O2={valores[3]}L/min, Matriz={valores[4]}% | Risco: {risco}/10."},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Modo de Contingência: Analisar padrão do Módulo Fotovoltaico. Erro: {str(e)}"


def gerar_telemetria_simulada():
    temp = round(random.uniform(22, 42), 1)
    com = round(random.uniform(20, 98), 1)
    bat = round(random.uniform(15, 95), 1)
    o2 = round(random.uniform(7.5, 12.5), 1)
    matriz = round(random.uniform(30, 98), 1)
    return [temp, com, bat, o2, matriz]


# ── Gerador parametrizável de missão (Fase 1.1) ──────────
# Ordem dos parâmetros: [temperatura, comunicacao, bateria_solar, consumo_o2, matriz]
PERFIS = ("estavel", "degradacao", "recuperacao", "caotica")

# Limites físicos plausíveis por parâmetro (clamp de geração).
LIMITES = [(18.0, 45.0), (0.0, 100.0), (0.0, 100.0), (6.5, 14.0), (0.0, 100.0)]

# Por parâmetro: (valor com saúde=0 → crítico, valor com saúde=1 → nominal).
_CRITICO_NOMINAL = [
    (42.0, 23.0),   # temperatura: saúde alta => temp baixa
    (20.0, 95.0),   # comunicacao
    (15.0, 92.0),   # bateria_solar
    (12.5, 7.8),    # consumo_o2: saúde alta => consumo baixo
    (32.0, 95.0),   # matriz
]


def _norm_perfil(perfil):
    """Normaliza o perfil (sem acento, minúsculo); default 'estavel' se inválido."""
    txt = unicodedata.normalize("NFKD", (perfil or "").strip().lower())
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt if txt in PERFIS else "estavel"


def _trajetoria_saude(perfil, n, rng):
    """Curva de 'saúde' [0..1] por ciclo. 1 = nominal, 0 = crítico."""
    saude = []
    h = rng.uniform(0.2, 0.8)  # usado apenas no perfil caótico (passeio aleatório)
    for i in range(n):
        u = i / (n - 1) if n > 1 else 0.0
        if perfil == "estavel":
            h = 0.82
        elif perfil == "degradacao":
            h = 0.92 - 0.80 * u
        elif perfil == "recuperacao":
            h = 0.12 + 0.80 * u
        else:  # caotica — passeio aleatório com momentum
            h = max(0.05, min(0.95, h + rng.uniform(-0.35, 0.35)))
        saude.append(h)
    return saude


# Eventos pontuais injetáveis (Fase 1.2): (índice_parâmetro, delta_aplicado).
EVENTOS = {
    "pico_termico":      (0, 12.0),    # pico de temperatura (+°C)
    "falha_comunicacao": (1, -55.0),   # apagão de sinal (−%)
    "queda_bateria":     (2, -35.0),   # dreno súbito de bateria (−%)
    "vazamento_o2":      (3, 3.0),     # vazamento/hiperventilação (+L/min)
    "instabilidade":     (4, -40.0),   # surto na matriz energética (−%)
}


def _indexar_eventos(eventos, n):
    """Mapeia [{'ciclo': i, 'tipo': t}] -> {idx_ciclo: [(param, delta), ...]}."""
    mapa = {}
    for ev in eventos or []:
        tipo = ev.get("tipo")
        ciclo = int(ev.get("ciclo", 0))
        if tipo in EVENTOS and 1 <= ciclo <= n:
            mapa.setdefault(ciclo - 1, []).append(EVENTOS[tipo])
    return mapa


def gerar_dados_missao(n_ciclos=6, perfil="estavel", seed=None, eventos=None):
    """Gera matriz de telemetria parametrizável e realista (Fases 1.1 + 1.2).

    n_ciclos: 6–20 (clamped). perfil: estavel|degradacao|recuperacao|caotica
    (aceita com/sem acento). seed: int opcional p/ reprodutibilidade.
    eventos: lista opcional de {'ciclo': int(1..n), 'tipo': str} para injetar
             perturbações pontuais (chaves válidas em EVENTOS).
    Retorna lista de linhas [temperatura, comunicacao, bateria_solar, consumo_o2, matriz].
    """
    n = max(6, min(20, int(n_ciclos)))
    perfil = _norm_perfil(perfil)
    rng = random.Random(seed)
    ruido = 0.12 if perfil == "caotica" else 0.16
    momentum = 0.65
    eventos_idx = _indexar_eventos(eventos, n)

    ruido_estado = [0.0] * 5           # ruído autocorrelacionado (AR1) por parâmetro
    matriz_dados = []
    for ci, h in enumerate(_trajetoria_saude(perfil, n, rng)):
        linha = []
        for p, (crit, nom) in enumerate(_CRITICO_NOMINAL):
            # variação suave: ruído com momentum (sem saltos brancos puros)
            ruido_estado[p] = momentum * ruido_estado[p] + (1 - momentum) * rng.uniform(-1, 1)
            base = crit + (nom - crit) * h
            linha.append(base + ruido_estado[p] * ruido * abs(nom - crit))

        # eventos pontuais (afetam apenas este ciclo)
        for p, delta in eventos_idx.get(ci, []):
            linha[p] += delta

        # correlação física: calor excessivo derruba estabilidade/bateria e eleva O2
        excesso = max(0.0, linha[0] - 30.0) / 15.0
        linha[4] -= excesso * 18.0
        linha[2] -= excesso * 12.0
        linha[3] += excesso * 0.8

        # clamp aos limites físicos + arredondamento
        for p, (lo, hi) in enumerate(LIMITES):
            linha[p] = round(max(lo, min(hi, linha[p])), 1)
        matriz_dados.append(linha)
    return matriz_dados


def processar_linha(valores, ciclo_idx):
    temp, com, bat, o2, matriz = valores
    r_temp, txt_temp = analisar_temperatura(temp)
    r_com, txt_com = analisar_comunicacao(com)
    r_bat, txt_bat = analisar_energia(bat)
    r_o2, txt_o2 = analisar_oxigenio(o2)
    r_mat, txt_mat = analisar_estabilidade(matriz)
    risco = r_temp + r_com + r_bat + r_o2 + r_mat
    evacuacao = detectar_evacuacao(temp, bat)
    ia = obter_insight_ia(ciclo_idx, valores, risco)
    alertas = [txt_temp, txt_com, txt_bat, txt_o2, txt_mat]
    return risco, evacuacao, ia, alertas


def gerar_sugestao_copiloto(ciclo):
    if ciclo.temperatura > 38:
        return f"⚠️ Temperatura crítica: {ciclo.temperatura}°C no Ciclo {ciclo.ciclo}. Como evitar colapso térmico do hardware?"
    if ciclo.bateria_solar < 30:
        return f"⚠️ Bateria Solar em {ciclo.bateria_solar}% no Ciclo {ciclo.ciclo}. Como otimizar a captação fotovoltaica?"
    if ciclo.comunicacao < 40:
        return f"⚠️ Sinal de comunicação em {ciclo.comunicacao}% no Ciclo {ciclo.ciclo}. Qual protocolo de alinhamento de antenas usar?"
    if ciclo.consumo_o2 > 11:
        return f"⚠️ Consumo de O2 em {ciclo.consumo_o2}L/min no Ciclo {ciclo.ciclo}. Como reduzir a pressão do módulo de suporte?"
    if ciclo.matriz < 50:
        return f"⚠️ Matriz energética em {ciclo.matriz}% no Ciclo {ciclo.ciclo}. Como estabilizar a rede elétrica da nave?"
    return f"✅ Ciclo {ciclo.ciclo} nominal (Risco {ciclo.risco}/10). Há otimizações de longo prazo recomendadas para a missão?"


def obter_resposta_chat(historico, pergunta):
    msgs = [{"role": "system", "content": "Você é um assistente de engenharia aeroespacial. Responda em português, de forma técnica, completa e bem estruturada. Forneça a resposta inteira, sem cortar; ajuste o tamanho ao que a pergunta exige."}]
    for m in historico:
        msgs.append({"role": m.role, "content": m.content})
    msgs.append({"role": "user", "content": pergunta})
    try:
        resp = groq_client.chat.completions.create(
            messages=msgs,
            model="llama-3.1-8b-instant",
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro na IA: {str(e)}"


# ════════════════════════════════════════════════════════
# FASE 2 — Sistema de alertas expandido (análise da série)
# ════════════════════════════════════════════════════════

ANALISADORES = (
    analisar_temperatura, analisar_comunicacao, analisar_energia,
    analisar_oxigenio, analisar_estabilidade,
)


def calcular_risco(linha):
    """Soma dos 5 scores (0–10) sem IA — Python puro (PCP)."""
    return sum(ANALISADORES[i](linha[i])[0] for i in range(5))


def _media_desvio(valores):
    n = len(valores)
    m = sum(valores) / n
    dp = (sum((x - m) ** 2 for x in valores) / n) ** 0.5
    return m, dp


def detectar_outliers(matriz_dados, k=2.0):
    """Para cada ciclo, set de índices de parâmetros que desviam > k·σ da média."""
    if not matriz_dados:
        return []
    stats = [_media_desvio(col) for col in zip(*matriz_dados)]
    flags = []
    for linha in matriz_dados:
        s = {p for p, x in enumerate(linha)
             if stats[p][1] > 0 and abs(x - stats[p][0]) > k * stats[p][1]}
        flags.append(s)
    return flags


def classificar_ciclos(matriz_dados):
    """Tags por ciclo (múltiplas possíveis): BOM, RUIM, OUTLIER, DESTAQUE."""
    riscos = [calcular_risco(l) for l in matriz_dados]
    outliers = detectar_outliers(matriz_dados)
    tags = []
    for i, r in enumerate(riscos):
        t = []
        if r <= 1:
            t.append("BOM")
        if r >= 6:
            t.append("RUIM")
        if outliers[i]:
            t.append("OUTLIER")
        if i > 0 and abs(riscos[i] - riscos[i - 1]) >= 4:
            t.append("DESTAQUE")
        tags.append(t)
    return tags


def gerar_alertas_avancados(matriz_dados):
    """Alertas analíticos sobre a série completa. Lista de {ciclo, tipo, detalhe}."""
    if not matriz_dados:
        return []
    riscos = [calcular_risco(l) for l in matriz_dados]
    outliers = detectar_outliers(matriz_dados)
    alertas = []
    for i, linha in enumerate(matriz_dados):
        c = i + 1
        # OUTLIER — parâmetro desvia > 2σ da média da missão
        for p in sorted(outliers[i]):
            alertas.append({"ciclo": c, "tipo": "OUTLIER",
                            "detalhe": f"{AREAS[p]} desvia mais de 2σ da média da missão."})
        # CORRELACIONADO — 2+ parâmetros críticos no mesmo ciclo
        criticos = [AREAS[p] for p in range(5) if ANALISADORES[p](linha[p])[0] == 2]
        if len(criticos) >= 2:
            alertas.append({"ciclo": c, "tipo": "CORRELACIONADO",
                            "detalhe": "Falha combinada: " + ", ".join(criticos) + "."})
        # ANOMALIA ENERGÉTICA — bateria/O2 fora do padrão esperado
        energia = [AREAS[p] for p in (2, 3) if p in outliers[i]]
        if energia:
            alertas.append({"ciclo": c, "tipo": "ANOMALIA_ENERGETICA",
                            "detalhe": "Consumo energético atípico: " + ", ".join(energia) + "."})
    # TENDÊNCIA NEGATIVA — 3 ciclos consecutivos piorando
    for i in range(2, len(riscos)):
        if riscos[i] > riscos[i - 1] > riscos[i - 2]:
            alertas.append({"ciclo": i + 1, "tipo": "TENDENCIA_NEGATIVA",
                            "detalhe": "Risco subiu em 3 ciclos consecutivos."})
    # RECUPERAÇÃO — saída de estado crítico (≥6) para atenção/normal (≤5)
    for i in range(1, len(riscos)):
        if riscos[i - 1] >= 6 and riscos[i] <= 5:
            alertas.append({"ciclo": i + 1, "tipo": "RECUPERACAO",
                            "detalhe": "Saída de estado crítico para estável/atenção."})
    return alertas


# ════════════════════════════════════════════════════════
# FASE 3 — Seção energética (SERS): potência, balanço, eficiência
# ════════════════════════════════════════════════════════

TENSAO_NOMINAL_V = 28.0      # barramento padrão de spacecraft
POTENCIA_BASE_W = 250.0      # carga vital mínima
GERACAO_PICO_W = 720.0       # potência de pico do painel solar
DURACAO_CICLO_H = 1.0        # assume 1h por ciclo


def calcular_metricas_energeticas(linha):
    """Métricas energéticas de 1 ciclo (SERS). Recebe [temp, com, bat, o2, matriz].

    Retorna: potencia_W, corrente_A, energia_Wh, geracao_Wh, balanco_Wh, eficiencia_pct.
    """
    temp, com, _bat, o2, matriz = linha
    # Potência consumida: base + suporte de vida + controle térmico + comms + perdas
    pot = POTENCIA_BASE_W
    pot += max(0.0, o2 - 8.0) * 60.0          # scrubbers/bombas de O2
    pot += max(0.0, temp - 25.0) * 18.0       # refrigeração ativa
    pot += (100.0 - com) * 1.5                # ganho de transmissão sob interferência
    pot += (100.0 - matriz) * 1.2             # perdas por instabilidade da rede
    pot = max(120.0, pot)

    corrente = pot / TENSAO_NOMINAL_V          # I = P / V
    energia = pot * DURACAO_CICLO_H            # E = P · t (Wh)

    # Geração fotovoltaica: escala com saúde da matriz e sofre derating térmico
    derate = 1.0 - min(0.4, max(0.0, temp - 25.0) * 0.012)
    geracao_W = GERACAO_PICO_W * (0.4 + 0.6 * matriz / 100.0) * derate
    geracao = max(0.0, geracao_W * DURACAO_CICLO_H)

    balanco = geracao - energia                # >0 carrega, <0 drena
    perda_pct = (100.0 - matriz) / 100.0 * 0.5  # instabilidade => perda resistiva
    eficiencia = (1.0 - perda_pct) * 100.0      # energia útil / consumida

    return {
        "potencia_W": round(pot, 1),
        "corrente_A": round(corrente, 2),
        "energia_Wh": round(energia, 1),
        "geracao_Wh": round(geracao, 1),
        "balanco_Wh": round(balanco, 1),
        "eficiencia_pct": round(eficiencia, 1),
    }


def resumo_energetico(matriz_dados):
    """Agrega métricas energéticas da missão + recomendação SERS automatizada."""
    if not matriz_dados:
        return {}
    metr = [calcular_metricas_energeticas(l) for l in matriz_dados]
    consumos = [m["energia_Wh"] for m in metr]
    geracoes = [m["geracao_Wh"] for m in metr]
    eficiencias = [m["eficiencia_pct"] for m in metr]
    balanco_total = round(sum(m["balanco_Wh"] for m in metr), 1)
    idx_pico = consumos.index(max(consumos))
    idx_pior_ef = eficiencias.index(min(eficiencias))

    if balanco_total < 0:
        rec = ("Déficit energético acumulado: a missão consome mais do que gera. "
               "Reduzir cargas secundárias e priorizar recarga dos bancos de bateria.")
    elif min(eficiencias) < 70:
        rec = ("Eficiência crítica por instabilidade da matriz. Estabilizar a rede "
               "antes de reativar sistemas não essenciais.")
    else:
        rec = "Balanço energético positivo e eficiência saudável. Operação sustentável."

    return {
        "consumo_medio_W": round(sum(consumos) / len(consumos), 1),
        "pico_consumo_W": max(consumos),
        "ciclo_pico_consumo": idx_pico + 1,
        "geracao_total_Wh": round(sum(geracoes), 1),
        "consumo_total_Wh": round(sum(consumos), 1),
        "balanco_total_Wh": balanco_total,
        "ciclo_menor_eficiencia": idx_pior_ef + 1,
        "menor_eficiencia_pct": min(eficiencias),
        "recomendacao": rec,
    }


# ════════════════════════════════════════════════════════
# FASE 6 — Apoio à geração em lote e narrativa única de IA
# ════════════════════════════════════════════════════════

def processar_linha_sem_ia(valores):
    """Análise rule-based de 1 ciclo SEM chamada à IA (geração em lote, Fase 6.2).

    Retorna (risco, evacuacao, insight, alertas) — insight é rule-based.
    """
    resultados = [ANALISADORES[i](valores[i]) for i in range(5)]
    scores = [r[0] for r in resultados]
    alertas = [r[1] for r in resultados]
    risco = sum(scores)
    evac = detectar_evacuacao(valores[0], valores[2])
    pior = max(range(5), key=lambda i: scores[i])
    insight = alertas[pior] if scores[pior] > 0 else "Telemetria nominal. Sistemas estáveis."
    return risco, evac, insight, alertas


def gerar_narrativa_missao(matriz_dados, energia):
    """Uma única análise narrativa da missão gerada (Fase 6.2). Tem fallback."""
    if not matriz_dados:
        return "Sem dados para análise."
    riscos = [calcular_risco(l) for l in matriz_dados]
    resumo = (
        f"{len(matriz_dados)} ciclos. Risco inicial {riscos[0]}, final {riscos[-1]}, "
        f"pico {max(riscos)}/10. Balanço energético {energia.get('balanco_total_Wh', '?')} Wh. "
        f"Eficiência mínima {energia.get('menor_eficiencia_pct', '?')}%."
    )
    try:
        resp = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é o engenheiro-chefe de uma missão espacial. Faça uma análise narrativa em português (máx 80 palavras): tendência da missão, principal risco e uma recomendação energética acionável."},
                {"role": "user", "content": resumo},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return (f"Modo de Contingência (IA indisponível). {resumo} "
                f"Recomenda-se priorizar a recarga dos bancos de bateria e estabilizar a "
                f"matriz energética antes de reativar sistemas secundários. [{str(e)[:50]}]")


# ════════════════════════════════════════════════════════
# GS2 — Classificação da missão, diagnóstico, eventos e relatório
# ════════════════════════════════════════════════════════

# Faixas de classificação do ciclo (PCP): 0 / 1–5 / 6+
def classificar_missao(risco):
    """Classificação do ciclo a partir da pontuação de risco (0–10)."""
    if risco == 0:
        return "MISSÃO ESTÁVEL"
    if risco <= 5:
        return "MISSÃO EM ATENÇÃO"
    return "MISSÃO CRÍTICA"


STATUS_TXT = {0: "NORMAL", 1: "ATENÇÃO", 2: "CRÍTICO"}

# Metadados de diagnóstico por variável (índice = ordem da telemetria)
VARIAVEIS = [
    {"nome": "Temperatura",   "unidade": "°C",    "faixa": "0 a 30 °C"},
    {"nome": "Comunicação",   "unidade": "%",     "faixa": "70% a 100%"},
    {"nome": "Bateria",       "unidade": "%",     "faixa": "60% a 100%"},
    {"nome": "Oxigênio",      "unidade": "L/min", "faixa": "≤ 9 L/min"},
    {"nome": "Estabilidade",  "unidade": "%",     "faixa": "80% a 100%"},
]
MSG_VAR = {
    0: {0: "Temperatura estável",            1: "Temperatura elevada",          2: "Risco de superaquecimento"},
    1: {0: "Comunicação estável",            1: "Comunicação instável",         2: "Comunicação com a base em nível crítico"},
    2: {0: "Energia estável",                1: "Bateria abaixo do recomendado",2: "Bateria em nível crítico"},
    3: {0: "Oxigênio adequado",              1: "Consumo de O₂ acima do ideal", 2: "Consumo de O₂ em nível crítico"},
    4: {0: "Estabilidade operacional adequada", 1: "Estabilidade operacional reduzida", 2: "Estabilidade operacional crítica"},
}
IMPACTO_VAR = {
    0: {0: "Operação térmica nominal.",   1: "Aquecimento acima do ideal.",     2: "Risco de colapso de hardware."},
    1: {0: "Enlace estável com a base.",  1: "Perda de pacotes / latência.",    2: "Risco de apagão de comunicação."},
    2: {0: "Energia disponível.",         1: "Capacidade operacional reduzida.",2: "Risco de perda total de energia."},
    3: {0: "Suporte de vida estável.",    1: "Consumo de O₂ acima do esperado.",2: "Risco direto ao suporte de vida."},
    4: {0: "Rede elétrica equilibrada.",  1: "Flutuações na matriz energética.",2: "Risco de blackout operacional."},
}
RECOM_VAR = {
    0: {0: "Manter monitoramento.", 1: "Verificar controle térmico.",            2: "Acionar radiadores de emergência."},
    1: {0: "Manter monitoramento.", 1: "Realinhar antena e reduzir ruído.",       2: "Acionar protocolo de emergência de comunicação."},
    2: {0: "Manter monitoramento.", 1: "Aumentar exposição dos painéis solares.", 2: "Cortar cargas e priorizar recarga."},
    3: {0: "Manter monitoramento.", 1: "Revisar consumo do suporte de vida.",     2: "Pressurizar módulo reserva."},
    4: {0: "Manter monitoramento.", 1: "Rebalancear a matriz energética.",        2: "Estabilizar a rede para evitar blackout."},
}


def diagnostico_variaveis(valores):
    """Diagnóstico rico por variável de 1 ciclo (valor, status, faixa, impacto, recomendação)."""
    out = []
    for i, meta in enumerate(VARIAVEIS):
        score = ANALISADORES[i](valores[i])[0]
        out.append({
            "nome": meta["nome"], "valor": valores[i], "unidade": meta["unidade"],
            "score": score, "status": STATUS_TXT[score], "faixa_ideal": meta["faixa"],
            "mensagem": MSG_VAR[i][score], "impacto": IMPACTO_VAR[i][score],
            "recomendacao": RECOM_VAR[i][score],
        })
    return out


def justificar_classificacao(valores):
    """Texto curto justificando a classificação (contagem de críticos/atenção)."""
    scores = [ANALISADORES[i](valores[i])[0] for i in range(5)]
    crit = [VARIAVEIS[i]["nome"] for i in range(5) if scores[i] == 2]
    aten = [VARIAVEIS[i]["nome"] for i in range(5) if scores[i] == 1]
    partes = []
    if crit:
        partes.append(f"{len(crit)} parâmetro(s) crítico(s): {', '.join(crit)}")
    if aten:
        partes.append(f"{len(aten)} em atenção: {', '.join(aten)}")
    if not partes:
        return "Todos os parâmetros em níveis nominais."
    return "; ".join(partes) + "."


def recomendar_ciclo(valores):
    """Recomendação operacional do ciclo (heurística PCP)."""
    scores = [ANALISADORES[i](valores[i])[0] for i in range(5)]
    risco = sum(scores)
    n_crit = scores.count(2)
    if risco == 0:
        return "Manter operação normal e continuar monitoramento."
    if n_crit >= 3:
        return "Ativar modo de segurança e priorizar suporte à vida, energia e comunicação."
    maxs = max(scores)
    if scores[0] == maxs and scores.count(maxs) == 1:   # temperatura é o pior fator isolado
        return "Verificar controle térmico da missão."
    return "Monitorar sistemas em atenção e preparar plano de contingência."


def tipo_evento_serie(matriz_dados):
    """Tipo de evento dominante por ciclo: Estável | Atenção | Crítico | Recuperação | Outlier | Correlacionado."""
    if not matriz_dados:
        return []
    riscos = [calcular_risco(l) for l in matriz_dados]
    outliers = detectar_outliers(matriz_dados)
    tipos = []
    for i, linha in enumerate(matriz_dados):
        n_crit = sum(1 for p in range(5) if ANALISADORES[p](linha[p])[0] == 2)
        if n_crit >= 2:
            tipos.append("Correlacionado")
        elif outliers[i]:
            tipos.append("Outlier")
        elif i > 0 and riscos[i - 1] >= 6 and riscos[i] <= 5:
            tipos.append("Recuperação")
        elif riscos[i] >= 6:
            tipos.append("Crítico")
        elif riscos[i] >= 1:
            tipos.append("Atenção")
        else:
            tipos.append("Estável")
    return tipos


def gerar_conclusao_missao(matriz_dados):
    """Conclusão narrativa dinâmica (rule-based) com base no comportamento dos ciclos."""
    if not matriz_dados:
        return "Sem ciclos suficientes para uma conclusão."
    riscos = [calcular_risco(l) for l in matriz_dados]
    pico, ultimo, primeiro = max(riscos), riscos[-1], riscos[0]
    n_crit = sum(1 for r in riscos if r >= 6)
    pontos = [0] * 5
    for l in matriz_dados:
        for i in range(5):
            pontos[i] += ANALISADORES[i](l[i])[0]
    area = AREAS[pontos.index(max(pontos))]

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
    elif primeiro == ultimo and pico == ultimo:
        f.append("O nível de risco permaneceu estável do início ao fim.")

    f.append(f"A área mais exigida foi {area}.")
    return " ".join(f)


def _fmt_valor(v, unidade):
    txt = f"{v:g}"
    return f"{txt}%" if unidade == "%" else f"{txt} {unidade}"


def gerar_relatorio_txt(matriz_dados, missao, equipe):
    """Gera o relatório .txt fiel ao modelo GS2 (dados e unidades reais do sistema)."""
    SEP = "=" * 60
    SUB = "-" * 60
    n = len(matriz_dados)
    L = []
    L.append("MISSION CONTROL AI")
    L.append(SEP)
    L.append(f"Missão: {missao}")
    L.append(f"Equipe: {equipe}")
    L.append(f"Quantidade de ciclos analisados: {n}")
    L.append(SEP)

    for idx, valores in enumerate(matriz_dados, start=1):
        diag = diagnostico_variaveis(valores)
        risco = sum(d["score"] for d in diag)
        L.append(f"CICLO {idx}")
        L.append(SUB)
        for d in diag:
            L.append(f"{d['nome']}: {_fmt_valor(d['valor'], d['unidade'])} | {d['status']} | {d['mensagem']}")
        L.append(f"Pontuação de risco do ciclo: {risco}")
        L.append(f"Classificação do ciclo: {classificar_missao(risco)}")
        L.append(f"Recomendação: {recomendar_ciclo(valores)}")
        L.append("")

    # ── Relatório final ──
    riscos = [calcular_risco(l) for l in matriz_dados]
    medias = [sum(l[i] for l in matriz_dados) / n for i in range(5)]
    pontos = [0] * 5
    for l in matriz_dados:
        for i in range(5):
            pontos[i] += ANALISADORES[i](l[i])[0]
    risco_medio = sum(riscos) / n
    ciclo_pior = riscos.index(max(riscos)) + 1
    n_crit = sum(1 for r in riscos if r >= 6)
    if riscos[-1] > riscos[0]:
        tendencia = "A missão apresentou tendência de piora."
    elif riscos[-1] < riscos[0]:
        tendencia = "A missão apresentou tendência de melhora."
    else:
        tendencia = "A missão manteve-se estável."

    L.append(SEP)
    L.append("RELATÓRIO FINAL DA MISSÃO")
    L.append(SEP)
    L.append(f"Missão: {missao}")
    L.append(f"Equipe: {equipe}")
    L.append("")
    L.append(f"Quantidade de ciclos analisados: {n}")
    L.append("")
    L.append(f"Média de temperatura: {medias[0]:.2f} °C")
    L.append(f"Média de comunicação: {medias[1]:.2f}%")
    L.append(f"Média de bateria: {medias[2]:.2f}%")
    L.append(f"Média de oxigênio: {medias[3]:.2f} L/min")
    L.append(f"Média de estabilidade: {medias[4]:.2f}%")
    L.append("")
    L.append(f"Ciclo mais crítico: Ciclo {ciclo_pior}")
    L.append(f"Maior pontuação de risco: {max(riscos)}")
    L.append(f"Risco médio da missão: {risco_medio:.2f}")
    L.append(f"Quantidade de ciclos críticos: {n_crit}")
    L.append("")
    L.append("Tendência da missão:")
    L.append(tendencia)
    L.append("")
    L.append("Pontuação acumulada por área:")
    for i, area in enumerate(AREAS):
        L.append(f"{area}: {pontos[i]} pontos")
    L.append("")
    L.append("Área mais afetada:")
    L.append(AREAS[pontos.index(max(pontos))])
    L.append("")
    L.append("Classificação final da missão:")
    L.append(classificar_missao(round(risco_medio)))
    L.append("")
    L.append("Conclusão:")
    L.append(gerar_conclusao_missao(matriz_dados))
    L.append("")
    L.append("")
    L.append("NORMAL = 0 ponto")
    L.append("ATENÇÃO = 1 ponto")
    L.append("CRÍTICO = 2 pontos")
    return "\n".join(L)
