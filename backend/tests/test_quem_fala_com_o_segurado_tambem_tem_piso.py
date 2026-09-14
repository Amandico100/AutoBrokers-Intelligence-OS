# -*- coding: utf-8 -*-
"""M-E2 -- QUEM FALA COM O SEGURADO TAMBEM TEM PISO (SPEC-EXTRA-001.1 BLOCO E).

O DEFEITO QUE ESTE ARQUIVO GUARDA
------------------------------------------------------------------------------
📊 Conferido em 13 e 14/09/2026, `app/factories/llm_factory.py`:

    PAPEIS_QUE_CONVERSAM = ("", "core", "attendance")

`insured_external` -- o papel de quem fala com o SEGURADO (GLOSSARIO) -- **nao
estava na tupla**, e `piso_de_saida` devolve o valor do banco sem eleva-lo
quando o papel nao esta na lista.

🔴 O QUE IMPEDE VENDER ISTO COMO INCIDENTE, e esta no proprio guarda:
📊 os 8 agentes da base sao **4 `core` + 4 `attendance`**. Nao existe hoje
nenhuma instancia viva com `agent_role='insured_external'`. **Nao ha vitima
medida.** Classificacao honesta (protocolo 2): ESSENCIAL LATENTE, nao BLOCKER.
O defeito acontece no dia em que a primeira corretora instalar um agente desse
papel: ele nasceria com o teto do banco (📊 hoje 1200 ou 2000) e a resposta ao
segurado sairia cortada -- exatamente como 10 das 95 respostas do corretor
sairam em 09-10/09/2026.

A correcao e UMA PALAVRA na tupla. Este arquivo e o que impede a palavra de
sumir de novo.

O ELO
------------------------------------------------------------------------------
```
o SEGURADO recebe a resposta inteira
  PORQUE `insured_external` esta em PAPEIS_QUE_CONVERSAM
  E PORQUE o piso NAO engessa quem configurou mais que ele
  E PORQUE quem NAO conversa (auxiliar, subagente) continua SEM piso
     -- o par de controle: sem ele, "tem piso" passaria com uma funcao que
     elevasse TODO MUNDO, e cada JSON de auxiliar custaria 8192 tokens de teto
```

⛔ Nenhum dado real, nenhuma rede, nenhum banco: so a fabrica de producao.

AS MUTACOES -- por COPIA, em SUBPROCESSO, so com `--mutar`
------------------------------------------------------------------------------
    M1  `insured_external` fora de PAPEIS_QUE_CONVERSAM  -> [G1] vermelho
    M2  o piso passa a valer para TODO papel             -> [G3] vermelho
    M3  o piso vira teto (engessa quem configurou mais)  -> [G2] vermelho

Rodar (a partir de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_quem_fala_com_o_segurado_tambem_tem_piso.py
    ... --mutar
"""
from __future__ import annotations

import importlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

PASS = 0
FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))
    return bool(cond)


def _ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return fh.read()


def _fabrica():
    """A FABRICA de producao -- nunca uma copia da regra (CLAUDE.md 9.4)."""
    return importlib.import_module("app.factories.llm_factory")


# ==========================================================================
# G1 -- QUEM FALA COM O SEGURADO TEM PISO
# ==========================================================================
def gate_G1():
    print("\n[G1] `insured_external` -- quem fala com o SEGURADO -- tem piso")
    fab = _fabrica()
    piso = fab.piso_de_saida
    valor = fab.PISO_DE_SAIDA_DA_CONVERSA

    check("[G1] o piso cabe uma apolice item a item (>= 8192)", valor >= 8192,
          "piso=%s" % valor)
    # 📊 1200 e o numero GRAVADO do agente core da Resulta em 09/09/2026, e o
    # mesmo que o tenant de sandbox recebia em `bootstrap-tenant/route.ts:106`.
    check("[G1] piso_de_saida('insured_external', 1200) == 8192",
          piso("insured_external", 1200) == valor,
          "recebido=%s" % piso("insured_external", 1200))
    # 📊 2000 e o outro valor medido na base (4 dos 8 agentes) e o DEFAULT de
    # DDL que continua em `schema_completo.sql:454` (P-E0011-DEFAULT-DDL-2000).
    check("[G1] piso_de_saida('insured_external', 2000) == 8192",
          piso("insured_external", 2000) == valor,
          "recebido=%s" % piso("insured_external", 2000))
    check("[G1] papel com espacos/caixa diferente tambem sobe "
          "('  Insured_External  ')",
          piso("  Insured_External  ", 1200) == valor,
          "recebido=%s" % piso("  Insured_External  ", 1200))
    check("[G1] `insured_external` esta DECLARADO na tupla, nao so por acaso",
          "insured_external" in fab.PAPEIS_QUE_CONVERSAM,
          "tupla=%r" % (fab.PAPEIS_QUE_CONVERSAM,))
    # os outros papeis que conversam continuam cobertos -- o acrescimo nao
    # pode ter derrubado ninguem
    for papel in ("core", "attendance", "", None):
        check("[G1] '%s' (que ja tinha piso) continua com piso" % papel,
              piso(papel, 1200) == valor, "recebido=%s" % piso(papel, 1200))


