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
                             ↑ o número que a atendente vê como "Nº do atendimento"

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


def idempotencia_de_continuacao(*, company_id: Any, protocolo: Any,
                                operacao: str) -> str:
    """A chave de uma operação SOBRE UM PEDIDO QUE JÁ EXISTE.

    🔴 Ela é deliberadamente OUTRA função, e não um parâmetro da chave de
    criação. A SPEC-074 L6 exige isso, e o motivo é que "criar" e "continuar"
    produzem efeitos opostos com a mesma aparência de sucesso: reaproveitar a
    chave de criação para uma continuação faria o guarda achar que o pedido já
    existe (e recusar a continuação legítima) ou que não existe (e criar um
    segundo). As duas saídas são erradas.

    A chave de CRIAÇÃO tem um dono só: `portal_params.chave_de_idempotencia`.
    Duas funções para a mesma pergunta é o que este projeto não faz — mas estas
    duas respondem perguntas diferentes.

    Identifica `empresa + protocolo + operação`. Sem protocolo não há
    continuação a identificar, e a chave é vazia (fail-open, como a de criação).
    """
    prot = _norm(protocolo)
    if not prot or not _norm(company_id):
        return ""
    crua = "|".join(["cont1", _norm(company_id), prot, _norm(operacao)])
    return hashlib.sha256(crua.encode("utf-8", "ignore")).hexdigest()[:32]


# --------------------------------------------------------------------------
# A ponte com o guard da SPEC-073
# --------------------------------------------------------------------------
# 📊 As duas fronteiras medidas, na ordem em que acontecem. O nome da ação é o
# que a journey DECLARA ao guard (`acao_material_esperada`), e é o que o
# validador confere antes de deixar a chamada sair.
FRONTEIRA_ABRIR = "criar_atendimento_maxpar"        # POST /atendimentos
FRONTEIRA_MATERIALIZAR = "gravar_questionario"      # POST /questionarios
FRONTEIRA_ATUALIZAR = "atualizar_atendimento"       # PATCH /atendimentos
FRONTEIRA_CANCELAR = "cancelar_atendimento"         # PUT  /atendimentos/cancelar
FRONTEIRA_ABANDONAR = "abandonar_atendimento"       # PATCH /atendimentos/abandonar
# 📊 EXTRA-001.10.1 — as três escritas que as capturas de 21/09 destravaram.
# Cada uma muda o que a seguradora faz com o segurado (o dia em que ele leva o
# carro; a fila do analista; o tipo de vistoria), e nenhuma se desfaz pela API.
FRONTEIRA_AGENDAR = "agendar_servico"               # POST /agendamentos
FRONTEIRA_PRIORIDADE = "gravar_prioridade"          # POST /atendimentos-prioridades
FRONTEIRA_OCORRENCIA = "gravar_ocorrencia_vistoria"  # POST /ocorrencias

FRONTEIRAS_MATERIAIS: Tuple[str, ...] = (
    FRONTEIRA_ABRIR, FRONTEIRA_MATERIALIZAR, FRONTEIRA_ATUALIZAR,
    FRONTEIRA_CANCELAR, FRONTEIRA_ABANDONAR,
    FRONTEIRA_AGENDAR, FRONTEIRA_PRIORIDADE, FRONTEIRA_OCORRENCIA,
)


# --------------------------------------------------------------------------
# 🔴 A CONTINUAÇÃO — em que ETAPA o pedido parou e o que falta para seguir
# --------------------------------------------------------------------------
# EXTRA-001.10.1. `evidence["continuacao"]["etapa"]` diz de onde a journey
# `continuar_atendimento` retoma; `acao_esperada` diz o que a CONVERSA precisa
# trazer (`responder:<slot>`) ou fazer (`agendar`, `vistoria`, `reler`).
# 🔴 A tabela é FECHADA: stage fora dela não tem continuação automática
# (`possivel=False`) — melhor a equipe olhar do que o robô adivinhar a fase.
ETAPA_CONTATO = "contato"
ETAPA_PECA = "peca"
ETAPA_CAUSA = "causa"
ETAPA_LATARIA = "lataria"
ETAPA_CIDADE = "cidade"
ETAPA_MATERIALIZAR = "materializar"
ETAPA_DESFECHO = "desfecho"
ETAPA_AGENDAR = "agendar"
ETAPA_VISTORIA = "vistoria"
ETAPA_CONCLUIDO = "concluido"

