"""Utilitários compartilhados pelos scripts de preparação de dados da Fase 1."""
from __future__ import annotations

import hashlib
import pathlib

import requests

SEED = 42
RAIZ = pathlib.Path(__file__).resolve().parents[1]

CABECALHOS = {"User-Agent": "CardioIA-FIAP/1.0 (projeto academico)"}


def baixar(url: str, destino: pathlib.Path, *, timeout: int = 60) -> pathlib.Path:
    """Baixa `url` para `destino`, criando diretórios. Idempotente: se o arquivo
    já existe e não está vazio, não baixa de novo."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    resposta = requests.get(url, headers=CABECALHOS, timeout=timeout)
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)
    return destino


def sha256_arquivo(caminho: pathlib.Path) -> str:
    """SHA-256 hexadecimal do conteúdo do arquivo."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()
