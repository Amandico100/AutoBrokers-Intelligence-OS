# -*- coding: utf-8 -*-
"""O AGGER DUBLÊ — SPEC-129-B F2 (borda externa dos testes do robô e do TESTE DO FIO).

Um servidor HTTP local (aiohttp) que imita o que o robô toca no Agger, com as FIXTURES SANEADAS da 128:

    http://agg.localhost:<porta>/login              a tela de login (e-mail, senha, "Entrar"; aviso de sessão ativa)
    http://agg.localhost:<porta>/cotacoes           a tela de entrada: chama pdocs e api com Authorization (o robô
                                                    captura o header), tenta TELEMETRIA (escrita fora da lista) e
                                                    WebSocket; o menu do usuário tem "Sair" (deslogaSessao)
    http://api-prod.agg.localhost:<porta>/…         usuario/login · usuario/login/pdocs · usuario/deslogaSessao ·
                                                    calculo/seguradoras · calculo/calcularV2
    http://pdocs.agg.localhost:<porta>/…            calculo/buscaPlaca · fipeModelo · cep · seguradorasRenovacao ·
                                                    cotacao/versoes/{id} · cotacao/calculos/{id}/{versao}
    http://quotation-files.agg.localhost:<porta>/…  o PDF da oferta

📊 `*.localhost` resolve para o loopback no Chromium: os SUBDOMÍNIOS são os do Agger real (api-prod., pdocs.,
quotation-files.), então `agger_sessao.bases_de` não tem ramo de teste.

🔴 G5: o dublê DEVOLVE DE PROPÓSITO segredos falsos onde o Agger real devolve (📊 a 128: 17/17 senhas no corpo,
28/28 nas consultas): `login/senha/loginWs/senhaWs/token` na config, nas versões e nos itens das rodadas, e a URL
do PDF (com um segredo no caminho) em `resultados[].pathPdf`. Todos começam por `SEGREDO-`; os tokens de sessão,
por `TOKEN-`. O teste procura esses prefixos em tudo que voltou ao Python.

As rodadas: cada GET `calculos/{id}/{v}` AVANÇA uma rodada da fixture (a última se repete) — o tempo do teste é o
das chamadas, não o do relógio.
"""
from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "agger"
EMAIL = "robo@exemplo.invalid"
SENHA = "senha-do-robo-de-teste"
USUARIO_ROBO = "usr-robo-0001"
PDF_BYTES = b"%PDF-1.4\n% PDF do dubl\xc3\xaa\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"


def segredos_do_item(rotulo: str) -> Dict[str, str]:
    return {"login": f"SEGREDO-LOGIN-{rotulo}", "senha": f"SEGREDO-SENHA-{rotulo}",
            "loginWs": f"SEGREDO-LOGINWS-{rotulo}", "senhaWs": f"SEGREDO-SENHAWS-{rotulo}",
            "token": f"SEGREDO-TOKEN-{rotulo}"}


def _agora_iso(delta_h: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=delta_h)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


HTML_LOGIN = """<!doctype html><html><head><meta charset="utf-8"><title>Agger dublê</title></head><body>
<form onsubmit="return false"><input type="email" id="e"><input type="password" id="s">
<button type="button" id="entrar">Entrar</button></form><div id="msg"></div>
<div id="aviso" role="dialog" style="display:none"><p>Você já possui uma sessão ativa em outro dispositivo.</p>
<button type="button" id="prosseguir">Prosseguir</button><button type="button" id="cancelar">Cancelar</button></div>
<script>
const API = location.protocol + '//api-prod.' + location.host;
async function entrar(forcar) {
  const corpo = {email: document.getElementById('e').value, senha: document.getElementById('s').value};
  if (forcar) corpo.forcarLogin = true;
  let r; try { r = await fetch(API + '/usuario/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(corpo)}); }
  catch (e) { document.getElementById('msg').innerText = 'falha de rede'; return; }
  const d = await r.json().catch(() => ({}));
  if (r.status >= 400) { document.getElementById('msg').innerText = 'Login ou senha inválidos'; return; }
  if (d.sessaoAtiva) { document.getElementById('aviso').style.display = 'block'; return; }
  const p = await fetch(API + '/usuario/login/pdocs', {method: 'POST', headers: {Authorization: d.token}});
  const dp = await p.json();
  sessionStorage.setItem('tApi', d.token); sessionStorage.setItem('tPdocs', dp.token);
  location.href = '/cotacoes';
}
document.getElementById('entrar').onclick = () => entrar(false);
// o clique em "Prosseguir" deixa MARCA por uma LEITURA (a guarda deixa passar GET): sem ela, a guarda barraria o
// 2º login e um robô que clicasse "Prosseguir" passaria despercebido pelo teste
document.getElementById('prosseguir').onclick = async () => { await fetch('/marca/prosseguiu').catch(() => {}); entrar(true); };
document.getElementById('cancelar').onclick = () => { document.getElementById('aviso').style.display = 'none'; };
</script></body></html>"""