# A ordem em que as fases da abertura acontecem. A continuação sem
# `CodigoAtendimento` retoma a partir da etapa gravada; as fases de LEITURA
# anteriores rodam de novo (ler é reversível e o `codigo_item` depende delas).
ORDEM_DAS_ETAPAS: Tuple[str, ...] = (
    ETAPA_CONTATO, ETAPA_PECA, ETAPA_CAUSA, ETAPA_LATARIA, ETAPA_CIDADE,
    ETAPA_MATERIALIZAR, ETAPA_DESFECHO,
)

ETAPA_DA_PARADA: Dict[str, Tuple[str, str]] = {
    "corretor_recusado": (ETAPA_CONTATO, "reler"),
    "tipo_de_telefone_desconhecido": (ETAPA_CONTATO, "reler"),
    "solicitante_recusado": (ETAPA_CONTATO, "reler"),
    "catalogo_indisponivel": (ETAPA_PECA, "reler"),
    "peca_ambigua": (ETAPA_PECA, "responder:peca"),
    "item_com_formato_desconhecido": (ETAPA_PECA, "reler"),
    "motivos_indisponiveis": (ETAPA_CAUSA, "reler"),
    "motivo_ambiguo": (ETAPA_CAUSA, "responder:como"),
    "pecas_de_lataria_ausentes": (ETAPA_LATARIA, "responder:pecas_lataria"),
    "peca_de_lataria_ambigua": (ETAPA_LATARIA, "responder:pecas_lataria"),
    "uf_desconhecida": (ETAPA_CIDADE, "responder:cidade_servico"),
    "cidade_ambigua": (ETAPA_CIDADE, "responder:cidade_servico"),
    "cidade_sem_rede": (ETAPA_CIDADE, "responder:cidade_servico"),
    "pronto_para_materializar": (ETAPA_MATERIALIZAR, "reler"),
    "patch_recusado": (ETAPA_MATERIALIZAR, "reler"),
    "questionario_incompleto": (ETAPA_MATERIALIZAR, "responder:pergunta"),
    "decidir_reparo": (ETAPA_MATERIALIZAR, "responder:aceita_reparo"),
    "reparo_nao_gravado": (ETAPA_DESFECHO, "reler"),
    "roteador_ilegivel": (ETAPA_DESFECHO, "reler"),
    "desfecho_ilegivel": (ETAPA_DESFECHO, "reler"),
    "desfecho_desconhecido": (ETAPA_DESFECHO, "reler"),
    # 🔴 a agenda que saiu e não confirmou: RELER, nunca repetir o POST
    "agendamento_nao_confirmado": (ETAPA_DESFECHO, "reler"),
    "pronto_para_agendar": (ETAPA_AGENDAR, "agendar"),
    "horario_indisponivel": (ETAPA_AGENDAR, "agendar"),
    "agenda_ilegivel": (ETAPA_AGENDAR, "agendar"),
    "decidir_vistoria": (ETAPA_VISTORIA, "vistoria"),
    "prioridade_nao_medida": (ETAPA_VISTORIA, "vistoria"),
    "pronto_para_vistoria": (ETAPA_VISTORIA, "vistoria"),
    "leitura_falhou": (ETAPA_DESFECHO, "reler"),
}

# Stages em que o efeito pode ter acontecido sem confirmação: a continuação
# LÊ, e se o agregado não provar o estado, para — nunca repete a escrita.
PARADAS_INCERTAS: Tuple[str, ...] = ("maybe_committed",)


def etapa_da_parada(stage: Any) -> Tuple[str, str]:
    """`(etapa, acao_esperada)` de uma parada. `("", "")` = sem continuação."""
    st = str(stage or "").strip()
    if st in PARADAS_INCERTAS:
        return ETAPA_DESFECHO, "reler"
    return ETAPA_DA_PARADA.get(st, ("", ""))


def fronteira_materializar_de(codigo_item_coberto: Any) -> str:
    """Qual ação, NESTA peça, faz o pedido existir para o analista.

    🔴 Esta função existe porque a resposta **não é a mesma para toda peça**, e
    a constante fixa que estava no lugar dela acertava metade dos casos.

    📊 Medido nas capturas de 20/09/2026, com o mesmo `GET /atendimentos` logo
    depois da mesma mutação:

        categoria `L` (lataria)      o `CodigoAtendimento` nasce logo após o
                                     **PATCH**, e não há `POST /questionarios`
                                     nenhum na captura inteira
        categoria `V` (vidraçaria)   o PATCH NÃO materializa: o código nasce
                                     depois do **POST /questionarios**
                                     (📊 N=2 em `V`: vidro de porta e para-brisa)

    Categoria desconhecida — inclusive `U` (roda/pneu), que esta SPEC não
    percorre — devolve a fronteira MAIS CONSERVADORA: arma **antes** do PATCH.
    Fail-closed: pedir autorização cedo demais custa uma pergunta; pedir tarde
    demais custa um pedido aberto sem ninguém ter autorizado.
    """
    from portal_worker.journeys import vidros_api as API

    categoria = str(API.partes_do_item_coberto(codigo_item_coberto).get("categoria") or "")
    if categoria == API.CATEGORIA_VIDRACARIA:
        return FRONTEIRA_MATERIALIZAR
    return FRONTEIRA_ATUALIZAR


