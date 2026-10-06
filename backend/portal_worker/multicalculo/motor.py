# -*- coding: utf-8 -*-
"""O motor do multicálculo — SPEC-129-B U4 (F3).

    laco_do_motor()   a task PRÓPRIA no startup do portal-worker, com navegador PRÓPRIO (D-MC-42)
    Motor.uma_volta() uma volta testável: expira · retoma · reserva · dispara os grupos

O FIO desta peça (SPEC §2, ③–⑦):

    fila `multicalculo_calculos` (na_fila) → reservar(): grupos (pedido, corretora) por prioridade
      → robos.escolher(): LEASE DO ROBÔ NO BANCO (D-129B-10) → CAS na_fila→disparando (dono + batida)
      → decifra o pedido (portal_worker.vault) → Sessoes.obter(conta, senha, negocios_do_robo)
      → padrão: agger_robo.disparar → 🔴 CHECKPOINT (calculando + negocio_ref + versao)
      → econômica no MESMO negócio → CHECKPOINT → acompanhar as duas em PARALELO
      → cada Evento: upsert da oferta + evento com chave ÚNICA (repetido = no-op)
      → copiar_pdfs → `_upload_portal_blob` → fechado

🔴 Não é executor paralelo (CLAUDE.md §5): vive no MESMO serviço `portal-worker` e reusa as peças
dele — cofre (`vault.decrypt`), redator (`redaction`), freio (`runtime.kill_switch_ativo`), upload
(`worker._upload_portal_blob`), modo do navegador (`worker._launch_kwargs`), identidade do dono
(`leases.identidade_do_worker`). A fila é própria porque o Founder decidiu (D-MC-42, D-129B-01): 📊
`run_lote` junta o lote num `asyncio.gather` (`worker.py:1795`) e um cálculo de 7 min seguraria a
cobrança e os vidros. O `poll_loop`/`run_lote` ficam INTOCADOS.

🔴 Retomada sem recalcular (D-129B-06, molde Stripe idempotency + Temporal): `calculando` com batida
vencida → outro motor RETOMA SÓ A LEITURA, com a rodada anterior montada das ofertas gravadas;
`disparando` com batida vencida → `incerto`. O motor NUNCA repete um POST sozinho.

⛔ O pedido decifrado e a senha só existem em memória: nunca em log, evento, erro ou exceção. Todo
`erro` gravado é texto CURTO e saneado — nunca `str(exceção)` cru.
⛔ Nenhuma mensagem sai desta peça. Nenhum modelo é chamado.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from .. import redaction as _R
from ..runtime import kill_switch_ativo
from ..worker import _inteiro_do_ambiente, _upload_portal_blob, portal_real_enabled
from . import robos
from .contrato import (
    CONJUNTO_FECHADO, NOVA_OFERTA, OFERTA, OFERTA_ATUALIZADA, SEGURADORA_RECUSOU, Ajuste, Evento, Oferta,
    RespostaDaSeguradora, RodadaDoCalculo,
)

logger = logging.getLogger("portal_worker.multicalculo")

# ==========================================================================
# As constantes, cada uma com o porquê
# ==========================================================================
# A batida a cada 20 s e a lease que vence em 90 s: o dono perde QUATRO batidas seguidas antes de
# outro motor assumir. Uma pausa de GC ou um PostgREST lento não trocam o dono; um processo morto é
# substituído em ≤ 90 s — e o cálculo do Agger leva 📊 40 s–7 min, então a retomada cabe dentro dele.
BATIDA_S = 20
LEASE_VENCE_S = robos.LEASE_VENCE_S

# De quanto em quanto tempo o laço olha a fila. 5 s: o 1º evento tem meta de ≤ 15 s (SPEC §1) e o
# login sozinho leva 📊 5–52 s (E1) — olhar mais devagar comeria a meta; mais depressa só gasta SELECT.
VOLTA_S = 5

# `SessaoOcupada` numa conta `ativo`: alguém (uma pessoa) entrou com o login do robô. 💭 30 min de
# afastamento: tempo de a pessoa terminar o que foi fazer sem o robô derrubar a sessão dela a cada volta.
OCUPADA_MIN = 30

# 💭 3 retomadas: a 4ª queda do acompanhamento do mesmo cálculo é defeito, não azar — vira `falhou`
# com o motivo, em vez de um laço infinito de leituras.
MAX_RETOMADAS = 3

# Sessão aberta e sem grupo: o motor SEGURA a lease do robô enquanto ela vive (outro motor que logasse
# por cima veria o aviso de "sessão ativa" e afastaria o robô por 30 min). 💭 10 min ociosa → logout e a
# lease volta: o login custa 📊 5–52 s (E1), e reaproveitar dentro de 10 min paga; ficar logado a tarde
# inteira sem trabalho só expõe a conta.
OCIOSA_MAX_S = 600

# Login que falhou por um motivo QUALQUER (rede, portal fora): o cálculo volta à fila com espera de
# 60 s × tentativas (teto 15 min). Sem isso o laço (5 s) tentaria logar 12 vezes por minuto num portal
# que caiu — é assim que um login é bloqueado pela seguradora. O `expira_em` do pedido encerra a espera.
ATRASO_POR_TENTATIVA_S = 60
ATRASO_MAX_S = 900

# Quantas linhas da fila uma volta olha. 💭 50: cobre ~25 pedidos de 2 opções; o resto espera 5 s.
LIMITE_DA_FILA = 50

# Os freios da corretora e do geral (D-129B-07), lidos A CADA VOLTA (mudar numa emergência não pode
# exigir reiniciar). 💭 120/h por corretora = 60 pedidos de 2 opções por hora — muito acima do uso de
# uma corretora (o robô faz um grupo por vez, de 40 s a 7 min), e baixo o bastante para um laço
# descontrolado parar antes de a seguradora marcar o CPF como "cotado em excesso". 💭 400/h geral =
# o teto de N corretoras juntas na mesma imagem.
TETO_CORRETORA_HORA_PADRAO = 120
TETO_GERAL_HORA_PADRAO = 400

ESTADOS_TERMINAIS = ("fechado", "falhou", "incerto", "cancelado", "expirado")
_ORDEM_DA_OPCAO = {"padrao": 0, "economica": 1, "ajuste": 2}

MOTIVO_PESSOA_MEXEU = "uma pessoa mexeu neste negócio há menos de 24 h"
MOTIVO_SAIU_DO_CANAL = "a corretora saiu do canal"
MOTIVO_AJUSTE_REPETIDO = "o mesmo ajuste deste cálculo já foi pedido e está em curso"
MOTIVO_NAO_LEU = "não consegui ler o resultado no Agger"
MOTIVO_LEU_PARTE = "o Agger parou de responder depois do quadro: fechado com o que foi lido"
MOTIVO_TESTE_INDEFINIDO = "o login da conta de teste não chegou ao fim: o robô parou e pausou a conta"
KIND_CANAL = "platform_canal"
MOTIVO_INCERTO = ("o disparo PODE ter saído no portal e o motor não teve a confirmação: "
                  "não refaça sem conferir o negócio no Agger")
MOTIVO_MORREU_NO_DISPARO = ("o motor caiu durante o disparo: o cálculo PODE ter saído no portal — "
                            "não refaça sem conferir o negócio no Agger")


def motor_ligado() -> bool:
    """D-129B-09: o motor nasce DESLIGADO."""
    return str(os.getenv("MULTICALCULO_MOTOR_LIGADO", "false")).strip().lower() in ("1", "true", "yes", "on")


def canario_ligado() -> bool:
    """D-129B-04: pedido `teste` (e a conta de PESSOA) só no processo do canário."""
    return str(os.getenv("AUTOBROKERS_CANARIO", "")).strip() == "1"


def teto_corretora_hora() -> int:
    return _inteiro_do_ambiente("MULTICALCULO_TETO_CORRETORA_HORA", TETO_CORRETORA_HORA_PADRAO, 1, 5000)


def teto_geral_hora() -> int:
    return _inteiro_do_ambiente("MULTICALCULO_TETO_GERAL_HORA", TETO_GERAL_HORA_PADRAO, 1, 50000)


def _agora_real() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat()


def _ts(valor: Any) -> Optional[datetime]:
    return robos._ts(valor)


_RE_ESPACOS = re.compile(r"\s+")


def erro_curto(texto: Any, limite: int = 200) -> str:
    """O `erro` que vai para o banco: sem URL, sem chave, sem PII, numa linha, curto.
    🔴 Nunca recebe `str(exceção)` — quem chama passa um texto escrito aqui ou um `motivo` curado."""
    s = _R.redigir_texto(_R.sem_url_nem_chave(texto))
    s = _RE_ESPACOS.sub(" ", s).strip()
    return s[:limite]


def _motivo_recusado(exc: BaseException) -> str:
    motivo = getattr(exc, "motivo", None)
    if isinstance(motivo, str) and motivo.strip():
        return erro_curto("o portal recusou o cálculo: " + motivo)
    return "o portal recusou o cálculo"


def chave_do_evento(e: Evento) -> str:
    """A chave ÚNICA do evento no cálculo (`unique(calculo_id, chave)`): repetir = no-op.

    tipo + seguradora + pacote + tipo de pacote + prêmio em CENTAVOS (a mesma oferta com outro preço
    é outro evento); `conjunto_fechado` sozinho. 🔴 A recusa leva a FAMÍLIA: `eventos_entre` narra a
    recusa de novo quando a família muda, e sem ela a 2ª seria engolida pela 1ª."""
    if e.tipo == CONJUNTO_FECHADO:
        return CONJUNTO_FECHADO
    seg = e.seguradora_codigo if e.seguradora_codigo is not None else (e.seguradora or "")
    o = e.oferta
    if o is not None:
        centavos = int(round(float(o.premio_total) * 100))
        return f"{e.tipo}|{seg}|{o.pacote}|{o.tipo_de_pacote}|{centavos}"
    return f"{e.tipo}|{seg}|{e.familia or ''}"


# ==========================================================================
# O grupo
# ==========================================================================
@dataclass
class Grupo:
    pedido_id: str
    company_id: str                 # a corretora de REGISTRO (dona do login e do negócio)
    solicitante_company_id: str     # quem pediu (a própria corretora ou o canal)
    calculos: List[Dict[str, Any]]
    origem: str = ""
    quadro_s: float = 60
    retomada: bool = False
    ativos: set = field(default_factory=set)   # ids que a batida ainda precisa segurar
    sessao_morta: bool = False                 # 401/403 ou página fechada: a sessão é DESCARTADA no fim do grupo


class _PossePerdida(Exception):
    """A batida não voltou: outro motor é o dono agora. Parar de gravar é a única saída segura."""


class _NuncaLevantada(Exception):
    """Lugar de `LeituraImpossivel` quando o robô injetado não a declara (o `except` não casa nada)."""


class _NavegadorProprio:
    """O navegador DO MOTOR (D-MC-42) — nunca o do `run_lote`. Abre só quando um robô foi escolhido:
    ligado e sem conta de robô, o motor não abre navegador nenhum (D-129B-09)."""

    def __init__(self) -> None:
        self._pw = None
        self._navegador = None

    async def abrir(self):
        from playwright.async_api import async_playwright

        from ..worker import _launch_kwargs
        from .agger_sessao import Sessoes

        self._pw = await async_playwright().start()
        self._navegador = await self._pw.chromium.launch(**_launch_kwargs())
        return Sessoes(self._navegador)

    async def fechar(self) -> None:
        for alvo in (self._navegador, self._pw):
            if alvo is None:
                continue
            try:
                await (alvo.close() if alvo is self._navegador else alvo.stop())
            except Exception:  # noqa: BLE001
                pass
        self._navegador = self._pw = None


# ==========================================================================
# O motor
# ==========================================================================
class Motor:
    """Uma instância por processo. Tudo que é borda é injetável (banco, sessões, robô, relógio,
    cofre, upload) para o teste atravessar o motor REAL com dublê só na borda."""

    def __init__(self, supa, *, sessoes=None,
                 fabrica_de_sessoes: Optional[Callable[[], Awaitable[Any]]] = None,
                 robo=None, sessao_mod=None, dono: Optional[str] = None,
                 agora: Optional[Callable[[], datetime]] = None,
                 batida_s: float = BATIDA_S, lease_s: int = LEASE_VENCE_S,
                 decifrar: Optional[Callable[[str], str]] = None,
                 upload: Optional[Callable[..., Awaitable[Optional[str]]]] = None,
                 freio: Optional[Callable[[], bool]] = None,
                 canario: Optional[bool] = None,
                 somente_pedidos: Optional[set] = None) -> None:
        self.supa = supa
        # Conserto 129-B (juiz P10): o motor do CANÁRIO serve só os pedidos que ele criou (o conjunto é lido a cada
        # volta: quem o passa pode acrescentar ids depois). None = a fila inteira (o serviço).
        self.somente_pedidos = somente_pedidos
        self._sessoes = sessoes
        self._fabrica = fabrica_de_sessoes
        self._navegador: Optional[_NavegadorProprio] = None
        self._robo = robo
        self._sessao_mod = sessao_mod
        if dono is None:
            from ..leases import identidade_do_worker

            dono = identidade_do_worker() + ":mc"
        self.dono = dono
        self.agora = agora or _agora_real
        self.batida_s = batida_s
        self.lease_s = lease_s
        self._decifrar = decifrar
        self._upload = upload or _upload_portal_blob
        self._freio = freio or kill_switch_ativo
        self._canario = canario
        self._tarefas: set = set()
        self._contas_em_uso: set = set()
        self._contas_com_sessao: Dict[str, Dict[str, Any]] = {}
        self._ociosas: Dict[str, Dict[str, Any]] = {}
        self._abrindo = asyncio.Lock()
        # 🔴 conserto 129-B (canário ao vivo 05/10): o motor que está ENCERRANDO (deploy) não grava estado de cálculo
        # nem de conta por caminho de erro — o erro é efeito da própria morte, não do Agger. Ver `encerrar()`.
        self._encerrando = False

    # -- as bordas, resolvidas tarde (o robô da F2 é importado só quando é usado) ----------
    @property
    def robo(self):
        if self._robo is None:
            from . import agger_robo

            self._robo = agger_robo
        return self._robo

    @property
    def sessao_mod(self):
        if self._sessao_mod is None:
            from . import agger_sessao

            self._sessao_mod = agger_sessao
        return self._sessao_mod

    def decifrar(self, token: str) -> str:
        if self._decifrar is not None:
            return self._decifrar(token)
        from .. import vault

        return vault.decrypt(token)

    def canario(self) -> bool:
        return canario_ligado() if self._canario is None else bool(self._canario)

    async def _sessoes_prontas(self):
        async with self._abrindo:
            if self._sessoes is None:
                if self._fabrica is not None:
                    self._sessoes = await self._fabrica()
                else:
                    self._navegador = _NavegadorProprio()
                    self._sessoes = await self._navegador.abrir()
            return self._sessoes

    async def _db(self, fn: Callable[[], Any]) -> Any:
        """Toda ida ao banco sai do laço de eventos: o supabase-py é BLOQUEANTE, e o `poll_loop` da
        cobrança e dos vidros mora no mesmo laço (G8)."""
        return await asyncio.to_thread(fn)

    # ======================================================================
    # A volta
    # ======================================================================
    async def uma_volta(self, *, esperar: bool = True) -> int:
        """Expira · retoma · reserva · dispara. Devolve quantos grupos começaram nesta volta.
        `esperar=True` (testes, canário) aguarda os grupos; o laço passa `False` e segue olhando a fila."""
        if self._freio():
            logger.warning("[MC] GLOBAL_KILL_SWITCH ativo — nenhum cálculo sai")
            return 0
        await self._cuidar_das_ociosas()
        await self._expirar()
        pares = await self._retomadas()
        pares += await self._reservar()
        novas = []
        for grupo, conta in pares:
            t = asyncio.create_task(self._executar_grupo(grupo, conta))
            self._tarefas.add(t)
            t.add_done_callback(self._tarefas.discard)
            novas.append(t)
        if esperar and novas:
            await asyncio.gather(*novas, return_exceptions=True)
        return len(novas)

    async def esperar_tudo(self) -> None:
        if self._tarefas:
            await asyncio.gather(*list(self._tarefas), return_exceptions=True)

    async def desligar(self) -> None:
        """Fecha as sessões (logout) e o navegador próprio. Os grupos em curso seguem até o fim da
        tarefa deles; quem está `calculando` é retomado por outro motor se este morrer."""
        try:
            if self._sessoes is not None:
                await self._sessoes.fechar_todas()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MC] fechar as sessões falhou (%s)", type(exc).__name__)
        for o in list(self._ociosas.values()):
            await self._db(lambda c=o["conta"]: robos.liberar(self.supa, c, self.dono))
        self._ociosas.clear()
        self._contas_com_sessao.clear()
        self._sessoes = None
        if self._navegador is not None:
            await self._navegador.fechar()
            self._navegador = None

    async def encerrar(self) -> None:
        """F4 (junta 8) — o DESLIGAR do processo (deploy, reinício): para os grupos em curso e faz o logout de
        TODAS as sessões, devolvendo as leases. 🔴 Sem isto, a sessão do robô fica viva no Agger e o próximo login
        vê o aviso de "sessão ativa" → o robô vira `ocupada` (ou `pausado`, se for conta `teste`) por um deploy.
        O que estava `calculando` fica para a retomada (o negócio existe; outro motor só LÊ); o que estava
        `disparando` vira `incerto` pela retomada — nunca um 2º POST.

        🔴 Conserto 129-B (📊 canário ao vivo 05/10 21:27): os 4 cálculos `calculando` viraram `falhou` "não consegui
        ler" 2–5 s DEPOIS deste encerrar. Causa: cancelar a tarefa do grupo não cancelava a do TRABALHO (o
        `asyncio.wait` não cancela o que espera); o acompanhamento seguia órfão, o `desligar()` fechava a página e o
        `TargetClosedError` virava `LeituraImpossivel(sessão morta)` → `falhou`. Agora, nesta ordem: (1) a marca
        `_encerrando` ANTES de cancelar — nenhum caminho de erro grava estado; (2) cancelar e AGUARDAR os grupos (cada
        grupo aguarda o trabalho, as leituras filhas e a batida); (3) só então logout e navegador."""
        self._encerrando = True
        tarefas = [t for t in list(self._tarefas) if not t.done()]
        for t in tarefas:
            t.cancel()
        if tarefas:
            await asyncio.gather(*tarefas, return_exceptions=True)
        await self.desligar()

    # ======================================================================
    # Expirar · retomar · reservar
    # ======================================================================
    def _so_meus(self, q):
        """O filtro do canário (`somente_pedidos`). Conjunto vazio = nenhum pedido (nunca a fila inteira)."""
        if self.somente_pedidos is None:
            return q
        return q.in_("pedido_id", sorted(self.somente_pedidos) or ["00000000-0000-0000-0000-000000000000"])

    async def _expirar(self) -> None:
        agora = _iso(self.agora())
        r = await self._db(lambda: self._so_meus(self.supa.table("multicalculo_calculos")
                           .select("id, company_id, pedido_id, solicitante_company_id")
                           .eq("status", "na_fila").lt("expira_em", agora)).limit(200).execute())
        pedidos = set()
        for c in (r.data or []):
            await self._db(lambda c=c: self.supa.table("multicalculo_calculos").update({
                "status": "expirado", "erro": "o pedido esperou na fila mais que o prazo dele",
                "fechado_em": agora,
            }).eq("id", c["id"]).eq("company_id", c["company_id"]).eq("status", "na_fila").execute())
            pedidos.add((c["pedido_id"], c["solicitante_company_id"]))
        for p in pedidos:
            await self._fechar_pedido_se_terminou(*p)

    async def _pedido(self, pedido_id: str, solicitante: str, colunas: str) -> Optional[Dict[str, Any]]:
        r = await self._db(lambda: self.supa.table("multicalculo_pedidos").select(colunas)
                           .eq("id", pedido_id).eq("company_id", solicitante).limit(1).execute())
        return (r.data or [None])[0]

    async def _retomadas(self) -> List[Tuple[Grupo, Dict[str, Any]]]:
        """D-129B-06. `disparando` vencido → `incerto` (nunca re-POST). `calculando` vencido → retomar
        SÓ a leitura, com um robô da MESMA corretora."""
        agora = self.agora()
        vencida = _iso(agora - timedelta(seconds=self.lease_s))
        r = await self._db(lambda: self._so_meus(self.supa.table("multicalculo_calculos").select("*")
                           .in_("status", ["disparando", "calculando"]).lt("batida_em", vencida))
                           .order("prioridade").limit(LIMITE_DA_FILA).execute())
        grupos: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for c in (r.data or []):
            if c["status"] == "disparando":
                await self._db(lambda c=c: self.supa.table("multicalculo_calculos").update({
                    "status": "incerto", "erro": MOTIVO_MORREU_NO_DISPARO, "fechado_em": _iso(agora),
                    "dono": None, "batida_em": None,
                }).eq("id", c["id"]).eq("company_id", c["company_id"]).eq("status", "disparando")
                    .lt("batida_em", vencida).execute())
                await self._fechar_pedido_se_terminou(c["pedido_id"], c["solicitante_company_id"])
                continue
            if int(c.get("tentativas") or 0) > MAX_RETOMADAS:
                await self._db(lambda c=c: self.supa.table("multicalculo_calculos").update({
                    "status": "falhou", "fechado_em": _iso(agora), "dono": None, "batida_em": None,
                    "erro": f"o acompanhamento caiu mais de {MAX_RETOMADAS} vezes; o negócio continua no "
                            "Agger e pode ser consultado lá",
                }).eq("id", c["id"]).eq("company_id", c["company_id"]).eq("status", "calculando")
                    .lt("batida_em", vencida).execute())
                await self._fechar_pedido_se_terminou(c["pedido_id"], c["solicitante_company_id"])
                continue
            grupos.setdefault((c["pedido_id"], c["company_id"]), []).append(c)

        pares: List[Tuple[Grupo, Dict[str, Any]]] = []
        for (pedido_id, corretora), calcs in grupos.items():
            solicitante = calcs[0]["solicitante_company_id"]
            pedido = await self._pedido(pedido_id, solicitante, "id, origem, quadro_s")
            if not pedido:
                continue
            if (pedido.get("origem") or "") == "teste" and not self.canario():
                continue   # conserto 129-B (red P6): pedido de teste só no canário — também na retomada
            conta = await self._escolher(corretora, pedido.get("origem") or "", agora, 1)
            if conta is None:
                continue
            tomados = []
            for c in calcs:
                ok = await self._db(lambda c=c: self.supa.table("multicalculo_calculos").update({
                    "dono": self.dono, "batida_em": _iso(agora), "account_id": conta["id"],
                    "tentativas": int(c.get("tentativas") or 0) + 1,
                }).eq("id", c["id"]).eq("company_id", corretora).eq("status", "calculando")
                    .lt("batida_em", vencida).execute())
                if ok.data:
                    tomados.append(ok.data[0])
            if not tomados:
                await self._soltar_conta(conta)
                continue
            logger.info("[MC] retomando %s cálculo(s) do pedido %s (só leitura)", len(tomados), pedido_id)
            pares.append((Grupo(pedido_id, corretora, solicitante, tomados, pedido.get("origem") or "",
                                float(pedido.get("quadro_s") or 60), retomada=True), conta))
        return pares

    async def _reservar(self) -> List[Tuple[Grupo, Dict[str, Any]]]:
        """Grupos (pedido, corretora) `na_fila` por prioridade → freios → robô (lease) → CAS de cada
        cálculo `na_fila→disparando` com dono + batida. Corretoras diferentes saem em PARALELO; a mesma
        conta, um grupo por vez (a lease)."""
        agora = self.agora()
        agora_iso = _iso(agora)
        r = await self._db(lambda: self._so_meus(self.supa.table("multicalculo_calculos").select("*")
                           .eq("status", "na_fila")
                           .or_(f"disponivel_em.is.null,disponivel_em.lte.{agora_iso}"))
                           .order("prioridade").order("criado_em").limit(LIMITE_DA_FILA).execute())
        linhas = list(r.data or [])
        if not linhas:
            return []
        grupos: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for c in linhas:
            grupos.setdefault((c["pedido_id"], c["company_id"]), []).append(c)

        desde = _iso(agora - timedelta(hours=1))
        # 🔴 O freio GERAL é uma contagem da imagem inteira (todas as corretoras): só `id`, nenhum dado.
        geral = await self._db(lambda: len(self.supa.table("multicalculo_calculos").select("id")
                                           .gte("disparado_em", desde).execute().data or []))
        por_corretora: Dict[str, int] = {}
        pares: List[Tuple[Grupo, Dict[str, Any]]] = []
        for (pedido_id, corretora), calcs in grupos.items():
            solicitante = calcs[0]["solicitante_company_id"]
            pedido = await self._pedido(pedido_id, solicitante, "id, origem, quadro_s, status")
            if not pedido:
                continue
            if pedido.get("status") not in (None, "aberto"):
                for c in calcs:   # pedido cancelado/fechado: o que ainda estava na fila não sai mais
                    await self._db(lambda c=c: self.supa.table("multicalculo_calculos").update({
                        "status": "cancelado", "fechado_em": agora_iso,
                    }).eq("id", c["id"]).eq("company_id", corretora).eq("status", "na_fila").execute())
                continue
            origem = pedido.get("origem") or ""
            if origem == "teste" and not self.canario():
                continue   # D-129B-04: pedido de teste só no processo do canário; fica até expirar
            if not await self._canal_autorizado(solicitante, corretora):
                # 🔴 conserto 129-B (red B2): a corretora saiu do canal com o pedido na fila — nada sai no login dela
                for c in calcs:
                    await self._cancelar_na_fila(c, corretora, MOTIVO_SAIU_DO_CANAL, agora_iso)
                continue
            calcs, repetidos = await self._separar_ajustes_repetidos(calcs, corretora)
            for c in repetidos:
                await self._cancelar_na_fila(c, corretora, MOTIVO_AJUSTE_REPETIDO, agora_iso)
            if not calcs:
                continue
            espera, conta_fixa = await self._conta_do_grupo(pedido_id, corretora, {c["id"] for c in calcs})
            if espera:
                continue   # um cálculo irmão está saindo AGORA noutro motor: o negócio dele ainda não existe
            if corretora not in por_corretora:
                por_corretora[corretora] = await self._db(lambda c=corretora: robos.calculos_na_ultima_hora(
                    self.supa, company_id=c, agora=agora))
            n = len(calcs)
            if geral + n > teto_geral_hora():
                logger.warning("[MC] teto GERAL por hora atingido (%s) — o grupo espera", teto_geral_hora())
                continue
            if por_corretora[corretora] + n > teto_corretora_hora():
                logger.warning("[MC] teto da corretora %s por hora atingido — o grupo espera", corretora)
                continue
            conta = await self._escolher(corretora, origem, agora, n, somente=conta_fixa)
            if conta is None:
                continue
            tomados = []
            for c in calcs:
                ok = await self._db(lambda c=c: self.supa.table("multicalculo_calculos").update({
                    "status": "disparando", "dono": self.dono, "batida_em": agora_iso,
                    "account_id": conta["id"], "disparado_em": agora_iso,
                    "tentativas": int(c.get("tentativas") or 0) + 1,
                }).eq("id", c["id"]).eq("company_id", corretora).eq("status", "na_fila").execute())
                if ok.data:
                    tomados.append(ok.data[0])
            if not tomados:
                await self._soltar_conta(conta)
                continue
            geral += len(tomados)
            por_corretora[corretora] += len(tomados)
            pares.append((Grupo(pedido_id, corretora, solicitante, tomados, origem,
                                float(pedido.get("quadro_s") or 60)), conta))
        return pares

    async def _escolher(self, corretora: str, origem: str, agora: datetime, quantos: int,
                        somente: Optional[str] = None):
        """`robos.escolher` + a marca EM USO já na seleção: dois grupos da mesma volta nunca pegam o
        mesmo robô, nem quando a lease dele já é deste motor (sessão ociosa)."""
        conta = await self._db(lambda: robos.escolher(
            self.supa, corretora, origem, dono=self.dono, agora=agora, quantos=quantos,
            canario=self.canario(), lease_s=self.lease_s, ignorar=set(self._contas_em_uso), somente=somente))
        if conta is not None:
            self._contas_em_uso.add(conta["id"])
            self._ociosas.pop(conta["id"], None)
        return conta

    # ------------------------------------------------------------------ as reconferências NA HORA do efeito
    async def _canal_autorizado(self, solicitante: str, corretora: str) -> bool:
        """🔴 Conserto 129-B (red B2): o login de uma corretora só trabalha para OUTRO solicitante se ele é a empresa
        do canal (`platform_canal`) E a adesão canal → corretora está ATIVA — conferido AGORA, não quando o pedido
        entrou na fila. Falha de leitura = não autorizado (fail-closed)."""
        if str(solicitante) == str(corretora):
            return True
        try:
            emp = await self._db(lambda: self.supa.table("companies").select("id, company_kind")
                                 .eq("id", solicitante).limit(1).execute())
            if ((emp.data or [{}])[0]).get("company_kind") != KIND_CANAL:
                return False
            ad = await self._db(lambda: self.supa.table("multicalculo_adesoes").select("id, ativa")
                                .eq("canal_company_id", solicitante).eq("corretora_company_id", corretora)
                                .eq("ativa", True).limit(1).execute())
            return bool([x for x in (ad.data or []) if x.get("ativa") is True])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MC] não consegui conferir a adesão (%s) — o cálculo não sai", type(exc).__name__)
            return False

    async def _cancelar_na_fila(self, c: Dict[str, Any], corretora: str, motivo: str, agora_iso: str) -> None:
        await self._db(lambda: self.supa.table("multicalculo_calculos").update({
            "status": "cancelado", "fechado_em": agora_iso, "erro": erro_curto(motivo),
        }).eq("id", c["id"]).eq("company_id", corretora).eq("status", "na_fila").execute())
        await self._fechar_pedido_se_terminou(c["pedido_id"], c["solicitante_company_id"])

    @staticmethod
    def _chave_do_ajuste(c: Dict[str, Any]) -> Optional[str]:
        if c.get("opcao") != "ajuste":
            return None
        aj = c.get("ajuste") if isinstance(c.get("ajuste"), dict) else {}
        return json.dumps([str(c.get("origem_calculo_id")), aj.get("tipo"), aj.get("valor"), aj.get("seguradora")],
                          sort_keys=True, default=str)

    async def _separar_ajustes_repetidos(self, calcs: List[Dict[str, Any]], corretora: str):
        """🔴 Conserto 129-B (red P4): o MESMO ajuste da MESMA origem duas vezes (clique duplo) sai UMA vez. Repetido =
        outro igual neste grupo (fica o mais antigo) ou um igual já `disparando`/`calculando`."""
        ajustes = [c for c in calcs if c.get("opcao") == "ajuste"]
        if not ajustes:
            return calcs, []
        origens = sorted({str(c.get("origem_calculo_id")) for c in ajustes if c.get("origem_calculo_id")})
        em_curso = set()
        if origens:
            r = await self._db(lambda: self.supa.table("multicalculo_calculos")
                               .select("id, opcao, origem_calculo_id, ajuste, status")
                               .eq("company_id", corretora).in_("origem_calculo_id", origens)
                               .in_("status", ["disparando", "calculando"]).execute())
            em_curso = {self._chave_do_ajuste(x) for x in (r.data or [])} - {None}
        vistos, manter, repetidos = set(em_curso), [], []
        for c in sorted(calcs, key=lambda x: str(x.get("criado_em") or "")):
            k = self._chave_do_ajuste(c)
            if k is not None and k in vistos:
                repetidos.append(c)
                continue
            if k is not None:
                vistos.add(k)
            manter.append(c)
        return manter, repetidos

    async def _conta_do_grupo(self, pedido_id: str, corretora: str, ids_do_grupo: set):
        """🔴 Conserto 129-B (juiz P11): (esperar, conta). Os cálculos de um mesmo (pedido, corretora) ficam na MESMA
        conta: a econômica (e o ajuste) entram no negócio que já existe, e o negócio é DA conta que o abriu. Um irmão
        ainda `disparando` (o negócio dele não existe ainda) → o grupo ESPERA, nunca abre negócio novo noutra conta."""
        r = await self._db(lambda: self.supa.table("multicalculo_calculos")
                           .select("id, status, account_id, negocio_ref, opcao, criado_em")
                           .eq("pedido_id", pedido_id).eq("company_id", corretora)
                           .in_("status", ["disparando", "calculando", "fechado"]).order("criado_em").execute())
        irmaos = [x for x in (r.data or []) if x["id"] not in ids_do_grupo]
        if any(x.get("status") == "disparando" for x in irmaos):
            return True, None
        com_negocio = [x for x in irmaos if x.get("account_id") and x.get("negocio_ref")]
        com_negocio.sort(key=lambda x: (x.get("opcao") == "ajuste", str(x.get("criado_em") or "")))
        return False, (str(com_negocio[0]["account_id"]) if com_negocio else None)

    async def _soltar_conta(self, conta: Dict[str, Any], *, perdeu: bool = False, descartar: bool = False) -> None:
        """Fim do uso do robô. Sessão aberta de conta `ativo` → fica OCIOSA com a lease (reaproveita o
        login); conta `teste` (login de PESSOA) → logout e lease devolvida (D-129B-04). Sessão MORTA (401/403)
        → descartada sem logout e NUNCA reaproveitada (conserto 129-B, juiz B1)."""
        self._contas_em_uso.discard(conta["id"])
        if descartar:
            self._ociosas.pop(conta["id"], None)
            await self._descartar_sessao(conta["id"])
            await self._db(lambda: robos.liberar(self.supa, conta, self.dono))
            return
        if (conta["id"] in self._contas_com_sessao and conta.get("robo_estado") != robos.TESTE
                and not perdeu):
            agora = self.agora()
            self._ociosas[conta["id"]] = {"conta": conta, "desde": agora, "batida": agora}
            return
        if conta["id"] in self._contas_com_sessao:
            await self._fechar_sessao(conta["id"])
        await self._db(lambda: robos.liberar(self.supa, conta, self.dono))

    async def _cuidar_das_ociosas(self) -> None:
        """A cada volta: sessão ociosa vencida, fora da janela ou de conta que deixou de estar ativa →
        logout + lease devolvida; as outras recebem a batida (a lease não pode vencer com a sessão viva)."""
        agora = self.agora()
        for conta_id, o in list(self._ociosas.items()):
            if conta_id in self._contas_em_uso:
                continue
            conta = o["conta"]
            r = await self._db(lambda: self.supa.table("portal_accounts").select("robo_estado, robo_janela")
                               .eq("id", conta_id).eq("company_id", conta["company_id"]).limit(1).execute())
            atual = (r.data or [None])[0]
            fechar = ((agora - o["desde"]).total_seconds() >= OCIOSA_MAX_S or not atual
                      or atual.get("robo_estado") != robos.ATIVO
                      or not robos.dentro_da_janela(atual.get("robo_janela"), agora))
            if not fechar and (agora - o["batida"]).total_seconds() >= self.batida_s:
                if await self._db(lambda: robos.renovar(self.supa, conta, self.dono, agora)):
                    o["batida"] = agora
                else:
                    fechar = True
            if fechar:
                self._ociosas.pop(conta_id, None)
                await self._fechar_sessao(conta_id)
                await self._db(lambda: robos.liberar(self.supa, conta, self.dono))

    # ======================================================================
    # O grupo: batida + trabalho; perdeu a posse → para de gravar
    # ======================================================================
    async def _executar_grupo(self, g: Grupo, conta: Dict[str, Any]) -> None:
        g.ativos = {c["id"] for c in g.calculos}
        self._contas_em_uso.add(conta["id"])
        perdeu = asyncio.Event()
        batida = asyncio.create_task(self._bater(g, conta, perdeu))
        trabalho = asyncio.create_task(self._trabalho(g, conta, perdeu))
        espera = asyncio.create_task(perdeu.wait())
        try:
            feito, _ = await asyncio.wait({trabalho, espera}, return_when=asyncio.FIRST_COMPLETED)
            if trabalho not in feito:
                # Como no `run_lote`: perdeu a posse → cancela. NADA volta para a fila — o que pode ter
                # tocado o portal fica com quem assumiu (retomada) ou vira `incerto`.
                logger.error("[MC] perdi a posse do grupo do pedido %s — parando de gravar", g.pedido_id)
                trabalho.cancel()
                try:
                    await trabalho
                except BaseException:  # noqa: BLE001
                    pass
            else:
                espera.cancel()
                exc = trabalho.exception()
                if exc is not None:
                    if not isinstance(exc, Exception):
                        raise exc
                    logger.error("[MC] o grupo do pedido %s falhou (%s)", g.pedido_id, type(exc).__name__)
        finally:
            # 🔴 conserto 129-B: o TRABALHO também (o `asyncio.wait` cancelado não cancela o que esperava) — e todos
            # AGUARDADOS: nenhuma leitura pode sobreviver ao grupo e tropeçar na página que o `desligar()` fecha
            for t in (trabalho, batida, espera):
                t.cancel()
            await asyncio.gather(trabalho, batida, espera, return_exceptions=True)
            # encerrando, a sessão sai com LOGOUT (a "morte" pode ser efeito do próprio desligar): descartar sem logout
            # deixaria a sessão viva no Agger e o próximo login veria o aviso de sessão ativa
            await self._soltar_conta(conta, perdeu=perdeu.is_set(),
                                     descartar=g.sessao_morta and not self._encerrando)
            await self._fechar_pedido_se_terminou(g.pedido_id, g.solicitante_company_id)

    async def _bater(self, g: Grupo, conta: Dict[str, Any], perdeu: asyncio.Event) -> None:
        ultimo_ok = self.agora()
        while True:
            await asyncio.sleep(self.batida_s)
            if self._encerrando:
                return   # quem encerra não perde a posse por engano: a batida para e a lease vence sozinha
            try:
                agora = self.agora()
                if not await self._db(lambda: robos.renovar(self.supa, conta, self.dono, agora)):
                    perdeu.set()
                    return
                ids = sorted(g.ativos)
                if ids:
                    r = await self._db(lambda: self.supa.table("multicalculo_calculos")
                                       .update({"batida_em": _iso(agora)})
                                       .in_("id", ids).eq("company_id", g.company_id).eq("dono", self.dono)
                                       .in_("status", ["disparando", "calculando"]).execute())
                    voltaram = {x["id"] for x in (r.data or [])}
                    # Só conta como perda o que AINDA está ativo depois da batida: um cálculo que fechou
                    # enquanto ela ia ao banco saiu de `ativos` ANTES de gravar o estado final.
                    if g.ativos - voltaram:
                        perdeu.set()
                        return
                ultimo_ok = agora
            except Exception as exc:  # noqa: BLE001
                if self._encerrando:
                    return
                logger.warning("[MC] batida falhou (%s)", type(exc).__name__)
                if (self.agora() - ultimo_ok).total_seconds() > self.lease_s - self.batida_s:
                    perdeu.set()
                    return

    async def _trabalho(self, g: Grupo, conta: Dict[str, Any], perdeu: asyncio.Event) -> None:
        linha = await self._pedido(g.pedido_id, g.solicitante_company_id, "id, pedido_cifrado")
        pedido: Optional[Dict[str, Any]] = None
        if not g.retomada:
            try:
                pedido = json.loads(self.decifrar((linha or {}).get("pedido_cifrado") or ""))
                if not isinstance(pedido, dict):
                    raise ValueError("pedido não é objeto")
            except Exception:  # noqa: BLE001 — nunca o conteúdo nem a mensagem da exceção
                for c in list(g.calculos):
                    await self._encerrar(g, c, "falhou", "não consegui abrir o pedido cifrado")
                return

        sessao = await self._abrir_sessao(g, conta)
        if sessao is None:
            return

        if g.retomada:
            disparos = {c["id"]: self.robo.Disparo(negocio_ref=c["negocio_ref"], versao=int(c["versao"]),
                                                    t0=(_ts(c.get("disparado_em")) or self.agora()).timestamp())
                        for c in g.calculos}
        else:
            disparos = await self._disparar_todos(g, conta, sessao, pedido or {}, perdeu)
        pedido = None   # o pedido decifrado não sobrevive ao disparo
        if not disparos or perdeu.is_set():
            return
        por_id = {c["id"]: c for c in g.calculos}
        await asyncio.gather(*[self._acompanhar(g, por_id[cid], sessao, d, perdeu)
                               for cid, d in disparos.items()])

    # ======================================================================
    # A sessão e os estados da conta
    # ======================================================================
    async def _abrir_sessao(self, g: Grupo, conta: Dict[str, Any]):
        SessaoOcupada = self.sessao_mod.SessaoOcupada
        CredencialRecusada = self.sessao_mod.CredencialRecusada
        try:
            sessoes = await self._sessoes_prontas()
            negocios = await self._negocios_da_corretora(g.company_id)
            senha = self.decifrar(conta.get("secret_encrypted") or "")
        except Exception as exc:  # noqa: BLE001
            logger.error("[MC] não consegui preparar a sessão do robô %s (%s)", conta["id"], type(exc).__name__)
            await self._devolver_a_fila(g, g.calculos, com_espera=True)
            return None
        try:
            sessao = await sessoes.obter(robos.conta_publica(conta), senha=senha, negocios_do_robo=negocios)
        except SessaoOcupada:
            await self._sessao_ocupada(g, conta, g.calculos)
            return None
        except CredencialRecusada:
            await self._credencial_recusada(g, conta, g.calculos)
            return None
        except Exception as exc:  # noqa: BLE001 — nada saiu: o login falhou antes de qualquer POST
            indefinida = getattr(self.sessao_mod, "SessaoIndefinida", None)
            if (indefinida is not None and isinstance(exc, indefinida)
                    and conta.get("robo_estado") == robos.TESTE):
                # 🔴 conserto 129-B (red P7): o login da PESSOA sem desfecho — o robô não tenta de novo de 1 em 1
                # minuto no login de alguém: pausa a conta e para (como a SessaoOcupada numa conta `teste`)
                await self._marcar(conta, robos.PAUSADO)
                logger.warning("[MC] conta de teste %s: login sem desfecho — pausada", conta["id"])
                for c in list(g.calculos):
                    await self._encerrar(g, c, "falhou", MOTIVO_TESTE_INDEFINIDO)
                return None
            logger.error("[MC] a sessão do robô %s não abriu (%s)", conta["id"], type(exc).__name__)
            await self._devolver_a_fila(g, g.calculos, com_espera=True)
            return None
        finally:
            senha = None  # noqa: F841 — a senha não sobrevive ao `obter`
        self._contas_com_sessao[conta["id"]] = conta
        return sessao

    async def _sessao_ocupada(self, g: Grupo, conta: Dict[str, Any], calcs: Iterable[Dict[str, Any]]) -> None:
        """O aviso de sessão ativa apareceu e foi CANCELADO: uma pessoa está no login.
        `teste` (login de PESSOA) → `pausado` e PARAR (PASSAGEM §8); `ativo` → `ocupada` 💭 30 min e o
        que não saiu volta à fila."""
        if self._encerrando:
            return   # conserto 129-B: o motor que encerra não muda o estado da conta nem dos cálculos
        calcs = list(calcs)
        if conta.get("robo_estado") == robos.TESTE:
            await self._marcar(conta, robos.PAUSADO)
            logger.warning("[MC] conta de teste %s em uso por uma pessoa — pausada", conta["id"])
            for c in calcs:
                await self._encerrar(g, c, "falhou",
                                     "a conta de teste estava em uso por uma pessoa: o robô cancelou e parou")
            return
        await self._marcar(conta, robos.OCUPADA, ocupada_min=OCUPADA_MIN)
        logger.warning("[MC] robô %s ocupado por uma pessoa — afastado por %s min", conta["id"], OCUPADA_MIN)
        await self._devolver_a_fila(g, calcs)

    async def _marcar(self, conta: Dict[str, Any], estado: str, **kw) -> bool:
        """`robos.marcar_estado` (CAS a partir do estado LIDO): a pausa do Founder vence o motor (red B1)."""
        if self._encerrando:
            logger.warning("[MC] encerrando: o robô %s não muda para %s", conta.get("id"), estado)
            return False
        try:
            return bool(await self._db(lambda: robos.marcar_estado(self.supa, conta, estado, agora=self.agora(),
                                                                  **kw)))
        except ValueError as exc:
            logger.warning("[MC] robô %s: %s", conta.get("id"), exc)
            return False

    async def _credencial_recusada(self, g: Grupo, conta: Dict[str, Any],
                                   calcs: Iterable[Dict[str, Any]]) -> None:
        """Senha recusada: UMA tentativa → `bloqueado` + evento `robo_bloqueado`. Nunca retenta (é como
        a conta da corretora é bloqueada na seguradora). O que não saiu volta à fila: outro robô da
        mesma corretora pode servir; sem outro, o cálculo expira no prazo dele."""
        if self._encerrando:
            return   # conserto 129-B: a recusa vista enquanto o motor morre não bloqueia a conta
        calcs = list(calcs)
        await self._marcar(conta, robos.BLOQUEADO)
        logger.error("[MC] robô %s com login/senha recusados — bloqueado", conta["id"])
        for c in calcs:
            await self._gravar_linha_de_evento(g, c, {
                "tipo": "robo_bloqueado", "chave": f"robo_bloqueado|{conta['id']}", "familia": None,
            })
        await self._devolver_a_fila(g, calcs)

    async def _fechar_sessao(self, conta_id: str) -> None:
        self._contas_com_sessao.pop(conta_id, None)
        if self._sessoes is None:
            return
        try:
            await self._sessoes.fechar(conta_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MC] fechar a sessão %s falhou (%s)", conta_id, type(exc).__name__)

    async def _descartar_sessao(self, conta_id: str) -> None:
        """A sessão morreu: fecha SEM logout (`Sessoes.descartar`); quem não tem `descartar` fecha normal."""
        self._contas_com_sessao.pop(conta_id, None)
        if self._sessoes is None:
            return
        try:
            descartar = getattr(self._sessoes, "descartar", None)
            await (descartar(conta_id) if descartar is not None else self._sessoes.fechar(conta_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MC] descartar a sessão %s falhou (%s)", conta_id, type(exc).__name__)

    # ======================================================================
    # Disparar · checkpoint
    # ======================================================================
    async def _negocios_da_corretora(self, corretora: str) -> set:
        """Os negócios que o robô PODE recalcular: os `negocio_ref` desta corretora no banco."""
        r = await self._db(lambda: self.supa.table("multicalculo_calculos").select("negocio_ref")
                           .eq("company_id", corretora).not_.is_("negocio_ref", "null").execute())
        return {x["negocio_ref"] for x in (r.data or []) if x.get("negocio_ref")}

    async def _negocio_do_pedido(self, g: Grupo) -> Optional[str]:
        """A econômica entra no negócio da padrão (D-129B-03) — mesmo quando a padrão saiu noutro grupo."""
        r = await self._db(lambda: self.supa.table("multicalculo_calculos").select("negocio_ref, opcao")
                           .eq("pedido_id", g.pedido_id).eq("company_id", g.company_id)
                           .not_.is_("negocio_ref", "null").order("criado_em").execute())
        refs = [x["negocio_ref"] for x in (r.data or []) if x.get("opcao") != "ajuste"]
        return refs[0] if refs else None

    async def _disparar_todos(self, g: Grupo, conta: Dict[str, Any], sessao, pedido: Dict[str, Any],
                              perdeu: asyncio.Event) -> Dict[str, Any]:
        robo = self.robo
        SessaoOcupada = self.sessao_mod.SessaoOcupada
        CredencialRecusada = self.sessao_mod.CredencialRecusada
        ordem = sorted(g.calculos, key=lambda c: _ORDEM_DA_OPCAO.get(c.get("opcao"), 9))
        negocio = await self._negocio_do_pedido(g)
        disparos: Dict[str, Any] = {}
        for i, c in enumerate(ordem):
            if perdeu.is_set():
                break
            if self._freio():
                logger.warning("[MC] freio puxado no meio do grupo — o que não saiu volta à fila")
                await self._devolver_a_fila(g, ordem[i:])
                break
            if not await self._canal_autorizado(g.solicitante_company_id, g.company_id):
                # 🔴 conserto 129-B (red B2): reconferido IMEDIATAMENTE antes de cada POST
                for resto in ordem[i:]:
                    await self._encerrar(g, resto, "cancelado", MOTIVO_SAIU_DO_CANAL)
                break
            try:
                if c.get("opcao") == "ajuste":
                    d = await self._recalcular(g, c, sessao)
                    if d is None:
                        continue
                else:
                    if negocio is not None and not await self._ninguem_mexeu(g, c, sessao, negocio):
                        # 🔴 conserto 129-B (red B4/juiz P2): TODO disparo num negócio que já existe confere a
                        # D-MC-47 — a econômica adiada, a retomada de um grupo partido
                        continue
                    d = await robo.disparar(sessao, pedido, c.get("coberturas") or {}, negocio_ref=negocio)
            except robo.DisparoRecusado as exc:
                if getattr(exc, "sessao_morta", False):
                    # nada saiu (401/403 antes do cálculo): a sessão é DESCARTADA e o que não saiu volta à fila
                    g.sessao_morta = True
                    logger.error("[MC] sessão do robô %s morta no disparo — descartada", conta["id"])
                    await self._devolver_a_fila(g, ordem[i:], com_espera=True)
                    break
                await self._encerrar(g, c, "falhou", _motivo_recusado(exc))
                continue
            except SessaoOcupada:
                await self._sessao_ocupada(g, conta, ordem[i:])
                break
            except CredencialRecusada:
                await self._credencial_recusada(g, conta, ordem[i:])
                break
            except Exception as exc:  # noqa: BLE001 — DisparoIncerto e o que não se sabe: NUNCA repetir
                logger.error("[MC] disparo incerto no cálculo %s (%s)", c["id"], type(exc).__name__)
                await self._encerrar(g, c, "incerto", MOTIVO_INCERTO)
                continue
            if not await self._checkpoint(g, c, d):
                perdeu.set()
                break
            disparos[c["id"]] = d
            if c.get("opcao") != "ajuste" and negocio is None:
                negocio = d.negocio_ref
        return disparos

    async def _checkpoint(self, g: Grupo, c: Dict[str, Any], d) -> bool:
        """🔴 O ELO da retomada: negócio + versão no banco ANTES do 1º GET. Morrer depois daqui = outro
        motor só LÊ; morrer antes = `incerto`. Nunca um 2º POST."""
        r = await self._db(lambda: self.supa.table("multicalculo_calculos").update({
            "status": "calculando", "negocio_ref": d.negocio_ref, "versao": int(d.versao),
            "batida_em": _iso(self.agora()),
        }).eq("id", c["id"]).eq("company_id", g.company_id).eq("dono", self.dono)
            .eq("status", "disparando").execute())
        if r.data:
            c.update({"status": "calculando", "negocio_ref": d.negocio_ref, "versao": int(d.versao)})
            return True
        logger.error("[MC] checkpoint do cálculo %s não gravou — perdi a posse", c["id"])
        return False

    async def _recalcular(self, g: Grupo, c: Dict[str, Any], sessao):
        """O ajuste: nova versão do MESMO negócio a partir da versão CERTA (a da origem), depois de
        conferir que nenhuma pessoa mexeu nele nas últimas 24 h (D-MC-47)."""
        r = await self._db(lambda: self.supa.table("multicalculo_calculos")
                           .select("id, negocio_ref, versao")
                           .eq("id", c.get("origem_calculo_id") or "").eq("company_id", g.company_id)
                           .limit(1).execute()) if c.get("origem_calculo_id") else None
        origem = ((r.data if r else None) or [None])[0]
        if not origem or not origem.get("negocio_ref") or origem.get("versao") is None:
            await self._encerrar(g, c, "falhou", "o cálculo de origem ainda não tem negócio no portal")
            return None
        ajuste = _ajuste_do_banco(c.get("ajuste"))
        if ajuste is None:
            await self._encerrar(g, c, "falhou", "o ajuste deste recálculo é inválido")
            return None
        ref = origem["negocio_ref"]
        if not await self._ninguem_mexeu(g, c, sessao, ref):
            return None
        return await self.robo.recalcular(sessao, ref, versao_base=int(origem["versao"]), ajuste=ajuste)

    async def _ninguem_mexeu(self, g: Grupo, c: Dict[str, Any], sessao, ref: str) -> bool:
        """D-MC-47: nenhuma pessoa mexeu no negócio `ref` nas últimas 24 h? Não → o cálculo `falhou` com o motivo e
        NADA sai. Sem conseguir conferir → também não sai (na dúvida, não se escreve por cima da pessoa)."""
        rv = await self._db(lambda: self.supa.table("multicalculo_calculos").select("versao")
                            .eq("company_id", g.company_id).eq("negocio_ref", ref).execute())
        versoes = {int(x["versao"]) for x in (rv.data or []) if x.get("versao") is not None}
        try:
            mexeu = await self.robo.pessoa_mexeu_recentemente(sessao, ref, horas=24, versoes_do_robo=versoes)
        except Exception as exc:  # noqa: BLE001 — sem saber, não recalcula
            logger.error("[MC] não consegui conferir as versões do negócio (%s)", type(exc).__name__)
            await self._encerrar(g, c, "falhou", "não consegui conferir se uma pessoa mexeu no negócio")
            return False
        if mexeu:
            await self._encerrar(g, c, "falhou", MOTIVO_PESSOA_MEXEU)
            return False
        return True

    # ======================================================================
    # Acompanhar · gravar · PDF · fechar
    # ======================================================================
    async def _acompanhar(self, g: Grupo, c: Dict[str, Any], sessao, d, perdeu: asyncio.Event) -> None:
        anterior = await self.rodada_gravada(g, c) if g.retomada else None
        primeira = {"feita": c.get("primeira_oferta_em") is not None}

        async def ao_evento(e: Evento) -> None:
            if perdeu.is_set():
                raise _PossePerdida()
            await self._gravar_evento(g, c, e, primeira)

        async def ao_quadro() -> None:
            if perdeu.is_set():
                raise _PossePerdida()
            await self._db(lambda: self.supa.table("multicalculo_calculos")
                           .update({"quadro_pronto_em": _iso(self.agora())})
                           .eq("id", c["id"]).eq("company_id", g.company_id).eq("dono", self.dono)
                           .is_("quadro_pronto_em", "null").execute())

        leitura_impossivel = getattr(self.robo, "LeituraImpossivel", None) or _NuncaLevantada
        try:
            rodada = await self.robo.acompanhar(sessao, d, ao_evento=ao_evento, anterior=anterior,
                                                quadro_s=g.quadro_s, ao_quadro=ao_quadro)
        except _PossePerdida:
            return
        except leitura_impossivel as exc:
            # 🔴 conserto 129-B (juiz B1): "não consegui ler" nunca vira `fechado` com 0 ofertas
            if self._encerrando:
                # 🔴 conserto 129-B (canário 05/10): a leitura caiu PORQUE o motor está encerrando — o negócio existe;
                # fica `calculando` e outro motor só LÊ (D-129B-06). Nem `falhou`, nem `fechado` com o que leu.
                logger.warning("[MC] encerrando: o cálculo %s fica para a retomada", c["id"])
                return
            if getattr(exc, "sessao_morta", False):
                g.sessao_morta = True
            if perdeu.is_set():
                return
            leu = bool(getattr(exc, "leu", False)) or bool(anterior is not None and anterior.respostas)
            quadro = bool(getattr(exc, "quadro_saiu", False)) or bool(c.get("quadro_pronto_em"))
            logger.error("[MC] não consegui ler o cálculo %s (leu=%s, quadro=%s, sessão morta=%s)", c["id"], leu,
                         quadro, g.sessao_morta)
            if leu and quadro:
                if not g.sessao_morta:
                    await self._copiar_pdfs(g, c, sessao, d)
                await self._encerrar(g, c, "fechado", MOTIVO_LEU_PARTE)
            elif getattr(exc, "pagina_fechada", False):
                # 🔴 conserto 129-B: a PÁGINA fechou sem o motor encerrar (o navegador caiu sozinho; um SIGTERM que
                # chegou ao Chromium antes do encerrar). Não é o Agger dizendo "não": o negócio existe e um login novo
                # o lê. Fica `calculando` → a retomada (limitada a MAX_RETOMADAS, depois `falhou` com o motivo).
                # 401/403 (o Agger recusou) segue `falhou` (juiz B1). 💭 nota 80 × 55 de `falhou` sem leitura alguma.
                logger.warning("[MC] a página do cálculo %s fechou — fica para a retomada", c["id"])
            else:
                await self._encerrar(g, c, "falhou", MOTIVO_NAO_LEU)
            return
        except Exception as exc:  # noqa: BLE001 — fica `calculando`: a retomada relê, nunca re-POST
            logger.error("[MC] acompanhar o cálculo %s caiu (%s) — fica para a retomada", c["id"],
                         type(exc).__name__)
            return
        if perdeu.is_set():
            return
        if rodada is None:
            # o robô devolveu NADA: não se fecha o que não foi lido
            await self._encerrar(g, c, "falhou", MOTIVO_NAO_LEU)
            return
        await self._copiar_pdfs(g, c, sessao, d)
        await self._encerrar(g, c, "fechado", None)

    async def _gravar_evento(self, g: Grupo, c: Dict[str, Any], e: Evento, primeira: dict) -> None:
        oferta_id = None
        if e.oferta is not None:
            linha = self._linha_da_oferta(g, c, e.oferta, nova=(e.tipo == NOVA_OFERTA))
            r = await self._db(lambda: self.supa.table("multicalculo_ofertas").upsert(
                linha, on_conflict="calculo_id,seguradora_codigo,pacote,tipo_de_pacote").execute())
            oferta_id = ((r.data or [{}])[0]).get("id")
            if not primeira["feita"]:
                primeira["feita"] = True
                await self._db(lambda: self.supa.table("multicalculo_calculos")
                               .update({"primeira_oferta_em": _iso(self.agora())})
                               .eq("id", c["id"]).eq("company_id", g.company_id)
                               .is_("primeira_oferta_em", "null").execute())
        o = e.oferta
        await self._gravar_linha_de_evento(g, c, {
            "tipo": e.tipo, "chave": chave_do_evento(e),
            # seguradora/pacote EXATOS como o leitor entregou (ele já tirou URL e chave): são a
            # identidade da oferta, e o `anterior` da retomada é montado deles.
            "seguradora": e.seguradora,
            "seguradora_codigo": e.seguradora_codigo,
            "pacote": o.pacote if o is not None else None,
            "tipo_de_pacote": o.tipo_de_pacote if o is not None else None,
            "familia": e.familia, "oferta_id": oferta_id, "t_s": e.t_s,
        })

    async def _gravar_linha_de_evento(self, g: Grupo, c: Dict[str, Any], campos: Dict[str, Any]) -> None:
        linha = {"calculo_id": c["id"], "pedido_id": g.pedido_id, "company_id": g.company_id,
                 "solicitante_company_id": g.solicitante_company_id, **campos}
        await self._db(lambda: self.supa.table("multicalculo_eventos").upsert(
            linha, on_conflict="calculo_id,chave", ignore_duplicates=True).execute())

    def _linha_da_oferta(self, g: Grupo, c: Dict[str, Any], o: Oferta, *, nova: bool) -> Dict[str, Any]:
        """A Oferta do leitor como linha. A 2ª rede depois da lista branca do robô: o texto LIVRE (alerta,
        franquia, cobertura) passa pelo redator (URL/chave/PII somem); só as chaves que a `Oferta` conhece
        entram. Seguradora e pacote vão exatos: o leitor já os saneou e eles são a identidade da oferta."""
        linha: Dict[str, Any] = {
            "calculo_id": c["id"], "pedido_id": g.pedido_id, "company_id": g.company_id,
            "solicitante_company_id": g.solicitante_company_id,
            "seguradora": o.seguradora, "seguradora_codigo": o.seguradora_codigo,
            "pacote": o.pacote, "tipo_de_pacote": o.tipo_de_pacote,   # a identidade (unique), exata
            "premio_total": float(o.premio_total), "premio_mensal": o.premio_mensal,
            "franquia_valor": o.franquia_valor,
            "franquia_tipo": erro_curto(o.franquia_tipo, 120) if o.franquia_tipo else None,
            "coberturas": {str(k): (erro_curto(v, 200) if isinstance(v, str) else v) for k, v in o.coberturas},
            "parcelamentos": [{"parcelas": p.parcelas, "tipo_pagamento": p.tipo_pagamento,
                               "primeira_parcela": p.primeira_parcela, "demais_parcelas": p.demais_parcelas}
                              for p in o.parcelamentos],
            "tem_pdf": bool(o.tem_pdf), "alertas": [erro_curto(a, 300) for a in o.alertas],
            "comissao_percentual": o.comissao_percentual,   # INTERNO: a porta corta para quem não é a dona
            "atualizada_em": _iso(self.agora()),
        }
        if nova:
            linha["recebida_em"] = _iso(self.agora())
        return linha

    async def _copiar_pdfs(self, g: Grupo, c: Dict[str, Any], sessao, d) -> None:
        """Os PDFs da seguradora para o NOSSO armazenamento (o bucket privado que o worker já usa).
        🔴 Falha de PDF nunca falha o cálculo: a oferta vale sem o PDF."""
        try:
            pdfs = await self.robo.copiar_pdfs(sessao, d) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MC] copiar os PDFs do cálculo %s falhou (%s)", c["id"], type(exc).__name__)
            return
        for chave, blob in pdfs.items():
            try:
                cod, pacote, tipo = chave
                q = (self.supa.table("multicalculo_ofertas").select("id")
                     .eq("calculo_id", c["id"]).eq("company_id", g.company_id)
                     .eq("seguradora_codigo", cod).eq("pacote", pacote))
                q = q.is_("tipo_de_pacote", "null") if tipo is None else q.eq("tipo_de_pacote", tipo)
                r = await self._db(lambda q=q: q.limit(1).execute())
                oferta = (r.data or [None])[0]
                if not oferta or not blob:
                    continue
                caminho = f"multicalculo/{g.company_id}/{c['id']}/{oferta['id']}.pdf"
                salvo = await self._upload(self.supa, caminho, blob)
                if salvo:
                    await self._db(lambda o=oferta, s=salvo: self.supa.table("multicalculo_ofertas")
                                   .update({"pdf_path": s, "tem_pdf": True})
                                   .eq("id", o["id"]).eq("company_id", g.company_id).execute())
            except Exception as exc:  # noqa: BLE001
                logger.warning("[MC] um PDF do cálculo %s não foi copiado (%s)", c["id"], type(exc).__name__)

    async def _encerrar(self, g: Grupo, c: Dict[str, Any], status: str, erro: Optional[str]) -> None:
        """Estado final de um cálculo deste grupo. Sai de `ativos` ANTES de gravar (a batida não pode
        confundir "fechou" com "perdi").
        🔴 Conserto 129-B: com o motor ENCERRANDO, nada é gravado — `calculando` fica para a retomada (só leitura) e
        `disparando` vira `incerto` por ela (nunca um 2º POST). A guarda é AQUI, na escrita, e não em cada `except`:
        um caminho de erro novo não consegue esquecê-la."""
        if self._encerrando:
            logger.warning("[MC] encerrando: o cálculo %s não é gravado como %s", c["id"], status)
            return
        g.ativos.discard(c["id"])
        patch: Dict[str, Any] = {"status": status, "fechado_em": _iso(self.agora())}
        if erro is not None:
            patch["erro"] = erro_curto(erro)
        await self._db(lambda: self.supa.table("multicalculo_calculos").update(patch)
                       .eq("id", c["id"]).eq("company_id", g.company_id).eq("dono", self.dono)
                       .in_("status", ["disparando", "calculando"]).execute())

    async def _devolver_a_fila(self, g: Grupo, calcs: Iterable[Dict[str, Any]], *,
                               com_espera: bool = False) -> None:
        """Só o que NADA tocou no portal volta (status `disparando`, antes de qualquer POST). Os que
        estão `calculando` ficam: o negócio existe e a retomada lê. `com_espera` (falha de login sem
        causa conhecida): `disponivel_em` = agora + 60 s × tentativas, teto 15 min.
        🔴 Conserto 129-B: encerrando, nada volta — o erro pode ser a própria morte no MEIO de um POST; `disparando`
        vencido vira `incerto` pela retomada (o lado seguro: nunca um 2º POST)."""
        if self._encerrando:
            return
        for c in list(calcs):
            if g.retomada or c.get("status") == "calculando":
                continue
            g.ativos.discard(c["id"])
            patch: Dict[str, Any] = {"status": "na_fila", "dono": None, "batida_em": None, "account_id": None,
                                     "disparado_em": None}
            if com_espera:
                atraso = min(ATRASO_POR_TENTATIVA_S * max(1, int(c.get("tentativas") or 1)), ATRASO_MAX_S)
                patch["disponivel_em"] = _iso(self.agora() + timedelta(seconds=atraso))
            await self._db(lambda c=c, patch=patch: self.supa.table("multicalculo_calculos").update(patch).eq("id", c["id"]).eq("company_id", g.company_id).eq("dono", self.dono)
                .eq("status", "disparando").execute())

    async def _fechar_pedido_se_terminou(self, pedido_id: str, solicitante: str) -> None:
        try:
            r = await self._db(lambda: self.supa.table("multicalculo_calculos").select("status")
                               .eq("pedido_id", pedido_id).eq("solicitante_company_id", solicitante).execute())
            estados = [x.get("status") for x in (r.data or [])]
            if estados and all(s in ESTADOS_TERMINAIS for s in estados):
                await self._db(lambda: self.supa.table("multicalculo_pedidos")
                               .update({"status": "fechado", "atualizado_em": _iso(self.agora())})
                               .eq("id", pedido_id).eq("company_id", solicitante).eq("status", "aberto").execute())
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MC] fechar o pedido %s falhou (%s)", pedido_id, type(exc).__name__)

    # ======================================================================
    # A rodada anterior, montada do que está GRAVADO (a retomada)
    # ======================================================================
    async def rodada_gravada(self, g: Grupo, c: Dict[str, Any]) -> RodadaDoCalculo:
        """O `anterior` da retomada: o que este cálculo JÁ NARROU (os eventos gravados).

        Com ele, o `eventos_entre` do robô só narra o que é NOVO — sem ele, todo evento sairia de novo.
        🔴 Montado dos EVENTOS, não das ofertas: oferta e evento são duas escritas, e 📊 o G6 pegou o
        processo morrendo ENTRE as duas — a oferta gravada, o evento não. Montado das ofertas, o
        `anterior` escondia esse evento para sempre (29 de 30). Montado dos eventos, ele é narrado de
        novo e a oferta é regravada pelo upsert (idempotente). O prêmio vem da chave (centavos)."""
        r = await self._db(lambda: self.supa.table("multicalculo_eventos")
                           .select("tipo, seguradora, seguradora_codigo, pacote, tipo_de_pacote, familia, chave")
                           .eq("calculo_id", c["id"]).eq("company_id", g.company_id).order("id").execute())
        por_seg: Dict[Any, Dict[str, Any]] = {}
        fechado = False
        for ev in (r.data or []):
            tipo = ev.get("tipo")
            if tipo == CONJUNTO_FECHADO:
                fechado = True
                continue
            if tipo not in (NOVA_OFERTA, OFERTA_ATUALIZADA, SEGURADORA_RECUSOU):
                continue
            k = ev.get("seguradora_codigo") if ev.get("seguradora_codigo") is not None else ev.get("seguradora")
            s = por_seg.setdefault(k, {"seguradora": ev.get("seguradora") or "", "codigo": ev.get("seguradora_codigo"),
                                       "familia": None, "ofertas": {}})
            if tipo == SEGURADORA_RECUSOU:
                s["familia"] = ev.get("familia")   # a ÚLTIMA família narrada
                continue
            try:
                premio = int(str(ev.get("chave") or "").rsplit("|", 1)[1]) / 100.0
            except (IndexError, ValueError):
                continue
            s["ofertas"][(ev.get("pacote") or "", ev.get("tipo_de_pacote"))] = Oferta(
                seguradora=ev.get("seguradora") or "", seguradora_codigo=ev.get("seguradora_codigo"),
                pacote=ev.get("pacote") or "", tipo_de_pacote=ev.get("tipo_de_pacote"),
                premio_total=premio, premio_mensal=None, franquia_valor=None, franquia_tipo=None)
        respostas = tuple(RespostaDaSeguradora(
            seguradora=s["seguradora"], seguradora_codigo=s["codigo"],
            familia=OFERTA if s["ofertas"] else (s["familia"] or OFERTA), ofertas=tuple(s["ofertas"].values()))
            for s in por_seg.values())
        return RodadaDoCalculo(t_s=None, respostas=respostas, fechado=fechado)


def _ajuste_do_banco(valor: Any) -> Optional[Ajuste]:
    """`calculos.ajuste` (jsonb) → `contrato.Ajuste`. Um ajuste por recálculo (§6.4)."""
    if isinstance(valor, list) and len(valor) == 1:
        valor = valor[0]
    if not isinstance(valor, dict):
        return None
    try:
        return Ajuste(tipo=str(valor.get("tipo")), valor=valor.get("valor"),
                      seguradora=valor.get("seguradora"))
    except (TypeError, ValueError):
        return None


# ==========================================================================
# O laço
# ==========================================================================
# O motor DESTE processo (o laço cria um só). O desligar do `portal_worker.main` o encontra aqui.
_MOTOR_DO_PROCESSO: Optional[Motor] = None


def registrar_motor_do_processo(motor: Optional[Motor]) -> None:
    global _MOTOR_DO_PROCESSO
    _MOTOR_DO_PROCESSO = motor


async def desligar_o_motor_do_processo() -> bool:
    """Chamado no SHUTDOWN do serviço: encerra o motor (grupos parados, logout de todas as sessões, leases
    devolvidas). Nunca levanta. Devolve se havia motor para desligar."""
    motor = _MOTOR_DO_PROCESSO
    if motor is None:
        return False
    try:
        await motor.encerrar()
    except Exception as exc:  # noqa: BLE001 — o shutdown não pode travar no motor (o cancelamento passa)
        logger.warning("[MC] desligar o motor no shutdown falhou (%s)", type(exc).__name__)
    finally:
        registrar_motor_do_processo(None)
    return True

async def laco_do_motor(*, supa_fabrica: Optional[Callable[[], Any]] = None,
                        fabrica_de_sessoes: Optional[Callable[[], Awaitable[Any]]] = None,
                        intervalo_s: float = VOLTA_S) -> None:
    """A task do motor no startup do portal-worker. Nunca derruba o processo.

    D-129B-09: `MULTICALCULO_MOTOR_LIGADO` (padrão falso) e `PORTAL_REAL_ENABLED` no boot — desligado,
    a task termina e não abre navegador nem banco. Ligado, as duas e o `GLOBAL_KILL_SWITCH` são
    conferidos A CADA VOLTA: frear não exige reiniciar o serviço."""
    if not motor_ligado():
        logger.info("[MC] motor do multicálculo em standby (MULTICALCULO_MOTOR_LIGADO=false)")
        return
    if not portal_real_enabled():
        logger.info("[MC] motor do multicálculo em standby (PORTAL_REAL_ENABLED=false)")
        return
    logger.info("[MC] motor do multicálculo iniciado (volta %ss)", intervalo_s)
    motor: Optional[Motor] = None
    while True:
        try:
            if kill_switch_ativo() or not motor_ligado() or not portal_real_enabled():
                logger.warning("[MC] freio/desligado — nenhum cálculo novo sai")
                if motor is not None and not motor._tarefas:
                    await motor.desligar()
            else:
                if motor is None:
                    from ..worker import _supabase

                    supa = await asyncio.to_thread(supa_fabrica or _supabase)
                    motor = Motor(supa, fabrica_de_sessoes=fabrica_de_sessoes)
                    registrar_motor_do_processo(motor)
                n = await motor.uma_volta(esperar=False)
                if n:
                    logger.info("[MC] %s grupo(s) começaram", n)
        except Exception as exc:  # noqa: BLE001
            logger.error("[MC] volta do motor falhou (%s)", type(exc).__name__)
        await asyncio.sleep(intervalo_s)


__all__: tuple = (
    "BATIDA_S", "LEASE_VENCE_S", "VOLTA_S", "OCUPADA_MIN", "MAX_RETOMADAS", "Motor", "Grupo",
    "laco_do_motor", "motor_ligado", "canario_ligado", "teto_corretora_hora", "teto_geral_hora",
    "chave_do_evento", "erro_curto", "registrar_motor_do_processo", "desligar_o_motor_do_processo",
)
