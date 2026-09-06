# -*- coding: utf-8 -*-
"""A proposta de métrica vira trabalho durável — SPEC-094.1 · BLOCO D.

🔴 **ESTE MÓDULO É O PRIMEIRO CHAMADOR DE `WorkApprovalService.solicitar()` DO
PRODUTO.**

📊 Medido em 03/09/2026 (SPEC-094.1 §1.7): `solicitar()` existe desde a SPEC-055
e tem **ZERO chamadores**. A SPEC-053 §11.1 é direta — *"prompt não é gate"* — e
até hoje o gate era só a peça, sem ninguém do outro lado. Aqui ele passa a ter
um caso de uso real, e o caso de uso é o mais barato possível de propósito: uma
proposta de métrica **não executa nada**. Se este primeiro chamador estiver
errado, o pior que acontece é uma linha em `approval_requests` que ninguém
decide — e não uma mensagem que sai, um portal que age ou um dinheiro que se
move. Estrear o HITL com o efeito mais caro seria estrear no lugar errado.

## O desenho, e por que ele é assim

```
o chat propõe          `propor_metrica` (tool)  →  este módulo
o registro nasce       work_runs, workflow_key='metric.proposal', SEM fila
o humano decide        approval_requests → `decidir()` pela API admin da 055
a promoção é FORA      `python -m app.comercial.metricas.promover ...`
```

⛔ **Não existe tool de promover, e a ausência é a peça.** Modelado no MCP do
Cube (ref ①), que *"deliberately exposes no commit tool"*: remover a capacidade,
não pedir contenção. Um modelo que pudesse promover promoveria — 📊 BIRD mede o
melhor sistema em 82,28% contra 92,96% do humano, e pelo CLAUDE.md §9.5 a
resposta errada é a silenciosa.

## O run NÃO tem executor, e é por isso que não vai para a fila

Como a `claims.shadow` da 093-B: é um **registro durável**, não um trabalho
enfileirado. `criar_registro_sem_fila` grava na mesma tabela, com o mesmo enum
de status e a mesma linha do tempo em `work_events` — o que ele não tem é
outbox. 🔴 Se fosse pelo RPC `work_run_create`, o Smith Worker pegaria um run
sem handler e o marcaria `failed`: um espelho durável que MENTE, pior do que
não existir.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "metric.proposal"
OUTCOME_TYPE = "metric.proposal"
OUTCOME_TITLE = "Proposta de métrica nova"
#: O que distingue o caminho é ESTE campo, e não `source_type` — que tem CHECK
#: (`ck_work_runs_source`) e só aceita chat|routine|auxiliary|portal|api|admin|
#: system|retry|child_run. Não há "proposta" ali, e inventar um valor seria um
#: INSERT recusado.
RUNTIME_KIND = "proposta"
SOURCE_TYPE = "chat"
PREFIXO_DA_CHAVE = "metric.proposal:"

#: 🔴 O status de ESPERA do vocabulário que já existe. 📊 Medido no código, e
#: não presumido: `api/work_runs.py:314` conta
#: `_contar("work_runs", status="waiting_approval")` e `workflows.py:458,548`
#: transiciona para ele quando um passo pede humano. Inventar `proposta` como
#: status faria o painel de Work Runs deixar de contar estas linhas — e uma
#: proposta que não aparece no painel é uma proposta que ninguém decide.
#:
#: 📊 E medido TAMBÉM no banco, em 04/09/2026 (SPEC-094.1, integração), porque
#: código não é schema: `work_runs.status` não tem CHECK — é o ENUM
#: `work_run_status`, e `waiting_approval` é um dos 13 rótulos dele
#: (`draft|queued|planning|running|waiting_approval|waiting_input|paused|
#: retry_scheduled|cancelling|cancelled|failed|completed|expired`).
#:
#: ```sql
#: select a.attname, format_type(a.atttypid, a.atttypmod),
#:        (select string_agg(e.enumlabel,'|' order by e.enumsortorder)
#:           from pg_enum e where e.enumtypid = a.atttypid)
#:   from pg_attribute a join pg_class c on c.oid = a.attrelid
#:  where c.relname = 'work_runs' and a.attname = 'status';
#: ```
STATUS_DE_ESPERA = "waiting_approval"
RISCO = "low"

ACTION_TYPE = "metric.proposal"
#: 🔴 SPEC-094.1, conserto de 04/09/2026 (rodada 3). Era `"metric_proposal"`,
#: com `subject_id` = o NOME da métrica.
#:
#: 📊 O defeito medido ao vivo pelo juiz fresco: `approval_requests.subject_id`
#: é **`uuid`** (lido de `information_schema.columns`, e a fixture
#: `tests/fixtures/schema_vivo.json` guarda essa leitura). Gravar
#: `"proposta.x"` ali devolvia `22P02 invalid input syntax for type uuid` —
#: então `propor()` NUNCA gravou uma aprovação, em nenhuma corretora, desde que
#: foi escrita. O `work_run` já estava criado quando o `insert` estourava, e o
#: que sobrava no banco era um run `waiting_approval` que ninguém jamais
#: aprovaria: 📊 `c66c3bf7-539f-4c15-93d3-570aa6df88cb`, o único
#: `metric.proposal` do banco.
#:
#: ✅ O sujeito da aprovação passa a ser o `work_run`, que é a única coisa desta
#: história que TEM um uuid. O nome da métrica viaja em `request_payload` e
#: `requested_preview`, que são `jsonb` e existem para isso.
SUBJECT_TYPE = "work_run"

#: O status para onde o run vai quando a aprovação (ou o evento) não puder ser
#: escrita. ⛔ Um run `waiting_approval` sem `approval_request` é uma linha que
#: espera para sempre uma decisão que ninguém consegue tomar.
STATUS_DA_FALHA = "failed"
#: 📊 Lido do enum `work_run_status` em 04/09/2026:
#: draft·queued·planning·running·waiting_approval·waiting_input·paused·
#: retry_scheduled·cancelling·cancelled·failed·completed·expired.
CODIGO_DA_FALHA = "approval_not_written"
EVENTO_CRIADA = "metric.proposta_criada"
EVENTO_PROMOVIDA = "metric.promovida"

#: 🔴 Quem aprova, por padrão. **F-094.1-02 é uma decisão ABERTA do Founder**
#: (SPEC-094.1 §6): você, ou o dono da corretora? O default desta SPEC é o
#: Founder, e o parâmetro `aprovador` existe para que a decisão, quando vier,
#: seja uma linha de configuração e não uma reescrita.
#:
#: ⚠️ É um PAPEL, e não o id de uma pessoa: nome de gente não entra em payload
#: (CLAUDE.md §12 e SPEC-094 §2).
APROVADOR_PADRAO = "founder"
APROVADORES = ("founder", "company_owner")

#: 💭 Quanto tempo a proposta fica de pé esperando decisão. Uma semana: métrica
#: nova não é urgência, e expirar em 24h (o padrão do HITL, que foi pensado
#: para efeito externo) faria toda proposta morrer antes de alguém olhar.
VALIDADE_HORAS = 24 * 7


def _chave(company_id: str, resumo: Dict[str, Any]) -> str:
    """A chave de idempotência da proposta — **o PEDIDO INTEIRO, e não o nome.**

    🔴 SPEC-094.1, conserto de 04/09/2026. 📊 O defeito: a chave era
    `sha256(company_id + nome_sugerido)`. Dois pedidos DIFERENTES do dono que
    caíssem no mesmo `nome_sugerido` — o que é comum, porque o nome é derivado
    da pergunta e a derivação normaliza muito — recebiam
    `reused=True`. A segunda proposta era engolida, e o chat devolvia ao dono os
    **fatos e dimensões que ele acabou de pedir**, enquanto o registro guardava
    os do primeiro pedido. O texto na tela e a linha no painel discordavam, e
    nada travava.

    ⚠️ Agora entram no hash o nome **e** o conteúdo: famílias de fato,
    dimensões, base temporal e a pergunta já normalizada. Mesmo pedido, mesma
    chave — mesmo pedido duas vezes na mesma semana continua sendo UMA decisão
    para o dono tomar.

    🔴 E `company_id` continua DENTRO, além de o helper já casar pelo par
    `(company_id, idempotency_key)`: a chave viaja também para
    `approval_requests`, e lá o par não é garantido pelo índice.
    """
    corpo = json.dumps(
        {"nome_sugerido": str(resumo.get("nome_sugerido") or ""),
         "fatos": sorted(str(x) for x in (resumo.get("fatos") or ())),
         "dimensoes": sorted(str(x) for x in (resumo.get("dimensoes") or ())),
         "time_basis": str(resumo.get("time_basis") or ""),
         "pergunta_exemplo": str(resumo.get("pergunta_exemplo") or "")},
        ensure_ascii=False, sort_keys=True)
    marca = hashlib.sha256(
        ("%s|%s" % (company_id, corpo)).encode("utf-8")).hexdigest()[:16]
    return PREFIXO_DA_CHAVE + marca


def _proposta_gravada(db: Any, company_id: str, run_id: str,
                      cair_para: Dict[str, Any]) -> Dict[str, Any]:
    """O `input_payload` que está NO REGISTRO — e nunca o que acabou de chegar.

    🔴 Este é o outro lado do mesmo defeito: quando a proposta já existia, a
    função devolvia o resumo do pedido NOVO. O chat então dizia ao dono
    *"registrei sua proposta"* e listava dimensões que a linha do painel não
    tem. Quem for revisar lê uma coisa; quem pediu lembra de outra.

    ⚠️ Falha de leitura cai para o resumo do pedido, com o aviso no log: é
    melhor devolver algo do que derrubar a conversa — mas o caminho normal é o
    de cima.
    """
    try:
        cli = getattr(db, "client", db)
        r = (cli.table("work_runs").select("id, company_id, input_payload")
             .eq("id", run_id).eq("company_id", company_id).limit(1).execute())
        linhas = getattr(r, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[094.1] payload gravado nao lido (%s)",
                       type(exc).__name__)
        return dict(cair_para)
    if not linhas:
        return dict(cair_para)
    payload = dict(linhas[0].get("input_payload") or {})
    return {chave: payload.get(chave, cair_para.get(chave))
            for chave in cair_para} or dict(cair_para)


def resumo_da_proposta(proposta: Any) -> Dict[str, Any]:
    """O que a proposta leva para o registro: enums, ids e a pergunta ecoada.

    ⛔ Nenhum texto livre do modelo entra cru. `pergunta_exemplo` já chega
    normalizado e cortado por `PropostaDeMetrica` — sem pontuação, sem acento e
    com teto de tamanho — pela mesma razão pela qual `dimension` passou a ser
    lista fechada na 094: texto do LLM que entra num registro volta um dia com
    a autoridade de dado.
    """
    def _lista(nome: str):
        return [str(x) for x in (getattr(proposta, nome, ()) or ())]

    return {
        "nome_sugerido": str(getattr(proposta, "nome_sugerido", "") or ""),
        "fatos": _lista("fatos"),
        "dimensoes": _lista("dimensoes"),
        "time_basis": str(getattr(proposta, "time_basis", "") or ""),
        "parecida_com": _lista("parecida_com"),
        "pergunta_exemplo": str(getattr(proposta, "pergunta_exemplo", "") or ""),
    }


async def propor(db: Any, *, company_id: str, proposta: Any,
                 solicitante: Optional[str] = None,
                 aprovador: str = APROVADOR_PADRAO,
                 conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """Cria o `work_run`, a `approval_request` e o evento. Devolve os três ids.

    ```
    {"run_id": ..., "approval_id": ..., "reused": bool, "proposta": {...}}
    ```

    🔴 `company_id` é obrigatório e a ausência LEVANTA. O backend roda com
    service role: uma proposta sem tenant nasceria órfã, e órfã num painel
    multi-tenant é uma linha que a corretora errada abre (CLAUDE.md §7).

    ⚠️ A ordem é `run → approval → evento`, e não é indiferente: a
    `approval_request` tem `work_run_id` NOT NULL, e o evento é a linha do
    tempo — que só faz sentido depois de o que ela narra existir.

    ⛔ Este módulo **não** decide, não aprova e não promove. `decidir()` é da
    SPEC-055, pela API admin (`POST /work-runs/approvals/{id}/decide`), e a
    promoção é o CLI do BLOCO E.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        raise ValueError(
            "proposta de métrica sem `company_id`: uma proposta órfã aparece "
            "no painel da corretora errada")
    if aprovador not in APROVADORES:
        raise ValueError("aprovador fora do vocabulário: %r (F-094.1-02)"
                         % aprovador)
    resumo = resumo_da_proposta(proposta)
    nome = resumo["nome_sugerido"]
    if not nome:
        raise ValueError("proposta sem `nome_sugerido`")

    from app.services.work.runs import criar_registro_sem_fila

    chave = _chave(empresa, resumo)
    registro = await criar_registro_sem_fila(
        db,
        company_id=empresa,
        workflow_key=WORKFLOW_KEY,
        outcome_type=OUTCOME_TYPE,
        outcome_title=OUTCOME_TITLE,
        source_type=SOURCE_TYPE,
        source_id=str(solicitante) if solicitante else None,
        conversation_id=str(conversation_id) if conversation_id else None,
        runtime_kind=RUNTIME_KIND,
        status=STATUS_DE_ESPERA,
        risk_level=RISCO,
        idempotency_key=chave,
        input_payload=dict(resumo, aprovador=aprovador),
        # 🔴 SPEC-098 R8 — QUEM PEDIU VIAJA COM O TRABALHO.
        #
        # 📊 Medido em 06/09/2026: `work_runs` = 3.799 linhas com
        # `requester_user_id` preenchido em **0**. Este é o único chamador de
        # `criar_registro_sem_fila` que CONHECE a pessoa (`solicitante`) — ele já
        # a gravava em `source_id` e em `approval_requests.requested_by_user_id`,
        # e deixava vazia a coluna que existe para isso desde a SPEC-055.
        #
        # ⚠️ `source_id` é `text` e serve para reencontrar; `requester_user_id` é
        # `uuid` e é a coluna por onde se pergunta *"o que ESTA pessoa pediu?"*.
        # Ter o dado num campo de texto e a coluna certa vazia é o defeito da
        # CLAUDE.md §12.1 pelo avesso.
        requester_user_id=str(solicitante) if solicitante else None,
    )
    run_id = str((registro or {}).get("id") or "")
    if not run_id:
        raise RuntimeError("o work_run da proposta não foi criado")
    # 🔴 Proposta repetida não abre a segunda aprovação. O dono que pede a
    # mesma métrica duas vezes na mesma semana tem UMA decisão para tomar, e
    # duas linhas pendentes sobre a mesma coisa é como um painel de aprovações
    # deixa de ser lido.
    if (registro or {}).get("reused"):
        logger.info("[094.1] proposta ja existia para %s — nada duplicado", nome)
        # 🔴 O que volta é o payload GRAVADO, e não o pedido novo: é ele que o
        # revisor vai ler no painel, e o chat não pode descrever outra coisa.
        return {"run_id": run_id, "approval_id": "", "reused": True,
                "proposta": _proposta_gravada(db, empresa, run_id, resumo)}

    from app.services.work.approvals import WorkApprovalService

    servico = WorkApprovalService(db)
    try:
        linha = _solicitar(servico, empresa, run_id, nome, aprovador, resumo,
                           chave, solicitante)
    except Exception as exc:  # noqa: BLE001
        # 🔴 NADA ÓRFÃO. A ordem é `run -> approval -> evento` porque a
        # `approval_request` tem `work_run_id` NOT NULL — mas se a segunda
        # perna falha, a primeira não pode ficar de pé esperando uma decisão
        # que não existe. O run vai para `failed`, com o motivo escrito.
        _marcar_falha(db, empresa, run_id, exc)
        raise

    approval_id = str((linha or {}).get("id") or "")

    _evento(db, empresa, run_id, EVENTO_CRIADA, resumo,
            "Proposta de métrica registrada para revisão: %s" % nome)
    logger.info("[094.1] proposta %s criada run=%s approval=%s",
                nome, run_id, approval_id or "-")
    return {"run_id": run_id, "approval_id": approval_id, "reused": False,
            "proposta": resumo}


