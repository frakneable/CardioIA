import json
import pathlib
import re

DIR = pathlib.Path(__file__).resolve().parents[1] / "parte1"
SKETCH = (DIR / "sketch.ino").read_text(encoding="utf-8")
DIAGRAMA = json.loads((DIR / "diagram.json").read_text(encoding="utf-8"))


def _pino(nome):
    return re.search(rf"#define {nome}\s+(\d+)", SKETCH).group(1)


def _ligado(parte, pino_parte, pino_esp):
    pares = {frozenset((a, b)) for a, b, *_ in DIAGRAMA["connections"]}
    return frozenset((f"{parte}:{pino_parte}", f"esp:{pino_esp}")) in pares


def test_dois_sensores_distintos_com_dht22_obrigatorio():
    tipos = {p["type"] for p in DIAGRAMA["parts"]}
    assert "wokwi-dht22" in tipos
    assert {"wokwi-mpu6050", "wokwi-potentiometer"} <= tipos


def test_pinos_do_codigo_batem_com_o_circuito():
    assert _ligado("dht1", "SDA", _pino("PINO_DHT"))
    assert _ligado("pot1", "SIG", _pino("PINO_PULSO"))
    assert _ligado("sw1", "2", _pino("PINO_WIFI"))
    assert _ligado("imu1", "SDA", "21") and _ligado("imu1", "SCL", "22")


def test_bibliotecas_incluidas_estao_no_libraries_txt():
    libs = (DIR / "libraries.txt").read_text(encoding="utf-8")
    for include, lib in (("DHT.h", "DHT sensor library"), ("Adafruit_MPU6050.h", "Adafruit MPU6050")):
        assert f"#include <{include}>" in SKETCH and lib in libs


def test_capacidade_de_producao_cobre_24h_offline():
    intervalo_ms = int(re.search(r"#else\s+const unsigned long INTERVALO_LEITURA_MS = (\d+);", SKETCH).group(1))
    limite = int(re.search(r"#else[\s\S]*?LIMITE_REGISTROS = (\d+);", SKETCH).group(1))
    assert limite * intervalo_ms / 1000 >= 24 * 3600


def test_relatorio_tem_pelo_menos_uma_pagina():
    relatorio = (DIR / "RELATORIO.md").read_text(encoding="utf-8")
    assert len(relatorio.split()) >= 500
    for secao in ("Fluxo de funcionamento", "resiliência", "armazenamento limitado"):
        assert secao.lower() in relatorio.lower()


def test_tabela_de_particoes_tem_area_para_o_spiffs():
    linhas = (DIR / "partitions.csv").read_text(encoding="utf-8").splitlines()
    spiffs = [l.split(",") for l in linhas if l.startswith("spiffs")]
    assert spiffs and int(spiffs[0][4], 16) >= 1024 * 1024
