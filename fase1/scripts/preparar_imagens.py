"""Monta a base visual da Parte 3: 120 imagens de ECG de 12 derivações.

Fonte: "ECG Images dataset of Cardiac Patients", Khan & Hussain, Mendeley Data,
DOI 10.17632/gwbz3fsgp8.2 — licença CC BY 4.0 (redistribuição permitida com
atribuição, verificada em 2026-08-31). 928 imagens, coletadas no Ch. Pervaiz
Elahi Institute of Cardiology (Multan, Paquistão) com aparelho EDAN SERIES-3.

Amostra BALANCEADA de 30 por classe em vez de proporcional: o dataset de origem
é desbalanceado (Normal 284, MI 239, HB 233, PMI 172) e balancear a amostra já
mitiga viés de classe nas fases de treino. Decisão registrada em docs/VIESES.md.

A origem também tem duplicatas byte-a-byte sob nomes de arquivo diferentes —
verificado via content_details.sha256_hash da própria API: contando conteúdo
único por classe, são HB 233/233, MI só 30/239 (!), Normal 142/284 e
PMI 86/172. Por isso a seleção deduplica por hash de conteúdo antes de
sortear; para MI/infarto isso significa que a amostra de 30 é exatamente o
total de imagens únicas existentes — não sobra folga.

Normalização: JPEG qualidade 85, lado maior 1024px. Preserva a legibilidade do
traçado e mantém o repositório clonável (20,8 MB em vez de 615 MB).
"""
from __future__ import annotations

import csv
import random
import re

import requests
from PIL import Image

import comum

API = "https://data.mendeley.com/public-api/datasets/gwbz3fsgp8"
POR_CLASSE = 30
LADO_MAXIMO = 1024
QUALIDADE = 85

# Prefixo do nome de arquivo na origem -> nome da classe em português.
PREFIXO_PARA_CLASSE = {
    "Normal": "normal",
    "MI": "infarto",
    "PMI": "historico_infarto",
    "HB": "arritmia",
}


def listar_origem() -> list[dict]:
    resposta = requests.get(API, headers=comum.CABECALHOS, timeout=90)
    resposta.raise_for_status()
    return resposta.json()["files"]


def classe_de(nome_arquivo: str) -> str | None:
    prefixo = re.match(r"^[A-Za-z]+", nome_arquivo)
    if not prefixo:
        return None
    return PREFIXO_PARA_CLASSE.get(prefixo.group(0))


def selecionar(arquivos: list[dict]) -> dict[str, list[dict]]:
    por_classe: dict[str, list[dict]] = {c: [] for c in PREFIXO_PARA_CLASSE.values()}
    for arquivo in arquivos:
        classe = classe_de(arquivo["filename"])
        if classe:
            por_classe[classe].append(arquivo)

    rng = random.Random(comum.SEED)
    selecionados = {}
    for classe, lista in por_classe.items():
        # Ordenar antes de deduplicar/sortear: a ordem da API não é garantida,
        # a seed sozinha não basta para reprodutibilidade.
        lista.sort(key=lambda a: a["filename"])

        # A origem tem duplicatas byte-a-byte sob nomes de arquivo diferentes
        # (ex.: MI(79).jpg e MI(109).jpg são o mesmo conteúdo). Deduplicar pelo
        # hash do conteúdo antes de sortear evita que a amostra final tenha
        # imagens repetidas — o que vazaria entre treino/teste nas fases
        # seguintes e infla métricas de forma artificial.
        vistos: set[str] = set()
        unicos = []
        for arquivo in lista:
            hash_origem = arquivo["content_details"]["sha256_hash"]
            if hash_origem not in vistos:
                vistos.add(hash_origem)
                unicos.append(arquivo)

        if len(unicos) < POR_CLASSE:
            raise SystemExit(
                f"classe {classe} tem só {len(unicos)} imagens únicas na origem"
            )
        selecionados[classe] = rng.sample(unicos, POR_CLASSE)
    return selecionados


def normalizar(origem, destino) -> tuple[int, int]:
    with Image.open(origem) as img:
        img = img.convert("RGB")
        img.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
        img.save(destino, "JPEG", quality=QUALIDADE, optimize=True)
        return img.size


def main() -> None:
    dir_img = comum.RAIZ / "assets" / "imagens"
    dir_tmp = comum.RAIZ / "data" / "tmp" / "ecg"
    dir_img.mkdir(parents=True, exist_ok=True)

    selecionados = selecionar(listar_origem())
    linhas = []

    for classe in sorted(selecionados):
        for i, arquivo in enumerate(selecionados[classe], start=1):
            nome_origem = arquivo["filename"]
            url = arquivo["content_details"]["download_url"]
            bruto = comum.baixar(url, dir_tmp / nome_origem, timeout=120)

            nome_final = f"{classe}_{i:03d}.jpg"
            destino = dir_img / nome_final
            largura, altura = normalizar(bruto, destino)

            linhas.append({
                "arquivo": nome_final,
                "classe": classe,
                "arquivo_origem": nome_origem,
                "url_origem": url,
                "sha256": comum.sha256_arquivo(destino),
                "largura": largura,
                "altura": altura,
                "bytes": destino.stat().st_size,
            })
            print(f"  {nome_final}  <- {nome_origem}")

    with open(dir_img / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)

    total_mb = sum(linha["bytes"] for linha in linhas) / 1e6
    print(f"{len(linhas)} imagens, {total_mb:.1f} MB, manifest escrito")


if __name__ == "__main__":
    main()
