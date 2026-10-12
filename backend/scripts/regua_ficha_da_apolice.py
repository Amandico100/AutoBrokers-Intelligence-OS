#!/usr/bin/env python3
"""SPEC-130-B F5 · C6 — A RÉGUA DA FICHA DA APÓLICE: o leitor do PRODUTO sobre os BYTES REAIS.

Para cada apólice da bancada (32, semente 1311 — os localizadores ficam FORA do git, em
`docs/intake/BANCADA-130B/bancada_32.json`), pelo caminho do produto:

    POST /login → GET /documento (o `preliq` = o prêmio líquido esperado, `_expected_net_premium`)
    → o candidato de PDF (`_extract_official_document_candidates`; sem `policy_pdf`,
      `_fetch_policy_attachment_candidate` = `/documento_anexos`, a regra da F2)
    → download EM MEMÓRIA (`_fetch_official_document_candidate_for_policy_pipeline`)
    → `document_service.extrair_paginas_tolerante`
    → `policy_document_evidence_service.ler_documento_de_seguro` com o LEITOR REAL
      (papel `leitura_de_apolice`; o ledger grava `service_type='bancada_130b'`), sem orçamento

e mede Σ prêmio das linhas × prêmio líquido do `/documento`: pelo JUIZ do produto
(max R$ 0,05; 0,5 %) e também por ±2 %.

⛔ Só `/login` e GET na InfoCap, em série, ~0,35 s entre chamadas. Nada é gravado em
   `documents` nem no MinIO: o PDF vive na memória deste processo.
⛔ A saída não tem PII: por `id` + `locator_hash`, só contagens, dinheiro e enums.
   Só o RÓTULO genérico de cobertura das linhas lidas pelo modelo/visão (mascarado, ≤ 60 caracteres —
   conserto único, para o juiz conferir o nome); nenhum nº de apólice, URL, nome, CPF, trecho.
⛔ Credenciais: `docs/intake/BANCADA-130B/corp.env` (fora do git), carregado SÓ neste
   processo. Nunca impressas.

Uso (de backend/):
    python scripts/regua_ficha_da_apolice.py                  # as 32, com o modelo
    python scripts/regua_ficha_da_apolice.py --ids COND-TMAR-09 EMPR-PORT-18
    python scripts/regua_ficha_da_apolice.py --sem-modelo     # só o regex (custo zero)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND = Path(__file__).resolve().parent.parent
RAIZ = BACKEND.parent
sys.path.insert(0, str(BACKEND))

BANCADA = RAIZ / "docs" / "intake" / "BANCADA-130B" / "bancada_32.json"
CREDENCIAIS = RAIZ / "docs" / "intake" / "BANCADA-130B" / "corp.env"
RESULTADOS = BACKEND / "tests" / "corpus" / "bancada" / "RESULTADOS"
SERVICE_TYPE = "bancada_130b"
PAUSA_S = 0.35
BASE_PADRAO = "https://api.corpnuvem.com"

#: SPEC §6 — as metas por ramo (fecham pelo juiz / total com PDF não conta "sem PDF")
METAS = {"RESI": 7, "COND": 7, "EMPR": 5, "AUTO": 5}


def _carregar_ambiente() -> None:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
    if not CREDENCIAIS.exists():
        raise SystemExit("credenciais da bancada ausentes (docs/intake/BANCADA-130B/corp.env)")
    load_dotenv(CREDENCIAIS, override=True)


def _credencial(banco: str) -> Dict[str, str]:
    slug = banco.strip().upper()
    login = os.getenv(f"CORP_INFOCAP_{slug}_LOGIN", "")
    senha = os.getenv(f"CORP_INFOCAP_{slug}_PASSWORD", "")
    if not login or not senha:
        raise SystemExit(f"credencial do banco '{banco}' incompleta em corp.env (só o NOME é dito)")
    return {"email": login, "senha": senha}


def _decimal(valor: Any) -> Optional[Decimal]:
    try:
        return None if valor in (None, "") else Decimal(str(valor))
    except Exception:  # noqa: BLE001
        return None


def _degraus_sem_pii(degraus: Any) -> List[Dict[str, Any]]:
    saida = []
    for d in degraus or []:
        if not isinstance(d, dict):
            continue
        saida.append({k: d.get(k) for k in ("degrau", "linhas", "soma", "fecha", "venceu", "descartadas",
                                            "motivos_do_descarte", "erro", "duracao_s", "paginas_enviadas")
                      if k in d})
    return saida


def _rotulos_do_modelo(itens: Any) -> List[Dict[str, Any]]:
    """🔴 conserto único (juiz B1): por linha lida pelo MODELO/VISÃO, o RÓTULO genérico da cobertura — para o
    juiz conferir o nome, não só a soma. ⛔ Sem trecho, sem limite: só rótulo (mascarado e cortado), página,
    prêmio e de que degrau veio. Rótulo de cobertura não é dado pessoal ("Incêndio", "Danos Elétricos")."""
    from app.services.policy_document_evidence_service import mascarar_texto_de_apolice

    saida = []
    for item in itens or []:
        e = (item or {}).get("structured") or {}
        metodo = (item or {}).get("extraction_method")
        if e.get("kind") != "coverage_row" or metodo not in ("modelo", "visao"):
            continue
        saida.append({"pagina": item.get("page_number"), "degrau": metodo,
                      "rotulo": mascarar_texto_de_apolice(str(e.get("label") or ""))[:60],
                      "premio": e.get("premium"), "tem_limite": bool(e.get("lmi"))})
    return saida


class _Corp:
    """Cliente mínimo da InfoCap: login uma vez por banco, GET em série com pausa."""

    def __init__(self, httpx_mod, base_url: str):
        self.httpx = httpx_mod
        self.base_url = base_url
        self.client = None
        self.tokens: Dict[str, Any] = {}
        self._ultima = 0.0

    async def __aenter__(self):
        self.client = self.httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        return self

    async def __aexit__(self, *exc):
        await self.client.aclose()

    async def _pausa(self):
        espera = PAUSA_S - (time.monotonic() - self._ultima)
        if espera > 0:
            await asyncio.sleep(espera)
        self._ultima = time.monotonic()

    async def sessao(self, banco: str):
        if banco not in self.tokens:
            from app.api.infocap_connector import _extract_token

            await self._pausa()
            res = await self.client.post("/login", json={**_credencial(banco), "aplicacao": 0})
            if res.status_code >= 400:
                raise SystemExit(f"login do banco '{banco}' recusado (http {res.status_code})")
            try:
                token = _extract_token(res.json())
            except Exception:  # noqa: BLE001
                token = (res.text or "").strip() or None
            if not token:
                raise SystemExit(f"login do banco '{banco}' sem token")
            self.tokens[banco] = (token, res.cookies)
        token, cookies = self.tokens[banco]
        return {"Authorization": token, "Content-Type": "application/json"}, token, cookies

    async def get(self, caminho: str, params: Dict[str, Any], headers: Dict[str, str]):
        await self._pausa()
        return await self.client.get(caminho, params=params, headers=headers)


async def _medir_uma(corp: _Corp, apolice: Dict[str, Any], *, com_modelo: bool) -> Dict[str, Any]:
    import app.api.infocap_connector as C
    from app.services import policy_document_evidence_service as S
    from app.services.document_service import extrair_paginas_tolerante

    # ⛔ CLAUDE.md §13.9: o `banco` (qual corretora) NÃO vai à saída — ela entra no git.
    linha: Dict[str, Any] = {
        "id": apolice["id"], "locator_hash": apolice.get("locator_hash"),
        "ramo": apolice.get("ramo"), "seguradora": apolice.get("seguradora"),
    }
    inicio = time.monotonic()
    headers, token, cookies = await corp.sessao(apolice["banco"])
    params = {"codfil": apolice["codfil"], "nosnum": apolice["nosnum"]}

    det = await corp.get("/documento", params, headers)
    if det.status_code >= 400:
        linha.update({"fonte_do_pdf": "sem_documento", "http_documento": det.status_code})
        return linha
    envelope = det.json()
    esperado = C._expected_net_premium(envelope)
    linha["esperado"] = str(esperado) if esperado is not None else None

    # o candidato — a MESMA regra de `_maybe_attach_official_policy_document_evidence`
    candidatos = C._extract_official_document_candidates(envelope if isinstance(envelope, dict) else {})
    if not any(c.get("source_kind") == "policy_pdf" for c in candidatos):
        await corp._pausa()
        anexo = await C._fetch_policy_attachment_candidate(
            corp.client, headers, anexos_path="/documento_anexos",
            codfil=apolice["codfil"], nosnum=apolice["nosnum"], company_id="bancada-130b")
        if anexo:
            candidatos = [anexo, *candidatos]
    escolhido = next((c for c in candidatos if c.get("source_kind") == "policy_pdf"),
                     candidatos[0] if candidatos else None)
    if not escolhido:
        linha["fonte_do_pdf"] = "sem_pdf"
        return linha
    linha["fonte_do_pdf"] = escolhido.get("source_path")
    linha["tipo_da_fonte"] = escolhido.get("source_kind")

    await corp._pausa()
    baixado = await C._fetch_official_document_candidate_for_policy_pipeline(
        candidate=escolhido, token=token, auth_cookies=cookies, credential_origin_url=corp.base_url)
    if not baixado.get("ok"):
        linha.update({"fonte_do_pdf": linha["fonte_do_pdf"], "download": baixado.get("status"),
                      "download_bloqueio": [str(b)[:60] for b in (baixado.get("blockers") or [])][:3]})
        return linha
    corpo: bytes = baixado["body"]
    linha["bytes"] = len(corpo)

    try:
        pages, parser, total = await asyncio.to_thread(extrair_paginas_tolerante, corpo)
    except Exception as exc:  # noqa: BLE001
        linha.update({"pipeline": "caiu_na_extracao", "erro": type(exc).__name__})
        return linha

    conteudo_hash = hashlib.sha256(corpo).hexdigest()

    async def _leitor_texto(texto: str, *, company_id: str):
        return await S._leitor_modelo_padrao(texto, company_id=None, service_type=SERVICE_TYPE)

    async def _leitor_imagem(imagens, *, company_id: str):
        return await S._leitor_visao_padrao(imagens, company_id=None, service_type=SERVICE_TYPE)

    resultado = await S.ler_documento_de_seguro(
        pages, company_id="", premio_esperado=esperado, fonte_do_esperado="corp",
        file_bytes=corpo, total_paginas=total, parser_por_pagina=parser,
        permitir_modelo=com_modelo, leitor_modelo=_leitor_texto, leitor_visao=_leitor_imagem,
        document_id="bancada-" + apolice["id"], content_hash=conteudo_hash,
        policy_locator={"provider": "infocap", "codfil": str(apolice["codfil"]),
                        "nosnum": str(apolice["nosnum"])},
    )
    leitura = resultado.get("leitura") or {}
    soma = _decimal(leitura.get("soma_linhas"))
    fecha_2pct = None
    if soma is not None and esperado:
        fecha_2pct = abs(soma - esperado) <= (esperado * Decimal("0.02"))
    degraus = leitura.get("degraus") or []
    regex = next((d for d in degraus if isinstance(d, dict) and d.get("degrau") == "regex"), {})
    linha.update({
        "paginas": leitura.get("paginas"),
        "paginas_sem_texto": len(leitura.get("paginas_sem_texto") or []),
        "parser_por_pagina": dict(Counter((leitura.get("parser_por_pagina") or {}).values())),
        "tipo_documento": leitura.get("tipo_documento"),
        "estado": leitura.get("estado"),
        "motivo": leitura.get("motivo"),
        "degraus": _degraus_sem_pii(degraus),
        "linhas": leitura.get("linhas"),
        "soma": leitura.get("soma_linhas"),
        "diferenca": leitura.get("diferenca"),
        "fecha_juiz": leitura.get("estado") == "fechou",
        "fecha_pelo_regex": bool(regex.get("fecha")),
        "fecha_2pct": fecha_2pct,
        "custo_usd_estimado": leitura.get("custo_usd"),
        "modelo": leitura.get("modelo"),
        "duracao_leitura_s": leitura.get("duracao_s"),
        "conferencia": leitura.get("conferencia"),
        "texto_ao_modelo": leitura.get("texto_ao_modelo"),
        # o que entrou na ficha pelo modelo/visão, e o que ficou SÓ no registro (não fechou — J3)
        "rotulos_do_modelo": _rotulos_do_modelo(resultado.get("evidence_items")),
        "rotulos_nao_conferidos": _rotulos_do_modelo(resultado.get("linhas_nao_conferidas")),
    })
    linha["duracao_s"] = round(time.monotonic() - inicio, 2)
    return linha


def _familia(apolice_id: str) -> str:
    return apolice_id.split("-", 1)[0]


def _resumo(linhas: List[Dict[str, Any]], controle: List[str]) -> str:
    por: Dict[str, Dict[str, int]] = defaultdict(lambda: Counter())
    for l in linhas:
        f = _familia(l["id"])
        por[f]["total"] += 1
        com_pdf = l.get("estado") is not None
        por[f]["com_pdf"] += int(com_pdf)
        por[f]["sem_pdf"] += int(l.get("fonte_do_pdf") in ("sem_pdf", "sem_documento"))
        por[f]["juiz"] += int(bool(l.get("fecha_juiz")))
        por[f]["2pct"] += int(bool(l.get("fecha_2pct")))
        por[f]["caiu"] += int(bool(l.get("pipeline")) or l.get("estado") == "falhou"
                              or bool(l.get("download")))
    out = ["", "ramo  total  com_pdf  sem_pdf  fecha(juiz)  fecha(±2%)  caiu  meta"]
    for f in ("RESI", "COND", "EMPR", "AUTO"):
        c = por.get(f, Counter())
        out.append(f"{f:<5} {c['total']:>5}  {c['com_pdf']:>7}  {c['sem_pdf']:>7}  {c['juiz']:>11}  "
                   f"{c['2pct']:>10}  {c['caiu']:>4}  >= {METAS[f]}  {'OK' if c['juiz'] >= METAS[f] else 'ABAIXO'}")
    tot = Counter()
    for c in por.values():
        tot.update(c)
    out.append(f"TOTAL {tot['total']:>5}  {tot['com_pdf']:>7}  {tot['sem_pdf']:>7}  {tot['juiz']:>11}  "
               f"{tot['2pct']:>10}  {tot['caiu']:>4}")
    out.append("")
    out.append("controle (as 11 de hoje): id · fecha(juiz) · pelo regex · custo")
    por_id = {l["id"]: l for l in linhas}
    intactas = 0
    for cid in controle:
        l = por_id.get(cid)
        if l is None:
            out.append(f"  {cid:<14} (não medida nesta rodada)")
            continue
        ok = bool(l.get("fecha_juiz")) and bool(l.get("fecha_pelo_regex")) and not l.get("custo_usd_estimado")
        intactas += int(ok)
        out.append(f"  {cid:<14} {str(l.get('fecha_juiz')):<5} {str(l.get('fecha_pelo_regex')):<5} "
                   f"{l.get('custo_usd_estimado')}  {'OK' if ok else 'QUEBROU'}")
    out.append(f"  intactas: {intactas}/{len([c for c in controle if c in por_id])}")
    custo = sum(float(l.get("custo_usd_estimado") or 0) for l in linhas)
    out.append(f"\ncusto estimado da rodada (o real é o ledger, service_type='{SERVICE_TYPE}'): US$ {custo:.4f}")
    return "\n".join(out)


async def _rodar(args) -> int:
    import httpx

    bancada = json.loads(BANCADA.read_text(encoding="utf-8"))
    apolices = bancada["apolices"]
    if args.ids:
        pedidos = set(args.ids)
        apolices = [a for a in apolices if a["id"] in pedidos]
    controle = list(bancada.get("fecham_hoje") or [])
    linhas: List[Dict[str, Any]] = []
    custo = 0.0
    base = os.getenv("CORP_INFOCAP_BASE_URL") or BASE_PADRAO
    async with _Corp(httpx, base) as corp:
        for apolice in apolices:
            try:
                linha = await _medir_uma(corp, apolice, com_modelo=not args.sem_modelo)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001 — ⛔ só o TIPO, nunca a mensagem (pode ter URL)
                linha = {"id": apolice["id"], "locator_hash": apolice.get("locator_hash"),
                         "ramo": apolice.get("ramo"), "seguradora": apolice.get("seguradora"),
                         "pipeline": "excecao", "erro": type(exc).__name__}
            linhas.append(linha)
            custo += float(linha.get("custo_usd_estimado") or 0)
            print(f"{linha['id']:<14} fonte={str(linha.get('fonte_do_pdf')):<36} estado={str(linha.get('estado')):<24} "
                  f"linhas={str(linha.get('linhas')):<4} soma={str(linha.get('soma')):<12} "
                  f"esperado={str(linha.get('esperado')):<12} juiz={linha.get('fecha_juiz')} "
                  f"2%={linha.get('fecha_2pct')} custo={linha.get('custo_usd_estimado')} "
                  f"t={linha.get('duracao_s')}", flush=True)
            if custo > args.teto_usd:
                print(f"🛑 custo estimado US$ {custo:.4f} passou do teto US$ {args.teto_usd} — PAREI", flush=True)
                break

    RESULTADOS.mkdir(parents=True, exist_ok=True)
    saida = Path(args.saida) if args.saida else RESULTADOS / f"ficha_da_apolice_{date.today():%Y%m%d}.json"
    documento = {
        "spec": "SPEC-130-B F5 · C6", "semente": bancada.get("semente"), "leitor_versao": None,
        "com_modelo": not args.sem_modelo, "service_type": SERVICE_TYPE, "medido_em": date.today().isoformat(),
        "controle": controle, "apolices": linhas,
    }
    try:
        from app.services.policy_document_evidence_service import LEITOR_VERSAO

        documento["leitor_versao"] = LEITOR_VERSAO
    except Exception:  # noqa: BLE001
        pass
    saida.write_text(json.dumps(documento, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(_resumo(linhas, controle))
    print(f"\nsaída: {saida.relative_to(BACKEND) if saida.is_relative_to(BACKEND) else saida}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ids", nargs="*", help="só estes ids da bancada")
    p.add_argument("--sem-modelo", action="store_true", help="só o regex (custo zero)")
    p.add_argument("--teto-usd", type=float, default=0.50, help="para a rodada acima deste custo estimado")
    p.add_argument("--saida", help="arquivo de saída (padrão: RESULTADOS/ficha_da_apolice_<data>.json)")
    args = p.parse_args()
    logging.basicConfig(level=logging.ERROR)
    _carregar_ambiente()
    return asyncio.run(_rodar(args))


if __name__ == "__main__":
    raise SystemExit(main())