HTML_COTACOES = """<!doctype html><html><head><meta charset="utf-8"><title>Cotações</title></head><body>
<button type="button" aria-label="Menu do usuário" id="menu" style="position:fixed;right:30px;top:40px">Eu</button>
<div id="itens" style="display:none"><button type="button" id="sair">Sair</button></div>
<h1>Cotações</h1>
<script>
const API = location.protocol + '//api-prod.' + location.host, PD = location.protocol + '//pdocs.' + location.host;
const tApi = sessionStorage.getItem('tApi'), tPdocs = sessionStorage.getItem('tPdocs');
fetch(PD + '/calculo/negocio/busca/v2?page=1', {headers: {Authorization: tPdocs}}).catch(() => {});
fetch(API + '/calculo/seguradoras', {headers: {Authorization: tApi}}).catch(() => {});
fetch(API + '/telemetria/eventos', {method: 'POST', body: '{"e":"pageview"}', headers: {'Content-Type': 'application/json'}}).catch(() => {});
try { new WebSocket('ws://' + location.host + '/ws'); } catch (e) {}
document.getElementById('menu').onclick = () => { document.getElementById('itens').style.display = 'block'; };
document.getElementById('sair').onclick = async () => {
  await fetch(API + '/usuario/deslogaSessao', {method: 'POST', headers: {Authorization: tApi, 'Content-Type': 'application/json'},
    body: JSON.stringify({idSessao: 'sessao-1', token: tApi})});
  location.href = '/login';
};
</script></body></html>"""


