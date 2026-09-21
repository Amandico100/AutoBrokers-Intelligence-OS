# -*- coding: utf-8 -*-
"""G5 — o freio passou a saber DE QUAL JOB se trata. SPEC-EXTRA-001.10 P0-6.

## 🔴 O defeito que este arquivo fecha (BLOCKER)

📊 Medido em 13/09/2026 e reconfirmado em 20/09: `efeito_material_liberado()`
lê uma variável **do processo**, e `motivo_para_barrar` não recebia job, nem
CPF, nem corretora. Consequência direta, sem inferência nenhuma no meio:
**ligar o freio para fazer UM canário libera todos os jobs de vidros em voo
naquele worker, de qualquer corretora** — pedidos pagos, no nome de segurados
que ninguém escolheu, que a seguradora não desfaz.

📊 E em produção o freio global **já está ligado** nos dois serviços. Então a
allowlist não é conveniência: é o que torna o canário possível com segurança.

## O contrato, e a terceira frase é a que importa

```
vazia ......... comportamento de HOJE (o freio global manda sozinho)
preenchida .... só os listados passam; os outros são barrados COM motivo
🔴 ela nunca LIGA o freio — ela só o ESTREITA
```

A terceira é a diferença entre uma trava e um interruptor disfarçado. Se a
allowlist pudesse liberar com o freio global desligado, esquecer uma linha de
texto numa variável de ambiente abriria pedido de verdade — e **esquecer tem de
custar um pedido a menos, nunca um a mais**.

## ⛔ E este arquivo é metade CONTROLE

Um freio que barra tudo passaria em qualquer teste que só verificasse "o job
que não está na lista foi barrado".
"""
from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

PASS = FAIL = 0


def checar(cond, nome, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok]     " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  << " + str(extra)[:300] if extra else ""))


# Carrega o registro ISOLADO (mesmo molde de
# `test_o_freio_de_vidros_nao_mata_a_cobranca.py`): sem Playwright, sem app.
spec = importlib.util.spec_from_file_location(
    "journeys_isolado_e00110", os.path.join(RAIZ, "portal_worker", "journeys", "__init__.py"))
J = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = J
spec.loader.exec_module(J)

VIDROS = ("vidros_lanternas", "abrir_atendimento")
COBRANCA = ("allianz_corretor", "cobranca_sweep")

# 💭 Dois jobs de mentira, da MESMA journey. UUIDs inventados, óbvios.
JOB_DO_CANARIO = "11111111-1111-4111-8111-111111111111"
JOB_DE_OUTRO_SEGURADO = "22222222-2222-4222-8222-222222222222"

# 💭 CPFs de teste (dígitos verificadores válidos, pessoas inexistentes).
CPF_DO_CANARIO = "529.982.247-25"
CPF_DE_OUTRO = "111.444.777-35"


class _Ambiente:
    """Roda com estas variáveis e devolve o ambiente exatamente ao que era."""

    def __init__(self, **valores):
        self.valores = valores
        self.antes = {}

    def __enter__(self):
        for k, v in self.valores.items():
            self.antes[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *a):
        for k, v in self.antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _com(freio=None, allowlist=None):
    return _Ambiente(PORTAL_EFEITO_MATERIAL_LIBERADO=freio,
                     PORTAL_CANARIO_ALLOWLIST=allowlist)


