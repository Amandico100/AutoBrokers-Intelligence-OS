# -*- coding: utf-8 -*-
"""BLOCO 0 da SPEC-131-A — medições AO VIVO no Agger (A1 · A7 · A11 · B4 · licença). Rascunho de MEDIÇÃO, não produto.

    cd backend
    PORTAL_HEADLESS_MODE=classic PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/bloco0_131a_agger_ao_vivo.py \
        --env <arquivo .env FORA do git> --saida <json FORA do git> --conta <PREFIXO> <prosseguir|leitura|pessoa>

    --conta PREFIXO  a credencial vem do ambiente em <PREFIXO>_LOGIN / <PREFIXO>_PASSWORD — o operador escolhe a conta
                     (CLAUDE.md §13.9: nenhum nome de corretora no código; a conta é argumento, nunca constante)

    prosseguir  A1+A11: o login de uma conta de ROBÔ (cotador@) em DOIS contextos; no 2º, o aviso de sessão ativa → "Prosseguir"
                (SÓ nesta conta de robô). Grava método, caminho, chaves de query e a FORMA do corpo (valores redigidos);
                mede quando o 1º contexto percebe (API e tela). Logout dos dois + um 3º login de conferência (fantasma?).
    leitura     B4+licença: uma conta de robô (cotador@), só leitura — aviso de licença na tela, a assinatura, e a URL que o
                CLIQUE num negócio produz. Depois, num contexto SEM login, a mesma URL (redireciona? guarda o destino?).
    pessoa      A7: uma conta de PESSOA, SÓ LEITURA. Aviso de sessão ativa → SÓ "Cancelar" e para.
⛔ Credenciais só do ambiente; nada de e-mail, CPF, nome, placa ou id de negócio na saída (ids viram <id>, valores <redigido>).
⛔ Nenhum `goto` numa sessão viva: só a 1ª carga de /login e cliques. A guarda de produção (agger_guarda) no contexto do robô.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlsplit

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
RE_DIGITOS = re.compile(r"\d[\d.\-/]{5,}\d")
RE_ID = re.compile(r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}|\b\d{4,}\b", re.I)
RE_PROSSEGUIR = re.compile(r"^\s*Prosseguir\s*$", re.I)
RE_UI_CAIU = re.compile(r"sess[aã]o[^.]{0,40}(encerr|expir|finaliz|inv[aá]lid|derrub)|desconectad|outro (dispositivo|local|navegador)"
                        r"|fa[cç]a login novamente|entrou em outro", re.I)
RE_LICENCA = re.compile(r"licen[cç]a|assinatura|plano[^.]{0,20}(venc|expir)|venc(e|eu|ida|imento)|expir", re.I)
FLAGS_TEXTO = {"s", "n", "sim", "nao", "não", "true", "false"}


def limpo(texto: Any, n: int = 160) -> str:
    t = RE_EMAIL.sub("<email>", str(texto or ""))
    t = RE_DIGITOS.sub("<num>", t)
    return re.sub(r"\s+", " ", t).strip()[:n]


def caminho_limpo(url: str) -> Dict[str, Any]:
    p = urlsplit(url or "")
    return {"host": (p.hostname or "").lower(), "caminho": RE_ID.sub("<id>", p.path or ""),
            "query_chaves": sorted(parse_qs(p.query, keep_blank_values=True).keys())}


def forma(v: Any, prof: int = 0) -> Any:
    """A FORMA de um JSON: chaves e tipos. Booleanos e flags curtas (S/N) ficam; o resto vira <tipo>."""
    if prof > 6:
        return "<...>"
    if isinstance(v, dict):
        return {k: forma(x, prof + 1) for k, x in v.items()}
    if isinstance(v, list):
        return {"<lista>": len(v), "item": forma(v[0], prof + 1) if v else None}
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return "<num>"
    if isinstance(v, str) and v.strip().lower() in FLAGS_TEXTO:
        return v
    return f"<str:{len(str(v))}>"


def forma_do_corpo(corpo: Optional[str]) -> Any:
    if corpo is None:
        return None
    if not corpo:
        return "<vazio>"
    try:
        return forma(json.loads(corpo))
    except Exception:  # noqa: BLE001
        try:
            q = parse_qs(corpo, keep_blank_values=True)
            if q:
                return {"<form>": sorted(q.keys())}
        except Exception:  # noqa: BLE001
            pass
        return f"<nao-json:{len(corpo)}>"


#: o PREFIXO da conta medida (argumento `--conta`) — nunca um nome de corretora no código (CLAUDE.md §13.9)
CONTA: Dict[str, Optional[str]] = {"prefixo": None}


def credencial() -> "tuple[str, str]":
    """(login, senha) de `<PREFIXO>_LOGIN` / `<PREFIXO>_PASSWORD` no ambiente carregado do `--env`."""
    prefixo = CONTA["prefixo"]
    if not prefixo:
        raise SystemExit("RECUSADO: esta medição precisa de --conta <PREFIXO> (a credencial vem do ambiente)")
    return os.environ[f"{prefixo}_LOGIN"], os.environ[f"{prefixo}_PASSWORD"]


def carregar_env(caminho: str) -> None:
    p = Path(caminho).resolve()
    try:
        p.relative_to(BACKEND.parent.resolve())
        raise SystemExit("RECUSADO: o --env precisa estar FORA do repositório")
    except ValueError:
        pass
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ------------------------------------------------------------------ memória (A11)
def memoria(rotulo: str, saida: Dict[str, Any]) -> None:
    try:
        import psutil  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        saida.setdefault("memoria", []).append({"rotulo": rotulo, "erro": "psutil ausente"})
        return
    filhos = [p for p in psutil.Process(os.getpid()).children(recursive=True)]
    chrome = [p for p in filhos if re.search(r"chrom|headless", (p.name() or ""), re.I)]
    rss = uss = 0
    for p in chrome:
        try:
            rss += p.memory_info().rss
            uss += p.memory_full_info().uss
        except Exception:  # noqa: BLE001
            pass
    saida.setdefault("memoria", []).append({"rotulo": rotulo, "processos_chromium": len(chrome),
                                            "rss_mb": round(rss / 2**20, 1), "uss_mb": round(uss / 2**20, 1),
                                            "t": round(time.time(), 1)})


# ------------------------------------------------------------------ helpers de página
async def visivel(locator: Any) -> Any:
    for i in range(await locator.count()):
        el = locator.nth(i)
        try:
            if await el.is_visible():
                return el
        except Exception:  # noqa: BLE001
            continue
    return None


async def fetch_status(pagina: Any, url: str, token: str) -> Dict[str, Any]:
    return await pagina.evaluate(
        """async ([u, a]) => { try { const r = await fetch(u, {headers: {Authorization: a}});
             let n = null; try { const j = await r.json(); n = Array.isArray(j) ? j.length : (j && typeof j === 'object' ? Object.keys(j).length : null); } catch (e) {}
             return {s: r.status, n}; } catch (e) { return {s: -1, erro: String(e).slice(0, 80)}; } }""", [url, token])


async def fetch_json(pagina: Any, url: str, token: str) -> Any:
    return await pagina.evaluate(
        """async ([u, a]) => { try { const r = await fetch(u, {headers: {Authorization: a}});
             let j = null; try { j = await r.json(); } catch (e) {} return {s: r.status, j}; }
             catch (e) { return {s: -1, j: null}; } }""", [url, token])


def resumo_busca(j: Any) -> Dict[str, Any]:
    """busca/v2 → SÓ contagens: linhas, negócios distintos (hash), e as chaves de usuário com a contagem de valores distintos."""
    linhas = j if isinstance(j, list) else (j.get("content") or j.get("dados") or j.get("data") or []) if isinstance(j, dict) else []
    out: Dict[str, Any] = {"tipo": type(j).__name__, "linhas": len(linhas)}
    if isinstance(j, dict):
        out["chaves_topo"] = sorted(j.keys())[:20]
    if linhas and isinstance(linhas[0], dict):
        chaves = sorted(linhas[0].keys())
        out["chaves_da_linha"] = chaves
        for k in chaves:
            if re.search(r"usu|user|vend|produt|corret|criad|respons|operad|login", k, re.I):
                vals = {hashlib.sha256(json.dumps(x.get(k), sort_keys=True, default=str).encode()).hexdigest()[:10]
                        for x in linhas}
                out.setdefault("distintos_por_chave_de_usuario", {})[k] = len(vals)
        for k in chaves:
            if re.search(r"^(id|idIntegracao|negocioId|idNegocio)$", k, re.I):
                out["negocios_distintos"] = len({str(x.get(k)) for x in linhas})
                break
    return out


NAV_TIMEOUT_MS = 120000   # 📊 12/10 18:5x: a 1ª carga de /login levou 32–90 s em 3 de 6 tentativas (o padrão é 30 s)


ESCUTA: Dict[str, Dict[str, Any]] = {}
BUSCA_DO_APP: Dict[str, str] = {}      # rótulo → URL crua da 1ª busca/v2 do app (só memória; nunca sai)


def classe(v: str) -> str:
    if v == "":
        return "vazio"
    if re.fullmatch(r"[\d,]{1,60}", v):
        return f"codigos:{v}"
    if re.fullmatch(r"[0-9a-f-]{32,36}", v, re.I):
        return f"uuid#{h(v)}"
    if v.lower() in ("true", "false", "asc", "desc"):
        return v
    return f"<str:{len(v)}>"
CAMPOS_DE_LICENCA = ("licenca", "expirationDate", "dataLimiteCalculo", "statusCorretora", "licencaCortesia", "qtdeLicenca",
                     "diasParaExpirarSenha", "senhaRequerAlteracao", "usuarioRestrito", "visualizacaoCalc", "hub", "status",
                     "aplicacaoOrigem", "expires")
RE_QUERY_SEGURA = re.compile(r"^[\w,.:-]{1,24}$")
RE_CHAVE_PROIBIDA = re.compile(r"text|busca|cpf|cnpj|nome|placa|email|fone|doc", re.I)


def h(v: Any) -> str:
    t = str(v or "")
    if t.lower().startswith("bearer "):
        t = t[7:]
    return hashlib.sha256(t.encode()).hexdigest()[:12] if t else ""


def _hashes_de_sessao(j: Any, pref: str = "") -> Dict[str, str]:
    out: Dict[str, str] = {}
    if isinstance(j, dict):
        for k, v in j.items():
            if isinstance(v, dict):
                out.update(_hashes_de_sessao(v, pref + k + "."))
            elif isinstance(v, str) and re.search(r"^(id|token|idSessao|sessao\w*|usuarioId|idIntegracao)$", k, re.I):
                out[pref + k] = h(v)
    return out


def escutar(ctx: Any, rotulo: str) -> None:
    """Grava, por contexto: as respostas de login (campos de licença/estado + HASHES de id/token) e os GET do app
    (caminho + query SEGURA). Nada de valor pessoal."""
    e = ESCUTA.setdefault(rotulo, {"logins": [], "gets": []})

    async def resp(r: Any) -> None:
        try:
            cl = caminho_limpo(r.url)
            if not re.search(r"/usuario/(login(/pdocs)?|current)$", cl["caminho"]):
                return
            j = await r.json()
            item = {"caminho": cl["caminho"], "status": r.status, "metodo": r.request.method,
                    "hashes": _hashes_de_sessao(j)}
            for fonte in (j, (j or {}).get("data") if isinstance(j, dict) else None):
                if isinstance(fonte, dict):
                    for k in CAMPOS_DE_LICENCA:
                        if k in fonte and (isinstance(fonte[k], (bool, int, float)) or fonte[k] is None
                                           or (isinstance(fonte[k], str) and len(fonte[k]) <= 30)):
                            item.setdefault("campos", {})[k] = fonte[k]
            if isinstance(j, dict) and isinstance(j.get("message"), str):
                item["message"] = limpo(j["message"], 120)
            e["logins"].append(item)
        except Exception:  # noqa: BLE001
            pass

    def req(r: Any) -> None:
        try:
            if r.method.upper() != "GET" or r.resource_type not in ("xhr", "fetch"):
                return
            p = urlsplit(r.url)
            if p.path.endswith("/calculo/negocio/busca/v2") and "modo=" in p.query and rotulo not in BUSCA_DO_APP:
                BUSCA_DO_APP[rotulo] = r.url
            q = {k: classe(v[0] or "") for k, v in parse_qs(p.query, keep_blank_values=True).items()}
            linha = {"host": (p.hostname or "").split(".")[0], "caminho": RE_ID.sub("<id>", p.path), "query": q}
            if linha not in e["gets"] and len(e["gets"]) < 60:
                e["gets"].append(linha)
        except Exception:  # noqa: BLE001
            pass

    ctx.on("response", lambda r: asyncio.ensure_future(resp(r)))
    ctx.on("request", req)


class NavPaciente:
    """O navegador com timeout de navegação de 120 s em todo contexto novo (só a MEDIÇÃO; o produto usa 30 s),
    e a escuta (`escutar`) ligada antes da 1ª aba."""

    def __init__(self, nav: Any, rotulo: str) -> None:
        self._nav = nav
        self._rotulo = rotulo

    async def new_context(self, **kw: Any) -> Any:
        ctx = await self._nav.new_context(**kw)
        ctx.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        escutar(ctx, self._rotulo)
        return ctx


def nova_sessoes(nav: Any, rotulo: str = "sessao"):
    from portal_worker.multicalculo.agger_sessao import Sessoes  # noqa: PLC0415
    return Sessoes(NavPaciente(nav, rotulo), url_base=os.environ.get("AGGER_URL_BASE", "https://aggilizador.com.br"))


async def contar_negocios(pagina: Any, bases: Dict[str, str], token: str) -> Dict[str, Any]:
    """busca/v2 por ramo (📊 129-C: `?ramos=<r>&periodo=730`) — só contagens."""
    from urllib.parse import urlencode  # noqa: PLC0415
    out: Dict[str, Any] = {}
    crua = next(iter(BUSCA_DO_APP.values()), None)
    if not crua:
        out["erro"] = "o app não fez a busca/v2 (sem molde)"
        return out
    pu = urlsplit(crua)
    base_q = {k: v[0] for k, v in parse_qs(pu.query, keep_blank_values=True).items()}
    variantes = {"como_o_app_730d": {"periodo": "730", "limit": "500", "page": "1"},
                 "usuario_vazio_730d": {"periodo": "730", "limit": "500", "page": "1", "usuario": ""}}
    for nome, troca in variantes.items():
        q = dict(base_q, **troca)
        j = await fetch_json(pagina, f"{bases['pdocs']}{pu.path}?{urlencode(q)}", token)
        out[nome] = {"status": j.get("s"), **resumo_busca(j.get("j"))}
    return out


async def logout_por_clique(sessoes: Any, sessao: Any, saida: Dict[str, Any], rotulo: str) -> None:
    """Logout pela TELA sem `goto`: se não estiver em /cotacoes, clica o menu Cotações antes (como gente)."""
    t0 = time.time()
    try:
        p = sessao.pagina
        if "/cotacoes" not in p.url:
            link = await visivel(p.get_by_text(re.compile(r"^\s*Cota[cç][oõ]es\s*$", re.I)))
            if link is not None:
                await link.click()
                await asyncio.sleep(2)
        if "/cotacoes" not in p.url:
            saida[rotulo] = {"ok": False, "motivo": "fora de /cotacoes; não fiz goto", "url": caminho_limpo(p.url)}
            return
        ok = await asyncio.wait_for(sessoes._sair(sessao), timeout=30)
        saida[rotulo] = {"ok": bool(ok), "s": round(time.time() - t0, 1)}
    except BaseException as e:  # noqa: BLE001
        if isinstance(e, asyncio.CancelledError):
            raise
        saida[rotulo] = {"ok": False, "erro": type(e).__name__, "s": round(time.time() - t0, 1)}


# ------------------------------------------------------------------ A1: o Prosseguir
async def medir_prosseguir(nav: Any, saida: Dict[str, Any]) -> None:
    from portal_worker.multicalculo import agger_guarda as G  # noqa: PLC0415
    from portal_worker.multicalculo.agger_sessao import RE_AVISO, SELETOR_DIALOGO, Sessao, SessaoOcupada  # noqa: PLC0415

    usuario, senha = credencial()
    conta = {"id": "a1-ctx1", "username": usuario, "robo_estado": "ativo"}
    memoria("navegador_sem_contexto", saida)
    websockets: List[Dict[str, Any]] = []
    if os.environ.get("BLOCO0_CTX1_COM_WEBSOCKET") == "1":
        from portal_worker.multicalculo import agger_sessao as AS  # noqa: PLC0415

        async def instalar_sem_ws(contexto: Any, estado: Any) -> None:
            async def rota1(route: Any, request: Any) -> None:
                m = (request.method or "").upper()
                corpo = ""
                if m not in G.LEITURA:
                    buf = request.post_data_buffer
                    corpo = buf.decode("utf-8", "ignore") if buf is not None else ""
                ok, motivo = G.decidir(m, request.url, corpo, estado, tipo_de_recurso=getattr(request, "resource_type", None))
                if ok and motivo == "login":
                    estado.logins += 1
                if ok:
                    await route.continue_()
                else:
                    estado.barradas += 1
                    await route.abort("blockedbyclient")
            await contexto.route("**/*", rota1)

            def ws(w: Any) -> None:
                item = {"host": caminho_limpo(w.url)["host"], "abriu_t": round(time.time(), 1), "quadros_recebidos": 0,
                        "fechou_t": None}
                websockets.append(item)
                w.on("framereceived", lambda _f: item.__setitem__("quadros_recebidos", item["quadros_recebidos"] + 1))
                w.on("close", lambda _w: item.__setitem__("fechou_t", round(time.time(), 1)))
            contexto.on("websocket", ws)
        AS.instalar = instalar_sem_ws
        saida["ctx1_modo"] = "como_pessoa: escrita na lista branca da guarda, WebSocket LIVRE"

    # ---- contexto 1: a sessão do PRODUTO (Sessoes + guarda de produção)
    s1 = nova_sessoes(nav, "ctx1")
    t = time.time()
    try:
        ctx1 = await s1.obter(conta, senha=senha, negocios_do_robo=set())
    except SessaoOcupada:
        saida["ctx1"] = {"entrou": False, "motivo": "aviso de sessão ativa JÁ no 1º login → Cancelar (fantasma?)"}
        return
    saida["ctx1"] = {"entrou": True, "login_s": round(time.time() - t, 1)}
    memoria("ctx1_logado", saida)
    b = s1.bases
    saida["ctx1"]["negocios_730d"] = await contar_negocios(ctx1.pagina, b, ctx1.token("pdocs"))

    async def sondar(pg: Any, tok_api: str, tok_pdocs: str) -> Dict[str, Any]:
        ra = await fetch_status(pg, b["api"] + "/calculo/seguradoras", tok_api)
        rc = await fetch_status(pg, b["api"] + "/usuario/current", tok_api)
        # a MESMA busca que o app faz ao abrir /cotacoes (molde do ctx1), com limit=1 — a de "?ramos=&periodo=" dá 400
        crua = BUSCA_DO_APP.get("ctx1")
        alvo = (crua.replace("limit=40", "limit=1") if crua
                else b["pdocs"] + "/calculo/negocio/busca/v2?ramos=31&periodo=30")
        rp = await fetch_status(pg, alvo, tok_pdocs)
        return {"api_seguradoras": ra.get("s"), "api_current": rc.get("s"), "pdocs_busca": rp.get("s")}

    saida["ctx1"]["controle_antes_do_clique"] = await sondar(ctx1.pagina, ctx1.token("api"), ctx1.token("pdocs"))
    saida["ctx1"]["hash_tokens"] = {"api": h(ctx1.token("api")), "pdocs": h(ctx1.token("pdocs"))}

    # ---- contexto 2: o MESMO login, guarda de MEDIÇÃO (registra tudo; deixa o Prosseguir passar SÓ nesta conta de robô)
    reqs: List[Dict[str, Any]] = []
    resps: List[Dict[str, Any]] = []
    scripts_txt: List[str] = []
    estado2 = G.EstadoDaGuarda(host_api=b["host_api"])
    clique = {"t": None}
    contadores = {"login": 0, "outras_usuario": 0}

    ctx2 = await nav.new_context(viewport={"width": 1440, "height": 900}, locale="pt-BR", service_workers="block")
    ctx2.set_default_navigation_timeout(NAV_TIMEOUT_MS)
    escutar(ctx2, "ctx2")
    tokens2: Dict[str, str] = {}
    derruba: Dict[str, str] = {}
    await ctx2.add_init_script(G.JS_SEM_WEBSOCKET)

    async def rota(route: Any, request: Any) -> None:
        m = (request.method or "").upper()
        corpo = None
        if m not in G.LEITURA:
            try:
                buf = request.post_data_buffer
                corpo = buf.decode("utf-8", "ignore") if buf is not None else ""
            except Exception:  # noqa: BLE001
                corpo = None
        cl = caminho_limpo(request.url)
        rel = None if clique["t"] is None else round(time.time() - clique["t"], 2)
        try:
            auth = request.headers.get("authorization")
            if auth and cl["host"] == b["host_api"]:
                tokens2["api"] = auth
            elif auth and cl["host"] == b["host_pdocs"]:
                tokens2["pdocs"] = auth
            if corpo and "derruba" in corpo.lower():
                jj = json.loads(corpo)
                derruba.update({k: h(v) for k, v in jj.items() if re.search("derrub", k, re.I)})
        except Exception:  # noqa: BLE001
            pass
        if m in G.LEITURA:
            ok, motivo = G.decidir(m, request.url, "", estado2, tipo_de_recurso=getattr(request, "resource_type", None))
        elif cl["host"] != b["host_api"]:
            ok, motivo = False, "escrita_fora_da_api"
        elif cl["caminho"].endswith("/usuario/login"):
            contadores["login"] += 1
            ok, motivo = contadores["login"] <= 2, "login"
        elif cl["caminho"].endswith("/usuario/login/pdocs"):
            ok, motivo = True, "pdocs"
        elif cl["caminho"].endswith("/usuario/deslogaSessao"):
            ok, motivo = True, "logout"
        elif "/usuario/" in cl["caminho"] and clique["t"] is not None and not re.search(r"tod[oa]s|all|usuarios", cl["caminho"], re.I):
            contadores["outras_usuario"] += 1
            ok, motivo = contadores["outras_usuario"] <= 2, "usuario_pos_prosseguir"
        else:
            ok, motivo = False, "escrita_barrada"
        if m not in G.LEITURA or (clique["t"] is not None and cl["host"] == b["host_api"]):
            reqs.append({"t_pos_clique": rel, "metodo": m, **cl, "corpo": forma_do_corpo(corpo),
                         "passou": ok, "motivo": motivo, "tipo": getattr(request, "resource_type", None)})
        if ok:
            await route.continue_()
        else:
            await route.abort("blockedbyclient")

    await ctx2.route("**/*", rota)

    async def ao_responder(resp: Any) -> None:
        try:
            req = resp.request
            cl = caminho_limpo(resp.url)
            if req.resource_type == "script" and cl["host"].endswith("aggilizador.com.br"):
                try:
                    scripts_txt.append(await resp.text())
                except Exception:  # noqa: BLE001
                    pass
                return
            if req.method.upper() not in G.LEITURA or "/usuario/" in cl["caminho"]:
                corpo = None
                try:
                    corpo = forma(await resp.json())
                except Exception:  # noqa: BLE001
                    pass
                resps.append({"t_pos_clique": None if clique["t"] is None else round(time.time() - clique["t"], 2),
                              "metodo": req.method, **cl, "status": resp.status, "corpo": corpo})
        except Exception:  # noqa: BLE001
            pass

    ctx2.on("response", lambda r: asyncio.ensure_future(ao_responder(r)))
    pag2 = await ctx2.new_page()
    t2 = time.time()
    await pag2.goto(b["app"] + "/login", wait_until="domcontentloaded")
    await pag2.wait_for_selector('input[type="email"]', timeout=NAV_TIMEOUT_MS)
    await pag2.fill('input[type="email"]', usuario)
    await pag2.fill('input[type="password"]', senha)
    await pag2.locator("button", has_text=re.compile(r"^\s*Entrar\s*$", re.I)).first.click()
    aviso = None
    while time.time() - t2 < 90:
        await asyncio.sleep(0.5)
        aviso = await visivel(pag2.locator(SELETOR_DIALOGO).filter(has_text=RE_AVISO))
        if aviso is None and await visivel(pag2.get_by_text(RE_AVISO)) is not None:
            aviso = pag2.locator("body")
        if aviso is not None or "/cotacoes" in pag2.url:
            break
    a1: Dict[str, Any] = {"aviso_apareceu": aviso is not None, "ate_aviso_s": round(time.time() - t2, 1),
                          "url_ctx2": caminho_limpo(pag2.url)}
    saida["a1"] = a1
    if aviso is None:
        a1["nota"] = "o aviso NÃO apareceu (o 2º login entrou direto?)"
    else:
        try:
            a1["texto_do_aviso"] = limpo(await aviso.inner_text(), 400)
        except Exception:  # noqa: BLE001
            pass
        botoes = aviso.locator("button")
        a1["botoes"] = [limpo(await botoes.nth(i).inner_text(), 40) for i in range(await botoes.count())]
        prosseguir = await visivel(aviso.locator("button", has_text=RE_PROSSEGUIR))
        if prosseguir is None:
            a1["nota"] = "sem botão Prosseguir visível — cancelando"
            cancelar = await visivel(aviso.locator("button", has_text=re.compile(r"^\s*Cancelar\s*$", re.I)))
            if cancelar is not None:
                await cancelar.click()
        else:
            memoria("ctx1_logado+ctx2_no_aviso", saida)
            clique["t"] = time.time()
            await prosseguir.click()
            while time.time() - clique["t"] < 90:
                await asyncio.sleep(0.5)
                if "/cotacoes" in pag2.url:
                    break
            a1["ctx2_chegou_em_cotacoes_s"] = round(time.time() - clique["t"], 1) if "/cotacoes" in pag2.url else None
            await asyncio.sleep(3)
            memoria("ctx1+ctx2_logados", saida)
            # ---- o ctx1 caiu? sondagem pela API (o token dele) e pela TELA, a cada 5 s, até 150 s
            sond: List[Dict[str, Any]] = []
            caiu_api = caiu_ui = None
            while time.time() - clique["t"] < 150:
                tt = round(time.time() - clique["t"], 1)
                r1 = await sondar(ctx1.pagina, ctx1.token("api"), ctx1.token("pdocs"))
                r2 = await sondar(pag2, tokens2.get("api", ""), tokens2.get("pdocs", "")) if len(sond) % 4 == 0 else None
                ra = {"s": r1["api_current"] if r1["api_current"] in (401, 403) else r1["api_seguradoras"]}
                rp = {"s": r1["pdocs_busca"]}
                try:
                    corpo_ui = await ctx1.pagina.inner_text("body")
                except Exception:  # noqa: BLE001
                    corpo_ui = ""
                ui = RE_UI_CAIU.search(corpo_ui or "")
                sond.append({"t": tt, "ctx1": r1, "ctx2_controle": r2, "url": caminho_limpo(ctx1.pagina.url)["caminho"],
                             "ui_aviso": limpo(ui.group(0), 60) if ui else None})
                if caiu_api is None and (ra.get("s") in (401, 403) or rp.get("s") in (401, 403)):
                    caiu_api = tt
                dlg1 = await visivel(ctx1.pagina.locator(SELETOR_DIALOGO))
                if dlg1 is not None and not sond[-1].get("dialogo"):
                    sond[-1]["dialogo"] = limpo(await dlg1.inner_text(), 200)
                if caiu_ui is None and (ui or "/login" in ctx1.pagina.url or "/cotacoes" not in ctx1.pagina.url or dlg1 is not None):
                    caiu_ui = tt
                if caiu_api is not None and caiu_ui is not None:
                    break
                if caiu_api is not None and time.time() - clique["t"] > caiu_api + 60:
                    break
                await asyncio.sleep(5)
            a1["sondagem_ctx1"] = sond
            a1["ctx1_caiu_api_s"] = caiu_api
            a1["ctx1_caiu_tela_s"] = caiu_ui
            try:
                a1["ctx1_texto_tela_fim"] = limpo(RE_UI_CAIU.search(await ctx1.pagina.inner_text("body")).group(0), 80)
            except Exception:  # noqa: BLE001
                a1["ctx1_texto_tela_fim"] = None
            a1["ctx2_em_cotacoes_no_fim"] = "/cotacoes" in pag2.url
            a1["ctx1_url_fim"] = caminho_limpo(ctx1.pagina.url)
            try:
                dlg = await visivel(ctx1.pagina.locator(SELETOR_DIALOGO))
                a1["ctx1_dialogo_fim"] = limpo(await dlg.inner_text(), 300) if dlg is not None else None
            except Exception:  # noqa: BLE001
                a1["ctx1_dialogo_fim"] = None
            a1["websockets_ctx1"] = [dict(w, abriu_rel=round(w["abriu_t"] - clique["t"], 1),
                                          fechou_rel=(round(w["fechou_t"] - clique["t"], 1) if w["fechou_t"] else None))
                                     for w in websockets]
            a1["hash_derrubaSessao"] = derruba
            a1["hash_tokens_ctx2"] = {"api": h(tokens2.get("api")), "pdocs": h(tokens2.get("pdocs"))}
    a1["requisicoes_ctx2"] = reqs
    a1["respostas_ctx2"] = resps
    # o bundle do app: rotas de usuário/sessão que existem (só nomes de rota)
    rotas = set()
    for txt in scripts_txt:
        for mm in re.finditer(r"usuario/[A-Za-z][A-Za-z0-9/_-]{2,60}", txt):
            rotas.add(mm.group(0))
        for mm in re.finditer(r"[\"'`]([^\"'`]{0,40}(derrub|prosseg|forcar|forçar|encerrar|deslog|kick|todasSess)[^\"'`]{0,40})[\"'`]", txt, re.I):
            rotas.add("str:" + limpo(mm.group(1), 90))
    a1["bundle_rotas_usuario_sessao"] = sorted(rotas)[:120]

    # ---- logout: o ctx2 (o vivo) primeiro, depois a tentativa no ctx1, depois um 3º login de CONFERÊNCIA
    s2 = nova_sessoes(nav, "ctx2-logout")
    sessao2 = Sessao({"id": "a1-ctx2"}, ctx2, pag2, estado2, b)
    if "/cotacoes" in pag2.url:
        await logout_por_clique(s2, sessao2, a1, "logout_ctx2")
    await logout_por_clique(s1, ctx1, a1, "logout_ctx1")
    for c in (ctx1.contexto, ctx2):
        try:
            await c.close()
        except Exception:  # noqa: BLE001
            pass
    memoria("contextos_fechados", saida)
    s3 = nova_sessoes(nav, "ctx3")
    t3 = time.time()
    try:
        c3 = await s3.obter({"id": "a1-ctx3", "username": usuario, "robo_estado": "ativo"}, senha=senha, negocios_do_robo=set())
        a1["conferencia_3o_login"] = {"aviso": False, "login_s": round(time.time() - t3, 1)}
        await logout_por_clique(s3, c3, a1, "logout_ctx3")
        await c3.contexto.close()
    except SessaoOcupada:
        a1["conferencia_3o_login"] = {"aviso": True, "nota": "sessão ativa no 3º login → Cancelar (sobrou sessão)"}
    except Exception as e:  # noqa: BLE001
        a1["conferencia_3o_login"] = {"erro": type(e).__name__}


# ------------------------------------------------------------------ B4 + licença (uma conta de robô, só leitura)
async def medir_leitura(nav: Any, saida: Dict[str, Any]) -> None:
    from portal_worker.multicalculo.agger_sessao import SessaoOcupada  # noqa: PLC0415

    s = nova_sessoes(nav, "leitura")
    usuario, senha = credencial()
    conta = {"id": "b4-leitura", "username": usuario, "robo_estado": "ativo"}
    t = time.time()
    try:
        sess = await s.obter(conta, senha=senha, negocios_do_robo=set())
    except SessaoOcupada:
        saida["leitura"] = {"entrou": False, "motivo": "aviso de sessão ativa → Cancelar"}
        return
    out: Dict[str, Any] = {"entrou": True, "login_s": round(time.time() - t, 1)}
    saida["leitura"] = out
    memoria("leitura_logado", saida)
    p = sess.pagina
    await asyncio.sleep(4)
    corpo = await p.inner_text("body")
    out["licenca_na_tela"] = sorted({limpo(corpo[max(0, m.start() - 50): m.end() + 60], 140) for m in RE_LICENCA.finditer(corpo)})[:10]
    for base, tok in ((sess.bases["api"], "api"), (sess.bases["pdocs"], "pdocs")):
        r = await fetch_json(p, base + "/cfg/assinatura-aggilizador", sess.token(tok))
        if r.get("s") == 200:
            j = r.get("j") or {}
            j = j[0] if isinstance(j, list) and j else j
            out["assinatura"] = {"host": tok, "chaves": sorted(j.keys()) if isinstance(j, dict) else None,
                                 "licenca": (j.get("licenca") if isinstance(j, dict) else None),
                                 "qtdeLicenca": (j.get("qtdeLicenca") if isinstance(j, dict) else None)}
            out["assinatura"]["campos_de_data_ou_status"] = {
                k: v for k, v in (j.items() if isinstance(j, dict) else [])
                if re.search(r"licen|venc|valid|expir|status|ativo|bloq|data|fim|inicio", k, re.I)
                and (isinstance(v, (bool, int)) or (isinstance(v, str) and re.fullmatch(r"[\d\-/:T. +Z]{6,30}|[A-Za-z_]{1,20}", v)))}
            break
        out.setdefault("assinatura_status", {})[tok] = r.get("s")
    out["negocios_730d"] = await contar_negocios(p, sess.bases, sess.token("pdocs"))
    # B4: clicar o 1º negócio da lista, como gente, e ver a URL
    antes = p.url
    alvos = ["table tbody tr", "mat-row", "[role=row]", ".card", "a[href*='/cotacao/']"]
    clicado = None
    for sel in alvos:
        el = await visivel(p.locator(sel))
        if el is not None:
            try:
                await el.click()
                clicado = sel
                break
            except Exception:  # noqa: BLE001
                continue
    await asyncio.sleep(5)
    out["b4"] = {"clicou_em": clicado, "url_antes": caminho_limpo(antes), "url_depois": caminho_limpo(p.url),
                 "mudou": p.url != antes}
    hrefs = await p.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href')).filter(h => /cotac|negoc|calcul/i.test(h)).slice(0, 30)")
    out["b4"]["hrefs_de_negocio"] = sorted({RE_ID.sub("<id>", h.split("?")[0]) for h in hrefs})
    link = p.url if p.url != antes else None
    memoria("leitura_negocio_aberto", saida)
    await logout_por_clique(s, sess, out, "logout")
    await sess.contexto.close()
    # o mesmo link num contexto SEM login (nenhuma sessão é criada: não há POST de login)
    if link:
        ctx = await nav.new_context(viewport={"width": 1440, "height": 900}, locale="pt-BR", service_workers="block")
        ctx.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        posts: List[str] = []

        async def so_leitura(route: Any, request: Any) -> None:
            if request.method.upper() not in ("GET", "HEAD", "OPTIONS"):
                posts.append(caminho_limpo(request.url)["caminho"])
                await route.abort("blockedbyclient")
            else:
                await route.continue_()
        await ctx.route("**/*", so_leitura)
        pg = await ctx.new_page()
        await pg.goto(link, wait_until="domcontentloaded")
        await asyncio.sleep(6)
        q = parse_qs(urlsplit(pg.url).query)
        out["b4"]["sem_login"] = {"url_final": caminho_limpo(pg.url),
                                  "guarda_o_destino": any(RE_ID.sub("<id>", urlsplit(link).path) in RE_ID.sub("<id>", v[0])
                                                          for v in q.values() if v),
                                  "escritas_barradas": posts}
        await ctx.close()


# ------------------------------------------------------------------ A7 (pessoa, SÓ LEITURA)
async def medir_pessoa(nav: Any, saida: Dict[str, Any]) -> None:
    from portal_worker.multicalculo.agger_sessao import SessaoOcupada  # noqa: PLC0415

    s = nova_sessoes(nav, "pessoa")
    usuario, senha = credencial()
    conta = {"id": "a7-pessoa", "username": usuario, "robo_estado": "teste"}
    try:
        sess = await s.obter(conta, senha=senha, negocios_do_robo=set())
    except SessaoOcupada:
        saida["a7"] = {"medido": False, "motivo": "NÃO MEDIDO — pessoa logada (Cancelar clicado)"}
        return
    out: Dict[str, Any] = {"entrou": True}
    saida["a7"] = out
    out["negocios_730d"] = await contar_negocios(sess.pagina, sess.bases, sess.token("pdocs"))
    out["escritas"] = sess.contagem_de_escritas()
    await logout_por_clique(s, sess, out, "logout")
    await sess.contexto.close()


# ------------------------------------------------------------------ B4 sem login: as ROTAS do app no bundle
async def medir_rotas(nav: Any, saida: Dict[str, Any]) -> None:
    """Carrega SÓ a tela de /login (nenhum POST sai: todo método que não é leitura é abortado) e lê, nos scripts do app,
    as rotas declaradas do roteador (`path:"..."`) — a pergunta B4 é se existe rota com o id de um negócio/cálculo."""
    ctx = await nav.new_context(viewport={"width": 1440, "height": 900}, locale="pt-BR", service_workers="block")
    ctx.set_default_navigation_timeout(NAV_TIMEOUT_MS)
    textos: List[str] = []
    posts: List[str] = []

    async def so_leitura(route: Any, request: Any) -> None:
        if request.method.upper() not in ("GET", "HEAD", "OPTIONS"):
            posts.append(caminho_limpo(request.url)["caminho"])
            await route.abort("blockedbyclient")
        else:
            await route.continue_()

    async def guardar(r: Any) -> None:
        try:
            if r.request.resource_type == "script" and caminho_limpo(r.url)["host"] == "aggilizador.com.br":
                textos.append(await r.text())
        except Exception:  # noqa: BLE001
            pass

    await ctx.route("**/*", so_leitura)
    ctx.on("response", lambda r: asyncio.ensure_future(guardar(r)))
    pg = await ctx.new_page()
    await pg.goto("https://aggilizador.com.br/login", wait_until="domcontentloaded")
    await asyncio.sleep(8)
    # os chunks preguiçosos: o app só baixa a rota quando navega; os nomes vêm do chunk principal (loadChildren/path)
    rotas, com_param = set(), set()
    for t in textos:
        for m in re.finditer(r"path\s*:\s*[\"'`]([^\"'`]{0,80})[\"'`]", t):
            rotas.add(m.group(1))
            if ":" in m.group(1):
                com_param.add(m.group(1))
        for m in re.finditer(r"[\"'`](/?(?:cotacao|cotacoes|negocio|negocios|calculo|resultado)[A-Za-z0-9_/:-]{0,60})[\"'`]", t):
            rotas.add("str:" + m.group(1))
    saida["rotas"] = {"scripts_lidos": len(textos), "bytes": sum(len(t) for t in textos), "escritas_barradas": posts,
                      "rotas": sorted(rotas)[:150], "rotas_com_parametro": sorted(com_param)}
    await ctx.close()


async def main_async(args: argparse.Namespace) -> Dict[str, Any]:
    from playwright.async_api import async_playwright  # noqa: PLC0415

    from portal_worker.worker import _launch_kwargs  # noqa: PLC0415

    saida: Dict[str, Any] = {"medicao": args.medicao, "inicio_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    async with async_playwright() as pw:
        nav = await pw.chromium.launch(**_launch_kwargs())
        try:
            fn = {"prosseguir": medir_prosseguir, "leitura": medir_leitura, "pessoa": medir_pessoa,
                  "rotas": medir_rotas}[args.medicao]
            await fn(nav, saida)
        except Exception as e:  # noqa: BLE001
            saida["erro"] = f"{type(e).__name__}: {limpo(e, 200)}"
        finally:
            await nav.close()
    saida["fim_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    saida["escuta"] = ESCUTA
    return saida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--conta", default=None, help="PREFIXO das variáveis <PREFIXO>_LOGIN / <PREFIXO>_PASSWORD")
    ap.add_argument("medicao", choices=("prosseguir", "leitura", "pessoa", "rotas"))
    args = ap.parse_args()
    carregar_env(args.env)
    CONTA["prefixo"] = args.conta
    saida = asyncio.run(main_async(args))
    texto = json.dumps(saida, ensure_ascii=False, indent=1, default=str)
    texto = RE_EMAIL.sub("<email>", texto)
    Path(args.saida).write_text(texto, encoding="utf-8")
    print(texto[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
