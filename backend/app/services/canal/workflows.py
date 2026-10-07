# -*- coding: utf-8 -*-
"""O Work Run `canal.cotacao` — SPEC-133-A U6 (D-130A1-06: uma pergunta no fim e até 2 lembretes, nunca mais).

    acompanhar   porta.consultar a cada `INTERVALO_DE_CONSULTA_S` até o quadro de todas as corretoras ficar pronto
                 (ou o teto) — nenhuma mensagem intermediária: a "calculando…" já saiu da conversa (no máximo 1)
    entregar     publicar_proposta(premio_atual_declarado) → a mensagem do canal (mensagem_para, com a pergunta final)
                 → envio.enviar → o estado da conversa vira `resultado` (url, anfitriã, validade)
    lembrete_i   dorme (runs.dormir; o despertador do Work OS acorda) até `follow_up` dentro do horário comercial →
                 relê o estado: a pessoa respondeu? para. Senão, 1 lembrete. i ≤ 2, sempre.

Registrado por `work.workflows.carregar_extras` (o dono do registro). Efeitos externos (`entregar`, `lembrete_i:enviar`)
são `externo`: interrompidos no meio NÃO se repetem (EfeitoIncerto) — melhor um lembrete a menos que dois iguais.

🔴 Conserto B2 (07/10) — o run que DESISTE devolve a conversa: `ao_desistir` (o gancho do Work OS para run expirado ou
efeito incerto) e qualquer erro do próprio run chamam `desistir_da_cotacao` → a conversa vai a `falhou`, perde o que
guardava e a pessoa recebe UMA frase honesta (`conversa.FRASE_NAO_TERMINOU`). E o run nunca escreve por cima de uma
conversa que não é mais a dele (`_ainda_e_a_conversa`: a pessoa recomeçou, parou, ou o teto a tirou de "calculando").
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

from app.services.work.workflows import _agora, _ler_ts, _runs_mod, executar_passo, registrar_workflow

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "canal.cotacao"
INTERVALO_DE_CONSULTA_S = 5
#: o canal pede com validade de 10 min na fila (`porta.VALIDADE["canal"]`) + a leitura 💭
TETO_DO_ACOMPANHAMENTO_S = 11 * 60
#: D-130A1-06 — "nunca mais que isso": a config pode PEDIR menos, nunca mais
MAX_LEMBRETES = 2
TERMINAIS = frozenset({"fechado", "falhou", "incerto", "cancelado", "expirado"})

_dormir = asyncio.sleep   # os testes trocam


def _fuso():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/Sao_Paulo")
    except Exception:  # noqa: BLE001 — sem tzdata: o Brasil não tem horário de verão desde 2019
        return timezone(timedelta(hours=-3))


#: conserto 5 (decisão do gerente, nota 80): lembrete só de segunda a sábado — domingo empurra para segunda
DIA_SEM_LEMBRETE = 6   # `datetime.weekday()`: segunda 0 … domingo 6


def no_horario_comercial(instante: datetime, horario: Mapping[str, Any]) -> datetime:
    """O instante, ou o próximo início do horário comercial (hora local de Brasília), de segunda a sábado."""
    inicio, fim = int(horario.get("inicio_h", 9)), int(horario.get("fim_h", 20))
    local = instante.astimezone(_fuso())
    if local.hour < inicio:
        local = local.replace(hour=inicio, minute=0, second=0, microsecond=0)
    elif local.hour >= fim:
        local = (local + timedelta(days=1)).replace(hour=inicio, minute=0, second=0, microsecond=0)
    if local.weekday() == DIA_SEM_LEMBRETE:
        local = (local + timedelta(days=1)).replace(hour=inicio, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


def _follow_up(db: Any, company_id: str) -> Dict[str, Any]:
    from app.services.multicalculo import config as CFG

    try:
        cfg = CFG.carregar(company_id, db=db)
    except Exception as exc:  # noqa: BLE001 — lembrete é cortesia: sem config, o padrão do produto
        logger.warning("[CANAL] config ilegível (%s) — follow-up do padrão", type(exc).__name__)
        cfg = CFG.mesclar(None)
    return dict((cfg.get("canal") or {}).get("follow_up") or {})


def _lembrete(i: int, estado: Mapping[str, Any]) -> str:
    nome = estado.get("primeiro_nome")
    validade = (estado.get("resultado") or {}).get("validade_ate")
    if i == 1:
        return (f"Oi{', ' + nome if nome else ''}! Conseguiu ver a cotação? Se quiser fechar ou tirar alguma dúvida, "
                "é só responder aqui.")
    fim = f" os preços da sua cotação valem até {validade}." if validade else " a sua cotação continua aqui."
    return f"Passando só pra lembrar:{fim} Se fizer sentido pra você, me responde. Se não, tudo bem também!"


async def _enviar_e_contar(db: Any, company_id: str, telefone: str, baloes: list, *, respeitar_teto: bool) -> int:
    """O envio do run conta no MESMO teto do dia que a entrada usa (`repositorio.contar_enviadas`): o resultado e os
    lembretes são mensagens nossas. `respeitar_teto=True` (lembrete — cortesia): no teto, cala. O resultado sai mesmo
    no teto (a pessoa pediu a cotação e está esperando) — mas conta."""
    from app.services.canal import envio, repositorio

    if respeitar_teto:
        try:
            teto = repositorio.teto_de_mensagens(await asyncio.to_thread(_config_do_canal, db, company_id))
            if await asyncio.to_thread(repositorio.enviadas_hoje, db, company_id, telefone) >= teto:
                logger.warning("[CANAL] teto do dia atingido com %s — o lembrete não sai",
                               repositorio.mascarar(telefone))
                return 0
        except Exception as exc:  # noqa: BLE001 — sem saber o teto, o lembrete (cortesia) cala
            logger.warning("[CANAL] teto do dia ilegível (%s) — o lembrete não sai", type(exc).__name__)
            return 0
    n = await envio.enviar(db, company_id, telefone, baloes)
    if n:
        try:
            await asyncio.to_thread(repositorio.contar_enviadas, db, company_id, telefone, n)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CANAL] contagem do dia não gravada (%s)", type(exc).__name__)
    return n


def _config_do_canal(db: Any, company_id: str) -> Dict[str, Any]:
    from app.services.multicalculo import config as CFG

    return CFG.carregar(company_id, db=db)


def _anfitria_do_artefato(db: Any, company_id: str, artifact_id: str) -> Dict[str, Any]:
    """Quem é a anfitriã (a vencedora) da proposta publicada — do assunto e do modelo da versão, com o filtro do canal."""
    saida: Dict[str, Any] = {}
    try:
        a = (db.table("artifacts").select("id, subject_ref").eq("id", artifact_id).eq("company_id", company_id)
             .limit(1).execute())
        linha = (getattr(a, "data", None) or [{}])[0]
        saida["anfitria_id"] = str((linha.get("subject_ref") or {}).get("anfitria_company_id") or "")
        v = (db.table("artifact_versions").select("artifact_id, version, payload").eq("artifact_id", artifact_id)
             .eq("company_id", company_id).execute())
        versoes = sorted(getattr(v, "data", None) or [], key=lambda x: int(x.get("version") or 0))
        anf = ((versoes[-1].get("payload") or {}).get("anfitria") or {}) if versoes else {}
        saida["anfitria_nome"] = anf.get("nome")
        saida["whatsapp"] = anf.get("whatsapp")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CANAL] anfitriã da proposta ilegível (%s)", type(exc).__name__)
    return saida


def _ainda_e_a_conversa(est: Mapping[str, Any], pedido_id: str) -> bool:
    """A conversa ainda espera ESTE cálculo? (a pessoa não recomeçou, não parou, o teto não a tirou de "calculando")"""
    return str((est or {}).get("pedido_id") or "") == pedido_id and (est or {}).get("etapa") == "calculando"


async def desistir_da_cotacao(db: Any, company_id: str, payload: Mapping[str, Any], motivo: str) -> bool:
    """🔴 Conserto B2 — o run do canal não vai entregar: a conversa SAI de "calculando" (etapa `falhou`, só o
    consentimento fica) e a pessoa recebe UMA frase honesta, que conta no teto do dia. Só mexe se a conversa ainda é a
    deste cálculo (não pisa numa conversa nova, num "parar" ou num resultado já entregue). Nunca levanta."""
    from app.services.canal import repositorio
    from app.services.canal.conversa import FRASE_NAO_TERMINOU, estado_de_saida
    from app.services.canal.cotacao import decifrar_contato

    db = getattr(db, "client", db)
    try:
        pedido_id = str((payload or {}).get("pedido_id") or "")
        telefone = str(decifrar_contato(str((payload or {}).get("contato") or "")).get("telefone") or "")
        if not pedido_id or not telefone:
            return False
        est = await asyncio.to_thread(repositorio.carregar_estado, db, company_id, telefone)
        if not _ainda_e_a_conversa(est, pedido_id):
            return False
        await asyncio.to_thread(repositorio.salvar_estado, db, company_id, telefone,
                                estado_de_saida(est, "falhou", falha="run_desistiu"))
        await _enviar_e_contar(db, company_id, telefone, [FRASE_NAO_TERMINOU], respeitar_teto=False)
        logger.warning("[CANAL] a cotação de %s não terminou (%s) — a pessoa foi avisada",
                       repositorio.mascarar(telefone), str(motivo or "")[:80])
        return True
    except Exception as exc:  # noqa: BLE001 — o teto de "calculando" da conversa é a 2ª rede
        logger.warning("[CANAL] desistência do run não aplicada (%s)", type(exc).__name__)
        return False


#: as tarefas lançadas pelo gancho síncrono (referência forte: o laço não as perde para o coletor)
_DESISTENCIAS: set = set()


def _canal_desistiu(db: Any, run: dict, motivo: str) -> None:
    """`ao_desistir(db, run, motivo)` do `canal.cotacao` — o Work OS desistiu (expirou ou efeito incerto). O gancho é
    SÍNCRONO (o worker e o despertador o chamam assim); a desistência manda mensagem (assíncrona): dentro de um laço
    vira tarefa, fora dele roda até o fim. Nunca levanta."""
    run_id, company_id = str((run or {}).get("id") or ""), str((run or {}).get("company_id") or "")
    if not run_id or not company_id:
        return
    try:
        cliente = getattr(db, "client", db)
        r = (cliente.table("work_runs").select("id, company_id, input_payload").eq("id", run_id)
             .eq("company_id", company_id).limit(1).execute())
        payload = dict(((getattr(r, "data", None) or [{}])[0] or {}).get("input_payload") or {})
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CANAL] entrada do run ilegível na desistência (%s)", type(exc).__name__)
        return
    coro = desistir_da_cotacao(db, company_id, payload, motivo)
    try:
        laco = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return
    tarefa = laco.create_task(coro)
    _DESISTENCIAS.add(tarefa)
    tarefa.add_done_callback(_DESISTENCIAS.discard)


@registrar_workflow(WORKFLOW_KEY, idade_maxima_s=3 * 86400, ao_desistir=_canal_desistiu)
async def workflow_canal_cotacao(ctx: dict) -> Any:
    """O run. Erro do próprio run (porta, publicar, banco) → a conversa é devolvida ANTES de o erro subir ao worker
    (que marca `failed` sem chamar o gancho). Efeito incerto / etapa não verificada são do worker (ele chama o gancho);
    o cancelamento (`CancelamentoPedido`) não é desistência — é a pessoa que respondeu ou recomeçou."""
    _R = _runs_mod()
    try:
        return await _cotacao(ctx)
    except (_R.EfeitoIncerto, _R.EtapaNaoVerificada):
        raise
    except Exception as exc:  # noqa: BLE001
        await desistir_da_cotacao(ctx["db"], str(ctx["company_id"]), ctx.get("payload") or {}, type(exc).__name__)
        raise


async def _cotacao(ctx: dict) -> Any:
    from app.services.canal import envio, repositorio
    from app.services.canal.cotacao import _porta, decifrar_contato

    _R = _runs_mod()
    db = getattr(ctx["db"], "client", ctx["db"])
    company_id, run_id = str(ctx["company_id"]), ctx["run_id"]
    payload = ctx.get("payload") or {}
    pedido_id = str(payload.get("pedido_id") or "")
    contato = decifrar_contato(str(payload.get("contato") or ""))
    telefone = str(contato.get("telefone") or "")
    if not pedido_id or not telefone:
        raise ValueError("run do canal sem pedido ou sem contato")

    # ① acompanhar — só leitura
    async def _acompanhar() -> dict:
        porta = _porta(db)
        inicio = time.monotonic()
        while True:
            and_ = await porta.consultar(company_id=company_id, pedido_id=pedido_id)
            prontos = [e for e in and_.estados if e.get("status") in TERMINAIS or e.get("quadro_pronto_em")]
            if (and_.estados and len(prontos) == len(and_.estados)) or \
                    time.monotonic() - inicio > TETO_DO_ACOMPANHAMENTO_S or ctx["cancelado"]():
                return {"situacao": "com_preco" if and_.ofertas else "sem_preco", "ofertas": len(and_.ofertas)}
            await _dormir(INTERVALO_DE_CONSULTA_S)

    r1 = await executar_passo(ctx, step_key="acompanhar", ordinal=1, nome="Acompanhar o cálculo nas corretoras",
                              step_type="system", fn=_acompanhar, guardar=("situacao", "ofertas"))

    # ② entregar — publica e manda (efeito externo: não se repete)
    async def _entregar() -> dict:
        from app.services.multicalculo.proposta import SemCanalDeFechamento, publicar_proposta

        # 🔴 conserto B2: a conversa ainda espera ESTE cálculo? Se a pessoa recomeçou, parou ou o teto a tirou de
        # "calculando", o run não publica, não manda e não escreve por cima
        if not _ainda_e_a_conversa(await asyncio.to_thread(repositorio.carregar_estado, db, company_id, telefone),
                                   pedido_id):
            return {"situacao": "abandonada", "enviados": 0}
        if (r1 or {}).get("situacao") != "com_preco":
            n = await _enviar_e_contar(db, company_id, telefone, [
                "Não consegui preço nas seguradoras desta vez. Isso acontece quando elas estão fora do ar ou pedem "
                "uma análise a mais. Se quiser tentar de novo mais tarde, é só escrever *nova cotação*."], respeitar_teto=False)
            est = await asyncio.to_thread(repositorio.carregar_estado, db, company_id, telefone)
            est.update({"etapa": "sem_preco"})
            await asyncio.to_thread(repositorio.salvar_estado, db, company_id, telefone, est)
            return {"situacao": "sem_preco", "enviados": n}
        kw = dict(company_id=company_id, pedido_id=pedido_id, situacao="novo_sem_apolice",
                  primeiro_nome=contato.get("primeiro_nome"), db=db,
                  premio_atual_declarado=contato.get("premio_atual_declarado"))
        try:
            pub = await publicar_proposta(**kw)
        except SemCanalDeFechamento:
            # decisão do gerente (piloto): publica sem o botão "Quero fechar" e REGISTRA. No canal o botão volta à
            # CONVERSA do canal (D-133A-13): sem o número pareado do canal (nem a reserva `canal.whatsapp`), não há botão
            ctx["runs"].evento(company_id, run_id, "canal.sem_botao_quero_fechar",
                               "O canal não tem número de WhatsApp pareado (nem a reserva canal.whatsapp na config): a "
                               "proposta saiu sem o botão \"Quero fechar\" — a pessoa ainda fecha respondendo aqui.",
                               severity="warning")
            pub = await publicar_proposta(**kw, permitir_sem_whatsapp=True)
        n = await _enviar_e_contar(db, company_id, telefone, list(pub["mensagem"]), respeitar_teto=False)
        anf = await asyncio.to_thread(_anfitria_do_artefato, db, company_id, str(pub["artifact_id"]))
        est = await asyncio.to_thread(repositorio.carregar_estado, db, company_id, telefone)
        est.update({"etapa": "resultado", "respondeu_em": None, "lembretes": 0,
                    "resultado": {"url": pub["url"], "validade_ate": pub.get("validade_ate"),
                                  "entregue_em": _agora().isoformat(), **anf}})
        await asyncio.to_thread(repositorio.salvar_estado, db, company_id, telefone, est)
        return {"situacao": "entregue", "artifact_id": str(pub["artifact_id"]), "versao": int(pub["versao"]),
                "enviados": n}

    r2 = await executar_passo(ctx, step_key="entregar", ordinal=2, nome="Publicar a proposta e mandar no WhatsApp",
                              step_type="tool", fn=_entregar, efeito="externo",
                              guardar=("situacao", "artifact_id", "versao", "enviados"))
    if (r2 or {}).get("situacao") == "abandonada":
        return "A conversa não espera mais este cálculo (a pessoa recomeçou, parou ou o teto a tirou): nada saiu."
    if (r2 or {}).get("situacao") != "entregue":
        return "A cotação terminou sem preço; a pessoa foi avisada."

    # ③ até 2 lembretes — dormem no Work OS; a resposta da pessoa (estado) os cancela
    fu = await asyncio.to_thread(_follow_up, db, company_id)
    # conserto 3: `max_sem_resposta: 0` DESLIGA os lembretes (antes `0 or 2` dava 2); ausente/ilegível = o teto
    pedido = fu.get("max_sem_resposta")
    quantos = MAX_LEMBRETES if pedido is None or isinstance(pedido, bool) or not isinstance(pedido, (int, float)) \
        else max(0, min(MAX_LEMBRETES, int(pedido)))
    horario = dict(fu.get("horario_comercial") or {})
    atrasos = [timedelta(minutes=float(fu.get("primeiro_apos_min") or 15)),
               timedelta(hours=float(fu.get("segundo_apos_h") or 24))]

    for i in range(1, quantos + 1):
        ref = f"lembrete_{i}"

        async def _esperar(ref=ref, atraso=atrasos[min(i, len(atrasos)) - 1]) -> Any:
            espera = ctx.get("espera") if isinstance(ctx.get("espera"), dict) else {}
            if espera.get("tipo") == "relogio" and espera.get("ref") == ref:
                prazo = _ler_ts(espera.get("prazo"))
                if prazo is not None and _agora() >= prazo:
                    return {"acordou": int(espera.get("acordou") or 0)}
                segundos = max(1, int(((prazo or _agora()) - _agora()).total_seconds()))
            else:
                alvo = no_horario_comercial(_agora() + atraso, horario)
                segundos = max(1, int((alvo - _agora()).total_seconds()))
            return ctx["runs"].dormir(run_id, lease_token=ctx.get("lease_token"), acordar_em_s=segundos,
                                      wait_for={"tipo": "relogio", "ref": ref, "prazo_s": segundos,
                                                "passo": f"{ref}:esperar"},
                                      company_id=company_id)

        espera = await executar_passo(ctx, step_key=f"{ref}:esperar", ordinal=2 + 2 * i - 1,
                                      nome=f"Esperar o lembrete {i}", step_type="system", fn=_esperar,
                                      efeito="idempotente", guardar=("acordou",))
        if isinstance(espera, _R.Esperando):
            return espera

        async def _enviar(i=i) -> dict:
            est = await asyncio.to_thread(repositorio.carregar_estado, db, company_id, telefone)
            # 🔴 G8: QUALQUER resposta depois do resultado para os lembretes (a conversa marca `respondeu_em` e muda
            # a etapa); o cancelamento do run é a 2ª rede — esta leitura vale mesmo se ele se perder
            if est.get("respondeu_em") or est.get("etapa") != "resultado" or est.get("pedido_id") != pedido_id:
                return {"enviado": False, "motivo": "respondeu"}
            if int(est.get("lembretes") or 0) >= min(i, MAX_LEMBRETES):
                return {"enviado": False, "motivo": "ja_enviado"}
            # 🔴 conserto 4: o número AINDA é convidado? (o Founder pode tê-lo removido depois do resultado) — sem ler
            # o convite, o lembrete (cortesia) cala
            try:
                ainda = await asyncio.to_thread(repositorio.convidado, db, company_id, telefone)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[CANAL] convite ilegível antes do lembrete (%s) — não sai", type(exc).__name__)
                ainda = None
            if ainda is None:
                return {"enviado": False, "motivo": "nao_convidado"}
            n = await _enviar_e_contar(db, company_id, telefone, [_lembrete(i, est)], respeitar_teto=True)
            # relê ANTES de gravar e só soma o contador: uma resposta ("quero fechar") que chegou durante o envio fica
            atual = await asyncio.to_thread(repositorio.carregar_estado, db, company_id, telefone)
            if str(atual.get("pedido_id") or "") == pedido_id:
                atual["lembretes"] = max(int(atual.get("lembretes") or 0), i)
                await asyncio.to_thread(repositorio.salvar_estado, db, company_id, telefone, atual)
            return {"enviado": bool(n), "motivo": "enviado"}

        env = await executar_passo(ctx, step_key=f"{ref}:enviar", ordinal=2 + 2 * i, nome=f"Lembrete {i}",
                                   step_type="tool", fn=_enviar, efeito="externo", guardar=("enviado", "motivo"))
        if not (env or {}).get("enviado"):
            return "A pessoa respondeu: os lembretes pararam."
    return f"Proposta entregue; {quantos} lembrete(s) sem resposta — encerrado (nunca mais que {MAX_LEMBRETES})."