# --------------------------------------------------------------------------
# 🔴 O DESFECHO — quem decide loja ou agenda é o PORTAL, e ele diz por escrito
# --------------------------------------------------------------------------
DESFECHO_LOJA_DIRETA = "loja_direta"
DESFECHO_AGENDA = "agenda"
DESFECHO_ANALISTA = "analista"
DESFECHO_VISTORIA = "vistoria"
DESFECHO_DESCONHECIDO = "desconhecido"
# 📊 EXTRA-001.10.1 — o "Agendado para" LIDO do ScriptFinalizacao (LATERAL [049]).
DESFECHO_AGENDADO = "agendado"
# 📊 EXTRA-001.10.1 — ramo 7 do roteador do SPA (`PermiteOpcaoVistoria` sem
# nada antes): o portal quer PRIORIDADE + PREFERÊNCIA DE VISTORIA antes de
# concluir. Não é "vistoria" (ramos 2–5, que o robô não faz): é uma PERGUNTA ao
# segurado, e com a resposta dele o portal conclui (LATARIA [089]→[093]→[094]).
DESFECHO_VISTORIA_OPCIONAL = "vistoria_opcional"

DESFECHOS: Tuple[str, ...] = (
    DESFECHO_LOJA_DIRETA, DESFECHO_AGENDA, DESFECHO_ANALISTA,
    DESFECHO_VISTORIA, DESFECHO_DESCONHECIDO,
    DESFECHO_AGENDADO, DESFECHO_VISTORIA_OPCIONAL,
)

# 📊 As 20 chaves de `GET /agendamentos/opcoes-disponiveis`, medidas nas 3
# capturas que chegaram até lá (para-brisa, lataria, vidro de porta). A lista é
# FECHADA de propósito: uma chave booleana nova, ligada, é uma decisão do portal
# que este roteador não sabe ler — e a resposta certa para isso é parar.
CHAVES_DO_ROTEADOR: Tuple[str, ...] = (
    "AceitaReparo", "BloqueadoIlhaNormal", "BloqueadoPorFraude",
    "DisponibilizarAgendamento", "ExibirAvisoVistoria",
    "ExibirAvisoVistoriaPorRegraDeFraude", "ExisteAgendamento",
    "ExisteOrdemServico", "ExisteVistoriaCriada", "GerarOrdemServicoGenesis",
    "IrParaConclusaoDeAtendimento", "MensagemVistoria", "OpcoesAgendamento",
    "PermiteOpcaoVistoria", "PermiteVistoriaAmbas", "PermiteVistoriaLoja",
    "PermiteVistoriaMobile", "RealizarVistoria", "VistoriaFinalizada",
    "VistoriaOnline",
)

# As que o roteador do bundle de fato consulta, NA ORDEM em que ele as consulta.
_CONCLUSAO: Tuple[str, ...] = (
    "IrParaConclusaoDeAtendimento", "ExisteVistoriaCriada", "ExisteAgendamento",
    "ExisteOrdemServico", "VistoriaFinalizada",
)
_VISTORIA: Tuple[str, ...] = (
    "PermiteVistoriaAmbas", "PermiteVistoriaLoja", "PermiteVistoriaMobile",
    "RealizarVistoria",
)


