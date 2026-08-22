"""Motor de acionamento de seguradora (SPEC-017 P4 / S17-5, S17-6).

Máquina de estados POR CASO que conversa com a seguradora usando um playbook:
  preparing -> ready_to_send -> [GATE] -> ura -> human_phase -> captured
                                   \\-> qualquer divergência -> needs_human

Regras duras:
- GATE (S17-6): `INSURER_DISPATCH_LIVE` OFF (default) = DRY-RUN completo —
  o plano/transcript é gerado e NADA é enviado à seguradora real.
- Passo de URA desconhecido = pausa + handoff (nunca responde às cegas).
- Protocolo/senha/agendamento SÓ por âncora capturada (nunca inventados).
- O envio real (quando o gate abrir) usa o MESMO número da corretora via seam.

Núcleo PURO: quem envia/recebe é injetado (sender). Persistência do estado do
dispatch fica no caso (metadata) — este módulo não fala com banco.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.services.corridor_playbooks import (
    _norm as _norm_corredor,
    MAX_CORRECOES_POR_CAMPO,
    MAX_CORRECOES_POR_SESSAO,
    auto_subservice_menu_value,
    canonical_subservice,
    conferir_confirmacao,
    detect_finalize_anchor,
    detect_handoff_trigger,
    detect_native_flow,
    detect_referral_step,
    digest_da_conferencia,
    e_afirmativa,
    extract_capture_anchors,
    get_playbook,
    match_ura_step,
    missing_slots_for_subservice,
    montar_resposta_de_flow,
    native_flow,
    parse_address_br,
    pode_confirmar_de_novo,
    registrar_confirmacao,
    render_opening_message,
    render_reply,
    resolve_playbook_ref,
    resposta_de_correcao,
    subservice_referral,
)

logger = logging.getLogger(__name__)

DISPATCH_STATES = (
    "preparing",
    "ready_to_send",
    "ura",
    "human_phase",
    "captured",
    "monitoring",      # protocolo capturado; só repassa updates da seguradora ao cliente
    "encaminhado",     # a seguradora NÃO abre chamado aqui: entregou formulário/orientação
    "resolvido",       # o serviço foi prestado e o ciclo fechou (encerramento do follow-up)
    "test_aborted",    # modo TESTE: fluxo completo executado e CANCELADO na confirmação final
    "needs_human",
)
# `blocked_gate` foi REMOVIDO em 03/08/2026 (SPEC-063 Bloco E).
# 📊 `grep -rn "blocked_gate"` no repositório inteiro devolvia UMA ocorrência: a
# própria declaração. Nada atribuía, nada lia, nada testava.
#
# E o nome mentia sobre a máquina. O portão (`INSURER_DISPATCH_LIVE`) nunca
# BLOQUEIA uma fase: com ele fechado o acionamento roda inteiro em DRY-RUN —
# `_emit` grava o transcript, marca `dry_run: True` e avança o estado do mesmo
# jeito. Quem registra se o envio foi real é `session["live"]`, não um estado.
#
# Estado morto num enum que agora vira LINHA DE BANCO (espelho durável no Work
# Run) é pior que estado morto em memória: obriga a reconciliação a classificar
# como "em voo" ou "encerrado" algo que nenhuma transição produz. Removido.

# ---------------------------------------------------------------------------
# A máquina de estados, escrita como dado — SPEC-063 Bloco E
# ---------------------------------------------------------------------------
#
# Esta é a única máquina de estados real do produto, e até 03/08/2026 ela morava
# SÓ no Redis (`dispatch:active:{company}:{digits}`, TTL 6h — 24h em
# `monitoring`). 📊 `grep -c work_run insurer_dispatch_service.py` → 0.
#
# Um restart do Redis, ou seis horas de silêncio, perdiam um acionamento EM VOO
# e não havia reconciliação: um segurado com o guincho a caminho ficava órfão e
# ninguém ficava sabendo. Isso viola CLAUDE.md §6 (Supabase é a verdade durável,
# Redis é transitório) e a SPEC-055 (Work Run = execução universal).
#
# O que segue é PURO — o núcleo continua sem falar com banco. Quem escreve o
# espelho durável é o `dispatch_router`, usando estas funções para não inventar
# um segundo vocabulário de fases ao lado deste.

# Quantas fases já andou. Serve de `ordinal` da etapa no Work Run e de ordem de
# leitura humana na linha do tempo. NÃO é chave: a conversa oscila
# (ura → human_phase → ura) e a mesma fase se repete várias vezes por sessão.
_ORDEM_DAS_FASES: Dict[str, int] = {
    "preparing": 1,
    "ready_to_send": 2,
    "ura": 3,
    "human_phase": 4,
    "captured": 5,
    "monitoring": 6,
    "encaminhado": 7,
    "resolvido": 8,
    "needs_human": 9,
    "test_aborted": 10,
}

# EM VOO = existe trabalho acontecendo que alguém precisa terminar.
FASES_EM_VOO = ("preparing", "ready_to_send", "ura", "human_phase", "captured", "monitoring")

# ENCERRADAS = a máquina não fala mais com a seguradora por conta própria.
#
# `encaminhado` é o SEGUNDO desfecho de sucesso do produto (P-46). Ele entra
# aqui e não em FASES_EM_VOO porque o trabalho ACABOU: a seguradora disse que
# não abre chamado por este canal e entregou o caminho; o corredor entregou esse
# caminho ao segurado. Esperar um protocolo que não vem é como o caso ficava
# aberto até o watchdog.
# `resolvido` fecha o ciclo INTEIRO: o serviço foi aberto, acompanhado, e o
# follow-up confirmou o desfecho. É o desfecho que o produto existe para
# produzir — e ele foi introduzido em 03/08 SEM entrar em mapa nenhum.
#
# 📊 O preço disso, medido na auditoria do mesmo dia: `ordem_da_fase` devolvia
# 0, `status_duravel_da_fase` devolvia "running" (**o Work Run nunca fechava**),
# e o estado ficava fora de `_TERMINAL_STATES` — o Vigia perseguiria para sempre
# uma conversa encerrada com sucesso.
#
# Estado novo sem mapa é estado que só existe para quem o escreveu.
FASES_ENCERRADAS = ("needs_human", "test_aborted", "encaminhado", "resolvido")

# Fase do acionamento → status durável do Work Run (SPEC-055 §9).
#
# Não inventamos vocabulário: o enum `work_run_status` do banco já tem as
# palavras certas. `monitoring` e `needs_human` são `waiting_input` porque em
# ambas o trabalho existe, não terminou, e depende de algo de fora — a
# seguradora mandando update, ou uma pessoa assumindo.
STATUS_WORK_RUN_POR_FASE: Dict[str, str] = {
    "preparing": "queued",
    "ready_to_send": "queued",
    "ura": "running",
    "human_phase": "running",
    "captured": "running",
    "monitoring": "waiting_input",
    "needs_human": "waiting_input",
    # `encaminhado` é `completed` — e não `waiting_input` — porque nada mais é
    # esperado de ninguém: o segurado já tem o formulário/orientação na mão.
    "encaminhado": "completed",
    "resolvido": "completed",
    "test_aborted": "completed",
}

# Quanto tempo uma sessão desta fase ainda vale. Espelha o TTL do Redis: passou
# disso, restaurar não ajuda ninguém — a conversa com a seguradora já morreu.
_JANELA_DE_VIDA_SEGUNDOS: Dict[str, int] = {"monitoring": 24 * 3600}
_JANELA_PADRAO_SEGUNDOS = 6 * 3600

# Chaves que NUNCA entram no retrato durável. Nenhuma existe hoje na sessão —
# a lista está aqui para que um campo novo com nome de credencial não vire linha
# de banco por descuido (CLAUDE.md §7: nenhum segredo em log ou artifact).
_CHAVES_PROIBIDAS = ("token", "secret", "senha_acesso_portal", "api_key",
                     "password_hash", "authorization", "credential")


def ordem_da_fase(state: str) -> int:
    return _ORDEM_DAS_FASES.get(str(state or ""), 0)


def fase_em_voo(state: str) -> bool:
    return str(state or "") in FASES_EM_VOO


def status_duravel_da_fase(state: str) -> str:
    """A fase do acionamento traduzida para o vocabulário do Work Run."""
    return STATUS_WORK_RUN_POR_FASE.get(str(state or ""), "running")


def janela_de_vida_segundos(state: str) -> int:
    """Por quanto tempo uma sessão nesta fase ainda merece ser restaurada."""
    return _JANELA_DE_VIDA_SEGUNDOS.get(str(state or ""), _JANELA_PADRAO_SEGUNDOS)


def snapshot_duravel(session: Dict[str, Any], *, cauda: int = 8) -> Dict[str, Any]:
    """Retrato da sessão que basta para ela VOLTAR do banco.

    Duas escolhas deliberadas:

    1. **O transcript vai só de rabo.** Os bytes inteiros já são duráveis: o
       Espelho (SPEC-034) grava cada mensagem em `messages`, lincada ao caso.
       Repetir o transcript completo em cada checkpoint transformaria uma
       conversa de 20 mensagens em centenas de KB de jsonb duplicado. O que o
       motor precisa para continuar é a fase, os slots e as capturas; a cauda
       fica porque o guard de loop e o dossiê de handoff leem as últimas saídas.

    2. **Nada com cara de credencial atravessa.** Ver `_CHAVES_PROIBIDAS`.
    """
    retrato = {k: v for k, v in dict(session or {}).items()
               if not any(p in str(k).lower() for p in _CHAVES_PROIBIDAS)}
    transcript = list(retrato.get("transcript") or [])
    retrato["transcript"] = transcript[-max(0, int(cauda)):] if cauda else []
    retrato["transcript_total"] = len(transcript)
    return retrato


def sessao_restaurada(snapshot: Dict[str, Any], *, motivo: str) -> Dict[str, Any]:
    """A sessão que volta do banco, com o contador do Espelho recalibrado.

    Sem esta recalibragem o Espelho PARARIA DE ESPELHAR em silêncio: ele decide
    o que gravar por `transcript[mirror_idx:]`, e o retrato durável carrega só a
    cauda. Um `mirror_idx` de 20 sobre um transcript de 8 faz
    `len(transcript) <= idx` — e toda mensagem nova a partir daí some do
    dashboard até o transcript passar de 20 outra vez.
    """
    sessao = dict(snapshot or {})
    sessao.pop("transcript_total", None)
    sessao["mirror_idx"] = len(sessao.get("transcript") or [])
    sessao["restaurado_em"] = _now()
    sessao["restaurado_motivo"] = str(motivo or "")[:200]
    return sessao


# ===========================================================================
# P-90 — O INTERRUPTOR PASSA A SER UM SÓ: `agents.is_active`
# ===========================================================================
#
# Decisão do Founder, 04/08/2026, dita duas vezes e nas palavras dele:
#
#   "A questão de trava no final sempre foi por um motivo exclusivo. Eu estava
#    fazendo os testes no meu próprio celular. Se não tivesse a trava, seriam
#    feitos os acionamentos dos serviços de vidro de verdade."
#   "Quero tudo pronto e funcionando, mas o agente de atendimento tem que
#    continuar desligado. Só podem funcionar se clicar em LIGAR AGENTE."
#
# O que isso muda: as travas de ENV existiam porque não havia um interruptor
# confiável no produto. Agora há — `agents.is_active` do agente de atendimento,
# lido por `attendance_agent_active`, com fail-closed em erro de leitura. 📊 Em
# 04/08/2026 os quatro agentes `attendance` do banco estão `is_active=false`
# (`SELECT agent_role, is_active FROM agents`).
#
# Trava sobre trava não protege mais; esconde. Quem tem duas fechaduras nunca
# sabe qual está segurando — e a auditoria de 02/08 já registrou o custo disso
# ("uma trava que depende de outra trava não é trava, é sorte").
#
# O que fica: UM freio de emergência, legível, desarmado por padrão. Ele existe
# para o dia em que for preciso parar tudo sem esperar um deploy — uma linha de
# env, os dois corredores (portal de vidros E WhatsApp) param juntos.

FREIO_DE_EMERGENCIA = "ACIONAMENTO_FREIO_DE_EMERGENCIA"

# O que conta como "sim" e o que conta como "não". Escrito uma vez: um dos dois
# conjuntos escrito com uma palavra a menos vira um portão que abre por engano.
_LIGADO = ("1", "true", "yes", "on", "sim")
_DESLIGADO = ("0", "false", "no", "off", "nao", "não")


def freio_de_emergencia_armado(valor: Optional[str] = None) -> bool:
    """O freio de emergência está PUXADO? PURO quando `valor` é passado.

    Desarmado por padrão — no sentido seguro, que aqui é o sentido do Founder:
    com o freio solto, quem segura o acionamento é o agente desligado, e mais
    nada. Armar é uma linha (`ACIONAMENTO_FREIO_DE_EMERGENCIA=true`) e derruba
    os DOIS corredores de uma vez, sem deploy.

    Só um "sim" explícito arma. Um valor escrito errado (`ACIONAMENTO_FREIO=xyz`)
    NÃO arma o freio de propósito: um freio que se arma sozinho por um typo é um
    produto que para de funcionar sem ninguém entender por quê — e o efeito de
    não acionar é invisível, ao contrário do efeito de acionar.
    """
    bruto = os.getenv(FREIO_DE_EMERGENCIA, "") if valor is None else valor
    return str(bruto or "").strip().lower() in _LIGADO


def acionamento_liberado(agente_ligado: bool, freio_armado: Optional[bool] = None) -> bool:
    """PURO. A REGRA, escrita num lugar só — vale para o portal e para o WhatsApp.

    Duas condições, as duas necessárias:
      1. o agente de atendimento da corretora está LIGADO;
      2. o freio de emergência está solto.

    `agente_ligado` chega de fora porque quem sabe responder é
    `attendance_agent_active(company_id)`, que fala com o banco e é async — e a
    regra tem de poder ser provada sem banco, sem rede e sem LLM. Guarda que só
    existe dentro de um `await` é guarda que ninguém consegue testar.
    """
    if not bool(agente_ligado):
        return False
    return not (freio_de_emergencia_armado() if freio_armado is None else bool(freio_armado))


def dispatch_live_enabled() -> bool:
    """O envio REAL à seguradora está liberado pelo AMBIENTE?

    Mudou em 04/08/2026 (P-90) e o que mudou foi o PADRÃO, não a mecânica.

    Antes: `INSURER_DISPATCH_LIVE` ausente = FECHADO. O gate S17-6 nasceu quando
    o Founder testava no próprio celular e um acionamento de verdade mandaria um
    prestador à casa dele. Esse motivo acabou: hoje quem segura é o agente
    desligado, e `InsurerDispatchTool` só existe para um agente `attendance`
    ATIVO (graph.py só a anexa para esse papel; `_get_raw_agent` filtra
    `is_active=True`; e o webhook já parou antes, em `attendance_agent_active`).

    Agora: ausente = ABERTO. Duas coisas ainda fecham, e as duas são explícitas:
      · o freio de emergência (`ACIONAMENTO_FREIO_DE_EMERGENCIA`);
      · um `INSURER_DISPATCH_LIVE=false` escrito por alguém.

    O "não" explícito continua valendo de propósito. Ignorar uma variável que um
    operador escreveu com a própria mão é como discordar dele em silêncio — e o
    silêncio só é descoberto quando já não dá para desfazer.

    ⚠️ Consequência operacional, e ela é real: se o ambiente de produção herdou
    `INSURER_DISPATCH_LIVE=false` do `.env.example` antigo, ligar o agente NÃO
    basta — é preciso apagar aquela linha. Está registrado em PENDENCIAS.

    🔴 14/08/2026 — O PADRÃO VOLTA A SER FECHADO, E NÃO É UMA REVERSÃO.

    A decisão de 04/08 (P-90) abriu o padrão com um motivo escrito logo acima:
    *"hoje quem segura é o agente desligado"*. **É exatamente essa premissa que
    a SPEC-071 vai derrubar** — a semana de 18/08 é a semana de LIGAR o agente,
    com Regina e Saionara monitorando. No instante em que o agente acende, o
    único freio que restava some, e some em silêncio.

    Regra R1 do Founder, 14/08, literal: *"não pode ser enviado nada até eu
    liberar"*. Aqui ela vira código, e não lembrança: um interruptor que
    depende de alguém escrever uma linha no painel é um interruptor que um dia
    ninguém escreve. Fechado por construção, aberto por decisão.

    Ligar é `INSURER_DISPATCH_LIVE=true`, sem deploy — e é o Founder quem liga,
    depois do teste de peças.

    ⚠️ Este é o portão EXTERNO: "podemos falar com a seguradora?". O interno —
    "podemos CONCLUIR o pedido?" — é `finalize_live_for` logo abaixo,
    controlado por `DISPATCH_FINALIZE_MODE`. São dois freios em série, e os
    dois precisam estar abertos para um guincho sair de verdade.
    """
    if freio_de_emergencia_armado():
        return False
    bruto = str(os.getenv("INSURER_DISPATCH_LIVE", "")).strip().lower()
    return bruto in ("1", "true", "yes", "on", "sim")


def finalize_live_for(playbook_ref: str) -> bool:
    """O corredor pode CONCLUIR o pedido na seguradora, ou cancela no final?

    Decisão do founder (2026-07-11): o freio de finalização existe SÓ para os
    TESTES — a IA executa o fluxo inteiro e CANCELA antes de abrir o serviço.

    04/08/2026 (P-90): o padrão passou de `test` para `live`, pelo mesmo motivo
    do gate acima e por um a mais, que é o pior dos dois.

    Meio aberto é pior que fechado. Com o envio liberado e a finalização em
    `test`, mensagens REAIS chegam à URA da seguradora, o fluxo anda até o fim
    e é CANCELADO — o segurado ouviu "estou acionando", ninguém vem, e a
    seguradora registrou uma conversa que não virou serviço. Ou o corredor
    trabalha, ou ele não fala; não existe um meio termo honesto.

    Continua sendo possível voltar ao ensaio, e sem deploy:
      · DISPATCH_FINALIZE_MODE=test volta a cancelar na confirmação final;
      · DISPATCH_FINALIZE_LIVE_PLAYBOOKS=ref1,ref2 gradua corredor a corredor
        (só faz sentido junto com `test`);
      · o freio de emergência fecha tudo, aqui também.
    """
    if freio_de_emergencia_armado():
        return False
    mode = str(os.getenv("DISPATCH_FINALIZE_MODE", "live")).strip().lower()
    if mode == "live":
        return True
    live_refs = [x.strip() for x in str(os.getenv("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", "")).split(",") if x.strip()]
    return str(playbook_ref or "") in live_refs


def _finalize_allowed(session: Dict[str, Any]) -> bool:
    return bool(session.get("finalize_approved")) or finalize_live_for(str(session.get("playbook_ref") or ""))


# Mensagens de pós-atendimento da seguradora (pesquisa/avaliação): nunca responder.
_SURVEY_NOOP_RE = (
    r"pesquisa de (?:satisfa[çc][ãa]o|qualidade)|avalie (?:sua|a sua|nosso)|sua opini[ãa]o [ée] muito importante|"
    r"o quanto voc[êe] recomendaria|grau de satisfa[çc][ãa]o|responda nossa pesquisa"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derivar_teclas_do_caso(slots: dict) -> None:
    """Traduz o que o segurado disse para as teclas que a URA espera.

    Muda `slots` no lugar, e só preenche o que ainda está vazio — quem já
    tem valor (do subserviço ou da atendente) manda.

    🔴 Cada derivação tem um DEFAULT, e isso é deliberado. A alternativa é o
    silêncio, e 📊 o silêncio custou 2 minutos e 22 segundos e um clique
    manual no teste de 18/08. Menu de seguradora com a tecla mais provável é
    corrigível; menu sem resposta nenhuma trava o acionamento inteiro.
    """
    from app.services.corridor_playbooks import _norm

    texto = _norm(" ".join(str(slots.get(c) or "") for c in
                               ("problema_descricao", "problema_relato",
                                "descricao", "servico_texto")))

    # ---- "O que aconteceu?" (eletricista) ----------------------------
    # 📊 A tela real: "1 - Casa inteira ou parcial sem energia
    #                  2 - Curto circuito ou mau funcionamento das tomadas,
    #                      interruptores, disjuntores"
    if not str(slots.get("problema_eletrico_opcao") or "").strip():
        curto = any(p in texto for p in (
            "curto", "curto circuito", "tomada", "interruptor", "disjuntor",
            "chuveiro", "mau funcionamento", "nao funciona", "queimou a tomada",
            "faisca na tomada", "esquentando"))
        # `1` é o default: 📊 "sem energia" é o motivo dominante de chamado
        # de eletricista residencial, e foi o caso do teste ("Parte da casa
        # sem luz").
        slots["problema_eletrico_opcao"] = "2" if curto else "1"

    # ---- QUAL ANIMAL DOMESTICO (consulta veterinaria) ----------------
    # 📊 "Atendimento para qual animal domestico? *1 -* Cachorro
    #    *2 -* Gato *3 -* Outros" -- 1 sessao (c58a171a), que chega ao protocolo.
    #
    # ⚠️ Esta e das poucas em que o relato SEMPRE diz: ninguem pede consulta
    #    veterinaria sem dizer de que bicho se trata. O default e "3 - Outros",
    #    que e opcao da propria URA -- nunca "Cachorro", que inventaria a especie.
    if not str(slots.get("pet_especie_opcao") or "").strip():
        if any(p in texto for p in ("cachorro", "cao", "cadela", "dog", "filhote de "
                                    "cachorro", "pitbull", "poodle", "vira-lata",
                                    "vira lata")):
            slots["pet_especie_opcao"] = "1"
        elif any(p in texto for p in ("gato", "gata", "felino")):
            slots["pet_especie_opcao"] = "2"
        else:
            slots["pet_especie_opcao"] = "3"

    # ---- O VAZAMENTO ESTA APARENTE? ----------------------------------
    # 📊 "O vazamento esta aparente, sabe informar o local exato e o tipo de
    #    tubulacao? *1 -* Sim *2 -* Nao" -- 3 sessoes.
    #
    # 🔴 E PERGUNTA DE COBERTURA disfarcada: vazamento NAO aparente e
    #    CACA-VAZAMENTO, e o texto da propria allianz diz que caca-vazamento e
    #    vazamento interno (paredes, teto, pisos) NAO sao cobertos.
    #    Responder "1" no escuro abre um chamado que o prestador nega no local.
    #
    # A traducao le o que o segurado ja descreveu: cano na parede, piso, teto ou
    # "nao sei de onde vem" e NAO aparente.
    if not str(slots.get("vazamento_aparente_opcao") or "").strip():
        escondido = any(p in texto for p in (
            "parede", "piso", "teto", "embutid", "enterrad", "nao sei de onde",
            "nao sei onde", "infiltra", "mancha", "subsolo", "laje"))
        slots["vazamento_aparente_opcao"] = "2" if escondido else "1"

    # ---- QUANTOS PNEUS -----------------------------------------------
    # 📊 Duas telas, duas seguradoras, a mesma pergunta:
    #     yelum/hdi "Quantos pneus foram furados/danificados?
    #                1-Apenas um pneu  2-Mais de um pneu"
    #     alfa      "Quantos pneus furaram? 1-Apenas um  2-Dois ou mais"
    #
    # 🔴 "Mais de um pneu" MUDA O SERVICO para GUINCHO: um borracheiro leva um
    #    estepe, nao dois. Constante aqui manda borracheiro para carro que
    #    precisa de reboque -- e o prestador chega, olha, e vai embora.
    if not str(slots.get("pneus_quantidade_opcao") or "").strip():
        varios = any(p in texto for p in (
            "dois pneus", "2 pneus", "tres pneus", "3 pneus", "quatro pneus",
            "4 pneus", "mais de um pneu", "varios pneus", "dois furos",
            "os dois", "ambos os pneus"))
        slots["pneus_quantidade_opcao"] = "2" if varios else "1"
    # a alfa usa outro nome para a MESMA pergunta
    if not str(slots.get("pneus_furados_opcao") or "").strip():
        slots["pneus_furados_opcao"] = slots["pneus_quantidade_opcao"]

    # ---- O QUE ACONTECEU COM A CHAVE (auto) --------------------------
    # 📊 yelum/hdi: "O que aconteceu com a chave? Dentro do veiculo (chave
    #    trancada dentro) / Perda / Quebrou / Outros"
    # 🔴 Sao ROTULOS, nao numeros -- e "Dentro do veiculo" e o caso mais comum
    #    de chaveiro de auto: a chave ficou trancada. Mas so o relato diz.
    if not str(slots.get("chave_problema") or "").strip():
        if any(p in texto for p in ("trancad", "dentro do carro", "dentro do veiculo",
                                    "fechou com a chave dentro", "chave dentro")):
            slots["chave_problema"] = "Dentro do veiculo"
        elif any(p in texto for p in ("quebrou", "quebrad", "partiu", "torceu")):
            slots["chave_problema"] = "Quebrou"
        elif any(p in texto for p in ("perdi", "perdeu", "perda", "sumiu", "extraviad")):
            slots["chave_problema"] = "Perda"
        else:
            slots["chave_problema"] = "Outros"

    # ---- JA SABE O DESTINO? (guincho) --------------------------------
    # 🔴 Esta NAO sai do relato: sai do PROPRIO CASO. Se a corretora informou
    #    `local_destino`, o destino e conhecido; se nao informou, nao e. Deduzir
    #    isso de palavras seria adivinhar o que o formulario ja responde.
    if not str(slots.get("tem_destino") or "").strip():
        slots["tem_destino"] = "Sim" if str(slots.get("local_destino") or "").strip() else "Nao"

    # ---- "Conserto do ar condicionado" x "Limpeza do ar condicionado" -
    # 📊 A tela, literal (allianz residencial):
    #   "O servico e destinado ao conserto de aparelhos/equipamentos de uso
    #    domestico que estejam fora da garantia do fabricante e que pertencam a
    #    residencia segurada. Voce precisa de:
    #    *1 -* Conserto do ar condicionado
    #    *2 -* Limpeza do ar condicionado"
    #
    # 🔴 SAO TRABALHOS DIFERENTES, e a diferenca chega na conta do segurado:
    #    conserto e defeito (coberto); limpeza e manutencao preventiva, que
    #    costuma NAO ser coberta pela apolice. Ate 22/08/2026 o corredor
    #    respondia "1" fixo nesta tela -- inclusive para casos de MAQUINA DE
    #    LAVAR, que nao tem o que fazer aqui.
    if not str(slots.get("ar_condicionado_servico_opcao") or "").strip():
        limpeza = any(p in texto for p in (
            "limpeza", "limpar", "higieniz", "sujo", "mau cheiro", "cheiro ruim",
            "manutencao preventiva", "filtro sujo"))
        slots["ar_condicionado_servico_opcao"] = "2" if limpeza else "1"

    # ---- "Identifiquei que temos uma solicitação de serviço feita" ------
    # 📊 A tela, literal (allianz auto E residencial, 3 + 10 sessões):
    #   "O que deseja? *1 -* Ver detalhes *2 -* Abrir novo atendimento"
    #
    # 🔴 A resposta é "2", e a razão não é preferencia -- é o que o corredor
    #    ESTÁ FAZENDO ALI. Ele só roda quando a corretora pediu um acionamento
    #    NOVO; "Ver detalhes" abriria o chamado antigo e o trabalho pedido nunca
    #    aconteceria. Quem quer acompanhar um chamado existente não passa por
    #    este corredor.
    #
    # ⚠️ E fica derivável, não constante, porque o dia em que existir uma rota
    #    de ACOMPANHAMENTO ela precisa poder dizer "1" -- e aí basta preencher
    #    o slot, sem tocar no passo.
    if not str(slots.get("solicitacao_existente_opcao") or "").strip():
        acompanhar = any(p in texto for p in (
            "acompanhar", "ver detalhes", "status do chamado", "como esta o chamado",
            "andamento do servico", "ja abri"))
        slots["solicitacao_existente_opcao"] = "1" if acompanhar else "2"

    # ---- "Qual desses serviços, você precisa?" (allianz residencial) ------
    # 📊 A tela, literal, 2 telas / 21 sessões:
    #   "*1 -* Dedetização  *2 -* Limpeza do Imóvel  *3 -* Limpeza de Caixa
    #    d'Água  *4 -* Substituição de Telhas  *5 -* Cobertura Provisória de
    #    Telhado  *6 -* Consulta Veterinária  *7 -* Outros  *8 -* Voltar"
    #
    # 🔴 SEIS trabalhos que o produto não declara como subserviço. Enquanto
    #    não declarar, a tradução lê o que o segurado pediu e escolhe a tecla;
    #    não havendo palavra reconhecível, a resposta honesta é **"7 - Outros"**,
    #    que é opção da própria URA -- nunca "1", que abriria uma dedetização.
    if not str(slots.get("outro_servico_opcao") or "").strip():
        if any(p in texto for p in ("dedetiz", "barata", "formiga", "cupim", "rato",
                                    "escorpi", "praga", "inseto")):
            slots["outro_servico_opcao"] = "1"
        elif any(p in texto for p in ("limpeza do imovel", "faxina", "limpeza pos",
                                      "limpar a casa")):
            slots["outro_servico_opcao"] = "2"
        elif any(p in texto for p in ("caixa d agua", "caixa dagua", "caixa de agua",
                                      "reservatorio")):
            slots["outro_servico_opcao"] = "3"
        # 🔴 A ORDEM DE NOVO, e a mesma armadilha do cambio x embreagem:
        #    **"telhado" CONTÉM "telha"**. Se a substituição de telha viesse antes,
        #    "o vento destelhou parte do telhado" abriria uma troca de telhas em
        #    vez da cobertura provisória de emergência -- e a cobertura provisória
        #    é a que impede a casa de encher de água na mesma noite.
        elif any(p in texto for p in ("cobertura provisoria", "lona", "destelh",
                                      "telhado voou", "sem telhado", "telhado arranc")):
            slots["outro_servico_opcao"] = "5"
        elif "telha" in texto:
            slots["outro_servico_opcao"] = "4"
        elif any(p in texto for p in ("veterinar", "pet", "cachorro", "gato", "animal")):
            slots["outro_servico_opcao"] = "6"
        else:
            # 🔴 "Outros" e opcao da URA, e e a resposta honesta de quem nao
            #    reconheceu o pedido. "1" abriria uma dedetizacao que ninguem pediu.
            slots["outro_servico_opcao"] = "7"

    # ---- "Selecione a opção que condiz com a pane" (yelum/hdi) -------
    # 📊 O menu real, NOVE opções:
    #   1-Problemas elétricos 2-Luzes do painel 3-Vazamento
    #   4-Superaquecimento 5-Problemas no motor 6-Embreagem 7-Câmbio
    #   8-Não sei 9-Mais opções
    #
    # 🔴 Até 22/08/2026 o passo respondia "Problemas no motor", CONSTANTE, nas
    #    nove. E é esta tecla que a URA usa para separar REBOQUE de MECÂNICO NO
    #    LOCAL: 📊 a sessão real de socorro mecânico da HDI (71caf82f,
    #    01/06/2026, protocolo 9662631) apertou "Problemas elétricos".
    #
    # ⚠️ "Não sei" (8) é uma opção HONESTA da própria URA, e é o default quando
    #    o relato não diz nada — melhor que afirmar um defeito que ninguém viu.
    if not str(slots.get("pane_detalhe_opcao") or "").strip():
        if any(p in texto for p in ("eletric", "eletrico", "bateria", "alternador",
                                    "nao liga", "nao pega", "nao da partida",
                                    "descarregad", "injec", "ignic")):
            slots["pane_detalhe_opcao"] = "1"
        elif any(p in texto for p in ("luz do painel", "luzes do painel", "painel aceso",
                                      "luz acesa", "lampada do painel")):
            slots["pane_detalhe_opcao"] = "2"
        elif any(p in texto for p in ("vazando", "vazamento", "oleo no chao",
                                      "perdendo oleo", "perdendo agua")):
            slots["pane_detalhe_opcao"] = "3"
        elif any(p in texto for p in ("superaquec", "esquentando", "fervendo",
                                      "temperatura alta", "radiador")):
            slots["pane_detalhe_opcao"] = "4"
        elif any(p in texto for p in ("motor", "fundiu", "batendo pino", "morreu andando")):
            slots["pane_detalhe_opcao"] = "5"
        # 🔴 A ORDEM AQUI É REGRA, E ELA CUSTOU UM CONTROLE VERMELHO.
        #    A primeira versão testava embreagem antes e punha "nao entra marcha"
        #    na lista dela. 📊 O relato "Não entra marcha, problema no câmbio"
        #    dava **6 (embreagem)** -- o segurado nomeou a peça e o corredor
        #    escolheu outra.
        #    A peça NOMEADA vence o sintoma. "nao entra marcha" sozinho é
        #    vocabulário de câmbio, e por isso desceu para o ramo 7.
        elif any(p in texto for p in ("embreagem", "pedal da embreagem", "patinando")):
            slots["pane_detalhe_opcao"] = "6"
        elif any(p in texto for p in ("cambio", "transmiss", "marcha", "engatar")):
            slots["pane_detalhe_opcao"] = "7"
        else:
            # 🔴 "Não sei" é opção da URA, e é a resposta honesta de quem não sabe.
            slots["pane_detalhe_opcao"] = "8"

    # ---- "O que aconteceu?" (ENCANADOR) ------------------------------
    # 📊 A tela real, allianz-residencial, 4 sessões:
    #   "1 - Vazamento em dispositivo como sifões, rabichos, torneiras e válvulas
    #    2 - Vazamento em tubulação de água ou esgoto"
    #
    # 🔴 A pergunta é a MESMA do eletricista ("O que aconteceu?") e as opções são
    #    outras. Até 22/08/2026 a âncora era seca e o passo do eletricista
    #    respondia a tecla do problema ELÉTRICO nesta tela. Agora cada ofício tem
    #    o seu — e cada um precisa da sua tradução.
    #
    # A resposta muda a árvore inteira que vem depois, então ela vem do RELATO,
    # nunca de constante. `1` é o default porque 📊 o vazamento em dispositivo
    # (torneira, sifão, descarga) é o motivo dominante de chamado de encanador
    # residencial; tubulação exige a palavra do segurado.
    if not str(slots.get("problema_vazamento_opcao") or "").strip():
        tubulacao = any(p in texto for p in (
            "tubulacao", "tubulaç", "cano", "encanamento", "esgoto", "coluna",
            "parede", "piso", "enterrad", "embutid", "ramal", "prumada"))
        slots["problema_vazamento_opcao"] = "2" if tubulacao else "1"

    # ---- "O que aconteceu?" (CHAVEIRO) -------------------------------
    # 📊 A tela real, allianz-residencial, 2 sessões:
    #   "1 - Perda ou quebra das chaves
    #    2 - Roubo ou furto das chaves
    #    3 - Arrombamento, roubo ou furto da residência"
    #
    # ⚠️ Uma das duas sessões MORREU aqui: `aa2e0a68`, 03/07/2026 —
    #    "Opção inválida" → "Vamos tentar novamente" → transferência ao
    #    especialista, sem protocolo. Era a tela sem passo.
    #
    # 🔴 A ORDEM DOS TESTES IMPORTA: "arrombaram e levaram as chaves" é
    #    arrombamento (3), não roubo (2). O caso mais grave é testado primeiro.
    if not str(slots.get("problema_chave_opcao") or "").strip():
        if any(p in texto for p in ("arromb", "invadir", "invadiram", "invasao",
                                    "forcaram a porta", "arrombar")):
            slots["problema_chave_opcao"] = "3"
        elif any(p in texto for p in ("roub", "furt", "assalt", "levaram")):
            slots["problema_chave_opcao"] = "2"
        else:
            # perdi / quebrou / trancou dentro — o caso comum
            slots["problema_chave_opcao"] = "1"

    # ---- A DATA do agendamento (eletrodoméstico) ---------------------
    # 📊 "Os agendamentos estão disponíveis de segunda a sexta, para os
    #     próximos 7 dias. Escolha qual data: 1- ... 7- ..."
    #
    # As datas são DINÂMICAS — mudam a cada dia. Por isso a resposta é a
    # POSIÇÃO, e `1` é sempre a mais próxima. Quem tem a máquina de lavar
    # parada quer o técnico o quanto antes; adiar é a decisão que o segurado
    # tomaria explicitamente, nunca a que o sistema toma por ele.
    if not str(slots.get("data_agendamento_opcao") or "").strip():
        slots["data_agendamento_opcao"] = "1"

    # ---- O PERÍODO do agendamento -------------------------------------
    # 📊 "manhã das 09h às 13h e tarde, das 13h às 18h" — 1 e 2.
    #
    # ⚠️ A própria URA declara: agendamento para o DIA SEGUINTE é
    # obrigatoriamente à TARDE, e feito no fim de semana vai para o próximo
    # dia útil à tarde. Por isso `tarde` é o default: é a opção que a URA
    # aceita em mais situações, e escolher `manhã` num dia em que ela não é
    # permitida devolveria "Opção inválida".
    if not str(slots.get("periodo_agendamento_opcao") or "").strip():
        pref = _norm(str(slots.get("periodo_preferido") or ""))
        slots["periodo_agendamento_opcao"] = "1" if "manha" in pref else "2"


def new_dispatch_session(
    *,
    case_id: str,
    company_id: str,
    playbook_ref: str,
    subservice: str,
    slots: Dict[str, Any],
) -> Dict[str, Any]:
    """Cria a sessão de dispatch. Slots incompletos → preparing com blockers."""
    playbook = get_playbook(playbook_ref)
    if not playbook:
        return {"state": "needs_human", "reason": "playbook_not_found", "playbook_ref": playbook_ref}

    # `canonical_subservice`, e não `.lower()` cru.
    #
    # 📊 O apelido existe justamente para isto: a Porto chama "elétrica" e
    # "hidráulica" o que nós chamamos de eletricista e encanador. Três outros
    # pontos do produto já canonicalizavam — `missing_slots_for_subservice`,
    # `auto_subservice_menu_value` e `match_ura_step`. Este, que é o PRIMEIRO da
    # cadeia, não.
    #
    # O efeito era pior do que uma falha: `sub` vinha vazio, então
    # `tipo_servico_opcao` ficava None e a sessão nascia `ready_to_send` — a
    # peça mais adiante é que travava, no meio da conversa com a URA rodando.
    # A sessão dizia que estava pronta, e não estava.
    sub = (playbook.get("subservices") or {}).get(canonical_subservice(subservice), {})
    merged_slots = dict(slots or {})
    # TODA opção de menu declarada no subserviço vira slot — pelo SUFIXO, não
    # pelo nome. Era `tipo_servico_opcao` escrito à mão, um campo só.
    #
    # 📊 04/08/2026: a URA residencial da Allianz tem DOIS menus em sequência —
    # "Informe o tipo de serviço" (a família) e "De qual profissional?" (o
    # ofício, 13 ocorrências). Com a injeção nominal, declarar a segunda tecla no
    # playbook não bastava: ela nunca chegava aos slots, `render_reply` devolvia
    # `missing` e o acionamento parava no menu que o corredor sabia responder.
    #
    # O sufixo `_opcao` já é a regra em `missing_slots_for_subservice` ("o que o
    # MOTOR preenche não se cobra do cliente") e em `_slots_com_padrao_do_motor`.
    # Ler a mesma regra aqui é o que faz a tecla nova nascer ligada.
    for chave, valor in (sub or {}).items():
        if chave.endswith("_opcao") and valor and not merged_slots.get(chave):
            merged_slots[chave] = valor
    # Default seguro: sem telefone extra => usa o registrado (opção 2).
    if not str(merged_slots.get("telefone_adicionar_opcao") or "").strip():
        merged_slots["telefone_adicionar_opcao"] = "1" if merged_slots.get("telefone_contato") else "2"

    # 🔴 AS TECLAS QUE SAEM DO QUE O SEGURADO JÁ DISSE — SPEC-082, 18/08/2026.
    #
    # 📊 O DEFEITO QUE ISTO CONSERTA, medido no teste real do Founder:
    #
    #     12:23:43  a URA manda "O que aconteceu? 1-Casa sem energia 2-Curto"
    #               ⟵ 2 minutos e 22 segundos de SILÊNCIO ⟶
    #     12:26:05  o Founder clicou "1" do próprio celular
    #
    # O passo `o_que_aconteceu` exigia o slot `problema_eletrico_opcao`, e
    # NADA no produto preenchia esse slot. Um passo que exige um slot que
    # ninguém preenche não responde e não avisa: fica calado.
    #
    # A saída errada seria uma constante — a tela escolhe o TIPO DE DEFEITO,
    # e tecla errada abre chamado errado. A saída certa é TRADUZIR o que o
    # segurado já contou: ele descreve com as palavras dele, e o corredor
    # converte para a tecla da seguradora. É o trabalho do corredor.
    _derivar_teclas_do_caso(merged_slots)

    # Os campos que o MOTOR preencheu, e que o cliente nunca confirmou.
    # Ver o comentário logo abaixo, no bloco AUTO.
    _slots_padrao: set = set()
    # AUTO (SPEC-031): injeta a opção/rótulo do menu de serviço da seguradora
    # (guincho => "3" na Allianz, "Guincho" na Porto) nos slots que os passos usam.
    if str(playbook.get("line_kind") or "") == "auto":
        menu_value = auto_subservice_menu_value(playbook, subservice)
        if menu_value:
            merged_slots.setdefault("servico_opcao", menu_value)
            merged_slots.setdefault("servico_texto", menu_value)
        # O QUE O MOTOR PREENCHE NÃO É O QUE O CLIENTE DISSE.
        #
        # 📊 Achado em 05/08/2026. Estes `setdefault` existem para a URA não
        # travar pedindo um campo opcional — e isso está certo. O defeito é o
        # que vinha depois: o prompt listava TUDO junto, sem distinção, sob o
        # título "Dados do caso (únicos números permitidos)".
        #
        # Consequência: se o segurado está na BR-101 e o parser não pegou, o
        # modelo afirma a uma PESSOA de verdade que ele **não** está em
        # rodovia. E rodovia troca o caminhão que vem. O prompt estava
        # mandando o agente inventar, com todas as letras.
        #
        # A lista abaixo é gravada na sessão para que o prompt possa marcar
        # cada linha com "(padrão — não confirmado com o cliente)". Marcar é o
        # conserto certo; remover o padrão faria a URA travar.
        for _campo, _valor in (("roda_travada", "não"), ("quando", "agora"),
                               ("veiculo_cor", "não sei"), ("rodovia", "Não")):
            if _campo not in merged_slots or merged_slots.get(_campo) in (None, ""):
                merged_slots[_campo] = _valor
                _slots_padrao.add(_campo)
    # Referência do local é opcional em TODAS as linhas ('não tem' é o padrão real).
    if "ponto_referencia" not in merged_slots or merged_slots.get("ponto_referencia") in (None, ""):
        merged_slots["ponto_referencia"] = "não tem"
        _slots_padrao.add("ponto_referencia")
    # Endereços decompostos (rua/nº/bairro/cidade/UF) p/ URAs que pedem separado.
    from app.services.corridor_playbooks import inject_address_slots

    inject_address_slots(merged_slots)

    missing = missing_slots_for_subservice(playbook, subservice, merged_slots)
    session = {
        "case_id": case_id,
        "company_id": company_id,
        "playbook_ref": playbook_ref,
        "subservice": str(subservice or "").lower(),
        "slots": merged_slots,
        # Quais desses slots o MOTOR preencheu sem o cliente confirmar. O
        # prompt marca cada um, para o agente nunca afirmar a uma pessoa de
        # verdade um dado que ninguém disse.
        "slots_padrao": sorted(_slots_padrao),
        "state": "preparing" if missing else "ready_to_send",
        "missing_slots": missing,
        "transcript": [],  # [{direction, text, at, dry_run}]
        "captured": {},
        "live": dispatch_live_enabled(),
        "created_at": _now(),
    }
    return session


def build_dry_run_plan(playbook_ref: str, subservice: str, slots: Dict[str, Any]) -> Dict[str, Any]:
    """P5: plano completo do acionamento SEM enviar nada — o que SERIA respondido
    em cada passo da URA com os dados do caso. Usado pela tool do atendente e
    pela revisão humana antes do gate abrir."""
    playbook = get_playbook(playbook_ref)
    if not playbook:
        return {"ok": False, "error": "playbook_not_found", "steps": [], "missing_slots": []}
    session = new_dispatch_session(
        case_id="dry-run", company_id="dry-run", playbook_ref=playbook_ref, subservice=subservice, slots=slots
    )
    if session.get("state") == "needs_human":
        return {"ok": False, "error": session.get("reason"), "steps": [], "missing_slots": []}
    if session.get("missing_slots"):
        return {"ok": False, "error": "missing_slots", "steps": [], "missing_slots": session["missing_slots"]}
    # Abertura CURTA ("Olá") — é assim que a operadora real inicia; a URA não lê
    # texto longo. O resumo estruturado vai ao ANALISTA humano (fase humana).
    steps: List[Dict[str, str]] = [{"step": "abertura", "reply": "Olá"}]
    # 🔴 SÓ OS PASSOS DESTA ROTA — 19/08/2026.
    #
    # O laço percorria `ura_steps` inteiro. 📊 Depois que o corredor
    # residencial da Allianz ganhou os nove passos de eletrodoméstico, o plano
    # de um chamado de ELETRICISTA passou a listar `aparelho_marca` e
    # `aparelho_modelo` como `[PENDENTE: ...]` — dados que um eletricista
    # nunca vai ter.
    #
    # E o plano não é enfeite: é o que o atendente lê antes de acionar e o
    # que a revisão humana aprova. Um passo `[PENDENTE:]` ali é a promessa de
    # uma resposta em branco na URA da seguradora.
    #
    # `only_subservices` já é o filtro que `missing_slots_for_subservice` usa
    # para a mesma pergunta. Usar o mesmo aqui é o que impede as duas
    # respostas de divergirem — foi a divergência entre elas que produziu o
    # defeito.
    rota = canonical_subservice(session.get("subservice") or subservice)
    for step in playbook.get("ura_steps") or []:
        only = step.get("only_subservices")
        if only and str(rota or "").lower() not in [str(x).lower() for x in only]:
            continue
        rendered = render_reply(step, session["slots"])
        steps.append({
            "step": str(step.get("step")),
            "reply": rendered["reply"] if rendered["ok"] else f"[PENDENTE: {','.join(rendered['missing'])}]",
        })
    return {
        "ok": True,
        "playbook_ref": playbook_ref,
        "subservice": session["subservice"],
        "missing_slots": [],
        "steps": steps,
        "live": dispatch_live_enabled(),
        "note": (
            "Acionamento REAL liberado pelo ambiente." if dispatch_live_enabled()
            else ("MODO SIMULAÇÃO: nada será enviado à seguradora — o ambiente está fechado "
                  "(freio de emergência armado ou INSURER_DISPATCH_LIVE=false).")
        ),
    }


def start_dispatch(
    session: Dict[str, Any],
    *,
    sender: Optional[Callable[[str], Any]] = None,
    opening_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Inicia o acionamento (mensagem de abertura). Respeita o GATE."""
    if session.get("state") not in ("ready_to_send",):
        return session
    return _emit(session, opening_message or "Olá", sender=sender, next_state="ura")


