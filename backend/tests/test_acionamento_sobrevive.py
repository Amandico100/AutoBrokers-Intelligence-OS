"""O acionamento sobrevive ao Redis — e o que se perde grita em vez de sumir.

O defeito, medido em 03/08/2026
--------------------------------
    grep -c "work_run" backend/app/services/insurer_dispatch_service.py   ->  0

O acionamento de seguradora é a ÚNICA máquina de estados real do produto:

    preparing -> ready_to_send -> [portao] -> ura -> human_phase -> captured
         |________________________ needs_human <_______|            -> monitoring

E ela morava inteira em `dispatch:active:{company_id}:{digits}` no Redis, com
TTL de 6h (24h em `monitoring`) e, sem Redis, num dicionário de processo.

Um restart do Redis, ou seis horas de silêncio, perdiam um acionamento EM VOO.
Não havia reconciliação nenhuma: **um segurado com o guincho a caminho ficava
órfão e ninguém percebia**. O Vigia (`dispatch_watchdog`) é cego para isso por
construção — ele varre as sessões que ESTÃO no Redis, e o defeito é justamente a
sessão que não está mais lá.

Isso viola CLAUDE.md §6 (Supabase = verdade operacional durável; Redis =
transitório: fila, lock, lease, cache) e a SPEC-055 (Work Run = execução
universal, com etapa, checkpoint e retomada).

A correção, e o que ela deliberadamente NÃO faz
------------------------------------------------
Cada transição de fase virou checkpoint durável num **Work Run**. Nenhuma tabela
nova: `work_runs` para o estado, `work_steps` para o retrato de cada fase,
`work_events` para a linha do tempo.

📊 A tabela nova já foi tentada e morreu — `corridor_runs` tem 50 execuções
abandonadas, todas em `active`, hoje no schema `graveyard`. CLAUDE.md §5 proíbe
repetir isso, e este teste trava a porta: nenhuma tabela de estado paralela.

E a reconciliação **não restaura tudo**. Restaura `monitoring`, onde o motor
nunca fala com a seguradora — só repassa updates ao segurado. Não restaura `ura`
nem `human_phase`: ali a sessão voltaria a RESPONDER à seguradora, e com
`INSURER_DISPATCH_LIVE` aberto isso é mensagem real num atendimento que já andou
sem nós. Ressuscitar uma conversa dessas é o bug "sessão zumbi" de 12/07 com
outro nome. Essas viram `needs_human` com motivo escrito, e uma pessoa assume.

Menos automação. Nunca automação errada.

O estado morto
--------------
📊 `grep -rn "blocked_gate"` devolvia UMA ocorrência no repositório inteiro: a
própria declaração em `DISPATCH_STATES`. Nada atribuía, nada lia. E o nome
mentia: o portão nunca BLOQUEIA uma fase — com ele fechado o acionamento roda
inteiro em DRY-RUN e avança do mesmo jeito. Estado morto num enum que agora vira
linha de banco é pior que estado morto em memória. Removido.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import os
import sys
import types
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


def _corpo_da_funcao(fonte: str, assinatura: str) -> str:
    """O corpo de UMA função — para afirmar o que ela faz sem que outra
    função do mesmo arquivo responda no lugar dela."""
    if assinatura not in fonte:
        return ""
    resto = fonte.split(assinatura, 1)[1]
    for fim in ("\nasync def ", "\ndef ", "\nclass "):
        if fim in resto:
            resto = resto.split(fim, 1)[0]
    return resto


# ---------------------------------------------------------------------------
# Dublês: banco em memória com a mesma gramática do cliente Supabase async.
# ---------------------------------------------------------------------------


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.b, self.t = banco, tabela
        self.op = None
        self.linhas = None
        self.campos = None
        self.filtros = []
        self._limite = None
        self._ordem = None

    def select(self, *a, **k):
        self.op = "select"
        return self

    def insert(self, linhas):
        self.op = "insert"
        self.linhas = linhas if isinstance(linhas, list) else [linhas]
        return self

    def update(self, campos):
        self.op = "update"
        self.campos = campos
        return self

    def eq(self, col, val):
        self.filtros.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self.filtros.append(("in", col, [str(v) for v in vals]))
        return self

    def order(self, col, desc=False):
        self._ordem = (col, desc)
        return self

    def limit(self, n):
        self._limite = int(n)
        return self

    def maybe_single(self):
        return self

    def _casa(self, linha) -> bool:
        for tipo, col, val in self.filtros:
            if tipo == "eq" and str(linha.get(col)) != str(val):
                return False
            if tipo == "in" and str(linha.get(col)) not in val:
                return False
        return True

    async def execute(self):
        tabela = self.b.dados.setdefault(self.t, [])
        self.b.chamadas.append((self.t, self.op))
        if self.op == "insert":
            gravadas = []
            for l in self.linhas:
                linha = dict(l)
                # Como no Postgres real: `id uuid DEFAULT gen_random_uuid()`.
                # Sem isto o dublê mentiria justo onde o código procura a etapa
                # para atualizar — e o teste passaria por engano.
                linha.setdefault("id", f"id-{len(tabela)}-{self.t}")
                tabela.append(linha)
                gravadas.append(dict(linha))
            return _Resposta(gravadas)
        alvo = [l for l in tabela if self._casa(l)]
        if self.op == "update":
            for l in alvo:
                l.update(self.campos)
            return _Resposta([dict(l) for l in alvo])
        if self._ordem:
            col, desc = self._ordem
            alvo = sorted(alvo, key=lambda l: str(l.get(col) or ""), reverse=bool(desc))
        if self._limite is not None:
            alvo = alvo[: self._limite]
        return _Resposta([dict(l) for l in alvo])


class BancoFalso:
    def __init__(self):
        self.dados: dict = {}
        self.chamadas: list = []

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, tabela):
        return self.dados.get(tabela, [])


ATIVIDADES: list = []
BANCO = BancoFalso()


def _carregar():
    """Carrega o roteador REAL com Redis ausente e banco de mentira.

    Redis ausente é de propósito: `_redis()` devolve `None` e o módulo cai no
    `_memory_store`, que é onde este teste simula a sessão sumindo."""

    def _load(dotted, rel):
        caminho = os.path.join(BACKEND, rel)
        spec = importlib.util.spec_from_file_location(dotted, caminho)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = mod
        spec.loader.exec_module(mod)
        return mod

    for nome in ("app", "app.core", "app.services", "app.tasks"):
        m = sys.modules.setdefault(nome, types.ModuleType(nome))
        m.__path__ = []

    redis_mod = types.ModuleType("app.core.redis")

    async def _sem_redis():
        raise RuntimeError("offline")

    redis_mod.get_async_redis_client = _sem_redis
    sys.modules["app.core.redis"] = redis_mod

    db_mod = types.ModuleType("app.core.database")

    async def _cliente():
        return BANCO

    db_mod.create_async_supabase_client = _cliente
    sys.modules["app.core.database"] = db_mod

    espelho = types.ModuleType("app.services.dispatch_mirror")

    async def _mirror(*a, **k):
        return None

    espelho.mirror_session = _mirror
    sys.modules["app.services.dispatch_mirror"] = espelho

    atividades = types.ModuleType("app.services.activity_log")

    async def _log_activity(company_id, categoria, titulo, detalhe=""):
        ATIVIDADES.append((company_id, categoria, titulo))

    atividades.log_activity = _log_activity
    sys.modules["app.services.activity_log"] = atividades

    _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
    disp = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
    rot = _load("app.services.dispatch_router", "app/services/dispatch_router.py")
    # A varredura de boot é disparada por cache-miss. Aqui ela é chamada à mão,
    # para que o teste prove o resultado e não uma corrida com o event loop.
    rot._reconciliacao_agendada = True
    return disp, rot


DISPATCH, ROTEADOR = _carregar()

EMPRESA = "co-espelho"
SEGURADORA = "551140901444"


def _zerar():
    BANCO.dados.clear()
    BANCO.chamadas.clear()
    ATIVIDADES.clear()
    ROTEADOR._memory_store.clear()


def _sessao(fase: str, **extra) -> dict:
    base = {
        "case_id": "caso-guincho-77",
        "company_id": EMPRESA,
        "playbook_ref": "porto-auto-whatsapp@v1",
        "subservice": "guincho",
        "state": fase,
        "slots": {"titular_cpf": "11122233344", "veiculo_placa": "ABC1D23"},
        "captured": {"protocol": "PT-99887766", "eta_minutes": "40"},
        "transcript": [{"direction": "out", "text": "Ola", "at": "2026-08-03T10:00:00+00:00"}],
        "client_phone": "5548999990000",
        "insurer_phone": SEGURADORA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "live": True,
    }
    base.update(extra)
    return base


def _run_unico() -> dict:
    linhas = BANCO.linhas("work_runs")
    return linhas[0] if linhas else {}


# ---------------------------------------------------------------------------


def teste_o_estado_morto_saiu():
    print("\n[E1] `blocked_gate` nao existe mais em lugar nenhum")
    fonte = _ler("backend", "app", "services", "insurer_dispatch_service.py")
    estados = fonte.split("DISPATCH_STATES = (", 1)[1].split(")", 1)[0]

    checar('"blocked_gate"' not in estados,
           "o estado morto saiu de DISPATCH_STATES",
           "estava declarado e nenhuma transicao o atribuia")
    checar(len(_sem_comentario(fonte).split('"blocked_gate"')) == 1,
           "e nao voltou por nenhuma outra porta do modulo")
    checar("blocked_gate" in fonte,
           "mas a REMOCAO esta explicada no arquivo",
           "apagar sem dizer por que faz o proximo leitor recriar o estado")

    for fase in ("preparing", "ready_to_send", "ura", "human_phase",
                 "captured", "monitoring", "test_aborted", "needs_human"):
        checar(fase in DISPATCH.DISPATCH_STATES, f"a fase real '{fase}' continua declarada")


def teste_toda_fase_tem_status_duravel():
    print("\n[E2] Cada fase sabe virar estado durável do Work Run")
    for fase in DISPATCH.DISPATCH_STATES:
        # EXPLÍCITO, não pelo fallback: uma fase nova que ninguem mapeou cairia
        # em 'running' calada, e o Control Plane mostraria "rodando" para um
        # trabalho que ninguem esta tocando.
        status = DISPATCH.STATUS_WORK_RUN_POR_FASE.get(fase)
        checar(status in ("draft", "queued", "planning", "running", "waiting_approval",
                          "waiting_input", "paused", "retry_scheduled", "cancelling",
                          "cancelled", "failed", "completed", "expired"),
               f"'{fase}' mapeia para um status do enum work_run_status ({status})",
               "inventar palavra nova aqui quebraria o Control Plane que le a tabela")
        checar(fase in DISPATCH.FASES_EM_VOO or fase in DISPATCH.FASES_ENCERRADAS,
               f"'{fase}' esta classificada como em voo OU encerrada",
               "a reconciliacao precisa saber o que fazer com toda fase declarada")
    checar(DISPATCH.status_duravel_da_fase("test_aborted") == "completed",
           "o teste que rodou ponta a ponta e cancelou fecha o run",
           "run que ninguem fecha vira o entulho do corridor_runs")
    checar(DISPATCH.status_duravel_da_fase("monitoring") == "waiting_input",
           "monitoring fica esperando o mundo de fora, nao 'rodando'")
    checar(set(DISPATCH.FASES_EM_VOO) & set(DISPATCH.FASES_ENCERRADAS) == set(),
           "nenhuma fase e ao mesmo tempo 'em voo' e 'encerrada'")


def teste_o_redis_deixou_de_ser_a_unica_verdade():
    print("\n[E3] O checkpoint durável vem ANTES do Redis")
    fonte = _ler("backend", "app", "services", "dispatch_router.py")
    corpo = _corpo_da_funcao(fonte, "async def save_active_dispatch(")

    checar("registrar_checkpoint(" in corpo, "save_active_dispatch grava o checkpoint")
    pos_ckpt = corpo.find("registrar_checkpoint(")
    pos_redis = corpo.find("_gravar_no_redis(")
    checar(pos_ckpt != -1 and pos_redis != -1 and pos_ckpt < pos_redis,
           "o durável e escrito ANTES do cache",
           "cache mais novo que a verdade e exatamente o defeito desta SPEC")

    corpo_clear = _corpo_da_funcao(fonte, "async def clear_active_dispatch(")
    checar("_encerrar_work_run(" in corpo_clear,
           "encerrar a sessao tambem encerra o Work Run",
           "senao toda sessao encerrada de proposito vira um orfao futuro")


def teste_nenhum_motor_paralelo():
    print("\n[E4] Nenhuma tabela de estado nova, nenhuma fila nova")
    sql = _ler("backend", "supabase", "migrations",
               "20260803_06_spec063_acionamento_duravel.sql")
    checar("CREATE TABLE" not in sql.upper(),
           "a migration nao cria tabela nenhuma",
           "o corridor_runs ja provou onde isso termina")
    for marca in ("APPLY", "VERIFY", "ROLLBACK"):
        checar(f"-- {marca}" in sql, f"a migration traz {marca} escrito antes de rodar")
    checar("IF NOT EXISTS" in sql, "o DDL e idempotente")

    fonte = _sem_comentario(_ler("backend", "app", "services", "dispatch_router.py"))
    checar("work_queue_outbox" not in fonte,
           "o acionamento nao entra na fila do Smith Worker",
           "entraria so para o worker marca-lo failed com workflow_desconhecido")
    for tabela in ("work_runs", "work_steps", "work_events"):
        checar(f'table("{tabela}")' in fonte, f"escreve em {tabela} (SPEC-055)")


def teste_o_portao_e_o_freio_nao_afrouxaram():
    print("\n[E5] SEGURANCA: portao de envio e freio de finalizacao intactos")
    fonte = _ler("backend", "app", "services", "insurer_dispatch_service.py")

    # ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — aqui se afirmava que o
    # portao nascia FECHADO e o freio nascia em 'test'. Era verdade ate a
    # decisao do Founder: a unica trava passa a ser `agents.is_active` do agente
    # de atendimento. As duas travas de env existiam porque ele testava no
    # proprio celular, e esse motivo acabou quando o interruptor virou produto.
    #
    # A licao migra: o que este caso protege e que o portao continua EXISTINDO e
    # continua FECHAVEL. Ele passa a exercita-lo em vez de ler a receita dele.
    _antes = {k: os.environ.get(k) for k in ("INSURER_DISPATCH_LIVE",
                                             "DISPATCH_FINALIZE_MODE",
                                             DISPATCH.FREIO_DE_EMERGENCIA)}
    try:
        for k in _antes:
            os.environ.pop(k, None)
        # CONTROLE: sem nada armado os dois abrem. Sem esta linha, as duas
        # asserções seguintes passariam mesmo num portao que so sabe dizer nao.
        checar(DISPATCH.dispatch_live_enabled() is True
               and DISPATCH.finalize_live_for("hdi-auto-whatsapp@v1") is True,
               "CONTROLE: sem nada armado, portao e freio nascem ABERTOS")
        os.environ[DISPATCH.FREIO_DE_EMERGENCIA] = "true"
        checar(DISPATCH.dispatch_live_enabled() is False,
               "o freio de emergencia continua FECHANDO o portao de envio")
        checar(DISPATCH.finalize_live_for("hdi-auto-whatsapp@v1") is False,
               "e continua segurando a finalizacao junto")
    finally:
        for k, v in _antes.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    checar("if finalize and not _finalize_allowed(session):" in fonte,
           "o bloco que CANCELA antes de abrir o servico segue de pe")

    emit = _corpo_da_funcao(fonte, "def _emit(")
    checar("live = bool(session.get(\"live\")) and dispatch_live_enabled()" in emit,
           "o envio real exige a sessao E a variavel de ambiente",
           "as duas condicoes, nunca uma so")
    checar("if live and sender is not None:" in emit,
           "e nada sai sem o portao aberto")

    # A reconciliação não pode ter virado um caminho de envio.
    rot = _ler("backend", "app", "services", "dispatch_router.py")
    for nome in ("async def reconciliar_acionamentos_orfaos(", "async def _reconciliar_um("):
        corpo = _corpo_da_funcao(rot, nome)
        for proibido in ("sender=", "send_to_insurer", "start_dispatch(",
                         "handle_insurer_message(", "reply_human_phase("):
            checar(proibido not in corpo,
                   f"{nome.split('(')[0].split()[-1]} nao chama '{proibido}'",
                   "restaurar NUNCA pode virar falar com a seguradora")


def teste_o_retrato_duravel_nao_carrega_o_mundo():
    print("\n[E6] O retrato durável leva o necessario — e nada com cara de segredo")
    sessao = _sessao("ura")
    sessao["transcript"] = [{"direction": "in", "text": f"m{i}"} for i in range(30)]
    sessao["api_key_da_seguradora"] = "nao-pode-ir"
    sessao["access_token"] = "nao-pode-ir"

    retrato = DISPATCH.snapshot_duravel(sessao)
    checar(len(retrato["transcript"]) == 8,
           "so a cauda do transcript vai para o banco",
           f"foram {len(retrato['transcript'])} de 30")
    checar(retrato["transcript_total"] == 30,
           "mas o tamanho real fica registrado",
           "senao a cauda pareceria a conversa inteira")
    checar("api_key_da_seguradora" not in retrato and "access_token" not in retrato,
           "nada com nome de credencial atravessa (CLAUDE.md 7)")
    checar(retrato["slots"]["veiculo_placa"] == "ABC1D23" and retrato["captured"]["protocol"],
           "o que o motor precisa para continuar continua la")

    volta = DISPATCH.sessao_restaurada(retrato, motivo="teste")
    checar(volta["mirror_idx"] == len(volta["transcript"]),
           "na volta, o contador do Espelho e recalibrado",
           "sem isso o Espelho pararia de gravar em silencio")


def teste_a_fase_vira_checkpoint_duravel():
    print("\n[F1] Cada fase vira etapa gravada no Work Run")
    _zerar()
    sessao = _sessao("ura")
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))

    run = _run_unico()
    checar(bool(run), "o acionamento criou UM Work Run")
    checar(run.get("workflow_key") == "acionamento.seguradora",
           "com a chave de workflow do acionamento")
    checar(run.get("runtime_kind") == "acionamento",
           "marcado como movido por fora do Smith Worker",
           "quem o move e o inbound do WhatsApp, mensagem por mensagem")
    checar(run.get("status") == "running" and run.get("current_step_key") == "ura",
           "com o estado e a fase corrente gravados",
           f"status={run.get('status')} fase={run.get('current_step_key')}")
    checar(run.get("risk_level") == "high",
           "risco alto: do outro lado esta a seguradora de verdade")
    checar(run.get("lease_owner") is None,
           "sem lease — o varredor de orfaos da SPEC-055 nao o alcanca")
    checar(sessao.get("work_run_id") == run.get("id"),
           "e a sessao passa a carregar o id do run")

    etapas = BANCO.linhas("work_steps")
    checar(len(etapas) == 1 and etapas[0]["step_key"] == "ura",
           "a fase virou uma etapa em work_steps")
    checar(etapas[0]["output_summary"].get("state") == "ura",
           "cujo retrato guarda o estado da sessao")

    # Segunda mensagem na MESMA fase: atualiza a etapa, nao cria outra.
    sessao["transcript"].append({"direction": "in", "text": "menu"})
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
    checar(len(BANCO.linhas("work_runs")) == 1, "nao duplica o run")
    checar(len(BANCO.linhas("work_steps")) == 1,
           "nem a etapa da fase (uma etapa por fase, atualizada)")
    checar(len(BANCO.linhas("work_steps")[0]["output_summary"]["transcript"]) == 2,
           "e o retrato acompanha a conversa")

    eventos = [e for e in BANCO.linhas("work_events")]
    checar(any(e["event_type"] == "run.created" for e in eventos),
           "a linha do tempo registra a abertura")
    checar(len([e for e in eventos if e["event_type"] == "step.completed"]) == 1,
           "e a mudanca de fase entra UMA vez, nao a cada mensagem")


def teste_a_sessao_some_do_redis_e_nao_fica_orfa():
    print("\n[F2] Sessao some do Redis: o monitoramento VOLTA")
    _zerar()
    sessao = _sessao("monitoring", followup_at="2026-08-03T12:00:00+00:00")
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
    chave = ROTEADOR._key(EMPRESA, SEGURADORA)
    checar(chave in ROTEADOR._memory_store, "a sessao esta no cache antes do acidente")

    # O ACIDENTE: restart do Redis / TTL vencido. O banco continua sabendo.
    ROTEADOR._memory_store.clear()
    checar(asyncio.run(ROTEADOR.load_active_dispatch(EMPRESA, SEGURADORA)) is None,
           "e o cache nao tem mais nada — era aqui que o segurado virava orfao")

    resumo = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(resumo["vistos"] == 1, "a reconciliacao ve o acionamento no banco", str(resumo))
    checar(resumo["restaurados"] == 1, "e o restaura", str(resumo))

    voltou = asyncio.run(ROTEADOR.load_active_dispatch(EMPRESA, SEGURADORA))
    checar(voltou is not None, "a sessao esta de volta no cache")
    checar(voltou and voltou.get("state") == "monitoring", "na mesma fase")
    checar(voltou and voltou.get("client_phone") == "5548999990000",
           "com o telefone do segurado — que e o que faz o acompanhamento continuar")
    checar(voltou and voltou.get("captured", {}).get("protocol") == "PT-99887766",
           "e com o protocolo capturado")
    checar(voltou and voltou.get("restaurado_motivo") == "reconciliacao_boot",
           "e dizendo que veio de uma restauracao, nao do fluxo normal")
    checar(voltou and voltou.get("mirror_idx") == len(voltou.get("transcript") or []),
           "com o Espelho recalibrado para continuar gravando")
    checar(any(e["event_type"] == "run.recovered" for e in BANCO.linhas("work_events")),
           "e a recuperacao ficou escrita na linha do tempo")

    # E de novo: idempotente, agora a sessao esta viva e ninguem mexe nela.
    r2 = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(r2["vivos"] == 1 and r2["restaurados"] == 0,
           "rodar de novo nao restaura o que ja esta vivo", str(r2))


def teste_a_fase_que_fala_com_a_seguradora_nao_ressuscita():
    print("\n[F3] Fase que voltaria a FALAR com a seguradora vira handoff, nao zumbi")
    _zerar()
    sessao = _sessao("ura")
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
    ROTEADOR._memory_store.clear()

    resumo = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(resumo["orfaos"] == 1, "o acionamento perdido e reconhecido", str(resumo))
    checar(resumo["restaurados"] == 0,
           "e NAO e devolvido ao cache",
           "em 'ura' a sessao responderia a seguradora; com o portao aberto, "
           "isso e mensagem real num atendimento que ja andou sem nos")
    checar(ROTEADOR._key(EMPRESA, SEGURADORA) not in ROTEADOR._memory_store,
           "a chave do Redis continua vazia — nada de sessao zumbi")

    run = _run_unico()
    checar(run.get("status") == "waiting_input",
           "o trabalho passa a esperar uma PESSOA", str(run.get("status")))
    checar(run.get("error_code") == "acionamento_orfao",
           "com o motivo em codigo, para a tela poder filtrar")
    checar("precisa de alguém" in str(run.get("error_message") or "").lower(),
           "e com o motivo em portugues, para a pessoa poder ler",
           str(run.get("error_message")))

    gritos = [e for e in BANCO.linhas("work_events") if e.get("severity") == "error"]
    checar(len(gritos) == 1, "a linha do tempo registra um evento de ERRO", str(len(gritos)))
    checar(ATIVIDADES and ATIVIDADES[-1][1] == "acionamentos",
           "e a corretora ve no feed de Atividades que alguem precisa assumir",
           "orfao silencioso e o defeito; orfao que grita, nao")

    # Idempotencia: quem ja gritou nao grita de novo a cada boot.
    r2 = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(r2["ja_sinalizados"] == 1 and r2["orfaos"] == 0,
           "o segundo boot reconhece que ja sinalizou", str(r2))
    checar(len([e for e in BANCO.linhas("work_events") if e.get("severity") == "error"]) == 1,
           "sem gritar duas vezes",
           "alarme repetido e como se ensina uma equipe a ignorar alarme")


def teste_o_handoff_ja_feito_nao_vira_alarme_falso():
    print("\n[F4] needs_human que sai do cache fecha — nao vira alarme falso")
    _zerar()
    sessao = _sessao("needs_human", reason="handoff_trigger:sinistro")
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
    run = _run_unico()
    checar(run.get("status") == "waiting_input",
           "no handoff, o run espera a pessoa que recebeu o dossie")

    ROTEADOR._memory_store.clear()
    resumo = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(resumo["encerrados"] == 1 and resumo["orfaos"] == 0,
           "sumir do cache aqui e o fim natural da parte automatica", str(resumo))
    checar(_run_unico().get("status") == "completed", "o run fecha")
    checar(not [e for e in BANCO.linhas("work_events") if e.get("severity") == "error"],
           "e ninguem e acordado por um handoff que ja aconteceu")


def teste_monitoramento_vencido_encerra_em_vez_de_apodrecer():
    print("\n[F5] Monitoramento fora da janela encerra — nada apodrece em 'em voo'")
    _zerar()
    sessao = _sessao("monitoring")
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
    ROTEADOR._memory_store.clear()
    # Envelhece o checkpoint para alem das 24h da janela de monitoramento.
    velho = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    for etapa in BANCO.linhas("work_steps"):
        etapa["finished_at"] = velho

    resumo = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(resumo["encerrados"] == 1 and resumo["restaurados"] == 0,
           "passou da janela: encerra em vez de restaurar", str(resumo))
    checar(_run_unico().get("status") == "completed",
           "o run vira terminal",
           "📊 corridor_runs tem 50 execucoes eternamente 'active' por falta disso")
    r2 = asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())
    checar(r2["vistos"] == 0, "e some da varredura seguinte", str(r2))


def teste_encerrar_a_sessao_encerra_o_trabalho():
    print("\n[F6] Sessao encerrada de proposito nao deixa run em voo")
    _zerar()
    sessao = _sessao("monitoring")
    asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
    asyncio.run(ROTEADOR.clear_active_dispatch(EMPRESA, SEGURADORA))

    run = _run_unico()
    checar(run.get("status") == "completed", "o run fecha junto com a sessao",
           str(run.get("status")))
    checar(bool(run.get("finished_at")), "com hora de termino")
    checar(asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())["vistos"] == 0,
           "e a reconciliacao nao o encontra mais em voo")


def teste_o_banco_fora_do_ar_nao_derruba_o_acionamento():
    print("\n[F7] Banco indisponivel nao derruba o segurado")
    _zerar()
    original = ROTEADOR._db

    async def _sem_banco():
        return None

    ROTEADOR._db = _sem_banco
    try:
        sessao = _sessao("ura")
        asyncio.run(ROTEADOR.save_active_dispatch(EMPRESA, SEGURADORA, sessao))
        checar(ROTEADOR._key(EMPRESA, SEGURADORA) in ROTEADOR._memory_store,
               "sem banco, o acionamento continua pelo cache",
               "travar o motor por causa do espelho seria trocar um defeito por outro pior")
        checar(asyncio.run(ROTEADOR.reconciliar_acionamentos_orfaos())["vistos"] == 0,
               "e a reconciliacao apenas nao acha nada")
    finally:
        ROTEADOR._db = original


def main() -> int:
    print("=" * 68)
    print("O ACIONAMENTO SOBREVIVE AO REDIS — E O ORFAO GRITA")
    print("=" * 68)
    for t in (teste_o_estado_morto_saiu,
              teste_toda_fase_tem_status_duravel,
              teste_o_redis_deixou_de_ser_a_unica_verdade,
              teste_nenhum_motor_paralelo,
              teste_o_portao_e_o_freio_nao_afrouxaram,
              teste_o_retrato_duravel_nao_carrega_o_mundo,
              teste_a_fase_vira_checkpoint_duravel,
              teste_a_sessao_some_do_redis_e_nao_fica_orfa,
              teste_a_fase_que_fala_com_a_seguradora_nao_ressuscita,
              teste_o_handoff_ja_feito_nao_vira_alarme_falso,
              teste_monitoramento_vencido_encerra_em_vez_de_apodrecer,
              teste_encerrar_a_sessao_encerra_o_trabalho,
              teste_o_banco_fora_do_ar_nao_derruba_o_acionamento):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O ESTADO E DURAVEL, A VOLTA E SEGURA, E NADA SOME CALADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