def ler_desfecho(opcoes: Any, agregado: Any) -> Dict[str, Any]:
    """O que o portal decidiu — função PURA sobre as duas respostas dele.

    🔴 O ELO desta SPEC: *"a loja aparece PORQUE `opcoes-disponiveis` mandou"*.
    Nenhum `if categoria == "L"` mora aqui. 📊 A prova de que não é atributo da
    peça: mesma seguradora, mesma apólice, mesma categoria `V` — o para-brisa
    terminou em loja direta e o vidro de porta em agenda, porque as respostas
    deste endpoint foram opostas.

    A ordem é a do bundle (`function M(o)`, laudo §2), e inverter troca o
    desfecho de gente de verdade:

        (1) conclusão (5 chaves, OU)  → agendado · loja já atribuída · analista
        (2–5) vistoria (4 chaves)     → vistoria
        (6) DisponibilizarAgendamento → agenda, com `OpcoesAgendamento[]`
        (7) PermiteOpcaoVistoria      → vistoria_opcional (prioridade + preferência)
        (8) nenhuma                   → conclusão (o SPA chama `F()`)

    Fail-closed em dois casos, e os dois viram `desconhecido` com o roteador
    inteiro preenchido para o dossiê: (1) a resposta não trouxe as chaves que o
    roteador consulta; (2) veio uma chave booleana **fora das 20 medidas** e ela
    está LIGADA — o portal passou a decidir por um caminho que nós não lemos.
    """
    o = opcoes if isinstance(opcoes, dict) else {}
    a = agregado if isinstance(agregado, dict) else {}
    base, script = _base_do_desfecho(o, a)
    return _ramos_do_roteador(o, base, script)


def ler_conclusao(opcoes: Any, agregado: Any) -> Dict[str, Any]:
    """O desfecho DEPOIS de uma escrita que leva o SPA direto à conclusão.

    📊 EXTRA-001.10.1: depois do `POST /agendamentos` (LATERAL [048]→[049]) e da
    ocorrência de vistoria (LATARIA [093]→[094]) o SPA chama `F()` — a tela de
    conclusão — SEM reler `opcoes-disponiveis`. O que vale é o ScriptFinalizacao
    do `GET /atendimentos` seguinte. `opcoes` entra só para o dossiê.
    """
    o = opcoes if isinstance(opcoes, dict) else {}
    a = agregado if isinstance(agregado, dict) else {}
    base, script = _base_do_desfecho(o, a)
    return conclusao(base, script)


