"""SPEC-130-C · F1 — as FOTOS e os PRÊMIOS da corretora. O único escritor dos dois.

O que a corretora sobe aqui vai à página que o SEGURADO abre (cotação, renovação, Quem Cobra Menos). Por isso:

* **os BYTES decidem o tipo** — nunca o nome do arquivo nem o cabeçalho do navegador. Só JPEG, PNG, WEBP e HEIC (a foto do
  iPhone) entram, e só depois de o Pillow abrir, conferir (`verify`) e reabrir. SVG, GIF, PDF, executável, HTML: recusados.
* **nenhum metadado sai daqui** — a foto de celular traz EXIF com o GPS de onde foi tirada (muitas vezes a casa de alguém
  da equipe). A orientação é aplicada nos pixels e o resto é DESCARTADO: a imagem gravada é uma cópia só de pixels.
* **a foto é reduzida no servidor** (≤ 1080 px no maior lado, WEBP ≤ 90 KB) e guardada como `data:` em
  `brand_assets.storage_ref` — o mesmo desenho do logo (`capture.py` `LOGO_TIPOS_ACEITOS`): a página do `/r/` já aceita
  `img-src data:` e nenhuma URL pública nova nasce (D-130C-03).
* **toda leitura e toda escrita filtram `company_id` no código** (CLAUDE.md §7): o backend usa service role e as tabelas têm
  RLS sem policy — a RLS não protege nada contra um filtro esquecido aqui. Um id de foto de outra corretora é "não
  encontrada", nunca uma escrita.

Contrato com F3 (`multicalculo/proposta.py`): `fotos_da_pagina` e `premios` — nunca levantam; erro ou ausência → `[]`.
"""

from __future__ import annotations

import base64
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.brand.capture import EntradaRecusada

logger = logging.getLogger(__name__)

# ======================================================================================================================
# os tetos — cada um com o porquê
# ======================================================================================================================

#: 8 fotos guardadas, 4 na página (SPEC §4). 8 dá para a corretora escolher sem a tela virar um álbum.
FOTOS_TETO = 8
#: a página mostra as 4 primeiras (o carrossel do bloco da corretora); F3 pode pedir menos.
FOTOS_NA_PAGINA = 4
#: 10 MB de ENTRADA: uma foto de celular moderno tem 3–6 MB (HEIC menos); acima disso é vídeo, PDF ou arquivo errado.
ENTRADA_TETO_BYTES = 10 * 1024 * 1024
#: a foto ocupa no máximo a largura de um celular deitado (1080 px); maior que isso só pesa a página.
LADO_MAXIMO_PX = 1080
#: 💭 90 KB por foto em WEBP (web.dev, "choose the right image format"): 4 fotos ≈ 360 KB embutidos no HTML da página do
#: segurado, abrindo no 4G. É um TETO de projeto, não uma medição — o número vem da SPEC §4.
SAIDA_TETO_BYTES = 90 * 1024
#: as qualidades tentadas, da melhor para a mais leve; abaixo de 50 o WEBP de foto de gente começa a mostrar bloco.
QUALIDADES_WEBP = (80, 72, 64, 56, 50)
#: se nem a qualidade 50 cabe, o lado encolhe nestes passos — mas nunca abaixo de 480 px (ainda nítida no celular).
LADO_MINIMO_PX = 480
#: o tamanho vem do CABEÇALHO antes de decodificar: um PNG de 20 KB pode dizer 169 Mpx e pedir 1 GB de memória
#: (📊 o mesmo ataque medido pelo red team da 132-A, `chat_anexos.py` PIXELS_MAXIMOS). 50 Mpx cobre a câmera de 48 Mpx.
PIXELS_MAXIMOS = 50_000_000
#: a legenda vai a uma linha embaixo da foto na página do cliente.
LEGENDA_TETO = 80
#: prêmios: até 10, nome de 2 a 80 caracteres, ano de 1950 até o ano corrente (o ano que vem ainda não premiou ninguém).
PREMIOS_TETO = 10
PREMIO_NOME_MIN, PREMIO_NOME_MAX = 2, 80
PREMIO_ANO_MINIMO = 1950

