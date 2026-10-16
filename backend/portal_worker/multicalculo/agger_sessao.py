# -*- coding: utf-8 -*-
"""A SESSÃO do robô no Agger — SPEC-129-B U3 (interface §6.4).

    Sessoes(navegador, url_base=...)            um contexto por CONTA, reaproveitado (📊 login leva 5–52 s, E1)
      .obter(conta, senha=..., negocios_do_robo=...) → Sessao
      .fechar(conta_id) · .fechar_todas()      logout (POST usuario/deslogaSessao) + fecha o contexto
    Sessao
      .registrar_negocio(ref)                  a guarda passa a aceitar recálculo deste negócio
      .contagem_de_escritas()                  {"calcularV2": n, "barradas": m, ...}

O login é pela TELA (📊 05/10: 2 logins ao vivo, 37 s e 55 s, sessao.py do laboratório), com a GUARDA instalada
antes da 1ª aba (agger_guarda). O aviso de "sessão ativa" (outra pessoa logada com o MESMO login) → o robô
clica SÓ "Cancelar" e levanta `SessaoOcupada` — nunca derruba a pessoa (PASSAGEM §8). 🔴 SPEC-131-A: a única
exceção é a política da madrugada (`obter(prosseguir=True)`, decidida pelo motor, só no Agger de uma PESSOA): clica
"Prosseguir" e a guarda deixa passar SÓ o POST que derruba a sessão do aviso, por id (📊 BLOCO 0 A1). Senha recusada →
`CredencialRecusada` (1 tentativa: a guarda barra o 2º login do contexto).

O token: o app do Agger manda `Authorization` nas chamadas a `pdocs.` e `api-prod.`; a sessão o captura do
header (📊 sessao.py: o de `pdocs` e o de `api-prod` são distintos). Vencimento 💭 3 h (E18; NÃO MEDIDO, P-128-01):
faltando < 20 min, a sessão recarrega a tela para o app renovar.
⛔ A senha decifrada só existe dentro de `obter()` (vai para o campo da tela e morre). O token mora só em
atributo privado; `repr` não mostra nada disso; nada aqui loga corpo, header, senha ou e-mail.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Set
from urllib.parse import urlsplit

from .agger_guarda import EstadoDaGuarda, instalar

logger = logging.getLogger("portal_worker.multicalculo")

URL_BASE_AGGER = "https://aggilizador.com.br"
TOKEN_VALE_S = 3 * 3600          # 💭 E18 (não medido): o token do Agger dura 3 h
RENOVAR_FALTANDO_S = 20 * 60     # renova quando faltar < 20 min
LOGIN_TIMEOUT_S = 90             # 📊 login 5–52 s (E1); 90 s de folga
LOGOUT_INDEFINIDO_S = 25         # o logout de um login sem desfecho: a tela + 15 s da resposta, e desiste
MONTADOR_JS = (Path(__file__).with_name("montador.js")).read_text(encoding="utf-8")

# O aviso de sessão ativa: o texto (como o laboratório, 📊 "text=sessão ativa") E o diálogo que o contém.
# 🔴 O botão é procurado DENTRO do diálogo e pelo texto EXATO "Cancelar". O "Prosseguir" (RE_PROSSEGUIR, abaixo) só é
# procurado quando a política da madrugada pediu (`obter(prosseguir=True)`) — fora dela, nenhum caminho o clica.
RE_AVISO = re.compile(r"sess[aã]o\s+ativa", re.I)
SELETOR_DIALOGO = "[role=dialog], [role=alertdialog], mat-dialog-container, .cdk-overlay-pane, .modal"
RE_CANCELAR = re.compile(r"^\s*Cancelar\s*$", re.I)
# 🔴 SPEC-131-A (D-131-03 revista): o "Prosseguir" EXISTE só para a política da madrugada (`obter(prosseguir=True)`, que
# só o motor decide, só em conta `uso='membro'`). Sem ela, o seletor acima continua o único que se clica.
RE_PROSSEGUIR = re.compile(r"^\s*Prosseguir\s*$", re.I)
# 📊 BLOCO 0 A1: a 1ª resposta do login com sessão aberta é 201 `{message: "Já existe uma sessão ativa…", data: {id,
# token, …}}` — o `data.id` é o alvo do Prosseguir; ⛔ o `data.token` é o da OUTRA sessão e NUNCA é lido para fora daqui
RE_JA_EXISTE = re.compile(r"j[aá]\s+existe\s+uma\s+sess[aã]o\s+ativa", re.I)
ESPERA_DO_ID_S = 10              # o Prosseguir espera o `data.id` da resposta; sem ele, Cancelar (fail-closed)
# O que o login devolve da LICENÇA (📊 BLOCO 0: `licenca`, `dataLimiteCalculo`, `diasParaExpirarSenha`; `expirationDate`
# no `/usuario/current`) — SÓ estas chaves saem da resposta, e só datas ou números
CHAVES_DA_LICENCA = ("licenca", "dataLimiteCalculo", "diasParaExpirarSenha", "expirationDate")
# 🔴 conserto C2 (juiz B3: 📊 0 eventos `licenca_agger` ao vivo com logins reais). ONDE a licença mora, medido na escuta
# do BLOCO 0 (12/10, 3 rodadas, fora do git): o corpo do `POST /usuario/login` de um login NORMAL não foi lido em 0 de 4
# contextos (só o do Prosseguir, 2/2); o `GET /usuario/current` que o PRÓPRIO app faz trouxe licenca/expirationDate/
# diasParaExpirarSenha em 4 de 4 (📊 21× em 147 s num contexto); o `POST /usuario/login/pdocs` trouxe `dataLimiteCalculo`
# em 6 de 6. A sessão lê as TRÊS respostas interceptadas (nenhuma chamada nova); se o `current` do app ainda não veio
# quando o login fecha, espera `ESPERA_DO_CURRENT_S` e, sem ele, faz UM `GET /usuario/current` na sessão já aberta
# (nunca `goto`). A licença é AVISO: nada aqui derruba o login.
ROTA_DO_CURRENT = "/usuario/current"
ESPERA_DO_CURRENT_S = 2.0
# 🔴 SPEC-129-D (achado do produto, 📊 BLOCO 0 M6 ao vivo 16/10): a leitura do CORPO de `/usuario/current`
# (`Response.json` → `Response.body`) NÃO voltou em 2 de 2 logins nesta máquina (Windows, Chromium headless) — o
# `gather` sem prazo prendeu o `obter` 16–20 min, a sessão nunca foi entregue e o robô ficou logado, parado, sem logout.
# A licença é AVISO: espera no máximo isto pelas leituras; estourou, segue SEM ela e registra. 💭 5 s: o `current` do app
# respondeu 21× em 147 s num contexto (BLOCO 0 da 131-A) — uma leitura sã de um corpo pequeno cabe com folga.
PRAZO_DA_LICENCA_S = 5.0
_RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}")


def extrair_licenca(corpo: Any, _prof: int = 0) -> Dict[str, Any]:
    """Só as datas/números da licença de uma resposta de login (busca rasa no objeto). Data → `AAAA-MM-DD`; número →
    int. Todo o resto — token, e-mail, ids — é IGNORADO e nunca sai daqui."""
    saida: Dict[str, Any] = {}
    if _prof > 3:
        return saida
    if isinstance(corpo, dict):
        for k, v in corpo.items():
            if k in CHAVES_DA_LICENCA and k not in saida:
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    saida[k] = int(v)
                elif isinstance(v, str) and _RE_DATA.match(v.strip()):
                    saida[k] = v.strip()[:10]
            elif isinstance(v, (dict, list)):
                for k2, v2 in extrair_licenca(v, _prof + 1).items():
                    saida.setdefault(k2, v2)
    elif isinstance(corpo, list):
        for item in corpo[:5]:
            for k2, v2 in extrair_licenca(item, _prof + 1).items():
                saida.setdefault(k2, v2)
    return saida


def id_da_sessao_ativa(corpo: Any) -> Optional[str]:
    """O `data.id` da resposta "Já existe uma sessão ativa" — ou None. Nada mais é lido dela."""
    if not isinstance(corpo, dict) or not RE_JA_EXISTE.search(str(corpo.get("message") or "")):
        return None
    dados = corpo.get("data")
    alvo = dados.get("id") if isinstance(dados, dict) else None
    return str(alvo) if isinstance(alvo, (str, int)) and not isinstance(alvo, bool) and str(alvo).strip() else None
RE_SENHA_RECUSADA = re.compile(r"(senha|credenciais?|login)[^.]{0,40}(inv[aá]lid|incorret)|usu[aá]rio n[aã]o encontrado", re.I)
RE_SAIR = re.compile(r"^\s*(Sair|Logout|Desconectar)\s*$", re.I)


class SessaoOcupada(Exception):
    """O aviso de sessão ativa apareceu e foi CANCELADO."""


class CredencialRecusada(Exception):
    """Login/senha recusados (1 tentativa)."""


class SessaoIndefinida(Exception):
    """O login não chegou ao fim nem a um dos dois avisos no prazo (nada foi derrubado)."""


def bases_de(url_base: str) -> Dict[str, str]:
    """app · api · pdocs · pdf a partir da URL do app. 📊 O Agger usa subdomínios do MESMO host:
    `api-prod.`, `pdocs.` e `quotation-files.` (o PDF). O dublê dos testes usa `agg.localhost`."""
    p = urlsplit(url_base.rstrip("/"))
    host = p.hostname or ""
    porta = f":{p.port}" if p.port else ""
    esq = p.scheme or "https"
    return {"app": f"{esq}://{host}{porta}", "api": f"{esq}://api-prod.{host}{porta}",
            "pdocs": f"{esq}://pdocs.{host}{porta}", "host_api": f"api-prod.{host}".lower(),
            "host_pdocs": f"pdocs.{host}".lower()}


class Sessao:
    """Uma sessão viva de um robô (um contexto, uma aba)."""

    def __init__(self, conta: Dict[str, Any], contexto: Any, pagina: Any, estado: EstadoDaGuarda,
                 bases: Dict[str, str]) -> None:
        self.conta_id: str = str(conta.get("id"))
        self.robo_estado: Optional[str] = conta.get("robo_estado")
        self.contexto = contexto
        self.pagina = pagina
        self.bases = bases
        self._estado = estado
        self._tokens: Dict[str, str] = {}
        self._token_em: float = 0.0
        self._renovacao_tentada_em: float = 0.0
        # SPEC-131-A: o login desta sessão PROSSEGUIU sobre uma sessão aberta (o motor grava o evento e zera) · as
        # datas/números da licença que o login devolveu (`extrair_licenca`: nada além delas)
        self.prosseguiu: bool = False
        self.licenca: Dict[str, Any] = {}

    def __repr__(self) -> str:  # ⛔ nunca token, e-mail ou senha
        return f"Sessao(conta_id={self.conta_id!r}, estado={self.robo_estado!r})"

    __str__ = __repr__

    # ---------------------------------------------------------------- interface §6.4
    def registrar_negocio(self, negocio_ref: str) -> None:
        self._estado.registrar_negocio(negocio_ref)

    def registrar_ids_do_negocio(self, negocio_ref: str, *, negocio_id: Any = None, versao_id: Any = None) -> None:
        """Os ids que o Agger deu para o negócio (lidos de `versoes/{ref}` na página): a guarda só deixa um POST
        com ids preenchidos passar se eles forem ESTES (conserto 129-B)."""
        self._estado.registrar_ids(negocio_ref, negocio_id=negocio_id, versao_id=versao_id)

    def contagem_de_escritas(self) -> Dict[str, int]:
        return self._estado.contagem()

    # ---------------------------------------------------------------- uso interno do robô
    @property
    def estado_da_guarda(self) -> EstadoDaGuarda:
        return self._estado

    def _capturar(self, request: Any) -> None:
        try:
            host = (urlsplit(request.url).hostname or "").lower()
            auth = request.headers.get("authorization")
        except Exception:  # noqa: BLE001
            return
        if not auth:
            return
        if host == self.bases["host_pdocs"]:
            if self._tokens.get("pdocs") != auth:
                self._token_em = time.time()
            self._tokens["pdocs"] = auth
        elif host == self.bases["host_api"]:
            self._tokens["api"] = auth

    def token(self, qual: str) -> str:
        t = self._tokens.get(qual)
        if not t:
            raise SessaoIndefinida(f"sem token de {qual} na sessão")
        return t

    def tem_tokens(self) -> bool:
        return bool(self._tokens.get("pdocs") and self._tokens.get("api"))

    async def garantir_token(self) -> None:
        """Faltando < 20 min das 3 h (💭 E18), recarrega a tela para o app renovar. No máximo 1 tentativa a cada
        10 min (o token pode simplesmente durar mais: P-128-01 segue não medido)."""
        agora = time.time()
        if agora - self._token_em < TOKEN_VALE_S - RENOVAR_FALTANDO_S:
            return
        if agora - self._renovacao_tentada_em < 600:
            return
        self._renovacao_tentada_em = agora
        antes = self._tokens.get("pdocs")
        try:
            await self.pagina.goto(self.bases["app"] + "/cotacoes", wait_until="domcontentloaded")
            for _ in range(30):
                if self._tokens.get("pdocs") and self._tokens.get("pdocs") != antes:
                    break
                await asyncio.sleep(1)
        except Exception as e:  # noqa: BLE001
            logger.warning("multicalculo.sessao renovação de token falhou (%s)", type(e).__name__)

    async def avaliar(self, js: str, arg: Any = None) -> Any:
        """O ÚNICO caminho do robô para dentro da página. Carrega o montador (window.__abM) se faltar."""
        return await self.pagina.evaluate(
            "async ([src, js, arg]) => { if (!window.__abM) (0, eval)(src);"
            " const f = (0, eval)('(' + js + ')'); return await f(arg); }",
            [MONTADOR_JS, js, arg])


class Sessoes:
    """As sessões vivas do processo, uma por conta de robô."""

    def __init__(self, navegador: Any, *, url_base: str = URL_BASE_AGGER) -> None:
        self.navegador = navegador
        self.url_base = url_base.rstrip("/")
        self.bases = bases_de(self.url_base)
        self._sessoes: Dict[str, Sessao] = {}
        self._travas: Dict[str, asyncio.Lock] = {}

    async def obter(self, conta: Dict[str, Any], *, senha: str, negocios_do_robo: Set[str],
                    prosseguir: bool = False,
                    antes_de_prosseguir: Optional[Callable[[], Awaitable[bool]]] = None) -> Sessao:
        """`prosseguir` (SPEC-131-A, a política da madrugada — só o motor decide): se o aviso de sessão ativa aparecer,
        clica "Prosseguir" em vez de "Cancelar", e a guarda deixa passar SÓ o POST que derruba a sessão do aviso. Vale
        apenas para o Agger de uma PESSOA (`uso='membro'`): conta da corretora ou de teste NUNCA prossegue.
        🔴 conserto C2 (red P5): `antes_de_prosseguir` é a RESERVA do "1× por noite" (o motor grava a marca), chamada
        DEPOIS de o aviso aparecer e ANTES do clique; sem ela, ou se ela não devolver True, o robô CANCELA (fail-closed)."""
        conta_id = str(conta.get("id"))
        prosseguir = bool(prosseguir) and conta.get("uso") == "membro" and conta.get("robo_estado") != "teste"
        trava = self._travas.setdefault(conta_id, asyncio.Lock())
        async with trava:
            viva = self._sessoes.get(conta_id)
            if viva is not None and not viva.pagina.is_closed():
                for n in negocios_do_robo or ():
                    viva.registrar_negocio(n)
                viva.robo_estado = conta.get("robo_estado", viva.robo_estado)
                await viva.garantir_token()
                return viva
            self._sessoes.pop(conta_id, None)
            sessao = await self._entrar(conta, senha, negocios_do_robo, prosseguir=prosseguir,
                                        antes_de_prosseguir=antes_de_prosseguir)
            self._sessoes[conta_id] = sessao
            return sessao

    @staticmethod
    async def _reservou(antes_de_prosseguir: Optional[Callable[[], Awaitable[bool]]]) -> bool:
        """A reserva do motor (a marca do "1× por noite") — qualquer falha, ou a falta dela, é NÃO."""
        if antes_de_prosseguir is None:
            return False
        try:
            return (await antes_de_prosseguir()) is True
        except Exception as e:  # noqa: BLE001
            logger.warning("multicalculo.sessao a reserva do Prosseguir falhou (%s) — Cancelar", type(e).__name__)
            return False

    async def _completar_licenca(self, sessao: "Sessao", lidas: Dict[str, bool], leituras: list) -> None:
        """J-B3: a licença vem do `GET /usuario/current` que o app já faz (interceptado). Se ele ainda não veio, espera
        `ESPERA_DO_CURRENT_S`; sem ele, UM `GET /usuario/current` na sessão aberta (o corpo é lido SÓ pelo interceptador:
        à página volta só o status). Nunca `goto`. Nada aqui derruba o login."""
        try:
            limite = time.time() + ESPERA_DO_CURRENT_S
            while not lidas.get("respondeu") and time.time() < limite:
                await asyncio.sleep(0.2)
            if not lidas.get("respondeu") and sessao._tokens.get("api"):
                await sessao.pagina.evaluate(
                    "async ([u, t]) => { try { const r = await fetch(u, {headers: {Authorization: t}});"
                    " return r.status; } catch (e) { return 0; } }",
                    [sessao.bases["api"] + ROTA_DO_CURRENT, sessao._tokens["api"]])
                limite = time.time() + ESPERA_DO_CURRENT_S      # o evento da resposta chega pelo interceptador
                while not lidas.get("respondeu") and time.time() < limite:
                    await asyncio.sleep(0.1)
            if leituras:
                # 🔴 `wait` com PRAZO (nunca `gather` sem prazo): devolve no prazo mesmo que uma leitura nunca acorde, e
                # não espera o cancelamento dela terminar (o `wait_for` esperaria)
                _feitas, presas = await asyncio.wait(set(leituras), timeout=PRAZO_DA_LICENCA_S)
                for t in presas:
                    t.cancel()
                if presas:
                    logger.info("multicalculo.sessao conta=%s licença: %s leitura(s) sem resposta em %.0fs — segue sem "
                                "ela", getattr(sessao, "conta_id", "?"), len(presas), PRAZO_DA_LICENCA_S)
        except Exception as e:  # noqa: BLE001
            logger.info("multicalculo.sessao licença não lida (%s)", type(e).__name__)

    async def _entrar(self, conta: Dict[str, Any], senha: str, negocios_do_robo: Set[str], *,
                      prosseguir: bool = False,
                      antes_de_prosseguir: Optional[Callable[[], Awaitable[bool]]] = None) -> Sessao:
        usuario = str(conta.get("username") or "")
        if not usuario or not senha:
            raise CredencialRecusada("conta sem usuário ou senha")
        estado = EstadoDaGuarda(host_api=self.bases["host_api"], prosseguir_permitido=bool(prosseguir))
        for n in negocios_do_robo or ():
            estado.registrar_negocio(n)
        ctx = await self.navegador.new_context(viewport={"width": 1440, "height": 900}, locale="pt-BR",
                                               service_workers="block")
        try:
            await instalar(ctx, estado)                       # 🔴 ANTES da 1ª aba
            status_login: Dict[str, int] = {}
            licenca: Dict[str, Any] = {}
            leituras: list = []

            async def _ler_login(resp: Any) -> None:
                """O corpo da resposta do login é lido AQUI e morre aqui: sai só o `data.id` do aviso (para a guarda,
                e só com a política ligada) e as datas/números da licença. ⛔ Nenhum log, nenhuma exceção com ele."""
                try:
                    corpo = await resp.json()
                except Exception:  # noqa: BLE001 — sem o tipo nem a mensagem: o corpo não sai daqui
                    return
                try:
                    alvo = id_da_sessao_ativa(corpo)
                    if alvo is not None:
                        estado.registrar_sessao_ativa(alvo)
                    elif resp.status < 300:
                        licenca.update(extrair_licenca(corpo))
                except Exception:  # noqa: BLE001
                    pass
                finally:
                    corpo = None  # noqa: F841

            lidas: Dict[str, bool] = {}

            async def _ler_licenca(resp: Any) -> None:
                """J-B3: `GET /usuario/current` e `POST /usuario/login/pdocs` — SÓ as datas/números da licença saem."""
                try:
                    corpo = await resp.json()
                    licenca.update(extrair_licenca(corpo))
                except Exception:  # noqa: BLE001 — o corpo não sai daqui, nem no tipo do erro
                    return
                finally:
                    corpo = None  # noqa: F841

            def _resp(resp: Any) -> None:
                try:
                    req = resp.request
                    partes = urlsplit(resp.url)
                    caminho = partes.path
                    if req.method == "GET" and caminho.endswith(ROTA_DO_CURRENT) and                             (partes.hostname or "").lower() == self.bases["host_api"]:
                        lidas["respondeu"] = True       # qualquer status: a espera acaba (o corpo só se lê se < 300)
                    if req.method == "POST" and caminho.endswith("/usuario/login"):
                        status_login["s"] = resp.status
                        if resp.status < 300:
                            leituras.append(asyncio.ensure_future(_ler_login(resp)))
                    elif resp.status < 300 and (partes.hostname or "").lower() == self.bases["host_api"] and (
                            (req.method == "POST" and caminho.endswith("/usuario/login/pdocs"))
                            or (req.method == "GET" and caminho.endswith(ROTA_DO_CURRENT))):
                        leituras.append(asyncio.ensure_future(_ler_licenca(resp)))
                except Exception:  # noqa: BLE001
                    pass

            ctx.on("response", _resp)
            pagina = await ctx.new_page()
            sessao = Sessao(conta, ctx, pagina, estado, self.bases)
            ctx.on("request", sessao._capturar)
            t0 = time.time()
            await pagina.goto(self.bases["app"] + "/login", wait_until="domcontentloaded")
            await pagina.wait_for_selector('input[type="email"]', timeout=LOGIN_TIMEOUT_S * 1000)
            await pagina.fill('input[type="email"]', usuario)
            await pagina.fill('input[type="password"]', senha)
            await pagina.locator("button", has_text=re.compile(r"^\s*Entrar\s*$", re.I)).first.click()
            prosseguiu_clicado, prosseguiu_em = False, 0.0
            while time.time() - t0 < LOGIN_TIMEOUT_S:
                await asyncio.sleep(0.5)
                if "/cotacoes" in pagina.url and sessao.tem_tokens():
                    await self._completar_licenca(sessao, lidas, leituras)
                    sessao.licenca = dict(licenca)
                    sessao.prosseguiu = estado.prosseguiu > 0
                    logger.info("multicalculo.sessao conta=%s entrou em %.1fs%s", sessao.conta_id, time.time() - t0,
                                " (prosseguiu sobre uma sessão aberta)" if sessao.prosseguiu else "")
                    return sessao
                if prosseguir and not prosseguiu_clicado and await self._aviso_visivel(pagina):
                    # 🔴 a política da madrugada: o Prosseguir só com o `data.id` do aviso NESTE contexto (a guarda só
                    # deixa passar o POST que derruba ESSA sessão). Sem o id no prazo → Cancelar, como sempre
                    limite = time.time() + ESPERA_DO_ID_S
                    while not estado.sessao_ativa_id and time.time() < limite:
                        await asyncio.sleep(0.2)
                    # 🔴 conserto C2 (red P5): a marca do "1× por noite" é RESERVADA antes do clique; sem ela → Cancelar
                    if (estado.sessao_ativa_id and await self._reservou(antes_de_prosseguir)
                            and await self._prosseguir_aviso(pagina)):
                        prosseguiu_clicado, prosseguiu_em = True, time.time()
                        logger.info("multicalculo.sessao conta=%s: Prosseguir da madrugada sobre uma sessão aberta",
                                    sessao.conta_id)
                        continue
                if prosseguiu_clicado and time.time() - prosseguiu_em < 5:
                    continue      # o diálogo fecha depois do clique: não confundir o fechamento com um aviso novo
                if await self._cancelar_aviso_se_houver(pagina):
                    raise SessaoOcupada("aviso de sessão ativa: cancelado")
                if status_login.get("s", 0) >= 400 or await self._senha_recusada(pagina):
                    raise CredencialRecusada("login recusado pelo Agger")
            # 🔴 conserto 129-B (red P7): o login pode ter sido ACEITO sem a tela chegar ao fim — sem logout, sobra
            # uma sessão fantasma e o próximo login vê o aviso de "sessão ativa". Se o POST de login SAIU, tenta o
            # logout (curto, a guarda só deixa o do próprio robô) antes de fechar o contexto.
            if estado.logins >= 1:
                try:
                    await asyncio.wait_for(self._sair(sessao), timeout=LOGOUT_INDEFINIDO_S)
                except BaseException as e:  # noqa: BLE001
                    if isinstance(e, asyncio.CancelledError):
                        raise
                    logger.warning("multicalculo.sessao logout do login sem desfecho falhou (%s)", type(e).__name__)
            raise SessaoIndefinida("login sem desfecho no prazo")
        except BaseException:
            try:
                await ctx.close()
            except Exception:  # noqa: BLE001
                pass
            raise

    @staticmethod
    async def _primeiro_visivel(locator: Any) -> Any:
        """O 1º elemento VISÍVEL do locator, ou None. 🔴 `count()` conta elemento ESCONDIDO (📊 o dublê: o modal
        do aviso mora no DOM com display:none desde o carregamento) — por isso nunca se decide por contagem.
        Sem `filter(visible=)` de propósito: a imagem do worker fixa o Playwright 1.47, que não o tem."""
        for i in range(await locator.count()):
            el = locator.nth(i)
            try:
                if await el.is_visible():
                    return el
            except Exception:  # noqa: BLE001
                continue
        return None

    @classmethod
    async def _cancelar_aviso_se_houver(cls, pagina: Any) -> bool:
        dialogo = await cls._primeiro_visivel(pagina.locator(SELETOR_DIALOGO).filter(has_text=RE_AVISO))
        if dialogo is not None:
            botao = await cls._primeiro_visivel(dialogo.locator("button", has_text=RE_CANCELAR))
            if botao is not None:
                await botao.click()
            return True
        if await cls._primeiro_visivel(pagina.get_by_text(RE_AVISO)) is not None:
            # sem contêiner de diálogo reconhecível: o botão VISÍVEL de texto EXATO "Cancelar", e só ele
            botao = await cls._primeiro_visivel(pagina.locator("button", has_text=RE_CANCELAR))
            if botao is not None:
                await botao.click()
            return True
        return False

    @classmethod
    async def _aviso_visivel(cls, pagina: Any) -> bool:
        try:
            return await cls._primeiro_visivel(pagina.get_by_text(RE_AVISO)) is not None
        except Exception:  # noqa: BLE001
            return False

    @classmethod
    async def _prosseguir_aviso(cls, pagina: Any) -> bool:
        """🔴 SPEC-131-A: o botão VISÍVEL de texto EXATO "Prosseguir", DENTRO do diálogo do aviso de sessão ativa — e só
        ele. Sem diálogo reconhecível, não clica (o Cancelar do laço segue valendo)."""
        dialogo = await cls._primeiro_visivel(pagina.locator(SELETOR_DIALOGO).filter(has_text=RE_AVISO))
        if dialogo is None:
            return False
        botao = await cls._primeiro_visivel(dialogo.locator("button", has_text=RE_PROSSEGUIR))
        if botao is None:
            return False
        await botao.click()
        return True

    @classmethod
    async def _senha_recusada(cls, pagina: Any) -> bool:
        try:
            return await cls._primeiro_visivel(pagina.get_by_text(RE_SENHA_RECUSADA)) is not None
        except Exception:  # noqa: BLE001
            return False

    async def fechar(self, conta_id: str) -> None:
        sessao = self._sessoes.pop(str(conta_id), None)
        if sessao is None:
            return
        try:
            await self._sair(sessao)
        except Exception as e:  # noqa: BLE001
            logger.warning("multicalculo.sessao logout conta=%s falhou (%s)", sessao.conta_id, type(e).__name__)
        finally:
            try:
                await sessao.contexto.close()
            except Exception:  # noqa: BLE001
                pass

    async def descartar(self, conta_id: str) -> None:
        """A sessão MORREU (401/403, página fechada): fecha o contexto SEM logout — o token não vale mais, e o
        logout pela tela só gastaria 15 s esperando uma resposta que não vem. Nunca é reaproveitada (conserto 129-B)."""
        sessao = self._sessoes.pop(str(conta_id), None)
        if sessao is None:
            return
        try:
            await sessao.contexto.close()
        except Exception:  # noqa: BLE001
            pass

    async def fechar_todas(self) -> None:
        """Logout de TODAS, em paralelo (F4, junta 8): no desligar do serviço o `docker stop` dá 📊 10 s de graça;
        em série, N logouts pela tela (≈1–3 s cada) não cabem e o robô seguinte veria o aviso de sessão ativa."""
        await asyncio.gather(*(self.fechar(c) for c in list(self._sessoes)), return_exceptions=True)

    async def _sair(self, sessao: Sessao) -> bool:
        """Logout pela TELA (o app monta `{idSessao, token}` — 📊 6 logouts 201 na 128/05/10). O menu do usuário:
        pelo rótulo acessível; senão o canto superior direito que o laboratório provou (1390, 58 em 1440×900)."""
        p = sessao.pagina
        if p.is_closed():
            return False
        if "/cotacoes" not in p.url:
            await p.goto(self.bases["app"] + "/cotacoes", wait_until="domcontentloaded")
        sair = p.get_by_text(RE_SAIR)
        if not await sair.count() or not await sair.first.is_visible():
            menu = p.locator('[aria-label*="usuário" i], [aria-label*="usuario" i], [aria-label*="perfil" i]')
            if await menu.count():
                await menu.first.click()
            else:
                await p.mouse.click(1390, 58)
            await asyncio.sleep(0.8)
        async with p.expect_response(lambda r: urlsplit(r.url).path.endswith("/usuario/deslogaSessao"),
                                     timeout=15000) as info:
            await p.get_by_text(RE_SAIR).first.click()
        resp = await info.value
        logger.info("multicalculo.sessao conta=%s logout %s", sessao.conta_id, resp.status)
        return resp.status < 300
