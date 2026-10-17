# -*- coding: utf-8 -*-
"""SPEC-130-C · F1 — as fotos e os prêmios da corretora (`app/services/brand/fotos.py`).

O que se afirma é o comportamento do MÓDULO sobre BYTES REAIS gerados pelo Pillow — nenhum helper reimplementa a regra
(CLAUDE.md §9.4). Só o TRANSPORTE é dublê: um cliente supabase em memória, BURRO de propósito — compara igualdade de
coluna e mais nada. Se o módulo esquecer o `.eq("company_id", …)`, o dublê devolve as linhas da outra corretora, como o
PostgREST com service role devolveria (CLAUDE.md §7: a RLS sem policy não protege nada contra filtro esquecido).

O dublê só sabe do banco o que a MIGRATION 20261016_03 garante: o índice único parcial (um atual por papel, EXCETO foto)
e o CHECK da legenda ≤ 80 — para que um teste não passe gravando o que o Postgres recusaria.

Mutações (CLAUDE.md §9.3 — o guarda tem de CONSEGUIR ficar vermelho; rodadas uma vez, restauradas por cópia):
  M1  tirar `.eq("company_id", company_id)` de `fotos_da_pagina`  → test_duas_corretoras_a_pagina_de_a_nunca_tem_foto_de_b
  M2  tirar `img = _sem_metadados(img)` de `_reduzir`             → test_o_que_vai_ao_codificador_nao_tem_exif
"""
from __future__ import annotations

import base64
import io
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

from app.services.brand import fotos  # noqa: E402
from app.services.brand.capture import EntradaRecusada  # noqa: E402

A = "aaaaaaaa-0000-4000-8000-00000000000a"
B = "bbbbbbbb-0000-4000-8000-00000000000b"
USUARIO = "cccccccc-0000-4000-8000-00000000000c"


# ======================================================================================================================
# o dublê do cliente supabase-py — BURRO
# ======================================================================================================================

class _Resp:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Op:
    """`table(x).select/insert/update/delete(...).eq(...).neq(...).order(...).limit(...).maybe_single().execute()`."""

    def __init__(self, banco: "Banco", nome: str) -> None:
        self.banco, self.nome = banco, nome
        self.tipo = "select"
        self.payload: Any = None
        self.filtros: List = []
        self.ordens: List = []
        self.n: Any = None
        self.um = False

    # leitura
    def select(self, *_a, **_k):
        self.tipo = "select"
        return self

    def eq(self, col, val):
        self.filtros.append(("eq", col, str(val)))
        return self

    def neq(self, col, val):
        self.filtros.append(("neq", col, str(val)))
        return self

    def order(self, col, desc=False):
        self.ordens.append((col, desc))
        return self

    def limit(self, n):
        self.n = int(n)
        return self

    def maybe_single(self):
        self.um = True
        return self

    # escrita
    def insert(self, linha):
        self.tipo, self.payload = "insert", linha
        return self

    def update(self, patch):
        self.tipo, self.payload = "update", dict(patch)
        return self

    def delete(self):
        self.tipo = "delete"
        return self

    def _casa(self, linha):
        for op, col, val in self.filtros:
            igual = str(linha.get(col)) == val
            if (op == "eq" and not igual) or (op == "neq" and igual):
                return False
        return True

    def execute(self):
        self.banco.chamadas.append((self.nome, self.tipo, list(self.filtros)))
        if self.banco.quebrado:
            raise RuntimeError("banco fora")
        tabela = self.banco.tabelas.setdefault(self.nome, [])
        if self.tipo == "insert":
            novas = []
            for linha in self.payload if isinstance(self.payload, list) else [self.payload]:
                nova = dict(linha)
                nova.setdefault("id", str(uuid.uuid4()))
                nova.setdefault("created_at", self.banco.relogio())
                if self.nome == "brand_assets":
                    nova.setdefault("is_current", True)
                self.banco.conferir(self.nome, nova, tabela)
                novas.append(nova)
            tabela.extend(novas)
            return _Resp([dict(x) for x in novas])
        if self.tipo == "update":
            tocadas = []
            for linha in tabela:
                if self._casa(linha):
                    candidata = {**linha, **self.payload}
                    self.banco.conferir(self.nome, candidata, [l for l in tabela if l is not linha])
                    linha.update(self.payload)
                    tocadas.append(dict(linha))
            return _Resp(tocadas)
        if self.tipo == "delete":
            fora = [l for l in tabela if self._casa(l)]
            self.banco.tabelas[self.nome] = [l for l in tabela if not self._casa(l)]
            return _Resp([dict(x) for x in fora])
        linhas = [dict(l) for l in tabela if self._casa(l)]
        for col, desc in reversed(self.ordens):
            linhas.sort(key=lambda l: (l.get(col) is None, l.get(col) if l.get(col) is not None else 0), reverse=desc)
        if self.n is not None:
            linhas = linhas[: self.n]
        if self.um:
            return _Resp(linhas[0] if linhas else None)
        return _Resp(linhas)