_MIME_DO_FORMATO = {"JPEG": "image/jpeg", "MPO": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp",
                    "HEIF": "image/heic"}
_MARCAS_HEIF = (b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1")

FRASE_NAO_E_FOTO = ("Esse arquivo não é uma foto que dê para usar. Envie uma foto em JPG, PNG, WebP ou HEIC "
                    "(a do iPhone).")
FRASE_ANIMADA = "Essa imagem é animada. Envie uma foto parada, em JPG, PNG, WebP ou HEIC."
FRASE_GRANDE_DEMAIS = "Essa foto é grande demais para abrir. Envie uma versão menor (até 10 MB)."
FRASE_TETO = f"Até {FOTOS_TETO} fotos. Remova uma para adicionar outra."
FRASE_NAO_ENCONTRADA = "Essa foto não foi encontrada. Recarregue a página e tente de novo."
#: SPEC-130-C · F4 — enquanto a migration 20261016_04 (o DROP do índice antigo, passo do Founder) não roda, o índice
#: `brand_assets_one_current_per_kind (company_id, kind) WHERE is_current` ainda existe e recusa a 2ª foto ATUAL com
#: 23505. A corretora lê ESTA frase (nunca um 500 cru): ela diz o que falta e com quem falar.
FRASE_FALTA_A_MIGRATION = ("A 2ª foto precisa de um passo de instalação do banco (a migration 20261016_04); "
                           "fale com o suporte.")
#: o nome EXATO do índice antigo — o novo (`…_exceto_foto`) começa igual e não pode casar
_INDICE_ANTIGO = re.compile(r"brand_assets_one_current_per_kind(?![A-Za-z0-9_])")


# ======================================================================================================================
# pequenos auxiliares
# ======================================================================================================================

def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _linhas(resp: Any) -> list:
    dados = getattr(resp, "data", None)
    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        return [dados]
    return []


def _uuid_valido(valor: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(valor)))
    except (ValueError, TypeError, AttributeError):
        return None


_CONTROLE = re.compile(r"[\x00-\x1f\x7f​-‏ -‮⁦-⁩]")


def limpar_legenda(bruta: Any) -> Optional[str]:
    """A legenda como a corretora escreveu, sem caractere de controle e sem espaço sobrando. Vazia → None."""
    if bruta is None:
        return None
    texto = _CONTROLE.sub(" ", str(bruta))
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        return None
    if len(texto) > LEGENDA_TETO:
        raise EntradaRecusada(f"A legenda pode ter até {LEGENDA_TETO} caracteres (esta tem {len(texto)}).")
    return texto


# ======================================================================================================================
# a foto: bytes → WEBP limpo
# ======================================================================================================================

def tipo_da_foto(dados: bytes) -> Optional[str]:
    """O formato pelo CONTEÚDO (assinatura dos primeiros bytes). None = não é foto que se aceita."""
    if dados.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "WEBP"
    if dados[4:8] == b"ftyp" and dados[8:12] in _MARCAS_HEIF:
        return "HEIF"
    return None


def _sem_metadados(img):
    """🔴 O DESCARTE. Devolve uma imagem NOVA só com os pixels: nada de EXIF (GPS, aparelho, data), XMP, comentário.

    Não se confia no codificador para "não copiar": é a imagem gravada que não tem de onde copiar. O perfil de cor é
    tratado antes (`_para_srgb`) — depois dele, as cores já estão nos pixels.
    """
    from PIL import Image

    limpa = Image.new(img.mode, img.size)
    limpa.paste(img)
    return limpa


def _para_srgb(img):
    """Foto do iPhone vem em Display P3: sem converter, perder o perfil desbota a cor. Falhou? segue sem perfil."""
    icc = img.info.get("icc_profile")
    if not icc:
        return img
    try:
        from PIL import ImageCms

        origem = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        destino = ImageCms.createProfile("sRGB")
        return ImageCms.profileToProfile(img, origem, destino, outputMode="RGB")
    except Exception:  # noqa: BLE001 — perfil quebrado não impede a foto; a cor fica como veio
        return img


