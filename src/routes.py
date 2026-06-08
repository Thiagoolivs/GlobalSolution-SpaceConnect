from flask import Blueprint, render_template, jsonify, request
from . import db
from .models import CicloTelemetria, MensagemChat
from flask import Response
from .services import (
    gerar_telemetria_simulada, processar_linha, processar_linha_sem_ia,
    obter_resposta_chat, gerar_sugestao_copiloto, AREAS,
    analisar_temperatura, analisar_comunicacao, analisar_energia,
    analisar_oxigenio, analisar_estabilidade,
    gerar_dados_missao, _norm_perfil, resumo_energetico,
    calcular_metricas_energeticas, gerar_alertas_avancados,
    classificar_ciclos, gerar_narrativa_missao,
    classificar_missao, justificar_classificacao, diagnostico_variaveis,
    tipo_evento_serie, gerar_relatorio_txt,
)

bp = Blueprint("main", __name__)

NOME_MISSAO = "Orion Test Alpha"
EQUIPE = "Equipe Apollo"

DADOS_INICIAIS = [
    [24, 92, 88, 8.2, 90],
    [27, 80, 72, 8.8, 85],
    [31, 65, 58, 9.5, 70],
    [36, 42, 38, 10.8, 55],
    [39, 28, 19, 11.5, 35],
    [29, 75, 65, 8.5, 82],
]

_ANALISADORES = [
    analisar_temperatura, analisar_comunicacao, analisar_energia,
    analisar_oxigenio, analisar_estabilidade,
]


def _seed_inicial():
    if CicloTelemetria.query.count() == 0:
        for i, v in enumerate(DADOS_INICIAIS):
            risco, evac, ia, _ = processar_linha(v, i + 1)
            db.session.add(CicloTelemetria(
                ciclo=i + 1, temperatura=v[0], comunicacao=v[1],
                bateria_solar=v[2], consumo_o2=v[3], matriz=v[4],
                risco=risco, classificacao=classificar_missao(risco),
                alerta_evacuacao=evac, ia_insight=ia,
            ))
        db.session.commit()


def _fmt_ciclo(c):
    vals = [c.temperatura, c.comunicacao, c.bateria_solar, c.consumo_o2, c.matriz]
    return {
        "id": c.id, "ciclo": c.ciclo, "valores": vals,
        "risco": c.risco, "alertas": [fn(vals[i])[1] for i, fn in enumerate(_ANALISADORES)],
        "ia_insight": c.ia_insight, "timestamp": c.timestamp.strftime("%H:%M:%S"),
        "alerta_evacuacao": c.alerta_evacuacao,
        "classificacao": c.classificacao or classificar_missao(c.risco),
        "justificativa": justificar_classificacao(vals),
        "anomalias": sum(1 for i, fn in enumerate(_ANALISADORES) if fn(vals[i])[0] >= 1),
    }


def _consolidado(ciclos):
    n = len(ciclos)
    if n == 0:
        return {"medias": {}, "tendencia": "—", "area_mais_afetada": "—"}
    somas = [0.0] * 5
    pontos = [0] * 5
    for c in ciclos:
        vals = [c.temperatura, c.comunicacao, c.bateria_solar, c.consumo_o2, c.matriz]
        for i, x in enumerate(vals):
            somas[i] += x
            pontos[i] += _ANALISADORES[i](x)[0]
    medias = {AREAS[i]: round(somas[i] / n, 2) for i in range(5)}
    r0, rn = ciclos[0].risco, ciclos[-1].risco
    tendencia = (
        "DEGRADAÇÃO (O risco aumentou ao longo da missão)" if rn > r0 else
        "RECUPERAÇÃO/ESTABILIZAÇÃO (O sistema está retornando ao equilíbrio)" if rn < r0 else
        "ESTÁVEL (O nível de risco permaneceu constante)"
    )
    return {"medias": medias, "tendencia": tendencia, "area_mais_afetada": AREAS[pontos.index(max(pontos))]}


def _proximo_ciclo():
    # MAX(ciclo)+1 — robusto a deleções e multi-worker (substitui count()+1).
    return (db.session.query(db.func.max(CicloTelemetria.ciclo)).scalar() or 0) + 1


def _matriz(ciclos):
    return [[c.temperatura, c.comunicacao, c.bateria_solar, c.consumo_o2, c.matriz] for c in ciclos]


def _salvar_ciclo(v, proximo, com_ia=True):
    # com_ia=False usa análise rule-based (geração em lote, sem chamada Groq por ciclo).
    if com_ia:
        risco, evac, ia, alertas = processar_linha(v, proximo)
    else:
        risco, evac, ia, alertas = processar_linha_sem_ia(v)
    novo = CicloTelemetria(
        ciclo=proximo, temperatura=v[0], comunicacao=v[1],
        bateria_solar=v[2], consumo_o2=v[3], matriz=v[4],
        risco=risco, classificacao=classificar_missao(risco),
        alerta_evacuacao=evac, ia_insight=ia,
    )
    db.session.add(novo)
    db.session.commit()
    return novo, alertas, risco, evac, ia


