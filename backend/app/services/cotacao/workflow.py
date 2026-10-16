# -*- coding: utf-8 -*-
"""O Work Run `cotacao.chat` — SPEC-132-B (B1 · D-132B-04: a resposta volta na MESMA conversa).

    abrir(db, ...)        o run nasce no disparo (e no ajuste), com `conversation_id` (a coluna da 20260826_02, FK
                          COMPOSTA com a corretora — o banco recusa a conversa de outra casa)
    acompanhar            porta.consultar a cada `INTERVALO_S` até o quadro de todos os cálculos fechar ou o corte de
                          💭 `TETO_S` (6 min) — segue com o que chegou
    entregar              publicar_cotacao (B2) → mensagem_de_cotacao (B2) → `messages` (assistant) na MESMA conversa:
                          "Pronto: N seguradoras responderam." + 3 linhas + o link + a mensagem para o cliente.
                          Nenhuma seguradora com preço → a frase honesta. O run que desiste → a frase honesta.

Modelado no `canal.cotacao` (`canal/workflows.py`: o MESMO `executar_passo`, a MESMA porta), sem duplicar motor
(CLAUDE.md §5): a porta calcula, o motor do portal-worker roda, a B2 publica — aqui só se ESPERA e se ESCREVE.

🔴 IDEMPOTENTE: a mensagem tem `id` determinístico (uuid5 do run + o tipo) — rodar 2× (retomada, Reprocessar, o gancho
   de desistência depois da entrega) não grava 2 mensagens. A etapa `entregar` que terminou não repete (`guardar`).
🔴 MULTI-TENANT: o run lê a conversa com `company_id` e só escreve nela se ela for DESTA corretora (§7). `messages` não
   tem `company_id`: a coerência é a conversa conferida antes de cada escrita.
⛔ O `input_payload` vai EM CLARO para `work_runs`: ids, a situação, a seguradora atual e o RESUMO do cliente que a aba
   Cotações lista (B4 · `resumo_do_cliente`): o PRIMEIRO nome, o documento MASCARADO (≤ 2 dígitos, a regra da
   renovação), o carro ("Onix 2022") e a placa. Nunca o CPF, o nome inteiro, o telefone, o e-mail.
🔴 O `result_payload` (B4 · `Concluido`): o link, o token, o artefato, a mensagem para o cliente (já sem documento) e
   o resumo das opções — é o que a aba Cotações (B3) mostra sem republicar.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Mapping, Optional

from app.services.work.workflows import _runs_mod, executar_passo, registrar_workflow

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "cotacao.chat"
OUTCOME_TYPE = "cotacao.chat"
INTERVALO_S = 5
#: 💭 o corte: 📊 LAUDO-I1 p90 406 s (§2.1 C7) — 6 min pega quase tudo e não deixa o corretor esperando uma madrugada
TETO_S = 6 * 60
TERMINAIS = frozenset({"fechado", "falhou", "incerto", "cancelado", "expirado"})
#: o espaço do uuid5 das mensagens deste workflow (fixo: é ele que faz a 2ª escrita cair na mesma linha)
_ESPACO = uuid.uuid5(uuid.NAMESPACE_URL, "autobrokers:cotacao.chat:mensagem")

_dormir = asyncio.sleep   # os testes trocam

#: SPEC-129-D (conserto K3) — a VIDA (= `contrato.RAMO_VIDA`). A entrega de vida responde NO CHAT, ao corretor, sem
#: publicar a página do cliente: a apresentação de vida é da 130-C (D-129D-10) e nesta SPEC nada de vida vai ao cliente.
RAMO_VIDA = 91
NOTA_DA_VIDA = ("Os valores são para você conferir: a página de vida para o cliente ainda não existe — mande os "
                "valores ao cliente você mesmo, ou abra o cálculo no Agger.")


async def _opcoes_de_vida_sem_pagina(db: Any, company_id: str, pedido_id: str) -> Optional[List[Dict[str, Any]]]:
    """As opções da cotação de VIDA para a tabela do chat — o MESMO comparador da página (`proposta.montar_proposta` →
    `resumo_da_cotacao`), SEM publicar nada (o modelo é só lido). Falhou → None (a frase honesta com o total)."""
    try:
        from app.services.multicalculo.proposta import montar_proposta, resumo_da_cotacao

        modelo = await montar_proposta(company_id, pedido_id, "novo_sem_apolice", None, None, db=db)
        return list(resumo_da_cotacao(modelo).get("opcoes") or [])
    except Exception as exc:  # noqa: BLE001 — o resultado existe; a tabela é que não saiu
        logger.warning("[COTACAO] as opções de vida não foram montadas (%s)", type(exc).__name__)
        return None


def _cliente(db: Any) -> Any:
    return getattr(db, "client", db)


def _dados(resp: Any) -> List[Dict[str, Any]]:
    return list(getattr(resp, "data", None) or [])


def _porta(db: Any) -> Any:
    from app.services.multicalculo.porta import MulticalculoProvider
    from app.services.multicalculo.repositorio import RepositorioMulticalculo

    return MulticalculoProvider(RepositorioMulticalculo(_cliente(db)))


# =====================================================================================================================
# a conversa e a mensagem
# =====================================================================================================================
def conversa_da_corretora(db: Any, company_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    """A conversa SE for desta corretora (filtro no banco E reconferido aqui — CLAUDE.md §7). Senão None."""
    if not conversation_id or not company_id:
        return None
    linhas = _dados(_cliente(db).table("conversations").select("id, company_id, user_id, session_id")
                    .eq("id", str(conversation_id)).eq("company_id", str(company_id)).limit(1).execute())
    linhas = [c for c in linhas if str(c.get("id")) == str(conversation_id)
              and str(c.get("company_id")) == str(company_id)]
    return linhas[0] if linhas else None


def id_da_mensagem(run_id: str, tipo: str) -> str:
    return str(uuid.uuid5(_ESPACO, f"{run_id}:{tipo}"))


def gravar_mensagem(db: Any, *, company_id: str, conversation_id: str, run_id: str, tipo: str, texto: str,
                    payload: Optional[Mapping[str, Any]] = None) -> bool:
    """A mensagem do ASSISTENTE na conversa — como o chat grava a dele (`chat.py`: role assistant, type text) e com o
    `payload.cotacao` que a aba Cotações e a bolha podem ler. Devolve True se ESCREVEU agora; False se já estava (a 2ª
    escrita do mesmo run+tipo) ou se a conversa não é desta corretora (nada é escrito)."""
    cli = _cliente(db)
    if conversa_da_corretora(cli, company_id, conversation_id) is None:
        logger.warning("[COTACAO] a conversa do run não é desta corretora (ou sumiu) — nada escrito")
        return False
    mid = id_da_mensagem(run_id, tipo)
    ja = _dados(cli.table("messages").select("id, conversation_id").eq("id", mid)
                .eq("conversation_id", str(conversation_id)).limit(1).execute())
    if ja:
        return False
    linha = {"id": mid, "conversation_id": str(conversation_id), "role": "assistant", "content": texto,
             "type": "text", "payload": {"cotacao": {"tipo": tipo, "work_run_id": str(run_id), **dict(payload or {})}}}
    try:
        cli.table("messages").insert(linha).execute()
    except Exception as exc:  # noqa: BLE001 — 23505: a outra escrita chegou primeiro (é o sistema funcionando)
        if "23505" in str(exc) or "duplicate" in str(exc).lower():
            return False
        raise
    try:
        from datetime import datetime, timezone

        cli.table("conversations").update({
            "last_message_preview": str(texto or "")[:100],
            "last_message_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", str(conversation_id)).eq("company_id", str(company_id)).execute()
    except Exception as exc:  # noqa: BLE001 — a prévia é cortesia; a mensagem já está lá
        logger.warning("[COTACAO] prévia da conversa não atualizada (%s)", type(exc).__name__)
    # SPEC-132-C C3 — a conversa nasceu no WhatsApp do corretor? a mesma mensagem volta por lá (nunca levanta)
    from app.services.atalho.envio import avisar_pelo_atalho_sem_esperar
    avisar_pelo_atalho_sem_esperar(cli, company_id=company_id, conversation_id=conversation_id, texto_markdown=texto)
    return True


#: as chaves do resumo do cliente no `input_payload` (o que a aba Cotações — `api/cotacoes.do_run` — lê)
CHAVES_DO_CLIENTE = ("cliente_nome_curto", "documento_mascarado", "risco", "placa")
_PLACA = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")


def resumo_do_cliente(campos: Optional[Mapping[str, Any]], descricao: Any = None) -> Dict[str, str]:
    """Do pedido confirmado (`{grupo: {campo: valor}}`), SÓ o que pode ir em claro ao `work_runs`: o primeiro nome, o
    documento mascarado, o carro e a placa. Campo que não veio não entra (a aba cai no pedido cifrado)."""
    from app.services.multicalculo.renovacao import mascarar_documento, primeiro_nome

    campos = campos if isinstance(campos, Mapping) else {}
    seg = campos.get("segurado") if isinstance(campos.get("segurado"), Mapping) else {}
    vei = campos.get("veiculo") if isinstance(campos.get("veiculo"), Mapping) else {}
    saida: Dict[str, str] = {}
    nome = primeiro_nome(seg.get("nome"))
    if nome:
        saida["cliente_nome_curto"] = nome
    doc = mascarar_documento(seg.get("cpf_cnpj"))
    if doc and sum(ch.isdigit() for ch in doc) <= 2:
        saida["documento_mascarado"] = doc
    placa = str(vei.get("placa") or "").strip().upper().replace("-", "")
    if _PLACA.match(placa):
        saida["placa"] = placa
    from app.services.cotacao.resposta import sem_documento_inteiro

    # 🔴 conserto juiz P2 / RT P-RT-1: o "risco" vai EM CLARO ao `work_runs` e à aba — passa pela MÁSCARA (CPF/CNPJ
    #    pontuado, colado ou com espaços) e, por cinto, nenhuma sequência colada de 6+ dígitos sobra ("Onix 2021 2022"
    #    fica: é ano/modelo, não documento)
    risco = sem_documento_inteiro(str(descricao or vei.get("modelo") or "").strip())
    if risco and not re.search(r"\d{6,}", risco):
        saida["risco"] = risco[:60]
    elif "placa" in saida:
        saida["risco"] = f"Placa {saida['placa']}"
    return saida


def _cliente_do_run_anterior(db: Any, company_id: str, pedido_id: str) -> Dict[str, str]:
    """O resumo do cliente do run de cotação anterior do MESMO pedido (o recálculo não tem a confirmação)."""
    try:
        linhas = _dados(_cliente(db).table("work_runs").select("id, company_id, workflow_key, input_payload")
                        .eq("company_id", str(company_id)).eq("workflow_key", WORKFLOW_KEY)
                        .eq("source_id", str(pedido_id)).execute())
    except Exception as exc:  # noqa: BLE001 — sem o anterior, a aba lê do pedido cifrado
        logger.info("[COTACAO] run anterior ilegível (%s)", type(exc).__name__)
        return {}
    for r in linhas:
        ent = r.get("input_payload") if isinstance(r.get("input_payload"), Mapping) else {}
        if str(r.get("company_id")) == str(company_id) and str(ent.get("pedido_id") or "") == str(pedido_id):
            achado = {k: ent[k] for k in CHAVES_DO_CLIENTE if isinstance(ent.get(k), str) and ent[k].strip()}
            if achado:
                return achado
    return {}


def _apolice_do_run_anterior(db: Any, company_id: str, pedido_id: str) -> Optional[Dict[str, Any]]:
    """A `apolice_atual` do run de DISPARO do mesmo pedido (o que não é recálculo), desta corretora."""
    try:
        linhas = _dados(_cliente(db).table("work_runs").select("id, company_id, workflow_key, input_payload")
                        .eq("company_id", str(company_id)).eq("workflow_key", WORKFLOW_KEY)
                        .eq("source_id", str(pedido_id)).execute())
    except Exception as exc:  # noqa: BLE001
        logger.info("[COTACAO] run anterior ilegível (%s)", type(exc).__name__)
        return None
    for r in linhas:
        ent = r.get("input_payload") if isinstance(r.get("input_payload"), Mapping) else {}
        if (str(r.get("company_id")) == str(company_id) and str(ent.get("pedido_id") or "") == str(pedido_id)
                and not ent.get("ajuste_calculo_id") and isinstance(ent.get("apolice_atual"), Mapping)):
            return dict(ent["apolice_atual"])
    return None


def contas_do_pedido(db: Any, company_id: str, pedido_id: str) -> List[Dict[str, Any]]:
    """Em qual conta cada cálculo do pedido TEM de sair (o que a porta gravou da decisão do `qual_agger`)."""
    linhas = _dados(_cliente(db).table("multicalculo_calculos")
                    .select("id, pedido_id, solicitante_company_id, company_id, opcao, conta_regra, conta_motivo, "
                            "conta_exigida_id, criado_em, origem_calculo_id, negocio_ref, status")
                    .eq("pedido_id", str(pedido_id)).eq("solicitante_company_id", str(company_id)).execute())
    return [c for c in linhas if str(c.get("solicitante_company_id")) == str(company_id)]


# =====================================================================================================================
# abrir o run
# =====================================================================================================================
def abrir(db: Any, *, company_id: str, user_id: str, conversation_id: str, pedido_id: str,
          situacao: str = "novo_sem_apolice", apolice_atual: Optional[Mapping[str, Any]] = None,
          ajuste: Optional[str] = None, ajuste_calculo_id: Optional[str] = None,
          cliente: Optional[Mapping[str, Any]] = None, ramo: Optional[int] = None) -> str:
    """O run (`WorkRunService.criar`, a RPC com o outbox) + a `conversation_id` na linha. Devolve o `run_id`.
    `cliente`: o `resumo_do_cliente` (o disparo o tem); sem ele (o recálculo), o do run anterior do mesmo pedido."""
    from app.services.work.runs import WorkRunService

    cli = _cliente(db)
    chave = f"{WORKFLOW_KEY}:{pedido_id}" + (f":ajuste:{ajuste_calculo_id}" if ajuste_calculo_id else "")
    entrada: Dict[str, Any] = {"pedido_id": str(pedido_id), "conversation_id": str(conversation_id),
                               "solicitante_user_id": str(user_id), "situacao": situacao}
    if ramo is not None and int(ramo) == RAMO_VIDA:
        entrada["ramo"] = RAMO_VIDA     # SPEC-129-D (K3): só a vida marca o ramo — o run do auto/RE não muda um byte
    if ajuste and not apolice_atual:
        # o recálculo é a MESMA cotação: a apólice lida no disparo (e a situação) seguem com ele — sem isso a página
        # depois do ajuste perderia o "Igual à sua atual" e a economia que a de antes mostrava
        anterior = _apolice_do_run_anterior(cli, company_id, pedido_id)
        if anterior:
            apolice_atual, situacao = anterior, "novo_com_apolice"
            entrada["situacao"] = situacao
    if apolice_atual:
        entrada["apolice_atual"] = {k: apolice_atual[k] for k in ("seguradora", "premio_anual", "origem", "base")
                                    if k in apolice_atual}
    if ajuste:
        entrada.update({"ajuste": str(ajuste)[:80], "ajuste_calculo_id": str(ajuste_calculo_id or "")})
    do_cliente = dict(cliente) if cliente else _cliente_do_run_anterior(cli, company_id, pedido_id)
    entrada.update({k: str(do_cliente[k]) for k in CHAVES_DO_CLIENTE if do_cliente.get(k)})
    linha = WorkRunService(cli).criar(
        company_id=company_id, source_type="chat", outcome_type=OUTCOME_TYPE,
        outcome_title=("Cotação Rápida — recálculo pedido no chat" if ajuste else "Cotação Rápida — pedida no chat"),
        workflow_key=WORKFLOW_KEY, idempotency_key=chave, input_payload=entrada, requester_user_id=str(user_id),
        source_id=str(pedido_id), priority=40, risk_level="high")
    run_id = str((linha or {}).get("run_id") or (linha or {}).get("id") or "")
    if run_id:
        try:
            cli.table("work_runs").update({"conversation_id": str(conversation_id)}) \
                .eq("id", run_id).eq("company_id", str(company_id)).execute()
        except Exception as exc:  # noqa: BLE001 — a resposta usa o payload; a coluna é a junção da tela
            logger.warning("[COTACAO] conversation_id não gravado no run (%s)", type(exc).__name__)
    return run_id


# =====================================================================================================================
# a desistência
# =====================================================================================================================
def _payload_do_run(db: Any, run_id: str, company_id: str) -> Dict[str, Any]:
    r = _dados(_cliente(db).table("work_runs").select("id, company_id, input_payload").eq("id", run_id)
               .eq("company_id", company_id).limit(1).execute())
    return dict((r[0] if r else {}).get("input_payload") or {})


def avisar_que_nao_terminou(db: Any, company_id: str, run_id: str, payload: Optional[Mapping[str, Any]] = None
                            ) -> bool:
    """A frase honesta na conversa — UMA vez (id determinístico), e nunca depois da resposta pronta (se a entrega já
    gravou, o corretor já tem o resultado: o "não terminou" seria mentira)."""
    from app.services.cotacao.resposta import texto_nao_terminou

    try:
        payload = dict(payload or _payload_do_run(db, run_id, company_id))
        conversa = str(payload.get("conversation_id") or "")
        if not conversa:
            return False
        cli = _cliente(db)
        for tipo in ("pronta", "sem_resposta", "sem_publicar"):
            if _dados(cli.table("messages").select("id").eq("id", id_da_mensagem(run_id, tipo))
                      .eq("conversation_id", conversa).limit(1).execute()):
                return False
        return gravar_mensagem(cli, company_id=company_id, conversation_id=conversa, run_id=run_id,
                               tipo="nao_terminou", texto=texto_nao_terminou(),
                               payload={"pedido_id": payload.get("pedido_id"), "estado": "nao_terminou"})
    except Exception as exc:  # noqa: BLE001 — nunca levanta (o gancho é do Work OS)
        logger.warning("[COTACAO] aviso de 'não terminou' não gravado (%s)", type(exc).__name__)
        return False


def _cotacao_desistiu(db: Any, run: dict, motivo: str) -> None:
    """`ao_desistir(db, run, motivo)` — o Work OS desistiu (expirou ou efeito incerto). Síncrono, nunca levanta."""
    run_id, company_id = str((run or {}).get("id") or ""), str((run or {}).get("company_id") or "")
    if run_id and company_id:
        avisar_que_nao_terminou(db, company_id, run_id)
        logger.warning("[COTACAO] run %s desistiu (%s)", run_id[:8], str(motivo or "")[:60])


# =====================================================================================================================
# o workflow
# =====================================================================================================================
@registrar_workflow(WORKFLOW_KEY, idade_maxima_s=2 * 3600, ao_desistir=_cotacao_desistiu)
async def workflow_cotacao_chat(ctx: dict) -> Any:
    """Erro do próprio run (porta, publicação, banco) → a frase honesta na conversa ANTES de o erro subir ao worker.
    Efeito incerto / etapa não verificada são do worker (ele chama o gancho)."""
    _R = _runs_mod()
    try:
        return await _cotacao(ctx)
    except (_R.EfeitoIncerto, _R.EtapaNaoVerificada):
        raise
    except Exception as exc:  # noqa: BLE001
        await asyncio.to_thread(avisar_que_nao_terminou, ctx["db"], str(ctx["company_id"]), str(ctx["run_id"]),
                                ctx.get("payload") or {})
        logger.error("[COTACAO] o run falhou (%s)", type(exc).__name__)
        raise


async def _cotacao(ctx: dict) -> Any:
    from app.services.cotacao import resposta as RESP

    db = _cliente(ctx["db"])
    company_id, run_id = str(ctx["company_id"]), str(ctx["run_id"])
    payload = dict(ctx.get("payload") or {})
    pedido_id = str(payload.get("pedido_id") or "")
    conversa = str(payload.get("conversation_id") or "")
    pessoa = str(payload.get("solicitante_user_id") or "") or None
    ajuste = payload.get("ajuste") or None
    ajuste_calculo_id = str(payload.get("ajuste_calculo_id") or "") or None
    if not pedido_id or not conversa:
        raise ValueError("run da cotação sem pedido ou sem conversa")

    # ① acompanhar — só leitura
    async def _acompanhar() -> dict:
        porta = _porta(db)
        inicio = time.monotonic()
        while True:
            and_ = await porta.consultar(company_id=company_id, pedido_id=pedido_id)
            prontos = [e for e in and_.estados if e.get("status") in TERMINAIS or e.get("quadro_pronto_em")]
            acabou = bool(and_.estados) and len(prontos) == len(and_.estados)
            if acabou or time.monotonic() - inicio > TETO_S or ctx["cancelado"]():
                # 🔴 conserto juiz B1 / RT B-2: no RECÁLCULO contam só as seguradoras que responderam AO AJUSTE
                ofertas = ([o for o in and_.ofertas if str(o.get("calculo_id")) == ajuste_calculo_id]
                           if ajuste_calculo_id else and_.ofertas)
                n = RESP.seguradoras_que_responderam(ofertas)
                return {"situacao": "com_preco" if n else "sem_preco", "responderam": n,
                        "cortado": not acabou}
            await _dormir(INTERVALO_S)

    r1 = await executar_passo(ctx, step_key="acompanhar", ordinal=1, nome="Esperar as seguradoras responderem",
                              step_type="system", fn=_acompanhar, guardar=("situacao", "responderam", "cortado"))

    # ② entregar — publica (B2) e escreve a resposta na conversa (idempotente: o id da mensagem é fixo)
    produzido: Dict[str, Any] = {}

    async def _entregar() -> dict:
        contas = await asyncio.to_thread(contas_do_pedido, db, company_id, pedido_id)
        onde = RESP.onde_pelas_contas(contas)
        aviso = RESP.aviso_da_conta(onde)
        responderam = int((r1 or {}).get("responderam") or 0)
        if (r1 or {}).get("situacao") != "com_preco":
            escreveu = await asyncio.to_thread(
                gravar_mensagem, db, company_id=company_id, conversation_id=conversa, run_id=run_id,
                tipo="sem_resposta", texto=RESP.texto_sem_resposta(aviso=aviso, ajuste=ajuste),
                payload={"pedido_id": pedido_id, "estado": "sem_resposta"})
            return {"situacao": "sem_preco", "escreveu": bool(escreveu)}
        if str(payload.get("ramo") or "") == str(RAMO_VIDA):
            # SPEC-129-D (K3): a vida responde AQUI, ao corretor — a tabela do comparador, sem link e sem mensagem
            # para o cliente (D-129D-10). ⛔ Nada de fumante/renda/esporte nesta mensagem: só seguradora e preço.
            opcoes = await _opcoes_de_vida_sem_pagina(db, company_id, pedido_id)
            texto = (RESP.texto_pronto(responderam=responderam, opcoes=opcoes or [], link=None,
                                       mensagem_para_o_cliente=None, aviso_da_conta=aviso)
                     + ("" if opcoes else "\n\nOs valores de cada seguradora estão em Cotação Rápida → Cotações e no "
                                          "Agger.")
                     + f"\n\n{NOTA_DA_VIDA}")
            resumo_vida = {"opcoes": opcoes or []}
            produzido.update({"pedido_id": pedido_id, "url": None, "token": None, "artifact_id": None,
                              "mensagem": None, "resumo": resumo_vida})
            escreveu = await asyncio.to_thread(
                gravar_mensagem, db, company_id=company_id, conversation_id=conversa, run_id=run_id, tipo="pronta",
                texto=RESP.sem_documento_inteiro(texto),
                payload={"pedido_id": pedido_id, "estado": "pronta", "ramo": RAMO_VIDA, "resumo": resumo_vida})
            return {"situacao": "entregue", "artifact_id": None, "escreveu": bool(escreveu)}
        try:
            from app.services.multicalculo.proposta import publicar_cotacao

            # 🔴 conserto juiz B1 / RT B-2: o run do RECÁLCULO publica a página DEPOIS do ajuste (a opção ajustada
            #    com as ofertas dele) — o modelo muda, e com ele a tabela daqui e o link (versão nova)
            extra = {"ajuste_calculo_id": ajuste_calculo_id} if ajuste_calculo_id else {}
            pub = await publicar_cotacao(company_id, pedido_id, pessoa_user_id=pessoa,
                                         apolice_atual=payload.get("apolice_atual"), db=db,
                                         primeiro_nome=payload.get("cliente_nome_curto") or None, **extra)
        except Exception as exc:  # noqa: BLE001 — o resultado existe; a página é que não saiu
            logger.error("[COTACAO] a apresentação não foi publicada (%s)", type(exc).__name__)
            escreveu = await asyncio.to_thread(
                gravar_mensagem, db, company_id=company_id, conversation_id=conversa, run_id=run_id,
                tipo="sem_publicar", texto=RESP.texto_sem_publicar(responderam=responderam),
                payload={"pedido_id": pedido_id, "estado": "sem_publicar"})
            return {"situacao": "sem_publicar", "escreveu": bool(escreveu)}
        resumo = pub.get("resumo") if isinstance(pub.get("resumo"), Mapping) else {}
        msg: Mapping[str, Any] = {}
        try:
            from app.services.multicalculo.mensagem import mensagem_de_cotacao

            # 🔴 B4: a mensagem é montada do MODELO da página — o `resumo` não tem o que ela lê (com ele a função
            #    recusava "sem opção com preço" e o corretor ficava sem a mensagem para o cliente)
            msg = mensagem_de_cotacao(pub.get("modelo") if isinstance(pub.get("modelo"), Mapping) else pub,
                                      pub.get("url")) or {}
        except Exception as exc:  # noqa: BLE001 — sem o texto pronto, o link e a tabela ainda chegam
            logger.warning("[COTACAO] mensagem para o cliente indisponível (%s)", type(exc).__name__)
        texto = RESP.texto_pronto(responderam=responderam, opcoes=list(resumo.get("opcoes") or []),
                                  link=pub.get("url"), mensagem_para_o_cliente=msg.get("texto"),
                                  aviso_da_conta=aviso, ajuste=ajuste)
        mensagem = {"texto": RESP.sem_documento_inteiro(msg.get("texto") or ""),
                    "texto_curto": RESP.sem_documento_inteiro(msg.get("texto_curto") or "")}
        produzido.update({"pedido_id": pedido_id, "url": pub.get("url"), "token": pub.get("token"),
                          "artifact_id": str(pub.get("artifact_id") or "") or None,
                          "mensagem": mensagem if mensagem["texto"] else None, "resumo": dict(resumo)})
        escreveu = await asyncio.to_thread(
            gravar_mensagem, db, company_id=company_id, conversation_id=conversa, run_id=run_id, tipo="pronta",
            texto=texto, payload={"pedido_id": pedido_id, "estado": "pronta", "url": pub.get("url"),
                                  "token": pub.get("token"),
                                  "artifact_id": str(pub.get("artifact_id") or "") or None,
                                  "mensagem_para_o_cliente": mensagem["texto"],
                                  "texto_curto": mensagem["texto_curto"], "resumo": dict(resumo)})
        return {"situacao": "entregue", "artifact_id": str(pub.get("artifact_id") or "") or None,
                "escreveu": bool(escreveu)}

    r2 = await executar_passo(ctx, step_key="entregar", ordinal=2, nome="Publicar e responder na conversa",
                              step_type="tool", fn=_entregar, efeito="idempotente",
                              guardar=("situacao", "artifact_id", "escreveu"))
    situacao = (r2 or {}).get("situacao")
    _R = _runs_mod()
    if situacao == "entregue":
        if not produzido:                       # a retomada: a etapa já tinha entregue — o que ela gravou na conversa
            produzido.update(await asyncio.to_thread(_produzido_da_mensagem, db, conversa, run_id, pedido_id))
        return _R.Concluido(f"Cotação entregue na conversa: {(r1 or {}).get('responderam')} seguradora(s) "
                            "responderam.", {**produzido, "situacao": "entregue"})
    if situacao == "sem_publicar":
        return _R.Concluido("As seguradoras responderam, mas a apresentação não saiu; a conversa foi avisada.",
                            {"pedido_id": pedido_id, "situacao": "sem_publicar"})
    return _R.Concluido("Nenhuma seguradora respondeu com preço; a conversa foi avisada.",
                        {"pedido_id": pedido_id, "situacao": "sem_preco"})


def _produzido_da_mensagem(db: Any, conversa: str, run_id: str, pedido_id: str) -> Dict[str, Any]:
    """O `result_payload` reconstruído da mensagem `pronta` que a etapa JÁ gravou (o run morreu entre a entrega e o
    `concluir`): o link, o token, a mensagem e o resumo estão no `payload.cotacao` dela."""
    linhas = _dados(_cliente(db).table("messages").select("id, conversation_id, payload")
                    .eq("id", id_da_mensagem(run_id, "pronta")).eq("conversation_id", str(conversa)).limit(1).execute())
    cot = ((linhas[0].get("payload") or {}).get("cotacao") or {}) if linhas else {}
    if not isinstance(cot, Mapping) or not cot.get("url"):
        return {"pedido_id": pedido_id}
    texto = cot.get("mensagem_para_o_cliente") or ""
    return {"pedido_id": pedido_id, "url": cot.get("url"), "token": cot.get("token"),
            "artifact_id": cot.get("artifact_id"),
            "mensagem": {"texto": texto, "texto_curto": cot.get("texto_curto") or ""} if texto else None,
            "resumo": dict(cot.get("resumo") or {})}