class Banco:
    def __init__(self) -> None:
        self.tabelas: Dict[str, List[dict]] = {}
        self.chamadas: List = []
        self.quebrado = False
        self._t = 0

    def relogio(self) -> str:
        self._t += 1
        return f"2026-10-16T00:00:{self._t:02d}+00:00"

    def table(self, nome: str) -> _Op:
        return _Op(self, nome)

    def conferir(self, nome: str, linha: dict, outras: List[dict]) -> None:
        """Só o que a migration 20261016_03 garante no Postgres."""
        if nome != "brand_assets":
            return
        if linha.get("caption") is not None and len(linha["caption"]) > 80:
            raise ValueError("23514 brand_assets_caption_len_ck")
        if linha.get("is_current") and linha.get("kind") != "photo":
            for o in outras:
                if (o.get("is_current") and str(o.get("company_id")) == str(linha.get("company_id"))
                        and o.get("kind") == linha.get("kind")):
                    raise ValueError("23505 brand_assets_one_current_per_kind_exceto_foto")

    def linhas(self, nome: str, **filtro) -> List[dict]:
        return [l for l in self.tabelas.get(nome, []) if all(str(l.get(k)) == str(v) for k, v in filtro.items())]


@pytest.fixture
def db() -> Banco:
    return Banco()


# ======================================================================================================================
# bytes reais
# ======================================================================================================================

def _jpeg(tamanho=(1200, 800), cor=(200, 30, 30), exif=None, ruido=False, qualidade=88) -> bytes:
    img = Image.new("RGB", tamanho, cor)
    if ruido:
        ruido_img = Image.effect_noise(tamanho, 40).convert("RGB")
        img = Image.blend(img, ruido_img, 0.35)
    out = io.BytesIO()
    if exif is not None:
        img.save(out, format="JPEG", quality=qualidade, exif=exif)
    else:
        img.save(out, format="JPEG", quality=qualidade)
    return out.getvalue()


def _png(tamanho=(640, 480), cor=(20, 60, 200), modo="RGB") -> bytes:
    out = io.BytesIO()
    Image.new(modo, tamanho, cor if modo != "1" else 0).save(out, format="PNG")
    return out.getvalue()


def _exif_com_gps(orientacao=6):
    exif = Image.Exif()
    exif[0x0112] = orientacao                     # Orientation: 6 = girar 90° no sentido horário
    exif[0x010F] = "FabricanteDoCelular"          # Make
    gps = exif.get_ifd(0x8825)
    gps[1] = "S"
    gps[2] = (27.0, 35.0, 48.0)                   # 💭 uma coordenada qualquer — é o que NÃO pode sair daqui
    gps[3] = "W"
    gps[4] = (48.0, 32.0, 56.0)
    return exif


def _webp_gravado(linha: dict) -> bytes:
    ref = linha["storage_ref"]
    assert ref.startswith("data:image/webp;base64,"), ref[:40]
    return base64.b64decode(ref.split(",", 1)[1])


# ======================================================================================================================
# 1 · o EXIF (GPS!) nunca é gravado — mutação M2
# ======================================================================================================================

def test_o_que_vai_ao_codificador_nao_tem_exif(db, monkeypatch):
    """O guarda que CONSEGUE ficar vermelho: espia a imagem entregue ao `save` do WEBP.

    📊 medido 16/10/2026: o codificador WEBP do Pillow 12.3 NÃO copia `info["exif"]` sozinho — por isso o teste de
    bytes (abaixo) fica verde mesmo sem o descarte. Este aqui olha a imagem que CHEGA ao codificador: sem o
    `_sem_metadados`, ela carrega o EXIF com o GPS (o `exif_transpose` só tira a orientação).
    """
    vistas: list = []
    original = Image.Image.save

    def espia(self, fp, format=None, **params):  # noqa: A002
        if str(format).upper() == "WEBP":
            vistas.append((dict(self.info), dict(self.getexif()), params))
        return original(self, fp, format=format, **params)

    monkeypatch.setattr(Image.Image, "save", espia)
    fotos.adicionar_foto(db, A, USUARIO, _jpeg(exif=_exif_com_gps()), "Equipe")
    assert vistas, "o WEBP nem foi gerado"
    for info, exif, params in vistas:
        assert "exif" not in info, "a imagem entregue ao codificador ainda carrega EXIF"
        assert not exif, f"EXIF residual: {sorted(exif)}"
        assert not params.get("exif"), "o save recebeu EXIF explícito"
        assert "xmp" not in info and "XML:com.adobe.xmp" not in info


