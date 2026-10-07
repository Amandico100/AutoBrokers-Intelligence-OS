# -*- coding: utf-8 -*-
"""SPEC-133-A · FM — o logo que a corretora envia, o ano de fundação e a captura presa.

    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a_fm_logo_e_fundacao.py -q

⛔ Nenhum banco real, nenhuma rede, nenhum modelo. Os dois tenants são UUIDs
inventados; nenhum nome de corretora aparece aqui (CLAUDE.md §13.9).

O FIO (o primeiro teste): rota do backend `POST /api/brand/logo` + `PATCH
/api/brand/profile` → `BrandCaptureService` → `brand_assets`/`brand_profiles` →
o MESMO leitor que monta a proposta (`multicalculo.proposta.montar_anfitria`).
Dublê só na borda: o banco.
"""
from __future__ import annotations

import asyncio
import base64
import os
import struct
import sys
import types
import zlib
from datetime import datetime, timedelta, timezone

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app.services.brand import capture as C  # noqa: E402

A = "aaaaaaaa-0000-4000-8000-000000000001"
B = "bbbbbbbb-0000-4000-8000-000000000002"
CHAVE = "chave-de-teste-fm"


# ==========================================================================
# Dublê do PostgREST — com o ÍNDICE PARCIAL do banco real
# ==========================================================================

class _Resp:
    def __init__(self, data):
        self.data = data


class ErroDoBanco(Exception):
    pass


class _Q:
    def __init__(self, banco, nome):
        self.b, self.nome, self.f, self.lim, self.unico, self.op = banco, nome, [], None, False, None

    def select(self, *a, **k):
        return self

    def eq(self, c, v):
        self.f.append((c, v))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        self.lim = n
        return self

    def maybe_single(self):
        self.lim, self.unico = 1, True
        return self

    def insert(self, l):
        self.op = ("insert", l)
        return self

    def update(self, p):
        self.op = ("update", p)
        return self

    def upsert(self, l, on_conflict=None, **k):
        self.op = ("upsert", l, on_conflict)
        return self

    def _casa(self, l):
        return all(str(l.get(c)) == str(v) for c, v in self.f)

    def _indice_parcial(self):
        # 📊 `brand_assets_one_current_per_kind`: UNIQUE (company_id, kind) WHERE is_current
        if self.nome != "brand_assets":
            return
        vistos = set()
        for l in self.b.dados.get("brand_assets", []):
            if l.get("is_current"):
                k = (str(l["company_id"]), l["kind"])
                if k in vistos:
                    raise ErroDoBanco("23505 brand_assets_one_current_per_kind")
                vistos.add(k)

    def execute(self):
        linhas = self.b.dados.setdefault(self.nome, [])
        op = self.op
        if op and op[0] == "insert":
            nova = dict(op[1])
            nova.setdefault("id", f"{self.nome}-{len(linhas) + 1}")
            linhas.append(nova)
            self._indice_parcial()
            self.b.escritas.append((self.nome, "insert"))
            return _Resp([nova])
        if op and op[0] == "update":
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(op[1])
            self._indice_parcial()
            self.b.escritas.append((self.nome, "update"))
            return _Resp(tocadas)
        if op and op[0] == "upsert":
            carga, conflito = op[1], op[2]
            if self.nome == "brand_assets" and conflito == "company_id,kind":
                # 📊 07/10/2026, EXPLAIN no banco vivo: o índice é PARCIAL, e o
                # Postgres responde 42P10 a este ON CONFLICT.
                raise ErroDoBanco("42P10 there is no unique or exclusion constraint matching the ON CONFLICT")
            self.b.escritas.append((self.nome, "upsert"))
            for l in linhas:
                if (l.get("brand_profile_id"), l.get("field_path")) == (carga.get("brand_profile_id"), carga.get("field_path")):
                    l.update(carga)
                    return _Resp([l])
            nova = dict(carga)
            nova.setdefault("id", f"{self.nome}-{len(linhas) + 1}")
            linhas.append(nova)
            return _Resp([nova])
        achadas = [l for l in linhas if self._casa(l)]
        if self.lim:
            achadas = achadas[: self.lim]
        if self.unico:
            return _Resp(achadas[0] if achadas else None)
        return _Resp(achadas)