# ===========================================================================
# BANCO DE RESPOSTAS DETERMINÍSTICO — a camada ANTES do Cérebro
# ===========================================================================
#
# O DEFEITO DE ARQUITETURA QUE ISTO DESFAZ
# -----------------------------------------
# Até aqui, uma tela da URA sem passo mapeado tinha UM caminho: a sessão
# pausava, o Vigia percebia na varredura (a cada 20s), acionava o Sentinela, que
# chamava o Cérebro (LLM forte, rede, latência de modelo). **São minutos.**
#
# E a URA da HDI encerra a conversa sozinha — está escrito na tela de
# boas-vindas dela. Gastar minutos para responder *"qual o CEP?"*, com o CEP na
# ficha desde a primeira mensagem do segurado, não é lento: é perder o
# acionamento por causa de um dado que já estava na mão.
#
# A DIVISÃO, E POR QUE ELA É ASSIMÉTRICA
# ---------------------------------------
#   pergunta de DADO      responde NA HORA, da ficha. Sem LLM, sem espera.
#   pergunta de DECISÃO   só passo mapeado do corredor, ou uma pessoa.
#
# Errar numa pergunta de DADO custa um dado errado, que a URA rejeita ou o
# analista corrige. Errar numa de DECISÃO **abre um serviço no nome do
# segurado** — despacha guincho, agenda visita, cria protocolo. Por isso a
# lista de DECISÃO é uma NEGATIVA EXPLÍCITA: qualquer tela que cheire a
# confirmação, agendamento ou escolha de serviço nunca é respondida daqui,
# mesmo que também pareça uma pergunta de dado.
#
# ISTO NÃO SUBSTITUI O CÉREBRO. Fica na frente dele. Pergunta que este banco
# não reconhece, ou cujo dado não está na ficha, segue exatamente o caminho de
# antes — pausa, Vigia, Sentinela, Cérebro. Nada foi removido.