# ── ROTAS ────────────────────────────────────────────────

@bp.route("/")
def index():
    _seed_inicial()
    ciclos_db = CicloTelemetria.query.order_by(CicloTelemetria.id).all()
    consolidado = _consolidado(ciclos_db)
    ciclos_fmt = [_fmt_ciclo(c) for c in ciclos_db]
    matriz = _matriz(ciclos_db)
    energetico = resumo_energetico(matriz)
    alertas_av = gerar_alertas_avancados(matriz)
    classificacoes = classificar_ciclos(matriz)
    tipos = tipo_evento_serie(matriz)
    for i, t in enumerate(tipos):
        ciclos_fmt[i]["tipo_evento"] = t
    diagnostico = diagnostico_variaveis(matriz[-1]) if matriz else []
    # Só reflete o estado do ciclo mais recente, não histórico
    alerta_evacuacao_global = ciclos_db[-1].alerta_evacuacao if ciclos_db else False
    return render_template(
        "index.html",
        ciclos=ciclos_fmt,
        consolidado=consolidado,
        missao=NOME_MISSAO,
        equipe=EQUIPE,
        alerta_evacuacao_global=alerta_evacuacao_global,
        energetico=energetico,
        alertas_avancados=alertas_av,
        classificacoes=classificacoes,
        diagnostico=diagnostico,
    )


@bp.route("/api/telemetria/novo", methods=["POST"])
def nova_telemetria():
    proximo = _proximo_ciclo()
    novo, alertas, risco, evac, ia = _salvar_ciclo(gerar_telemetria_simulada(), proximo)
    return jsonify({
        "id": novo.id, "ciclo": novo.ciclo,
        "valores": [novo.temperatura, novo.comunicacao, novo.bateria_solar, novo.consumo_o2, novo.matriz],
        "risco": risco, "alertas": alertas, "ia_insight": ia,
        "timestamp": novo.timestamp.strftime("%H:%M:%S"), "alerta_evacuacao": evac,
    })


def _num(x, default, lo, hi):
    # Parse seguro + clamp de range (validação server-side — TASK-003).
    try:
        val = float(x)
    except (TypeError, ValueError):
        val = default
    return max(lo, min(hi, val))


@bp.route("/api/telemetria/manual", methods=["POST"])
def telemetria_manual():
    d = request.get_json(force=True)
    v = [
        _num(d.get("temperatura"), 24, 0, 60),
        _num(d.get("comunicacao"), 80, 0, 100),
        _num(d.get("bateria_solar"), 70, 0, 100),
        _num(d.get("consumo_o2"), 8.5, 0, 25),
        _num(d.get("matriz"), 85, 0, 100),
    ]
    proximo = _proximo_ciclo()
    novo, alertas, risco, evac, ia = _salvar_ciclo(v, proximo)
    return jsonify({
        "id": novo.id, "ciclo": novo.ciclo, "valores": v,
        "risco": risco, "alertas": alertas, "ia_insight": ia,
        "timestamp": novo.timestamp.strftime("%H:%M:%S"), "alerta_evacuacao": evac,
    })


@bp.route("/api/copiloto")
def copiloto():
    ultimo = CicloTelemetria.query.order_by(CicloTelemetria.id.desc()).first()
    if not ultimo:
        return jsonify({"sugestao": "Aguardando dados de telemetria.", "risco": 0, "ciclo": 0})
    return jsonify({
        "sugestao": gerar_sugestao_copiloto(ultimo),
        "risco": ultimo.risco, "ciclo": ultimo.ciclo,
        "alerta_evacuacao": ultimo.alerta_evacuacao,
    })


@bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    pergunta = data.get("mensagem", "").strip()
    if not pergunta:
        return jsonify({"erro": "Mensagem vazia"}), 400
    historico = MensagemChat.query.order_by(MensagemChat.id).all()
    resposta = obter_resposta_chat(historico, pergunta)
    db.session.add(MensagemChat(role="user", content=pergunta))
    db.session.add(MensagemChat(role="assistant", content=resposta))
    db.session.commit()
    return jsonify({"resposta": resposta})


@bp.route("/api/chat/historico")
def historico_chat():
    msgs = MensagemChat.query.order_by(MensagemChat.id).all()
    return jsonify([{"role": m.role, "content": m.content} for m in msgs])


