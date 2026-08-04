"""A varredura do acionamento órfão não depende mais de tráfego.

P-34. A varredura estava certa. O GATILHO dela é que era frágil.
----------------------------------------------------------------
Um acionamento em voo vive em duas verdades: o Work Run no Postgres (durável) e
a sessão em `dispatch:active:{empresa}:{telefone}` no Redis (transitória, TTL de
6h — 24h em `monitoring`). Quando a segunda some e a primeira fica, existe um
**órfão**: um segurado com o guincho a caminho e ninguém do nosso lado sabendo.

A SPEC-063 Bloco E construiu `reconciliar_acionamentos_orfaos()`, que compara as
duas e grita. Ela é boa, é idempotente, e não restaura o que não deve. O que
ficou pendente foi como ela é DISPARADA::

    async def load_active_dispatch(company_id, insurer_phone):
        sessao = await _ler_do_redis(company_id, insurer_phone)
        if sessao is None:
            _agendar_reconciliacao_uma_vez()      # <- o gatilho inteiro
        return sessao

Duas falhas, e a segunda é a que dói:

**1. Uma vez por processo.** `_agendar_reconciliacao_uma_vez` trava um global na
primeira execução. Um Redis esvaziado às 3h da manhã só seria notado no próximo
deploy.

**2. Depende de TRÁFEGO.** O gatilho é um cache-miss, e cache-miss só acontece
se alguém chamar `load_active_dispatch` — ou seja, se chegar mensagem. Se o
cache cair e ninguém escrever, o miss nunca acontece, a varredura nunca roda, e
o órfão fica **em silêncio**. É exatamente o cenário que a varredura existe para
cobrir, e era o único que o gatilho não alcançava. O sintoma visível é nenhum:
uma conversa que não anda.

O conserto: uma linha no laço de manutenção
--------------------------------------------
O job entra em `buffer_processor.start_buffer_scheduler()`, ao lado do Vigia e
do heartbeat de canal. O atraso máximo para perceber um órfão deixa de ser "até
alguém mandar uma mensagem" e passa a ser um número — 5 minutos por padrão,
folgado contra uma janela de 6h/24h.

E `next_run_time` no boot + 60s, porque logo depois de um deploy o cache está
vazio e a verdade durável não: é o momento de maior chance de órfão do dia.

Como este arquivo verifica
--------------------------
Por AST, não por `in`. O que interessa é a CHAMADA registrada — id do job,
função referenciada, intervalo, `max_instances`, `next_run_time`. Um comentário
que diga "agenda a reconciliação" não pode passar no lugar da linha que agenda.
E o caso [5] roda a mesma verificação sobre o código de ANTES, para provar que
ela distingue os dois (CLAUDE.md §9.3).
"""

from __future__ import annotations

import ast
import asyncio
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

LACO = ("app", "tasks", "buffer_processor.py")
ROTEADOR = ("app", "services", "dispatch_router.py")

ID_DO_JOB = "dispatch_reconcile_check"
FUNCAO_DA_VARREDURA = "reconciliar_acionamentos_orfaos"


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Leitura estrutural das chamadas `scheduler.add_job(...)`
# --------------------------------------------------------------------------- #

def _jobs_registrados(fonte: str) -> dict:
    """{id_do_job: {alvo, kwargs}} lendo as chamadas add_job de verdade.

    Substring diria "sim" para um comentário. A árvore só diz "sim" para a
    chamada que o Python vai executar.
    """
    achados: dict = {}
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        f = no.func
        if not (isinstance(f, ast.Attribute) and f.attr == "add_job"):
            continue
        kwargs = {k.arg: k.value for k in no.keywords if k.arg}
        no_id = kwargs.get("id")
        if not isinstance(no_id, ast.Constant) or not isinstance(no_id.value, str):
            continue
        alvo = no.args[0] if no.args else None
        achados[no_id.value] = {
            "alvo": alvo.id if isinstance(alvo, ast.Name) else ast.dump(alvo) if alvo else "",
            "kwargs": kwargs,
            "gatilho": (no.args[1].value if len(no.args) > 1
                        and isinstance(no.args[1], ast.Constant) else None),
        }
    return achados


def _intervalo_em_minutos(kwargs: dict) -> float | None:
    """Minutos entre execuções, seja o job declarado em `minutes` ou `seconds`."""
    for chave, fator in (("minutes", 1.0), ("seconds", 1 / 60.0), ("hours", 60.0)):
        no = kwargs.get(chave)
        if no is None:
            continue
        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
            return float(no.value) * fator
        # `_env_int("NOME", padrao)` — o padrão é o segundo argumento.
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "_env_int":
            if len(no.args) > 1 and isinstance(no.args[1], ast.Constant):
                return float(no.args[1].value) * fator
    return None


