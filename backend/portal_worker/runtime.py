# -*- coding: utf-8 -*-
"""`PortalRuntimeContext` — a infraestrutura compartilhada do job. SPEC-073 §6.1.

Como ele entra sem quebrar nada
===============================
O worker injeta uma chave reservada em `params`:

    params["_runtime"] = PortalRuntimeContext(...)

Journey antiga nunca lê `_runtime` e continua funcionando exatamente como
funcionava. Journey nova (ou modernizada) faz:

    runtime = params.get("_runtime")
    if runtime:
        await runtime.guard.before(action="create_attendance",
                                   action_class=MATERIAL_SIDE_EFFECT)

🔴 É **aditivo por decisão**, não por preguiça. A alternativa — mudar a
assinatura `journey_fn(page, params, evidence)` — obrigaria a tocar em Allianz,
HDI, Tokio, Yelum, MAPFRE e Zurich de uma vez, que é exatamente a migração em
massa que a SPEC-073 R2 proíbe. Seis journeys que cobram boleto hoje não vão
parar para adotar um objeto novo.

O que o runtime NÃO é
=====================
    ✗ não guarda senha
    ✗ não guarda Authorization serializável
    ✗ não implementa regra de negócio de seguradora
    ✗ não substitui `params`
    ✗ não é salvo no banco (só o que ele PRODUZ vai para `evidence`)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional

from portal_worker import guardrails as G
from portal_worker import perception as P
from portal_worker import redaction as R
from portal_worker.profiler import PortalProfiler

logger = logging.getLogger(__name__)


def _flag(nome: str, padrao: str = "") -> bool:
    return str(os.getenv(nome, padrao)).strip().lower() in ("1", "true", "yes", "on")


def discovery_mode() -> bool:
    """`PORTAL_DISCOVERY_MODE` — nasce `false` (SPEC-073 C1)."""
    return _flag("PORTAL_DISCOVERY_MODE")


def profiler_enabled() -> bool:
    """`PORTAL_PROFILER_ENABLED` — nasce `true`: é passivo e é o que ensina."""
    return _flag("PORTAL_PROFILER_ENABLED", "true")


def raw_trace_enabled() -> bool:
    """`PORTAL_DISCOVERY_RAW_TRACE` — nasce `false` e assim deve ficar em produção.

    O ZIP de trace do Playwright pode conter PII bruta. Nunca vai para o Git,
    nunca é exigido para produção.
    """
    return _flag("PORTAL_DISCOVERY_RAW_TRACE")


def kill_switch_ativo() -> bool:
    """O freio de emergência que **realmente** alcança este processo.

    📊 Medido em 16/08/2026: `GLOBAL_KILL_SWITCH` existia, estava `true` no
    ambiente, e era lido **apenas** em `lib/security/production-gates.ts` — um
    arquivo Next.js que o portal-worker Python nunca importa. `grep -rn
    "GLOBAL_KILL_SWITCH" backend/` devolvia vazio.

    Ou seja: havia um freio no painel que não estava ligado na roda. Quem
    apertasse em uma emergência veria a tela dizer "parado" enquanto o worker
    continuava entrando em portal.

    Aqui ele passa a valer de verdade. Semântica preservada do lado TS: a
    variável é considerada ATIVA por padrão e só `"false"` a desliga — então um
    ambiente que perdeu a variável falha fechado, não aberto.
    """
    bruto = os.getenv("GLOBAL_KILL_SWITCH")
    if bruto is None:
        return False  # variável ausente = comportamento historico do worker
    return str(bruto).strip().lower() != "false"


@dataclass
class PortalRuntimeContext:
    """Tudo que uma journey moderna precisa, e nada que ela não deva ter."""

    job_id: str = ""
    company_id: str = ""
    portal_key: str = ""
    journey: str = ""
    account_id: Optional[str] = None
    account_label: str = ""

    discovery_mode: bool = False
    vision_enabled: bool = False
    profiler_enabled: bool = True

    evidence: Dict[str, Any] = field(default_factory=dict)
    profiler: Optional[PortalProfiler] = None
    guard: Optional[G.PortalActionGuard] = None
    escada: P.EscadaDePercepcao = field(default_factory=P.EscadaDePercepcao)

    # `checkpoint(patch)` grava incrementalmente em `portal_jobs.evidence`.
    _checkpoint: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

    async def checkpoint(self, patch: Dict[str, Any]) -> None:
        """Grava AGORA, sem esperar o `JourneyResult`.

        🔴 A regra do Bloco B6: a informação cuja perda pode causar repetição
        material precisa chegar ao banco **antes** do próximo clique perigoso.
        Esperar o fim do job é exatamente o que transforma uma queda em um
        segundo atendimento.
        """
        if not isinstance(patch, dict) or not patch:
            return
        self.evidence.update(patch)
        if self._checkpoint is None:
            return
        try:
            await self._checkpoint(patch)
        except Exception as e:  # noqa: BLE001
            # Falha de checkpoint não pode virar falha de job — mas também não
            # pode passar calada, porque ela degrada a proteção transacional.
            logger.warning("[PORTAL] checkpoint nao gravou: %s", type(e).__name__)
            self.evidence.setdefault("checkpoint_falhou", []).append(type(e).__name__)

    def declarar_acao_material(self, rotulo: str) -> None:
        """A journey nomeia o único botão material que espera clicar."""
        if self.guard is not None:
            self.guard.acao_material_esperada = str(rotulo or "")

    def registrar_camada(self, camada: str) -> None:
        self.escada.registrar(camada)

    def resumo_execucao(self) -> Dict[str, Any]:
        """O bloco `execution` de `evidence` — SPEC-073 H1."""
        base = self.escada.resumo()
        drifts = 0
        if self.profiler is not None:
            drifts = len([t for t in self.profiler.telas
                          if t.get("drift") not in ("none", "unknown")])
        return {
            "layers_used": base.get("layers_used", []),
            "layer_final": base.get("layer_final", ""),
            "fallback_count": base.get("fallback_count", 0),
            "screen_drifts": drifts,
            "rejected_actions": base.get("rejected_actions", []),
        }

    def selar_evidencia(self) -> Dict[str, Any]:
        """O envelope final, redigido. É o que o worker mescla em `evidence`.

        Tudo aqui passa pelo redator único: um campo novo acrescentado com
        pressa numa journey não vira o vazamento da próxima semana.
        """
        bloco: Dict[str, Any] = {
            "runtime": {
                "portal_key": self.portal_key,
                "journey": self.journey,
                "discovery": bool(self.discovery_mode),
                "vision": bool(self.vision_enabled),
                "account_label": self.account_label,
            },
            "execution": self.resumo_execucao(),
            "critical_effect": G.efeito_critico(self.evidence),
        }
        if self.profiler is not None and self.profiler.habilitado:
            bloco["profiler"] = self.profiler.resumo()
            if self.discovery_mode:
                bloco["discovery"] = self.profiler.discovery_block()
        if self.guard is not None and self.guard.bloqueios:
            bloco["blocked_actions"] = self.guard.bloqueios[:12]
        return R.redigir(bloco)


def montar_runtime(job: Dict[str, Any],
                   *,
                   account_label: str = "",
                   account_id: Optional[str] = None,
                   evidence: Optional[Dict[str, Any]] = None,
                   checkpoint: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
                   host_portal: str = "") -> PortalRuntimeContext:
    """Cria o contexto UMA vez por `_run_job`, com as flags do ambiente.

    A liberação material vem de `params["confirm"]` — que nasce `False` em
    `portal_params.py` e só é ligado pelo gate determinístico do agente. O
    runtime **não decide** isso; ele apenas transporta a decisão de quem tem
    autoridade.
    """
    ev = evidence if isinstance(evidence, dict) else {}
    params = job.get("params") if isinstance(job.get("params"), dict) else {}
    disc = discovery_mode()

    prof = PortalProfiler(
        portal_key=str(job.get("portal_key") or ""),
        host_portal=host_portal,
        habilitado=profiler_enabled(),
        discovery=disc,
    )

    guard = G.PortalActionGuard(
        job_id=str(job.get("id") or ""),
        company_id=str(job.get("company_id") or ""),
        portal_key=str(job.get("portal_key") or ""),
        journey=str(job.get("journey") or ""),
        discovery_mode=disc,
        material_liberado=bool(params.get("confirm")),
        evidence=ev,
        _checkpoint=checkpoint,
    )

    rt = PortalRuntimeContext(
        job_id=str(job.get("id") or ""),
        company_id=str(job.get("company_id") or ""),
        portal_key=str(job.get("portal_key") or ""),
        journey=str(job.get("journey") or ""),
        account_id=account_id,
        account_label=account_label,
        discovery_mode=disc,
        vision_enabled=P.visao_habilitada(),
        profiler_enabled=profiler_enabled(),
        evidence=ev,
        profiler=prof,
        guard=guard,
        _checkpoint=checkpoint,
    )
    return rt
