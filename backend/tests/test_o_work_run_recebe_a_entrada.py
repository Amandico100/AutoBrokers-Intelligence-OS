# -*- coding: utf-8 -*-
"""O Work Run recebe A ENTRADA do trabalho — e nao so o roteiro para chegar ate ele.

O DEFEITO QUE ESTE ARQUIVO GUARDA
---------------------------------
Medido em 17/08/2026, Work Run `ca6bb47e-acb1-4e23-8621-78896bec9c82`:

    result_summary : "Rotina sem identificador - nada a executar."
    input_payload  : {"routine_id": "cc69c3b9-..."}
    status         : completed
    duracao        : 1 segundo

O identificador ESTAVA no banco. O executor nao o recebeu.

A causa: o outbox publica na fila uma mensagem MINIMA, por desenho
(`work_queue_outbox.payload_minimal`) --

    {"run_id": ..., "company_id": ..., "workflow_key": "bridge.routine.execute"}

-- e a leitura do `input_payload` no banco estava dentro de
`if not workflow_key:`. Um ramo que so roda quando a chave FALTA na mensagem,
ou seja: nunca, porque o outbox sempre a manda.

Resultado: o handler recebeu um pacote sem a entrada do trabalho, devolveu
"nada a executar" e o run terminou COMPLETED. Verde no painel, zero trabalho
feito. E o pior tipo de falha, porque nem parece falha -- o Founder ficou 15
minutos esperando um boleto de um trabalho que o sistema considerava um
sucesso.

POR QUE UM TESTE, E NAO SO O CONSERTO
-------------------------------------
Porque a mensagem da fila e minima DE PROPOSITO e vai continuar sendo. Toda vez
que alguem escrever um workflow novo, ele vai depender de o worker carregar a
entrada do banco. Este guarda existe para que "carregar sempre" nao vire
"carregar as vezes" de novo.
"""
from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER = os.path.join(RAIZ, "app", "workers", "smith_worker.py")
WORKFLOWS = os.path.join(RAIZ, "app", "services", "work", "workflows.py")
QUEUE = os.path.join(RAIZ, "app", "services", "work", "queue.py")

PASS = FAIL = 0


def check(nome: str, cond: bool, extra: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


def ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def corpo_da_funcao(fonte: str, nome: str) -> str:
    """O codigo de UMA funcao/metodo, sem comentarios. Le a arvore, nao o texto.

    Casar com o texto do arquivo inteiro seria o defeito que esta SPEC ja
    encontrou quatro vezes: um guarda que a documentacao satisfaz nao guarda
    nada. Aqui o `ast.unparse` devolve so o codigo -- comentario nao sobrevive
    a arvore.
    """
    arvore = ast.parse(fonte)
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return ast.unparse(no)
    return ""


# ===========================================================================
print("\n[1] A MENSAGEM DA FILA E MINIMA -- e por isso o banco tem de ser lido")
# ===========================================================================

fonte_queue = ler(QUEUE)
# O `publish({...})` do outbox: pegamos o dicionario literal passado a ele, na
# arvore. Casar com o texto do arquivo inteiro pegaria comentario.
publicado = ""
for no in ast.walk(ast.parse(fonte_queue)):
    if isinstance(no, ast.Call) and getattr(no.func, "attr", "") == "publish" and no.args:
        publicado = ast.unparse(no.args[0])
        break

check("achei a chamada `publish({...})` do outbox", bool(publicado), publicado[:120])
check(
    "o outbox publica so o roteamento (outbox_id, work_run_id, event_kind) + payload_minimal",
    "outbox_id" in publicado and "payload_minimal" in publicado,
    publicado[:200],
)
check(
    "e NAO acrescenta `input_payload` na mensagem",
    "input_payload" not in publicado,
    "o desenho e minimo de proposito; a entrada mora no banco",
)

# ===========================================================================
print("\n[2] O WORKER LE A ENTRADA DO BANCO -- SEMPRE, nao so as vezes")
# ===========================================================================

fonte_worker = ler(WORKER)
executar = corpo_da_funcao(fonte_worker, "_executar_workflow") or corpo_da_funcao(
    fonte_worker, "_processar") or fonte_worker

check(
    "o worker consulta `work_runs` pela entrada",
    "input_payload" in executar and "work_runs" in executar,
)

# 🔴 A ASSERCAO QUE PEGA O DEFEITO.
#
# O jeito honesto de verificar "sempre" e provar que a leitura NAO esta dentro
# de um `if not workflow_key`. Procurar a string `if not workflow_key` no texto
# pegaria um comentario; por isso a checagem e na ARVORE.
arvore_worker = ast.parse(fonte_worker)
leitura_condicionada = False
for no in ast.walk(arvore_worker):
    if not isinstance(no, ast.If):
        continue
    teste = ast.unparse(no.test)
    if "workflow_key" not in teste:
        continue
    corpo = "\n".join(ast.unparse(x) for x in no.body)
    if "input_payload" in corpo:
        leitura_condicionada = True

check(
    "a leitura do `input_payload` NAO esta dentro de um `if` sobre workflow_key",
    not leitura_condicionada,
    "era exatamente aqui que o routine_id se perdia -- o ramo nunca roda "
    "porque o outbox sempre manda o workflow_key",
)

# A ordem do merge: o do BANCO por baixo, o da FILA por cima.
check(
    "o merge poe a entrada do banco por baixo e a da fila por cima",
    "**payload}" in executar.replace(" ", "") or "**payload }" in executar,
    "a fila carrega roteamento e e mais recente; o banco carrega a entrada",
)

# Falhar e melhor que rodar vazio.
check(
    "se o banco nao responder, o run FALHA em vez de rodar sem entrada",
    "entrada_indisponivel" in executar,
    "rodar vazio e reportar sucesso e a falha que ninguem percebe",
)

# ===========================================================================
print("\n[3] CONTROLE -- o guarda CONSEGUE ficar vermelho")
# ===========================================================================
#
# Sem esta linha, um `corpo_da_funcao` que devolvesse string vazia faria as
# assercoes de "nao contem" passarem todas.

def leitura_esta_condicionada(fonte: str) -> bool:
    """O detector, isolado — para poder ser apontado para codigo de mentira."""
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.If) and "workflow_key" in ast.unparse(no.test):
            if "input_payload" in "\n".join(ast.unparse(x) for x in no.body):
                return True
    return False


