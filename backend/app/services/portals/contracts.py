# -*- coding: utf-8 -*-
"""Os contratos globais de execução de portal — SPEC-075 Blocos B, G e H.

Este módulo é **puro**: sem Supabase, sem rede, sem Playwright. Ele existe para
que a decisão possa ser testada sem infraestrutura, e para que o mesmo
vocabulário seja usado pelo Gateway, pelo Tool Gateway, pelas Rotinas e pelos
Auxiliares — em vez de cada um inventar o seu.

O que ele NÃO é
===============
Não é um segundo Tool Gateway, não é um segundo Work Run e não é um segundo
registry. É o formato do pedido, o formato da resposta, e as regras puras que
decidem entre os dois.

Três ideias emprestadas de quem já resolveu isto
=================================================
Nenhuma dependência nova entra por causa delas — só o desenho:

**Stripe, chave de idempotência.** A chave sozinha não basta: o mesmo valor
chegando com um corpo DIFERENTE é erro, não repetição. Sem essa conferência, um
segundo pedido — de peça diferente, de lado diferente — herdaria o resultado do
primeiro em silêncio, e o segurado receberia "já abri" sobre um pedido que não é
o dele. Ver `IdempotencyRecord.conflita_com`.

**Temporal, erro não-retentável declarado.** A política de retry não é um número
de tentativas: é uma tabela que diz **quais falhas não devem ser repetidas
nunca**. Aqui isso é `politica_de_retry()`, dirigida pela classe de efeito e pela
fase do checkpoint da SPEC-073 — e não por um contador.

**Kubernetes Lease.** Lock com dono, prazo e renovação — não `SETNX` e reza. Um
processo que morre libera por expiração; um que trabalha renova. Isso vive em
`leases.py`; aqui fica só o vocabulário.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# --------------------------------------------------------------------------
# Modos de operação da ponte — SPEC-075 §49
# --------------------------------------------------------------------------
MODO_LEGACY = "legacy"   # a ponte não é usada; cada chamador faz o que fazia
MODO_SHADOW = "shadow"   # a ponte resolve e REGISTRA, o caminho legado executa
MODO_ON = "on"           # a ponte executa

MODOS_VALIDOS: Tuple[str, ...] = (MODO_LEGACY, MODO_SHADOW, MODO_ON)


def modo_valido(valor: Any, padrao: str = MODO_LEGACY) -> str:
    """Modo desconhecido vira `legacy`, nunca `on`.

    Uma variável de ambiente com erro de digitação não pode ligar um caminho
    novo em produção. O default mais seguro é o comportamento de ontem.
    """
    v = str(valor or "").strip().lower()
    return v if v in MODOS_VALIDOS else padrao


# --------------------------------------------------------------------------
# Como esperar — SPEC-075 §10.1
# --------------------------------------------------------------------------
ESPERA_AGUARDAR = "await"    # bloqueia até o desfecho, com teto
ESPERA_ENFILEIRAR = "enqueue"  # devolve o handle e segue a vida


# --------------------------------------------------------------------------
# O pedido
# --------------------------------------------------------------------------
@dataclass
class PortalExecutionRequest:
    """O que um chamador do Work OS diz. Note o que NÃO está aqui.

    🔴 Não existe `journey_key`, `module`, `function`, `account_id`, `cookie`,
    `token`, `password` nem `proxy` neste contrato — e essa ausência é a razão
    de o contrato existir. O que o modelo pode dizer é o RESULTADO que quer
    (`operation_key`) e os DADOS DE NEGÓCIO (`business_input`). Quem escolhe a
    função é o registro; quem escolhe a conta é o resolver.

    Os campos `*_hint` são a exceção nomeada, e só valem quando
    `origem_confiavel=True` — ver `hints_utilizaveis()`.
    """

    company_id: str
    operation_key: str
    business_input: Dict[str, Any] = field(default_factory=dict)

    # linhagem — injetada pelo runtime, NUNCA pelo LLM
    work_run_id: Optional[str] = None
    work_step_id: Optional[str] = None
    skill_release_id: Optional[str] = None
    tool_release_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # origem governada
    insurer_key: Optional[str] = None
    portal_key_hint: Optional[str] = None
    account_id_hint: Optional[str] = None

    # 🔴 Só código server-side marca isto. O schema exposto ao agente não tem
    # este campo — se um dia tiver, os hints deixam de valer (ver o teste).
    origem_confiavel: bool = False

    # proteção
    idempotency_key: Optional[str] = None
    effect_class_autorizada: Optional[str] = None
    priority: int = 100
    wait_mode: str = ESPERA_AGUARDAR

    def hints_utilizaveis(self) -> bool:
        """Hint só vale de chamador server-side confiável — SPEC-075 §10.3 C.

        `billing_collection` deriva o `portal_key` do próprio registro, então o
        valor nasceu de código. Texto de modelo nunca nasce de código.
        """
        return bool(self.origem_confiavel)

    def impressao_do_pedido(self) -> str:
        """Hash estável do que este pedido PEDE.

        Serve à conferência do Stripe: mesma chave de idempotência + corpo
        diferente = conflito. Só entram campos de negócio — linhagem e
        prioridade mudam entre chamadas legítimas do mesmo pedido.
        """
        corpo = {
            "company_id": str(self.company_id or ""),
            "operation_key": str(self.operation_key or ""),
            "insurer_key": str(self.insurer_key or ""),
            "business_input": self.business_input or {},
        }
        crua = json.dumps(corpo, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), default=str)
        return hashlib.sha256(crua.encode("utf-8")).hexdigest()[:32]


# --------------------------------------------------------------------------
# O resultado canônico — SPEC-075 Bloco H
# --------------------------------------------------------------------------
# Estado de NEGÓCIO. Não é o status técnico do job: um job `failed` pode ter
# deixado um pedido aberto na seguradora, e um job `done` pode ter descoberto
# que não havia nada a fazer. Quem lê para decidir precisa do estado de negócio.
NEGOCIO_OK = "ok"
NEGOCIO_NADA_A_FAZER = "nothing_to_do"
NEGOCIO_PRECISA_HUMANO = "needs_human"
NEGOCIO_NAO_SUPORTADO = "not_supported"
NEGOCIO_NAO_AUTORIZADO = "not_authorized"
NEGOCIO_SEM_CONEXAO = "no_connection"
NEGOCIO_BLOQUEADO_PELO_PORTAL = "portal_blocked"
NEGOCIO_TALVEZ_COMMITADO = "maybe_committed"
NEGOCIO_FALHOU = "failed"

ESTADOS_DE_NEGOCIO: Tuple[str, ...] = (
    NEGOCIO_OK, NEGOCIO_NADA_A_FAZER, NEGOCIO_PRECISA_HUMANO,
    NEGOCIO_NAO_SUPORTADO, NEGOCIO_NAO_AUTORIZADO, NEGOCIO_SEM_CONEXAO,
    NEGOCIO_BLOQUEADO_PELO_PORTAL, NEGOCIO_TALVEZ_COMMITADO, NEGOCIO_FALHOU,
)

# Os estados em que REPETIR é proibido, sem exceção.
NAO_REPETIR: Tuple[str, ...] = (NEGOCIO_TALVEZ_COMMITADO,)


@dataclass
class PortalExecutionResult:
    """O que qualquer portal devolve, seja qual for a seguradora.

    O chamador não deve precisar saber de que portal veio para saber o que
    fazer. É por isso que `business_state` é obrigatório e `raw` é opcional.
    """

    business_state: str
    operation_key: str = ""
    portal_key: str = ""
    portal_job_id: Optional[str] = None
    work_run_id: Optional[str] = None
    tool_invocation_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    motivo: str = ""
    pode_repetir: bool = True
    idempotency_key: Optional[str] = None
    # `raw` guarda o `JourneyResult` original quando útil ao diagnóstico. Nunca
    # é o que o chamador deve ler para decidir.
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.business_state == NEGOCIO_OK

    def para_dict(self) -> Dict[str, Any]:
        return {
            "business_state": self.business_state,
            "operation_key": self.operation_key,
            "portal_key": self.portal_key,
            "portal_job_id": self.portal_job_id,
            "work_run_id": self.work_run_id,
            "tool_invocation_id": self.tool_invocation_id,
            "data": self.data,
            "message": self.message,
            "motivo": self.motivo,
            "pode_repetir": self.pode_repetir,
            "idempotency_key": self.idempotency_key,
        }


def recusa(estado: str, motivo: str, *, operation_key: str = "",
           portal_key: str = "", pode_repetir: bool = True) -> PortalExecutionResult:
    """Uma recusa sempre EXPLICA. Resultado sem motivo vira ticket de suporte."""
    return PortalExecutionResult(
        business_state=estado, operation_key=operation_key, portal_key=portal_key,
        motivo=motivo, message=motivo, pode_repetir=pode_repetir)


# --------------------------------------------------------------------------
# Idempotência — Bloco G, com a conferência do Stripe
# --------------------------------------------------------------------------
@dataclass
class IdempotencyRecord:
    """O que sabemos sobre uma chave já vista."""

    idempotency_key: str
    request_fingerprint: str
    portal_job_id: Optional[str] = None
    business_state: Optional[str] = None

    def conflita_com(self, req: "PortalExecutionRequest") -> bool:
        """A mesma chave chegou com um pedido DIFERENTE?

        🔴 Este é o caso que a idempotência ingênua trata errado. Se a chave
        bate mas o corpo mudou, o certo NÃO é devolver o resultado antigo — o
        chamador acha que pediu uma coisa e recebeu outra. É erro, e erro alto.

        Registro sem impressão digital (linha antiga, gravada antes desta
        SPEC) nunca conflita: ausência de informação não é prova de divergência,
        e recusar retroativamente quebraria pedidos legítimos em curso.
        """
        if not self.request_fingerprint:
            return False
        return self.request_fingerprint != req.impressao_do_pedido()


def precisa_de_idempotencia(effect_class: str) -> bool:
    """Só efeito material exige chave — SPEC-075 §15.1/§15.2.

    Leitura repetida não machuca ninguém e exigir chave para ler só criaria
    atrito. O que não pode repetir é o que escreve.
    """
    return str(effect_class or "").strip().lower() == "material_side_effect"


# --------------------------------------------------------------------------
# Retry por classe de efeito — Bloco O, no desenho do Temporal
# --------------------------------------------------------------------------
RETRY_AUTOMATICO = "retry_automatico"
RETRY_SE_NADA_CRIADO = "retry_se_nada_criado"
RETRY_PROIBIDO = "retry_proibido"
RECONCILIAR = "reconciliar"


def politica_de_retry(effect_class: Any, fase_do_efeito: Any = "") -> Tuple[str, str]:
    """`(política, motivo)` — o que fazer quando esta execução falhou.

    A decisão NÃO é "quantas tentativas sobraram". É o que a fase do checkpoint
    da SPEC-073 prova sobre o mundo:

        nada armado          → nada aconteceu lá fora, pode repetir
        armed                → ia acontecer; ninguém sabe se aconteceu
        submitted            → saiu da mão, resposta perdida
        confirmed            → aconteceu, e temos o protocolo
        unknown              → o pior caso, e o mais comum em queda de rede

    Fase desconhecida é tratada como incerta. Não saber é motivo para
    reconciliar, nunca para repetir.
    """
    classe = str(effect_class or "").strip().lower()
    fase = str(fase_do_efeito or "").strip().lower()

    if classe in ("read_only", "read", ""):
        return RETRY_AUTOMATICO, "leitura nao muda o mundo: repetir e seguro"

    if fase == "confirmed":
        return (RETRY_PROIBIDO,
                "efeito CONFIRMADO com prova: repetir criaria a segunda operacao")
    if fase in ("submitted", "unknown"):
        return (RECONCILIAR,
                f"efeito em fase `{fase}`: pode ter acontecido no portal. "
                "Consulte antes de qualquer nova tentativa")
    if fase == "armed":
        return (RECONCILIAR,
                "o efeito foi armado e o desfecho se perdeu: reconcilie")

    if classe == "reversible_ui":
        return (RETRY_SE_NADA_CRIADO,
                "acao reversivel sem efeito armado: repetir e aceitavel")
    if classe == "material_side_effect":
        return (RETRY_SE_NADA_CRIADO,
                "material sem efeito armado: nada foi criado, pode repetir")

    return RECONCILIAR, f"classe de efeito desconhecida (`{classe}`): trate como incerta"


def pode_repetir(effect_class: Any, fase_do_efeito: Any = "") -> bool:
    pol, _ = politica_de_retry(effect_class, fase_do_efeito)
    return pol in (RETRY_AUTOMATICO, RETRY_SE_NADA_CRIADO)
