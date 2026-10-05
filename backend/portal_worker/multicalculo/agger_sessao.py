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
clica SÓ "Cancelar" e levanta `SessaoOcupada` — nunca derruba a pessoa (PASSAGEM §8). Senha recusada →
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
from typing import Any, Dict, Optional, Set
from urllib.parse import urlsplit

from .agger_guarda import EstadoDaGuarda, instalar

logger = logging.getLogger("portal_worker.multicalculo")

URL_BASE_AGGER = "https://aggilizador.com.br"
TOKEN_VALE_S = 3 * 3600          # 💭 E18 (não medido): o token do Agger dura 3 h
RENOVAR_FALTANDO_S = 20 * 60     # renova quando faltar < 20 min
LOGIN_TIMEOUT_S = 90             # 📊 login 5–52 s (E1); 90 s de folga
MONTADOR_JS = (Path(__file__).with_name("montador.js")).read_text(encoding="utf-8")

# O aviso de sessão ativa: o texto (como o laboratório, 📊 "text=sessão ativa") E o diálogo que o contém.
# 🔴 O botão é procurado DENTRO do diálogo e pelo texto EXATO "Cancelar" — nenhum seletor aqui casa "Prosseguir".
RE_AVISO = re.compile(r"sess[aã]o\s+ativa", re.I)
SELETOR_DIALOGO = "[role=dialog], [role=alertdialog], mat-dialog-container, .cdk-overlay-pane, .modal"
RE_CANCELAR = re.compile(r"^\s*Cancelar\s*$", re.I)
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

    def __repr__(self) -> str:  # ⛔ nunca token, e-mail ou senha
        return f"Sessao(conta_id={self.conta_id!r}, estado={self.robo_estado!r})"

    __str__ = __repr__

    # ---------------------------------------------------------------- interface §6.4
    def registrar_negocio(self, negocio_ref: str) -> None:
        self._estado.registrar_negocio(negocio_ref)

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

    async def obter(self, conta: Dict[str, Any], *, senha: str, negocios_do_robo: Set[str]) -> Sessao:
        conta_id = str(conta.get("id"))
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
            sessao = await self._entrar(conta, senha, negocios_do_robo)
            self._sessoes[conta_id] = sessao
            return sessao

    async def _entrar(self, conta: Dict[str, Any], senha: str, negocios_do_robo: Set[str]) -> Sessao:
        usuario = str(conta.get("username") or "")
        if not usuario or not senha:
            raise CredencialRecusada("conta sem usuário ou senha")
        estado = EstadoDaGuarda(host_api=self.bases["host_api"])
        for n in negocios_do_robo or ():
            estado.registrar_negocio(n)
        ctx = await self.navegador.new_context(viewport={"width": 1440, "height": 900}, locale="pt-BR",
                                               service_workers="block")
        try:
            await instalar(ctx, estado)                       # 🔴 ANTES da 1ª aba
            status_login: Dict[str, int] = {}

            def _resp(resp: Any) -> None:
                try:
                    req = resp.request
                    if req.method == "POST" and urlsplit(resp.url).path.endswith("/usuario/login"):
                        status_login["s"] = resp.status
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
            while time.time() - t0 < LOGIN_TIMEOUT_S:
                await asyncio.sleep(0.5)
                if "/cotacoes" in pagina.url and sessao.tem_tokens():
                    logger.info("multicalculo.sessao conta=%s entrou em %.1fs", sessao.conta_id, time.time() - t0)
                    return sessao
                if await self._cancelar_aviso_se_houver(pagina):
                    raise SessaoOcupada("aviso de sessão ativa: cancelado")
                if status_login.get("s", 0) >= 400 or await self._senha_recusada(pagina):
                    raise CredencialRecusada("login recusado pelo Agger")
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

    async def fechar_todas(self) -> None:
        for conta_id in list(self._sessoes):
            await self.fechar(conta_id)

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
