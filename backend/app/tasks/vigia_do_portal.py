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

# 🔴 SPEC-EXTRA-001.10.1 C4 — a RELEITURA automática de uma parada técnica.
#
# 📊 O token do portal EXPIRA (21/09 22:09 UTC → 401 em 23/09 23:40 UTC; o
# intervalo exato é ❓). Uma releitura só vale enquanto a sessão é jovem: 30
# minutos a partir de `continuacao.emitida_em`. Passou disso, a chance de 401 é
# alta, e quem conclui é a equipe (o texto da parada já diz).
JANELA_DA_RELEITURA_S = 30 * 60

#: As paradas que só a EQUIPE resolve depois da continuação — o segurado já
#: recebeu a mensagem (pela tool), mas a equipe tem de saber (C4: "401 ⇒ alerta
#: humano com dossiê").
PARADAS_SO_DA_EQUIPE = ("sessao_expirada", "sessao_indisponivel",
                        "atendimento_cancelado", "agendamento_nao_confirmado")


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


def _e_continuacao(job: Dict[str, Any]) -> bool:
    return str(job.get("journey") or "") == "continuar_atendimento"


def pedir_releitura(job: Dict[str, Any], agora: Optional[datetime] = None) -> bool:
    """PURO: este job deve ganhar UMA continuação "reler" agora?

    As condições, e cada uma fecha uma porta:
      · terminou parado (`needs_human`/`failed`) numa parada TÉCNICA — nada a
        perguntar ao segurado; a releitura pelo estado REAL do agregado resolve;
      · a journey PROVOU que dá para continuar (`continuacao.possivel is True`);
      · a sessão é jovem (< 30 min de `emitida_em`) — depois, 401 é o provável;
      · UMA vez por job (`releitura_pedida_em`), e nunca releitura de releitura:
        sem isso uma parada técnica persistente viraria um laço de jobs;
      · ⛔ nunca `maybe_committed`: ali a chamada material SAIU e a resposta se
        perdeu — quem decide é a reconciliação, não uma nova tentativa.
    """
    from app.agents.tools.portal_params import (
        ESTAGIOS_TECNICOS,
        continuacao_da_evidencia,
        continuacao_possivel,
    )

    agora = agora or datetime.now(timezone.utc)
    job = job or {}
    ev = job.get("evidence") if isinstance(job.get("evidence"), dict) else {}
    if str(job.get("status") or "") not in ("needs_human", "failed"):
        return False
    stage = str(ev.get("stage") or "").strip().lower()
    if stage not in ESTAGIOS_TECNICOS:
        return False
    if not continuacao_possivel(ev) or ev.get("releitura_pedida_em"):
        return False
    est = ev.get("vidros_estado") if isinstance(ev.get("vidros_estado"), dict) else {}
    if est.get("precisa_reconciliar"):
        return False
    cont_propria = ((job.get("params") or {}).get("_continuacao") or {})
    if isinstance(cont_propria, dict) and cont_propria.get("operacao") == "reler":
        return False
    idade = _idade_s(continuacao_da_evidencia(ev).get("emitida_em"), agora)
    return idade is not None and 0 <= idade < JANELA_DA_RELEITURA_S


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
    # 🔴 SPEC-EXTRA-001.10.1 — um job de CONTINUAÇÃO não "abre" nada: o pedido
    # já existe. Dizer "não consegui abrir" sobre ele convidaria o segurado a
    # pedir de novo — o segundo atendimento.
    abrir = "continuar" if _e_continuacao(job) else "abrir"

    if status == "queued":
        idade = _idade_s(job.get("created_at"), agora)
        if idade is None or idade < LIMITE_NA_FILA_S:
            return None
        return {
            "motivo": "nunca_pegou",
            "para_o_segurado": (
                f"Oi! Não consegui {abrir} {assunto} no sistema da seguradora agora — "
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
                f"{abrir} {assunto}. Não vou te deixar no vácuo: já passei pra alguém da "
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
    # 🔴 B-N2: ENTREGUE AO AGENTE NAO E "TRABALHO CONCLUIDO".
    #
    # 📊 Medido em 20/09/2026: desfecho `agenda` e `vistoria` terminam `done`, a
    # mensagem diz ao segurado que "a equipe confirma com a loja" — e NADA avisa
    # a equipe. O run era concluido, o vigia se calava por causa desta marca, e
    # o aviso ficava dependendo de o LLM lembrar de avisar alguem.
    #
    # Nestes dois desfechos o vigia fala com o SUPORTE mesmo com a marca — uma
    # vez so (`vigia_avisou_em`, ja checado acima) e **sem segunda mensagem ao
    # segurado**, que ja recebeu a dele.
    _desf = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else {}
    _tipo = str(_desf.get("tipo") or "").strip().lower()
    from app.agents.tools.portal_params import ESTAGIOS_TECNICOS, continuacao_possivel

    _stage = str(ev.get("stage") or "").strip().lower()
    # 🔴 "Já estou tentando de novo" só é verdade se a releitura VAI sair (sessão
    # jovem, uma vez, nunca releitura de releitura). Fora disso a parada técnica
    # volta ao texto honesto — a equipe assume.
    _pode_continuar = continuacao_possivel(ev) and (
        _stage not in ESTAGIOS_TECNICOS or pedir_releitura(job, agora))
    if ev.get("entregue_ao_agente"):
        if (status in ("needs_human", "failed") and _stage in ESTAGIOS_TECNICOS
                and continuacao_possivel(ev) and not ev.get("releitura_pedida_em")
                and not pedir_releitura(job, agora)):
            # O segurado ouviu "já estou tentando de novo" (pela tool), mas a
            # releitura não vai sair (sessão velha, ou já era uma releitura). A
            # promessa só se cumpre se uma PESSOA assumir — e ela precisa saber.
            return {
                "motivo": f"releitura_impossivel_{_stage}",
                "para_o_segurado": "",
                "para_o_suporte": (
                    f"🔴 A EQUIPE PRECISA CONCLUIR: a parada tecnica `{_stage}` nao pode "
                    f"ser relida automaticamente (sessao do portal com mais de "
                    f"{JANELA_DA_RELEITURA_S // 60} min, ou ja era uma releitura). O pedido "
                    f"EXISTE: NAO reabra. Pedido: {assunto}\n" + _dossie(job)).strip(),
            }
        if status in ("needs_human", "failed") and _stage in PARADAS_SO_DA_EQUIPE:
            # 🔴 SPEC-EXTRA-001.10.1 C4 — o segurado já ouviu (pela tool); a
            # EQUIPE não. 401 na continuação é o caso: o pedido existe, o token
            # morreu, e só uma pessoa conclui no portal.
            from app.agents.tools.portal_params import texto_da_parada

            _par = texto_da_parada(_stage) or ("", "")
            _num = str((_desf or {}).get("codigo_atendimento")
                       or (ev.get("vidros_estado") or {}).get("codigo_atendimento")
                       or ev.get("protocolo") or "").strip()
            return {
                "motivo": f"parou_em_{_stage}_equipe",
                # ⛔ VAZIO de proposito: ele ja recebeu a mensagem pela tool.
                "para_o_segurado": "",
                "para_o_suporte": (
                    f"🔴 A EQUIPE PRECISA CONCLUIR: atendimento {_num or '(sem numero)'}. "
                    f"{_par[1]} Pedido: {assunto}\n" + _dossie(job)).strip(),
            }
        if status == "done" and _tipo in ("agenda", "vistoria") and _pode_continuar:
            # 🔴 SPEC-EXTRA-001.10.1 — com a continuação POSSÍVEL quem fecha é o
            # robô, quando o segurado escolher. Chamar a equipe aqui a treinaria a
            # ignorar o vigia (e duas mãos fechariam o mesmo agendamento).
            return None
        if status == "done" and _tipo in ("agenda", "vistoria"):
            _num = str(_desf.get("codigo_atendimento")
                       or (ev.get("vidros_estado") or {}).get("codigo_atendimento")
                       or ev.get("protocolo") or "").strip()
            _lojas = [str(x.get("nome") or "") for x in (_desf.get("lojas") or [])
                      if isinstance(x, dict)][:4]
            _escolha = str(ev.get("escolha_do_segurado") or "").strip()
            return {
                "motivo": f"desfecho_{_tipo}_aguarda_a_equipe",
                # ⛔ VAZIO de proposito: ele ja recebeu a mensagem do desfecho.
                "para_o_segurado": "",
                "para_o_suporte": (
                    f"🔴 A EQUIPE PRECISA CONCLUIR: o atendimento {_num or '(sem numero)'} "
                    f"existe na seguradora e o portal pediu "
                    + ("AGENDAMENTO com a loja" if _tipo == "agenda" else "VISTORIA")
                    + ". O segurado ja foi avisado; quem fecha no portal e a equipe. "
                    + (f"Lojas oferecidas: {', '.join(_lojas)}. " if _lojas else "")
                    + (f"O segurado ja escolheu: {_escolha}. " if _escolha else "")
                    + "NAO reexecute o acionamento — reabrir cria um segundo pedido."),
            }
        return None

    # ----------------------------------------------------------------------
    # SPEC-074 — o ESTADO DE NEGÓCIO decide o que dizer, antes do técnico.
    #
    # 🔴 O defeito que isto corrige: um job pode terminar `failed` com o pedido
    # JÁ ABERTO na seguradora — o navegador caiu depois do clique que cria. O
    # ramo `failed` abaixo diria ao segurado *"tentei e não consegui"*, sobre um
    # atendimento que existe e vai receber visita de vidraceiro.
    #
    # É a pior frase possível: ela convida o segurado a pedir de novo.
    # ----------------------------------------------------------------------
    est = ev.get("vidros_estado") if isinstance(ev.get("vidros_estado"), dict) else {}
    numero = str(est.get("codigo_atendimento") or ev.get("protocolo") or "").strip()

    # ----------------------------------------------------------------------
    # 🔴 SPEC-EXTRA-001.10 N-1 — O DESFECHO QUE O PORTAL DECIDIU VEM PRIMEIRO.
    #
    # Fora da janela dos 150s, quem fala com o segurado é este vigia. Se ele
    # não souber ler `evidence["desfecho"]`, o segurado recebe a frase genérica
    # ("consegui abrir na seguradora ✅") sobre um pedido que já tem número,
    # franquia, loja e endereço — tudo lido e guardado, e nada entregue.
    #
    # ⛔ E a mensagem é composta pelo MESMO escritor que a tool usa
    # (`portal_params.mensagem_do_desfecho`): duas versões do mesmo texto
    # fariam o segurado receber coisas diferentes dependendo de o relógio ter
    # estourado ou não.
    # ----------------------------------------------------------------------
    desfecho = ev.get("desfecho") if isinstance(ev.get("desfecho"), dict) else None
    if desfecho:
        from app.agents.tools.portal_params import mensagem_do_desfecho

        corpo = mensagem_do_desfecho(desfecho, ev.get("continuacao")
                                     if isinstance(ev.get("continuacao"), dict) else None)
        if corpo:
            tipo = str(desfecho.get("tipo") or "desconhecido").strip().lower()
            numero = str(desfecho.get("codigo_atendimento") or numero or "").strip()
            conhecido = tipo in ("loja_direta", "agenda", "analista", "agendado") or (
                _pode_continuar and tipo in ("vistoria", "vistoria_opcional",
                                             "decidir_vistoria"))
            return {
                "motivo": f"desfecho_{tipo or 'sem_tipo'}",
                "para_o_segurado": corpo,
                "para_o_suporte": (
                    ("🟢" if conhecido else "🟠")
                    + f" VIGIA DO PORTAL: desfecho `{tipo or 'sem_tipo'}` lido no portal e "
                      f"entregue ao segurado agora. Pedido: {assunto}"
                    + (f" · nº {numero}" if numero else " · numero NAO lido")
                    + ("" if conhecido else
                       "\n⚠️ A equipe PRECISA concluir: a escolha de loja/dia e a vistoria "
                       "não são feitas pelo robô.")
                    + f"\nroteador do portal: {desfecho.get('roteador')}\n"
                    + _dossie(job)).strip(),
            }

    # As paradas com nome próprio (decidir_reparo, peca_ambigua, cidade_sem_rede,
    # motivo_ambiguo, questionario_incompleto, tela_desconhecida). Cada uma tem
    # UMA pergunta para o segurado e um dossiê para quem resolve — e é por isso
    # que elas vêm antes do `switch` de status: `needs_human` diria a mesma
    # frase vaga para as seis.
    if status in ("needs_human", "failed"):
        from app.agents.tools.portal_params import texto_da_parada

        parada = texto_da_parada(ev.get("stage"), _pode_continuar)
        if parada:
            para_ele, para_equipe = parada
            opcoes = [str(o)[:60] for o in (ev.get("opcoes") or [])][:12]
            if opcoes:
                para_ele += "\n\nAs opções são: " + " · ".join(opcoes)
            return {
                "motivo": f"parou_em_{str(ev.get('stage') or '').strip().lower()}",
                "para_o_segurado": para_ele,
                "para_o_suporte": (
                    f"🟠 VIGIA DO PORTAL: {para_equipe} Pedido: {assunto}"
                    + (f" · nº {numero}" if numero else "")
                    + "\n" + _dossie(job)).strip(),
            }

    if _e_continuacao(job) and status in ("needs_human", "failed"):
        return {
            "motivo": "continuacao_parou",
            "para_o_segurado": (
                f"Oi! Seu pedido de {assunto} continua aberto na seguradora"
                + (f" (nº {numero})" if numero else "")
                + ", mas não consegui concluir este passo por aqui. Já passei para a "
                  "nossa equipe finalizar direto com a seguradora — você não precisa "
                  "pedir de novo. 🙏"),
            "para_o_suporte": (
                f"🟠 VIGIA DO PORTAL: a CONTINUACAO do pedido terminou `{status}` sem "
                f"texto proprio. NAO reabra: o pedido existe. Pedido: {assunto}"
                + (f" · nº {numero}" if numero else "")
                + f"\nerro: {str(job.get('error') or '')[:200]}\n" + _dossie(job)).strip(),
        }

    if est.get("estado") == "aguardando_escolha_do_segurado":
        # 99%: o pedido nasceu e falta o segurado escolher a loja.
        # Isso NÃO é incidente — é o fluxo funcionando. Alertar suporte aqui
        # treinaria a equipe a ignorar o Vigia.
        # 🔴 RED B5 (conserto da 001.10.1) — D-E001101-05: domicílio FORA. Este
        # texto sai no caminho DOM (produção com a flag desligada) e oferecia
        # "um técnico vai até você" — uma opção que o produto não entrega.
        return {
            "motivo": "aguardando_escolha_do_segurado",
            "para_o_segurado": (
                f"Oi! {assunto.capitalize()} já está aberto na seguradora"
                + (f" (nº {numero})" if numero else "")
                + ". Falta só você escolher em qual loja credenciada prefere "
                  "fazer o serviço. Qual fica melhor para você?"),
            "para_o_suporte": (
                f"🟢 VIGIA DO PORTAL: pedido ABERTO aguardando escolha do segurado "
                f"(qual loja). Nao e falha. Pedido: {assunto}"
                + (f" · nº {numero}" if numero else "")),
        }

    if est.get("existe_algo_na_seguradora") and status in ("failed", "needs_human"):
        return {
            "motivo": "falhou_depois_de_abrir",
            "para_o_segurado": (
                f"Oi! {assunto.capitalize()} FOI aberto na seguradora"
                + (f" — o número é {numero}. " if numero else ". ")
                + "Só não consegui concluir a última etapa por aqui. Já passei "
                  "para nossa equipe finalizar. Seu pedido está registrado. 🙏"),
            "para_o_suporte": (
                f"🟠 VIGIA DO PORTAL: o pedido EXISTE na seguradora e o job "
                f"terminou `{status}`. NAO reexecute — reabrir cria um segundo "
                f"atendimento. Pedido: {assunto}"
                + (f" · nº {numero}" if numero else " · numero NAO lido")
                + f"\nestado={est.get('estado')} "
                  f"safe_to_retry={est.get('safe_to_retry_open')}\n"
                + _dossie(job)).strip(),
        }

    if est.get("precisa_reconciliar"):
        return {
            "motivo": "maybe_committed",
            "para_o_segurado": (
                f"Oi! Estou confirmando com a seguradora se {assunto} foi aberto. "
                "Te aviso em seguida — não precisa pedir de novo. 🙏"),
            "para_o_suporte": (
                f"🔴 VIGIA DO PORTAL: MAYBE_COMMITTED. A operacao pode ter "
                f"acontecido no portal e a resposta se perdeu. NAO reexecute: "
                f"consulte o atendimento antes. Pedido: {assunto}\n"
                + _dossie(job)).strip(),
        }

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


async def _aprender_com_a_tela_cega(cliente, company_id: str, job: Dict[str, Any]) -> bool:
    """A tela que o portal mostrou e ninguém sabe ler entra na fila. `False` = não entrou.

    🔴 `company_id` do PRÓPRIO JOB, nunca de um default: a fila de aprendizado é
    por corretora, e uma linha na casa errada é a tela de uma corretora aparecendo
    no trabalho da outra (CLAUDE.md §7).

    ⚠️ UMA vez por job. A marca vai no `evidence` e não num relógio: o vigia roda
    a cada 60s, e sem a marca a mesma tela entraria 1.440 vezes por dia — a fila
    deixaria de ordenar por "quantas vezes apareceu", que é o que a torna útil.
    """
    import logging as _logging

    log = _logging.getLogger(__name__)
    try:
        from app.agents.tools.portal_params import (
            resumo_da_tela_desconhecida,
            slug_da_seguradora,
        )

        ev = job.get("evidence") or {}
        if ev.get("tela_cega_registrada") or not company_id:
            return False
        resumo = resumo_da_tela_desconhecida(ev)
        if not resumo:
            return False

        from app.services.tela_cega import registrar_tela_cega

        await registrar_tela_cega(
            company_id=company_id,
            insurer_key=slug_da_seguradora(job.get("params") or {}),
            ramo="vidros",
            playbook_ref=f"portal:vidros_lanternas:{resumo['onde']}",
            texto=resumo["texto"],
        )
        # ⚠️ O dicionário do job é atualizado ANTES do banco de propósito: o
        # passo 3 da varredura grava `vigia_avisou_em` espalhando
        # `job["evidence"]`, e com a cópia velha ele apagaria esta marca no
        # mesmo segundo em que ela foi escrita — a fila receberia de novo na
        # próxima volta, e a dedupe viraria contagem inflada.
        job["evidence"] = {**ev, "tela_cega_registrada": True}
        cliente.table("portal_jobs").update({
            "evidence": job["evidence"],
        }).eq("id", job["id"]).eq("company_id", company_id).execute()
        return True
    except Exception as e:  # noqa: BLE001
        log.error("[VIGIA-PORTAL] fila de aprendizado nao recebeu (%s)", type(e).__name__)
        return False


def _reler_evidencia(cliente, job_id: str, company_id: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """A evidence ATUAL do banco — nunca a cópia do SELECT de 200 linhas (P5)."""
    atual = dict(fallback or {})
    try:
        lido = (cliente.table("portal_jobs").select("evidence")
                .eq("id", job_id).eq("company_id", company_id).limit(1).execute())
        linhas = getattr(lido, "data", None) or []
        if linhas and isinstance(linhas[0].get("evidence"), dict):
            atual = dict(linhas[0]["evidence"])
    except Exception:  # noqa: BLE001
        pass
    return atual


async def pedir_a_releitura(cliente, job: Dict[str, Any], agora: datetime) -> bool:
    """🔴 SPEC-EXTRA-001.10.1 C4 — enfileira UMA continuação "reler" para este job.

    ⛔ Nenhum escritor novo: a linha sai de `portal_params.montar_job_de_
    continuacao` e o insert de `portal_tool.enfileirar_continuacao` — os MESMOS
    que a tool usa quando o segurado responde. O interruptor é lido AGORA por
    `portal_tool.envio_liberado` (a mesma regra da abertura).

    A marca `releitura_pedida_em` vai na evidence RELIDA do job de origem
    (mesmo padrão de `_aprender_com_a_tela_cega`), e com `company_id` no
    filtro — o backend roda com service role (CLAUDE.md §7).
    """
    import logging as _logging

    log = _logging.getLogger(__name__)
    company_id = str(job.get("company_id") or "")
    if not company_id or not job.get("id"):
        return False
    try:
        from app.agents.tools.portal_params import (
            montar_job_de_continuacao,
            numero_do_pedido,
        )
        from app.agents.tools.portal_tool import enfileirar_continuacao, envio_liberado

        params = job.get("params") or {}
        pedido_key = str(params.get("_pedido_key") or job.get("idempotency_key") or "")
        confirm = await envio_liberado(company_id, str(params.get("cpf_cnpj") or ""),
                                       "continuar_atendimento")
        linha = montar_job_de_continuacao(
            company_id=company_id, job_origem=job, operacao="reler",
            pedido_key=pedido_key,
            protocolo=numero_do_pedido(job.get("evidence")) or pedido_key,
            confirm=confirm, extra=str(job["id"]))
        novo_id, ja = enfileirar_continuacao(cliente, linha)
        if not (novo_id or ja):
            return False
        atual = _reler_evidencia(cliente, str(job["id"]), company_id, job.get("evidence") or {})
        atual.update({"releitura_pedida_em": agora.isoformat(),
                      "releitura_job": novo_id or str((ja or {}).get("id") or ""),
                      # O resultado chega pela RELEITURA; este job se cala.
                      "vigia_avisou_em": agora.isoformat(),
                      "vigia_motivo": "releitura_pedida"})
        job["evidence"] = atual
        cliente.table("portal_jobs").update({"evidence": atual}).eq(
            "id", job["id"]).eq("company_id", company_id).execute()
        return True
    except Exception as e:  # noqa: BLE001
        log.error("[VIGIA-PORTAL] releitura nao pedida (%s)", type(e).__name__)
        return False


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
            "created_at, started_at, finished_at, journey, work_run_id, agent_id, "
            "idempotency_key"
        ).eq("portal_key", "vidros_lanternas").order(
            "created_at", desc=True).limit(200).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VIGIA-PORTAL] indisponível: {type(e).__name__}")
        return 0

    agora = datetime.now(timezone.utc)
    for job in (res.data or []):
        try:
            # 0) 🔴 SPEC-EXTRA-001.10.1 C4 — parada TÉCNICA com sessão jovem:
            # antes de chamar gente, o robô relê o pedido pelo estado real. O
            # resultado chega pelo job da releitura (que este vigia entrega).
            if pedir_releitura(job, agora):
                if await pedir_a_releitura(cliente, job, agora):
                    tratados += 1
                    logger.warning(f"[VIGIA-PORTAL] job {job.get('id')} -> releitura_pedida")
                    continue
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
                # ⚠️ Mensagem VAZIA não sai (os achados "só para a equipe"
                # devolvem ""): mandar "" é ruído no melhor caso e erro de API
                # no pior.
                if telefone and pode_falar and str(achado["para_o_segurado"] or "").strip():
                    wa.send_message(telefone, achado["para_o_segurado"], integracao)
                elif telefone:
                    logger.info("[VIGIA-PORTAL] 🔇 agente em silêncio — só a equipe é avisada")

            # 2) a equipe, com o dossiê pronto.
            from app.tasks.dispatch_watchdog import _support_alert
            await _support_alert(company_id, achado["para_o_suporte"], wa, integracao)

            # 2b) 🔴 P-PILOTO-08 — a tela que ninguém conhece vira FILA.
            #
            # 📊 `tela_cega` (SPEC-087) só era escrita pelo corredor de URA; o
            # worker do navegador gravava `debug_dom` num jsonb que ninguém
            # varria. Aqui, FORA da janela do atendimento; dentro dela quem
            # registra é a própria `portal_tool` — a mesma função pura decide
            # nos dois lados, e a marca em `evidence` garante UMA linha por job.
            #
            # ⛔ Falhar aqui não pode derrubar o aviso ao segurado, que já saiu.
            await _aprender_com_a_tela_cega(cliente, company_id, job)

            # 2c) 🔴 SPEC-EXTRA-001.10.1 — quem ENTREGA fecha o run. Fora da
            # janela dos 150 s (e na releitura, que não tem tool esperando) o
            # run do pedido ficava parado em "rodando". A regra é a MESMA da
            # tool (`portal_tool.fechar_work_run`), e só para job TERMINAL.
            # ⚠️ Job que a tool ENTREGOU já teve o run fechado por ela.
            if (str(job.get("status") or "") in TERMINAIS and job.get("work_run_id")
                    and not (job.get("evidence") or {}).get("entregue_ao_agente")):
                try:
                    from app.agents.tools.portal_tool import fechar_work_run

                    fechar_work_run(company_id, str(job["work_run_id"]), job)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[VIGIA-PORTAL] run nao fechado: {type(e).__name__}")

            # 3) marca, para não repetir.
            # 🔴 P5: mesmo padrao da tool — funde na evidence RELIDA e filtra
            # por `company_id`. Regravar o dicionario que veio do SELECT de 200
            # linhas apaga o que a tool escreveu nesse meio-tempo (a marca
            # `entregue_ao_agente` inclusive), e um UPDATE sem `company_id` e um
            # UPDATE que confia no id para isolar tenant.
            _atual = dict(job.get("evidence") or {})
            try:
                _lido = (cliente.table("portal_jobs").select("evidence")
                         .eq("id", job["id"]).eq("company_id", company_id)
                         .limit(1).execute())
                _linhas = getattr(_lido, "data", None) or []
                if _linhas and isinstance(_linhas[0].get("evidence"), dict):
                    _atual = dict(_linhas[0]["evidence"])
            except Exception:  # noqa: BLE001
                pass
            cliente.table("portal_jobs").update({
                "evidence": {**_atual,
                             "vigia_avisou_em": agora.isoformat(),
                             "vigia_motivo": achado["motivo"]},
            }).eq("id", job["id"]).eq("company_id", company_id).execute()
            tratados += 1
            logger.warning(f"[VIGIA-PORTAL] job {job.get('id')} -> {achado['motivo']}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[VIGIA-PORTAL] falha ao tratar job: {type(e).__name__}")
    return tratados