def _abrir(dados: bytes, formato: str):
    """Abre com o Pillow RESTRITO ao formato que os bytes disseram, confere e reabre. Levanta EntradaRecusada."""
    from PIL import Image

    formatos = [formato] if formato != "JPEG" else ["JPEG", "MPO"]
    if formato == "HEIF":
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
        except Exception as exc:  # noqa: BLE001
            raise EntradaRecusada("Não consegui abrir a foto do iPhone (HEIC). Envie a foto em JPG.") from exc
    try:
        with Image.open(io.BytesIO(dados), formats=formatos) as prova:
            largura, altura = prova.size
            if largura <= 0 or altura <= 0 or largura * altura > PIXELS_MAXIMOS:
                raise EntradaRecusada(FRASE_GRANDE_DEMAIS)
            if prova.format in ("PNG", "WEBP") and getattr(prova, "is_animated", False):
                raise EntradaRecusada(FRASE_ANIMADA)
            prova.verify()   # o arquivo inteiro é o que diz ser — só então se decodifica
    except EntradaRecusada:
        raise
    except Image.DecompressionBombError as exc:
        raise EntradaRecusada(FRASE_GRANDE_DEMAIS) from exc
    except Exception as exc:  # noqa: BLE001 — qualquer coisa que o Pillow não abre não é foto
        raise EntradaRecusada(FRASE_NAO_E_FOTO) from exc
    try:
        img = Image.open(io.BytesIO(dados), formats=formatos)   # `verify` inutiliza o objeto: reabre
        if img.format in ("JPEG", "MPO"):
            # o JPEG se decodifica JÁ REDUZIDO (1/2, 1/4, 1/8): 48 Mpx não viram 144 MB de pixels
            img.draft("RGB", (LADO_MAXIMO_PX, LADO_MAXIMO_PX))
        img.load()
        return img
    except Exception as exc:  # noqa: BLE001
        raise EntradaRecusada(FRASE_NAO_E_FOTO) from exc


def preparar_foto(dados: bytes) -> dict:
    """bytes do corretor → {webp, largura, altura, mime}. Recusa com a frase que ELE lê (EntradaRecusada)."""
    if not dados:
        raise EntradaRecusada("O arquivo chegou vazio. Escolha a foto de novo.")
    if len(dados) > ENTRADA_TETO_BYTES:
        mb = len(dados) / (1024 * 1024)
        raise EntradaRecusada(f"A foto tem {mb:.1f} MB e o limite é 10 MB. Envie uma versão menor.")
    formato = tipo_da_foto(dados)
    if formato is None:
        raise EntradaRecusada(FRASE_NAO_E_FOTO)

    img = _abrir(dados, formato)
    try:
        return _reduzir(img)
    except EntradaRecusada:
        raise
    except Exception as exc:  # noqa: BLE001 — modo de cor exótico, arquivo que abriu mas não converte: não é foto útil
        logger.warning("[brand.fotos] foto abriu mas nao converteu: %s", type(exc).__name__)
        raise EntradaRecusada(FRASE_NAO_E_FOTO) from exc


def _reduzir(img) -> dict:
    from PIL import Image, ImageOps

    # reduz ANTES de girar: o `exif_transpose` sobre o original de 48 Mpx decodificaria tudo
    img.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX), Image.Resampling.LANCZOS)
    img = ImageOps.exif_transpose(img)        # a orientação vira PIXEL; a etiqueta some com o resto
    img = _para_srgb(img)
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        fundo = Image.new("RGB", rgba.size, (255, 255, 255))
        fundo.paste(rgba, mask=rgba.split()[-1])
        img = fundo
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img = _sem_metadados(img)

    lado = max(img.size)
    while True:
        atual = img if max(img.size) <= lado else img.resize(
            _encolher(img.size, lado), Image.Resampling.LANCZOS)
        for q in QUALIDADES_WEBP:
            saida = io.BytesIO()
            atual.save(saida, format="WEBP", quality=q, method=4)
            webp = saida.getvalue()
            if len(webp) <= SAIDA_TETO_BYTES:
                return {"webp": webp, "largura": atual.size[0], "altura": atual.size[1], "mime": "image/webp",
                        "qualidade": q}
        if lado <= LADO_MINIMO_PX:
            raise EntradaRecusada("Não consegui deixar essa foto leve o bastante para a página. Tente outra foto.")
        lado = max(LADO_MINIMO_PX, int(lado * 0.8))