def test_jpeg_com_gps_e_gravado_sem_exif_e_na_orientacao_certa(db):
    entrada = _jpeg(tamanho=(1200, 800), exif=_exif_com_gps(orientacao=6))
    with Image.open(io.BytesIO(entrada)) as prova:   # linha de CONTROLE: a entrada TEM o GPS
        assert prova.getexif().get_ifd(0x8825), "o controle falhou: a entrada não tem GPS"

    nova = fotos.adicionar_foto(db, A, USUARIO, entrada, "Nossa equipe")
    linha = db.linhas("brand_assets", id=nova["id"])[0]
    webp = _webp_gravado(linha)
    assert b"Exif" not in webp and b"FabricanteDoCelular" not in webp
    with Image.open(io.BytesIO(webp)) as g:
        assert g.format == "WEBP"
        assert not g.getexif(), "EXIF gravado"
        assert "exif" not in g.info
        # orientação 6 aplicada nos PIXELS: 1200×800 deitado → em pé, ≤ 1080 no maior lado
        assert g.size == (720, 1080), g.size
    assert linha["kind"] == "photo" and linha["source_kind"] == "upload" and linha["is_current"] is True
    assert linha["mime_type"] == "image/webp" and linha["byte_size"] == len(webp)
    assert linha["company_id"] == A and linha["created_by"] == USUARIO and linha["caption"] == "Nossa equipe"


# ======================================================================================================================
# 2 · o tamanho
# ======================================================================================================================

def test_foto_4000x3000_vira_no_maximo_1080_e_90kb(db):
    entrada = _jpeg(tamanho=(4000, 3000), ruido=True, qualidade=92)
    assert len(entrada) > 300 * 1024, "controle: a entrada precisa ser pesada"
    nova = fotos.adicionar_foto(db, A, USUARIO, entrada, None)
    webp = _webp_gravado(db.linhas("brand_assets", id=nova["id"])[0])
    assert len(webp) <= fotos.SAIDA_TETO_BYTES, len(webp)
    with Image.open(io.BytesIO(webp)) as g:
        assert max(g.size) <= fotos.LADO_MAXIMO_PX and min(g.size) > 0
    assert nova["largura"] <= 1080 and nova["altura"] <= 1080


def test_entrada_acima_de_10mb_e_recusada(db):
    with pytest.raises(EntradaRecusada, match="10 MB"):
        fotos.adicionar_foto(db, A, USUARIO, b"\xff\xd8\xff" + b"0" * (fotos.ENTRADA_TETO_BYTES + 1), None)
    assert db.linhas("brand_assets") == []


def test_bomba_de_pixels_e_recusada_antes_de_decodificar(db):
    # PNG 1-bit de 60 Mpx: poucos KB no disco, ~60 MB a ~180 MB se decodificado em RGB
    bomba = _png(tamanho=(10_000, 6_000), modo="1")
    assert len(bomba) < 200 * 1024
    with pytest.raises(EntradaRecusada, match="grande demais"):
        fotos.adicionar_foto(db, A, USUARIO, bomba, None)
    assert db.linhas("brand_assets") == []


# ======================================================================================================================
# 3 · os BYTES decidem o tipo
# ======================================================================================================================

def test_png_com_nome_de_qualquer_coisa_entra_como_webp(db):
    # o nome nunca chega ao módulo: os bytes são PNG, e é isso que vale (o "foto.exe" do navegador não importa)
    nova = fotos.adicionar_foto(db, A, USUARIO, _png(), "Escritório")
    linha = db.linhas("brand_assets", id=nova["id"])[0]
    assert linha["storage_ref"].startswith("data:image/webp;base64,")
    with Image.open(io.BytesIO(_webp_gravado(linha))) as g:
        assert g.format == "WEBP" and g.mode == "RGB"