# O CODIGO EXATO QUE ESTAVA NO PRODUTO ATE 17/08/2026, em miniatura.
CODIGO_COM_O_DEFEITO = '''
def processar(payload, db, run_id):
    workflow_key = payload.get("workflow_key")
    if not workflow_key:
        res = db.table("work_runs").select("workflow_key, input_payload").eq("id", run_id).execute()
        workflow_key = (res.data or {}).get("workflow_key")
        payload = {**payload, **((res.data or {}).get("input_payload") or {})}
    return workflow_key, payload
'''

CODIGO_CONSERTADO = '''
def processar(payload, db, run_id):
    workflow_key = payload.get("workflow_key")
    res = db.table("work_runs").select("workflow_key, input_payload").eq("id", run_id).execute()
    linha = res.data or {}
    workflow_key = workflow_key or linha.get("workflow_key")
    payload = {**(linha.get("input_payload") or {}), **payload}
    return workflow_key, payload
'''

check(
    "CONTROLE: o detector ACHA a leitura condicionada (o codigo do defeito)",
    leitura_esta_condicionada(CODIGO_COM_O_DEFEITO),
    "se este falhar, a assercao do bloco [2] nao prova nada -- ela passaria "
    "sobre qualquer arquivo, inclusive um vazio",
)
check(
    "CONTROLE: e NAO acha no codigo consertado (nao acusa qualquer `if`)",
    not leitura_esta_condicionada(CODIGO_CONSERTADO),
    "um detector que acusa tudo tambem nao serve",
)

# ===========================================================================
print("\n[4] O BILHETE DE ENTREGA E CARIMBADO NA CHEGADA")
# ===========================================================================
#
# `_criar_work_run_para_rotina` insere um routine_runs `delegated` com
# "executando como Work Run". Ninguem o fechava: a tela mostrava "executando"
# para sempre, com o Work Run ja completed.

fonte_wf = ler(WORKFLOWS)
bridge = corpo_da_funcao(fonte_wf, "bridge_rotina")
check("o bridge de rotina existe", bool(bridge))
check(
    "e ele FECHA a linha `delegated` ao terminar",
    "delegated" in bridge and "routine_runs" in bridge and "finished_at" in bridge,
    "sem isto a tela mostra 'executando como Work Run' para sempre",
)
check(
    "fechando SO a linha deste run (nunca as de outros)",
    'eq("work_run_id"' in bridge or "eq('work_run_id'" in bridge,
)

print("\n" + "=" * 70)
print(f"  {PASS} asseroes verdes - {FAIL} vermelhas".replace("asseroes", "assercoes"))
print("=" * 70)
sys.exit(1 if FAIL else 0)