def _solicitar(servico: Any, empresa: str, run_id: str, nome: str,
               aprovador: str, resumo: Dict[str, Any], chave: str,
               solicitante: Optional[str]) -> Dict[str, Any]:
    """A chamada ao HITL da SPEC-055. ⚠️ Separada para que a falha dela seja
    capturável sem envolver o `insert` do run na mesma cláusula."""
    return servico.solicitar(
        company_id=empresa,
        work_run_id=run_id,
        work_step_id=None,
        action_type=ACTION_TYPE,
        subject_type=SUBJECT_TYPE,
        # 🔴 O uuid do RUN, e nunca o nome da métrica: a coluna é `uuid`.
        subject_id=run_id,
        preview={
            "titulo": "Registrar a métrica %s?" % nome,
            # 🔴 O nome vive AQUI — em `preview`/`requested_preview` e em
            # `action_payload`/`request_payload`, que são `jsonb`. É por esta
            # chave que a tela de revisão sabe qual métrica está em jogo.
            "metrica_proposta": nome,
            "aprovador": aprovador,
            "o_que_e": ("uma métrica que o dono pediu e o registry não tem. "
                        "Aprovar NÃO calcula nada: quem registra a definição é "
                        "gente, seguindo docs/canon/COMO-NASCE-UM-RELATORIO.md"),
            **resumo,
        },
        action_payload={"workflow_key": WORKFLOW_KEY, **resumo},
        risk_level=RISCO,
        idempotency_key=chave,
        requested_by_user_id=str(solicitante) if solicitante else None,
        validade_horas=VALIDADE_HORAS,
    )