def _encolher(tamanho: tuple[int, int], lado: int) -> tuple[int, int]:
    largura, altura = tamanho
    escala = lado / float(max(largura, altura))
    return max(1, round(largura * escala)), max(1, round(altura * escala))


# ======================================================================================================================
# leitura (o contrato com F3 + a tela)
# ======================================================================================================================

def _fotos_atuais(db: Any, company_id: str) -> list[dict]:
    """As fotos ATUAIS desta corretora, na ordem da página. Levanta se o banco falhar (quem escreve quer saber)."""
    linhas = _linhas(db.table("brand_assets")
                     .select("id, company_id, storage_ref, caption, sort_order, width, height, byte_size, created_at")
                     .eq("company_id", company_id).eq("kind", "photo").eq("is_current", True)
                     .execute())
    return sorted(linhas, key=_chave_de_ordem)


def _chave_de_ordem(linha: dict) -> tuple:
    ordem = linha.get("sort_order")
    return (ordem is None, ordem if isinstance(ordem, int) else 0, str(linha.get("created_at") or ""),
            str(linha.get("id") or ""))


def _publica(linha: dict) -> dict:
    return {"id": linha.get("id"), "src": linha.get("storage_ref"), "legenda": linha.get("caption") or "",
            "ordem": linha.get("sort_order"), "largura": linha.get("width"), "altura": linha.get("height"),
            "bytes": linha.get("byte_size"), "criada_em": linha.get("created_at")}


def fotos_da_pagina(db: Any, company_id: str, teto: int = FOTOS_NA_PAGINA) -> list[dict]:
    """CONTRATO F1 → F3: as fotos que vão à página DESTA corretora → [{"src": "data:image/webp;base64,…", "legenda"}].

    🔴 O filtro `company_id` está no SELECT (CLAUDE.md §7). Nunca levanta: sem corretora, sem foto ou banco fora → [].
    Só `data:image/` sai — a página do `/r/` só aceita imagem embutida (CSP `img-src 'self' data:`).
    """
    if not company_id:
        return []
    try:
        n = max(0, min(int(teto), FOTOS_TETO))
    except (TypeError, ValueError):
        n = FOTOS_NA_PAGINA
    if n == 0:
        return []
    try:
        linhas = _linhas(db.table("brand_assets")
                         .select("storage_ref, caption, sort_order, created_at, id")
                         .eq("company_id", company_id)
                         .eq("kind", "photo").eq("is_current", True)
                         .execute())
    except Exception as exc:  # noqa: BLE001 — a página sai sem fotos, nunca quebra
        logger.warning("[brand.fotos] leitura das fotos falhou: %s", type(exc).__name__)
        return []
    saida = []
    for linha in sorted(linhas, key=_chave_de_ordem):
        src = str(linha.get("storage_ref") or "")
        if not src.startswith("data:image/"):
            continue
        saida.append({"src": src, "legenda": str(linha.get("caption") or "")})
        if len(saida) >= n:
            break
    return saida


def listar_fotos(db: Any, company_id: str) -> list[dict]:
    """Para a tela da Identidade: todas as fotos atuais da corretora, com id, legenda e ordem."""
    return [_publica(l) for l in _fotos_atuais(db, company_id)]