# ==========================================================================
# G2 -- O PISO NAO ENGESSA
# ==========================================================================
def gate_G2():
    print("\n[G2] o piso e PISO, nao teto: quem configurou mais continua mandando")
    fab = _fabrica()
    piso = fab.piso_de_saida
    valor = fab.PISO_DE_SAIDA_DA_CONVERSA

    check("[G2] piso_de_saida('core', 9000) == 9000",
          piso("core", 9000) == 9000, "recebido=%s" % piso("core", 9000))
    check("[G2] piso_de_saida('insured_external', 16000) == 16000",
          piso("insured_external", 16000) == 16000,
          "recebido=%s" % piso("insured_external", 16000))
    check("[G2] valor exatamente no piso permanece no piso",
          piso("insured_external", valor) == valor)
    # valor ausente/ilegivel nao vira zero nem excecao
    check("[G2] valor nulo em papel que conversa cai NO PISO (nunca em 0)",
          piso("insured_external", None) == valor,
          "recebido=%s" % piso("insured_external", None))
    check("[G2] valor ilegivel em papel que conversa cai NO PISO",
          piso("insured_external", "muito") == valor,
          "recebido=%s" % piso("insured_external", "muito"))


# ==========================================================================
# G3 -- O PAR DE CONTROLE: quem NAO conversa continua sem piso
#
# 🔴 Sem este gate, G1 passaria com uma funcao que elevasse TODO MUNDO -- e
# cada auxiliar que devolve um JSON de 40 tokens passaria a carregar teto de
# 8192, custo puro sem um byte de mudanca para ninguem (protocolo 2).
# ==========================================================================
def gate_G3():
    print("\n[G3] PAR DE CONTROLE: quem NAO fala com gente continua sem piso")
    fab = _fabrica()
    piso = fab.piso_de_saida

    # 📊 os dois papeis que existem no codigo e NAO conversam (grep em
    # `app/agents/**` e `app/factories/**`, 14/09/2026): `auxiliary` e `subagent`.
    for papel in ("auxiliary", "subagent"):
        check("[G3] '%s' mantem o valor GRAVADO (1200 continua 1200)" % papel,
              piso(papel, 1200) == 1200, "recebido=%s" % piso(papel, 1200))
        check("[G3] '%s' mantem 512 (JSON curto nao precisa de 8192)" % papel,
              piso(papel, 512) == 512, "recebido=%s" % piso(papel, 512))
        check("[G3] '%s' NAO esta em PAPEIS_QUE_CONVERSAM" % papel,
              papel not in fab.PAPEIS_QUE_CONVERSAM,
              "tupla=%r" % (fab.PAPEIS_QUE_CONVERSAM,))

    # 🔴 A prova de que os dois lados CONSEGUEM ser diferentes (CLAUDE.md 9.3):
    # se conversa e nao-conversa devolvessem a mesma coisa, o guarda inteiro
    # seria um carimbo.
    check("[G3] conversa e nao-conversa devolvem valores DIFERENTES para o "
          "mesmo 1200",
          piso("insured_external", 1200) != piso("auxiliary", 1200),
          "%s vs %s" % (piso("insured_external", 1200), piso("auxiliary", 1200)))


GATES = {"G1": gate_G1, "G2": gate_G2, "G3": gate_G3}


# ==========================================================================
# AS MUTACOES -- (id, arquivo, de, para, gate)
# ==========================================================================
MUTACOES = [
    ("M1", "app/factories/llm_factory.py",
     'PAPEIS_QUE_CONVERSAM = ("", "core", "attendance", "insured_external")',
     'PAPEIS_QUE_CONVERSAM = ("", "core", "attendance")',
     "G1"),
    ("M2", "app/factories/llm_factory.py",
     "    if papel not in PAPEIS_QUE_CONVERSAM:\n        return max_tokens",
     "    if False:\n        return max_tokens",
     "G3"),
    ("M3", "app/factories/llm_factory.py",
     "    return max(atual, PISO_DE_SAIDA_DA_CONVERSA)",
     "    return PISO_DE_SAIDA_DA_CONVERSA",
     "G2"),
]


def rodar_mutacoes(filtro=None):
    print("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO; a arvore parada")
    vermelhas = verdes = 0
    for mid, rel, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, rel)
        original = _ler(caminho)
        if de not in original:
            check("%s: o trecho a mutar EXISTE em %s" % (mid, rel), False,
                  "ancora ausente: %r" % de[:80])
            verdes += 1
            continue
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak").name
        shutil.copyfile(caminho, backup)
        try:
            with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
                fh.write(original.replace(de, para, 1))
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--so", gate],
                cwd=RAIZ, capture_output=True, text=True, timeout=600,
                env={**os.environ, "PYTHONIOENCODING": "utf-8",
                     "PYTHONDONTWRITEBYTECODE": "1"})
            falhas = [l.strip() for l in (r.stdout or "").splitlines()
                      if "[FALHOU]" in l]
            if r.returncode != 0 and falhas:
                vermelhas += 1
                print("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:160]))
            else:
                verdes += 1
                print("  [FALHOU] %s NAO deixou %s vermelho (rc=%s)\n%s"
                      % (mid, gate, r.returncode, (r.stdout or r.stderr)[-1200:]))
        finally:
            shutil.copyfile(backup, caminho)   # 🔴 restaura por COPIA
            os.unlink(backup)
            assert _ler(caminho) == original, "restauracao falhou em " + rel
    print("\n  PLACAR DAS MUTACOES: %d vermelhas · %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M") else None
        sys.exit(0 if rodar_mutacoes(filtro) else 1)
    so = args[args.index("--so") + 1] if "--so" in args else None
    print("=" * 74)
    print("  M-E2 -- QUEM FALA COM O SEGURADO TAMBEM TEM PISO")
    print("=" * 74)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            check("%s roda sem excecao" % gid, False,
                  "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()[-700:]))
    print("\n" + "=" * 74)
    print("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
    print("=" * 74)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