class Banco:
    def __init__(self):
        self.dados, self.escritas = {}, []

    def table(self, nome):
        return _Q(self, nome)


def _png(w=4, h=2) -> bytes:
    """Um PNG válido de verdade (preto sobre branco), feito aqui."""
    linha = b"\x00" + b"\x00\x00\x00" * (w // 2) + b"\xff\xff\xff" * (w - w // 2)
    cru = linha * h

    def bloco(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(cru)) + bloco(b"IEND", b""))


def _banco_dois_tenants() -> Banco:
    b = Banco()
    b.dados["companies"] = [{"id": A, "company_name": "Corretora A"}, {"id": B, "company_name": "Corretora B"}]
    b.dados["brand_profiles"] = [
        {"id": "pa", "company_id": A, "capture_status": "failed", "capture_error": "motivo antigo", "palette": {}, "is_published": False},
        {"id": "pb", "company_id": B, "capture_status": "manual", "logo_asset_id": "logo-b",
         "palette": {"primary": "#1D5579"}, "is_published": True},
    ]
    b.dados["brand_assets"] = [{"id": "logo-b", "company_id": B, "kind": "logo_primary",
                                "storage_ref": "data:image/png;base64,QkJC", "is_current": True,
                                "source_kind": "upload"}]
    return b


# ==========================================================================
# 0. O FIO — rota → serviço → banco → o leitor da proposta
# ==========================================================================

def _cliente(banco, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.brand as rota
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setattr(rota, "get_supabase_client", lambda: types.SimpleNamespace(client=banco))
    app = FastAPI()
    app.include_router(rota.router)
    return TestClient(app)


def test_o_fio__logo_enviado_e_ano_chegam_a_proposta(monkeypatch):
    banco = _banco_dois_tenants()
    cli = _cliente(banco, monkeypatch)
    h = {"X-Internal-Key": CHAVE}
    png = _png()

    r = cli.post("/api/brand/logo", headers=h, json={
        "company_id": A, "mime_type": "image/png", "data_base64": base64.b64encode(png).decode()})
    assert r.status_code == 200, r.text
    novo = r.json()["asset"]["id"]

    r = cli.patch("/api/brand/profile", headers=h, json={"company_id": A, "values": {
        "founded_year": 2011, "palette": {"primary": "#111111", "accent": "#111111"}, "is_published": True}})
    assert r.status_code == 200, r.text
    perfil = r.json()["profile"]
    assert perfil["logo_asset_id"] == novo and perfil["founded_year"] == 2011
    assert perfil["capture_status"] == "manual"          # deixou de ser "failed" ao receber logo/cor à mão
    assert perfil.get("capture_error") is None

    from app.services.multicalculo.proposta import montar_anfitria
    anf = asyncio.run(montar_anfitria(banco, A, {}))
    assert anf["marca_cadastrada"] is True
    assert anf["desde"] == 2011
    assert anf["logo_data_url"] == "data:image/png;base64," + base64.b64encode(png).decode()
    # e a B segue intacta
    b_perfil = next(p for p in banco.dados["brand_profiles"] if p["company_id"] == B)
    assert b_perfil["logo_asset_id"] == "logo-b"


# ==========================================================================
# 1. O envio do logo — tipo, tamanho, dois tenants
# ==========================================================================

def test_logo_novo_vira_o_atual_e_o_anterior_fica_no_historico():
    banco = _banco_dois_tenants()
    svc = C.BrandCaptureService(banco)
    primeiro = svc.trocar_logo(A, _png())["asset"]["id"]
    segundo = svc.trocar_logo(A, _png(6, 2))["asset"]["id"]
    da_a = [x for x in banco.dados["brand_assets"] if x["company_id"] == A]
    assert len(da_a) == 2                                   # nada apagado
    assert {x["id"]: x["is_current"] for x in da_a} == {primeiro: False, segundo: True}
    atual = next(x for x in da_a if x["id"] == segundo)
    assert atual["source_kind"] == "upload" and atual["storage_ref"].startswith("data:image/png;base64,")
    prov = [p for p in banco.dados["brand_field_provenance"] if p["field_path"] == "logo_asset_id"]
    assert prov and prov[0]["human_edited"] is True         # nenhuma captura o troca


@pytest.mark.parametrize("dados, trecho", [
    (b"GIF89a" + b"\x00" * 40, "PNG, JPG, SVG ou WebP"),
    (b"isto e um texto", "PNG, JPG, SVG ou WebP"),
    (b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024), "limite é 2 MB"),
    (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "traz código"),
    (b"<svg xmlns='http://www.w3.org/2000/svg' onload='x()'></svg>", "traz código"),
    (b"", "vazio"),
], ids=["gif", "texto", "acima_de_2MB", "svg_script", "svg_onload", "vazio"])
def test_logo_recusado_nao_escreve_nada(dados, trecho):
    banco = _banco_dois_tenants()
    with pytest.raises(C.EntradaRecusada) as e:
        C.BrandCaptureService(banco).trocar_logo(A, dados)
    assert trecho in str(e.value)
    assert banco.escritas == []


