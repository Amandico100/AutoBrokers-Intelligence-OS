# -*- coding: utf-8 -*-
"""A GUARDA de escrita do robô do Agger — SPEC-129-B U3 (G3).

LISTA BRANCA, nunca lista negra (📊 o captador v1 da 128, lista negra, levou 52 do revisor; o v2, lista
branca, passou 14 cálculos ao vivo e barrou 51 escritas de telemetria em 05/10 — LAUDO-M0-M3 §G7).
Instalada no BrowserContext ANTES da 1ª aba (`instalar` recusa contexto com aba), por `context.route`
(https://playwright.dev/python/docs/network#modify-requests): cada requisição passa por `decidir`.

    LEITURA (GET · HEAD · OPTIONS) .... passa SÓ no domínio do Agger e nos subdomínios dele (`*.aggilizador.com.br`,
                                       SPEC U3; conserto 129-B) e nunca com "excluir/delet/remov/apagar" no caminho.
                                       ⚠️ fonte/script/telemetria de terceiro (Google, Clarity, Refiner) é barrado
                                       também por GET — 📊 o captador v2 já barrava os POST deles ao vivo; o GET deles
                                       só se mede no canário (se a tela não montar, é aqui)
    ESCRITA, só no host da API (api-prod.<host do Agger>):
      POST usuario/login ............. 1 por CONTEXTO; corpo sem "derrubar/forçar/prosseguir/encerrar/nova sessão"
                                       (o aviso de sessão ativa: o robô CANCELA; nunca derruba a pessoa)
      POST usuario/login/pdocs ....... ≤ 6 por HORA (📊 o app chama 2× por login; 6/h = 3 logins/h, já anômalo)
      POST usuario/deslogaSessao ..... o logout do PRÓPRIO robô (o token no header é o dele)
      POST calculo/calcularV2 ........ ids de negócio NULOS = negócio NOVO; ids preenchidos SÓ com os QUATRO
                                       presentes: `cotacao.idIntegracao` em `negocios_do_robo`, `negocio.id` ==
                                       `cotacao.negocioId`, e os dois + `cotacao.id` iguais aos que o Agger deu
                                       para ESSE negócio (`registrar_ids`) — nunca o negócio de uma pessoa
    TUDO O MAIS ..................... abortado e CONTADO. URL com "derrub" é abortada até em leitura.
    WebSocket ....................... fechado (route_web_socket quando a versão do Playwright tem; e um
                                       stub de `window.WebSocket` por init script SEMPRE — a imagem do worker
                                       fixa o Playwright 1.47, que não tem route_web_socket)
    Service Worker .................. o contexto nasce com service_workers="block" (agger_sessao)

`decidir` é PURA: (método, url, corpo, estado, agora) → (permitir, motivo). Quem conta é `instalar`.
⛔ O motivo e a URL registrados nunca carregam corpo, query ou id: só método, caminho com ids trocados e motivo.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional, Set, Tuple
from collections import deque
from urllib.parse import urlsplit

logger = logging.getLogger("portal_worker.multicalculo")

LEITURA = ("GET", "HEAD", "OPTIONS")
DERRUBA = re.compile(r"derrub|for[cç]|prosseg|sobrescr|encerr|kill|nova\W*sess", re.I)
# GET com cara de ação (📊 red team 05/10: `GET .../negocio/excluir/123` passava como leitura).
LEITURA_DESTRUTIVA = re.compile(r"excluir|delet|remov|apagar", re.I)
_UUID = re.compile(r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}", re.I)
PDOCS_POR_HORA = 6
LOGINS_POR_CONTEXTO = 1

# Os 4 lugares do corpo do calcularV2 que dizem QUAL negócio (📊 128: negocio.id = versão.negocioId,
# cotacao.id = versão.id, cotacao.negocioId, cotacao.idIntegracao — 14/14 recálculos da 128 + 1 de 05/10).
CAMPOS_DE_ID = ("negocio.id", "cotacao.id", "cotacao.negocioId", "cotacao.idIntegracao")

# Stub do WebSocket por init script: qualquer `new WebSocket(...)` falha antes de abrir conexão.
JS_SEM_WEBSOCKET = """(() => {
  const Bloqueado = function () { throw new Error('websocket bloqueado pelo robo'); };
  try { Object.defineProperty(window, 'WebSocket', {value: Bloqueado, configurable: false, writable: false}); }
  catch (e) { window.WebSocket = Bloqueado; }
})();"""


def norm_id(valor: Any) -> str:
    return re.sub(r"-", "", str(valor or "").strip().lower())


def dominio_de(host_api: str) -> str:
    """`api-prod.aggilizador.com.br` → `aggilizador.com.br` (o dublê: `api-prod.agg.localhost` → `agg.localhost`)."""
    h = str(host_api or "").strip().lower()
    return h[len("api-prod."):] if h.startswith("api-prod.") else h


@dataclass
class EstadoDaGuarda:
    """O que a guarda sabe de UM contexto (uma sessão de robô)."""
    host_api: str                                   # ex.: api-prod.aggilizador.com.br
    negocios_do_robo: Set[str] = field(default_factory=set)   # idIntegracao normalizados
    logins: int = 0
    pdocs: Deque[float] = field(default_factory=deque)        # instantes dos POST login/pdocs
    calcular: int = 0
    logout: int = 0
    barradas: int = 0
    motivos_barrados: Dict[str, int] = field(default_factory=dict)
    # 🔴 conserto 129-B (red P1/juiz P1): os ids que o Agger deu para cada negócio do robô (lidos de
    # `versoes/{ref}` DENTRO da página, antes do POST). idIntegracao → {"negocio": {...}, "versao": {...}}
    ids_do_negocio: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)
    dominio: str = ""                               # leitura só neste domínio e nos subdomínios dele

    def __post_init__(self) -> None:
        if not self.dominio:
            self.dominio = dominio_de(self.host_api)

    def registrar_negocio(self, negocio_ref: str) -> None:
        n = norm_id(negocio_ref)
        if n:
            self.negocios_do_robo.add(n)

    def registrar_ids(self, negocio_ref: str, *, negocio_id: Any = None, versao_id: Any = None) -> None:
        n = norm_id(negocio_ref)
        if not n:
            return
        d = self.ids_do_negocio.setdefault(n, {"negocio": set(), "versao": set()})
        if norm_id(negocio_id):
            d["negocio"].add(norm_id(negocio_id))
        if norm_id(versao_id):
            d["versao"].add(norm_id(versao_id))

    def host_de_leitura(self, host: str) -> bool:
        h = (host or "").lower()
        return bool(self.dominio) and (h == self.dominio or h.endswith("." + self.dominio))

    def pdocs_na_ultima_hora(self, agora: float) -> int:
        return sum(1 for t in self.pdocs if agora - t < 3600)

    def contagem(self) -> Dict[str, int]:
        return {"calcularV2": self.calcular, "barradas": self.barradas, "login": self.logins,
                "pdocs": len(self.pdocs), "logout": self.logout}


def _caminho(url: str) -> Tuple[str, str]:
    p = urlsplit(url or "")
    return (p.hostname or "").lower(), p.path or ""


def ids_de_negocio(corpo: Optional[str]) -> Optional[Dict[str, str]]:
    """{campo: id normalizado} dos 4 lugares preenchidos; None = corpo ilegível."""
    try:
        b = json.loads(corpo or "")
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(b, dict):
        return None
    cot = b.get("cotacao")
    neg = b.get("negocio")
    if not isinstance(cot, dict) or not (neg is None or isinstance(neg, dict)):
        return None
    neg = neg or {}
    valores = {"negocio.id": neg.get("id"), "cotacao.id": cot.get("id"),
               "cotacao.negocioId": cot.get("negocioId"), "cotacao.idIntegracao": cot.get("idIntegracao")}
    saida = {}
    for k, v in valores.items():
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if not isinstance(v, (str, int)) or isinstance(v, bool):
            return None
        saida[k] = norm_id(v)
    return saida


def decidir(metodo: str, url: str, corpo: Optional[str], estado: EstadoDaGuarda,
            agora: Optional[float] = None) -> Tuple[bool, str]:
    """PURA. (permitir, motivo). Toda escrita fora da lista branca é barrada."""
    agora = time.time() if agora is None else agora
    m = (metodo or "").upper()
    if re.search(r"derrub", url or "", re.I):
        return False, "derruba_sessao"
    host, caminho = _caminho(url)
    if m in LEITURA:
        # 🔴 conserto 129-B (red P1/juiz P1): leitura SÓ no domínio do Agger (a SPEC U3: `*.aggilizador.com.br`) —
        # telemetria/coletor de terceiro por GET é barrado — e nunca um GET com cara de ação destrutiva
        if not estado.host_de_leitura(host):
            return False, "leitura_fora_do_agger"
        if LEITURA_DESTRUTIVA.search(caminho):
            return False, "leitura_destrutiva"
        return True, "leitura"
    if host != estado.host_api:
        return False, "escrita_fora_da_api"
    if corpo is None:
        return False, "corpo_ilegivel"
    if m != "POST":
        return False, "escrita_fora_da_lista_branca"
    if caminho.endswith("/usuario/login"):
        if DERRUBA.search(corpo):
            return False, "derruba_sessao"
        if estado.logins >= LOGINS_POR_CONTEXTO:
            return False, "segundo_login"
        return True, "login"
    if caminho.endswith("/usuario/login/pdocs"):
        if DERRUBA.search(corpo):
            return False, "derruba_sessao"
        if estado.pdocs_na_ultima_hora(agora) >= PDOCS_POR_HORA:
            return False, "pdocs_demais"
        return True, "pdocs"
    if caminho.endswith("/usuario/deslogaSessao"):
        return True, "logout"
    if caminho.endswith("/calculo/calcularV2"):
        ids = ids_de_negocio(corpo)
        if ids is None:
            return False, "corpo_ilegivel"
        if not ids:
            return True, "calculo_novo"
        ref = ids.get("cotacao.idIntegracao")
        if not ref or ref not in estado.negocios_do_robo:
            return False, "negocio_que_nao_e_do_robo"
        # 🔴 conserto 129-B: qualquer id preenchido exige os QUATRO, coerentes entre si e com o que o Agger deu
        # para ESTE negócio (registrado antes do POST) — nunca o negócio de uma pessoa num id e o do robô noutro
        if any(c not in ids for c in CAMPOS_DE_ID):
            return False, "ids_de_negocio_incompletos"
        if ids["negocio.id"] != ids["cotacao.negocioId"]:
            return False, "ids_de_negocio_incoerentes"
        conhecidos = estado.ids_do_negocio.get(ref)
        if not conhecidos:
            return False, "ids_de_negocio_nao_conferidos"
        if ids["negocio.id"] not in conhecidos["negocio"] or ids["cotacao.id"] not in conhecidos["versao"]:
            return False, "ids_de_negocio_incoerentes"
        return True, "calculo_do_robo"
    return False, "escrita_fora_da_lista_branca"


def _url_para_registro(url: str) -> str:
    host, caminho = _caminho(url)
    return f"{host}{_UUID.sub('<id>', caminho)}"


async def instalar(contexto: Any, estado: EstadoDaGuarda) -> None:
    """Liga a guarda no contexto. 🔴 ANTES da 1ª aba: requisição de aba aberta antes passaria sem guarda."""
    if getattr(contexto, "pages", None):
        raise RuntimeError("a guarda tem de subir ANTES da 1ª aba do contexto")

    async def rota(route: Any, request: Any) -> None:
        metodo = (request.method or "").upper()
        corpo: Optional[str] = ""
        if metodo not in LEITURA:
            try:
                buf = request.post_data_buffer
                corpo = buf.decode("utf-8", "ignore") if buf is not None else ""
            except Exception:  # noqa: BLE001
                corpo = None
        try:
            ok, motivo = decidir(metodo, request.url, corpo, estado)
        except Exception as e:  # noqa: BLE001 — surpresa: barra (falha FECHADO)
            ok, motivo = False, "erro_na_guarda:" + type(e).__name__
        if not ok:
            estado.barradas += 1
            estado.motivos_barrados[motivo] = estado.motivos_barrados.get(motivo, 0) + 1
            logger.info("multicalculo.guarda barrou %s %s (%s)", metodo, _url_para_registro(request.url), motivo)
            await route.abort("blockedbyclient")
            return
        if motivo == "login":
            estado.logins += 1
        elif motivo == "pdocs":
            estado.pdocs.append(time.time())
        elif motivo in ("calculo_novo", "calculo_do_robo"):
            estado.calcular += 1
        elif motivo == "logout":
            estado.logout += 1
        await route.continue_()

    await contexto.route("**/*", rota)
    await contexto.add_init_script(JS_SEM_WEBSOCKET)
    if hasattr(contexto, "route_web_socket"):
        async def ws(rota_ws: Any) -> None:
            estado.barradas += 1
            estado.motivos_barrados["websocket"] = estado.motivos_barrados.get("websocket", 0) + 1
            await rota_ws.close()
        await contexto.route_web_socket("**/*", ws)