# ==========================================================================
def g5_o_par_de_vereditos_opostos() -> None:
    """Dois jobs, mesma journey, freio ligado, allowlist com UM deles."""
    print("\n[G5] dois jobs, mesma journey, allowlist com UM")

    with _com(freio="true", allowlist=f"job:{JOB_DO_CANARIO}"):
        do_canario = J.motivo_para_barrar(*VIDROS, job_id=JOB_DO_CANARIO)
        do_outro = J.motivo_para_barrar(*VIDROS, job_id=JOB_DE_OUTRO_SEGURADO)

        checar(do_canario == "", "o job LISTADO passa", repr(do_canario))
        checar(bool(do_outro), "e o job de OUTRO segurado e BARRADO", repr(do_outro))
        checar("allowlist" in do_outro.lower(),
               "e o motivo diz, em texto, que foi a allowlist do canario",
               do_outro)
        checar("PORTAL_CANARIO_ALLOWLIST" in do_outro,
               "e nomeia a variavel, para quem for conferir nao precisar do codigo",
               do_outro)

        # 🔴 PII: o motivo vai para `portal_jobs.error` e para o log. Nem o CPF
        # nem o hash dele podem aparecer ali (CLAUDE.md §7).
        hash_do_outro = J.cpf_hash_de(CPF_DE_OUTRO)
        checar(hash_do_outro not in do_outro
               and "".join(c for c in CPF_DE_OUTRO if c.isdigit()) not in do_outro,
               "e o motivo NAO carrega CPF nem hash — ele vai para o log",
               do_outro)

    # A allowlist tambem aceita o CPF, porque no ponto de CRIACAO o job ainda
    # nao existe (a tool decide antes do insert).
    with _com(freio="true", allowlist=f"cpf:{J.cpf_hash_de(CPF_DO_CANARIO)}"):
        checar(J.motivo_para_barrar(*VIDROS, cpf_hash=J.cpf_hash_de(CPF_DO_CANARIO)) == "",
               "por CPF: o segurado do canario passa")
        checar(bool(J.motivo_para_barrar(*VIDROS, cpf_hash=J.cpf_hash_de(CPF_DE_OUTRO))),
               "por CPF: outro segurado e barrado")
        # 🔴 No ponto de criacao NAO ha job_id. Se a ausencia dele liberasse,
        # a allowlist nao valeria nada justamente onde o pedido nasce.
        checar(bool(J.motivo_para_barrar(*VIDROS)),
               "sem job e sem CPF, com allowlist preenchida: BARRADO",
               "ausencia de identificacao nunca pode virar permissao")


def g5_os_pares_de_controle() -> None:
    """Os três controles. Sem eles, um freio que barra tudo passaria acima."""
    print("\n[G5-controle] vazia = hoje · freio desligado = ninguem")

    # PAR 1 — allowlist VAZIA e o comportamento de hoje, para os DOIS jobs.
    for allow in (None, "", "   ", ",,"):
        with _com(freio="true", allowlist=allow):
            checar(J.motivo_para_barrar(*VIDROS, job_id=JOB_DO_CANARIO) == ""
                   and J.motivo_para_barrar(*VIDROS, job_id=JOB_DE_OUTRO_SEGURADO) == "",
                   f"allowlist {allow!r}: os DOIS passam (comportamento de hoje)")
            # E a chamada ANTIGA, sem argumento nenhum, continua respondendo o
            # que respondia — nenhum chamador do repositorio precisou mudar.
            checar(J.motivo_para_barrar(*VIDROS) == "",
                   f"allowlist {allow!r}: a chamada SEM argumentos segue valendo")

    # PAR 2 — 🔴 a allowlist NUNCA liga o freio.
    with _com(freio=None, allowlist=f"job:{JOB_DO_CANARIO}"):
        checar(bool(J.motivo_para_barrar(*VIDROS, job_id=JOB_DO_CANARIO)),
               "freio DESLIGADO + allowlist preenchida: NINGUEM passa",
               "se passasse, a allowlist seria um interruptor disfarcado de trava")
        checar("PORTAL_EFEITO_MATERIAL_LIBERADO" in J.motivo_para_barrar(
                   *VIDROS, job_id=JOB_DO_CANARIO),
               "e o motivo aponta o freio global, nao a allowlist",
               "quem le o erro tem de saber QUAL das duas travas barrou")

    # PAR 3 — a COBRANCA (READ_ONLY) nao e afetada por nada disto.
    for freio, allow in ((None, None), ("true", None), ("true", f"job:{JOB_DO_CANARIO}"),
                         (None, f"job:{JOB_DO_CANARIO}")):
        with _com(freio=freio, allowlist=allow):
            checar(J.motivo_para_barrar(*COBRANCA, job_id=JOB_DE_OUTRO_SEGURADO) == "",
                   f"CONTROLE: a cobranca passa (freio={freio!r} allow={allow!r})",
                   "foi exatamente aqui que a primeira recomendacao da SPEC-075 errou")