def _nome_da_env(kwargs: dict) -> str:
    for chave in ("minutes", "seconds", "hours"):
        no = kwargs.get(chave)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "_env_int":
            if no.args and isinstance(no.args[0], ast.Constant):
                return str(no.args[0].value)
    return ""


def _fonte_da_funcao(fonte: str, nome: str) -> str:
    arvore = ast.parse(fonte)
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return ast.get_source_segment(fonte, no) or ""
    return ""


def _chamadores_de(fonte: str, alvo: str) -> set:
    """Quais funções chamam `alvo`. É como se mede de que o gatilho depende."""
    chamadores = set()
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for interno in ast.walk(no):
            if isinstance(interno, ast.Call) and isinstance(interno.func, ast.Name) \
                    and interno.func.id == alvo:
                chamadores.add(no.name)
    return chamadores


# --------------------------------------------------------------------------- #
# Casos
# --------------------------------------------------------------------------- #

def teste_o_gatilho_antigo_dispara_uma_vez_so():
    print("\n[1] O gatilho de antes trava depois da primeira execucao")
    fonte = _ler(*ROTEADOR)
    codigo = _fonte_da_funcao(fonte, "_agendar_reconciliacao_uma_vez")
    checar(bool(codigo), "a funcao de boot continua existindo",
           "ela nao foi removida: cobre o cache-miss, que continua sendo sinal")

    # Executa a função DE VERDADE, com um dublê no lugar da varredura, para
    # medir quantas vezes ela dispara. Afirmar "uma vez" lendo o `global` seria
    # ler a intenção; contar é medir.
    disparos = []

    async def _falsa_varredura():
        disparos.append(1)

    ns: dict = {"_reconciliacao_agendada": False,
                FUNCAO_DA_VARREDURA: _falsa_varredura}
    exec(compile(codigo, "<agendador>", "exec"), ns)  # noqa: S102 — é o código do produto

    async def _tres_vezes():
        for _ in range(3):
            ns["_agendar_reconciliacao_uma_vez"]()
        await asyncio.sleep(0)  # deixa as tasks agendadas rodarem

    asyncio.run(_tres_vezes())
    checar(len(disparos) == 1,
           "tres cache-miss produzem UMA varredura, nao tres",
           f"disparos={len(disparos)} — depois dela, o processo fica cego a "
           "um Redis esvaziado as 3h da manha")


def teste_o_gatilho_antigo_depende_de_trafego():
    print("\n[2] E ele so acontece quando CHEGA MENSAGEM")
    fonte = _ler(*ROTEADOR)
    chamadores = _chamadores_de(fonte, "_agendar_reconciliacao_uma_vez")
    checar(chamadores == {"load_active_dispatch"},
           "o unico chamador e a leitura da sessao — ou seja, o inbound",
           f"chamadores={sorted(chamadores)}. Sem mensagem nova, nenhum "
           "cache-miss acontece e a varredura NUNCA roda — que e exatamente "
           "o caso que ela existe para cobrir")


def teste_a_varredura_entrou_no_laco_de_manutencao():
    print("\n[3] A varredura passa a rodar sozinha, no laco")
    jobs = _jobs_registrados(_ler(*LACO))
    checar(ID_DO_JOB in jobs,
           f"existe um job '{ID_DO_JOB}' no agendador",
           f"jobs registrados: {sorted(jobs)}")
    if ID_DO_JOB not in jobs:
        return

    job = jobs[ID_DO_JOB]
    checar(job["alvo"] == FUNCAO_DA_VARREDURA,
           f"e ele chama {FUNCAO_DA_VARREDURA}",
           f"alvo={job['alvo']!r} — agendar outra coisa com o nome certo "
           "seria pior que nao agendar nada")
    checar(job["gatilho"] == "interval",
           "e é periodico, nao um disparo unico", str(job["gatilho"]))

    max_inst = job["kwargs"].get("max_instances")
    checar(isinstance(max_inst, ast.Constant) and max_inst.value == 1,
           "max_instances=1 — duas varreduras simultaneas nao se atropelam",
           "a varredura escreve no Work Run do orfao; duas ao mesmo tempo "
           "sinalizariam o mesmo caso duas vezes")

    checar("next_run_time" in job["kwargs"],
           "e a primeira passada e logo apos o BOOT",
           "depois de um deploy o cache esta vazio e a verdade duravel nao: "
           "e o momento de maior chance de orfao do dia inteiro")

    # O import tem de estar lá também — job que referencia nome inexistente
    # explode no boot do worker, e o laço inteiro não sobe.
    checar(f"import {FUNCAO_DA_VARREDURA}" in _ler(*LACO),
           "a funcao e importada no laco",
           "nome nao resolvido derrubaria o start_buffer_scheduler inteiro")