def test_png_com_transparencia_fica_com_fundo_branco(db):
    nova = fotos.adicionar_foto(db, A, USUARIO, _png(cor=(0, 0, 0, 0), modo="RGBA"), None)
    with Image.open(io.BytesIO(_webp_gravado(db.linhas("brand_assets", id=nova["id"])[0]))) as g:
        r, gg, b = g.convert("RGB").getpixel((10, 10))
        assert min(r, gg, b) > 240


def _gif_animado() -> bytes:
    quadros = [Image.new("RGB", (64, 64), c) for c in ((255, 0, 0), (0, 255, 0))]
    out = io.BytesIO()
    quadros[0].save(out, format="GIF", save_all=True, append_images=quadros[1:], duration=100, loop=0)
    return out.getvalue()


def _webp_animado() -> bytes:
    quadros = [Image.new("RGB", (64, 64), c) for c in ((255, 0, 0), (0, 255, 0))]
    out = io.BytesIO()
    quadros[0].save(out, format="WEBP", save_all=True, append_images=quadros[1:], duration=100)
    return out.getvalue()


@pytest.mark.parametrize("nome, dados", [
    ("svg_com_script", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
    ("svg_xml", b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'),
    ("html", b"<!doctype html><html><body><script>fetch('/x')</script></body></html>"),
    ("executavel_mz", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 200),
    ("pdf", b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"),
    ("gif_animado", None),
    ("webp_animado", None),
    ("jpeg_falso", b"\xff\xd8\xff\xe0" + b"isto nao e um jpeg" * 50),
    ("png_cortado", None),
    ("vazio", b""),
])
def test_o_que_nao_e_foto_e_recusado_e_nada_e_gravado(db, nome, dados):
    if nome == "gif_animado":
        dados = _gif_animado()
    elif nome == "webp_animado":
        dados = _webp_animado()
    elif nome == "png_cortado":
        dados = _png()[:60]
    with pytest.raises(EntradaRecusada):
        fotos.adicionar_foto(db, A, USUARIO, dados, "x")
    assert db.linhas("brand_assets") == [], nome


def test_heic_do_iphone_entra_quando_o_pillow_heif_escreve():
    pillow_heif = pytest.importorskip("pillow_heif")
    pillow_heif.register_heif_opener()
    out = io.BytesIO()
    try:
        Image.new("RGB", (800, 600), (10, 120, 10)).save(out, format="HEIF", quality=80)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"sem codificador HEIF nesta máquina: {type(exc).__name__}")
    dados = out.getvalue()
    assert fotos.tipo_da_foto(dados) == "HEIF"
    r = fotos.preparar_foto(dados)
    with Image.open(io.BytesIO(r["webp"])) as g:
        assert g.format == "WEBP" and g.size == (800, 600)


# ======================================================================================================================
# 4 · o teto de 8 e a legenda
# ======================================================================================================================

def test_a_nona_foto_e_recusada_com_frase_de_gente(db):
    for i in range(8):
        fotos.adicionar_foto(db, A, USUARIO, _png(cor=(i * 20, 10, 10)), f"foto {i + 1}")
    assert len(fotos.listar_fotos(db, A)) == 8
    with pytest.raises(EntradaRecusada, match="Até 8 fotos"):
        fotos.adicionar_foto(db, A, USUARIO, _png(), "nona")
    assert len(db.linhas("brand_assets", company_id=A)) == 8
    # o teto é POR corretora: B ainda adiciona
    fotos.adicionar_foto(db, B, USUARIO, _png(), "da B")
    assert len(db.linhas("brand_assets", company_id=B)) == 1


def test_duas_fotos_ao_mesmo_tempo_nao_furam_o_teto(db, monkeypatch):
    for i in range(7):
        fotos.adicionar_foto(db, A, USUARIO, _png(cor=(i * 20, 10, 10)), None)
    # a outra aba gravou a 8ª ENTRE a contagem e a gravação desta: esta viu 7 e grava a 9ª
    original = fotos.preparar_foto

    def corrida(dados):
        r = original(dados)
        db.tabelas["brand_assets"].append({"id": str(uuid.uuid4()), "company_id": A, "kind": "photo",
                                           "is_current": True, "sort_order": 7, "storage_ref": "data:image/webp;base64,AA",
                                           "created_at": db.relogio()})
        return r

    monkeypatch.setattr(fotos, "preparar_foto", corrida)
    with pytest.raises(EntradaRecusada, match="Até 8 fotos"):
        fotos.adicionar_foto(db, A, USUARIO, _png(), None)
    assert len(db.linhas("brand_assets", company_id=A, is_current=True)) == 8


def test_legenda_e_limpa_e_tem_teto_de_80(db):
    nova = fotos.adicionar_foto(db, A, USUARIO, _png(), "  Prêmio\x00 da\n\nequipe‮  ")
    assert nova["legenda"] == "Prêmio da equipe"
    with pytest.raises(EntradaRecusada, match="80"):
        fotos.adicionar_foto(db, A, USUARIO, _png(), "x" * 81)
    with pytest.raises(EntradaRecusada, match="80"):
        fotos.atualizar_foto(db, A, nova["id"], legenda="y" * 81)
    fotos.atualizar_foto(db, A, nova["id"], legenda="Evento de fim de ano")
    assert db.linhas("brand_assets", id=nova["id"])[0]["caption"] == "Evento de fim de ano"
    fotos.atualizar_foto(db, A, nova["id"], legenda="   ")
    assert db.linhas("brand_assets", id=nova["id"])[0]["caption"] is None


# ======================================================================================================================
# 5 · DUAS CORRETORAS — mutação M1
# ======================================================================================================================

def _duas_corretoras(db):
    ids = {A: [], B: []}
    for cid, cor in ((A, (220, 20, 20)), (B, (20, 20, 220))):
        for i in range(2):
            ids[cid].append(fotos.adicionar_foto(db, cid, USUARIO, _png(cor=(cor[0], cor[1] + i * 30, cor[2])),
                                                 f"{'vermelha' if cid == A else 'azul'} {i}")["id"])
    return ids


def test_duas_corretoras_a_pagina_de_a_nunca_tem_foto_de_b(db):
    _duas_corretoras(db)
    refs_a = {l["storage_ref"] for l in db.linhas("brand_assets", company_id=A)}
    refs_b = {l["storage_ref"] for l in db.linhas("brand_assets", company_id=B)}
    assert len(refs_a) == 2 and len(refs_b) == 2 and not (refs_a & refs_b), "controle: bytes distintos por corretora"

    pagina_a = fotos.fotos_da_pagina(db, A)
    pagina_b = fotos.fotos_da_pagina(db, B)
    assert {f["src"] for f in pagina_a} == refs_a
    assert {f["src"] for f in pagina_b} == refs_b
    assert all("vermelha" in f["legenda"] for f in pagina_a)
    assert all("azul" in f["legenda"] for f in pagina_b)
    # a cor dos PIXELS confirma: a página de A só tem vermelho
    for f in pagina_a:
        with Image.open(io.BytesIO(base64.b64decode(f["src"].split(",", 1)[1]))) as g:
            r, _, b = g.convert("RGB").getpixel((5, 5))
            assert r > 150 and b < 100
    # e a consulta levou o filtro (o elo: a foto é da corretora certa PORQUE o SELECT filtra company_id)
    leituras = [c for c in db.chamadas if c[0] == "brand_assets" and c[1] == "select"]
    assert ("eq", "company_id", A) in leituras[-2][2]


def test_id_de_outra_corretora_e_nao_encontrada_e_nada_muda(db):
    ids = _duas_corretoras(db)
    antes = [dict(l) for l in db.linhas("brand_assets", company_id=B)]
    alvo = ids[B][0]
    with pytest.raises(EntradaRecusada, match="não foi encontrada"):
        fotos.remover_foto(db, A, alvo)
    with pytest.raises(EntradaRecusada, match="não foi encontrada"):
        fotos.atualizar_foto(db, A, alvo, legenda="invadida")
    with pytest.raises(EntradaRecusada, match="não confere"):
        fotos.reordenar(db, A, list(reversed(ids[B])))
    with pytest.raises(EntradaRecusada, match="não confere"):
        fotos.reordenar(db, A, [ids[A][0], ids[B][0]])
    assert [dict(l) for l in db.linhas("brand_assets", company_id=B)] == antes
    # toda escrita levou o filtro da corretora
    for tabela, tipo, filtros in db.chamadas:
        if tabela == "brand_assets" and tipo in ("update", "delete"):
            assert any(f[1] == "company_id" for f in filtros), (tipo, filtros)


def test_premios_de_uma_corretora_nunca_aparecem_na_outra(db):
    db.tabelas["brand_profiles"] = [{"id": "p-a", "company_id": A, "awards": []}]
    fotos.salvar_premios(db, A, USUARIO, [{"nome": "Melhor corretora do ano", "ano": 2025}])
    fotos.salvar_premios(db, B, USUARIO, [{"nome": "Destaque regional", "ano": None}])
    assert fotos.premios(db, A) == [{"nome": "Melhor corretora do ano", "ano": 2025}]
    assert fotos.premios(db, B) == [{"nome": "Destaque regional", "ano": None}]
    # B não tinha perfil: nasceu UM, só dela; o de A não foi tocado pela gravação de B
    assert len(db.linhas("brand_profiles", company_id=B)) == 1
    assert db.linhas("brand_profiles", id="p-a")[0]["awards"] == [{"nome": "Melhor corretora do ano", "ano": 2025}]
    # e a versão do perfil foi gravada no histórico que já existe
    assert db.linhas("brand_profile_versions", company_id=A)


# ======================================================================================================================
# 6 · ordem, remoção, a página
# ======================================================================================================================

def test_ordem_remocao_e_as_4_primeiras_na_pagina(db):
    ids = [fotos.adicionar_foto(db, A, USUARIO, _png(cor=(i * 40, 50, 50)), f"f{i}")["id"] for i in range(6)]
    assert [f["ordem"] for f in fotos.listar_fotos(db, A)] == [0, 1, 2, 3, 4, 5]
    assert [f["legenda"] for f in fotos.fotos_da_pagina(db, A)] == ["f0", "f1", "f2", "f3"]
    assert len(fotos.fotos_da_pagina(db, A, teto=2)) == 2
    assert fotos.fotos_da_pagina(db, A, teto=0) == []

    nova_ordem = [ids[5], ids[0], ids[1], ids[2], ids[3], ids[4]]
    fotos.reordenar(db, A, nova_ordem)
    assert [f["legenda"] for f in fotos.fotos_da_pagina(db, A)] == ["f5", "f0", "f1", "f2"]

    fotos.remover_foto(db, A, ids[5])
    assert db.linhas("brand_assets", id=ids[5]) == [], "a foto removida é APAGADA (imagem de pessoa sem leitor)"
    assert [f["ordem"] for f in fotos.listar_fotos(db, A)] == [0, 1, 2, 3, 4]
    assert [f["legenda"] for f in fotos.fotos_da_pagina(db, A)] == ["f0", "f1", "f2", "f3"]

    with pytest.raises(EntradaRecusada):
        fotos.reordenar(db, A, ids[:2])                  # faltando foto
    with pytest.raises(EntradaRecusada):
        fotos.reordenar(db, A, [ids[0]] * 5)             # repetida


def test_a_foto_nao_rebaixa_o_logo_e_o_logo_continua_um_so(db):
    db.tabelas["brand_assets"] = [{"id": str(uuid.uuid4()), "company_id": A, "kind": "logo_primary",
                                   "is_current": True, "storage_ref": "data:image/png;base64,AA",
                                   "created_at": "2026-01-01"}]
    for _ in range(3):
        fotos.adicionar_foto(db, A, USUARIO, _png(), None)
    assert len(db.linhas("brand_assets", company_id=A, kind="logo_primary", is_current=True)) == 1
    assert len(db.linhas("brand_assets", company_id=A, kind="photo", is_current=True)) == 3
    # controle do dublê: dois logos atuais continuam recusados (o índice novo só libera FOTO)
    with pytest.raises(ValueError, match="23505"):
        db.table("brand_assets").insert({"company_id": A, "kind": "logo_primary", "is_current": True,
                                         "storage_ref": "x"}).execute()


def test_a_pagina_so_recebe_imagem_embutida(db):
    db.tabelas["brand_assets"] = [
        {"id": "1", "company_id": A, "kind": "photo", "is_current": True, "sort_order": 0,
         "storage_ref": "https://outro.site/foto.jpg", "caption": "externa", "created_at": "1"},
        {"id": "2", "company_id": A, "kind": "photo", "is_current": False, "sort_order": 1,
         "storage_ref": "data:image/webp;base64,AA", "caption": "antiga", "created_at": "2"},
        {"id": "3", "company_id": A, "kind": "logo_primary", "is_current": True,
         "storage_ref": "data:image/png;base64,AA", "caption": None, "created_at": "3"},
        {"id": "4", "company_id": A, "kind": "photo", "is_current": True, "sort_order": 2,
         "storage_ref": "data:image/webp;base64,BB", "caption": None, "created_at": "4"},
    ]
    assert fotos.fotos_da_pagina(db, A) == [{"src": "data:image/webp;base64,BB", "legenda": ""}]


def test_o_contrato_com_f3_nunca_levanta(db):
    db.quebrado = True
    assert fotos.fotos_da_pagina(db, A) == []
    assert fotos.premios(db, A) == []
    db.quebrado = False
    assert fotos.fotos_da_pagina(db, "") == []
    assert fotos.premios(db, None) == []
    assert fotos.premios(db, A) == []                      # sem perfil
    db.tabelas["brand_profiles"] = [{"id": "p", "company_id": A,
                                     "awards": [{"nome": "Ok", "ano": 2024}, "lixo", {"nome": ""}, {"nome": "X", "ano": True}]}]
    assert fotos.premios(db, A) == [{"nome": "Ok", "ano": 2024}, {"nome": "X", "ano": None}]


# ======================================================================================================================
# 7 · os prêmios — o que a corretora pode escrever
# ======================================================================================================================

ANO = datetime.now(timezone.utc).year


@pytest.mark.parametrize("premios_brutos, trecho", [
    ([{"nome": f"Prêmio {i}", "ano": 2020} for i in range(11)], "Até 10"),
    ([{"nome": "A", "ano": 2020}], "de 2 a 80"),
    ([{"nome": "x" * 81, "ano": 2020}], "de 2 a 80"),
    ([{"nome": "<b>Melhor</b>", "ano": 2020}], "sem link"),
    ([{"nome": "Veja em https://premio.com", "ano": 2020}], "sem link"),
    ([{"nome": "Premio www.algo", "ano": 2020}], "sem link"),
    ([{"nome": "Prêmio", "ano": 1949}], "1950"),
    ([{"nome": "Prêmio", "ano": ANO + 1}], str(ANO)),
    ([{"nome": "Prêmio", "ano": "20x5"}], "1950"),
    ([{"nome": "Prêmio", "ano": True}], "1950"),
    ("texto solto", "formato"),
])
def test_premio_invalido_e_recusado_e_nada_e_gravado(db, premios_brutos, trecho):
    db.tabelas["brand_profiles"] = [{"id": "p", "company_id": A, "awards": [{"nome": "Antigo", "ano": 2001}]}]
    with pytest.raises(EntradaRecusada, match=trecho):
        fotos.salvar_premios(db, A, USUARIO, premios_brutos)
    assert db.linhas("brand_profiles", id="p")[0]["awards"] == [{"nome": "Antigo", "ano": 2001}]


def test_premio_valido_e_limpo_e_sem_repeticao(db):
    r = fotos.salvar_premios(db, A, USUARIO, [
        {"nome": "  Corretora   destaque ", "ano": "2025"},
        {"nome": "corretora destaque", "ano": 2025},       # repetido (caixa e espaço) → um só
        {"nome": "Selo de qualidade", "ano": None},
        {"nome": "Top 10 do estado", "ano": ""},
    ])
    assert r == [{"nome": "Corretora destaque", "ano": 2025}, {"nome": "Selo de qualidade", "ano": None},
                 {"nome": "Top 10 do estado", "ano": None}]
    assert fotos.salvar_premios(db, A, USUARIO, []) == []
    assert fotos.premios(db, A) == []


# ======================================================================================================================
# 8 · a migration diz o que o dublê supõe
# ======================================================================================================================

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "supabase", "migrations",
                         "20261016_03_spec130c_fotos_e_premios.sql")


MIGRATION_CONTRACT = os.path.join(os.path.dirname(__file__), "..", "supabase", "migrations",
                                  "20261016_04_spec130c_fotos_contract.sql")


def test_a_migration_troca_o_indice_na_ordem_certa_e_tem_apply_verify_rollback():
    """§9.3 (SPEC-130-C, F4): o gerente DIVIDIU a migration (16/10) — a _03 (EXPAND: o índice novo, aplicada) e a _04
    (CONTRACT: o DROP do antigo, passo do Founder). A lição "o novo nasce ANTES de o antigo sair" migra: a _03 cria e NÃO
    derruba; a _04 só derruba DEPOIS de conferir que o substituto existe."""
    sql = open(MIGRATION, encoding="utf-8").read()
    for marca in ("APPLY:", "VERIFY", "ROLLBACK", "EXPAND-FIRST:", "DESTRUTIVA:"):
        assert marca in sql, marca
    corpo = "\n".join(l for l in sql.split("set lock_timeout", 1)[1].splitlines() if not l.lstrip().startswith("--"))
    assert "create unique index if not exists brand_assets_one_current_per_kind_exceto_foto" in corpo
    assert "drop index" not in corpo, "a _03 é só EXPAND: o DROP do índice antigo mora na _04"
    assert "where is_current and kind <> 'photo'" in corpo
    assert "char_length(caption) <= 80" in corpo
    assert "jsonb_typeof(awards) = 'array'" in corpo
    # o ROLLBACK tem a guarda das 2+ fotos atuais
    assert "having count(*) > 1" in sql.split("ROLLBACK", 1)[1]

    contrato = open(MIGRATION_CONTRACT, encoding="utf-8").read()
    for marca in ("APPLY:", "VERIFY:", "ROLLBACK", "EXPAND-FIRST:", "DESTRUTIVA:"):
        assert marca in contrato, marca
    corpo4 = "\n".join(l for l in contrato.split("set lock_timeout", 1)[1].splitlines()
                       if not l.lstrip().startswith("--"))
    guarda = corpo4.index("indexname = 'brand_assets_one_current_per_kind_exceto_foto'")
    derruba = corpo4.index("drop index if exists public.brand_assets_one_current_per_kind;")
    assert guarda < derruba, "a _04 só derruba o antigo depois de conferir que o substituto existe"
    assert "raise exception" in corpo4[guarda:derruba]
    assert "comment on column public.brand_assets.storage_ref" in corpo4


# ======================================================================================================================
# 9 · a API do backend — o company_id é o do chamador, e a Identidade não recebe as fotos como "assets"
# ======================================================================================================================

def _cliente_da_api(db, monkeypatch):
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app.api import brand as api

    class _Wrapper:
        client = db

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste")
    monkeypatch.setattr(api, "get_supabase_client", lambda: _Wrapper())
    app = fastapi.FastAPI()
    app.include_router(api.router)
    return TestClient(app), {"X-Internal-Key": "chave-de-teste"}


def test_api_fotos_ponta_a_ponta_com_duas_corretoras(db, monkeypatch):
    cli, h = _cliente_da_api(db, monkeypatch)
    r = cli.post("/api/brand/photos", headers=h, data={"company_id": A, "legenda": "Equipe"},
                 files={"foto": ("foto.exe", _jpeg(exif=_exif_com_gps()), "application/octet-stream")})
    assert r.status_code == 200, r.text
    id_a = r.json()["foto"]["id"]
    r = cli.post("/api/brand/photos", headers=h, data={"company_id": B},
                 files={"foto": ("logo.svg", b"<svg><script>alert(1)</script></svg>", "image/svg+xml")})
    assert r.status_code == 400 and "não é uma foto" in r.json()["error"]

    assert cli.get(f"/api/brand/photos?company_id={B}", headers=h).json()["fotos"] == []
    assert [f["id"] for f in cli.get(f"/api/brand/photos?company_id={A}", headers=h).json()["fotos"]] == [id_a]

    # B tenta mexer na foto de A pelo id: 404, nada muda
    assert cli.patch(f"/api/brand/photos/{id_a}", headers=h, json={"company_id": B, "legenda": "x"}).status_code == 404
    assert cli.delete(f"/api/brand/photos/{id_a}?company_id={B}", headers=h).status_code == 404
    assert db.linhas("brand_assets", id=id_a)[0]["caption"] == "Equipe"

    # sem chave interna: 401
    assert cli.get(f"/api/brand/photos?company_id={A}").status_code in (401, 422)

    r = cli.put("/api/brand/awards", headers=h, json={"company_id": A, "awards": [{"nome": "Prêmio X", "ano": 2025}]})
    assert r.status_code == 200 and r.json()["awards"] == [{"nome": "Prêmio X", "ano": 2025}]
    r = cli.put("/api/brand/awards", headers=h, json={"company_id": A, "awards": [{"nome": "<i>x</i>"}]})
    assert r.status_code == 400

    assert cli.delete(f"/api/brand/photos/{id_a}?company_id={A}", headers=h).status_code == 200
    assert db.linhas("brand_assets", id=id_a) == []


def test_o_perfil_da_identidade_nao_traz_as_fotos_como_assets(db, monkeypatch):
    cli, h = _cliente_da_api(db, monkeypatch)
    db.tabelas["brand_profiles"] = [{"id": "p-a", "company_id": A, "awards": [], "capture_status": "manual"}]
    db.tabelas["brand_assets"] = [
        {"id": "logo", "company_id": A, "kind": "logo_primary", "is_current": True, "storage_ref": "data:image/png;base64,AA"},
        {"id": "foto", "company_id": A, "kind": "photo", "is_current": True, "storage_ref": "data:image/webp;base64,BB",
         "sort_order": 0},
    ]
    r = cli.get(f"/api/brand/profile?company_id={A}", headers=h)
    assert r.status_code == 200, r.text
    assert [a["id"] for a in r.json()["assets"]] == ["logo"]
