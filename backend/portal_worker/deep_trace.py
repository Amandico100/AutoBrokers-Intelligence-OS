# -*- coding: utf-8 -*-
"""DeepTrace — a SEGUNDA modalidade de observação do portal. SPEC-077 Blocos C e D.

O que ele é, e o que ele **não** substitui
==========================================
O `PortalProfiler` da SPEC-073 (`profiler.py`) é leve, always-on e barato:
📊 três ouvintes (`response`, `requestfailed`, `framenavigated`), sem corpo, sem
console, um dicionário achatado no fim. Ele fica **exatamente como está** — é o
que roda em produção normal, e mexer nele para "aproveitar o código" trocaria um
observador de custo conhecido por um de custo desconhecido no caminho da
cobrança.

O DeepTrace é o outro extremo: **on-demand**, para laboratório, discovery e
depuração de journey que quebrou. Ele liga um segundo cliente CDP sobre a MESMA
página que a journey está dirigindo, escuta Network/Log/Page/Runtime + console,
fatia a corrida por navegação e produz uma linha do tempo onde as ações do
agente e os eventos do navegador aparecem intercaladas.

🔴 A invariante absoluta: ELE NUNCA AGE
=======================================
O DeepTrace **jamais** envia comando de ação por CDP. Nada de `Input.*`, nada de
`Runtime.evaluate`, nada de `Page.navigate`, nada de cookie, nada de
`Fetch.*`/`Network.setRequestInterception`. Ele só habilita domínios de leitura
e escuta. **A journey continua sendo o único motorista.**

Isso não é uma promessa de docstring: é uma lista fechada
(`METODOS_CDP_PERMITIDOS`) e uma função (`validar_metodo_cdp`) por onde todo
`send` passa. Qualquer método fora da lista levanta `MetodoCdpProibido` antes de
tocar o socket. Um método novo só entra na lista por decisão de quem lê este
arquivo — não por descuido de quem está depurando às duas da manhã.

📊 Por que CDP nativo, e não o `browse` CLI (SPEC-077-AUDIT §1.3 e §3.1)
=======================================================================
O CLI do upstream tem fonte não auditável (o `repository` do pacote aponta para
dois repositórios que devolvem 404) e justamente as duas capacidades que nos
interessam — abrir CDP e capturar corpos — moram no que não dá para ler. Não
precisamos dele: confirmado nesta instalação que
`BrowserContext.new_cdp_session`, `CDPSession.send/.on/.detach`,
`context.route` e `page.route` existem todos. Zero Node, zero Browserbase, zero
dependência nova.

📊 O firehose CDP não traz corpo (SPEC-077-AUDIT §1.4)
=====================================================
`Network.responseReceived` descreve a resposta; **não** carrega o corpo dela.
Cada corpo custa uma ida e volta `Network.getResponseBody` com o `requestId`.
Duas consequências que decidem o desenho:

1. captura de corpo é **cara e seletiva** — não é "ligue e veja";
2. o join evento↔corpo é **por `requestId`**, nunca por URL nem por timestamp.
   URLs se repetem (a mesma tela chama o mesmo endpoint várias vezes) e o
   timestamp do CDP é de um relógio monotônico do navegador, não epoch.

🔴 Corpo bruto NUNCA é persistido "para redigir depois"
=======================================================
O pipeline é obrigatório e está escrito em `_processar_corpo`:

    Network.getResponseBody → memória temporária (variável local)
    → redator / extrator de forma
    → o que sai é forma ou amostra sanitizada
    → só ISSO é guardado

"Salvo agora, redijo na hora de exportar" é como PII de segurado vira arquivo
esquecido em disco de laboratório. O bruto morre no escopo da função — o `del`
explícito existe para que quem editar o código veja a intenção.

🔴 Falha do trace nunca derruba a journey
=========================================
Todo caminho tem `try/except` que degrada para "sem trace" e registra o motivo
em `self.erros`. Uma cobrança que quebra porque o **observador** quebrou é o
pior resultado possível deste módulo — pior que não ter trace nenhum.

Flag
====
`PORTAL_DEEP_TRACE_ENABLED` nasce **desligada**. Com ela off a classe existe,
`attach()` não abre CDP, nenhum ouvinte é registrado e `resumo()` devolve
`{"enabled": False}`: custo zero no caminho de produção.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from portal_worker import redaction as R
from portal_worker.profiler import normalizar_path

logger = logging.getLogger(__name__)


# ==========================================================================
# Flag — mesmo padrão de `runtime.py`
# ==========================================================================
def _flag(nome: str, padrao: str = "") -> bool:
    return str(os.getenv(nome, padrao)).strip().lower() in ("1", "true", "yes", "on")


def deep_trace_enabled() -> bool:
    """`PORTAL_DEEP_TRACE_ENABLED` — nasce `false` (SPEC-077 §38).

    Diferente do profiler (que nasce `true` porque é passivo e barato), o
    DeepTrace custa: um segundo cliente CDP, eventos de rede em volume,
    screenshots e, quando pedido, uma ida e volta por corpo. Produção normal
    roda sem ele; o laboratório liga.
    """
    return _flag("PORTAL_DEEP_TRACE_ENABLED")


# ==========================================================================
# 🔴 A lista fechada. É AQUI que mora a garantia de passividade.
# ==========================================================================
# Regra para incluir um método novo: ele precisa ser LEITURA ou habilitação de
# domínio de leitura. Se o método muda estado da página, do input, dos cookies,
# da navegação ou do tráfego, ele NÃO entra — nem "só para um teste".
METODOS_CDP_PERMITIDOS: frozenset[str] = frozenset({
    # habilitar/desabilitar domínios de OBSERVAÇÃO
    "Network.enable",
    "Network.disable",
    "Log.enable",
    "Log.disable",
    "Page.enable",
    "Page.disable",
    "Runtime.enable",
    "Runtime.disable",
    # leitura pura, sempre por requestId (nunca por URL — ver docstring do módulo)
    "Network.getResponseBody",
    "Network.getRequestPostData",
})

# Não são a garantia (a garantia é a allowlist acima); servem para que a
# mensagem de erro diga POR QUE aquilo é proibido, em vez de só "não está na
# lista". Depurar uma recusa é mais barato quando ela se explica.
_FAMILIAS_DE_ACAO: Tuple[Tuple[str, str], ...] = (
    ("Input.", "sintetiza teclado/mouse — quem clica e digita e a journey"),
    ("Fetch.", "intercepta e reescreve trafego — o DeepTrace so observa"),
    ("Storage.", "mexe em cookie/localStorage da sessao da corretora"),
    ("Emulation.", "altera o ambiente medido — mediria a si mesmo"),
    ("Browser.", "controla o navegador inteiro, nao a pagina observada"),
    ("Target.", "cria/fecha alvos — pode derrubar a sessao da journey"),
    ("Page.navigate", "navega — a journey e a unica motorista"),
    ("Page.reload", "recarrega — perde estado de formulario da journey"),
    ("Page.close", "fecha a pagina que nao e dele"),
    ("Runtime.evaluate", "executa script na pagina — isso e agir"),
    ("Runtime.callFunctionOn", "executa script na pagina — isso e agir"),
    ("Network.setCookie", "escreve cookie de sessao autenticada"),
    ("Network.clearBrowserCook", "apaga a sessao da journey"),
    ("Network.setRequestInterception", "intercepta trafego — so observamos"),
    ("DOM.setAttribute", "edita o DOM medido"),
)


class MetodoCdpProibido(RuntimeError):
    """Tentativa de enviar comando fora da allowlist de leitura.

    🔴 Nunca capture esta exceção "para seguir em frente". Ela significa que
    alguém escreveu, no observador, um comando que AGE sobre a página — e o
    conserto é remover o comando, não silenciar o guarda.
    """


def validar_metodo_cdp(metodo: Any) -> str:
    """Devolve o método se ele for de leitura; levanta `MetodoCdpProibido` senão.

    É a única porta: `DeepTrace._enviar` chama isto antes de qualquer `send`.
    Recusa por allowlist (não por blacklist) porque o protocolo CDP cresce a
    cada versão do Chromium — uma blacklist envelhece sozinha e passa a deixar
    entrar o método de ação que ainda não existia quando foi escrita.
    """
    m = str(metodo or "").strip()
    if m in METODOS_CDP_PERMITIDOS:
        return m
    for prefixo, porque in _FAMILIAS_DE_ACAO:
        if m.startswith(prefixo):
            raise MetodoCdpProibido(
                f"CDP '{m}' recusado: {porque}. O DeepTrace e observador passivo."
            )
    raise MetodoCdpProibido(
        f"CDP '{m}' recusado: fora da allowlist de leitura do DeepTrace "
        f"({len(METODOS_CDP_PERMITIDOS)} metodos). Se for mesmo leitura pura, "
        f"acrescente em METODOS_CDP_PERMITIDOS com justificativa."
    )


# ==========================================================================
# Modos de corpo — SPEC-077 §10.3
# ==========================================================================
MODO_SHAPE_ONLY = "shape_only"          # default: forma, nunca valor
MODO_SANITIZED = "sanitized_sample"     # só Lab explícito + host na allowlist
MODO_DESLIGADO = "off"

MODOS_DE_CORPO = (MODO_DESLIGADO, MODO_SHAPE_ONLY, MODO_SANITIZED)

# Só content-type de DADO. Imagem, fonte, vídeo e binário não têm forma útil
# para inferir contrato de API e só gastariam a ida e volta cara do
# `getResponseBody`.
_CT_DE_DADO: Tuple[str, ...] = (
    "application/json",
    "application/problem+json",
    "application/ld+json",
    "application/xml",
    "application/xhtml+xml",
    "application/x-www-form-urlencoded",
    "text/",
)
_CT_PROIBIDO: Tuple[str, ...] = (
    "image/", "font/", "video/", "audio/", "application/octet-stream",
    "application/pdf", "application/zip", "application/wasm",
)


def content_type_e_de_dado(content_type: Any) -> bool:
    """`application/json` e `text/*` sim; imagem, fonte, vídeo e PDF não."""
    ct = str(content_type or "").split(";")[0].strip().lower()
    if not ct:
        return False
    if any(ct.startswith(p) for p in _CT_PROIBIDO):
        return False
    return any(ct.startswith(p) for p in _CT_DE_DADO)


def _host_de(url: Any) -> str:
    try:
        return (urlsplit(str(url or "")).hostname or "").lower()
    except ValueError:
        return ""


def _path_de(url: Any) -> str:
    try:
        return urlsplit(str(url or "")).path or "/"
    except ValueError:
        return "/"


def host_permitido(host: str, allowlist: Sequence[str]) -> bool:
    """Casamento por host exato ou subdomínio. Allowlist vazia = ninguém passa.

    🔴 O default fechado é deliberado: `sanitized_sample` sem allowlist não
    deve virar "captura tudo" por omissão de quem chamou.
    """
    h = str(host or "").strip().lower()
    if not h:
        return False
    for item in allowlist or ():
        a = str(item or "").strip().lower().lstrip(".")
        if not a:
            continue
        if h == a or h.endswith("." + a):
            return True
    return False


# ==========================================================================
# Orçamento — SPEC-077 §27.2. Tudo tem teto; nada roda "até acabar".
# ==========================================================================
@dataclass
class OrcamentoTrace:
    """Os tetos. Um trace sem teto é um vazamento de disco e de tempo.

    Os valores default cobrem um fluxo de portal inteiro com folga. O que passa
    disso é laço — e laço se diagnostica pelo contador de descarte, não relendo
    quatro mil linhas de JSONL.
    """

    max_eventos: int = 4000
    max_paginas: int = 60
    max_corpos: int = 60
    max_bytes_por_corpo: int = 256 * 1024
    max_bytes_total: int = 8 * 1024 * 1024
    max_screenshots: int = 40
    intervalo_min_screenshot_s: float = 2.0
    max_duracao_s: float = 900.0
    # DOM snapshot é o item mais perigoso do conjunto: HTML de portal
    # autenticado é PII densa. Nasce desligado; quando ligado, passa por
    # `redigir_texto` e vai truncado.
    dom_snapshots: bool = False
    max_bytes_dom: int = 200 * 1024
    # A fila de corpos tem teto próprio: se o portal disparar 500 XHR em rajada,
    # o consumidor não pode acumular trabalho até estourar memória.
    max_fila_corpos: int = 200
    # Uma ida e volta CDP travada não pode segurar o `parar()`.
    timeout_corpo_s: float = 5.0
    timeout_parada_s: float = 8.0


# ==========================================================================
# Bucket de página — SPEC-077 §9.6
# ==========================================================================
@dataclass
class BucketDePagina:
    """Uma navegação = uma pasta em `pages/NNN/`.

    O `resumo()` do profiler é um dicionário achatado: bom para `evidence`,
    inútil para responder *"o que aconteceu na tela 3?"*. O bucket existe para
    reduzir o custo cognitivo de quem lê o run depois — inclusive de um modelo,
    que consegue abrir só a pasta da tela que interessa.
    """

    indice: int = 0
    url_normalizada: str = ""
    host: str = ""
    ts_inicio: float = 0.0
    ts_fim: float = 0.0
    requests: int = 0
    falhas: int = 0
    excecoes: int = 0
    acoes: List[Dict[str, Any]] = field(default_factory=list)
    screenshot: str = ""          # nome do arquivo mais próximo, ""=nenhum
    dom_snapshot: str = ""
    status_ruins: List[int] = field(default_factory=list)

    def duracao_ms(self) -> int:
        fim = self.ts_fim or time.time()
        return max(0, int((fim - self.ts_inicio) * 1000)) if self.ts_inicio else 0

    def para_dict(self) -> Dict[str, Any]:
        return {
            "indice": self.indice,
            "url_normalizada": self.url_normalizada,
            "host": self.host,
            "duracao_ms": self.duracao_ms(),
            "requests": self.requests,
            "falhas": self.falhas,
            "excecoes_console": self.excecoes,
            "status_ruins": sorted(set(self.status_ruins))[:12],
            "acoes": self.acoes[:40],
            "screenshot": self.screenshot,
            "dom_snapshot": self.dom_snapshot,
        }


# ==========================================================================
# O observador
# ==========================================================================
class DeepTrace:
    """Observador passivo sobre uma página Playwright que **outra pessoa** dirige.

    Uso pelo laboratório::

        trace = DeepTrace(portal_key="mapfre_corretor", job_id=job_id)
        await trace.attach(page)                 # nada acontece se a flag off
        ...
        trace.registrar_acao_do_agente("click", alvo="Emitir 2a via")
        ...
        await trace.parar()                      # idempotente, seguro após crash
        trace.gravar(Path("/tmp/lab/run-1"))     # opcional

    🔴 Ele **nunca** envia comando de ação (ver `METODOS_CDP_PERMITIDOS`).
    🔴 Nenhuma exceção dele sobe para a journey: tudo degrada para "sem trace".
    """

    def __init__(
        self,
        *,
        portal_key: str = "",
        job_id: str = "",
        journey: str = "",
        habilitado: Optional[bool] = None,
        modo_corpo: str = MODO_SHAPE_ONLY,
        hosts_corpo: Optional[Sequence[str]] = None,
        orcamento: Optional[OrcamentoTrace] = None,
        host_portal: str = "",
    ) -> None:
        self.portal_key = str(portal_key or "")
        self.job_id = str(job_id or "")
        self.journey = str(journey or "")
        self.host_portal = str(host_portal or "").strip().lower()
        # `habilitado=None` significa "pergunte à flag". Passar `True`
        # explicitamente é o caminho do teste e do comando de laboratório, que
        # não deveriam depender do ambiente do processo.
        self.habilitado: bool = deep_trace_enabled() if habilitado is None else bool(habilitado)

        modo = str(modo_corpo or MODO_SHAPE_ONLY).strip().lower()
        # 🔴 Modo desconhecido cai no MAIS restritivo, nunca no mais permissivo.
        # Um typo em `"sanitized_smaple"` não pode virar captura de valor.
        self.modo_corpo: str = modo if modo in MODOS_DE_CORPO else MODO_SHAPE_ONLY
        self.hosts_corpo: Tuple[str, ...] = tuple(hosts_corpo or ())
        self.orc = orcamento or OrcamentoTrace()

        self.run_id = f"{self.portal_key or 'portal'}-{int(time.time())}"
        self.ts_inicio = time.time()
        self.ts_fim: float = 0.0

        # Linha do tempo unificada — SPEC-077 §9.7
        self.eventos: List[Dict[str, Any]] = []
        self.paginas: List[BucketDePagina] = []
        self.erros: List[str] = []
        self.screenshots: List[Tuple[str, bytes]] = []
        self.doms: List[Tuple[str, str]] = []

        # contadores
        self.eventos_descartados = 0
        self.corpos_capturados = 0
        self.corpos_bytes = 0
        self.corpos_recusados: Dict[str, int] = {}
        self._ultimo_shot_ts: float = 0.0

        # join evento↔corpo é por requestId. Ver docstring do módulo.
        self._req_meta: Dict[str, Dict[str, Any]] = {}
        self.corpos: Dict[str, Dict[str, Any]] = {}

        # estado de anexação
        self._page: Any = None
        self._cdp: Any = None
        self._ligado = False
        self._parado = False
        self._parando = False
        self._fila: Optional["asyncio.Queue[Any]"] = None
        self._tarefa: Optional["asyncio.Task[None]"] = None
        # (evento, callback) para poder desinscrever sem adivinhação
        self._inscricoes_cdp: List[Tuple[str, Callable[..., None]]] = []
        self._inscricoes_page: List[Tuple[str, Callable[..., None]]] = []

    # ----------------------------------------------------------------------
    # Registro de erro do próprio tracer
    # ----------------------------------------------------------------------
    def _falhou(self, onde: str, e: BaseException) -> None:
        """Anota e segue. 🔴 O observador quebrado não pode quebrar a journey.

        Registrar o TIPO (e não a mensagem) é de propósito: mensagem de exceção
        de rede costuma carregar URL com token de sessão dentro.
        """
        marca = f"{onde}:{type(e).__name__}"
        if marca not in self.erros:
            self.erros.append(marca)
        logger.warning("[PORTAL][deep_trace] %s", marca)

    # ----------------------------------------------------------------------
    # A única porta de saída para o CDP
    # ----------------------------------------------------------------------
    async def _enviar(self, metodo: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Envia um comando CDP **de leitura**. Qualquer outro é recusado aqui.

        🔴 `MetodoCdpProibido` sobe: é defeito de programação deste módulo, não
        condição de ambiente, e tem de aparecer no teste em vez de virar um
        `erros` silencioso.
        """
        m = validar_metodo_cdp(metodo)
        if self._cdp is None:
            raise RuntimeError("CDP nao anexado")
        return await self._cdp.send(m, params or {})

    # ----------------------------------------------------------------------
    # attach — SPEC-077 §9.2
    # ----------------------------------------------------------------------
    async def attach(self, page: Any) -> bool:
        """Abre o segundo cliente CDP e liga os ouvintes. Devolve se ligou.

        📊 A permissão técnica vem do próprio protocolo: *"CDP allows multiple
        concurrent clients on the same target"*. É isso que deixa o DeepTrace
        observar sem disputar o volante com o Playwright que a journey usa.

        🔴 Toda a função é um `try` largo. Se a versão do Playwright mudar um
        nome, se o alvo já estiver fechado, se o contexto não expuser
        `new_cdp_session` — o worker precisa continuar cobrando boleto, cego
        mas de pé.
        """
        if not self.habilitado or page is None or self._ligado or self._parado:
            return False
        self._page = page
        try:
            contexto = getattr(page, "context", None)
            criar = getattr(contexto, "new_cdp_session", None)
            if criar is None:
                self._falhou("attach", RuntimeError("sem_new_cdp_session"))
                self.habilitado = False
                return False
            self._cdp = await criar(page)

            # Só domínios de LEITURA. `Runtime.enable` entra apenas por causa de
            # `Runtime.exceptionThrown` — não para avaliar nada.
            for dominio in ("Network.enable", "Page.enable", "Log.enable", "Runtime.enable"):
                try:
                    await self._enviar(dominio)
                except MetodoCdpProibido:
                    raise
                except Exception as e:  # noqa: BLE001
                    # Um domínio que não sobe não invalida os outros.
                    self._falhou(f"enable:{dominio}", e)

            self._inscrever_cdp()
            self._inscrever_page(page)

            self._fila = asyncio.Queue(maxsize=max(8, int(self.orc.max_fila_corpos)))
            self._tarefa = asyncio.create_task(self._consumir())

            self._ligado = True
            self.ts_inicio = time.time()
            self._abrir_pagina(getattr(page, "url", "") or "", motivo="attach")
            return True
        except MetodoCdpProibido:
            raise
        except Exception as e:  # noqa: BLE001
            self._falhou("attach", e)
            self.habilitado = False
            # Não deixa meio-anexado: um CDP aberto sem consumidor é lixo.
            await self.parar()
            return False

    # ----------------------------------------------------------------------
    # Ouvintes
    # ----------------------------------------------------------------------
    def _on_cdp(self, evento: str, cb: Callable[..., None]) -> None:
        try:
            self._cdp.on(evento, cb)
            self._inscricoes_cdp.append((evento, cb))
        except Exception as e:  # noqa: BLE001
            self._falhou(f"on:{evento}", e)

    def _on_page(self, evento: str, cb: Callable[..., None]) -> None:
        try:
            self._page.on(evento, cb)
            self._inscricoes_page.append((evento, cb))
        except Exception as e:  # noqa: BLE001
            self._falhou(f"page.on:{evento}", e)

    def _inscrever_cdp(self) -> None:
        """Network + Page + Log + Runtime, todos só de leitura."""
        self._on_cdp("Network.requestWillBeSent", self._cdp_request)
        self._on_cdp("Network.responseReceived", self._cdp_response)
        self._on_cdp("Network.loadingFinished", self._cdp_finalizado)
        self._on_cdp("Network.loadingFailed", self._cdp_falhou_rede)
        self._on_cdp("Page.frameNavigated", self._cdp_navegou)
        self._on_cdp("Log.entryAdded", self._cdp_log)
        self._on_cdp("Runtime.exceptionThrown", self._cdp_excecao)

    def _inscrever_page(self, page: Any) -> None:
        """Console vem por `page.on`, não por CDP.

        `Runtime.consoleAPICalled` daria o mesmo, com `RemoteObject` cru para
        desembrulhar à mão. `page.on("console")` já entrega texto pronto, é a
        API que o resto do worker usa e não acrescenta um domínio a mais.
        """
        self._on_page("console", self._page_console)
        self._on_page("pageerror", self._page_erro)

    # ----------------------------------------------------------------------
    # Linha do tempo unificada — SPEC-077 §9.7
    # ----------------------------------------------------------------------
    def _evento(self, source: str, **campos: Any) -> Optional[Dict[str, Any]]:
        """Uma linha de `unified-events.jsonl`. Redigida, com teto.

        🔴 O timestamp é carimbado **na chegada**, com `time.time()`, para as
        duas fontes. O `timestamp` que o CDP manda é de um relógio monotônico do
        navegador; intercalar aquilo com o relógio de parede do agente
        produziria uma ordem sem sentido — e a ordem é o produto inteiro desta
        estrutura ("a ação X foi seguida de HTTP 403").
        """
        if not self.habilitado or self._parado:
            return None
        if len(self.eventos) >= self.orc.max_eventos:
            self.eventos_descartados += 1
            return None
        agora = time.time()
        if self.orc.max_duracao_s and (agora - self.ts_inicio) > self.orc.max_duracao_s:
            self.eventos_descartados += 1
            return None
        linha: Dict[str, Any] = {
            "source": source,
            "ts": round(agora, 4),
            "t_ms": int((agora - self.ts_inicio) * 1000),
            "page": self.paginas[-1].indice if self.paginas else 0,
        }
        for k, v in campos.items():
            if v is None:
                continue
            if isinstance(v, str):
                linha[k] = R.redigir_texto(v)[:400]
            elif isinstance(v, (int, float, bool)):
                linha[k] = v
            elif isinstance(v, (dict, list, tuple)):
                linha[k] = R.redigir(v)
            else:
                linha[k] = R.redigir_texto(str(v))[:400]
        self.eventos.append(linha)
        return linha

    def registrar_acao_do_agente(self, acao: str, *, alvo: str = "",
                                 resultado: str = "", **detalhes: Any) -> None:
        """A journey marca o que ela ACABOU de fazer. Síncrono de propósito.

        🔴 É esta chamada que dá valor à linha do tempo. Sem ela o run diz
        *"houve um 403 às 14:22:07"*; com ela diz *"o clique em 'Emitir 2ª via'
        foi seguido de 403 em `/api/boleto`"* — a diferença entre uma hipótese e
        uma prova.

        Não é `async` porque precisa poder ser chamada de qualquer ponto de uma
        journey sem obrigar a um `await` que ninguém vai lembrar de pôr. O
        screenshot que ela dispara é enfileirado para a tarefa consumidora.
        """
        if not self.habilitado or self._parado:
            return
        try:
            linha = self._evento("agent", action=str(acao or "")[:80],
                                 alvo=alvo, resultado=resultado, **detalhes)
            if self.paginas and linha is not None:
                self.paginas[-1].acoes.append({
                    "t_ms": linha.get("t_ms"),
                    "action": linha.get("action"),
                    "alvo": linha.get("alvo", ""),
                    "resultado": linha.get("resultado", ""),
                })
            # Ação do agente é evento SEMÂNTICO: é aqui que screenshot vale a
            # pena. Nunca por evento de rede — seriam centenas.
            self._enfileirar(("shot", f"acao:{acao}"))
        except Exception as e:  # noqa: BLE001
            self._falhou("registrar_acao", e)

    # ----------------------------------------------------------------------
    # Buckets de página — SPEC-077 §9.6
    # ----------------------------------------------------------------------
    def _abrir_pagina(self, url: str, *, motivo: str = "") -> None:
        try:
            agora = time.time()
            if self.paginas:
                self.paginas[-1].ts_fim = agora
            if len(self.paginas) >= self.orc.max_paginas:
                self.eventos_descartados += 1
                return
            b = BucketDePagina(
                indice=len(self.paginas),
                url_normalizada=normalizar_path(_path_de(url)),
                host=_host_de(url),
                ts_inicio=agora,
            )
            self.paginas.append(b)
            self._evento("browser", method="Page.frameNavigated",
                         url=b.url_normalizada, host=b.host, motivo=motivo)
            # Navegação também é evento semântico.
            self._enfileirar(("shot", "navegacao"))
            if self.orc.dom_snapshots:
                self._enfileirar(("dom", b.url_normalizada))
        except Exception as e:  # noqa: BLE001
            self._falhou("abrir_pagina", e)

    def _bucket(self) -> Optional[BucketDePagina]:
        return self.paginas[-1] if self.paginas else None

    # ----------------------------------------------------------------------
    # Handlers CDP — todos síncronos, todos blindados
    # ----------------------------------------------------------------------
    def _cdp_request(self, p: Dict[str, Any]) -> None:
        try:
            rid = str(p.get("requestId") or "")
            req = p.get("request") or {}
            url = str(req.get("url") or "")
            if not rid:
                return
            if len(self._req_meta) < self.orc.max_eventos:
                self._req_meta[rid] = {
                    "method": str(req.get("method") or "")[:8],
                    "host": _host_de(url),
                    "path": normalizar_path(_path_de(url)),
                    "resource_type": str(p.get("type") or "")[:24],
                    "ts": time.time(),
                }
            b = self._bucket()
            if b is not None:
                b.requests += 1
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_request", e)

    def _cdp_response(self, p: Dict[str, Any]) -> None:
        try:
            rid = str(p.get("requestId") or "")
            resp = p.get("response") or {}
            meta = self._req_meta.get(rid) or {}
            status = int(resp.get("status") or 0)
            ct = str(resp.get("mimeType") or "")
            host = meta.get("host") or _host_de(resp.get("url"))
            path = meta.get("path") or normalizar_path(_path_de(resp.get("url")))
            meta.update({"status": status, "content_type": ct, "host": host, "path": path})
            self._req_meta[rid] = meta
            self._evento("browser", method="Network.responseReceived",
                         request_id=rid, status=status, host=host, path=path,
                         content_type=ct.split(";")[0][:64],
                         http_method=meta.get("method", ""))
            b = self._bucket()
            if b is not None and status >= 400:
                b.status_ruins.append(status)
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_response", e)

    def _cdp_finalizado(self, p: Dict[str, Any]) -> None:
        """Só depois de `loadingFinished` o corpo existe para ser buscado.

        E ele tem prazo: o navegador descarta o buffer quando a página navega.
        Por isso a fila é drenada por uma tarefa que roda já, e não no fim.
        """
        try:
            rid = str(p.get("requestId") or "")
            if not rid or self.modo_corpo == MODO_DESLIGADO:
                return
            meta = self._req_meta.get(rid)
            if not meta:
                return
            motivo = self._recusa_de_corpo(meta)
            if motivo:
                self.corpos_recusados[motivo] = self.corpos_recusados.get(motivo, 0) + 1
                return
            self._enfileirar(("corpo", rid))
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_finalizado", e)

    def _cdp_falhou_rede(self, p: Dict[str, Any]) -> None:
        try:
            rid = str(p.get("requestId") or "")
            meta = self._req_meta.get(rid) or {}
            self._evento("browser", method="Network.loadingFailed",
                         host=meta.get("host", ""), path=meta.get("path", ""),
                         erro=str(p.get("errorText") or "")[:120],
                         cancelado=bool(p.get("canceled")))
            b = self._bucket()
            if b is not None:
                b.falhas += 1
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_falhou_rede", e)

    def _cdp_navegou(self, p: Dict[str, Any]) -> None:
        try:
            frame = p.get("frame") or {}
            # Só o frame principal abre bucket. Iframe de captcha/analytics
            # navegando sozinho não é "outra tela".
            if frame.get("parentId"):
                return
            self._abrir_pagina(str(frame.get("url") or ""), motivo="frameNavigated")
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_navegou", e)

    def _cdp_log(self, p: Dict[str, Any]) -> None:
        try:
            entry = p.get("entry") or {}
            nivel = str(entry.get("level") or "")
            self._evento("browser", method="Log.entryAdded", nivel=nivel,
                         fonte=str(entry.get("source") or "")[:32],
                         texto=str(entry.get("text") or "")[:300])
            b = self._bucket()
            if b is not None and nivel == "error":
                b.excecoes += 1
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_log", e)

    def _cdp_excecao(self, p: Dict[str, Any]) -> None:
        try:
            det = p.get("exceptionDetails") or {}
            texto = str(det.get("text") or "")
            exc = det.get("exception") or {}
            desc = str(exc.get("description") or "")
            self._evento("browser", method="Runtime.exceptionThrown",
                         texto=texto[:200], descricao=desc[:300],
                         linha=det.get("lineNumber"))
            b = self._bucket()
            if b is not None:
                b.excecoes += 1
            self._enfileirar(("shot", "excecao"))
        except Exception as e:  # noqa: BLE001
            self._falhou("cdp_excecao", e)

    def _page_console(self, msg: Any) -> None:
        try:
            tipo = str(getattr(msg, "type", "") or "")
            texto = str(getattr(msg, "text", "") or "")
            self._evento("browser", method="Console", nivel=tipo, texto=texto[:300])
            b = self._bucket()
            if b is not None and tipo in ("error", "assert"):
                b.excecoes += 1
        except Exception as e:  # noqa: BLE001
            self._falhou("page_console", e)

    def _page_erro(self, err: Any) -> None:
        try:
            self._evento("browser", method="PageError", texto=str(err)[:300])
            b = self._bucket()
            if b is not None:
                b.excecoes += 1
            self._enfileirar(("shot", "pageerror"))
        except Exception as e:  # noqa: BLE001
            self._falhou("page_erro", e)

    # ----------------------------------------------------------------------
    # Fila e tarefa consumidora — UMA tarefa, rastreada, morta no `parar()`
    # ----------------------------------------------------------------------
    def _enfileirar(self, job: Tuple[Any, ...]) -> None:
        """Enfileira sem bloquear. Fila cheia = descarta e conta.

        🔴 Uma tarefa por corpo (`create_task` solto no handler) seria mais
        curta de escrever e deixaria tarefa órfã na queda — que é exatamente o
        que a SPEC-077 §9.5 proíbe. Uma fila e um consumidor dão limite de
        concorrência de graça e um único ponto para desligar.
        """
        if self._fila is None or self._parado or self._parando:
            return
        try:
            self._fila.put_nowait(job)
        except asyncio.QueueFull:
            self.corpos_recusados["fila_cheia"] = self.corpos_recusados.get("fila_cheia", 0) + 1
        except Exception as e:  # noqa: BLE001
            self._falhou("enfileirar", e)

    async def _consumir(self) -> None:
        """Drena a fila até o sentinela. Nunca deixa exceção escapar."""
        while True:
            try:
                job = await self._fila.get()  # type: ignore[union-attr]
            except asyncio.CancelledError:
                return
            except Exception as e:  # noqa: BLE001
                self._falhou("consumir", e)
                return
            try:
                if job is None:  # sentinela de parada
                    return
                tipo = job[0]
                if tipo == "corpo":
                    await self._processar_corpo(job[1])
                elif tipo == "shot":
                    await self._talvez_screenshot(str(job[1]))
                elif tipo == "dom":
                    await self._talvez_dom(str(job[1]))
            except asyncio.CancelledError:
                return
            except Exception as e:  # noqa: BLE001
                self._falhou(f"consumir:{job[0] if job else '?'}", e)

    # ----------------------------------------------------------------------
    # Corpo — SPEC-077 Bloco D. É aqui que a PII se decide.
    # ----------------------------------------------------------------------
    def _recusa_de_corpo(self, meta: Dict[str, Any]) -> str:
        """Devolve o motivo da recusa, ou `""` quando o corpo pode ser buscado.

        Recusar cedo importa por dois motivos: cada corpo custa uma ida e volta
        síncrona ao navegador, e o que não é buscado não pode vazar.
        """
        if self.corpos_capturados >= self.orc.max_corpos:
            return "teto_de_corpos"
        if self.corpos_bytes >= self.orc.max_bytes_total:
            return "teto_de_bytes"
        if not content_type_e_de_dado(meta.get("content_type")):
            return "content_type"
        status = int(meta.get("status") or 0)
        if status == 204 or status == 304:
            return "sem_corpo"
        return ""

    def _modo_para(self, meta: Dict[str, Any]) -> str:
        """Que modo de corpo vale para ESTE host.

        A allowlist de `sanitized_sample` responde *"de quais hosts podemos
        guardar VALOR?"* — e a resposta para os demais é `shape_only`, não
        "nada".

        🔴 A primeira versão recusava o corpo inteiro do host fora da lista. Isso
        troca informação por uma segurança que já existia: `shape_only` não
        guarda valor nenhum. A saída dele é `{"cpf": "<string:14>"}` — tipo e
        tamanho, nunca conteúdo. Recusar a forma não protege ninguém e cega o
        inferidor justamente nos hosts que ainda não conhecemos, que são os que
        mais precisam ser mapeados.

        A allowlist continua valendo integralmente para o que ela existe: **só
        host autorizado tem valor persistido.**
        """
        if self.modo_corpo != MODO_SANITIZED:
            return self.modo_corpo
        if host_permitido(str(meta.get("host") or ""), self.hosts_corpo):
            return MODO_SANITIZED
        return MODO_SHAPE_ONLY

    async def _processar_corpo(self, request_id: str) -> None:
        """`getResponseBody` → memória → redator/forma → guarda. Nunca bruto.

        🔴 O pipeline da SPEC-077 §10.2 está aqui inteiro, e a ordem é o
        produto. "Salvo o bruto agora e redijo na exportação" é como HTML de
        portal autenticado com CPF de segurado vira arquivo esquecido num disco
        de laboratório. A variável `bruto` morre nesta função — o `del` no fim
        não é otimização, é a intenção escrita para quem vier editar.

        📊 E o join é por `requestId` (SPEC-077-AUDIT §1.4): a mesma URL aparece
        várias vezes no mesmo fluxo, então casar por URL ou por timestamp
        misturaria o corpo de uma chamada com o metadado de outra.
        """
        meta = self._req_meta.get(request_id)
        if not meta:
            return
        motivo = self._recusa_de_corpo(meta)
        if motivo:
            self.corpos_recusados[motivo] = self.corpos_recusados.get(motivo, 0) + 1
            return

        bruto: Optional[str] = None
        try:
            resp = await asyncio.wait_for(
                self._enviar("Network.getResponseBody", {"requestId": request_id}),
                timeout=self.orc.timeout_corpo_s,
            )
        except MetodoCdpProibido:
            raise
        except Exception as e:  # noqa: BLE001
            # Corpo evictado, alvo fechado, timeout. Diagnóstico, não falha.
            self.corpos_recusados["indisponivel"] = self.corpos_recusados.get("indisponivel", 0) + 1
            self._falhou("get_body", e)
            return

        try:
            if not isinstance(resp, dict):
                return
            if resp.get("base64Encoded"):
                # Binário disfarçado de content-type de dado. Não decodificamos:
                # não há forma útil e há bytes que não queremos em memória.
                self.corpos_recusados["binario"] = self.corpos_recusados.get("binario", 0) + 1
                return
            bruto = resp.get("body")
            if not isinstance(bruto, str) or not bruto:
                return

            n_bytes = len(bruto.encode("utf-8", "ignore"))
            registro: Dict[str, Any] = {
                "request_id": request_id,
                "method": meta.get("method", ""),
                "host": meta.get("host", ""),
                "path": meta.get("path", ""),
                "status": meta.get("status", 0),
                "content_type": str(meta.get("content_type") or "").split(";")[0][:64],
                "bytes": n_bytes,
                "modo": self._modo_para(meta),
            }

            if n_bytes > self.orc.max_bytes_por_corpo:
                # Não parseamos nem truncamos JSON grande: JSON cortado não
                # parseia, e "quase parseou" produz forma errada — pior que
                # nenhuma forma, porque parece verdade.
                registro["shape"] = {"__truncado__": n_bytes}
                registro["truncado"] = True
            else:
                registro.update(self._extrair(bruto, registro["content_type"], meta))

            self.corpos[request_id] = registro
            self.corpos_capturados += 1
            self.corpos_bytes += n_bytes
            self._evento("browser", method="Network.getResponseBody",
                         request_id=request_id, host=registro["host"],
                         path=registro["path"], bytes=n_bytes, modo=self.modo_corpo)
        except Exception as e:  # noqa: BLE001
            self._falhou("processar_corpo", e)
        finally:
            # 🔴 O bruto sai de escopo aqui, sempre. Nada em `self` o referencia.
            bruto = None
            del bruto

    def _extrair(self, bruto: str, content_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Do texto cru para o que É PERMITIDO guardar. Nunca devolve o cru.

        `shape_only` (default) devolve só `shape_of`: chaves, tipos e tamanhos.
        Suficiente para inferir um contrato de API, insuficiente para
        identificar alguém — o ponto de equilíbrio da SPEC-073 D3.

        `sanitized_sample` devolve o valor **depois** de `redigir()`, e ainda
        assim passa por `tem_vazamento()` antes de sair. Se o guarda achar algo,
        a amostra é descartada e sobra a forma. Cinto e suspensório de propósito:
        o redator é bom, e o dia em que um padrão novo escapar dele, o custo é
        PII de segurado em disco.
        """
        saida: Dict[str, Any] = {}
        dado: Any = None
        e_json = "json" in content_type
        if e_json:
            try:
                dado = json.loads(bruto)
            except Exception:  # noqa: BLE001
                dado = None
        if dado is None:
            # Texto/HTML/form: a forma é só o tamanho. `shape_of` de uma string
            # devolve `<string:N>` — nenhum caractere do conteúdo sobrevive.
            saida["shape"] = R.shape_of(bruto)
            return saida

        saida["shape"] = R.shape_of(dado)
        # 🔴 O modo é decidido POR HOST, não globalmente — ver `_modo_para`.
        # Host fora da allowlist ainda ganha a FORMA (que não guarda valor); o
        # que a allowlist protege é a amostra com valor.
        if self._modo_para(meta) != MODO_SANITIZED:
            return saida

        try:
            amostra = R.redigir(dado)
            vazou = R.tem_vazamento(amostra)
            if vazou:
                saida["amostra_recusada"] = vazou[:6]
                self.corpos_recusados["vazamento_detectado"] = (
                    self.corpos_recusados.get("vazamento_detectado", 0) + 1)
                return saida
            texto = json.dumps(amostra, ensure_ascii=False)[:self.orc.max_bytes_por_corpo]
            saida["amostra_sanitizada"] = json.loads(texto) if len(texto) < self.orc.max_bytes_por_corpo else amostra
        except Exception as e:  # noqa: BLE001
            self._falhou("sanitizar", e)
        return saida

    # ----------------------------------------------------------------------
    # Screenshot / DOM — SPEC-077 §9.5
    # ----------------------------------------------------------------------
    async def _talvez_screenshot(self, motivo: str) -> None:
        """Por evento SEMÂNTICO ou intervalo mínimo. Nunca por evento de rede.

        🔴 Uma tela de portal dispara dezenas de XHR. Screenshot por request
        produziria centenas de JPEG idênticos, encheria o teto de bytes e
        esconderia as três imagens que importam. Os gatilhos são: navegação,
        ação do agente, exceção — e mesmo eles respeitam o intervalo mínimo.
        """
        if self._parado or self._page is None:
            return
        if len(self.screenshots) >= self.orc.max_screenshots:
            return
        agora = time.time()
        if (agora - self._ultimo_shot_ts) < self.orc.intervalo_min_screenshot_s:
            return
        try:
            if getattr(self._page, "is_closed", None) and self._page.is_closed():
                return
            raw = await self._page.screenshot(type="jpeg", quality=55, full_page=False)
            if not raw:
                return
            self._ultimo_shot_ts = agora
            nome = f"shot-{len(self.screenshots):03d}.jpg"
            self.screenshots.append((nome, bytes(raw)))
            b = self._bucket()
            if b is not None:
                b.screenshot = nome  # "mais próximo" = o último desta página
            self._evento("tracer", method="Screenshot", arquivo=nome, motivo=motivo[:60])
        except Exception as e:  # noqa: BLE001
            self._falhou("screenshot", e)

    async def _talvez_dom(self, rotulo: str) -> None:
        """Snapshot de HTML — 🔴 só quando `orc.dom_snapshots` estiver ligado.

        HTML de portal autenticado é PII densa: nome, CPF, apólice, placa, tudo
        junto. Por isso nasce desligado, passa por `redigir_texto` e vai
        truncado. Nem assim é material para produção — é ferramenta de
        laboratório com o Founder olhando.
        """
        if self._parado or self._page is None or not self.orc.dom_snapshots:
            return
        if len(self.doms) >= self.orc.max_screenshots:
            return
        try:
            if getattr(self._page, "is_closed", None) and self._page.is_closed():
                return
            html = await self._page.content()
            limpo = R.redigir_texto(str(html or ""))[:self.orc.max_bytes_dom]
            nome = f"dom-{len(self.doms):03d}.html"
            self.doms.append((nome, limpo))
            b = self._bucket()
            if b is not None:
                b.dom_snapshot = nome
            self._evento("tracer", method="DomSnapshot", arquivo=nome, rotulo=rotulo[:60])
        except Exception as e:  # noqa: BLE001
            self._falhou("dom", e)

    # ----------------------------------------------------------------------
    # parar() — SPEC-077 §9.5 "stop garantido, nenhum processo órfão"
    # ----------------------------------------------------------------------
    async def parar(self) -> None:
        """Desliga tudo. Idempotente e seguro depois de crash.

        A ordem importa:

        1. marca `_parando` — para de aceitar trabalho novo na fila;
        2. desinscreve os ouvintes — evento que chega depois não mexe no estado;
        3. drena a fila com prazo, para não perder os corpos já pedidos;
        4. cancela a tarefa se o prazo estourar — **nada de tarefa órfã**;
        5. `detach` do CDP.

        Cada passo tem `try/except` próprio: o passo 5 tem de rodar mesmo que o
        3 exploda, senão sobra um cliente CDP anexado a um alvo morto.
        """
        if self._parado:
            return
        self._parando = True

        # 2. ouvintes
        for evento, cb in list(self._inscricoes_cdp):
            try:
                self._cdp.remove_listener(evento, cb)
            except Exception:  # noqa: BLE001
                pass  # alvo já morto: não há de quem desinscrever
        self._inscricoes_cdp.clear()
        for evento, cb in list(self._inscricoes_page):
            try:
                self._page.remove_listener(evento, cb)
            except Exception:  # noqa: BLE001
                pass
        self._inscricoes_page.clear()

        # 3 e 4. fila e tarefa
        tarefa, self._tarefa = self._tarefa, None
        if tarefa is not None:
            try:
                if self._fila is not None:
                    try:
                        self._fila.put_nowait(None)  # sentinela
                    except Exception:  # noqa: BLE001
                        pass
                await asyncio.wait_for(tarefa, timeout=self.orc.timeout_parada_s)
            except Exception as e:  # noqa: BLE001
                # inclui TimeoutError e CancelledError da própria espera
                self._falhou("parar:drenar", e)
                try:
                    tarefa.cancel()
                    await asyncio.gather(tarefa, return_exceptions=True)
                except Exception:  # noqa: BLE001
                    pass
        self._fila = None

        # 5. CDP
        cdp, self._cdp = self._cdp, None
        if cdp is not None:
            try:
                await cdp.detach()
            except Exception:  # noqa: BLE001
                pass  # sessão já caiu junto com o alvo — nada a fazer

        self._parado = True
        self._ligado = False
        self.ts_fim = time.time()
        if self.paginas and not self.paginas[-1].ts_fim:
            self.paginas[-1].ts_fim = self.ts_fim
        self._page = None

    # ----------------------------------------------------------------------
    # Saída
    # ----------------------------------------------------------------------
    def duracao_ms(self) -> int:
        fim = self.ts_fim or time.time()
        return max(0, int((fim - self.ts_inicio) * 1000))

    def resumo(self) -> Dict[str, Any]:
        """`summary.json` — e também o bloco que pode ir para `evidence`.

        Tudo passa por `redigir()` na saída. É redundante com a redação feita na
        entrada de cada evento, e é assim de propósito: um campo novo
        acrescentado com pressa em `_evento` não vira o vazamento da semana que
        vem.
        """
        if not self.habilitado:
            return {"enabled": False}
        bloco: Dict[str, Any] = {
            "enabled": True,
            "run_id": self.run_id,
            "portal_key": self.portal_key,
            "journey": self.journey,
            "job_id": self.job_id,
            "modo_corpo": self.modo_corpo,
            "hosts_corpo": list(self.hosts_corpo),
            "duracao_ms": self.duracao_ms(),
            "paginas": [b.para_dict() for b in self.paginas],
            "totais": {
                "eventos": len(self.eventos),
                "eventos_descartados": self.eventos_descartados,
                "requests": sum(b.requests for b in self.paginas),
                "falhas": sum(b.falhas for b in self.paginas),
                "excecoes": sum(b.excecoes for b in self.paginas),
                "corpos": self.corpos_capturados,
                "corpos_bytes": self.corpos_bytes,
                "screenshots": len(self.screenshots),
                "dom_snapshots": len(self.doms),
            },
            "corpos_recusados": dict(self.corpos_recusados),
            "erros_do_tracer": self.erros[:12],
            "parado": self._parado,
        }
        return R.redigir(bloco)

    def timeline(self) -> List[Dict[str, Any]]:
        """A linha do tempo unificada, já em ordem.

        Os eventos entram em ordem de chegada e todos usam o mesmo relógio, mas
        o `sorted` é estável e barato — e protege de um evento enfileirado que
        chegou fora de ordem.
        """
        return sorted(self.eventos, key=lambda e: (e.get("ts", 0.0), e.get("t_ms", 0)))

    def contratos_observados(self) -> List[Dict[str, Any]]:
        """O que sobrou dos corpos, pronto para o inferidor da SPEC-077 Bloco E.

        Nunca contém valor cru: só forma e, quando explicitamente pedido, a
        amostra já sanitizada.
        """
        return R.redigir(sorted(
            self.corpos.values(),
            key=lambda c: (str(c.get("host", "")), str(c.get("path", ""))),
        ))

    # ----------------------------------------------------------------------
    # Gravação em disco — SPEC-077 §9.6
    # ----------------------------------------------------------------------
    def gravar(self, destino: Any) -> Optional[str]:
        """Escreve `run/` navegável. Devolve o caminho, ou `None` se falhou.

        Síncrono porque é o fim do laboratório, não o caminho da journey — e
        porque `parar()` já rodou. 🔴 Ainda assim é blindado: nem um problema de
        permissão de disco pode levantar exceção para quem chamou.

        A estrutura é a da SPEC-077 §9.6 e existe para reduzir custo cognitivo:
        quem investiga abre `pages/003/` e vê a tela, as ações e o que a rede
        respondeu, sem varrer o JSONL inteiro.
        """
        if not self.habilitado:
            return None
        try:
            from pathlib import Path

            raiz = Path(str(destino))
            raiz.mkdir(parents=True, exist_ok=True)
            (raiz / "summary.json").write_text(
                json.dumps(self.resumo(), ensure_ascii=False, indent=2), encoding="utf-8")
            with (raiz / "unified-events.jsonl").open("w", encoding="utf-8") as fh:
                for linha in self.timeline():
                    fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
            corpos = self.contratos_observados()
            if corpos:
                (raiz / "bodies.json").write_text(
                    json.dumps(corpos, ensure_ascii=False, indent=2), encoding="utf-8")

            # 🔴 `media/` recebe TUDO que foi capturado, não só o que virou
            # "mais próximo" de alguma página. Uma tela pode gerar dois
            # screenshots (navegação + ação) e só o último fica apontado no
            # bucket; se a gravação escrevesse apenas os apontados, a imagem do
            # instante anterior — muitas vezes a que mostra o formulário ANTES
            # do erro — sumiria sem ninguém notar.
            shots = dict(self.screenshots)
            doms = dict(self.doms)
            if shots or doms:
                media = raiz / "media"
                media.mkdir(parents=True, exist_ok=True)
                for nome, dados in shots.items():
                    (media / nome).write_bytes(dados)
                for nome, texto in doms.items():
                    (media / nome).write_text(texto, encoding="utf-8")

            for b in self.paginas:
                pasta = raiz / "pages" / f"{b.indice:03d}"
                pasta.mkdir(parents=True, exist_ok=True)
                (pasta / "page.json").write_text(
                    json.dumps(R.redigir(b.para_dict()), ensure_ascii=False, indent=2),
                    encoding="utf-8")
                eventos_da_pagina = [e for e in self.timeline() if e.get("page") == b.indice]
                with (pasta / "events.jsonl").open("w", encoding="utf-8") as fh:
                    for linha in eventos_da_pagina:
                        fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
                if b.screenshot and b.screenshot in shots:
                    (pasta / b.screenshot).write_bytes(shots[b.screenshot])
                if b.dom_snapshot and b.dom_snapshot in doms:
                    (pasta / b.dom_snapshot).write_text(doms[b.dom_snapshot], encoding="utf-8")
            return str(raiz)
        except Exception as e:  # noqa: BLE001
            self._falhou("gravar", e)
            return None

    # ----------------------------------------------------------------------
    # Açúcar: `async with`
    # ----------------------------------------------------------------------
    async def __aenter__(self) -> "DeepTrace":
        return self

    async def __aexit__(self, *_exc: Any) -> bool:
        await self.parar()
        return False  # 🔴 nunca engole a exceção da journey


__all__ = [
    "DeepTrace",
    "OrcamentoTrace",
    "BucketDePagina",
    "MetodoCdpProibido",
    "METODOS_CDP_PERMITIDOS",
    "validar_metodo_cdp",
    "deep_trace_enabled",
    "content_type_e_de_dado",
    "host_permitido",
    "MODO_SHAPE_ONLY",
    "MODO_SANITIZED",
    "MODO_DESLIGADO",
    "MODOS_DE_CORPO",
]