def _marcar_falha(db: Any, company_id: str, run_id: str,
                  exc: BaseException) -> bool:
    """O run que não conseguiu aprovação vai para `failed`. Nunca levanta.

    🔴 SPEC-094.1, conserto de 04/09/2026 (rodada 3). 📊 O que este `UPDATE`
    impede está medido no banco: **um** run `metric.proposal` existia, em
    `waiting_approval`, **sem nenhuma `approval_request`** — porque o `insert`
    da aprovação estourava depois de o run já estar gravado. Um run parado à
    espera de uma decisão que ninguém consegue tomar é pior que run nenhum: ele
    ocupa o painel da corretora afirmando que há trabalho em curso.

    ⚠️ Ele engole a própria exceção de propósito: a que interessa a quem chamou
    é a ORIGINAL, e trocá-la por *"não consegui marcar como falho"* esconderia
    a causa. O filtro por `company_id` está no CÓDIGO (CLAUDE.md §7).
    """
    try:
        cli = getattr(db, "client", db)
        (cli.table("work_runs")
         .update({"status": STATUS_DA_FALHA,
                  "error_code": CODIGO_DA_FALHA,
                  "error_message": ("a aprovação da proposta não pôde ser "
                                    "registrada (%s)" % type(exc).__name__)[:300],
                  "finished_at": datetime.now(timezone.utc).isoformat()})
         .eq("id", run_id).eq("company_id", company_id).execute())
        return True
    except Exception as outra:  # noqa: BLE001
        logger.warning("[094.1] run %s ficou orfao (%s)", run_id,
                       type(outra).__name__)
        return False


