"""API REST do CardioIA (Flask + SQLite).

Recebe as leituras do vestível, aplica a verificação de risco, guarda tudo e
dispara o e-mail de alerta. Rotas (todas em JSON):

    GET  /api/v1/saude                       verifica se a API está no ar (sem chave)
    POST /api/v1/leituras                    envia uma leitura          (201 / 200 se repetida)
    GET  /api/v1/leituras?paciente=&limite=  últimas leituras
    GET  /api/v1/alertas?paciente=&limite=   alertas gerados e status do e-mail
    GET  /api/v1/pacientes/<id>/status       situação atual do paciente

As rotas protegidas exigem o cabeçalho ``X-API-Key`` (variável CARDIOIA_API_KEY).

Uso: ``python api.py`` (sobe em http://127.0.0.1:5050)
"""

import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request

import notificador
from risco import JANELA_IMOVEL, avaliar

PASTA = Path(__file__).resolve().parent
BANCO_PADRAO = PASTA / "cardioia.db"
CHAVE_PADRAO = "cardioia-demo"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS leituras (
    id          INTEGER PRIMARY KEY,
    paciente    TEXT    NOT NULL,
    seq         INTEGER NOT NULL,
    ts          INTEGER NOT NULL,
    temp        REAL    NOT NULL,
    umid        REAL    NOT NULL,
    bpm         INTEGER NOT NULL,
    acel        REAL    NOT NULL,
    movimento   TEXT    NOT NULL,
    motivos     TEXT    NOT NULL,          -- lista JSON, vazia = normal
    severidade  TEXT    NOT NULL,
    UNIQUE (paciente, ts, seq)             -- reenvio da mesma leitura não duplica
);
CREATE TABLE IF NOT EXISTS alertas (
    id            INTEGER PRIMARY KEY,
    leitura_id    INTEGER NOT NULL REFERENCES leituras(id),
    paciente      TEXT    NOT NULL,
    ts            INTEGER NOT NULL,
    motivos       TEXT    NOT NULL,
    novos         TEXT    NOT NULL,
    severidade    TEXT    NOT NULL,
    email_status  TEXT    NOT NULL,        -- enviado | falhou
    email_destino TEXT
);
"""

# campo: (tipo aceito, mínimo, máximo)
CAMPOS = {
    "paciente": (str, None, None),
    "seq": (int, 0, None),
    "ts": (int, 1, None),
    "temp": ((int, float), 20, 45),
    "umid": ((int, float), 0, 100),
    "bpm": (int, 0, 300),
    "acel": ((int, float), 0, 16),
}


def validar(dados) -> list[str]:
    if not isinstance(dados, dict):
        return ["o corpo precisa ser um objeto JSON"]
    erros = []
    for campo, (tipo, minimo, maximo) in CAMPOS.items():
        valor = dados.get(campo)
        if valor is None:
            erros.append(f"{campo}: obrigatório")
        elif isinstance(valor, bool) or not isinstance(valor, tipo):
            erros.append(f"{campo}: tipo inválido")
        elif tipo is str and not valor.strip():
            erros.append(f"{campo}: vazio")
        elif minimo is not None and valor < minimo or maximo is not None and valor > maximo:
            erros.append(f"{campo}: fora da faixa [{minimo}, {maximo}]")
    return erros


def linha_para_dict(linha: sqlite3.Row) -> dict:
    d = dict(linha)
    for campo in ("motivos", "novos"):
        if campo in d:
            d[campo] = json.loads(d[campo])
    if "motivos" in d and "movimento" in d:
        d["alerta"] = bool(d["motivos"])
    return d


def create_app(banco: Path | str = BANCO_PADRAO, chave: str | None = None, enviar_email=None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    chave = chave or os.getenv("CARDIOIA_API_KEY", CHAVE_PADRAO)
    enviar_email = enviar_email or notificador.enviar

    def db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(banco)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def fechar(_):
        conexao = g.pop("db", None)
        if conexao is not None:
            conexao.close()

    with sqlite3.connect(banco) as conexao:
        conexao.executescript(ESQUEMA)

    @app.before_request
    def autenticar():
        if request.path != "/api/v1/saude" and request.headers.get("X-API-Key") != chave:
            return jsonify(erro="chave de API ausente ou inválida"), 401

    @app.errorhandler(404)
    def nao_encontrado(_):
        return jsonify(erro="rota não encontrada"), 404

    @app.get("/api/v1/saude")
    def saude():
        return jsonify(status="ok")

    @app.post("/api/v1/leituras")
    def receber_leitura():
        dados = request.get_json(silent=True)
        erros = validar(dados)
        if erros:
            return jsonify(erro="leitura inválida", detalhes=erros), 400
        leitura = {campo: dados[campo] for campo in CAMPOS}

        repetida = db().execute(
            "SELECT * FROM leituras WHERE paciente = ? AND ts = ? AND seq = ?",
            (leitura["paciente"], leitura["ts"], leitura["seq"]),
        ).fetchone()
        if repetida:
            return jsonify(leitura=linha_para_dict(repetida), repetida=True, email=None), 200

        # Histórico do paciente antes desta leitura (mais recente primeiro).
        anteriores = db().execute(
            "SELECT acel, motivos FROM leituras WHERE paciente = ? AND ts < ? "
            "ORDER BY ts DESC, seq DESC LIMIT ?",
            (leitura["paciente"], leitura["ts"], JANELA_IMOVEL - 1),
        ).fetchall()
        risco = avaliar(leitura, [a["acel"] for a in anteriores])

        cursor = db().execute(
            "INSERT INTO leituras (paciente, seq, ts, temp, umid, bpm, acel, movimento, motivos, severidade) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*leitura.values(), risco.movimento, json.dumps(risco.motivos), risco.severidade),
        )
        leitura_id = cursor.lastrowid

        # Só manda e-mail quando aparece um motivo que a leitura anterior não
        # tinha. Enquanto o mesmo alerta continua, a enfermagem não é inundada.
        motivos_antes = json.loads(anteriores[0]["motivos"]) if anteriores else []
        novos = [m for m in risco.motivos if m not in motivos_antes]
        email = None
        if novos:
            try:
                destino = enviar_email(notificador.montar_email(leitura, risco, novos))
                email = {"status": "enviado", "destino": destino}
            except Exception as exc:  # a leitura não pode se perder por falha no e-mail
                app.logger.error("falha ao enviar e-mail: %s", exc)
                email = {"status": "falhou", "destino": None}
            db().execute(
                "INSERT INTO alertas (leitura_id, paciente, ts, motivos, novos, severidade, email_status, email_destino) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (leitura_id, leitura["paciente"], leitura["ts"], json.dumps(risco.motivos),
                 json.dumps(novos), risco.severidade, email["status"], email["destino"]),
            )
        db().commit()

        resposta = {
            **leitura,
            "id": leitura_id,
            "movimento": risco.movimento,
            "alerta": risco.alerta,
            "motivos": risco.motivos,
            "severidade": risco.severidade,
        }
        return jsonify(leitura=resposta, repetida=False, email=email), 201

    def filtro_paciente_e_limite():
        paciente = request.args.get("paciente")
        try:
            limite = max(1, min(int(request.args.get("limite", 20)), 500))
        except ValueError:
            limite = 20
        onde, params = ("WHERE paciente = ?", [paciente]) if paciente else ("", [])
        return onde, params, limite

    @app.get("/api/v1/leituras")
    def listar_leituras():
        onde, params, limite = filtro_paciente_e_limite()
        linhas = db().execute(
            f"SELECT * FROM leituras {onde} ORDER BY ts DESC, seq DESC LIMIT ?", (*params, limite)
        ).fetchall()
        return jsonify(leituras=[linha_para_dict(l) for l in linhas])

    @app.get("/api/v1/alertas")
    def listar_alertas():
        onde, params, limite = filtro_paciente_e_limite()
        linhas = db().execute(
            f"SELECT * FROM alertas {onde} ORDER BY ts DESC, id DESC LIMIT ?", (*params, limite)
        ).fetchall()
        return jsonify(alertas=[linha_para_dict(l) for l in linhas])

    @app.get("/api/v1/pacientes/<paciente>/status")
    def status_paciente(paciente):
        ultima = db().execute(
            "SELECT * FROM leituras WHERE paciente = ? ORDER BY ts DESC, seq DESC LIMIT 1", (paciente,)
        ).fetchone()
        if ultima is None:
            return jsonify(erro=f"paciente {paciente} sem leituras"), 404
        total_alertas = db().execute(
            "SELECT COUNT(*) FROM alertas WHERE paciente = ?", (paciente,)
        ).fetchone()[0]
        return jsonify(paciente=paciente, ultima_leitura=linha_para_dict(ultima), alertas_enviados=total_alertas)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORTA", "5050")))