@bp.route("/api/estatisticas")
def estatisticas():
    ciclos_db = CicloTelemetria.query.order_by(CicloTelemetria.id).all()
    if not ciclos_db:
        return jsonify({})

    campos = ["temperatura", "comunicacao", "bateria_solar", "consumo_o2", "matriz"]
    labels = ["Temperatura (°C)", "Comunicação (%)", "Bateria Solar (%)", "Consumo O2 (L/min)", "Matriz (%)"]
    resultado = {}

    for i, campo in enumerate(campos):
        valores = sorted([getattr(c, campo) for c in ciclos_db])
        n = len(valores)
        media = round(sum(valores) / n, 2)
        mediana = round(valores[n // 2] if n % 2 else (valores[n // 2 - 1] + valores[n // 2]) / 2, 2)
        variancia = round(sum((x - media) ** 2 for x in valores) / n, 2)
        desvio = round(variancia ** 0.5, 2)
        cv = round((desvio / media * 100) if media else 0, 1)
        q1 = round(valores[n // 4], 2)
        q3 = round(valores[3 * n // 4], 2)
        resultado[campo] = {
            "label": labels[i],
            "media": media,
            "mediana": mediana,
            "minimo": round(min(valores), 2),
            "maximo": round(max(valores), 2),
            "amplitude": round(max(valores) - min(valores), 2),
            "variancia": variancia,
            "desvio_padrao": desvio,
            "coef_variacao": cv,
            "q1": q1,
            "q3": q3,
            "n": n,
        }
    return jsonify(resultado)


@bp.route("/api/simulacao/gerar", methods=["POST"])
def gerar_simulacao():
    d = request.get_json(force=True)
    n = int(d.get("n_ciclos", 6))
    perfil = d.get("perfil", "estavel")
    try:
        seed = int(d.get("seed"))
    except (TypeError, ValueError):
        seed = None
    eventos = d.get("eventos") or None

    matriz = gerar_dados_missao(n, perfil, seed=seed, eventos=eventos)
    proximo = _proximo_ciclo()
    novos = []
    for i, v in enumerate(matriz):
        novo, *_ = _salvar_ciclo(v, proximo + i, com_ia=False)
        novos.append(_fmt_ciclo(novo))
    tipos = tipo_evento_serie(matriz)
    for i, t in enumerate(tipos):
        novos[i]["tipo_evento"] = t

    energia = resumo_energetico(matriz)
    return jsonify({
        "ciclos": novos,
        "perfil": _norm_perfil(perfil),
        "n_ciclos": len(matriz),
        "seed": seed,
        "energetico": energia,
        "alertas": gerar_alertas_avancados(matriz),
        "classificacoes": classificar_ciclos(matriz),
        "narrativa": gerar_narrativa_missao(matriz, energia),
    })


@bp.route("/api/energetico")
def energetico_endpoint():
    ciclos = CicloTelemetria.query.order_by(CicloTelemetria.id).all()
    matriz = _matriz(ciclos)
    por_ciclo = [
        dict(ciclo=ciclos[i].ciclo, **calcular_metricas_energeticas(linha))
        for i, linha in enumerate(matriz)
    ]
    return jsonify({"resumo": resumo_energetico(matriz), "por_ciclo": por_ciclo})


@bp.route("/api/alertas")
def alertas_endpoint():
    ciclos = CicloTelemetria.query.order_by(CicloTelemetria.id).all()
    matriz = _matriz(ciclos)
    tags = classificar_ciclos(matriz)
    tipos = tipo_evento_serie(matriz)
    return jsonify({
        "alertas": gerar_alertas_avancados(matriz),
        "classificacoes": [
            {
                "ciclo": ciclos[i].ciclo, "tags": tags[i], "tipo_evento": tipos[i],
                "pontuacao": ciclos[i].risco,
                "classificacao": ciclos[i].classificacao or classificar_missao(ciclos[i].risco),
            }
            for i in range(len(matriz))
        ],
    })


@bp.route("/api/diagnostico")
def diagnostico_endpoint():
    ultimo = CicloTelemetria.query.order_by(CicloTelemetria.id.desc()).first()
    if not ultimo:
        return jsonify({"ciclo": 0, "variaveis": [], "energetico": {}})
    vals = [ultimo.temperatura, ultimo.comunicacao, ultimo.bateria_solar, ultimo.consumo_o2, ultimo.matriz]
    return jsonify({
        "ciclo": ultimo.ciclo,
        "classificacao": ultimo.classificacao or classificar_missao(ultimo.risco),
        "risco": ultimo.risco,
        "variaveis": diagnostico_variaveis(vals),
        "energetico": calcular_metricas_energeticas(vals),
    })


@bp.route("/api/relatorio")
def relatorio_endpoint():
    ciclos = CicloTelemetria.query.order_by(CicloTelemetria.id).all()
    txt = gerar_relatorio_txt(_matriz(ciclos), NOME_MISSAO, EQUIPE)
    return Response(
        txt, mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=relatorio_missao.txt"},
    )