def test_controle__svg_limpo_e_jpg_passam():
    banco = _banco_dois_tenants()
    svc = C.BrandCaptureService(banco)
    svc.trocar_logo(A, b"<svg xmlns='http://www.w3.org/2000/svg'><circle r='4'/></svg>")
    svc.trocar_logo(A, b"\xff\xd8\xff\xe0" + b"\x00" * 64)
    tipos = [x["mime_type"] for x in banco.dados["brand_assets"] if x["company_id"] == A]
    assert tipos == ["image/svg+xml", "image/jpeg"]


def test_dois_tenants__a_nao_troca_o_logo_da_b():
    banco = _banco_dois_tenants()
    svc = C.BrandCaptureService(banco)
    svc.trocar_logo(A, _png())
    logo_b = next(x for x in banco.dados["brand_assets"] if x["id"] == "logo-b")
    assert logo_b["is_current"] is True and logo_b["storage_ref"] == "data:image/png;base64,QkJC"
    # e apontar o logo da B a partir da A é recusado
    with pytest.raises(C.EntradaRecusada, match="não pertence"):
        svc.editar(A, {"logo_asset_id": "logo-b"})
    perfil_a = next(p for p in banco.dados["brand_profiles"] if p["company_id"] == A)
    assert perfil_a.get("logo_asset_id") != "logo-b"


def test_rota_devolve_a_frase_em_error(monkeypatch):
    cli = _cliente(_banco_dois_tenants(), monkeypatch)
    r = cli.post("/api/brand/logo", headers={"X-Internal-Key": CHAVE}, json={
        "company_id": A, "data_base64": base64.b64encode(b"GIF89a....").decode()})
    assert r.status_code == 400 and "PNG, JPG, SVG ou WebP" in r.json()["error"]
    r = cli.patch("/api/brand/profile", headers={"X-Internal-Key": CHAVE},
                  json={"company_id": A, "values": {"founded_year": 1850}})
    assert r.status_code == 400 and "entre 1900 e" in r.json()["error"]


# ==========================================================================
# 2. O ano de fundação
# ==========================================================================

@pytest.mark.parametrize("valor", [1899, 2027, "abc", True, 2011.5, "20111"])
def test_ano_fora_da_faixa_e_recusado(valor):
    with pytest.raises(C.EntradaRecusada, match="entre 1900 e 2026"):
        C.validar_ano_fundacao(valor, ano_atual=2026)


@pytest.mark.parametrize("valor, esperado", [(2011, 2011), ("2011", 2011), (1900, 1900),
                                             (2026, 2026), (None, None), ("", None)])