# O reconhecedor é REGEX sobre a tela, nunca um modelo. Um classificador
# probabilístico aqui traria de volta a latência que estamos matando, e traria
# junto a chance de classificar "podemos confirmar?" como pergunta de dado.
_MARCA_DE_PERGUNTA = (
    r"\?|\b(?:informe|informa|digite|digita|qual|quais|envie|envia|preciso d|"
    r"poderia (?:me )?(?:informar|dizer|passar)|me (?:informe|diga|passe)|nos informe)\b"
)

# A NEGATIVA EXPLÍCITA. Casar com QUALQUER uma destas encerra o assunto: o
# banco não responde, e a tela segue para o caminho antigo (passo mapeado, ou
# gente). Escrita larga de propósito — um falso positivo aqui custa uma pausa;
# um falso negativo custa um prestador despachado.
_PERGUNTAS_DE_DECISAO = (
    r"\bconfirm(?:a|ar|e|ei|amos|ado|ada|acao)\b",
    r"(?:podemos|posso|deseja|gostaria de|quer) (?:confirmar|continuar|prosseguir|seguir|abrir|agendar|cancelar)",
    r"\bagendar\b|\bagendamento\b|\breagendar\b|\bagendad",
    # 📊 O ponto de não-retorno da família HDI/Yelum, nas três redações reais.
    # O prompt desta tarefa listava "agora ou agendar" como pergunta de DADO.
    # Ela NÃO é: responder 'Agora' ABRE o serviço na hora, e o corredor já a
    # trata como `finalize_anchor` (freio) E como passo mapeado `quando_agora`.
    # Respondê-la daqui seria abrir uma segunda porta em volta do freio —
    # exatamente o que o aviso de segurança desta tarefa proíbe. Fica em
    # DECISÃO, e quem responde continua sendo o passo mapeado, atrás do freio.
    r"atendimento (?:para )?agora ou prefere",
    r"est[ao]{1,2}o? corret[oa]s?\b|\bconfere\b|\bresumo (?:do|da|de|abaixo)\b",
    r"abrir (?:o |a |um |uma )?(?:chamado|servi[cç]o|solicita[cç][ao]{1,2}o|assist[eê]ncia|atendimento)",
    r"(?:qual|escolha|selecione|informe)[^\n]{0,30}\b(?:servi[cç]o|op[cç][ao]{1,2}o|alternativa|tipo de atendimento)\b",
    r"\bcancelar\b|\bencerrar\b|\bdesistir\b",
)