def _ler_premios(bruto: Any) -> list[dict]:
    saida = []
    for item in bruto if isinstance(bruto, list) else []:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome") or "").strip()
        if not nome:
            continue
        ano = item.get("ano")
        saida.append({"nome": nome, "ano": ano if isinstance(ano, int) and not isinstance(ano, bool) else None})
    return saida[:PREMIOS_TETO]


def premios(db: Any, company_id: str) -> list[dict]:
    """CONTRATO F1 → F3: os prêmios DESTA corretora → [{"nome", "ano": int | None}]. Nunca levanta (→ [])."""
    if not company_id:
        return []
    try:
        linhas = _linhas(db.table("brand_profiles").select("awards")
                         .eq("company_id", company_id).limit(1).execute())
    except Exception as exc:  # noqa: BLE001 — sem coluna (migration não aplicada) ou banco fora: página sem prêmio
        logger.warning("[brand.fotos] leitura dos prêmios falhou: %s", type(exc).__name__)
        return []
    return _ler_premios(linhas[0].get("awards")) if linhas else []


# ======================================================================================================================
# escrita — fotos
# ======================================================================================================================

def bate_no_indice_antigo(exc: BaseException) -> bool:
    """A exceção é o 23505 (unique_violation) do índice ANTIGO `brand_assets_one_current_per_kind`? O PostgREST
    (`postgrest.exceptions.APIError`) traz `code`/`message`/`details`; outros clientes, só o texto — confere os dois."""
    codigo = str(getattr(exc, "code", "") or "")
    texto = " ".join(str(x or "") for x in (getattr(exc, "message", ""), getattr(exc, "details", ""), exc))
    return (codigo == "23505" or "23505" in texto or "duplicate key" in texto.lower()) and bool(
        _INDICE_ANTIGO.search(texto))


def adicionar_foto(db: Any, company_id: str, user_id: Optional[str], dados: bytes,
                   legenda: Optional[str] = None) -> dict:
    """Valida os BYTES, reduz, descarta o EXIF e grava a foto como a ÚLTIMA da corretora. Levanta EntradaRecusada."""
    if not company_id:
        raise EntradaRecusada("Corretora não identificada.")
    legenda_limpa = limpar_legenda(legenda)
    atuais = _fotos_atuais(db, company_id)
    if len(atuais) >= FOTOS_TETO:
        raise EntradaRecusada(FRASE_TETO)

    foto = preparar_foto(dados)
    ordens = [l.get("sort_order") for l in atuais if isinstance(l.get("sort_order"), int)]
    proxima = (max(ordens) + 1) if ordens else len(atuais)
    linha = {
        "company_id": company_id, "kind": "photo",
        "storage_ref": "data:image/webp;base64," + base64.b64encode(foto["webp"]).decode("ascii"),
        "mime_type": foto["mime"], "byte_size": len(foto["webp"]),
        "width": foto["largura"], "height": foto["altura"], "has_transparency": False,
        "source_kind": "upload", "source_url": None, "confidence": 1.0,
        "is_current": True, "sort_order": proxima, "caption": legenda_limpa,
        "created_by": _uuid_valido(user_id),
    }
    try:
        gravada = _linhas(db.table("brand_assets").insert(linha).execute())
    except Exception as exc:  # noqa: BLE001 — só a violação do índice ANTIGO vira frase; o resto sobe como era
        if bate_no_indice_antigo(exc):
            logger.warning("[brand.fotos] 2a foto recusada pelo indice antigo: falta a migration 20261016_04")
            raise EntradaRecusada(FRASE_FALTA_A_MIGRATION) from exc
        raise
    if not gravada:
        raise RuntimeError("foto nao gravada")
    novo_id = gravada[0].get("id")

    # Duas fotos enviadas AO MESMO TEMPO podem ter visto 7 e gravado a 9ª. Reconta depois de gravar: passou do teto,
    # a que acabou de entrar sai (só ela, só desta corretora).
    if len(_fotos_atuais(db, company_id)) > FOTOS_TETO:
        (db.table("brand_assets").delete()
         .eq("id", novo_id).eq("company_id", company_id).eq("kind", "photo").execute())
        raise EntradaRecusada(FRASE_TETO)
    return _publica(gravada[0])