def test_controle__ano_valido_passa(valor, esperado):
    assert C.validar_ano_fundacao(valor, ano_atual=2026) == esperado


def test_editar_recusa_ano_antes_de_escrever():
    banco = _banco_dois_tenants()
    with pytest.raises(C.EntradaRecusada):
        C.BrandCaptureService(banco).editar(A, {"founded_year": 3000})
    assert banco.escritas == []


# ==========================================================================
# 3. A captura presa
# ==========================================================================

def _perfil_capturando(minutos: float) -> Banco:
    b = Banco()
    quando = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    b.dados["brand_profiles"] = [{"id": "pa", "company_id": A, "capture_status": "capturing",
                                  "updated_at": quando, "palette": {"primary": "#123456"}}]
    return b


def test_capturing_velho_vira_failed_com_o_motivo_e_nada_some():
    banco = _perfil_capturando(C.CAPTURA_VENCE_EM_S / 60 + 1)
    p = C.BrandCaptureService(banco).obter_ou_criar(A)
    assert p["capture_status"] == "failed" and "demorou demais" in p["capture_error"]
    gravado = banco.dados["brand_profiles"][0]
    assert gravado["capture_status"] == "failed" and gravado["palette"] == {"primary": "#123456"}


def test_controle__capturing_recente_continua_capturing():
    banco = _perfil_capturando(2)
    p = C.BrandCaptureService(banco).obter_ou_criar(A)
    assert p["capture_status"] == "capturing" and banco.escritas == []


def test_excecao_no_meio_da_captura_desmarca_capturing(monkeypatch):
    banco = _banco_dois_tenants()
    banco.dados["brand_profiles"][0]["website_url"] = "https://exemplo.invalid"
    svc = C.BrandCaptureService(banco)

    async def quebra(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(svc, "_capturar_marcado", quebra)
    with pytest.raises(RuntimeError):
        asyncio.run(svc.capturar(A))
    p = banco.dados["brand_profiles"][0]
    assert p["capture_status"] == "failed" and "parou no meio" in p["capture_error"]


def test_a_captura_grava_o_logo_do_site_sem_42P10_e_respeita_o_enviado(monkeypatch):
    """📊 A causa provável da AutoFleet presa: o upsert do logo do site batia no 42P10."""
    banco = _banco_dois_tenants()
    svc = C.BrandCaptureService(banco)
    enviado = svc.trocar_logo(A, _png())["asset"]["id"]

    async def baixa(url, allowlist=None):
        return _png(8, 4), "image/png"
    monkeypatch.setattr(C, "baixar_binario", baixa)
    sinais = C.SinaisWeb(url="https://exemplo.invalid", logo_urls=["https://exemplo.invalid/logo.png"])
    res = C.ResultadoCaptura("pa", company_id=A)
    asyncio.run(svc._propor_visual(res, A, "pa", sinais, ["https://exemplo.invalid"], None,
                                   logo_protegido=True))
    da_a = [x for x in banco.dados["brand_assets"] if x["company_id"] == A]
    assert len(da_a) == 2
    assert next(x for x in da_a if x["id"] == enviado)["is_current"] is True   # o enviado segue o atual


# ==========================================================================
# 4. Preto escolhido à mão é marca
# ==========================================================================

def test_preto_escolhido_a_mao_fica_preto_e_o_da_captura_segue_o_padrao():
    banco = _banco_dois_tenants()
    p = C.BrandCaptureService(banco).editar(A, {"palette": {"primary": "#111111", "accent": "#111111"}})
    assert p["palette"]["primary"] == "#111111" and p["palette"]["origin"] == "human"
    assert not [x for m in ("light", "dark") for x in p["palette"]["audit"][m] if not x["passa"]]
    # controle: o caminho da CAPTURA (logo preto lido do site) continua trocando pelo padrão da casa
    from app.services.brand.system import FALLBACK_PRIMARIA, build_design_system
    assert build_design_system("#111111")["primary"] == FALLBACK_PRIMARIA