class AggerDuble:
    def __init__(self, *, fixture: str = "vivo_conta_b", modo_login: str = "ok") -> None:
        self.modo_login = modo_login                # ok · sessao_ativa · senha_errada
        self.status_calcular: Optional[int] = None  # força a resposta do calcularV2 (ex.: 422, 503) — DEPOIS de registrar o POST
        self.fx = json.loads((FIX / f"{fixture}.json").read_text(encoding="utf-8"))
        r1 = json.loads((FIX / "gravacao_r1.json").read_text(encoding="utf-8"))
        self.fipe_modelo = r1["fipe_modelo"][0]["corpo"]
        self.renov = [dict(x, id=str(500 + i)) for i, x in enumerate(r1["seguradoras_renovacao"][0]["corpo"])]
        self.calculos_fx = [c for c in self.fx["calculos"] if c["rodadas"]]
        pedido_items = self.fx["calculos"][0]["pedido"]["corpo"]["cotacao"]["calculos"]
        self.codigos_do_pedido = sorted({int(i["seguradora"]) for i in pedido_items})
        self.config = self._config(pedido_items)
        # estado observável
        self.negocios: Dict[str, Dict[str, Any]] = {}   # idIntegracao → {negocioId, versoes: [..], gets: {v: n}}
        self.posts_calcular: List[dict] = []
        self.contagem: Dict[str, int] = {}
        self.logins: List[dict] = []
        self.porta: Optional[int] = None
        self._runner: Optional[web.AppRunner] = None

    # ------------------------------------------------------------------ dados
    def _config(self, itens: List[dict]) -> List[dict]:
        base_de = {9: 8, 10: 8, 13: 8, 22: 12}
        codigos = {int(i["seguradora"]) for i in itens}
        nomes = {int(i["seguradora"]): i.get("nomeSeguradora") for i in itens}
        cfg_codigos = {base_de.get(c, c) for c in codigos} | ({13} if 13 in codigos else set())
        out = []
        for c in sorted(cfg_codigos):
            out.append({"id": 9000 + c, "seguradora": c, "nomeSeguradora": nomes.get(c) or f"Seg {c}", "ativo": True,
                        "idIntegracao": f"cfg-{c}", "usuario": f"SEGREDO-LOGIN-usuario-{c}", "percComissao": 10,
                        "percDesconto": 0, "susep": "000000", **segredos_do_item(f"cfg{c}")})
        return out

    @property
    def base(self) -> str:
        return f"http://agg.localhost:{self.porta}"

    def url_pdf(self, n: int) -> str:
        return f"http://quotation-files.agg.localhost:{self.porta}/pdf/SEGREDO-PDF-{n}.pdf"

    def _rodadas_da_versao(self, versao: int) -> List[Any]:
        c = self.calculos_fx[(versao - 1) % len(self.calculos_fx)]
        return [r["corpo"] for r in c["rodadas"]]

    def _com_segredos(self, corpo: List[dict]) -> List[dict]:
        saida = copy.deepcopy(corpo)
        n = 0
        for it in saida:
            if not isinstance(it, dict):
                continue
            it.update(segredos_do_item(f"item{it.get('seguradora')}"))
            for r in it.get("resultados") or []:
                if isinstance(r, dict):
                    n += 1
                    if r.get("pathPdf"):
                        r["pathPdf"] = self.url_pdf(n)
                    if r.get("pdfFileNameAgger"):
                        r["pdfFileNameAgger"] = f"SEGREDO-PDFNOME-{n}.pdf"
        return saida

    def semear_negocio(self, versoes: List[dict]) -> str:
        """Um negócio que JÁ existe (de outra sessão, ou de uma pessoa). Cada versão: {versao, correlationId,
        usuarioId, criada_ha_h, coberturas: {chave: valor}, percComissao}."""
        ref = str(uuid.uuid4())
        neg = {"negocioId": f"neg-{uuid.uuid4().hex[:12]}", "versoes": [], "gets": {}}
        for v in versoes:
            calc = []
            for c in self.config:
                it = {"seguradora": c["seguradora"], "nomeSeguradora": c["nomeSeguradora"],
                      "percComissao": v.get("percComissao", 10), "percDesconto": 0, **segredos_do_item("versao")}
                it.update(v.get("coberturas") or {})
                calc.append(it)
            neg["versoes"].append(self._versao(ref, neg, int(v["versao"]), v.get("correlationId") or str(uuid.uuid4()),
                                               v.get("usuarioId", USUARIO_ROBO), calc, v.get("criada_ha_h", 0.0)))
        self.negocios[ref] = neg
        return ref

    def _versao(self, ref: str, neg: dict, versao: int, cid: str, usuario: str, calculos: List[dict],
                criada_ha_h: float = 0.0, cot: Optional[dict] = None) -> dict:
        base = {k: v for k, v in (cot or {}).items() if k not in ("calculos", "id", "versao", "idIntegracao", "negocioId")}
        return {**base, "id": f"ver-{uuid.uuid4().hex[:10]}", "idIntegracao": ref, "negocioId": neg["negocioId"],
                "versao": versao, "correlationId": cid, "usuarioId": usuario, "usuario": "SEGREDO-LOGIN-email",
                "customerIp": "10.0.0.1", "isAgger": True, "createdAt": _agora_iso(-criada_ha_h),
                "segurado": (cot or {}).get("segurado") or {"nome": "<pessoa>"},
                "automoveis": (cot or {}).get("automoveis") or [{"pctAjuste": 100}],
                "calculos": [dict(c, **segredos_do_item("v")) for c in calculos], "tipo": 5, "ramo": 31}

    # ------------------------------------------------------------------ HTTP
    def _cors(self, req: web.Request, resp: web.StreamResponse) -> web.StreamResponse:
        resp.headers["Access-Control-Allow-Origin"] = req.headers.get("Origin", "*")
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    def _json(self, req: web.Request, dado: Any, status: int = 200) -> web.Response:
        return self._cors(req, web.json_response(dado, status=status))

    async def _tratar(self, req: web.Request) -> web.StreamResponse:
        host = (req.host or "").split(":")[0]
        sub = host[: -len("agg.localhost")].rstrip(".") if host.endswith("agg.localhost") else "?"
        caminho = req.path
        self.contagem[f"{req.method} {sub}{caminho}"] = self.contagem.get(f"{req.method} {sub}{caminho}", 0) + 1
        if req.method == "OPTIONS":
            return self._cors(req, web.Response(status=204))
        if sub == "":
            if caminho == "/login":
                return web.Response(text=HTML_LOGIN, content_type="text/html")
            if caminho == "/cotacoes":
                return web.Response(text=HTML_COTACOES, content_type="text/html")
            return web.Response(status=404)
        if sub == "api-prod":
            return await self._api(req, caminho)
        if sub == "pdocs":
            return await self._pdocs(req, caminho)
        if sub == "quotation-files" and caminho.startswith("/pdf/"):
            return self._cors(req, web.Response(body=PDF_BYTES, content_type="application/pdf"))
        return web.Response(status=404)

    async def _api(self, req: web.Request, caminho: str) -> web.StreamResponse:
        if caminho == "/usuario/login" and req.method == "POST":
            d = await req.json()
            self.logins.append({"forcar": bool(d.get("forcarLogin"))})
            if self.modo_login == "senha_errada" or d.get("email") != EMAIL or d.get("senha") != SENHA:
                return self._json(req, {"message": "Login ou senha inválidos"}, 401)
            if self.modo_login == "sessao_ativa" and not d.get("forcarLogin"):
                return self._json(req, {"sessaoAtiva": True})
            return self._json(req, {"token": "TOKEN-API-" + uuid.uuid4().hex[:8], "idSessao": "sessao-1"}, 201)
        if caminho == "/usuario/login/pdocs" and req.method == "POST":
            return self._json(req, {"token": "TOKEN-PDOCS-" + uuid.uuid4().hex[:8], "expires": 10800,
                                    "urlPDocs": "SEGREDO-URL-PDOCS", "usuario": "SEGREDO-LOGIN-email"}, 201)
        if caminho == "/usuario/deslogaSessao" and req.method == "POST":
            return self._json(req, 1, 201)
        if not (req.headers.get("Authorization") or "").startswith("TOKEN-API-"):
            return self._json(req, {"message": "sem token"}, 401)
        if caminho == "/calculo/seguradoras":
            return self._json(req, self.config)
        if caminho == "/calculo/calcularV2" and req.method == "POST":
            corpo = await req.json()
            self.posts_calcular.append(corpo)
            if self.status_calcular is not None:
                return self._json(req, {"message": f"falha forçada {self.status_calcular}"}, self.status_calcular)
            cot = corpo.get("cotacao") or {}
            ref = cot.get("idIntegracao")
            if ref:
                neg = self.negocios.get(ref)
                if neg is None:
                    return self._json(req, {"message": "negócio não encontrado"}, 404)
            else:
                ref = str(uuid.uuid4())
                neg = {"negocioId": f"neg-{uuid.uuid4().hex[:12]}", "versoes": [], "gets": {}}
                self.negocios[ref] = neg
            versao = max([v["versao"] for v in neg["versoes"]] or [0]) + 1
            neg["versoes"].append(self._versao(ref, neg, versao, corpo.get("correlationId") or "", USUARIO_ROBO,
                                               cot.get("calculos") or [], 0.0, cot))
            return self._json(req, {"idIntegracao": ref, "versao": versao}, 201)
        return self._json(req, {"message": "rota desconhecida"}, 404)

    async def _pdocs(self, req: web.Request, caminho: str) -> web.StreamResponse:
        if not (req.headers.get("Authorization") or "").startswith("TOKEN-PDOCS-"):
            return self._json(req, {"message": "sem token"}, 401)
        if caminho == "/calculo/negocio/busca/v2":
            return self._json(req, [])
        if caminho == "/calculo/buscaPlaca":
            return self._json(req, {"fipe": "0013277", "anoMod": "2012", "anoFab": "2011", "codFabr": 104,
                                    "chassi": "CHASSIDUBLE0000001", "placa": req.query.get("placa"),
                                    "modelo": "MODELO DO DUBLE", "veiculos": []})
        if caminho == "/calculo/fipeModelo":
            return self._json(req, self.fipe_modelo)
        if caminho == "/calculo/cep":
            return self._json(req, {"cep": req.query.get("cep"), "logradouro": "Rua do Dublê", "cidade": "Cidade",
                                    "bairro": "Bairro", "uf": "SC"})
        if caminho == "/calculo/seguradorasRenovacao":
            return self._json(req, self.renov)
        partes = caminho.strip("/").split("/")
        if partes[:3] == ["calculo", "cotacao", "versoes"] and len(partes) == 4:
            neg = self.negocios.get(partes[3])
            return self._json(req, neg["versoes"] if neg else [], 200 if neg else 404)
        if partes[:3] == ["calculo", "cotacao", "calculos"] and len(partes) == 5:
            neg = self.negocios.get(partes[3])
            if not neg:
                return self._json(req, {"message": "não encontrado"}, 404)
            v = int(partes[4])
            n = neg["gets"].get(v, 0)
            neg["gets"][v] = n + 1
            rodadas = self._rodadas_da_versao(v)
            return self._json(req, self._com_segredos(rodadas[min(n, len(rodadas) - 1)]))
        return self._json(req, {"message": "rota desconhecida"}, 404)

    # ------------------------------------------------------------------ ciclo de vida
    async def iniciar(self) -> "AggerDuble":
        app = web.Application()
        app.router.add_route("*", "/{caminho:.*}", self._tratar)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        self.porta = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        return self

    async def parar(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