def _uma_foto(db: Any, company_id: str, foto_id: Any) -> dict:
    fid = _uuid_valido(foto_id)
    if not fid:
        raise EntradaRecusada(FRASE_NAO_ENCONTRADA)
    linhas = _linhas(db.table("brand_assets").select("id, sort_order, caption")
                     .eq("id", fid).eq("company_id", company_id).eq("kind", "photo").eq("is_current", True)
                     .limit(1).execute())
    if not linhas:
        raise EntradaRecusada(FRASE_NAO_ENCONTRADA)
    return linhas[0]


_NADA = object()


def atualizar_foto(db: Any, company_id: str, foto_id: Any, legenda: Any = _NADA, sort_order: Any = _NADA) -> dict:
    """Troca a legenda e/ou a ordem de UMA foto desta corretora. Id de outra corretora → "não encontrada"."""
    atual = _uma_foto(db, company_id, foto_id)
    patch: dict[str, Any] = {}
    if legenda is not _NADA:
        patch["caption"] = limpar_legenda(legenda)
    if sort_order is not _NADA and sort_order is not None:
        if isinstance(sort_order, bool) or not isinstance(sort_order, int) or not 0 <= sort_order < FOTOS_TETO:
            raise EntradaRecusada("A posição da foto precisa ser de 1 a 8.")
        patch["sort_order"] = sort_order
    if not patch:
        return {"id": atual["id"], "legenda": atual.get("caption") or "", "ordem": atual.get("sort_order")}
    (db.table("brand_assets").update(patch)
     .eq("id", atual["id"]).eq("company_id", company_id).eq("kind", "photo").execute())
    return {"id": atual["id"], "legenda": patch.get("caption", atual.get("caption")) or "",
            "ordem": patch.get("sort_order", atual.get("sort_order"))}


def remover_foto(db: Any, company_id: str, foto_id: Any) -> bool:
    """APAGA a foto desta corretora e renumera as que ficam.

    DELETE, e não `is_current=false`: a foto é imagem de PESSOAS (a equipe, um evento) e, removida, não tem mais leitor —
    nenhum histórico de foto é lido por ninguém (o logo, sim: `logo_asset_id` aponta para ele). Guardar uma cópia
    invisível do rosto de quem saiu da corretora seria reter dado pessoal sem finalidade (LGPD art. 16). Página já
    publicada guarda o próprio HTML e não depende desta linha.
    """
    atual = _uma_foto(db, company_id, foto_id)
    (db.table("brand_assets").delete()
     .eq("id", atual["id"]).eq("company_id", company_id).eq("kind", "photo").execute())
    restantes = _fotos_atuais(db, company_id)
    for posicao, linha in enumerate(restantes):
        if linha.get("sort_order") != posicao:
            (db.table("brand_assets").update({"sort_order": posicao})
             .eq("id", linha["id"]).eq("company_id", company_id).eq("kind", "photo").execute())
    return True


def reordenar(db: Any, company_id: str, ids: Any) -> list[dict]:
    """A nova ordem, de cima para baixo. Tem de ser EXATAMENTE as fotos atuais desta corretora, cada uma uma vez."""
    pedidos = [_uuid_valido(i) for i in (ids if isinstance(ids, list) else [])]
    atuais = _fotos_atuais(db, company_id)
    ids_atuais = [str(l["id"]) for l in atuais]
    if (None in pedidos or len(pedidos) != len(set(pedidos))
            or sorted(pedidos) != sorted(ids_atuais)):
        raise EntradaRecusada("A ordem não confere com as fotos atuais. Recarregue a página e tente de novo.")
    ordem_atual = {str(l["id"]): l.get("sort_order") for l in atuais}
    for posicao, fid in enumerate(pedidos):
        if ordem_atual.get(fid) != posicao:
            (db.table("brand_assets").update({"sort_order": posicao})
             .eq("id", fid).eq("company_id", company_id).eq("kind", "photo").execute())
    return listar_fotos(db, company_id)


