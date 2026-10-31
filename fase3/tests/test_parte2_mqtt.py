import json
import pathlib
import re

DIR = pathlib.Path(__file__).resolve().parents[1] / "parte2"
SKETCH = (DIR / "sketch.ino").read_text(encoding="utf-8")
DIAGRAMA = json.loads((DIR / "diagram.json").read_text(encoding="utf-8"))
FLUXO = json.loads((DIR / "node-red" / "flows.json").read_text(encoding="utf-8"))


def _pino(nome):
    return re.search(rf"#define {nome}\s+(\d+)", SKETCH).group(1)


def _ligado(parte, pino_parte, pino_esp):
    pares = {frozenset((a, b)) for a, b, *_ in DIAGRAMA["connections"]}
    return frozenset((f"{parte}:{pino_parte}", f"esp:{pino_esp}")) in pares


def _nos(tipo):
    return [n for n in FLUXO if n["type"] == tipo]


def test_botao_de_pulso_substitui_o_potenciometro():
    tipos = {p["type"] for p in DIAGRAMA["parts"]}
    assert "wokwi-pushbutton" in tipos and "wokwi-potentiometer" not in tipos
    assert _ligado("btn1", "1.r", _pino("PINO_PULSO"))
    assert "INPUT_PULLUP" in SKETCH and "attachInterrupt" in SKETCH


def test_dht22_e_conexao_ligados_aos_pinos_do_codigo():
    assert _ligado("dht1", "SDA", _pino("PINO_DHT"))
    assert _ligado("sw1", "2", _pino("PINO_CONEXAO"))


def test_node_red_assina_os_mesmos_topicos_que_o_esp32_publica():
    base = re.search(r'#define TOPICO_BASE "([^"]+)"', SKETCH).group(1)
    publicados = {base + "/" + t for t in ("vitais", "alerta", "status")}
    assinados = {n["topic"] for n in _nos("mqtt in")}
    assert assinados == publicados
    broker = _nos("mqtt-broker")[0]
    assert re.search(r'MQTT_BROKER = "([^"]+)"', SKETCH).group(1) == broker["broker"]


def test_dashboard_tem_grafico_gauge_e_indicador_de_alerta():
    assert len(_nos("ui-chart")) >= 1
    assert _nos("ui-gauge")[0]["units"] == "°C"
    alerta = next(n for n in _nos("ui-template") if "alerta" in n["name"].lower())
    assert "ALERTA" in alerta["format"] and "Sinais normais" in alerta["format"]


def test_faixa_de_febre_do_gauge_bate_com_o_limiar_do_esp32():
    febre = re.search(r"TEMP_FEBRE\s*=\s*([\d.]+)", SKETCH).group(1)
    faixas = {s["from"] for s in _nos("ui-gauge")[0]["segments"]}
    assert febre in faixas


def test_status_usa_last_will_e_retain():
    assert re.search(r'mqtt\.connect\([^)]*TOPICO_STATUS, 1, true, "offline"\)', SKETCH)
    assert 'mqtt.publish(TOPICO_STATUS, "online", true)' in SKETCH


def test_bibliotecas_e_particao_presentes():
    libs = (DIR / "libraries.txt").read_text(encoding="utf-8")
    assert "PubSubClient" in libs and "#include <PubSubClient.h>" in SKETCH
    assert "spiffs" in (DIR / "partitions.csv").read_text(encoding="utf-8")


def test_relatorio_tem_pelo_menos_duas_paginas():
    relatorio = (DIR / "RELATORIO.md").read_text(encoding="utf-8")
    assert len(relatorio.split()) >= 1100
    for secao in ("Fluxo de comunicação MQTT", "Configuração da dashboard"):
        assert secao in relatorio


def test_prints_da_entrega_existem():
    prints = {p.name for p in (DIR / "prints").glob("*.png")}
    assert {"01-dashboard-normal.png", "02-dashboard-alerta.png", "03-node-red-fluxo.png"} <= prints