# A tabela de perguntas de DADO: (campo, o que a tela pergunta, onde o dado mora).
#
# O que NÃO está aqui, e por quê: rua, número, bairro, cidade e estado. Eles são
# passos mapeados com `reply_repeat` — na família HDI a MESMA pergunta ("qual é
# o número?") significa a origem na primeira vez e o DESTINO na segunda. Um
# banco sem estado não sabe qual das duas é, e responder o número da origem
# quando a URA pede o do destino põe o guincho na rua errada. Pergunta cuja
# resposta depende de onde a conversa está não é pergunta de dado: é passo.
_PERGUNTAS_DE_DADO = (
    # Destino ANTES de origem: as duas falam de endereço, e a mais específica
    # tem de ser testada primeiro ou "para onde levar" cairia em `local_atual`.
    ("destino", r"para onde (?:devemos |vamos |voce quer |o senhor quer )?(?:levar|rebocar|remover|"
                r"encaminhar)|endere[cç]o (?:de|do) destino|local de destino|destino do (?:ve[ií]culo|reboque|guincho)",
     ("local_destino",)),
    ("destino_cep", r"cep (?:de|do) destino|cep (?:para|do local) (?:onde|para onde) (?:levar|vamos)",
     ("destino_cep",)),
    ("cep", r"\bcep\b", ("local_cep",)),
    ("telefone", r"(?:n[uú]mero de |numero de )?(?:telefone|celular|whatsapp)\b|\bddd\b",
     ("telefone_contato",)),
    ("nome_no_local", r"nome (?:completo )?(?:d[ae] |do )?pessoa que est[aá]|nome de quem est[aá]|"
                      r"nome do (?:contato|acompanhante)",
     ("pessoa_no_local", "titular_nome")),
    ("nome_titular", r"nome (?:completo )?do (?:titular|segurado|propriet[aá]ri|condutor)",
     ("titular_nome",)),
    ("cor", r"cor do (?:ve[ií]culo|carro|autom[oó]vel)|\bqual a cor\b", ("veiculo_cor",)),
    ("placa", r"\bplaca\b", ("veiculo_placa",)),
    ("cpf", r"\bcpf\b|\bcnpj\b", ("titular_cpf",)),
    ("endereco", r"endere[cç]o (?:onde|completo|do local|atual|em que)|\bqual (?:[eé] )?o endere[cç]o\b|"
                 r"onde (?:o )?(?:ve[ií]culo|carro) (?:est[aá]|se encontra)|localiza[cç][ao]{1,2}o do ve[ií]culo",
     ("local_atual",)),
)


def _rotulo(slot: str) -> str:
    """O nome humano de um slot, vindo do vocabulário ÚNICO da ficha.

    Import tardio e com rede de segurança: este módulo é núcleo puro e roda em
    testes que carregam um arquivo só. Rótulo é enfeite de leitura — nunca pode
    ser motivo de um acionamento não sair."""
    try:
        from app.services.attendance_ficha import rotulo as _r

        return _r(slot)
    except Exception:  # noqa: BLE001
        return str(slot or "")


def pergunta_de_decisao(playbook: Optional[Dict[str, Any]], insurer_message: str) -> str:
    """O padrão de DECISÃO que casou com a tela, ou "" quando nenhuma casou.

    Confere DUAS fontes, e a ordem importa pouco porque as duas vetam:

    1. Os `finalize_anchors` DO PRÓPRIO corredor — a lista que já define, por
       seguradora, o que abre serviço de verdade. Ler dela em vez de copiá-la é
       o que garante que uma âncora nova de finalização passe a proteger o
       banco de respostas no mesmo commit, sem ninguém lembrar de vir aqui.
    2. A lista genérica acima, para as seguradoras cujo freio ainda não tem
       aquela redação mapeada.
    """
    texto = _norm_text(insurer_message)
    if not texto.strip():
        return ""
    for padrao in ((playbook or {}).get("finalize_anchors") or []):
        try:
            if re.search(padrao, texto, re.IGNORECASE):
                return f"finalize_anchor:{padrao}"
        except re.error:  # noqa: PERF203 — âncora malformada não pode abrir a porta
            continue
    for padrao in _PERGUNTAS_DE_DECISAO:
        if re.search(padrao, texto, re.IGNORECASE):
            return f"decisao:{padrao}"
    return ""