# ======================================================================================================================
# escrita — prêmios
# ======================================================================================================================

_URL = re.compile(r"(https?://|www\.|\b[\w-]+\.(com|br|net|org|io|app|site)\b)", re.IGNORECASE)


def validar_premios(premios_brutos: Any, *, ano_atual: Optional[int] = None) -> list[dict]:
    """[{nome, ano?}] → a lista limpa. Recusa com a frase que a corretora lê. CDC art. 37: só o que ela cadastrou."""
    teto_ano = ano_atual or datetime.now(timezone.utc).year
    if premios_brutos is None:
        return []
    if not isinstance(premios_brutos, list):
        raise EntradaRecusada("Os prêmios chegaram num formato que não dá para ler. Recarregue a página.")
    if len(premios_brutos) > PREMIOS_TETO:
        raise EntradaRecusada(f"Até {PREMIOS_TETO} prêmios. Fique com os mais importantes.")
    limpos: list[dict] = []
    vistos: set[tuple] = set()
    for item in premios_brutos:
        if not isinstance(item, dict):
            raise EntradaRecusada("Cada prêmio precisa de um nome.")
        nome = re.sub(r"\s+", " ", _CONTROLE.sub(" ", str(item.get("nome") or ""))).strip()
        if not (PREMIO_NOME_MIN <= len(nome) <= PREMIO_NOME_MAX):
            raise EntradaRecusada(
                f"O nome do prêmio precisa ter de {PREMIO_NOME_MIN} a {PREMIO_NOME_MAX} caracteres.")
        if "<" in nome or ">" in nome or _URL.search(nome):
            raise EntradaRecusada("Escreva só o nome do prêmio, sem link e sem código.")
        ano_bruto = item.get("ano")
        ano: Optional[int]
        if ano_bruto is None or (isinstance(ano_bruto, str) and not ano_bruto.strip()):
            ano = None
        else:
            texto = str(ano_bruto).strip()
            if isinstance(ano_bruto, bool) or not re.fullmatch(r"\d{4}", texto):
                raise EntradaRecusada(f"O ano do prêmio precisa ser entre {PREMIO_ANO_MINIMO} e {teto_ano}.")
            ano = int(texto)
            if not PREMIO_ANO_MINIMO <= ano <= teto_ano:
                raise EntradaRecusada(f"O ano do prêmio precisa ser entre {PREMIO_ANO_MINIMO} e {teto_ano}.")
        chave = (nome.casefold(), ano)
        if chave in vistos:
            continue
        vistos.add(chave)
        limpos.append({"nome": nome, "ano": ano})
    return limpos


def salvar_premios(db: Any, company_id: str, user_id: Optional[str], premios_brutos: Any) -> list[dict]:
    """Grava `brand_profiles.awards` SÓ desta corretora (cria o perfil se ainda não existe) e versiona o perfil."""
    if not company_id:
        raise EntradaRecusada("Corretora não identificada.")
    limpos = validar_premios(premios_brutos)
    perfis = _linhas(db.table("brand_profiles").select("id").eq("company_id", company_id).limit(1).execute())
    if perfis:
        pid = perfis[0]["id"]
    else:
        novo = _linhas(db.table("brand_profiles").insert({"company_id": company_id}).execute())
        if not novo:
            raise RuntimeError("perfil nao criado")
        pid = novo[0]["id"]
    (db.table("brand_profiles")
     .update({"awards": limpos, "updated_at": _agora(), "updated_by": _uuid_valido(user_id)})
     .eq("id", pid).eq("company_id", company_id).execute())
    try:
        # o histórico append-only do perfil é o MESMO da edição humana (não um segundo histórico)
        from app.services.brand.capture import BrandCaptureService

        BrandCaptureService(db)._versionar(company_id, pid, "human_edit", ["awards"])
    except Exception as exc:  # noqa: BLE001 — sem versão o prêmio continua gravado; o log diz
        logger.warning("[brand.fotos] versao dos premios nao gravada: %s", type(exc).__name__)
    return limpos
