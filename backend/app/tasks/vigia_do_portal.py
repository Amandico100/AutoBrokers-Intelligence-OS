"""VIGIA DO PORTAL (SPEC-065) — nenhum acionamento de vidros morre em silêncio.

O buraco que este arquivo fecha
--------------------------------
📊 Medido em 04/08/2026: `dispatch_watchdog.py` e `handoff_watchdog.py` — os dois
vigias do sistema — têm **zero** menções a "portal". Eles vigiam
`dispatch_sessions`, que é o corredor de WhatsApp com a seguradora.

O portal é outro caminho: `portal_jobs`. E ninguém olhava para ele.

Onde isso doía, exatamente
---------------------------
A `portal_action` espera o worker por **150 segundos** (`POLL_TIMEOUT_S`) e
devolve o resultado ao agente, que conta ao segurado. Dentro dessa janela, tudo
funciona.

**Fora dela, não existe ninguém.** O job continua vivo, chega em `needs_human`
ou `done` mais tarde — e a conversa nunca fica sabendo. O segurado mandou "meu
vidro quebrou", ouviu "já vou abrir, um minutinho", e o minutinho não acaba
nunca.

E há um caso pior, que é o único que já aconteceu de verdade: o worker
**não pegar** o job. `poll_loop` devolve na hora quando `PORTAL_REAL_ENABLED`
está desligado — não fica em loop, não avisa, não erra. Os jobs se empilham em
`queued` para sempre, e o silêncio é idêntico ao do sucesso lento.

📊 Hoje o gate está ligado (`portal_real_enabled: true`, verificado no
`/health` do worker em 04/08). Mas o dia em que alguém desligar é o dia em que
todo acionamento de vidros vira silêncio — e ninguém vai relacionar as duas
coisas.

A regra, em uma frase
----------------------
    Se um segurado está esperando e o sistema não tem como contar a ele o
    que aconteceu, isso é um handoff — não uma espera.

Este módulo é PURO na parte que decide. `diagnosticar` não toca em rede, banco
nem relógio do sistema: recebe o job e o instante, devolve o que fazer. É por
isso que dá para provar offline que ele acusa cada caso — e, mais importante,
que ele **fica quieto** quando está tudo bem.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

# A janela em que o AGENTE ainda está esperando (portal_tool.POLL_TIMEOUT_S).
# Dentro dela quem conta ao segurado é o próprio atendimento. O Vigia só existe
# do lado de fora — duplicar aviso é pior que não avisar: o segurado recebe duas
# versões da mesma coisa e não sabe qual vale.
JANELA_DO_AGENTE_S = 150

# O worker pega um job em segundos. Passou disso, ele não vai pegar: está
# parado, sem gate, ou ocupado com algo que não termina.
LIMITE_NA_FILA_S = 4 * 60

# O `run_adaptive` tem teto de 22 passos e o worker recupera os próprios órfãos.
# Este limite é para quando **o worker inteiro** caiu — aí não há quem recupere,
# e a recuperação de dentro dele nunca roda.
LIMITE_RODANDO_S = 8 * 60

VIVOS = ("queued", "running")
TERMINAIS = ("done", "needs_human", "failed")


def _instante(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _idade_s(ts: Any, agora: datetime) -> Optional[float]:
    d = _instante(ts)
    return None if d is None else (agora - d).total_seconds()


def _peca(job: Dict[str, Any]) -> str:
    return str(((job.get("params") or {}).get("dano") or {}).get("peca") or "").strip()


def _sobre_o_que(job: Dict[str, Any]) -> str:
    """Como se refere ao pedido em português, sem jargão nem UUID."""
    peca = _peca(job)
    placa = str((job.get("params") or {}).get("placa") or "").strip()
    if peca and placa:
        return f"{peca} (placa {placa})"
    return peca or (f"placa {placa}" if placa else "o atendimento de vidros")


def _dossie(job: Dict[str, Any]) -> str:
    """O que um humano precisa para resolver em 10 segundos, sem reabrir o portal.

    A evidência já carrega isto desde a SPEC-064: a pergunta literal do portal,
    TODAS as opções oferecidas e o que o segurado disse. Aqui só viramos texto.
    """
    ev = job.get("evidence") or {}
    linhas = []
    if ev.get("pergunta"):
        linhas.append(f"O portal perguntou: \"{str(ev['pergunta'])[:180]}\"")
    if ev.get("opcoes"):
        linhas.append("Opções: " + ", ".join(str(o)[:40] for o in list(ev["opcoes"])[:10]))
    pedido = ev.get("pedido_do_segurado") or {}
    if pedido:
        dito = "; ".join(f"{k}: {str(v)[:70]}" for k, v in pedido.items() if v)
        if dito:
            linhas.append(f"O segurado disse: {dito}")
    passo = (ev.get("passo") or {}).get("titulo") or ev.get("stage")
    if passo:
        linhas.append(f"Parou em: {passo}")
    return "\n".join(linhas)


def diagnosticar(job: Dict[str, Any], agora: Optional[datetime] = None) -> Optional[Dict[str, str]]:
    """PURO: este job deixou alguém esperando sem resposta? None = está tudo bem.

    Devolve {'motivo', 'para_o_segurado', 'para_o_suporte'} — as duas mensagens
    já prontas, porque quem chama não deve ter que decidir o que dizer.
    """
    agora = agora or datetime.now(timezone.utc)
    job = job or {}
    status = str(job.get("status") or "")
    ev = job.get("evidence") or {}

    # Dispara UMA vez. Um Vigia que repete vira ruído, e ruído se ignora — foi
    # assim que o alerta de acionamento parou de ser lido, em 07/2026.
    if ev.get("vigia_avisou_em"):
        return None

    assunto = _sobre_o_que(job)

    if status == "queued":
        idade = _idade_s(job.get("created_at"), agora)
        if idade is None or idade < LIMITE_NA_FILA_S:
            return None
        return {
            "motivo": "nunca_pegou",
            "para_o_segurado": (
                f"Oi! Não consegui abrir {assunto} no sistema da seguradora agora — "
                "o canal automático não respondeu. Já chamei alguém da nossa equipe "
                "pra fazer isso na mão pra você, tá? Não vou te deixar esperando. 🙏"),
            "para_o_suporte": (
                f"🔴 VIGIA DO PORTAL: acionamento de vidros parado NA FILA há "
                f"{int(idade // 60)}min — o worker não pegou. Verifique se o "
                f"portal-worker está no ar e se PORTAL_REAL_ENABLED está ligado. "
                f"Pedido: {assunto}. O segurado já foi avisado e espera atendimento humano."),
        }

    if status == "running":
        idade = _idade_s(job.get("started_at") or job.get("created_at"), agora)
        if idade is None or idade < LIMITE_RODANDO_S:
            return None
        return {
            "motivo": "travado_rodando",
            "para_o_segurado": (
                f"Oi! O sistema da seguradora está demorando mais do que o normal pra "
                f"abrir {assunto}. Não vou te deixar no vácuo: já passei pra alguém da "
                "nossa equipe acompanhar e te retornar. 🙏"),
            "para_o_suporte": (
                f"🔴 VIGIA DO PORTAL: acionamento RODANDO há {int(idade // 60)}min sem "
                f"terminar. O worker pode ter caído no meio (a recuperação dele roda "
                f"por dentro e não roda se ele estiver fora). Pedido: {assunto}."),
        }

    if status not in TERMINAIS:
        return None

    # Terminal. A pergunta é: **o atendimento chegou a saber?**
    #
    # Quando a tool recebe o resultado dentro dos 150s, ela marca. Sem a marca,
    # ou o job passou da janela, ou a conversa caiu — e nos dois casos o
    # segurado ficou sem resposta. Não adivinhamos pelo relógio: exigimos a
    # marca. Relógio erra quando o processo reinicia; a marca, não.
    if ev.get("entregue_ao_agente"):
        return None

    if status == "done":
        return {
            "motivo": "concluiu_e_ninguem_soube",
            "para_o_segurado": (
                f"Oi! Voltando aqui: consegui abrir {assunto} na seguradora. ✅ "
                "Vou acompanhar e te aviso assim que tiver a data do serviço."),
            "para_o_suporte": (
                f"ℹ️ VIGIA DO PORTAL: acionamento CONCLUIU depois da janela do "
                f"atendimento — o segurado foi avisado agora pelo Vigia. Pedido: {assunto}."),
        }

    if status == "failed":
        return {
            "motivo": "falhou_e_ninguem_soube",
            "para_o_segurado": (
                f"Oi! Tentei abrir {assunto} no sistema da seguradora e não consegui "
                "concluir por aqui. Já pedi pra alguém da nossa equipe resolver isso "
                "direto com eles. Te aviso assim que tiver retorno. 🙏"),
            "para_o_suporte": (
                f"🔴 VIGIA DO PORTAL: acionamento FALHOU e ninguém soube. "
                f"Pedido: {assunto}. Erro: {str(job.get('error') or '?')[:200]}\n"
                + _dossie(job)).strip(),
        }

    # needs_human — o caso mais comum: 📊 33 dos 39 acionamentos de vidros.
    return {
        "motivo": "parou_e_ninguem_soube",
        "para_o_segurado": (
            f"Oi! Comecei a abrir {assunto} na seguradora e o sistema pediu uma "
            "confirmação que eu não consigo dar sozinho. Já passei pra nossa equipe "
            "concluir — não some não, te aviso assim que estiver aberto. 🙏"),
        "para_o_suporte": (
            f"🟠 VIGIA DO PORTAL: acionamento PAROU esperando decisão e ninguém foi "
            f"avisado. Pedido: {assunto}.\n" + _dossie(job)).strip(),
    }


async def varrer_portal() -> int:
    """Varre os `portal_jobs` que deixaram alguém esperando. Devolve quantos tratou.

    Mora ao lado do VIGIA dos acionamentos e roda no MESMO scheduler — não é um
    vigia paralelo, é a segunda varredura do mesmo. O corredor de WhatsApp e o
    portal são caminhos diferentes para o mesmo trabalho, e quem garante desfecho
    tem que enxergar os dois.
    """
    import logging

    logger = logging.getLogger(__name__)
    tratados = 0
    try:
        from app.core.database import get_supabase_client
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        supa = get_supabase_client()
        cliente = getattr(supa, "client", supa)
        wa = get_whatsapp_service()
        integracoes = get_integration_service()

        # Só o que ainda pode estar esperando alguém. `done` sem a marca entra:
        # é boa notícia que não foi entregue.
        res = cliente.table("portal_jobs").select(
            "id, company_id, session_id, status, params, evidence, error, "
            "created_at, started_at, finished_at"
        ).eq("portal_key", "vidros_lanternas").order(
            "created_at", desc=True).limit(200).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VIGIA-PORTAL] indisponível: {type(e).__name__}")
        return 0

    agora = datetime.now(timezone.utc)
    for job in (res.data or []):
        try:
            achado = diagnosticar(job, agora)
            if not achado:
                continue
            company_id = str(job.get("company_id") or "")
            integracao = integracoes.get_platform_whatsapp_integration(company_id) if company_id else None

            # 1) o segurado, primeiro. Ele é quem está esperando.
            #
            # 🔴 Mas SÓ se o agente estiver ligado. Este era o furo desta própria
            # varredura no dia em que ela nasceu: ela roda no scheduler, a cada
            # 60s, e o portão de silêncio do `webhook.py` não passa por aqui.
            #
            # Com o agente em modo observação, a atendente humana responde pelo
            # celular. Um robô entrando na conversa para dizer "não consegui
            # abrir seu vidro" seria o sistema falando sem ter permissão — e
            # numa conversa onde o segurado acha que está falando com gente.
            #
            # Fail-closed: erro de leitura = silêncio. É a mesma regra do
            # webhook, e ela vale para todo sender, não só para o que responde.
            sessao = str(job.get("session_id") or "")
            partes = sessao.split(":")
            if len(partes) >= 3 and partes[0] == "whatsapp" and integracao:
                try:
                    from app.services.atlas.attendance_capture import attendance_agent_active

                    pode_falar = await attendance_agent_active(company_id)
                except Exception:  # noqa: BLE001
                    pode_falar = False
                telefone = "".join(c for c in partes[1] if c.isdigit())
                if telefone and pode_falar:
                    wa.send_message(telefone, achado["para_o_segurado"], integracao)
                elif telefone:
                    logger.info("[VIGIA-PORTAL] 🔇 agente em silêncio — só a equipe é avisada")

            # 2) a equipe, com o dossiê pronto.
            from app.tasks.dispatch_watchdog import _support_alert
            await _support_alert(company_id, achado["para_o_suporte"], wa, integracao)

            # 3) marca, para não repetir.
            cliente.table("portal_jobs").update({
                "evidence": {**(job.get("evidence") or {}),
                             "vigia_avisou_em": agora.isoformat(),
                             "vigia_motivo": achado["motivo"]},
            }).eq("id", job["id"]).execute()
            tratados += 1
            logger.warning(f"[VIGIA-PORTAL] job {job.get('id')} -> {achado['motivo']}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[VIGIA-PORTAL] falha ao tratar job: {type(e).__name__}")
    return tratados
