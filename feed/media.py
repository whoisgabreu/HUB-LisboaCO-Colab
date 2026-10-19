"""Armazenamento e processamento das imagens do Feed.

Imagens são convertidas para WebP (leves, sem EXIF) e gravadas em
``static/images/feed/AAAA/MM/``. Servidas publicamente pelo Flask.
"""

import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

from PIL import Image, ImageOps

MAX_IMAGENS = 4
MAX_BYTES = 5 * 1024 * 1024
MAX_DIMENSAO = 1600
QUALIDADE_WEBP = 82

MEDIA_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "images", "feed",
)

_ARQUIVO_RE = re.compile(r"^\d{4}/\d{2}/[a-f0-9]{32}\.webp$")


def _preparar_raiz() -> None:
    os.makedirs(MEDIA_ROOT, exist_ok=True)


def url_publica(arquivo: str) -> str:
    """URL pública de uma imagem armazenada."""
    return "/static/images/feed/" + str(arquivo or "").replace("\\", "/").lstrip("/")


def _caminho_absoluto(arquivo: str) -> str | None:
    """Resolve um caminho armazenado, garantindo que fique dentro de MEDIA_ROOT."""
    if not _ARQUIVO_RE.match(str(arquivo or "")):
        return None
    caminho = os.path.abspath(os.path.join(MEDIA_ROOT, arquivo))
    raiz = os.path.abspath(MEDIA_ROOT)
    if os.path.commonpath([raiz, caminho]) != raiz:
        return None
    return caminho


def _tamanho_stream(stream) -> int:
    try:
        stream.seek(0, os.SEEK_END)
        tamanho = stream.tell()
        stream.seek(0)
        return tamanho
    except Exception:
        return 0


def processar_imagem(file_storage) -> Dict[str, Any]:
    """Valida, converte para WebP e grava uma imagem.

    Retorna ``{arquivo, largura, altura}``.
    """
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise ValueError("Nenhuma imagem enviada.")

    stream = file_storage.stream
    if _tamanho_stream(stream) > MAX_BYTES:
        raise ValueError("Cada imagem deve ter no máximo 5MB.")
    stream.seek(0)

    try:
        imagem = Image.open(stream)
        imagem.load()
        imagem = ImageOps.exif_transpose(imagem)
    except Exception:
        raise ValueError("Arquivo inválido: envie uma imagem (JPG, PNG, WebP...).")

    if imagem.width < 1 or imagem.height < 1:
        raise ValueError("Imagem inválida.")

    # Preserva transparência quando existir; senão, RGB.
    if imagem.mode in ("RGBA", "LA") or (
        imagem.mode == "P" and "transparency" in imagem.info
    ):
        imagem = imagem.convert("RGBA")
    else:
        imagem = imagem.convert("RGB")

    imagem.thumbnail((MAX_DIMENSAO, MAX_DIMENSAO), Image.Resampling.LANCZOS)
    largura, altura = imagem.size

    agora = datetime.now()
    subdir = f"{agora.year:04d}/{agora.month:02d}"
    destino_dir = os.path.join(MEDIA_ROOT, agora.strftime("%Y"), f"{agora.month:02d}")
    os.makedirs(destino_dir, exist_ok=True)

    nome = f"{uuid.uuid4().hex}.webp"
    caminho = os.path.join(destino_dir, nome)
    imagem.save(caminho, "WEBP", quality=QUALIDADE_WEBP, method=4)

    return {
        "arquivo": f"{subdir}/{nome}",
        "largura": int(largura),
        "altura": int(altura),
    }


def processar_upload(files) -> List[Dict[str, Any]]:
    """Processa uma lista de arquivos, respeitando o limite de imagens."""
    arquivos = [f for f in (files or []) if getattr(f, "filename", "")]
    if not arquivos:
        raise ValueError("Nenhuma imagem enviada.")
    if len(arquivos) > MAX_IMAGENS:
        raise ValueError(f"Envie no máximo {MAX_IMAGENS} imagens por publicação.")

    _preparar_raiz()
    return [processar_imagem(f) for f in arquivos]


def normalizar_referencias(itens) -> List[Dict[str, Any]]:
    """Valida as referências enviadas na criação do post.

    Aceita lista de dicts ``{arquivo, largura, altura}`` ou de strings.
    """
    if itens is None:
        return []
    if not isinstance(itens, list):
        raise ValueError("Formato de imagens inválido.")
    if len(itens) > MAX_IMAGENS:
        raise ValueError(f"Envie no máximo {MAX_IMAGENS} imagens por publicação.")

    normalizados: List[Dict[str, Any]] = []
    for item in itens:
        if isinstance(item, dict):
            arquivo = item.get("arquivo")
            largura = item.get("largura")
            altura = item.get("altura")
        else:
            arquivo = item
            largura = altura = None

        caminho = _caminho_absoluto(arquivo)
        if not caminho or not os.path.exists(caminho):
            raise ValueError("Imagem não encontrada. Envie a imagem novamente.")

        normalizados.append({
            "arquivo": arquivo,
            "largura": int(largura) if largura else None,
            "altura": int(altura) if altura else None,
        })
    return normalizados


def serializar_imagens(itens) -> List[Dict[str, Any]]:
    """Formata as imagens para o JSON consumido pelo frontend."""
    saida = []
    for item in (itens or []):
        arquivo = item.get("arquivo") if isinstance(item, dict) else item
        if not arquivo:
            continue
        caminho = _caminho_absoluto(arquivo)
        if not caminho or not os.path.exists(caminho):
            continue
        saida.append({
            "arquivo": arquivo,
            "url": url_publica(arquivo),
            "largura": (item.get("largura") if isinstance(item, dict) else None),
            "altura": (item.get("altura") if isinstance(item, dict) else None),
        })
    return saida


def remover_imagens(itens) -> None:
    """Remove os arquivos físicos de uma lista de imagens (ignora ausentes)."""
    for item in (itens or []):
        arquivo = item.get("arquivo") if isinstance(item, dict) else item
        caminho = _caminho_absoluto(arquivo)
        if not caminho:
            continue
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except Exception:
            pass