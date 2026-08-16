# -*- coding: utf-8 -*-
"""A journey API-first do portal de vidros — SPEC-074, atrás de flag.

Como ela entra sem arriscar o que funciona
==========================================
`PORTAL_VIDROS_API_FIRST` nasce **false**. Com a flag desligada,
`vidros_lanternas.abrir_atendimento` segue exatamente o caminho de hoje —
`_select_insurer_start` → passo 1 → modal → `run_adaptive`. Nenhuma linha muda.

Com a flag ligada, este módulo assume os passos que a API resolve melhor, e
devolve o controle ao caminho DOM em qualquer ponto que ele não conheça.

🔴 A ordem das operações NÃO é a da tela
========================================
📊 A medição mostrou que o portal cria o pedido MUITO antes do que o mapa
canônico dizia. O checkpoint tem de armar antes do passo 1 terminar:

    GET  /apolices          preflight — read-only, decide se PODE escrever
    ────────────── fronteira A ──────────────
    POST /atendimentos      NumeroProtocolo + Token · IRREVERSÍVEL
    PUT  /atendimentos/corretores
    POST /solicitantes
    PATCH /atendimentos     grava peça, causa, local
    POST /questionarios/perguntas  ×N   (leitura! não persiste)
    ────────────── fronteira B ──────────────
    POST /questionarios     CodigoAtendimento nasce · IRREVERSÍVEL

O laço de perguntas fica ENTRE as duas fronteiras e é **read-only**: dá para
descobrir que falta um dado e parar sem ter materializado nada.

O que este módulo NÃO faz
=========================
Não escolhe loja. Não agenda. Não cancela. Não finaliza. Essas são mutações que
a SPEC-074 M3 manda deixar preparadas e desligadas até haver tela medida.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from portal_worker.journeys import JourneyResult
from portal_worker.journeys import vidros_api as API
from portal_worker.journeys import vidros_estado as ST
from portal_worker.journeys import vidros_questionario as QZ
from portal_worker.journeys.vidros_sessao import SessaoVidros

logger = logging.getLogger(__name__)


def api_first_habilitado() -> bool:
    """A flag nasce DESLIGADA. So um `true`/`1` explicito liga."""
    return str(os.getenv("PORTAL_VIDROS_API_FIRST", "") or "").strip().lower() in ("1", "true", "yes", "on")


def _guard_do(params: Dict[str, Any]):
    """O guard da SPEC-073, ou um local equivalente em teste offline."""
    rt = params.get("_runtime")
    g = getattr(rt, "guard", None)
    if g is not None:
        return g
    from portal_worker.guardrails import PortalActionGuard

    return PortalActionGuard(material_liberado=bool(params.get("confirm")))


async def _checkpoint(params: Dict[str, Any], patch: Dict[str, Any]) -> None:
    rt = params.get("_runtime")
    if rt is not None and hasattr(rt, "checkpoint"):
        await rt.checkpoint(patch)


async def abrir_atendimento_api(page, params: Dict[str, Any],
                                evidence: Dict[str, Any]) -> Optional[JourneyResult]:
    """O fluxo API-first até a fronteira B. `None` = devolve ao caminho DOM.

    Devolver `None` é uma resposta legítima e frequente: qualquer coisa que a
    API não resolva com certeza cai para o navegador, que continua sendo a
    autoridade de último recurso.
    """
    estado = ST.EstadoDoAtendimento()
    sessao = SessaoVidros(page=page)
    guard = _guard_do(params)
    # A journey NOMEIA a única ação material que espera — SPEC-073.
    guard.acao_material_esperada = ST.FRONTEIRA_ABRIR

    seguradora = str(params.get("_seguradora_slug") or "").strip().upper()
    cpf = str(params.get("cpf_cnpj") or "").strip()
    placa = str(params.get("placa") or "").strip().upper()
    data = str(params.get("_data_iso") or "").strip()
    if not (seguradora and cpf and placa and data):
        evidence["api_first"] = {"usado": False,
                                 "motivo": "faltam dados para o preflight"}
        return None

    # ---- PREFLIGHT — read-only, e o único portão para a fronteira A --------
    tipo = API.tipo_atendimento_para(seguradora,
                                     (params.get("dano") or {}).get("peca"))
    r = await sessao.buscar_apolice(seguradora=seguradora, cpf_cnpj=cpf,
                                    placa=placa, data_sinistro=data,
                                    tipo_atendimento=tipo)
    veredito = API.classificar_preflight(r.get("status") or 0, r.get("json"))
    evidence["preflight"] = {k: v for k, v in veredito.items()
                             if k != "mensagem_portal"}
    evidence["vidros_estado"] = estado.para_evidencia()

    if veredito["estado"] == API.COVERAGE_ABSENT:
        # 📊 Detectado ANTES de qualquer escrita. Nenhum atendimento nasceu, e
        # nenhum vai nascer — repetir com outra cobertura seria adivinhar.
        return JourneyResult(
            status="needs_human",
            captured={"stage": "coverage_absent", "escopo": veredito.get("escopo", ""),
                      "business_state": ST.PRE_PROTOCOLO},
            message=("a apolice nao tem a cobertura necessaria para este item "
                     f"({veredito.get('escopo') or 'cobertura nao contratada'}). "
                     "Nenhum atendimento foi aberto."))

    if not veredito["pode_escrever"]:
        # policy_not_found · policy_ambiguous · regra desconhecida · erro.
        # Nenhum deles autoriza criar. Cai para o DOM, que sabe pedir dados
        # adicionais ao segurado nas telas que a API não expõe.
        evidence["api_first"] = {"usado": False,
                                 "motivo": f"preflight={veredito['estado']}"}
        return None

    # ---- FRONTEIRA A — a partir daqui existe registro na seguradora --------
    from portal_worker.guardrails import AcaoBloqueada, MATERIAL_SIDE_EFFECT

    corpo = {
        "Seguradora": seguradora,
        "NumeroDaApolice": str((r.get("json") or {}).get("NumeroDaApolice") or ""),
        "DataSinistro": data,
        "PlacaInformada": placa,
        "SufixoChassi": None,
        "CpfCnpjSegurado": cpf,
        "TipoAtendimento": tipo,
    }
    try:
        await guard.before(action=ST.FRONTEIRA_ABRIR,
                           action_class=MATERIAL_SIDE_EFFECT,
                           details={"idempotency_key":
                                    str(params.get("_idempotency_key") or "")},
                           origem="journey")
    except AcaoBloqueada as e:
        # `confirm=false` chega aqui. É a trava funcionando, não uma falha.
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "pronto_para_abrir", "business_state": ST.PRE_PROTOCOLO},
            message=("tudo conferido e a apolice tem cobertura — falta a "
                     f"autorizacao para abrir o pedido ({e})"))

    ra = await sessao.criar_atendimento(corpo)
    if not ra.get("ok"):
        # 🔴 A chamada saiu e não sabemos se o servidor a processou. Este é o
        # `maybe_committed`, e é o estado que existe para impedir o retry.
        estado.transitar(ST.DESCONHECIDO,
                         motivo=f"POST /atendimentos devolveu {ra.get('status')}")
        await guard.incerto(motivo="POST /atendimentos sem resposta de sucesso")
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "maybe_committed", "business_state": ST.DESCONHECIDO},
            message=("a chamada que cria o atendimento saiu e nao consegui "
                     "confirmar o resultado. NAO reexecute: consulte antes."))

    dados = ra.get("json") or {}
    protocolo = str(dados.get("NumeroProtocolo") or "")
    estado.transitar(ST.PROTOCOLO_CRIADO, motivo="POST /atendimentos 200",
                     numero_protocolo=protocolo)
    await guard.submetido(receipt=protocolo)
    # Grava AGORA, antes do próximo passo. Se cair daqui em diante, o recovery
    # precisa saber que já existe registro.
    evidence["vidros_estado"] = estado.para_evidencia()
    await _checkpoint(params, {"vidros_estado": estado.para_evidencia()})

    # ---- questionário: LEITURA, entre as duas fronteiras -------------------
    resultado = await QZ.rodar_questionario(
        sessao,
        respostas_do_segurado=dict(params.get("especificos") or {}),
        relato=str((params.get("dano") or {}).get("descricao") or ""))
    evidence["questionario"] = resultado.para_evidencia()

    if not resultado.completo:
        # O pedido existe (fronteira A já passou), mas falta dado para
        # materializar. O segurado precisa responder — e o número já é dele.
        estado.transitar(ST.PROTOCOLO_CRIADO, motivo=resultado.motivo)
        evidence["vidros_estado"] = estado.para_evidencia()
        pendente = resultado.pergunta_pendente
        return JourneyResult(
            status="needs_human",
            captured={"stage": "questionario_incompleto",
                      "business_state": ST.PROTOCOLO_CRIADO,
                      "pergunta": pendente.texto if pendente else "",
                      "opcoes": pendente.textos_das_opcoes if pendente else []},
            message=("o pedido foi aberto e o questionario parou: "
                     + resultado.motivo))

    # ---- FRONTEIRA B — materializa o CodigoAtendimento ---------------------
    guard.acao_material_esperada = ST.FRONTEIRA_MATERIALIZAR
    try:
        await guard.before(action=ST.FRONTEIRA_MATERIALIZAR,
                           action_class=MATERIAL_SIDE_EFFECT, origem="journey")
    except AcaoBloqueada as e:
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "pronto_para_materializar",
                      "business_state": ST.PROTOCOLO_CRIADO},
            message=f"questionario completo, falta autorizacao para gravar ({e})")

    rq = await sessao.gravar_questionario(resultado.respostas)
    if not rq.get("ok"):
        estado.transitar(ST.DESCONHECIDO,
                         motivo=f"POST /questionarios devolveu {rq.get('status')}")
        await guard.incerto(motivo="POST /questionarios sem sucesso")
        evidence["vidros_estado"] = estado.para_evidencia()
        return JourneyResult(
            status="needs_human",
            captured={"stage": "maybe_committed", "business_state": ST.DESCONHECIDO},
            message="gravei o questionario e nao confirmei. NAO reexecute.")

    # ---- confirma no read model, que é a única prova autoritativa ----------
    rg = await sessao.ler_atendimento()
    agregado = rg.get("json") or {}
    estado = ST.ler_estado_do_agregado(agregado, tinha_protocolo=bool(protocolo))
    estado.numero_protocolo = protocolo

    franquia = API.descricao_da_franquia(agregado)
    vistoria = API.vistoria_do_atendimento(agregado)

    if estado.codigo_atendimento:
        await guard.confirmado(receipt=estado.codigo_atendimento)
        # 📊 O número que a tela mostra e que o segurado anota é este.
        evidence["protocolo"] = estado.codigo_atendimento
    if franquia.get("tem"):
        evidence["franquia"] = franquia["itens"][0].get("valor", "")
    if vistoria.get("tem_link"):
        evidence["link_vistoria"] = vistoria["link"]

    # 99%: o pedido existe e falta a escolha do segurado. Não é falha, e o
    # browser NÃO fica pendurado esperando — a continuação é outra execução.
    estado.transitar(ST.AGUARDANDO_ESCOLHA,
                     motivo="pedido materializado; falta escolha de loja/domicilio")
    evidence["vidros_estado"] = estado.para_evidencia()
    evidence["api_first"] = {"usado": True, **sessao.resumo_para_evidencia()}
    await _checkpoint(params, {"vidros_estado": estado.para_evidencia()})

    return JourneyResult(
        status="done",
        captured={"business_state": estado.estado,
                  "protocolo": estado.codigo_atendimento,
                  "franquia": (franquia.get("itens") or [{}])[0].get("valor", ""),
                  "link_vistoria": vistoria.get("link", ""),
                  "customer_choice_needed": True},
        message=("atendimento aberto"
                 + (f" — n {estado.codigo_atendimento}" if estado.codigo_atendimento else "")
                 + ". Falta o segurado escolher loja ou domicilio."))
