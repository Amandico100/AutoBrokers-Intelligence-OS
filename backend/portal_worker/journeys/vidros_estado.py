# -*- coding: utf-8 -*-
"""A máquina de estados do atendimento de vidros — SPEC-074.

Por que uma máquina de estados, e não um booleano
=================================================
A pergunta que o sistema precisa responder depois de uma queda não é
*"deu certo?"*. É **"o que já existe no mundo lá fora?"** — e essa pergunta tem
mais de duas respostas.

📊 A mineração de 16/08/2026 mostrou que o portal tem **DUAS** fronteiras
materiais onde a tela sugeria uma só:

    POST /atendimentos    →  NumeroProtocolo (16 díg.) + Token de sessão
                             ↑ PRIMEIRO efeito material, logo no passo 1

    POST /questionarios   →  CodigoAtendimento (8 díg.) + ScriptFinalizacao
                             + LinkAreaSegurado
                             ↑ o número que a Regina vê como "Nº do atendimento"

Provado por leitura direta: às 21:15:46 o `GET /atendimentos` devolve
`CodigoAtendimento: null`; às 21:18:33, logo após o `POST /questionarios`, ele
existe.

🔴 A consequência prática é grande. O mapa canônico dizia *"o protocolo aparece
no passo 7"*, e por isso o guard e o checkpoint estavam desenhados para armar
perto do 80%. **Errado.** Quando o robô chega ao 80%, já existe um
`NumeroProtocolo` na seguradora há vários minutos. O checkpoint precisa armar
**antes do passo 1 terminar**.

Um `committed / not_committed` não consegue expressar isso. Esta máquina, sim.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# --------------------------------------------------------------------------
# Os estados. Cada um responde "o que existe lá fora?", não "como estou me
# sentindo sobre o job".
# --------------------------------------------------------------------------
PRE_PROTOCOLO = "pre_protocolo"
# Nada material aconteceu. Preflight, catálogos, leitura de apólice.

PROTOCOLO_CRIADO = "protocolo_criado"
# `POST /atendimentos` respondeu 200. Existe NumeroProtocolo e Token.
# 🔴 Já é irreversível. Repetir cria um SEGUNDO registro.

ATENDIMENTO_MATERIALIZADO = "atendimento_materializado"
# `POST /questionarios` respondeu 200 e o CodigoAtendimento nasceu.
# É o que o analista da seguradora enxerga.

AGUARDANDO_ESCOLHA = "aguardando_escolha_do_segurado"
# 99%: o pedido existe e falta o segurado escolher loja ou domicílio.
# NÃO é falha. O browser deve fechar; a continuação é outra execução.

FINALIZADO = "finalizado"
CANCELADO = "cancelado"          # PUT /atendimentos/cancelar, sobre pedido criado
ABANDONADO = "abandonado"        # PATCH /atendimentos/abandonar, desistência
DESCONHECIDO = "desconhecido"    # maybe_committed: saiu da mão, resposta perdida

ESTADOS: Tuple[str, ...] = (
    PRE_PROTOCOLO, PROTOCOLO_CRIADO, ATENDIMENTO_MATERIALIZADO,
    AGUARDANDO_ESCOLHA, FINALIZADO, CANCELADO, ABANDONADO, DESCONHECIDO,
)

# Estados em que JÁ EXISTE alguma coisa na seguradora. A lista é usada para
# responder a única pergunta que importa antes de um retry.
ESTADOS_COM_EFEITO: Tuple[str, ...] = (
    PROTOCOLO_CRIADO, ATENDIMENTO_MATERIALIZADO, AGUARDANDO_ESCOLHA,
    FINALIZADO, CANCELADO, DESCONHECIDO,
)

# Terminais de negócio: não há mais nada a fazer neste atendimento.
ESTADOS_TERMINAIS: Tuple[str, ...] = (FINALIZADO, CANCELADO, ABANDONADO)


def _norm(txt: Any) -> str:
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass
class EstadoDoAtendimento:
    """O que sabemos sobre o pedido, e como provamos.

    Cada campo aqui é FATO observado, nunca inferência. `numero_protocolo`
    preenchido significa que uma resposta HTTP 200 o trouxe — não que o robô
    achou que deu certo.
    """

    estado: str = PRE_PROTOCOLO
    numero_protocolo: str = ""      # 16 dígitos, de POST /atendimentos
    codigo_atendimento: str = ""    # 8 dígitos, de POST /questionarios
    link_area_segurado: str = ""
    motivo: str = ""
    # Trilha de como chegamos aqui. Vira evidência e explica o desfecho.
    transicoes: list = field(default_factory=list)

    # -- perguntas que o resto do sistema faz a este objeto ----------------
    @property
    def existe_algo_na_seguradora(self) -> bool:
        return self.estado in ESTADOS_COM_EFEITO or bool(self.numero_protocolo)

    @property
    def safe_to_retry_open(self) -> bool:
        """Pode chamar `abrir_atendimento` de novo?

        🔴 Só em UM caso: nada material aconteceu. Qualquer outro desfecho —
        inclusive `desconhecido` — responde não. A SPEC-074 O4 é explícita, e a
        razão é aritmética: um retry indevido produz dois vidraceiros na porta
        do segurado, e nenhum jeito de desfazer.
        """
        return self.estado == PRE_PROTOCOLO and not self.numero_protocolo

    @property
    def precisa_reconciliar(self) -> bool:
        return self.estado == DESCONHECIDO

    @property
    def referencia_para_o_segurado(self) -> str:
        """O número que a pessoa anota. É o de 8 dígitos, não o de 16.

        📊 O `NumeroProtocolo` (16 díg.) é interno: nasce no `POST /atendimentos`
        e não aparece em tela nenhuma. O que a UI mostra como
        `Nº do atendimento:` é o `CodigoAtendimento` (8 díg.).
        Dar o número errado ao segurado é o tipo de erro que só aparece quando
        ele liga na seguradora e ninguém acha o pedido dele.
        """
        return self.codigo_atendimento or ""

    def transitar(self, novo: str, *, motivo: str = "", **dados: Any) -> "EstadoDoAtendimento":
        """Avança o estado registrando de onde para onde, e por quê."""
        if novo not in ESTADOS:
            raise ValueError(f"estado desconhecido: {novo!r}")
        self.transicoes.append({"de": self.estado, "para": novo,
                                "motivo": str(motivo or "")[:200]})
        self.estado = novo
        if motivo:
            self.motivo = str(motivo)[:300]
        for k, v in dados.items():
            if hasattr(self, k) and v not in (None, ""):
                setattr(self, k, str(v))
        return self

    def para_evidencia(self) -> Dict[str, Any]:
        """O bloco que vai para `portal_jobs.evidence`. Sem PII."""
        return {
            "estado": self.estado,
            "tem_protocolo": bool(self.numero_protocolo),
            "tem_codigo_atendimento": bool(self.codigo_atendimento),
            "existe_algo_na_seguradora": self.existe_algo_na_seguradora,
            "safe_to_retry_open": self.safe_to_retry_open,
            "precisa_reconciliar": self.precisa_reconciliar,
            "motivo": self.motivo,
            "transicoes": self.transicoes[-12:],
        }


# --------------------------------------------------------------------------
# Leitura do agregado — o read model único do portal
# --------------------------------------------------------------------------
# 📊 `GET /atendimentos` é o ÚNICO endpoint de leitura do estado (7 chamadas na
# captura, sempre o mesmo agregado de ~58 campos). Não existem leituras
# granulares. Ele é chamado depois de cada mutação para re-hidratar a tela.
def ler_estado_do_agregado(atendimento: Any,
                           *,
                           tinha_protocolo: bool = False) -> EstadoDoAtendimento:
    """Deriva o estado a partir da resposta de `GET /atendimentos`.

    A ordem das checagens importa e é do mais forte para o mais fraco:
    cancelado vence tudo; código de atendimento vence protocolo; protocolo vence
    ausência. Inverter faria um pedido cancelado parecer ativo.
    """
    a = atendimento if isinstance(atendimento, dict) else {}
    est = EstadoDoAtendimento()

    codigo = str(a.get("CodigoAtendimento") or "").strip()
    link = str(a.get("LinkAreaSegurado") or "").strip()

    if a.get("Cancelado") is True:
        est.codigo_atendimento = codigo
        return est.transitar(CANCELADO, motivo="portal declarou Cancelado=true")

    if codigo:
        est.codigo_atendimento = codigo
        est.link_area_segurado = link
        return est.transitar(ATENDIMENTO_MATERIALIZADO,
                             motivo="CodigoAtendimento presente no agregado")

    if tinha_protocolo:
        return est.transitar(PROTOCOLO_CRIADO,
                             motivo="protocolo emitido; atendimento ainda nao materializado")

    return est


def idempotencia_da_operacao(*, company_id: Any, operacao: str,
                             placa: Any = "", data_sinistro: Any = "",
                             item: Any = "", lado: Any = "",
                             protocolo: Any = "") -> str:
    """Chave de idempotência derivada do NEGÓCIO, nunca de um UUID aleatório.

    🔴 A lateralidade entra na chave, e isso não é detalhe. O portal diz, em
    texto na tela: *"se o item possuir lateralidade será necessário abrir uma
    nova solicitação para o outro lado"*. Dois vidros quebrados são dois
    pedidos legítimos — e sem o lado na chave o segundo seria barrado como
    repetição, e o segurado descobriria quando o vidraceiro consertasse um só.

    Para operações de CONTINUAÇÃO a chave é outra: ela identifica
    `empresa + protocolo + operação`, nunca reaproveita a chave de criação. A
    SPEC-074 L6 é explícita, e o motivo é que "continuar" e "criar" produzem
    efeitos opostos com a mesma aparência de sucesso.
    """
    op = _norm(operacao)
    if protocolo:
        partes = ["v2", _norm(company_id), "cont", _norm(protocolo), op]
    else:
        partes = ["v2", _norm(company_id), op, _norm(placa),
                  _norm(data_sinistro), _norm(item), _norm(lado)]
    crua = "|".join(p for p in partes)
    # Sem os três dados que identificam o pedido, não há chave — e chave vazia
    # vira NULL no banco, que o índice parcial ignora. Fail-OPEN de propósito:
    # o guarda nunca pode ser o motivo de um acionamento legítimo não acontecer.
    if not protocolo and not (_norm(placa) and _norm(data_sinistro) and _norm(item)):
        return ""
    return hashlib.sha256(crua.encode("utf-8", "ignore")).hexdigest()[:32]


# --------------------------------------------------------------------------
# A ponte com o guard da SPEC-073
# --------------------------------------------------------------------------
# 📊 As duas fronteiras medidas, na ordem em que acontecem. O nome da ação é o
# que a journey DECLARA ao guard (`acao_material_esperada`), e é o que o
# validador confere antes de deixar a chamada sair.
FRONTEIRA_ABRIR = "criar_atendimento_maxpar"        # POST /atendimentos
FRONTEIRA_MATERIALIZAR = "gravar_questionario"      # POST /questionarios
FRONTEIRA_CANCELAR = "cancelar_atendimento"         # PUT  /atendimentos/cancelar
FRONTEIRA_ABANDONAR = "abandonar_atendimento"       # PATCH /atendimentos/abandonar

FRONTEIRAS_MATERIAIS: Tuple[str, ...] = (
    FRONTEIRA_ABRIR, FRONTEIRA_MATERIALIZAR, FRONTEIRA_CANCELAR, FRONTEIRA_ABANDONAR,
)


def fase_apos_falha(estado: EstadoDoAtendimento) -> str:
    """Traduz o estado de negócio para a fase de efeito da SPEC-073.

    Serve ao caminho de exceção do worker: se a journey morreu, o
    `critical_effect.phase` precisa contar a verdade para o recovery decidir.
    """
    from portal_worker import guardrails as G

    if estado.estado in (ATENDIMENTO_MATERIALIZADO, AGUARDANDO_ESCOLHA,
                         FINALIZADO, CANCELADO):
        return G.FASE_CONFIRMED
    if estado.estado == PROTOCOLO_CRIADO:
        return G.FASE_CONFIRMED     # o protocolo É a prova
    if estado.estado == DESCONHECIDO:
        return G.FASE_UNKNOWN
    return ""


def resultado_para_o_agente(estado: EstadoDoAtendimento,
                            *,
                            franquia: Optional[Dict[str, Any]] = None,
                            vistoria: Optional[Dict[str, Any]] = None,
                            opcoes: Optional[list] = None) -> Dict[str, Any]:
    """O envelope estruturado da SPEC-074 O2 — antes de virar frase.

    🔴 A frase humana deriva DAQUI, nunca o contrário. O defeito que isso
    impede está registrado na SPEC-074 P1: um job que falha tecnicamente
    **depois** do protocolo dizia ao segurado "não consegui abrir" enquanto o
    pedido existia na seguradora. Estado técnico e estado de negócio são coisas
    diferentes, e quem fala com o cliente precisa do segundo.
    """
    f = franquia or {}
    v = vistoria or {}
    criado = estado.existe_algo_na_seguradora
    return {
        "business_state": estado.estado,
        "request_created": criado,
        "protocol": estado.referencia_para_o_segurado or None,
        "protocolo_interno": estado.numero_protocolo or None,
        # Só sai quando foi LIDA. Nunca inventada — SPEC-074 R10.
        "franchise": (f.get("itens") or [None])[0] if f.get("tem") else None,
        "inspection_url": v.get("link") or None,
        "customer_choice_needed": (estado.estado == AGUARDANDO_ESCOLHA),
        "available_options": opcoes or [],
        "human_needed": estado.estado in (DESCONHECIDO,),
        "human_reason": estado.motivo if estado.estado == DESCONHECIDO else None,
        "safe_to_retry_open": estado.safe_to_retry_open,
        "link_area_segurado": estado.link_area_segurado or None,
    }
