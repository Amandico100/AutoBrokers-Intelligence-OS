"""Heartbeats e REGISTRO dos trabalhadores digitais (SPEC-036 Etapa 1 · SPEC-088 BLOCO A).

Cada task (Vigia/Sentinela, Follow-up, Garimpo, Auditor, Sugestões, Espelho via
router) registra pulso + contador de ações no Redis — a Central de Agentes do
portal admin lê daqui. Best-effort: nunca derruba a task.

🔴 SPEC-088 BLOCO A: `AGENT_TASKS` deixou de ser lista de tuplas `(id, nome, desc)`
e passou a ser o **registro único** dos trabalhadores digitais. Além do nome e da
descrição, cada linha declara:

    grupo               observa | atende_agora | mantem_rota | aprende_avisa
    cor                 🔴 saiu do frontend (`page.tsx` COLORS) e vive AQUI — uma lista só
    eixo                {"pulso": "redis"|"work_runs", "workflow_keys": (...)}
                        pulso = de onde vem o "rodou"; workflow_keys = de onde vem o TRABALHO
    fonte_de_producao   tupla de `Fonte` (o `last_success` do agente) ou **None EXPLÍCITO**
    cadencia_esperada_s de quanto em quanto tempo ele DEVIA PRODUZIR; None se não se sabe
    cadencia_pulso_s    de quanto em quanto tempo o LAÇO DELE devia PULSAR; None quando o
                        pulso não é de laço (é dirigido por tráfego) — e aí ele cai na
                        `cadencia_esperada_s`
    k                   multiplicador do limiar: limiar_s = k × cadência DELE
    desligado_quando    None, {"agents_attendance_all_inactive": True} ou
                        {"env_falso": "NOME_DA_CHAVE"}
    fonte_rotulo        o nome HUMANO do que ele produz ("as conversas capturadas") —
                        ⛔ nunca nome de tabela nem de coluna: é o que a tela mostra

🔴 **`cadencia_pulso_s` nasceu na rodada de conserto da SPEC-088**, e o defeito que ela
mata tem nome: um agente sem `cadencia_esperada_s` (porque a produção dele depende de
tráfego, não de relógio) ficava ⚫ NÃO MEDIDO **para sempre** — inclusive depois de morto.
📊 O Vigia/Sentinela roda a cada 20 s (`buffer_processor.py:113`) e não tinha como ficar
🟡 nem 🔴: o laço dele podia estar parado há uma semana e o card diria "não medido".
**Com a cadência do laço declarada, a morte vira 🔴 PARADO.**

⛔ **Não é uma tabela nova.** `max(coluna)` da tabela que o agente já escreve **é** o
histórico. Uma tabela `agent_health` seria um segundo lugar para a verdade (CLAUDE.md §5).

⚠️ `Agente` é um `NamedTuple` cujos TRÊS primeiros campos continuam sendo
`(id, nome, descricao)`: `admin_atlas.py:935` (`{t[0]: t[1] for t in AGENT_TASKS}`) e os
testes da SPEC-040 que fazem `t[0]` seguem funcionando sem uma linha de mudança.
Quem precisa da lista antiga inteira chama `agent_tasks_legacy()`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

_KEY = "spec034:heartbeat:{task}"
_TTL = 7 * 86400

# --------------------------------------------------------------------------- #
# Os grupos — por propósito para a corretora, não por tecnologia (SPEC-088 §3 ⑥)
# --------------------------------------------------------------------------- #
# 🔴 A ORDEM É A DA URGÊNCIA PARA O SEGURADO, não a alfabética nem a histórica:
# `atende_agora` vem PRIMEIRO porque é o único grupo em que alguém está esperando
# neste minuto. Um painel que abre pelo que aprendeu ontem enterra o que está
# doendo agora — e a tela lê esta tupla na ordem em que ela está escrita.
GRUPOS: Tuple[Tuple[str, str, str], ...] = (
    ("atende_agora", "ATENDE AGORA", "alguém está esperando neste minuto"),
    ("observa", "OBSERVA E REGISTRA", "o que aconteceu ficou gravado"),
    ("mantem_rota", "MANTÉM A ROTA CERTA", "a seguradora mudou e nós acompanhamos"),
    ("aprende_avisa", "APRENDE E AVISA", "ontem virou conserto e recomendação"),
)


class Fonte(NamedTuple):
    """De onde sai o `last_success` de um trabalhador.

    `tipo`:
      "tabela"            → max(greatest(colunas)) da `tabela`, com `filtro` opcional
      "work_runs_do_eixo" → max(work_runs.finished_at) status='completed' dos workflow_keys DELE
      "artifacts_do_eixo" → max(artifacts.created_at) cujos work_run_id caem nos workflow_keys DELE
    """

    tipo: str
    rotulo: str
    tabela: Optional[str] = None
    colunas: Tuple[str, ...] = ()
    # {"coluna": str, "op": "eq"|"like"|"in", "valor": Any}
    filtro: Optional[Dict[str, Any]] = None


class Agente(NamedTuple):
    """Uma linha do registro. Os 3 primeiros campos são a tupla histórica."""

    id: str
    nome: str
    descricao: str
    grupo: str
    cor: str
    eixo: Dict[str, Any]
    # 🔴 None EXPLÍCITO = "sem tabela própria" → o card sai ⚫ NÃO MEDIDO, nunca 🟢
    fonte_de_producao: Optional[Tuple[Fonte, ...]]
    cadencia_esperada_s: Optional[int]
    desligado_quando: Optional[Dict[str, Any]]
    k: int = 2
    #: de quanto em quanto tempo o LAÇO dele devia pulsar (None = não é laço de relógio)
    cadencia_pulso_s: Optional[int] = None
    #: o nome humano do que ele entrega. ⛔ Sem tabela, sem coluna, sem `_`.
    fonte_rotulo: Optional[str] = None


def _redis(workflow_keys: Tuple[str, ...] = ()) -> Dict[str, Any]:
    return {"pulso": "redis", "workflow_keys": workflow_keys}


def _por_runs(workflow_keys: Tuple[str, ...]) -> Dict[str, Any]:
    return {"pulso": "work_runs", "workflow_keys": workflow_keys}


def _tab(rotulo: str, tabela: str, *colunas: str, filtro: Optional[Dict[str, Any]] = None) -> Fonte:
    return Fonte(tipo="tabela", rotulo=rotulo, tabela=tabela, colunas=tuple(colunas), filtro=filtro)


_DESLIGA_COM_ATENDIMENTO = {"agents_attendance_all_inactive": True}


def _desliga_com_env(chave: str) -> Dict[str, Any]:
    """⚪ quando a variável `chave` está ausente ou falsa.

    🔴 SPEC-088 (conserto C7): 📊 `playbook_tailor.py:145` faz
    `if not auto_apply_ligado(): return 0` — ele corta ANTES do pulso, e
    📊 `ALFAIATE_AUTO_APPLY` não está em nenhuma config do repositório
    (`grep -rn ALFAIATE_AUTO_APPLY --include=*.yml --include=*.env* .` → 0).
    O card do Alfaiate ficava 🔴 PARADO para sempre, com um motivo que não
    citava a chave — o operador via "morto" onde o certo era "desligado, e
    quem liga é o Founder".
    """
    return {"env_falso": str(chave)}

# --------------------------------------------------------------------------- #
# 📊 AS FONTES, MEDIDAS EM 03/09/2026 (produção `dcajcvlzcjbmyapmklil`)
#
# Critério (SPEC-088 BLOCO A): a tabela em que o MÓDULO do agente faz INSERT e que
# nenhum outro agente escreve. Se nenhuma, `None` — e o card diz ⚫ "sem tabela própria".
#
#   espelho          → `dispatch_mirror.py` insere em `messages` (:73) e `conversations`
#                      (:155); 📊 `grep -rln 'table("messages").insert'` = 4 módulos
#                      (chat.py, webhook.py, espelho_chat.py, dispatch_mirror.py).
#                      Não é exclusiva → None.
#   vigia_sentinela  → 🔴 CORRIGIDO em 03/09 (rodada de conserto): "o módulo não faz
#                      INSERT" media a ferramenta errada. Ele escreve VIA SERVIÇO —
#                      `dispatch_watchdog.py:408` → `registrar_ato_do_agente(agente=
#                      "sentinela")` → `work_events` com `event_type='agente.sentinela'`.
#                      📊 `grep -rn 'agente="sentinela"' backend/app` = 1 → EXCLUSIVA.
#   cerebro          → `dispatch_router.py` insere `work_runs` (:548), `work_events` (:571)
#                      e `work_steps` (:1042) — as três são do motor de trabalho inteiro,
#                      não dele. Mas a MARCA é: `event_type='agente.cerebro'`
#                      (:2476 e :2566). 📊 `grep -rn 'agente="cerebro"'` = 2, no mesmo módulo.
#   conselho         → 📊 `grep -n 'table("' backend/app/services/agent_council.py` = 0 → None.
#
# 🔴 A LIÇÃO QUE ISTO DEIXA (CLAUDE.md §9.4, corolário do dialeto): `grep '.insert('` no
# ARQUIVO do agente responde "este arquivo escreve?", não "este agente produz?". Um
# módulo que delega a escrita a um serviço produz igual — e a prova é a MARCA que só ele
# grava, não a linha de INSERT. Duas fontes caíram nesse buraco.
# --------------------------------------------------------------------------- #

AGENT_TASKS: List[Agente] = [
    # ---------------------------------------------------------------- OBSERVA
    Agente(
        "observador", "Observador",
        "Observa em silêncio os atendimentos com as seguradoras e captura cada tela, botão e formulário nativo — nunca envia nada.",
        grupo="observa", cor="#7FB7E8", eixo=_redis(),
        # 📊 observed_events: 28.220 linhas, última 26/08 13:52. Intervalo entre linhas
        # em 14 dias (`lag(created_at)`, 185 linhas): máximo 2d17h31 (2.717h em segundos:
        # 235.891) — o buraco do canal parado em 26/08. Cadência diária × k=2 = 48 h.
        fonte_de_producao=(_tab("observed_events.created_at", "observed_events", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        # o pulso nasce na chegada da mensagem (`observer_intake.py:176`), não num laço
        cadencia_pulso_s=None,
        fonte_rotulo="as telas capturadas nos atendimentos",
    ),
    Agente(
        "tecelao", "Tecelão",
        "Costura as observações em mapas de rota fiéis à sequência real de cada seguradora.",
        grupo="observa", cor="#B48EAD", eixo=_redis(),
        # 🔴 O FILTRO É O CONSERTO. Tecelão e Cartógrafo declaravam `ura_maps` INTEIRA, e
        # duas fontes iguais são uma fonte que mente: o card de quem não trabalha herda a
        # produção de quem trabalha. 📊 03/09/2026,
        # `SELECT source, count(*), max(created_at) FROM ura_maps GROUP BY 1`:
        #   observed 321 (26/08 14:07) · cartographer_stopped 2 (14/07) · cartographer 1 (14/07)
        # Sem filtro, o Cartógrafo — parado desde 14/07 — sairia 🟢 com o mapa do Tecelão.
        # ⚠️ O `source='observed'` é o que o `weaver.py:897` grava, e só ele.
        # 📊 Intervalo entre mapas `observed` (321 linhas, 60 dias): máximo 4d22h31.
        fonte_de_producao=(_tab("ura_maps.created_at (tecidos da observação)", "ura_maps",
                                "created_at",
                                filtro={"coluna": "source", "op": "eq", "valor": "observed"}),),
        cadencia_esperada_s=604800, desligado_quando=None, k=2,
        cadencia_pulso_s=None,  # pulsa depois do INSERT do mapa (`weaver.py:904`)
        fonte_rotulo="os mapas de rota tecidos da observação",
    ),
    Agente(
        "espelho", "Espelho",
        "Espelha toda conversa com seguradora no banco e no dashboard, em tempo real.",
        grupo="observa", cor="#7FB7E8", eixo=_redis(),
        fonte_de_producao=None,  # 📊 medido: `messages`/`conversations` têm 4 escritores
        cadencia_esperada_s=None, desligado_quando=None, k=2,
        # ⚠️ E o pulso dele TAMBÉM não é de laço: `dispatch_mirror.py:90` pulsa quando
        # chega mensagem de acionamento. 📊 `grep -n "dispatch_mirror" backend/app/tasks/*.py`
        # = 0 — não há job periódico dele. Sem laço não há cadência de pulso honesta, e
        # inventar uma faria o card ficar 🔴 num dia sem acionamento. Fica ⚫, e a
        # pendência é ARRANJAR uma fonte, não inventar um relógio.
        cadencia_pulso_s=None,
        fonte_rotulo=None,
    ),
    Agente(
        "espelho_atendimento", "Espelho de Atendimento",
        "Captura as conversas de trabalho da equipe da corretora com os segurados — matéria-prima dos playbooks de conduta e knowledge cards (PII isolada, nunca no RAG).",
        grupo="observa", cor="#43C08C", eixo=_redis(),
        # 📊 attendance_transcripts: 156.917 linhas, última 03/09 01:39.
        # 🔴 A cadência era 💭 3600 s, NUNCA MEDIDA — e 1 h × k=2 = 2 h de limiar contra
        # uma captura dirigida por tráfego. Medido em 03/09/2026 com `lag(created_at)` na
        # janela em que o canal esteve de pé (17→26/08, 6.135 linhas):
        #     intervalo MÁXIMO 20h52 (75.166 s)  ·  p99 20 min  ·  médio 2 min 16
        # O máximo é a noite e o fim de semana — a corretora dorme. Com 3.600 s o card
        # ficava 🔴 TODA NOITE num agente saudável, que é o defeito §1.6 reconstruído.
        # 1 dia × k=2 = 48 h ≥ 1,5 × 20h52. ⚠️ O buraco de 7 dias (26/08→02/09) NÃO entra
        # na conta: foi o canal inteiro parado, e ali o 🔴 é a resposta certa.
        fonte_de_producao=(_tab("attendance_transcripts.created_at", "attendance_transcripts", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        # 📊 `check_attendance_purge` roda de hora em hora com marcador DIÁRIO
        # (`attendance_capture.py:363-378`): o pulso sem ação sai 1×/dia.
        cadencia_pulso_s=86400,
        fonte_rotulo="as conversas da equipe com os segurados",
    ),
    Agente(
        "cartografo", "Cartógrafo",
        "Mapeia os fluxos de URA das seguradoras (exploração ativa — só quando não há tráfego real).",
        grupo="observa", cor="#74ACE8", eixo=_redis(),
        # 🔴 O OUTRO LADO DO CONSERTO C1. `save_proposed_map(..., source="cartographer")`
        # e `source="cartographer_stopped"` (`admin_spec034.py:cartographer_stop`) são o
        # que ELE grava — o `like` cobre os dois e nenhum mapa do Tecelão.
        # 📊 3 linhas, última 14/07/2026: 51 dias de silêncio. Com a fonte compartilhada
        # este card saía 🟢 pelo trabalho do vizinho; agora sai 🔴, que é a verdade.
        fonte_de_producao=(_tab("ura_maps.created_at (exploração ativa)", "ura_maps",
                                "created_at",
                                filtro={"coluna": "source", "op": "like",
                                        "valor": "cartographer%"}),),
        cadencia_esperada_s=604800, desligado_quando=None, k=2,
        cadencia_pulso_s=None,  # exploração é disparada à mão pelo Founder, não por laço
        fonte_rotulo="os mapas de rota da exploração ativa",
    ),
    # ----------------------------------------------------------- ATENDE AGORA
    Agente(
        "vigia_sentinela", "Vigia + Sentinela",
        "Vigia o desfecho de todo acionamento; a Sentinela destrava conversas paradas na URA.",
        grupo="atende_agora", cor="#E2A94F", eixo=_redis(),
        # 🔴 ELE PASSOU A TER FONTE. O `grep -n '\.insert(' backend/app/tasks/dispatch_watchdog.py`
        # continua dando 0 — mas o módulo escreve VIA SERVIÇO, e isso conta:
        # 📊 `dispatch_watchdog.py:408` chama `registrar_ato_do_agente(agente="sentinela")`,
        # que insere em `work_events` com `event_type='agente.sentinela'`
        # (`dispatch_router.py:571`). 📊 `grep -rn 'agente="sentinela"' backend/app` = 1
        # ocorrência: a marca é EXCLUSIVA do módulo dele.
        # 📊 03/09/2026: `SELECT event_type, count(*) FROM work_events WHERE event_type
        # LIKE 'agente.%' GROUP BY 1` → [] (zero). Nenhum acionamento travou desde a
        # SPEC-085 — "nunca produziu" é o fato, e agora ele está escrito no card.
        # ⚠️ `cadencia_esperada_s` fica None DE PROPÓSITO: destravamento é dirigido por
        # tráfego, não por relógio. Declarar 1×/dia pintaria 🔴 num dia calmo, que é
        # alarme falso — e alarme falso é como se ensina a ignorar alarme.
        fonte_de_producao=(_tab("work_events.created_at (destravamentos da Sentinela)",
                                "work_events", "created_at",
                                filtro={"coluna": "event_type", "op": "eq",
                                        "valor": "agente.sentinela"}),),
        cadencia_esperada_s=None, desligado_quando=_DESLIGA_COM_ATENDIMENTO, k=2,
        # 🔴 E ESTE É O CONSERTO C3. 📊 `buffer_processor.py:113`: o job
        # `dispatch_watchdog_check` roda a cada 20 s. Sem esta linha o card dele era ⚫
        # para sempre — o laço podia estar morto há uma semana e a tela diria "não medido".
        cadencia_pulso_s=20,
        fonte_rotulo="os acionamentos destravados pela Sentinela",
    ),
    Agente(
        "cerebro", "Cérebro v2",
        "Decide nos desvios: lê o Mapa da URA e escolhe a opção que avança para o objetivo.",
        grupo="atende_agora", cor="#43C08C",
        # 📊 `acionamento.seguradora`: 4 runs em 30d, sem @registrar_workflow no repo (P-088-KEYS)
        eixo=_redis(("acionamento.seguradora",)),
        # 🔴 Mesma descoberta do Vigia: 📊 `dispatch_router.py:2476` e `:2566` chamam
        # `registrar_ato_do_agente(agente="cerebro")` → `work_events` com
        # `event_type='agente.cerebro'`. As três tabelas do motor (`work_runs`,
        # `work_events` sem filtro, `work_steps`) continuam NÃO sendo dele; a MARCA é.
        # 📊 03/09/2026: zero linhas `agente.%` em 35.672 eventos.
        fonte_de_producao=(_tab("work_events.created_at (redações do Cérebro)",
                                "work_events", "created_at",
                                filtro={"coluna": "event_type", "op": "eq",
                                        "valor": "agente.cerebro"}),),
        # ⚠️ Sem cadência e sem laço: ele só decide quando a seguradora responde. 📊 Não
        # há job dele em `buffer_processor.py` (`grep -n dispatch_router` = 1, e é a
        # reconciliação de órfãos, que não pulsa). Pulso e produção param juntos quando
        # não há acionamento — e é por isso que o ⚪ DESLIGADO dele continua valendo.
        cadencia_esperada_s=None, desligado_quando=_DESLIGA_COM_ATENDIMENTO, k=2,
        cadencia_pulso_s=None,
        fonte_rotulo="as respostas que o Cérebro redigiu à seguradora",
    ),
    # ⚠️ INCOMPLETO, e a descrição diz isso.
    #
    # 📊 03/08/2026: ele PERGUNTA ao segurado se o prestador chegou — e
    # **ninguém lê a resposta**. Ela cai no agente de atendimento comum, que não
    # tem acesso à sessão do acionamento (a chave do acionamento é o telefone da
    # SEGURADORA; o do cliente nunca casa).
    #
    # A descrição antiga prometia "confere se o prestador chegou". Perguntar não
    # é conferir. E o card ficava VERDE, porque o critério da Central era só "o
    # laço rodou". Com a SPEC-088 o critério é o par pulso × produção. Ver P-70.
    Agente(
        "followup", "Follow-up",
        "Pós-acionamento: PERGUNTA ao segurado se o prestador chegou e manda o encerramento. ⚠️ A resposta do cliente ainda não é lida por ninguém — o ciclo não fecha (P-70).",
        grupo="atende_agora", cor="#43C08C", eixo=_redis(),
        # 🔴 A SPEC declarava `platform_sends.created_at` SEM filtro e citava 19/08 19:41.
        # 📊 03/09: aquela linha é `kind='acionamento_protocolo'`, escrita pelo
        # `dispatch_router.py`, não pelo Follow-up. `platform_sends` tem 7 escritores
        # (`grep -rln platform_sends backend/app`). O Follow-up grava
        # `acionamento_followup`/`acionamento_encerramento` (`dispatch_followup.py:322`)
        # e 📊 `SELECT kind, count(*) FROM platform_sends GROUP BY 1` → billing 4,
        # acionamento_protocolo 1. **Zero.** Sem o filtro, o card dele ficaria verde com a
        # produção de outro agente — que é exatamente o defeito desta SPEC. P-088-03.
        fonte_de_producao=(_tab(
            "platform_sends.created_at (kind de follow-up)", "platform_sends", "created_at",
            filtro={"coluna": "kind", "op": "in",
                    "valor": ("acionamento_followup", "acionamento_encerramento")},
        ),),
        cadencia_esperada_s=86400, desligado_quando=_DESLIGA_COM_ATENDIMENTO, k=2,
        # 📊 `buffer_processor.py:103`: `dispatch_followup_check` a cada 60 s, e o
        # `beat("followup", sent)` de `dispatch_followup.py:371` é INCONDICIONAL no fim da
        # varredura. 🔴 O laço dele roda mesmo com todo atendimento inativo — e é por isso
        # que o ⚪ DESLIGADO deixou de vencer a evidência de pulso (conserto C2).
        cadencia_pulso_s=60,
        fonte_rotulo="as mensagens de acompanhamento enviadas ao segurado",
    ),
    # ------------------------------------------------------------ MANTÉM ROTA
    Agente(
        "sentinela_rotas", "Sentinela de Rotas",
        "Vigia se a seguradora mudou o menu; dispara a atualização e avisa no que for estrutural.",
        grupo="mantem_rota", cor="#74ACE8", eixo=_redis(),
        # 📊 route_drift: 17 linhas, última 26/08 14:07. `lag(created_at)` em 60 dias:
        # intervalo máximo 3d20h51 — mas drift é EVENTO, não relógio: ela varre todo dia e
        # só grava quando o menu muda. A cadência declarada mede a VARREDURA, e por isso
        # segue diária. (⚠️ hoje o card sai 🔴: o canal está parado desde 26/08.)
        fonte_de_producao=(_tab("route_drift.created_at", "route_drift", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        # 📊 `route_sentinel.py:668` pulsa SEMPRE que a varredura roda, e
        # `buffer_processor.py:193` a agenda a cada `ATLAS_INCREMENTAL_INTERVAL_MINUTES`
        # (padrão 15 min).
        cadencia_pulso_s=900,
        fonte_rotulo="as mudanças de menu detectadas nas seguradoras",
    ),
    Agente(
        "alfaiate", "Alfaiate",
        "Ajusta os playbooks quando a URA da seguradora muda — auto-aplica só o que passa no Simulador.",
        grupo="mantem_rota", cor="#B48EAD", eixo=_redis(),
        # 📊 playbook_overlays: 0 linhas, nunca. Cadência declarada de propósito (referência ②
        # da SPEC: quem NUNCA produziu tem de alertar — não há evento para comparar). P-088-02.
        fonte_de_producao=(_tab("playbook_overlays.created_at", "playbook_overlays", "created_at"),),
        cadencia_esperada_s=86400,
        # 🔴 CONSERTO C7 — ele não está parado, está DESLIGADO POR CHAVE.
        # 📊 `playbook_tailor.py:145`: `if not auto_apply_ligado(): return 0` corta antes
        # do `beat("alfaiate")` da linha 208, e 📊 `ALFAIATE_AUTO_APPLY` não aparece em
        # nenhuma config do repositório. Sem esta declaração o card ficava 🔴 PARADO para
        # sempre, com um motivo que não citava a chave — e o operador procurava defeito
        # onde havia decisão do Founder (SPEC-087 BLOCO B: "a arma foi consertada,
        # descarregada, e o gatilho fica com o Founder").
        desligado_quando=_desliga_com_env("ALFAIATE_AUTO_APPLY"), k=2,
        cadencia_pulso_s=None,  # pulsa depois do INSERT do overlay, não num laço
        fonte_rotulo="os ajustes de rota aplicados nos playbooks",
    ),
    # ---------------------------------------------------------- APRENDE E AVISA
    Agente(
        "garimpo", "Garimpo",
        "Extrai dores, desejos e pedidos das conversas dos corretores — vira insight de produto.",
        grupo="aprende_avisa", cor="#43C08C", eixo=_por_runs(("intelligence.garimpo",)),
        # 🔴 `greatest()` das DUAS tabelas e das DUAS colunas: o fluxo canônico grava
        # `intelligence_signals` e projeta em `broker_insights` (`garimpo_v3.py:106-108`),
        # a projeção é condicional ao dedupe, e no acerto de dedupe `signal_service.py:144-167`
        # move `last_seen_at`, não `created_at`. Um garimpo que só reconfirma sinais não move
        # `created_at` — e o card congelaria num agente saudável.
        # 📊 intelligence_signals source_type='garimpo': 32 linhas, última 26/08 00:05.
        # 📊 broker_insights source LIKE 'garimpo%': 270 linhas ('garimpo_v3'), última 26/08 00:05.
        fonte_de_producao=(
            _tab("intelligence_signals.last_seen_at ∪ created_at", "intelligence_signals",
                 "last_seen_at", "created_at",
                 filtro={"coluna": "source_type", "op": "eq", "valor": "garimpo"}),
            _tab("broker_insights.created_at", "broker_insights", "created_at",
                 filtro={"coluna": "source", "op": "like", "valor": "garimpo%"}),
        ),
        # 📊 03/09/2026, `lag(finished_at)` dos runs `completed` de `intelligence.garimpo`
        # em 14 dias (42 runs): intervalo MÁXIMO 1d00h01 (86.495 s), médio 7h36.
        # 1 dia × k=2 = 172.800 s ≥ 1,5 × 86.495 = 129.743. Confere.
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        # 📊 `tick.py:33` INTERVALO_GARIMPO_HORAS = 24, e o pulso dele É o eixo.
        cadencia_pulso_s=86400,
        fonte_rotulo="as dores e os pedidos garimpados nas conversas",
    ),
    Agente(
        "detector", "Detector de Sinais",
        "Varre o que acontece na plataforma e levanta sinais de risco e de oportunidade antes de alguém pedir.",
        grupo="aprende_avisa", cor="#8FBF7A", eixo=_por_runs(("intelligence.detect_signals",)),
        # 📊 intelligence_signals source_type='detector': 59 linhas, última 03/09 02:03
        fonte_de_producao=(
            _tab("intelligence_signals.last_seen_at ∪ created_at", "intelligence_signals",
                 "last_seen_at", "created_at",
                 filtro={"coluna": "source_type", "op": "eq", "valor": "detector"}),
        ),
        # 🔴 CONSERTO C6 — a cadência era 💭 3.600 s e NUNCA foi medida.
        # 📊 03/09/2026, `lag()` sobre `greatest(created_at, last_seen_at)` dos sinais
        # `source_type='detector'` em 14 dias (16 sinais):
        #     intervalo MÁXIMO 1d02h56 (96.982 s)  ·  médio 19h36
        # Ele RODA de hora em hora, mas só PRODUZ sinal quando acha alguma coisa — e com
        # 3.600 s × k=2 = 2 h o card ficava 🔴 mais de 20 h por dia num agente saudável.
        # 1 dia × k=2 = 172.800 s ≥ 1,5 × 96.982 = 145.473. Confere.
        # ⚠️ É o par que a SPEC-088 existe para separar: a cadência do LAÇO é uma hora,
        # a da PRODUÇÃO é um dia, e confundir as duas é o defeito §1.3 ao contrário.
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        # 📊 `tick.py:32` INTERVALO_DETECCAO_HORAS = 1; `lag(finished_at)` dos 1.008 runs
        # `completed` em 14 dias: intervalo máximo 01h04 (3.891 s). 3.600 × k=2 = 7.200 ≥
        # 1,5 × 3.891 = 5.837. Confere.
        cadencia_pulso_s=3600,
        fonte_rotulo="os sinais de risco e de oportunidade levantados",
    ),
    Agente(
        "auditor", "Auditor",
        "Dá nota de qualidade a cada conversa e detecta regressões nos corredores.",
        # ⛔ NÃO liga a `intelligence.investigate_quality`: 📊 0 runs em toda a história.
        # O pulso é o de `conversation_auditor.py:180` (Redis, 1×/dia); trabalho vazio.
        grupo="aprende_avisa", cor="#E2A94F", eixo=_redis(),
        # 📊 conversation_scorecards: 688 linhas, última 03/09 00:04. `lag(created_at)`
        # em 14 dias (230 linhas): intervalo máximo 7d22h44 — o buraco do canal parado,
        # não a cadência dele. A varredura é DIÁRIA por construção (marcador
        # `auditor:last_run` em `conversation_auditor.py:141`), e é isso que está declarado.
        fonte_de_producao=(_tab("conversation_scorecards.created_at", "conversation_scorecards", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        # 📊 o `beat("auditor")` de `conversation_auditor.py:180` fica DEPOIS do
        # `if last == today: return 0` — o pulso sai 1×/dia, não a cada 1.800 s do job.
        cadencia_pulso_s=86400,
        fonte_rotulo="as notas de qualidade dadas aos atendimentos",
    ),
    Agente(
        "sugestoes", "IA de Sugestões",
        "Envia recomendações semanais proativas às corretoras e registra as respostas.",
        grupo="aprende_avisa", cor="#7FB7E8", eixo=_redis(),
        # 📊 broker_insights source='sugestoes_ia': 0 de 270. Cadência None: não se sabe de
        # quanto em quanto tempo ele DEVIA produzir desde o cutover → ⚫, não um limiar inventado.
        fonte_de_producao=(_tab("broker_insights.created_at", "broker_insights", "created_at",
                                filtro={"coluna": "source", "op": "eq", "valor": "sugestoes_ia"}),),
        cadencia_esperada_s=None, desligado_quando=None, k=2,
        # ⚠️ E o pulso também não tem cadência: com `INTELLIGENCE_CUTOVER` ligado (padrão)
        # o `return sugestoes_desativadas()` de `proactive_suggestions.py:223` corta ANTES
        # do `beat` — de propósito (BLOCO E). Um `cadencia_pulso_s` aqui transformaria uma
        # decisão de arquitetura em alarme diário.
        cadencia_pulso_s=None,
        fonte_rotulo="as recomendações enviadas às corretoras",
    ),
    Agente(
        "conselho", "Conselho de Agentes",
        "Segunda opinião multi-modelo (GPT, Opus, Kimi, Grok) para decisões estruturais raras — liga por env, custo controlado.",
        grupo="aprende_avisa", cor="#E2A94F", eixo=_redis(),
        fonte_de_producao=None,  # 📊 medido: agent_council.py não escreve tabela nenhuma
        cadencia_esperada_s=None, desligado_quando=None, k=2,
        # ⚠️ Nem laço nem tabela: ele é chamado à mão, por env, para decisão estrutural
        # rara. ⚫ NÃO MEDIDO é a descrição correta — e um card que ficasse 🔴 por não
        # ter sido consultado esta semana seria alarme sobre o comportamento desejado.
        cadencia_pulso_s=None,
        fonte_rotulo=None,
    ),
    Agente(
        "briefing", "Briefing",
        "Escreve o resumo diário e o executivo semanal do que aconteceu na corretora — o que mudou, o que exige decisão.",
        grupo="aprende_avisa", cor="#88C0D0",
        eixo=_por_runs(("intelligence.daily_briefing", "intelligence.weekly_executive_briefing")),
        # 📊 artifacts com work_run_id desses dois keys em 7d: daily 21 · weekly 3.
        # A entrega (artifact) é a produção; o run completo é o piso quando não houver artifact.
        fonte_de_producao=(
            Fonte(tipo="artifacts_do_eixo", rotulo="artifacts.created_at (via work_run_id)"),
            Fonte(tipo="work_runs_do_eixo", rotulo="work_runs.finished_at (completed)"),
        ),
        # 📊 03/09/2026, `lag(finished_at)` dos runs `completed` em 14 dias:
        #   intelligence.daily_briefing            42 runs · intervalo máximo 1d00h05 (86.719 s)
        #   intelligence.weekly_executive_briefing  6 runs · intervalo máximo 6d23h59
        # A produção é o `max()` das DUAS chaves, então quem manda é a diária.
        # 1 dia × k=2 = 172.800 s ≥ 1,5 × 86.719 = 130.079. Confere.
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        cadencia_pulso_s=86400,  # o pulso dele É o eixo (runs completos das duas chaves)
        fonte_rotulo="os resumos diários e executivos entregues",
    ),
    Agente(
        "medidor", "Medidor de Resultados",
        "Mede se o que foi prometido aconteceu: compara o resultado esperado com o que a corretora obteve.",
        grupo="aprende_avisa", cor="#D08770", eixo=_por_runs(("intelligence.measure_outcomes",)),
        # 📊 351 runs completed em 30d, última 03/09 00:01.
        # 🔴 A SPEC declarava 💭 3600s ("horária"). Medido em 03/09 com o intervalo entre
        # runs consecutivos (`lag(created_at)`, 14 dias): 56 horas distintas em 15 dias,
        # intervalo MÁXIMO de 21.879s (6h05) — ele NÃO roda de hora em hora. Com 3600s o
        # card ficaria 🔴 três horas por dia num agente saudável, que é o defeito §1.6
        # (limiar de 900s condenando quem roda 1×/dia) reconstruído. 6h × k=2 = 12h de
        # limiar, o dobro do maior silêncio já observado.
        # 📊 Reconferido em 03/09 com `finished_at` (14 dias, 168 runs): intervalo
        # MÁXIMO 06h04 (21.859 s), médio 1h58. 21.600 × k=2 = 43.200 ≥ 1,5 × 21.859 =
        # 32.789. Confere — e bate com `tick.py:34` INTERVALO_MEDICAO_HORAS = 6.
        fonte_de_producao=(Fonte(tipo="work_runs_do_eixo", rotulo="work_runs.finished_at (completed)"),),
        cadencia_esperada_s=21600, desligado_quando=None, k=2,
        cadencia_pulso_s=21600,
        fonte_rotulo="as medições de resultado concluídas",
    ),
    Agente(
        "agrupador", "Agrupador de Demanda",
        "Junta pedidos parecidos de corretoras diferentes e mostra o que muita gente precisa da mesma coisa.",
        grupo="aprende_avisa", cor="#A3BE8C", eixo=_por_runs(("intelligence.cluster_demand",)),
        # 📊 31 runs completed em 30d, última 03/09 00:01. `lag(finished_at)` em 14 dias
        # (14 runs): intervalo MÁXIMO 1d00h02 (86.564 s), médio 23h59 — e
        # `tick.py:35` INTERVALO_CLUSTER_HORAS = 24. 1 dia × k=2 = 172.800 ≥
        # 1,5 × 86.564 = 129.846. Confere.
        fonte_de_producao=(Fonte(tipo="work_runs_do_eixo", rotulo="work_runs.finished_at (completed)"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
        cadencia_pulso_s=86400,
        fonte_rotulo="os agrupamentos de demanda concluídos",
    ),
]


# --------------------------------------------------------------------------- #
# 🔴 O registro CRESCE, ou a chave é recusada por escrito (SPEC-088 BLOCO A, gate ②)
#
# Todo `workflow_key` visto em `work_runs` nos últimos 30 dias tem trabalhador OU
# está aqui, com o motivo escrito. Lista vazia com chave sem card REPROVA.
# 📊 Medido em 03/09/2026 — chaves com run nos últimos 30 dias:
#   intelligence.detect_signals 2.097 · measure_outcomes 351 · garimpo 90 ·
#   daily_briefing 87 · cluster_demand 31 · weekly_executive_briefing 12 ·
#   bridge.routine.execute 7 · acionamento.seguradora 4
# ⚠️ `test.wf` (1 run) NÃO aparece na janela de 30 dias de hoje — é mais velho. Fica
# declarado assim mesmo: a lista descreve a decisão, não a janela.
# --------------------------------------------------------------------------- #
SEM_CARD_POR_DECISAO: Tuple[Tuple[str, str], ...] = (
    ("test.wf", "lixo de teste, 1 run em toda a história (P-088-KEYS)"),
    ("bridge.routine.execute", "ponte de rotina, contada no auxiliar"),
    ("bridge.auxiliary.execute", "ponte de auxiliar, contada no auxiliar"),
    ("bridge.portal.job", "portal worker, tela própria"),
    ("portal.operation", "portal worker, tela própria"),
    ("research.execute", "pesquisa, tela própria"),
    ("research.monitor_check", "pesquisa, tela própria"),
    ("research.site_audit", "pesquisa, tela própria"),
    ("research.business_discovery", "pesquisa, tela própria"),
    ("research.radar_weekly", "pesquisa, tela própria"),
    ("system.healthcheck", "sonda de plataforma, não é trabalhador"),
    ("intelligence.investigate_failures", "0 runs em 30 dias (medido 03/09/2026)"),
    ("intelligence.investigate_quality", "0 runs em toda a história (medido 03/09/2026)"),
    ("intelligence.memory_sweep", "0 runs em 30 dias (medido 03/09/2026)"),
)


def agente_por_id(agent_id: str) -> Optional[Agente]:
    for a in AGENT_TASKS:
        if a.id == agent_id:
            return a
    return None


def agent_tasks_legacy() -> List[Tuple[str, str, str]]:
    """A lista antiga `(id, nome, descricao)`, para quem ainda a espera inteira."""
    return [(a.id, a.nome, a.descricao) for a in AGENT_TASKS]


def workflow_keys_declarados() -> Dict[str, str]:
    """`workflow_key` → id do trabalhador que o reivindica."""
    out: Dict[str, str] = {}
    for a in AGENT_TASKS:
        for k in a.eixo.get("workflow_keys") or ():
            out[k] = a.id
    return out


def workflow_keys_sem_card(chaves_vistas) -> List[str]:
    """🔴 O gate ② do BLOCO A: as chaves que ninguém reivindicou nem recusou.

    Puro, sem I/O — o guarda passa a lista de chaves vistas em `work_runs` (30 dias)
    e recebe as órfãs, em ordem estável. Lista vazia = registro em dia.
    """
    declarados = set(workflow_keys_declarados())
    recusados = {k for k, _ in SEM_CARD_POR_DECISAO}
    vistas: List[str] = []
    for k in chaves_vistas or ():
        k = str(k or "").strip()
        if k and k not in vistas:
            vistas.append(k)
    return [k for k in vistas if k not in declarados and k not in recusados]


# --------------------------------------------------------------------------- #
# O pulso (Redis) — assinaturas MANTIDAS: 27 call sites dependem delas
# --------------------------------------------------------------------------- #
async def beat(task: str, actions: int = 0) -> None:
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        key = _KEY.format(task=task)
        raw = await redis.get(key)
        data = {}
        if raw:
            try:
                data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                data = {}
        today = datetime.now(timezone.utc).date().isoformat()
        if data.get("day") != today:
            data["day"] = today
            data["actions_today"] = 0
        data["last_run"] = datetime.now(timezone.utc).isoformat()
        data["actions_today"] = int(data.get("actions_today") or 0) + max(0, int(actions))
        await redis.set(key, json.dumps(data), ex=_TTL)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[HEARTBEAT] beat({task}) falhou: {type(e).__name__}")


async def read_all() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        for a in AGENT_TASKS:
            raw = await redis.get(_KEY.format(task=a.id))
            data = {}
            if raw:
                try:
                    data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                except Exception:  # noqa: BLE001
                    data = {}
            out.append({"id": a.id, "name": a.nome, "desc": a.descricao,
                        "last_run": data.get("last_run"), "actions_today": data.get("actions_today") or 0})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[HEARTBEAT] read_all falhou: {type(e).__name__}")
        out = [{"id": a.id, "name": a.nome, "desc": a.descricao, "last_run": None, "actions_today": 0}
               for a in AGENT_TASKS]
    return out