def _base_do_desfecho(o: Dict[str, Any], a: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    from portal_worker.journeys import vidros_api as API

    roteador = {k: o.get(k) for k in CHAVES_DO_ROTEADOR if k in o}
    script = API.script_de_finalizacao(a)
    franquia = API.descricao_da_franquia(a)
    base: Dict[str, Any] = {
        "tipo": DESFECHO_DESCONHECIDO,
        "roteador": roteador,
        "codigo_atendimento": str(a.get("CodigoAtendimento") or "").strip(),
        "titulo_portal": script["titulo"],
        "franquias": franquia.get("itens") or [],
        "reparo": None,
        "aceita_reparo_portal": o.get("AceitaReparo"),
        "link_area_segurado": str(a.get("LinkAreaSegurado") or "").strip(),
        "loja": None,
        "lojas": [],
        "motivo": "",
    }
    return base, script


def _ramos_do_roteador(o: Dict[str, Any], base: Dict[str, Any],
                       script: Dict[str, Any]) -> Dict[str, Any]:
    # 🔴 BLOQUEIO NUNCA VIRA "pode ligar para a loja" — red team, 20/09/2026.
    #
    # 📊 Com `BloqueadoPorFraude: true` (ou o aviso de vistoria por regra de
    # fraude) MAIS as chaves de conclusao, o roteador respondia `loja_direta` e
    # o segurado era mandado a uma loja que nao vai atende-lo.
    #
    # 🔴 EXTRA-001.10.1 — `BloqueadoIlhaNormal` SAIU desta lista, por medição:
    # 📊 a chave tem ZERO ocorrências nos 3 bundles do SPA (laudo §2), e no HAR
    # LATARIA [089] ela veio `true` junto de `PermiteOpcaoVistoria` e o portal
    # SEGUIU — prioridade [092], ocorrência [093], conclusão com o analista
    # [094]. Tratá-la como trava mandava para a mão humana um pedido que o
    # próprio portal conclui. As outras duas continuam travando (0 exercícios:
    # conservador até uma captura mostrar o contrário).
    travas = [k for k in ("BloqueadoPorFraude",
                          "ExibirAvisoVistoriaPorRegraDeFraude") if o.get(k) is True]
    if travas:
        base["motivo"] = ("o portal marcou bloqueio/retencao: " + ", ".join(travas)
                          + ". Nao ha desfecho a prometer ao segurado.")
        base["bloqueios"] = travas
        return base

    desconhecidas = [k for k, v in o.items()
                     if k not in CHAVES_DO_ROTEADOR and isinstance(v, bool) and v]
    if desconhecidas:
        base["motivo"] = ("o portal respondeu com chave(s) que este roteador nao "
                          "conhece, ligada(s): " + ", ".join(sorted(desconhecidas)))
        base["chaves_novas"] = sorted(desconhecidas)
        return base

    if not any(k in o for k in _CONCLUSAO + ("DisponibilizarAgendamento",)):
        base["motivo"] = ("opcoes-disponiveis veio sem as chaves do roteador "
                          f"(chaves recebidas: {len(o)})")
        return base

    if any(o.get(k) is True for k in _CONCLUSAO):
        return conclusao(base, script)

    if any(o.get(k) is True for k in _VISTORIA):
        base["tipo"] = DESFECHO_VISTORIA
        base["motivo"] = "portal pediu vistoria"
        return base

    if o.get("DisponibilizarAgendamento") is True:
        lojas = [x for x in (o.get("OpcoesAgendamento") or []) if isinstance(x, dict)]
        base["tipo"] = DESFECHO_AGENDA
        base["lojas"] = [{
            "codigo_cliente": x.get("CodigoCliente"),
            "codigo_produto": x.get("CodigoProduto"),
            "nome": str(x.get("NomeLoja") or "").strip(),
            "endereco": str(x.get("Endereco") or "").strip(),
            "bairro": str(x.get("Bairro") or "").strip(),
            "cidade": str(x.get("Cidade") or "").strip(),
            "uf": str(x.get("SiglaUF") or "").strip(),
            "cep": str(x.get("Cep") or "").strip(),
            # 📊 `"S"` na captura. A agenda só existe quando a loja a publica.
            "tem_agenda": str(x.get("DisponibilizaAgenda") or "").strip().upper() == "S",
            # 📊 laudo §1, função `I`: loja SEM estoque próprio e COM `TemPeca`
            # bloqueia blocos por previsão de peça — fórmula não medida. As
            # chaves não vieram na captura; se vierem, a agenda dela não é lida.
            "bloqueio_por_peca_nao_medido": (x.get("EstoqueProprio") is False
                                             and bool(x.get("TemPeca"))),
            "distancia": "", "tempo": "", "dias": [], "horarios": {},
        } for x in lojas]
        base["motivo"] = f"portal disponibilizou agendamento em {len(lojas)} loja(s)"
        return base

    if o.get("PermiteOpcaoVistoria") is True:
        base["tipo"] = DESFECHO_VISTORIA_OPCIONAL
        base["motivo"] = ("portal pediu a prioridade e a preferencia de vistoria "
                          "(ramo 7) antes de concluir")
        return base

    # (8) Nenhum ramo: o SPA vai para a conclusão (`F()`). 🔴 Só aceitamos se o
    # ScriptFinalizacao disser ALGUMA coisa — conclusão sem texto nenhum não é
    # desfecho que se entregue a alguém.
    if script["titulo"] or script["tem_loja"]:
        return conclusao(base, script)
    base["motivo"] = ("nenhum ramo do roteador ficou verdadeiro e o portal nao "
                      "escreveu desfecho")
    return base


def conclusao(base: Dict[str, Any], script: Dict[str, Any]) -> Dict[str, Any]:
    """O ramo de CONCLUSÃO: quem diz o que concluiu é o ScriptFinalizacao.

    📊 E ele só traz a loja DEPOIS de `opcoes-disponiveis` (ver
    `script_de_finalizacao`). Três leituras, da mais específica para a menos:
    "Agendado para" (EXTRA-001.10.1) → loja atribuída → com o analista.
    """
    if script.get("agendamento") and script.get("tem_loja"):
        ag = script["agendamento"]
        loja = script["loja"] or {}
        base["tipo"] = DESFECHO_AGENDADO
        base["loja"] = loja
        base["agendamento"] = {
            "loja": loja.get("nome", ""), "endereco": loja.get("endereco", ""),
            "referencia": loja.get("referencia", ""),
            "data": ag["data"], "horario": ag["horario"],
            "permanencia": ag.get("permanencia", ""),
            "confirmado_pelo_portal": True,
        }
        base["motivo"] = "o portal registrou o agendamento (Agendado para)"
    elif script["tem_loja"]:
        base["tipo"] = DESFECHO_LOJA_DIRETA
        base["loja"] = script["loja"]
        base["motivo"] = "portal concluiu com loja atribuida"
    else:
        base["tipo"] = DESFECHO_ANALISTA
        base["motivo"] = ("portal concluiu sem loja no script; o atendimento "
                          "esta com o analista")
    return base


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
