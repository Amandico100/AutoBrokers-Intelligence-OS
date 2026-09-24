# -*- coding: utf-8 -*-
"""A CONTINUAÇÃO de um atendimento de vidros que JÁ EXISTE — EXTRA-001.10.1.

O que ela é
===========
Uma journey curta que RETOMA um pedido aberto por `abrir_atendimento_api`,
com o token do próprio portal guardado cifrado em `evidence["continuacao"]`
do job de origem (A1). 📊 É o desenho do portal, não uma invenção: o SPA
"continua" um atendimento voltando com o token na URL (`#/yelum/passoN/<token>`,
5 URLs no HAR LATERAL; laudo §7a) — e não existe endpoint que devolva token de
atendimento existente (laudo §7c).

O que ela NÃO é
===============
⛔ Não é um segundo motor (CLAUDE.md §5). Tudo o que fala com o portal — fases,
desfecho, agenda, ramo 7 — mora em `vidros_apifirst`, e é o MESMO código da
abertura. Aqui só existem: decifrar a sessão, ler o agregado, decidir a
operação pelo ESTADO REAL e chamar as fases.

⛔ Nunca `POST /atendimentos`: a `SessaoVidros` em `modo_continuacao` recusa sem
tocar a rede (G3). Renovar o token criando outro pedido é exatamente o erro
que a RFC 6750 manda não cometer: 401 é desfecho LEGÍVEL (`sessao_expirada`).

O contrato de entrada (C → A)
=============================
`params` = os do job de origem + `params["_continuacao"]`:

    {"job_origem": uuid, "operacao": "agendar"|"responder"|"reler"|"vistoria",
     "escolha": {"loja": "<CodigoCliente>", "dia": "DD/MM", "horario": "HH:MM"},
     "respostas": {<slots novos>},
     "sessao": <evidence["continuacao"] do job de origem, COM sessao_cifrada>,
     "desfecho_anterior": <evidence["desfecho"] de origem ou None>}
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from portal_worker.journeys import JourneyResult
from portal_worker.journeys import vidros_api as API
from portal_worker.journeys import vidros_apifirst as AF
from portal_worker.journeys import vidros_estado as ST
from portal_worker.journeys.vidros_sessao import SessaoVidros

logger = logging.getLogger(__name__)

OPERACOES = ("agendar", "responder", "reler", "vistoria")

# Os slots que a conversa traz e o lugar deles no contrato A↔C da abertura.
_SLOTS_DO_DANO = ("peca", "como", "pecas_lataria", "descricao", "onde")


def mesclar_respostas(params: Dict[str, Any], respostas: Any) -> Dict[str, Any]:
    """Os params de origem com as respostas NOVAS por cima — no mesmo contrato.

    `peca`/`como`/`pecas_lataria` → `dano` · `cidade_servico` → `local` · o
    resto (`aceita_reparo`, `pergunta_N`, `preferencia_agenda`,
    `preferencia_vistoria`…) → `especificos`, que é onde as fases já procuram.
    """
    novo = dict(params)
    novo["dano"] = dict(params.get("dano") or {})
    novo["local"] = dict(params.get("local") or {})
    novo["especificos"] = dict(params.get("especificos") or {})
    for chave, valor in (respostas or {}).items() if isinstance(respostas, dict) else []:
        if valor in (None, "", [], {}):
            continue
        if chave in _SLOTS_DO_DANO:
            novo["dano"][chave] = valor
        elif chave == "cidade_servico":
            novo["local"]["cidade_servico"] = _cidade(valor)
        else:
            novo["especificos"][chave] = valor
    return novo


def _cidade(valor: Any) -> Dict[str, str]:
    """`{"uf","cidade"}` como a abertura espera. Texto `"Cidade/UF"` também serve."""
    if isinstance(valor, dict):
        return {"uf": str(valor.get("uf") or "").strip(),
                "cidade": str(valor.get("cidade") or "").strip()}
    txt = str(valor or "").strip()
    for sep in ("/", " - ", "-", ","):
        if sep in txt:
            cidade, uf = txt.rsplit(sep, 1)
            if len(uf.strip()) == 2:
                return {"uf": uf.strip().upper(), "cidade": cidade.strip()}
    return {"uf": "", "cidade": txt}


def _sem_sessao(evidence: Dict[str, Any], sessao_info: Dict[str, Any], *,
                stage: str, mensagem: str) -> JourneyResult:
    """Parada ANTES de falar com o portal: nada saiu, e a sessão não serve."""
    evidence["continuacao"] = {
        **{k: v for k, v in (sessao_info or {}).items() if k != "sessao_cifrada"},
        "sessao_cifrada": "", "possivel": False, "etapa": "",
        "acao_esperada": "", "motivo": mensagem[:300],
    }
    return JourneyResult(status="needs_human",
                         captured={"stage": stage,
                                   "protocolo": str((sessao_info or {}).get("codigo_atendimento")
                                                    or (sessao_info or {}).get("protocolo") or "")},
                         message=mensagem)


async def continuar_atendimento(page, params: Dict[str, Any],
                                evidence: Dict[str, Any]) -> JourneyResult:
    """A journey registrada como `vidros_lanternas.continuar_atendimento`."""
    cont = dict(params.get("_continuacao") or {})
    operacao = str(cont.get("operacao") or "").strip().lower()
    sessao_info = dict(cont.get("sessao") or {})
    evidence["continuacao_pedida"] = {"operacao": operacao,
                                      "job_origem": str(cont.get("job_origem") or "")}

    # ---- 1. a sessão: decifrar (G4) ---------------------------------------
    cifrada = str(sessao_info.get("sessao_cifrada") or "")
    if not cifrada or not sessao_info.get("sessao_guardada", True):
        return _sem_sessao(evidence, sessao_info, stage="sessao_indisponivel",
                           mensagem="nao ha sessao guardada deste pedido: a "
                                    "continuacao automatica e impossivel. A equipe "
                                    "continua pelo numero do atendimento.")
    try:
        from portal_worker import vault

        token = vault.decrypt(cifrada)
    except Exception as exc:  # noqa: BLE001
        # ⛔ Nem a cifra nem a mensagem da exceção vão para evidence/log.
        logger.warning("vidros: continuacao sem sessao decifravel (%s)", type(exc).__name__)
        return _sem_sessao(evidence, sessao_info, stage="sessao_indisponivel",
                           mensagem="a sessao guardada deste pedido nao pode ser "
                                    "aberta pelo cofre do worker: a continuacao "
                                    "automatica e impossivel.")
    if operacao not in OPERACOES:
        return _sem_sessao(evidence, sessao_info, stage="operacao_desconhecida",
                           mensagem=f"operacao de continuacao desconhecida: {operacao!r}")

    # ---- 2. a sessão retomada: NUNCA cria pedido (G3) ----------------------
    sessao = SessaoVidros(page=page, token=token, modo_continuacao=True)
    del token
    guard = AF._guard_do(params)
    p = mesclar_respostas(params, cont.get("respostas"))
    estado = ST.EstadoDoAtendimento()
    ex = AF.execucao_de(p, evidence, sessao=sessao, guard=guard, estado=estado)
    ex.seguradora = str(sessao_info.get("seguradora") or "")
    ex.protocolo = str(sessao_info.get("protocolo") or "")
    ex.continuacao = dict(sessao_info)

    # ---- 3. o "consultar": o ESTADO REAL, antes de qualquer escrita (G4) ----
    rg = await sessao.ler_atendimento()
    status = int(rg.get("status") or 0)
    if status in (401, 403):
        # 📊 B0.8: o token de 21/09 22:09Z → 401 em 23/09 23:40Z. Desfecho
        # legível, nunca retry cego — e nunca um POST para "renovar".
        evidence["api_first"] = {"usado": True, "parou_em": "sessao_expirada",
                                 **sessao.resumo_para_evidencia()}
        return _sem_sessao(evidence, sessao_info, stage="sessao_expirada",
                           mensagem="o portal recusou a sessao guardada (expirou). "
                                    "O pedido continua existindo: a equipe segue "
                                    "pelo numero do atendimento. Nada foi gravado.")
    agregado = rg.get("json") if rg.get("ok") and isinstance(rg.get("json"), dict) else None
    if agregado is None:
        AF._tela_desconhecida(evidence, onde=API.EP_ATENDIMENTOS, resposta=rg)
        return AF._parar(ex, "leitura_falhou",
                         "nao consegui ler o atendimento no portal agora. Nada "
                         "foi gravado; vale tentar de novo.")
    ex.agregado = agregado
    ex.estado = ST.ler_estado_do_agregado(agregado, tinha_protocolo=bool(ex.protocolo))
    ex.estado.numero_protocolo = ex.protocolo
    codigo = ex.estado.codigo_atendimento
    # 🔴 O job de continuação também carrega a prova do pedido: se ele falhar,
    # o worker não pode concluir que "nada aconteceu" e liberar um retry.
    if codigo or ex.protocolo:
        evidence["protocolo"] = codigo or ex.protocolo

    esperado = str(sessao_info.get("codigo_atendimento") or "").strip()
    if esperado and codigo and esperado != codigo:
        # A sessão abriu OUTRO atendimento que não o deste pedido. Não se age.
        return _sem_sessao(evidence, sessao_info, stage="sessao_de_outro_atendimento",
                           mensagem="a sessao guardada aponta para outro atendimento. "
                                    "Nada foi gravado.")
    if ex.estado.estado == ST.CANCELADO:
        return _sem_sessao(evidence, sessao_info, stage="atendimento_cancelado",
                           mensagem="o portal diz que este atendimento foi cancelado. "
                                    "Nada foi gravado.")

    # ---- 4. JÁ AGENDADO? conclui LENDO (JUIZ B1 / RED B2c) -----------------
    # 🔴 Qualquer operação: o agregado que acabamos de ler diz "Agendado para"
    # ⇒ o desfecho é esse, e nenhum `POST /agendamentos` sai — nem com outra
    # escolha, nem com uma preferência herdada, nem numa releitura.
    ja = await AF.concluir_se_ja_agendado(ex)
    if ja is not None:
        return ja

    # ---- 5. a operação, decidida pelo estado REAL -------------------------
    escolha = dict(cont.get("escolha") or {})
    # 🔴 RED B2(b): a releitura de um job `agendar` HERDA a escolha explícita
    # dele (`montar_job_de_continuacao`) — é isso que cumpre o "já estou
    # tentando de novo" dito ao segurado. Só a escolha que ELE fez; nada mais.
    if operacao == "agendar" or (operacao == "reler" and escolha):
        if not codigo:
            return AF._parar(ex, "desfecho_ilegivel",
                             "o atendimento ainda nao tem numero no portal; nao ha "
                             "agenda a escolher. Nada foi gravado.")
        return await AF.agendar_escolha(ex, escolha)

    if codigo:
        # responder · reler · vistoria sobre pedido materializado: o desfecho
        # de HOJE (opções → agregado → roteador → agenda/ramo 7/conclusão).
        # 🔴 RED B2(a): a RELEITURA nunca agenda pela preferência — ela lê.
        return await AF.fase_desfecho(ex, agendar_por_preferencia=operacao != "reler")

    if sessao_info.get("incerto"):
        # 🔴 A origem parou em `maybe_committed` e o agregado não prova que a
        # escrita pegou. Repetir seria apostar num segundo efeito.
        return AF._parar(ex, "reconciliar_antes",
                         "a ultima escrita deste pedido ficou sem confirmacao e o "
                         "portal ainda nao mostra o numero. Nada foi repetido: a "
                         "equipe confere antes.")
    etapa = str(sessao_info.get("etapa") or ST.ETAPA_PECA)
    return await AF.rodar_fases(ex, a_partir=etapa,
                                agendar_por_preferencia=operacao != "reler")