def responder_da_ficha(
    playbook: Optional[Dict[str, Any]],
    insurer_message: str,
    dados: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """A tela pergunta um DADO que já está na ficha? Então responde, na hora.

    Devolve sempre um dicionário com `ok`, e o `motivo` explica a recusa:

        ok=True   → {"campo", "slot", "resposta", "trecho"}
        ok=False  → motivo em {"vazia", "decisao", "nao_e_pergunta",
                               "nao_reconhecida", "sem_dado_na_ficha"}

    `sem_dado_na_ficha` é o motivo mais importante da lista: a pergunta FOI
    reconhecida e o dado NÃO existe. Aí não se inventa, não se aproxima e não
    se pega "o parecido" — cai no caminho antigo (pausa → Vigia → Cérebro), que
    é lento mas honesto. Um CEP inventado manda o guincho para outro bairro.
    """
    dados = {k: v for k, v in (dados or {}).items() if str(v or "").strip()}
    texto = _norm_text(insurer_message)
    if not texto.strip():
        return {"ok": False, "motivo": "vazia"}

    decisao = pergunta_de_decisao(playbook, insurer_message)
    if decisao:
        return {"ok": False, "motivo": "decisao", "padrao": decisao}

    # Aviso informativo ("o prestador está a caminho") não é pergunta, e uma
    # resposta a ele confundiria a URA — que espera silêncio ali.
    if not re.search(_MARCA_DE_PERGUNTA, texto, re.IGNORECASE):
        return {"ok": False, "motivo": "nao_e_pergunta"}

    for campo, padrao, candidatos in _PERGUNTAS_DE_DADO:
        if not re.search(padrao, texto, re.IGNORECASE):
            continue
        for slot in candidatos:
            valor = str(dados.get(slot) or "").strip()
            if valor:
                return {"ok": True, "campo": campo, "slot": slot, "resposta": valor,
                        "trecho": str(insurer_message)[:120]}
        # Reconhecida e sem dado: PARA AQUI. Continuar o laço deixaria uma
        # âncora mais larga (ex.: `\bcpf\b`) responder uma pergunta que já
        # tinha dono — e responder a pergunta errada com o dado certo é
        # indistinguível, para a seguradora, de responder qualquer bobagem.
        return {"ok": False, "motivo": "sem_dado_na_ficha", "campo": campo,
                "slot": candidatos[0], "rotulo": _rotulo(candidatos[0])}
    return {"ok": False, "motivo": "nao_reconhecida"}


# ===========================================================================
# FORMULÁRIO NATIVO — do reconhecimento ao transporte
# ===========================================================================

def registrar_formulario_nativo(session: Dict[str, Any],
                                interactive: Optional[Dict[str, Any]]) -> bool:
    """Guarda, NA SESSÃO, o que veio junto do formulário nativo.

    O `flow_token` mora no topo da sessão de propósito, e o nome dele é o que o
    protege: `snapshot_duravel` corta toda chave cujo nome contenha "token"
    (`_CHAVES_PROIBIDAS`), então ele fica no Redis — que é transitório, como a
    conversa — e **nunca** entra no checkpoint durável do Work Run. Aninhá-lo
    dentro de outro dicionário furaria esse corte em silêncio.
    """
    if not isinstance(interactive, dict) or interactive.get("kind") != "flow":
        return False
    flow = interactive.get("flow") or {}
    if not isinstance(flow, dict):
        return False
    token = "" if flow.get("flow_token") is None else str(flow["flow_token"]).strip()
    flow_id = "" if flow.get("flow_id") is None else str(flow["flow_id"]).strip()
    if not token and not flow_id:
        return False
    if token:
        session["flow_token"] = token          # volátil — some com a sessão
    if flow_id:
        session["flow_id_ativo"] = flow_id
    if flow.get("cta"):
        session["flow_cta"] = str(flow["cta"])[:120]
    # SPEC-063 — este é o NOME DO ENVELOPE, não o nome do formulário.
    #
    # 📊 O clique humano de 18/07/2026 traz `name = "galaxy_message"` — o rótulo
    # LEGADO da Meta, que o bot da família HDI/Yelum usa. O nome do formulário
    # ("Automóvel - Detalhes do atendimento…") é outra coisa e mora em
    # `wa_flow_response_params.flow_name`.
    #
    # A regra é ECOAR o que veio na captura. O padrão `"flow"` saiu daqui de
    # propósito: ele é o rótulo ATUAL da Meta, e chutá-lo numa seguradora que
    # usa o legado faz a resposta ser descartada em silêncio — gastando a única
    # janela antes de a URA encerrar. Sem captura, melhor pausar.
    if flow.get("name"):
        session["envelope_do_flow"] = str(flow["name"])
    return True


def _responder_formulario_nativo(
    session: Dict[str, Any],
    playbook: Dict[str, Any],
    insurer_message: str,
    *,
    interactive: Optional[Dict[str, Any]] = None,
    flow_sender: Optional[Callable[..., Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Detecta → monta → entrega. `None` = não é formulário; siga o fluxo antigo.

    Os três desfechos possíveis, e nenhum deles é "responde mais ou menos":

    - **falta dado** → pausa nomeando cada campo que falta, com a pergunta que
      a seguradora fez e as opções que ela oferece. Formulário meio preenchido
      escolhe o equipamento errado; é pior que formulário nenhum.
    - **pronto, sem transporte** → pausa. 📊 Este build do Evolution GO não tem
      rota de resposta de interativa (12 rotas de envio, nenhuma responde). A
      resposta montada vai no dossiê para a pessoa clicar em segundos, em vez
      de reentrevistar o segurado.
    - **pronto, com transporte provado** → envia, respeitando o MESMO portão de
      envio real de todo o resto do motor.
    """
    # A decisão é POR MENSAGEM, nunca pelo que a sessão lembra. Resolver o
    # schema por `session["flow_id_ativo"]` faria TODA mensagem seguinte ser
    # tratada como o formulário de novo: a URA manda dez telas depois dele, e o
    # motor responderia formulário a cada uma. O que identifica um formulário é
    # a mensagem que chegou agora — o texto que abre o flow, ou os metadados da
    # interativa desta mensagem.
    e_formulario_agora = isinstance(interactive, dict) and interactive.get("kind") == "flow"
    flow = detect_native_flow(playbook, insurer_message)
    if flow is None and e_formulario_agora:
        flow = native_flow(playbook, str(((interactive or {}).get("flow") or {}).get("flow_id") or ""))
    if not flow:
        # Chegou um formulário e não sabemos qual é.
        #
        # Até 03/08/2026 esta linha era inalcançável: os playbooks tinham um
        # gatilho `r"formulario nativo"` que mandava para humano antes de chegar
        # aqui. O gatilho saiu quando o canal de resposta passou a existir e foi
        # provado — e sem esta guarda o formulário desconhecido **escorregava
        # para a fase humana em silêncio**, sem motivo gravado, sem ninguém
        # avisado e sem nada a explicar depois.
        #
        # Fail-closed por construção: o que não se reconhece, não se responde —
        # e se diz por quê. É esta guarda, e não uma lista no playbook, que
        # protege os formulários que ainda não foram capturados.
        marcador = "FORMULARIO NATIVO" in str(insurer_message or "").upper()
        if e_formulario_agora or marcador:
            session["state"] = "needs_human"
            session["reason"] = "formulario_nativo_desconhecido"
            return session
        return None

    montado = montar_resposta_de_flow(flow, session.get("slots") or {})
    session["flow_resposta"] = {
        "ok": montado["ok"], "flow_id": montado["flow_id"], "flow_name": montado["flow_name"],
        "params": montado["params"], "missing": montado["missing"],
        "missing_detail": montado["missing_detail"], "defaults_used": montado["defaults_used"],
    }

    if not montado["ok"]:
        faltantes = [d.get("campo") for d in montado["missing_detail"]]
        session["state"] = "needs_human"
        session["reason"] = f"formulario_incompleto:{','.join(str(f) for f in faltantes)}"
        session["missing_slots"] = list(montado["missing"])
        return session

    token = str(session.get("flow_token") or "")
    if not token:
        # O corpo do formulário chegou, o token não. Sem ele o WhatsApp recusa a
        # resposta — e uma resposta recusada gasta a janela de 12min da URA sem
        # dizer nada a ninguém.
        session["state"] = "needs_human"
        session["reason"] = "formulario_pronto_sem_flow_token"
        return session
    if flow_sender is None:
        session["state"] = "needs_human"
        session["reason"] = "formulario_pronto_sem_transporte"
        return session

    live = bool(session.get("live")) and dispatch_live_enabled()
    resumo = f"[FORMULÁRIO NATIVO respondido: {len(montado['params'])} campos]"
    session.setdefault("transcript", []).append(
        {"direction": "out", "text": resumo, "at": _now(), "dry_run": not live,
         "step": "formulario_nativo"}
    )
    if live:
        try:
            envelope = session.get("envelope_do_flow")
            if not envelope:
                # Sem o nome ecoado da captura, não se envia. Pausa com a
                # resposta pronta — o humano marca em segundos.
                raise ValueError("envelope_do_flow ausente: nao ecoado da captura")
            enviado = flow_sender(
                flow_token=token,
                nome_do_envelope=envelope,
                params=montado["params"],
                flow_response_params={
                    k: v for k, v in (
                        ("flow_id", montado.get("flow_id")),
                        ("flow_name", montado.get("flow_name")),
                    ) if v
                } or None,
            )
        except Exception as exc:  # noqa: BLE001 — transporte nunca derruba o motor
            enviado = False
            session["flow_envio_erro"] = type(exc).__name__
        if not enviado:
            session["state"] = "needs_human"
            session["reason"] = "formulario_envio_falhou"
            return session
    session["state"] = "ura"
    return session


# ===========================================================================
# O QUE SERÁ PEDIDO — declarado ANTES, para coletar uma vez só
# ===========================================================================

def _slots_com_padrao_do_motor(playbook: Dict[str, Any], sub: Dict[str, Any]) -> List[str]:
    """Os slots que `new_dispatch_session` preenche sozinho, para ESTE corredor.

    Espelha a injeção de padrões daquela função — de propósito, campo por campo.
    Perguntar ao cliente algo cuja resposta o motor já sabe é a outra metade do
    defeito: a primeira metade é descobrir tarde o que falta; a segunda é fazer
    o segurado responder o que ninguém precisava perguntar."""
    comuns = ["telefone_adicionar_opcao", "ponto_referencia"]
    # Mesma regra de sufixo da injeção em `new_dispatch_session`: qualquer
    # `*_opcao` declarada no subserviço é do MOTOR, e some da lista do cliente.
    comuns += [chave for chave in (sub or {}) if chave.endswith("_opcao") and sub.get(chave)]
    if str(playbook.get("line_kind") or "") == "auto":
        comuns += ["servico_opcao", "servico_texto", "roda_travada", "quando",
                   "veiculo_cor", "rodovia"]
    return comuns


def tudo_que_sera_pedido(seguradora: str, ramo: str = "auto",
                         subservico: str = "") -> Dict[str, Any]:
    """A lista COMPLETA do que o acionamento vai pedir — antes de começar.

    O defeito que isto desfaz é de sequência, não de dado: hoje o acionamento
    descobre no MEIO da conversa com a seguradora que falta uma informação, e aí
    já é tarde — a URA está esperando, o relógio dela corre, e voltar ao
    segurado para perguntar mais uma coisa custa a conversa inteira. Com a lista
    na mão antes de abrir a conversa, a coleta com o cliente acontece **uma vez
    só**.

    E ela junta TRÊS fontes, porque as três aparecem na tela da seguradora:

    1. `required_slots` do subserviço — o que o corredor já declarava.
    2. Os `requires` dos passos de URA aplicáveis ao subserviço.
    3. **Os campos obrigatórios do formulário nativo** — a fonte que faltava, e
       a que 📊 travou os 4 acionamentos mais recentes da família HDI/Yelum. Um
       formulário que exige "em que nível da rua o veículo está" não perdoa: sem
       esse dado não há resposta possível, e ele nunca esteve em `required_slots`.

    Devolve ``{"ok", "playbook_ref", "seguradora", "subservico", "obrigatorios",
    "com_padrao", "slots", "erro"}``. `obrigatorios` traz, por item, `slot`,
    `rotulo`, `origem` e — quando vem do formulário — a `pergunta` e as `opcoes`
    exatas da seguradora, para o corretor perguntar com as palavras dela.
    """
    saida: Dict[str, Any] = {
        "ok": False, "playbook_ref": "", "seguradora": str(seguradora or ""),
        "subservico": canonical_subservice(subservico), "obrigatorios": [],
        "com_padrao": [], "slots": [], "erro": "",
    }
    ref = resolve_playbook_ref(seguradora, ramo)
    if not ref:
        saida["erro"] = "corredor_inexistente"
        return saida
    playbook = get_playbook(ref) or {}
    saida["playbook_ref"] = ref
    sub_key = canonical_subservice(subservico)
    sub = (playbook.get("subservices") or {}).get(sub_key)
    if sub is None:
        saida["erro"] = "subservico_invalido"
        return saida

    com_padrao = _slots_com_padrao_do_motor(playbook, sub)
    saida["com_padrao"] = [{"slot": s, "rotulo": _rotulo(s), "origem": "padrao_do_motor"}
                           for s in com_padrao]
    vistos: set = set(com_padrao)
    itens: List[Dict[str, Any]] = []

    def _somar(slot: str, origem: str, extra: Optional[Dict[str, Any]] = None) -> None:
        nome = str(slot or "").strip()
        if not nome or nome in vistos:
            return
        vistos.add(nome)
        itens.append({"slot": nome, "rotulo": _rotulo(nome), "origem": origem, **(extra or {})})

    for slot in sub.get("required_slots") or []:
        _somar(slot, "subservico")

    for step in playbook.get("ura_steps") or []:
        only = step.get("only_subservices")
        if only and sub_key not in [str(x).lower() for x in only]:
            continue
        for slot in step.get("requires") or []:
            _somar(slot, f"passo_de_ura:{step.get('step')}")

    for schema in (playbook.get("native_flows") or {}).values():
        for tela in schema.get("screens") or []:
            for comp in tela.get("components") or []:
                if not comp.get("required") or comp.get("default") is not None:
                    continue
                _somar(str(comp.get("slot") or comp.get("name") or ""), "formulario_nativo", {
                    "campo_do_formulario": str(comp.get("name") or ""),
                    "pergunta": str(comp.get("label") or ""),
                    "opcoes": [str(o.get("title") or "") for o in comp.get("options") or []
                               if str(o.get("title") or "").strip()],
                    "condicional": bool(comp.get("visible_if")),
                })

    saida["obrigatorios"] = itens
    saida["slots"] = [i["slot"] for i in itens]
    saida["ok"] = True
    return saida


# ---------------------------------------------------------------------------
# ENCAMINHAMENTO — o segundo desfecho possível do corredor (P-46)
# ---------------------------------------------------------------------------
#
# Até aqui todo corredor tinha um fim só: chegar ao protocolo. Vidros provou que
# isso é falso. 📊 URA da Porto, observada em 03/08/2026, TRÊS mensagens seguidas:
#
#     "Certo. Para conserto ou reparo de vidro, retrovisor, farol ou lanterna,
#      é necessário *preencher o formulário* de sinistro de vidros abaixo"
#     "https://porto.vc/reparovidros"
#     "Não se preocupe, esse acionamento *para vidros* não irá afetar a sua
#      classe de bônus."
#
# `detect_referral_step()` e `subservice_referral()` existiam e estavam
# provados, e **nada em produção os chamava**. O passo era `noop` — correto, o
# corredor não deve responder à URA aqui — e o caso ficava aberto até o
# watchdog: o segurado nunca recebia o formulário, e o desfecho era registrado
# como abandono.
#
# POR QUE NÃO SE FECHA NA PRIMEIRA MENSAGEM
# ------------------------------------------
# O ENTREGÁVEL é o link, e ele vem na mensagem SEGUINTE, sozinho. Fechar na
# âncora entregaria ao segurado uma frase sobre um formulário sem o formulário.
# Então a âncora abre uma janela curta de escuta, o link é capturado pelo mesmo
# `extract_capture_anchors` de sempre (`tracking_link`), e só aí o caso encerra.
#
# E se o link NÃO vier: handoff, com motivo escrito. `client_message` da Porto
# manda encaminhar "o link que a seguradora enviou NESTA conversa (nunca digite
# um endereço de memória)" — sem link não há entrega, e inventar um endereço de
# vidro é o tipo de ajuda que manda o segurado para o lugar errado.

# Quantas mensagens da seguradora esperar pelo link depois da âncora. Três é o
# tamanho da sequência observada; passar disso é a URA falando de outra coisa.
ENCAMINHAMENTO_MENSAGENS_DE_ESPERA = 3

# O que cada tipo de encaminhamento precisa ter em mãos para poder encerrar.
#
# `formulario` (Porto): o entregável é o ENDEREÇO. Sem ele, o `client_message`
# manda o atendente "encaminhar o link que a seguradora enviou nesta conversa" —
# uma instrução para repassar uma coisa que não existe. Espera, e sem link vira
# handoff: ninguém digita um endereço de vidro de memória.
#
# `orientacao` (Zurich): o entregável é o TEXTO. 📊 A mensagem observada em
# 03/08/2026 não traz link nenhum — "encontre informações sobre como pedir o
# reparo ou a troca de vidros, para-brisa, faróis e retrovisores". Esperar um
# link que a seguradora nunca mandou transformaria o desfecho certo em handoff.
_ENCAMINHAMENTO_EXIGE_LINK = ("formulario",)


def _resolver_encaminhamento(session: Dict[str, Any]) -> Dict[str, Any]:
    """Fecha o caso como `encaminhado` quando o entregável já está em mãos.

    Enquanto o link não chega, devolve a sessão sem resposta — quem está do
    outro lado é uma URA que não espera nada de nós neste ponto.
    """
    ref = dict(session.get("referral") or {})
    link = str((session.get("captured") or {}).get("tracking_link") or "").strip()
    exige_link = str(ref.get("kind") or "") in _ENCAMINHAMENTO_EXIGE_LINK

    if link or not exige_link:
        ref["link"] = link
        ref["entregue_em"] = _now()
        session["referral"] = ref
        session["state"] = "encaminhado"
        session["reason"] = f"encaminhado:{ref.get('kind') or 'orientacao'}"
        return session

    esperou = int(ref.get("aguardando") or 0) + 1
    ref["aguardando"] = esperou
    session["referral"] = ref
    if esperou > ENCAMINHAMENTO_MENSAGENS_DE_ESPERA:
        session["state"] = "needs_human"
        session["reason"] = "encaminhamento_sem_link"
    return session


# ===========================================================================
# 🔴 O GUARDA DA ÚNICA DECISÃO IRREVERSÍVEL
# ===========================================================================
#
# Ele mora AQUI, e não dentro de `guard_human_phase_reply`, por um motivo
# medido: 📊 quem responde a tela de confirmação, na maioria das seguradoras,
# não é a LLM — é o passo determinístico do corredor (`confirmar_atendimento` →
# "1", `confirmar_solicitacao` → "Confirmar solicitação", `confirmar_abertura`
# → "Sim"). `guard_human_phase_reply` fiscaliza o RASCUNHO da LLM e nunca vê
# esses três. Um guarda lá dentro deixaria passar justamente quem mais dispara.
#
# Este é o choke point por onde os DOIS caminhos passam: logo depois de
# `detect_finalize_anchor` e ANTES de `match_ura_step`. Um ponto só.

# Quantas mensagens da seguradora entram na janela de conferência.
#
# 📊 Não pode ser 1: na Azul o RESUMO e a PERGUNTA são mensagens SEPARADAS — o
# resumo não casa `finalize_anchor` nenhuma e a tela que casa não tem dado
# nenhum. Três cobre o pior caso real (resumo, um aviso no meio, a pergunta) sem
# arrastar dados de uma etapa antiga para dentro da conferência da etapa atual.
_JANELA_DE_CONFERENCIA = 3

# A pergunta que substitui o SEGUNDO "sim". Sem dígito nenhum de propósito: o
# guard de números do outro lado só autoriza dígito que venha do caso, e esta
# frase não precisa de nenhum para fazer o trabalho dela.
_PERGUNTA_DE_STATUS = ("Só para não duplicar o chamado: essa solicitação já foi registrada? "
                       "Se sim, pode me passar o número do atendimento?")


def _telas_da_conferencia(session: Dict[str, Any], atual: str,
                          quantas: int = _JANELA_DE_CONFERENCIA) -> List[str]:
    """As últimas mensagens DA SEGURADORA, da mais antiga para a mais nova."""
    entradas = [str(t.get("text") or "") for t in (session.get("transcript") or [])
                if t.get("direction") == "in" and str(t.get("text") or "").strip()]
    atual = str(atual or "")
    # `handle_insurer_message` já registrou a mensagem atual (truncada em 2000).
    # O `append` aqui é para quem chamar o guarda por fora desse caminho.
    if not entradas or entradas[-1] != atual[:2000]:
        entradas.append(atual)
    return entradas[-max(1, int(quantas)):]


# As saídas que ESTE código escreve e que, por construção, não são um "sim".
#
# A lista é de passos NOSSOS, e é por isso que ela pode existir: cada prefixo
# aqui nomeia uma mensagem que o motor gera e sabe o que significa. Uma lista
# dos passos que CONFIRMAM seria o contrário — teria de adivinhar o vocabulário
# de cada seguradora e erraria para o lado caro.
#
# Sem ela, a própria correção ("Antes de confirmar: o endereço de origem é…")
# seria lida como afirmativa: `e_afirmativa` casa a palavra "confirmar".
_PASSOS_QUE_NAO_CONFIRMAM = ("correcao:", "confirmacao_repetida", "ficha:",
                             "resumo_analista", "finalize_abort")


def _confirmacoes_que_de_fato_sairam(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Descarta o registro de confirmação em que NENHUM "sim" chegou a sair.

    Registrar ANTES de emitir é o certo — a trava tem de existir no instante em
    que o motor cai, e trava gravada depois não protege esse instante. Mas
    registrar não é emitir: um `needs_human` por slot faltando, ou uma LLM que
    preferiu perguntar, deixam para trás a trava de uma confirmação que nunca
    houve — e ela bloquearia o "sim" legítimo da tela seguinte.

    A pergunta é MEDIDA no transcript, não deduzida: depois do índice gravado,
    saiu alguma resposta afirmativa PARA AQUELA TELA?

    E a assimetria é deliberada. `e_afirmativa` falha para o lado do "sim"
    (texto que não dá para classificar é tratado como afirmativo), então a
    trava tende a FICAR DE PÉ na dúvida. O preço de errar assim é uma pergunta
    de status a mais; o preço de errar para o outro lado é um segundo guincho.
    """
    transcript = list(session.get("transcript") or [])

    def _foi_um_sim(t: Dict[str, Any], tela: str) -> bool:
        if t.get("direction") != "out":
            return False
        if str(t.get("step") or "").startswith(_PASSOS_QUE_NAO_CONFIRMAM):
            return False
        return e_afirmativa(str(t.get("text") or ""), tela)

    vivas = [
        c for c in list(session.get("confirmacoes") or [])
        if any(_foi_um_sim(t, str(c.get("tela") or ""))
               for t in transcript[int(c.get("saida_em") or 0):])
    ]
    session["confirmacoes"] = vivas
    return vivas


def _corrigir_em_vez_de_confirmar(session: Dict[str, Any], veredito: Dict[str, Any],
                                  tela: str, *,
                                  sender: Optional[Callable[[str], Any]] = None) -> Dict[str, Any]:
    """Reprovar NÃO é chamar humano. A escada, na ordem:

    1. a própria tela oferece o conserto ("Mudar localização atual")? responde ela;
    2. não oferece? corrige por texto, com o valor DO CASO;
    3. re-confere o próximo resumo (a próxima passagem por aqui);
    4. esgotou o teto → aí sim `needs_human`, com o dossiê que já existe.

    O teto existe porque o inverso de "nunca confirma" também é ruim: um
    corredor que corrige para sempre é uma URA presa numa tela até o timeout.
    """
    divergencias = list(veredito.get("divergencias") or [])
    campo = str(divergencias[0]["campo"]).split("_")[0] if divergencias else "?"
    contas = session.setdefault("correcoes", {})
    por_campo = int(contas.get(campo) or 0)
    total = sum(int(v or 0) for v in contas.values())
    proposta = resposta_de_correcao(divergencias, tela, session.get("slots") or {})
    if (por_campo >= MAX_CORRECOES_POR_CAMPO
            or total >= MAX_CORRECOES_POR_SESSAO
            or not str(proposta.get("reply") or "").strip()):
        session["state"] = "needs_human"
        session["reason"] = f"conferencia_divergente:{campo}"
        return session
    contas[campo] = por_campo + 1
    estado = session.get("state") if session.get("state") in ("ura", "human_phase") else "ura"
    return _emit(session, proposta["reply"], sender=sender, next_state=estado,
                 step=f"correcao:{campo}")


def _conferir_antes_de_confirmar(session: Dict[str, Any], playbook: Dict[str, Any],
                                 insurer_message: str, finalize: str, *,
                                 sender: Optional[Callable[[str], Any]] = None) -> Optional[Dict[str, Any]]:
    """Confere o resumo contra o caso. `None` = pode seguir o fluxo normal.

    Devolver `None` é o caminho da APROVAÇÃO, e é assim de propósito: aprovado,
    quem responde continua sendo quem sempre respondeu (o passo do corredor ou o
    cérebro). O guarda não vira um segundo respondedor — ele só decide se a
    resposta de sempre pode sair.
    """
    veredito = conferir_confirmacao(
        playbook, _telas_da_conferencia(session, insurer_message),
        session.get("slots") or {}, session.get("subservice") or "",
        parse_address=parse_address_br,
    )
    digest = digest_da_conferencia(veredito, finalize)
    # O veredito fica na sessão INTEIRO, inclusive quando aprova. É ele que
    # responde "com base em quê o agente disse sim?" depois do fato — e é onde
    # `resumo_nao_lido` aparece para quem mantém o corredor.
    session["conferencia"] = {
        "ok": bool(veredito["ok"]), "conferidos": list(veredito["conferidos"]),
        "divergencias": list(veredito["divergencias"]), "motivo": str(veredito["motivo"]),
        "digest": digest, "anchor": str(finalize or "")[:120], "at": _now(),
    }

    if not veredito["ok"]:
        return _corrigir_em_vez_de_confirmar(session, veredito, insurer_message, sender=sender)

    _confirmacoes_que_de_fato_sairam(session)
    trava = pode_confirmar_de_novo(session, digest)
    if not trava.get("ok"):
        # 📊 Sem o `_would_loop` aqui, a mesma tela reenviada cinco vezes gerava
        # CINCO perguntas de status idênticas — o corredor trocava um loop de
        # "sim" por um loop de pergunta, e ninguém era chamado. Perguntar duas
        # vezes é insistência legítima; a terceira é uma URA que não vai
        # responder, e aí quem resolve é gente.
        if trava.get("acao") == "perguntar_status" and not _would_loop(
                session, _PERGUNTA_DE_STATUS, "confirmacao_repetida"):
            estado = session.get("state") if session.get("state") in ("ura", "human_phase") else "ura"
            return _emit(session, _PERGUNTA_DE_STATUS, sender=sender, next_state=estado,
                         step="confirmacao_repetida")
        session["state"] = "needs_human"
        session["reason"] = f"confirmacao_bloqueada:{trava.get('motivo') or 'desconhecido'}"
        return session

    registrar_confirmacao(
        session, digest, finalize, _now(),
        saida_em=len(session.get("transcript") or []),
        # A CAUDA da tela, e não o começo: as opções ("1 - Sim", "Confirmar
        # solicitação") vivem no fim da mensagem, e é delas que
        # `e_afirmativa` precisa para reconhecer o "sim" que saiu.
        tela=str(insurer_message or "")[-400:],
    )
    return None


def handle_insurer_message(
    session: Dict[str, Any],
    insurer_message: str,
    *,
    sender: Optional[Callable[[str], Any]] = None,
    human_phase_reply: Optional[str] = None,
    interactive: Optional[Dict[str, Any]] = None,
    flow_sender: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Processa UMA mensagem da seguradora e decide a próxima ação.

    - captura âncoras SEMPRE (protocolo pode vir em qualquer fase);
    - gatilho de handoff → needs_human;
    - âncora de URA conhecida → resposta determinística;
    - sem âncora na fase ura → transição para human_phase;
    - human_phase: usa `human_phase_reply` (redigida pela LLM guardada) se dada.
    """
    playbook = get_playbook(session.get("playbook_ref") or "")
    if not playbook:
        session["state"] = "needs_human"
        session["reason"] = "playbook_not_found"
        return session

    # Inbound sem texto (mídia/sticker da seguradora): registra e não responde.
    if not str(insurer_message or "").strip():
        return session

    session.setdefault("transcript", []).append(
        {"direction": "in", "text": str(insurer_message)[:2000], "at": _now()}
    )

    # O `flow_token` chega JUNTO da mensagem que abre o formulário e não volta
    # mais. Guardar aqui, antes de qualquer decisão, é o que garante que ele
    # exista quando a resposta estiver pronta — inclusive se o formulário só for
    # respondido algumas mensagens depois.
    registrar_formulario_nativo(session, interactive)

    captured = extract_capture_anchors(playbook, insurer_message)
    if captured:
        session.setdefault("captured", {}).update(captured)

    got = session.get("captured", {})

    # P-46 — JÁ ESTAMOS NUM ENCAMINHAMENTO: a partir daqui tudo o que a
    # seguradora manda é ENTREGA, não pergunta. Esta janela vem antes de tudo de
    # propósito. Depois de "aqui não se abre chamado", uma âncora de protocolo
    # que casasse um telefone ou um número qualquer transformaria um formulário
    # de vidro em "seu serviço foi aberto, protocolo X" — e nenhum passo de URA
    # deve ser respondido enquanto se espera o link.
    if session.get("referral"):
        return _resolver_encaminhamento(session)

    # O PROTOCOLO SOZINHO JÁ É NOTÍCIA — e o segurado tem direito a ela.
    #
    # A regra era `protocol` E (`schedule` OU `eta` OU `tracking_link`). A ideia
    # era boa: só avisar quando houvesse o quadro completo. Mas 📊 o playbook
    # residencial da Allianz captura apenas `protocol`, `password` e `schedule`
    # — **sem eta e sem link**. Se a URA devolvesse o protocolo e o agendamento
    # não casasse o regex exato, o segurado **nunca era avisado**: o número
    # ficava no dossiê, e a pessoa que teve um cano estourando em casa não sabia
    # que o serviço tinha sido aberto.
    #
    # Protocolo é a prova de que o chamado existe. Chegou o protocolo, avisa —
    # com o que houver. `client_summary_from_capture` já monta a mensagem com os
    # campos presentes e omite os ausentes; não há risco de frase quebrada.
    #
    # E uma exceção que só apareceu ao afrouxar a regra: mensagem que pede
    # HANDOFF não vira captura, por mais que pareça trazer um protocolo.
    #
    # 📊 A Alfa responde *"no momento eu não consigo te ajudar, entre em contato
    # com a nossa Central nos telefones: 4003-2532"*. A âncora de protocolo casa
    # o **telefone**. Com a regra antiga isso passava despercebido — faltavam o
    # eta e o link, então nunca virava `captured`. Afrouxar teria transformado
    # uma recusa em "serviço aberto, aqui está seu protocolo 4003-2532".
    #
    # O handoff é avaliado depois da captura neste fluxo, e mudar essa ordem
    # mexeria em tudo. Consultá-lo aqui é a correção local e verificável.
    if got.get("protocol") and not detect_handoff_trigger(playbook, insurer_message):
        session["state"] = "captured"
        return session

    # P-46 — A SEGURADORA DISSE QUE NÃO ABRE CHAMADO AQUI.
    #
    # Espelho de `detect_finalize_anchor`, do outro lado do fluxo: em vez de "a
    # seguradora vai abrir o serviço", é "a seguradora não vai abrir serviço
    # nenhum aqui — ela entregou o caminho". Vem DEPOIS da captura de protocolo
    # (protocolo real vence sempre) e ANTES de qualquer passo de URA, porque a
    # partir daqui não há mais menu a responder.
    passo_encaminha = detect_referral_step(playbook, insurer_message)
    if passo_encaminha:
        session["referral"] = {
            **subservice_referral(playbook, session.get("subservice") or ""),
            "step": str(passo_encaminha.get("step") or ""),
            # As PALAVRAS DA SEGURADORA. Os dois `client_message` mandam
            # "repassar exatamente o que a seguradora enviou nesta conversa" —
            # sem guardar o texto, quem entrega teria de parafraseá-lo, e
            # paráfrase de instrução de sinistro é onde nasce a promessa que
            # ninguém fez.
            "insurer_text": str(insurer_message)[:600],
            "aguardando": 0,
        }
        return _resolver_encaminhamento(session)

    # Seguradora ENCERROU a conversa (timeout/resposta inválida): parar de falar
    # e liberar a corretora para reabrir (visto no teste Yelum 2026-07-10).
    if re.search(
        r"conversa ser[áa] encerrada|estamos encerrando (?:esta|a) conversa|"
        r"tempo m[áa]ximo de espera.*excedid|encerrad[ao] por (?:inatividade|falta de intera)|"
        r"falta de intera[çc][ãa]o esta conversa foi encerrada|conversa foi encerrada",
        _norm_text(insurer_message),
        re.IGNORECASE,
    ):
        session["state"] = "needs_human"
        session["reason"] = "insurer_closed"
        return session

    # FREIO DE FINALIZAÇÃO (founder 2026-07-11): existe SÓ para o modo TESTE.
    # A seguradora vai CONFIRMAR/ABRIR o serviço de verdade → em teste, CANCELA
    # educadamente (abort_reply do playbook; sem abort, silêncio e a URA encerra).
    # Em modo LIVE (corredor validado) NÃO trava: o passo de confirmação é
    # respondido pelos próprios ura_steps e o fluxo completa ponta a ponta.
    finalize = detect_finalize_anchor(playbook, insurer_message)
    if finalize and not _finalize_allowed(session):
        session["reason"] = f"finalize_test_abort:{finalize}"
        abort = str(playbook.get("finalize_abort_reply") or "").strip()
        if abort:
            return _emit(session, abort, sender=sender, next_state="test_aborted", step="finalize_abort")
        session["state"] = "test_aborted"
        return session

    # 🔴 A CONFERÊNCIA, E ELA VEM ANTES DE `match_ura_step` DE PROPÓSITO.
    #
    # Chegar aqui com `finalize` significa que o modo é LIVE (o freio de teste
    # acabou de devolver, logo acima) e que a próxima mensagem ABRE o serviço de
    # verdade. É o último instante em que ainda dá para não mandar o guincho
    # para o endereço errado.
    #
    # Uma linha depois de `match_ura_step` já seria tarde: o passo
    # `confirmar_atendimento` teria respondido "1" e voltado com `return`.
    if finalize:
        guarda = _conferir_antes_de_confirmar(
            session, playbook, insurer_message, finalize, sender=sender)
        if guarda is not None:
            return guarda

    # Âncora de URA conhecida responde ANTES dos gatilhos de handoff: menus reais
    # listam "Sinistro"/"Acidente" como OPÇÕES (Porto opção 6, Bradesco opção 2) e
    # isso não significa que o caso é sinistro. Handoff só quando NENHUM passo
    # conhecido casou (a mensagem é sobre o caso, não um menu mapeado).
    step = match_ura_step(playbook, insurer_message, subservice=session.get("subservice"))
    if step:
        # Passo "noop": mensagem informativa (fila, aguarde, "ainda não
        # identificamos") — reconhecer e NÃO responder nada.
        if step.get("noop"):
            return session
        # reply_repeat: na 2ª+ vez que o MESMO passo aparecer, responder diferente
        # (ex.: menu raiz da Porto — 1ª vez re-identifica o cliente, 2ª segue).
        step_counts = session.setdefault("step_counts", {})
        step_name = str(step.get("step") or "")
        effective = dict(step)
        if step.get("reply_repeat") and int(step_counts.get(step_name) or 0) >= 1:
            effective["reply"] = step["reply_repeat"]
        # reply_if_step_done: se OUTRO passo já aconteceu nesta sessão, a resposta
        # muda (ex.: menu raiz da Porto depois do CPF digitado → serviço direto,
        # sem re-identificar um cliente que já é o nosso).
        cond = step.get("reply_if_step_done")
        if isinstance(cond, dict) and int(step_counts.get(str(cond.get("step") or "")) or 0) >= 1:
            effective["reply"] = str(cond.get("reply") or effective["reply"])
        if step.get("dynamic") == "vehicle_by_plate":
            # Menu de veículos: escolhe pela PLACA MASCARADA (teste Allianz 12/07:
            # '1' fixo pegou o carro ERRADO numa apólice com 2 veículos).
            from app.services.corridor_playbooks import pick_option_by_plate

            picked = pick_option_by_plate(insurer_message, str((session.get("slots") or {}).get("veiculo_placa") or ""))
            if picked:
                effective["reply"] = picked
            elif step.get("fallback_adaptive"):
                effective["reply"] = ""  # sem match seguro → adaptativo decide
        rendered = render_reply(effective, session.get("slots") or {})
        if step.get("dynamic") == "vehicle_by_plate" and not (rendered.get("reply") or "").strip():
            rendered = {"ok": False, "missing": ["veiculo_opcao"], "reply": None}
        if not rendered["ok"]:
            # ==============================================================
            # 🔴 A TELA CONHECIDA COM DADO FALTANDO — 19/08/2026
            # ==============================================================
            #
            # ESTE ERA O TRAVAMENTO. Não a tela desconhecida: a CONHECIDA.
            #
            # 📊 Medido no acervo de corredores em 19/08: `fallback_adaptive`
            # existia em 29 de ~250 passos, e em **0 de 29** no
            # `allianz-residencial`. Ou seja: naquele corredor, QUALQUER tela
            # reconhecida cujo slot não estivesse preenchido virava
            # `needs_human` no mesmo instante — e `needs_human` está dentro de
            # `_TERMINAL_STATES` do Vigia, que começa com
            # `if state in _TERMINAL_STATES: return None`.
            #
            # O cérebro estava a três linhas daqui e nunca era consultado.
            # Ninguém tentava de novo. Nunca. 📊 Foi o que produziu os 2min22
            # e o clique manual do Founder em 18/08: a tela `o_que_aconteceu`
            # exigia `problema_eletrico_opcao`, nada preenchia, e o motor
            # parou de vez.
            #
            # O DISCRIMINADOR NÃO É NOVO, e isso é de propósito (CLAUDE.md §5).
            # `detect_finalize_anchor` já é a autoridade do produto sobre "esta
            # tela ABRE O SERVIÇO de verdade": é a lista `finalize_anchors` do
            # próprio corredor, a mesma que arma o freio de finalização.
            # Reusá-la significa que uma âncora nova protege este ponto no
            # MESMO commit, sem ninguém lembrar de vir aqui.
            #
            #   tela REVERSÍVEL (menu, pedido de dado)  → o cérebro pensa
            #   tela IRREVERSÍVEL (confirmar, abrir)    → para, como antes
            #
            # Errar num menu custa uma tela e um "Voltar". Errar na
            # confirmação manda um técnico ao endereço errado. Não é a mesma
            # aposta, e por isso não é a mesma regra.
            #
            # 🔴 NÃO É `pergunta_de_decisao`, e a diferença foi MEDIDA.
            #
            # A primeira versão deste bloco usava `pergunta_de_decisao`, que
            # parece a escolha óbvia pelo nome. 📊 Rodando as duas contra as
            # telas reais dos corredores residenciais, ela marca como
            # "decisão" três MENUS: "Qual o serviço que você precisa?",
            # "Informe o tipo de serviço" e — o pior — "Escolha qual data
            # deseja agendar", que é um passo do fluxo da máquina de lavar.
            # Ela é larga porque serve a outro propósito (decidir se o
            # silêncio é legítimo), e com ela o motor pararia exatamente onde
            # precisa pensar. `detect_finalize_anchor` não marca nenhum menu.
            #
            # ⚠️ RESIDUAL ANOTADO: uma tela de confirmação que o corredor
            # ainda não mapeou não é pega aqui. A segunda camada existe e é o
            # próprio prompt do cérebro (`finalize_rule`), que em modo de
            # teste manda responder NAO_SEI diante de qualquer confirmação.
            # Duas camadas, nenhuma perfeita sozinha.
            decisao = detect_finalize_anchor(playbook, insurer_message)
            if step.get("fallback_adaptive") or not decisao:
                # O cérebro assume. Ele recebe o caso inteiro, a intenção de
                # cada passo do playbook e os últimos turnos — e agora também
                # O QUE FALTOU, abaixo, que é a informação que mais o ajuda.
                session["falta_para_a_ura"] = {
                    "campo": step_name,
                    "slot": ",".join(rendered["missing"]),
                    "rotulo": (f"{', '.join(rendered['missing'])} "
                               f"(a tela `{step_name}` pede isso)"),
                }
                session["ultimo_passo_sem_dado"] = {
                    "step": step_name,
                    "faltou": list(rendered["missing"]),
                    "notes": str(step.get("notes") or ""),
                }
                logger.info(
                    "[DISPATCH] passo %r sem %s — REVERSÍVEL, o cérebro assume "
                    "(antes isto era needs_human terminal)",
                    step_name, rendered["missing"])
            else:
                # Irreversível. Continua parando — e agora o motivo diz por quê.
                session["state"] = "needs_human"
                session["reason"] = f"missing_slots:{','.join(rendered['missing'])}"
                session["missing_slots"] = rendered["missing"]
                session["parou_em_decisao"] = decisao
                logger.warning(
                    "[DISPATCH] 🔴 passo %r sem %s numa tela IRREVERSÍVEL (%s) "
                    "— parando, como deve ser", step_name, rendered["missing"],
                    decisao)
                return session
        else:
            # LOOP GUARD: nunca enviar a MESMA resposta À MESMA PERGUNTA 3x
            # (teste Yelum 2026-07-10: CPF repetido 4x até derrubar a conversa).
            if _would_loop(session, rendered["reply"], step_name):
                session["state"] = "needs_human"
                session["reason"] = "loop_guard"
                return session
            step_counts[step_name] = int(step_counts.get(step_name) or 0) + 1
            return _emit(session, rendered["reply"], sender=sender, next_state="ura", step=step_name)

    # FORMULÁRIO NATIVO (a tela que não aceita texto). Vem ANTES do gatilho de
    # handoff porque o gatilho `formulario nativo` do corredor casaria primeiro
    # e o caso viraria `needs_human` sem que ninguém tivesse tentado montar a
    # resposta. O gatilho continua no corredor, e continua sendo a rede: quando
    # o schema deste flow não é conhecido, esta função devolve None e a queda em
    # needs_human acontece exatamente como antes.
    pelo_formulario = _responder_formulario_nativo(
        session, playbook, insurer_message, interactive=interactive, flow_sender=flow_sender)
    if pelo_formulario is not None:
        return pelo_formulario

    trigger = detect_handoff_trigger(playbook, insurer_message)
    if trigger:
        session["state"] = "needs_human"
        session["reason"] = f"handoff_trigger:{trigger}"
        return session

    # Pesquisa de satisfação/avaliação pós-atendimento: ignorar sempre.
    if re.search(_SURVEY_NOOP_RE, _norm_text(insurer_message), re.IGNORECASE):
        return session

    # BANCO DE RESPOSTAS DETERMINÍSTICO — a camada ANTES do Cérebro.
    #
    # Chega aqui a tela que nenhum passo mapeado reconheceu. Antes, isso era
    # pausa garantida: Vigia (20s), Sentinela, Cérebro — minutos, numa URA que
    # encerra em 12. Se a pergunta for por um DADO que já está no caso, ela é
    # respondida agora, sem rede nenhuma. Se não for, nada muda: segue para a
    # fase humana e para o Cérebro, como sempre foi.
    da_ficha = responder_da_ficha(playbook, insurer_message, session.get("slots") or {})
    if da_ficha.get("ok"):
        passo = f"ficha:{da_ficha['campo']}"
        if _would_loop(session, da_ficha["resposta"], passo):
            session["state"] = "needs_human"
            session["reason"] = "loop_guard"
            return session
        estado = session.get("state") if session.get("state") in ("ura", "human_phase") else "ura"
        return _emit(session, da_ficha["resposta"], sender=sender, next_state=estado, step=passo)
    if da_ficha.get("motivo") == "sem_dado_na_ficha":
        # A pergunta foi entendida e o dado NÃO existe. Não se inventa: registra
        # o nome do que falta (o humano lê isso no dossiê) e segue o caminho antigo.
        session["falta_para_a_ura"] = {"campo": da_ficha.get("campo"),
                                       "slot": da_ficha.get("slot"),
                                       "rotulo": da_ficha.get("rotulo")}

    # Sem âncora de URA: fase humana da seguradora.
    if session.get("state") == "ura":
        session["state"] = "human_phase"
    # ANALISTA humano assumiu ("me chamo X, como posso ajudar?"): apresentar o
    # resumo estruturado do caso UMA vez, deterministicamente (é o que a
    # operadora real faz — colar o pedido completo para o analista).
    if (
        session.get("state") == "human_phase"
        and not session.get("summary_sent")
        and playbook.get("opening_template")
        and re.search(
            r"me chamo |meu nome [ée] |como posso (?:te )?ajudar|darei? (?:continuidade|prosseguimento)|"
            r"prosseguirei com o atendimento|irei realizar seu atendimento|vou te ajudar",
            _norm_text(insurer_message),
            re.IGNORECASE,
        )
    ):
        summary = render_opening_message(playbook, session.get("subservice") or "", session.get("slots") or {})
        session["summary_sent"] = True
        return _emit(session, summary, sender=sender, next_state="human_phase", step="resumo_analista")
    if session.get("state") == "human_phase" and human_phase_reply:
        if _would_loop(session, human_phase_reply, None):
            session["state"] = "needs_human"
            session["reason"] = "loop_guard"
            return session
        return _emit(session, human_phase_reply, sender=sender, next_state="human_phase")
    # Fail-safe: sem resposta preparada, não responde às cegas.
    session.setdefault("pending_insurer_messages", []).append(str(insurer_message)[:2000])
    return session


def _norm_text(text: str) -> str:
    """A MESMA normalização das âncoras de corredor — uma definição só.

    Era uma cópia literal de `corridor_playbooks._norm`, e cópia de normalizador
    é onde o conserto de um lado deixa o outro quebrado: os padrões daqui
    (`insurer_closed`, pesquisa de satisfação, "me chamo X") e os `finalize_anchors`
    lidos em `pergunta_de_decisao` são âncoras de corredor pelo mesmo critério —
    casam texto de seguradora. Delegar garante que o `*` do negrito do WhatsApp
    caia nos dois lugares, hoje e no próximo conserto.
    """
    return _norm_corredor(text)


def _would_loop(session: Dict[str, Any], reply: str, step: Optional[str] = None) -> bool:
    """True se as DUAS últimas saídas já foram a MESMA resposta À MESMA PERGUNTA
    (mesmo passo). Comparar só o texto dava FALSO POSITIVO (teste Allianz 12/07:
    a URA exige '1' legitimamente em passos seguidos — telefone ok=1,
    automotor=1, pane=1 — e o motor pausava achando que era loop)."""
    outs = [
        (t.get("text"), t.get("step"))
        for t in (session.get("transcript") or [])
        if t.get("direction") == "out"
    ]
    key = (reply, step)
    return len(outs) >= 2 and outs[-1] == key and outs[-2] == key


def build_human_phase_messages(session: Dict[str, Any], insurer_message: str,
                               ura_map: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Prompt da fase humana/adaptativa da seguradora (LLM redige, guard fiscaliza).

    INTELIGÊNCIA sem cabresto: além de responder o especialista humano, este cérebro
    também dá conta de uma URA que MUDOU (a Allianz trocou uma palavra/ordem do menu
    e nenhuma âncora determinística casou). Recebe a INTENÇÃO de cada passo do
    playbook + os dados do caso, e decide sozinho — inclusive escolher a opção certa
    de um menu numerado. Regras duras: só dados do caso, sem números inventados (o
    guard fiscaliza), e se realmente não der pra deduzir → NAO_SEI (pausa p/ humano)."""
    slots = session.get("slots") or {}
    captured = session.get("captured") or {}
    # CADA LINHA DIZ SE O CLIENTE CONFIRMOU OU SE O MOTOR CHUTOU.
    #
    # 📊 Sem a marca, o prompt afirmava `rodovia: Não` sob o título "Dados do
    # caso (únicos números permitidos)" — e o modelo repetia isso a um atendente
    # humano da seguradora como se o cliente tivesse dito. Rodovia troca o
    # caminhão que vem.
    padrao = set(session.get("slots_padrao") or ())
    fatos = "\n".join(
        f"- {k}: {v}" + ("   (padrão — o cliente NÃO confirmou)" if k in padrao else "")
        for k, v in slots.items() if v not in (None, "")
    )
    if captured:
        fatos += "\n" + "\n".join(f"- capturado {k}: {v}" for k, v in captured.items())
    if padrao:
        fatos += ("\n\nAs linhas marcadas (padrão) foram preenchidas pelo sistema para a URA "
                  "não travar, e NÃO vieram do cliente. Use-as para responder menu. "
                  "NUNCA as afirme a uma pessoa como fato: se perguntarem por elas, "
                  "diga que confirma e retorna, ou responda NAO_SEI.")
    pending = session.get("pending_insurer_messages") or []
    # A TELA ATUAL JÁ CHEGA MONTADA — e repeti-la aqui passou a mentir o rótulo.
    #
    # Desde que o roteador delibera por TURNO (`dispatch_router._tela_do_turno`),
    # `insurer_message` é a rajada inteira, montada a partir desta mesma lista.
    # Listá-la de novo sob "mensagens ANTERIORES" faria o modelo ler a pergunta
    # de agora como pergunta velha — e ainda repetida, que é o jeito mais rápido
    # de o modelo achar que já respondeu.
    #
    # Só entra o que ficou de fora da tela: o que sobrou de turnos passados.
    _tela_atual = " ".join(str(insurer_message or "").split())
    anteriores = [m for m in pending[-3:]
                  if " ".join(str(m).split()) not in _tela_atual]
    contexto_pendente = (
        "\nMensagens anteriores da seguradora ainda sem resposta:\n"
        + "\n".join(f"- {m}" for m in anteriores)
    ) if anteriores else ""

    # O MODELO COMEÇAVA DO ZERO A CADA TURNO. Era este o "engessado".
    #
    # 📊 Medido em 05/08/2026. A única memória que chegava ao prompt era
    # `pending_insurer_messages` — e `reply_human_phase` ZERA essa lista a cada
    # resposta aceita (linha ~1476). Ou seja: em toda a fase humana, o modelo
    # via UMA mensagem e não sabia o que ele mesmo tinha acabado de responder.
    #
    # 📊 Um acionamento tem mediana de 10 respostas nossas. Eram dez partidas
    # do zero. Nenhuma conversa é possível assim — e conversar é justamente o
    # que se pede dele, porque 89% dos atendimentos da Allianz terminam com um
    # atendente HUMANO da seguradora do outro lado.
    #
    # O `transcript` da sessão sempre teve os dois lados: `direction: "in"` na
    # entrada (linha ~1042) e `"out"` no `_emit` (linha ~1599). E o `_emit` só
    # roda DEPOIS que o guarda aceitou — então a cauda nunca traz rascunho
    # recusado, que seria o modelo achando que disse algo que nunca saiu.
    #
    # Seis turnos: cobre a mediana sem competir com o CONHECIMENTO DO FLUXO,
    # que é a parte medida do prompt e a que decide a resposta certa.
    historico = []
    for entrada in (session.get("transcript") or [])[-6:]:
        if not isinstance(entrada, dict):
            continue
        texto = " ".join(str(entrada.get("text") or "").split())[:300]
        if not texto:
            continue
        quem = "você" if str(entrada.get("direction")) == "out" else "seguradora"
        historico.append(f"[{quem}] {texto}")
    contexto_historico = (
        "\n\nO QUE JÁ FOI DITO NESTA CONVERSA (mais antigo primeiro):\n"
        + "\n".join(historico)
    ) if historico else ""
    # Intenção de cada passo do playbook — pra o cérebro reconhecer um menu que mudou
    # de texto/ordem e ainda assim escolher certo (adaptativo, não engessado).
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    intents = []
    for st in (playbook.get("ura_steps") or []):
        nome, nota, resp = st.get("step"), st.get("notes"), st.get("reply")
        try:
            resp_render = str(resp or "").format(**{k: str(v) for k, v in slots.items()})
        except Exception:  # noqa: BLE001 — slot faltante fica com o placeholder mesmo
            resp_render = str(resp or "")
        linha = f"- {nome}: responder '{resp_render}'" + (f" — {nota}" if nota else "")
        intents.append(linha)
    guia_ura = ("\nCONHECIMENTO DO FLUXO (passos típicos e a resposta certa de cada um; "
                "use pra reconhecer um menu mesmo que a seguradora tenha trocado palavras/ordem):\n"
                + "\n".join(intents)) if intents else ""
    # CÉREBRO v2 (SPEC-034): quando existe MAPA DE URA (Cartógrafo/Espelho), o
    # cérebro enxerga o TERRITÓRIO — todas as telas conhecidas e o que cada opção
    # faz — e decide pelo OBJETIVO mesmo se a tela atual mudou de texto.
    # O MAPA DA URA NÃO ENTRA NO PROMPT. DECISÃO DO FOUNDER, 05/08/2026.
    #
    # O parâmetro `ura_map` continua na assinatura porque os dois chamadores
    # (webhook.py e dispatch_watchdog.py) ainda o passam, e porque a decisão
    # pode ser revista quando o mapa souber recortar por caso. Ele é ignorado
    # de propósito, e este comentário é a razão.
    #
    # 📊 O QUE FOI MEDIDO, para um acionamento de GUINCHO na Allianz:
    #
    #   o bloco do mapa teria ......... 5.220 caracteres
    #   o prompt tem hoje ............. 5.098  → dobraria
    #   o menu de serviço AUTO está na  posição 31   ← o corte é de 30.
    #                                                  FICA DE FORA.
    #   telas de guincho .............. posições 56, 61 e 64
    #
    #   das 30 telas que ENTRARIAM:
    #     19 não têm opção nenhuma (avisos, perguntas abertas)
    #      6 são conversa de gente ("Ok", "Um momento", "Com quem falo?")
    #      2 são de ramo errado (Dedetização, Substituição de Telhas)
    #      1 é útil para um guincho
    #   e a "tela inicial" anunciada seria "Termo de Privacidade", sem opções.
    #
    # A CAUSA não é o mapa ser ruim. É ele ser `ramo='todos'` — uma árvore só,
    # com auto, residencial, condomínio e empresarial misturados — e o render
    # não receber o caso. Ordenar por "tela mais vista na seguradora inteira"
    # promove o boilerplate e o menu de residencial, porque é o que mais se
    # repete numa URA. O corte fica mais eficiente em escolher a coisa errada.
    #
    # E o mapa nem entrega o que se queria dele: o render não imprime
    # `leads_to`, então ele NÃO diz "o que vem depois" — que era o propósito.
    # 📊 Só 38% das opções da Allianz e 19% das da Porto têm destino gravado.
    #
    # O USO CERTO DO MAPA É OUTRO, e é offline: ele é a lista de trabalho de
    # quem escreve o corredor. 📊 Cruzando as 38 âncoras de `allianz-auto` com
    # o mapa, 141 telas de menu não têm resposta escrita. Essa lista vira
    # `ura_steps` — permanente, determinístico, e custo zero em atendimento.
    #
    # Ver docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md.
    _ = ura_map  # ignorado de propósito — ver acima
    # A ORIENTAÇÃO DO PLAYBOOK ENTRA NO PROMPT.
    #
    # 📊 `human_phase_guidance` existia em 4 playbooks e **nenhum código a lia** —
    # nem em `app/`, nem nos testes. Este prompt era montado do zero a partir dos
    # `ura_steps`, e toda a orientação escrita à mão ficava de fora.
    #
    # Uma delas, a residencial, carrega uma regra de SEGURANÇA sobre cobertura
    # esgotada. Estava escrita, revisada, e não chegava a lugar nenhum.
    orientacao = str(playbook.get("human_phase_guidance") or "").strip()
    if orientacao:
        guia_ura += ("\n\nORIENTAÇÃO DESTE CORREDOR (escrita por quem observou esta "
                     "seguradora — vale mais que a sua intuição):\n" + orientacao)
    subservice = str(session.get("subservice") or "")
    line_kind = str(playbook.get("line_kind") or "residencial")
    insurer_key = str(playbook.get("insurer_key") or "seguradora")
    linha_txt = "AUTO (guincho, bateria, pneu, chaveiro)" if line_kind == "auto" else "residencial"
    # Freio de TESTE vale para TODAS as linhas (auto E residencial). Em modo LIVE
    # (corredor validado) a instrução vira: confirmar quando o RESUMO confere.
    if _finalize_allowed(session):
        finalize_rule = (
            "3. CONFIRMAÇÃO FINAL: quando a seguradora mostrar o RESUMO e pedir para confirmar, "
            "confira os dados com o caso; se conferem, CONFIRME com a opção afirmativa (ex.: '1' ou 'Sim'). "
            "Se algo divergir do caso, corrija com o dado certo ou responda NAO_SEI.\n"
        )
    else:
        finalize_rule = (
            "3. FREIO DE TESTE: se a seguradora for CONFIRMAR/ABRIR o serviço de fato (agendar, "
            "'posso continuar', 'podemos confirmar', RESUMO final), responda exatamente: NAO_SEI — "
            "este é um TESTE e o pedido NÃO pode ser aberto de verdade.\n"
        )
    system = (
        f"Você conduz, EM NOME DA CORRETORA, um acionamento de assistência {linha_txt} no WhatsApp da "
        f"seguradora ({insurer_key}) que JÁ está em andamento. Pode ser a URA (menu numerado/botões) "
        "ou um atendente humano.\n"
        f"Subserviço deste caso: {subservice or 'não informado'}.\n"
        "COMO DECIDIR (seja inteligente, não robótico):\n"
        "- Se a mensagem for um MENU, escolha a opção coerente com o subserviço/dados do caso e "
        "responda com o número OU o rótulo do botão (ex.: '2' ou 'Guincho'). Use o CONHECIMENTO DO FLUXO "
        "abaixo como guia, mesmo que o texto do menu tenha mudado.\n"
        "- Se pedir um dado do caso (CPF, placa, endereço/local, número, telefone), responda com o valor exato do caso.\n"
        "- Se for um atendente humano perguntando algo, responda em 1-2 frases curtas, PT-BR cordial.\n"
        "REGRAS INEGOCIÁVEIS:\n"
        "1. Use SOMENTE os dados do caso. NUNCA invente números, protocolos, prazos, valores ou dados.\n"
        "2. Não prometa nada em nome da seguradora; não confirme cobertura.\n"
        f"{finalize_rule}"
        "4. Se realmente NÃO der pra deduzir a resposta a partir do caso e do fluxo, responda exatamente: NAO_SEI"
    )
    # A ORDEM DOS BLOCOS NÃO É ARBITRÁRIA.
    #
    # O histórico vem DEPOIS do conhecimento do fluxo e ANTES da mensagem
    # atual, porque é assim que uma conversa se lê: o que já foi dito, e então
    # o que acabaram de dizer. Colocá-lo no topo faria a cauda competir com os
    # dados do caso — que são a única fonte de número autorizada.
    # 🔴 O PONTO EXATO ONDE O MOTOR EMPACOU — 19/08/2026.
    #
    # Quando um passo MAPEADO fica sem o dado que ele exige, o motor agora
    # passa a bola para cá em vez de morrer (ver o bloco em
    # `handle_insurer_message`). Mas passar a bola calado desperdiça a melhor
    # informação que existe: o corredor SABE qual tela é, SABE qual dado
    # faltou, e frequentemente carrega no `notes` a lista de opções da tela.
    #
    # Sem este bloco o modelo veria só a tela crua e teria de redescobrir
    # sozinho o que o produto já sabia. Com ele, a pergunta deixa de ser
    # "o que é isto?" e vira "qual destas opções serve para este caso?" —
    # que é uma pergunta muito mais fácil de acertar.
    empacou = session.get("ultimo_passo_sem_dado") or {}
    ajuda_do_passo = ""
    if empacou.get("step"):
        ajuda_do_passo = (
            "\n\n🔴 ONDE O AUTOMÁTICO EMPACOU (é por isso que você foi chamado):\n"
            f"- a tela foi reconhecida como o passo `{empacou['step']}`\n"
            f"- faltou preencher: {', '.join(empacou.get('faltou') or []) or '?'}\n"
            + (f"- o que se sabe desta tela: {empacou['notes']}\n"
               if empacou.get("notes") else "")
            + "Decida a resposta desta tela usando os dados do caso. Se a tela "
              "for um menu, escolha a opção coerente com o problema relatado. "
              "Se realmente não der para deduzir, responda NAO_SEI."
        )

    user = (
        f"Dados do caso (únicos números permitidos):\n{fatos}{guia_ura}"
        f"{ajuda_do_passo}"
        f"{contexto_pendente}{contexto_historico}\n\n"
        # "TELA", não "mensagem". A seguradora manda o aviso numa bolha, o menu
        # na outra e a pergunta na terceira — e o que chega aqui é a rajada
        # inteira. Chamar isso de "mensagem" convidava o modelo a responder a
        # última linha; é a tela toda que decide, e a resposta é UMA.
        f"Tela da seguradora agora (pode ter chegado em várias mensagens "
        f"seguidas — leia INTEIRA e responda uma vez só):\n{insurer_message}"
        f"\n\nSua resposta:"
    )
    return {"system": system, "user": user}


def _digit_runs(text: str, min_len: int = 5) -> List[str]:
    runs, cur = [], ""
    for ch in str(text or ""):
        if ch.isdigit():
            cur += ch
        else:
            if len(cur) >= min_len:
                runs.append(cur)
            cur = ""
    if len(cur) >= min_len:
        runs.append(cur)
    return runs


# Os motivos de recusa do guarda, separados pelo que eles SIGNIFICAM.
#
# 📊 Achado em 05/08/2026: cinco motivos diferentes alimentavam UM contador, e
# duas recusas chamavam um humano. Uma resposta CERTA com 401 caracteres contava
# igual a "não sei". O agente acertava e era punido por prolixidade.
#
# Erro de redação se corrige pedindo de novo. Recusa de verdade, não.
MOTIVOS_DE_REDACAO = frozenset({"too_long", "empty", "protocol_without_capture",
                                "invented_number"})
MOTIVOS_DE_RECUSA = frozenset({"model_declined"})


def _tela_pede_alguma_coisa(playbook: Dict[str, Any], texto: str) -> bool:
    """A tela da seguradora está pedindo algo, ou só informando?

    É o discriminador que decide se o silêncio deliberado é legítimo. E ele é
    DETERMINÍSTICO de propósito: o modelo propõe o silêncio, o regex decide.
    Sem isso, "não responder" viraria só um jeito mais educado de travar — o
    modelo descobriria que calar não custa nada e calaria em tela que pergunta.
    """
    texto = str(texto or "")
    if not texto.strip():
        return False
    # Decisão irreversível NUNCA é silêncio, mesmo sem ponto de interrogação.
    try:
        if pergunta_de_decisao(playbook or {}, texto):
            return True
    except Exception:  # noqa: BLE001 — sem playbook, cai no marcador genérico
        pass
    return bool(re.search(_MARCA_DE_PERGUNTA, texto, re.IGNORECASE))


def guard_human_phase_reply(reply: str, session: Dict[str, Any],
                            *, insurer_message: str = "") -> Dict[str, Any]:
    """Guard determinístico da resposta da LLM na fase humana (fail-closed).

    TRÊS SAÍDAS, NÃO DUAS — e a terceira fechou quase metade do tráfego.
    ---------------------------------------------------------------------
    📊 Medido em 05/08/2026: **43,2% das mensagens das seguradoras não têm
    marca de pergunta nenhuma** — aviso, saudação, fila, "aguarde", termo de
    privacidade, pesquisa de satisfação. E o passo `noop`, que é o mecanismo de
    silêncio escrito à mão, cobre só 14,8% delas na Allianz.

    Os outros 85% caíam aqui, viravam `NAO_SEI`, e duas telas de aviso seguidas
    chamavam um humano. **Por dois avisos.**

    Agora existe `SEM_RESPOSTA` — mas ele só é aceito se o CÓDIGO provar que
    cabe. `_tela_pede_alguma_coisa` decide; o modelo apenas propõe. Se ele
    disser `SEM_RESPOSTA` numa tela que claramente pede algo, isso vira
    `model_declined` e gasta a chance, como antes.

    `insurer_message` é opcional para não quebrar os chamadores que já existem;
    sem ela, o silêncio é recusado — falha fechada, que é o certo quando não há
    como verificar.
    """
    text = str(reply or "").strip()
    if not text:
        return {"ok": False, "reason": "empty", "reply": ""}
    normalized = text.upper().replace("ÃO", "AO").replace(" ", "_")

    if "SEM_RESPOSTA" in normalized:
        playbook = get_playbook(str(session.get("playbook_ref") or "")) or {}
        tela = str(insurer_message or "")
        if not tela:
            # Sem a tela não há como verificar. Trata como recusa — nunca
            # aceitar silêncio no escuro.
            return {"ok": False, "reason": "model_declined", "reply": text}
        if _tela_pede_alguma_coisa(playbook, tela):
            # O modelo quis calar numa tela que pede algo. Isso é recusa.
            return {"ok": False, "reason": "model_declined", "reply": text}
        return {"ok": False, "reason": "silencio", "silencio": True, "reply": ""}

    if "NAO_SEI" in normalized:
        return {"ok": False, "reason": "model_declined", "reply": text}
    if len(text) > 400:
        return {"ok": False, "reason": "too_long", "reply": text}
    captured = session.get("captured") or {}
    if "protocolo" in text.lower() and not captured.get("protocol"):
        return {"ok": False, "reason": "protocol_without_capture", "reply": text}
    allowed_digits = " ".join(
        str(v) for v in list((session.get("slots") or {}).values()) + list(captured.values())
    )
    for run in _digit_runs(text):
        if run not in allowed_digits:
            return {"ok": False, "reason": "invented_number", "reply": text}
    return {"ok": True, "reason": "", "reply": text}


def reply_human_phase(
    session: Dict[str, Any],
    reply: str,
    *,
    sender: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """Emite a resposta GUARDADA na fase humana e limpa as pendências."""
    session = _emit(session, reply, sender=sender, next_state="human_phase")
    session["pending_insurer_messages"] = []
    # 🔴 O empaque foi resolvido: some com ele. Deixá-lo gravado faria o
    # prompt do PRÓXIMO turno anunciar um travamento que já passou — e o
    # modelo tentaria responder de novo uma tela que já respondeu. É a mesma
    # razão de `pending_insurer_messages` ser zerado na linha acima.
    session.pop("ultimo_passo_sem_dado", None)
    session.pop("falta_para_a_ura", None)
    return session


def build_handoff_dossier(session: Dict[str, Any], reason: str = "") -> str:
    """Dossiê MASTIGADO para o humano assumir sem perguntar nada ao cliente
    (exigência do founder: 'entregar tudo mastigadinho'). Texto de WhatsApp."""
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    slots = session.get("slots") or {}
    captured = session.get("captured") or {}
    insurer = str(playbook.get("insurer_key") or "?").upper()
    linhas = [
        "🚨 *ATENDIMENTO PRECISA DE VOCÊ*",
        f"Seguradora: {insurer} · Serviço: {session.get('subservice') or '?'}",
        f"Motivo: {reason or session.get('reason') or 'handoff'}",
        "",
        "*Dados do caso:*",
    ]
    labels = {
        "titular_cpf": "CPF", "titular_nome": "Titular", "veiculo_placa": "Placa",
        "veiculo_descricao": "Veículo", "local_atual": "Local do veículo",
        "local_destino": "Destino", "problema_descricao": "Problema",
        "telefone_contato": "Telefone", "pessoa_no_local": "No local",
    }
    for key, label in labels.items():
        val = str(slots.get(key) or "").strip()
        if val:
            linhas.append(f"- {label}: {val}")
    if captured:
        linhas.append("")
        linhas.append("*Já capturado da seguradora:*")
        for k, v in captured.items():
            linhas.append(f"- {k}: {v}")

    # FORMULÁRIO NATIVO: o que o humano vê aqui decide se ele leva 10 segundos
    # ou reentrevista o segurado. Quando a resposta está pronta, vai pronta —
    # ele só toca nas opções. Quando falta dado, vai a pergunta da seguradora
    # com as opções DELA, para ele perguntar com as palavras certas.
    flow_resposta = session.get("flow_resposta") or {}
    if flow_resposta:
        linhas.append("")
        if flow_resposta.get("ok") and flow_resposta.get("params"):
            linhas.append("*Formulário do app: RESPOSTA PRONTA — é só marcar assim:*")
            for campo, valor in (flow_resposta["params"] or {}).items():
                escolha = ", ".join(str(v) for v in valor) if isinstance(valor, (list, tuple)) else str(valor)
                linhas.append(f"- {campo}: {escolha}")
            if flow_resposta.get("defaults_used"):
                linhas.append(f"  (saíram de padrão: {', '.join(flow_resposta['defaults_used'])} — confira)")
        else:
            linhas.append("*Formulário do app: FALTA dado para responder.*")
            for det in (flow_resposta.get("missing_detail") or [])[:6]:
                pergunta = str(det.get("pergunta") or det.get("campo") or "")
                opcoes = ", ".join(str(o.get("titulo") or o.get("id")) for o in det.get("opcoes") or [])
                linhas.append(f"- {pergunta}" + (f"\n  opções: {opcoes}" if opcoes else ""))
                if det.get("motivo") == "valor_nao_reconhecido":
                    linhas.append(f"  (o caso diz \"{det.get('valor_recebido')}\" e isso não casa com "
                                  "nenhuma opção da tela)")

    falta = session.get("falta_para_a_ura") or {}
    if falta.get("rotulo"):
        linhas.append("")
        linhas.append(f"*A seguradora pediu e não temos:* {falta['rotulo']}")
    tail = [t for t in (session.get("transcript") or []) if t.get("text")][-6:]
    if tail:
        linhas.append("")
        linhas.append("*Últimas mensagens com a seguradora:*")
        for t in tail:
            who = "corretora" if t.get("direction") == "out" else "seguradora"
            linhas.append(f"[{who}] {str(t.get('text'))[:160]}")
    linhas.append("")
    linhas.append(f"Cliente no WhatsApp: {session.get('client_phone') or '?'} — ele JÁ foi avisado que a equipe vai assumir.")
    linhas.append("Próxima ação sugerida: continuar a conversa com a seguradora do ponto acima (espelho completo na página Conversas).")
    return "\n".join(linhas)


def client_summary_from_capture(session: Dict[str, Any]) -> Optional[str]:
    """Mensagem pronta para o CLIENTE quando protocolo+agendamento capturados."""
    captured = session.get("captured") or {}
    if not captured.get("protocol"):
        return None
    playbook = get_playbook(session.get("playbook_ref") or "") or {}
    lines: List[str] = []
    schedule = captured.get("schedule") or {}
    if schedule and schedule.get("from"):
        lines.append(
            f"Prontinho! ✅ Sua assistência foi agendada para o dia {schedule.get('day')}, entre {schedule.get('from')} e {schedule.get('to')}."
        )
    elif schedule and schedule.get("day"):
        quando = f" às {schedule.get('at')}" if schedule.get("at") else ""
        lines.append(f"Prontinho! ✅ Sua assistência foi agendada para o dia {schedule.get('day')}{quando}.")
    elif captured.get("eta_minutes"):
        lines.append(f"Prontinho! ✅ Sua assistência foi aberta — previsão de chegada em até {captured['eta_minutes']} minutos.")
    else:
        lines.append("Prontinho! ✅ Sua assistência foi aberta na seguradora.")
    lines.append(f"O número do atendimento é {captured['protocol']}.")
    if captured.get("password"):
        lines.append(f"O prestador vai pedir uma senha de acesso: {captured['password']}.")
    # A instrução certa para ESTE serviço.
    #
    # 📊 A fábrica injetava a lista do guincho em todos os subserviços, e a lista
    # de "serviço no local" existia sem consumidor. Quem pedia troca de pneu
    # recebia "aguarde com as chaves e o documento do veículo, e alguém para
    # acompanhar o GUINCHO" — mandando procurar documento que não vai precisar e
    # esperar um caminhão que não vem.
    por_sub = playbook.get("client_instructions_por_subservico") or {}
    sub_do_caso = canonical_subservice(session.get("subservice"))
    instrucoes = por_sub.get(sub_do_caso) or playbook.get("client_instructions") or []
    for instruction in instrucoes[:2]:
        lines.append(instruction)
    lines.append("Qualquer coisa até lá, é só me chamar por aqui 🙂")
    return "\n".join(lines)


def _emit(
    session: Dict[str, Any],
    text: str,
    *,
    sender: Optional[Callable[[str], Any]],
    next_state: str,
    step: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra a mensagem de saída; envia SÓ se o gate estiver aberto."""
    live = bool(session.get("live")) and dispatch_live_enabled()
    entry = {"direction": "out", "text": str(text), "at": _now(), "dry_run": not live}
    if step:
        entry["step"] = step
    session.setdefault("transcript", []).append(entry)
    if live and sender is not None:
        sender(str(text))
    session["state"] = next_state
    return session