#: 💭 Quantas propostas voltam numa leitura. Uma tela de revisão não lê mais
#: que isso de uma vez, e um teto escrito é o que impede a leitura de uma
#: corretora grande de virar a tabela inteira em memória.
TETO_DA_LISTA = 50


def listar_propostas(db: Any, *, company_id: str,
                     limite: int = TETO_DA_LISTA) -> list:
    """As propostas de métrica DESTA corretora. Nunca as de outra.

    🔴 O `company_id` é **obrigatório e keyword-only**, e o filtro está no
    CÓDIGO. O backend roda com service role: RLS sem policy não protege nada
    contra um filtro que ficou de fora (CLAUDE.md §7). Uma listagem sem tenant
    aqui seria a proposta de uma corretora aparecendo na revisão de outra —
    junto com a pergunta que a originou, que é dado de negócio.

    ⚠️ A leitura é a única deste módulo, e ela devolve o `input_payload` (o
    resumo da proposta: enums, ids e a pergunta já normalizada) — nunca uma
    junção com `approval_requests`, que tem dono, decisão e prazo próprios e é
    da SPEC-055.

    ⛔ Não escreve, não decide e não promove. É leitura.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        raise ValueError(
            "listagem de propostas sem `company_id`: uma leitura sem tenant "
            "devolve a proposta da corretora errada (CLAUDE.md §7)")
    try:
        cli = getattr(db, "client", db)
        r = (cli.table("work_runs")
             .select("id, company_id, status, created_at, input_payload")
             .eq("company_id", empresa)
             .eq("workflow_key", WORKFLOW_KEY)
             .order("created_at", desc=True)
             .limit(int(limite)).execute())
        linhas = getattr(r, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[094.1] propostas nao lidas (%s)", type(exc).__name__)
        return []
    saida = []
    for linha in linhas:
        # 🔴 O cinto: se a fonte devolver linha de outra corretora — filtro
        # esquecido no cliente, view mal escrita, mock de teste —, ela NÃO sai
        # daqui. Custa uma comparação e é a última porta antes da tela.
        if str(linha.get("company_id") or "") != empresa:
            continue
        payload = dict(linha.get("input_payload") or {})
        saida.append({
            "run_id": str(linha.get("id") or ""),
            "company_id": empresa,
            "status": str(linha.get("status") or ""),
            "created_at": str(linha.get("created_at") or ""),
            "nome_sugerido": str(payload.get("nome_sugerido") or ""),
            "parecida_com": [str(x) for x in (payload.get("parecida_com") or ())],
            "pergunta_exemplo": str(payload.get("pergunta_exemplo") or ""),
        })
    return saida


def _evento(db: Any, company_id: str, run_id: str, tipo: str,
            payload: Dict[str, Any], mensagem: str,
            actor_type: str = "agent") -> bool:
    """Uma linha em `work_events`. Nunca levanta: o registro já existe.

    🔴 `actor_type='agent'` — 📊 o CHECK `ck_work_events_actor` aceita
    `system|worker|user|agent|admin|provider`, e quem propôs foi o agente. Pôr
    `system` aqui faria a linha do tempo dizer que a máquina de infraestrutura
    propôs a métrica, que é outra história.

    ⛔ O payload leva SÓ enums e ids: `metric_id`, famílias de fato, base
    temporal. Nada de nome de pessoa, e nada de frase do modelo.
    """
    linha = {
        "company_id": company_id,
        "work_run_id": run_id,
        "event_type": tipo,
        "actor_type": actor_type,
        "severity": "info",
        "message_human": mensagem[:300],
        "payload_redacted": json.loads(json.dumps(payload, ensure_ascii=False)),
    }
    try:
        cli = getattr(db, "client", db)
        cli.table("work_events").insert(linha).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[094.1] evento '%s' nao registrado (%s)", tipo,
                       type(exc).__name__)
        return False