def teste_o_intervalo_e_sensato():
    print("\n[4] O intervalo tem numero, e o numero cabe na janela real")
    jobs = _jobs_registrados(_ler(*LACO))
    if ID_DO_JOB not in jobs:
        checar(False, "sem job, nao ha intervalo a conferir")
        return
    minutos = _intervalo_em_minutos(jobs[ID_DO_JOB]["kwargs"])
    checar(minutos is not None, "o job declara um intervalo legivel", str(minutos))
    if minutos is None:
        return

    # A janela real: a sessao vive 6h no Redis (24h em `monitoring`). Detectar
    # em 5 min e folgado; detectar em 6h nao serviria para nada.
    roteador = _ler(*ROTEADOR)
    checar("_TTL_SECONDS = 6 * 3600" in roteador,
           "a janela de referencia continua sendo 6h",
           "se este numero mudar, o intervalo abaixo precisa ser revisto")
    checar(0 < minutos <= 15,
           f"o intervalo ({minutos:g} min) e uma fracao pequena da janela de 6h",
           "acima disso o orfao espera demais; abaixo de 1 min a varredura "
           "vira carga constante em cima de work_runs sem ganho")

    env = _nome_da_env(jobs[ID_DO_JOB]["kwargs"])
    checar(env == "DISPATCH_RECONCILE_INTERVAL_MINUTES",
           "e o intervalo e ajustavel por ambiente", f"env={env!r}")
    checar(env in _ler(".env.example"),
           "a variavel esta documentada no .env.example",
           "variavel que so existe no codigo e variavel que ninguem sabe que tem")


def teste_o_guarda_tem_como_falhar():
    print("\n[5] CONTROLE — a mesma leitura, no laco de ANTES")
    # O laço como era: todos os jobs de sempre, e nenhum de reconciliação.
    antes = """
def start_buffer_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_buffers, "interval", seconds=1,
                          id="whatsapp_buffer_check", max_instances=10)
        scheduler.add_job(check_dispatch_watchdog, "interval", seconds=20,
                          id="dispatch_watchdog_check", max_instances=1)
        scheduler.add_job(verificar_canais, "interval",
                          minutes=_env_int("CHANNEL_HEARTBEAT_INTERVAL_MINUTES", 5),
                          id="channel_heartbeat_check", max_instances=1)
        scheduler.start()
"""
    jobs_antes = _jobs_registrados(antes)
    checar(len(jobs_antes) == 3,
           "o controle e mesmo um laco com jobs de verdade",
           f"lidos: {sorted(jobs_antes)} — se a leitura nao achasse nada, "
           "o caso [3] passaria por engano em qualquer arquivo")
    checar(ID_DO_JOB not in jobs_antes,
           "e o laco de ANTES REPROVA na verificacao do caso [3]",
           "se este caso ficar vermelho, a leitura nao distingue o conserto "
           "e nao guarda nada (CLAUDE.md §9.3)")

    # E o inverso: a leitura APROVA o laço de hoje.
    checar(ID_DO_JOB in _jobs_registrados(_ler(*LACO)),
           "e APROVA o laco de hoje — os dois lados conseguem ser diferentes")

    # A leitura tambem tem de recusar um comentario que MENCIONE o job.
    so_comentario = '''
def start_buffer_scheduler():
    # TODO: agendar reconciliar_acionamentos_orfaos com id="dispatch_reconcile_check"
    scheduler.start()
'''
    checar(ID_DO_JOB not in _jobs_registrados(so_comentario),
           "e um comentario que cita o job NAO conta como job registrado",
           "era o risco de verificar com `in` em vez de ler a arvore")


def teste_a_varredura_continua_barata_e_idempotente():
    print("\n[6] Rodar de 5 em 5 minutos nao pode custar caro")
    fonte = _ler(*ROTEADOR)
    corpo = _fonte_da_funcao(fonte, FUNCAO_DA_VARREDURA)
    checar(bool(corpo), "a varredura existe")
    checar("limite: int = 50" in corpo,
           "cada passada olha no maximo 50 runs em voo",
           "sem teto, uma varredura periodica vira varredura de tabela")
    checar('.in_("status", list(_STATUS_EM_VOO_WORK_RUN))' in corpo,
           "e so os runs EM VOO, nao o historico inteiro")
    checar('resumo["ja_sinalizados"]' in fonte,
           "orfao ja sinalizado nao vira alarme de novo",
           "sem isso, 5 em 5 minutos viraria 288 alarmes por dia do MESMO caso")


def main() -> int:
    print("=" * 72)
    print("A VARREDURA DO ORFAO NAO DEPENDE MAIS DE TRAFEGO — P-34")
    print("=" * 72)

    for teste in (teste_o_gatilho_antigo_dispara_uma_vez_so,
                  teste_o_gatilho_antigo_depende_de_trafego,
                  teste_a_varredura_entrou_no_laco_de_manutencao,
                  teste_o_intervalo_e_sensato,
                  teste_o_guarda_tem_como_falhar,
                  teste_a_varredura_continua_barata_e_idempotente):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 72)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O ORFAO E PROCURADO POR RELOGIO, NAO POR SORTE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
