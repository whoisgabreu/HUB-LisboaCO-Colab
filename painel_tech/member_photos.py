"""Armazenamento isolado de fotos dos membros do Painel TECH.

As fotos seguem a convenção já usada pelo HUB
``static/images/profile_pictures/<email>.png``. Este módulo não altera banco,
models ou services.
"""

from __future__ import annotations

import io
import os
import re
import tempfile
import unicodedata
import warnings
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_INPUT_DIMENSION = 4096
MAX_INPUT_PIXELS = 16_000_000
MAX_OUTPUT_DIMENSION = 1024
FORMATOS_ACEITOS = {"JPEG", "PNG", "WEBP"}

_EMAIL_SEGURO = re.compile(
    r"[a-z0-9][a-z0-9._%+\-]*@[a-z0-9](?:[a-z0-9.\-]*[a-z0-9])?\.[a-z]{2,63}"
)
_PROFILE_DIR = (
    Path(__file__).resolve().parent.parent / "static" / "images" / "profile_pictures"
)


class FotoMembroInvalida(ValueError):
    """Erro seguro para ser apresentado na interface de configurações."""


def normalizar_email(email: str | None) -> str:
    normalizado = unicodedata.normalize("NFKC", email or "").strip().lower()
    if len(normalizado) > 254 or not _EMAIL_SEGURO.fullmatch(normalizado):
        raise FotoMembroInvalida("Este membro não possui um e-mail válido para associar a foto.")
    return normalizado


def caminho_foto(email: str | None) -> Path:
    nome = f"{normalizar_email(email)}.png"
    pasta = _PROFILE_DIR.resolve()
    destino = (pasta / nome).resolve()
    if destino.parent != pasta:
        raise FotoMembroInvalida("Não foi possível determinar um destino seguro para a foto.")
    return destino


def foto_url(email: str | None) -> str | None:
    """Retorna a foto padronizada com cache-busting, quando ela existe."""
    try:
        caminho = caminho_foto(email)
        if not caminho.is_file():
            return None
        versao = caminho.stat().st_mtime_ns
    except (FotoMembroInvalida, OSError):
        return None
    nome = quote(caminho.name)
    return f"/static/images/profile_pictures/{nome}?v={versao}"


def _ler_upload(arquivo) -> bytes:
    if arquivo is None or not getattr(arquivo, "filename", ""):
        raise FotoMembroInvalida("Selecione uma imagem antes de enviar.")

    conteudo = arquivo.stream.read(MAX_UPLOAD_BYTES + 1)
    if not conteudo:
        raise FotoMembroInvalida("A imagem enviada está vazia.")
    if len(conteudo) > MAX_UPLOAD_BYTES:
        raise FotoMembroInvalida("A imagem deve ter no máximo 2 MB.")
    return conteudo


def _normalizar_png(conteudo: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(conteudo)) as verificacao:
                formato = (verificacao.format or "").upper()
                largura, altura = verificacao.size
                animada = getattr(verificacao, "n_frames", 1) > 1
                verificacao.verify()

            if formato not in FORMATOS_ACEITOS:
                raise FotoMembroInvalida("Use uma imagem PNG, JPG ou WEBP.")
            if animada:
                raise FotoMembroInvalida("Imagens animadas não são aceitas.")
            if (
                largura <= 0
                or altura <= 0
                or largura > MAX_INPUT_DIMENSION
                or altura > MAX_INPUT_DIMENSION
                or largura * altura > MAX_INPUT_PIXELS
            ):
                raise FotoMembroInvalida(
                    "A imagem possui dimensões muito grandes. Use até 4096×4096 px."
                )

            with Image.open(io.BytesIO(conteudo)) as origem:
                imagem = ImageOps.exif_transpose(origem)
                tem_alpha = imagem.mode in ("RGBA", "LA") or (
                    imagem.mode == "P" and "transparency" in imagem.info
                )
                imagem = imagem.convert("RGBA" if tem_alpha else "RGB")
                imagem.thumbnail(
                    (MAX_OUTPUT_DIMENSION, MAX_OUTPUT_DIMENSION),
                    Image.Resampling.LANCZOS,
                )
                saida = io.BytesIO()
                imagem.save(saida, format="PNG", optimize=True, compress_level=8)
                return saida.getvalue()
    except FotoMembroInvalida:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as erro:
        raise FotoMembroInvalida("O arquivo enviado não é uma imagem válida.") from erro


def _gravar_atomicamente(destino: Path, conteudo: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".tech-avatar-",
            suffix=".tmp",
            dir=destino.parent,
            delete=False,
        ) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, destino)
        temporario = None
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def salvar_foto(email: str | None, arquivo) -> Path:
    """Valida, normaliza e salva a foto do membro como PNG."""
    destino = caminho_foto(email)
    conteudo = _ler_upload(arquivo)
    png = _normalizar_png(conteudo)
    try:
        _gravar_atomicamente(destino, png)
    except OSError as erro:
        raise FotoMembroInvalida("Não foi possível salvar a foto agora.") from erro
    return destino