def g5_o_hash_do_cpf_e_um_so() -> None:
    """Quem gera, quem escreve e quem confere têm de produzir o MESMO texto."""
    print("\n[G5-hash] o apelido do CPF na allowlist")

    h = J.cpf_hash_de(CPF_DO_CANARIO)
    checar(len(h) == 12 and all(c in "0123456789abcdef" for c in h),
           f"o hash tem 12 hex ({h})", h)
    checar(J.cpf_hash_de("529.982.247-25") == J.cpf_hash_de("52998224725")
           == J.cpf_hash_de(" 529 982 247 25 "),
           "pontuacao nao muda o hash — e a mesma pessoa",
           "duas grafias do mesmo CPF dariam duas allowlists que nao casam")
    checar(J.cpf_hash_de(CPF_DO_CANARIO) != J.cpf_hash_de(CPF_DE_OUTRO),
           "CONTROLE: CPFs diferentes dao hashes diferentes",
           "um hash constante liberaria o mundo inteiro")
    checar(J.cpf_hash_de("") == "" and J.cpf_hash_de(None) == ""
           and J.cpf_hash_de("sem digitos") == "",
           "sem digitos, nao ha apelido — e '' nunca casa com nada na lista")

    # 🔴 E o comando que o Founder roda precisa dar ESTE mesmo valor. O comando
    # e provado dentro do conteiner em `docs`/relatorio; aqui provamos que a
    # formula e a de uma linha de `python -c` com hashlib, sem nada do app.
    import hashlib
    esperado = hashlib.sha256("52998224725".encode()).hexdigest()[:12]
    checar(h == esperado,
           "e a formula e sha256(so os digitos).hexdigest()[:12] — nada do app",
           f"{h} != {esperado}")


def g5_a_allowlist_e_tolerante_com_gente() -> None:
    """Espaço a mais e maiúscula não podem barrar o canário do Founder."""
    print("\n[G5-humano] espaco e caixa nao quebram a allowlist")

    for texto in (f"job:{JOB_DO_CANARIO}",
                  f" job:{JOB_DO_CANARIO} ",
                  f"job:{JOB_DO_CANARIO.upper()}",
                  f"cpf:aaaaaaaaaaaa, job:{JOB_DO_CANARIO}",
                  f"job:{JOB_DO_CANARIO},"):
        with _com(freio="true", allowlist=texto):
            checar(J.motivo_para_barrar(*VIDROS, job_id=JOB_DO_CANARIO) == "",
                   f"allowlist {texto!r}: o canario passa")
            checar(bool(J.motivo_para_barrar(*VIDROS, job_id=JOB_DE_OUTRO_SEGURADO)),
                   f"allowlist {texto!r}: CONTROLE — e o outro continua barrado")


def g5_os_dois_pontos_chamam_com_o_job() -> None:
    """O freio vale na CRIAÇÃO e na EXECUÇÃO — e agora os dois passam o alvo."""
    print("\n[G5-pontos] a criacao e a execucao identificam o job")

    import ast

    def argumentos_do_freio(caminho: str, funcao: str) -> set:
        """Quais nomeados a chamada REAL a `motivo_para_barrar` recebe.

        Le a ARVORE, nao o texto: casar a string pegaria o comentario que
        explica o freio — ja aconteceu seis vezes na SPEC-075.
        """
        arvore = ast.parse(open(os.path.join(RAIZ, caminho), encoding="utf-8").read())
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if no.name != funcao:
                continue
            for x in ast.walk(no):
                if isinstance(x, ast.Call) and getattr(x.func, "id", "") == "motivo_para_barrar":
                    return {k.arg for k in x.keywords}
        return set()

    execucao = argumentos_do_freio("portal_worker/worker.py", "_run_job")
    checar("job_id" in execucao and "cpf_hash" in execucao,
           "na EXECUCAO, o worker passa job_id e cpf_hash", str(execucao))

    criacao = argumentos_do_freio("app/agents/tools/portal_tool.py", "_envio_liberado")
    checar("cpf_hash" in criacao,
           "na CRIACAO, a tool passa cpf_hash (o job ainda nao existe)", str(criacao))
    checar("job_id" not in criacao,
           "CONTROLE: e ela NAO finge ter um job_id",
           "um job_id inventado no ponto de criacao nunca casaria com a lista")


if __name__ == "__main__":
    print("=" * 72)
    print("G5 — o freio escolhe UM job, e nunca se liga sozinho")
    print("=" * 72)
    g5_o_par_de_vereditos_opostos()
    g5_os_pares_de_controle()
    g5_o_hash_do_cpf_e_um_so()
    g5_a_allowlist_e_tolerante_com_gente()
    g5_os_dois_pontos_chamam_com_o_job()
    print("\n" + "=" * 72)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
    print("=" * 72)
    sys.exit(1 if FAIL else 0)
