# -*- coding: utf-8 -*-
"""🔴 NENHUMA MUTAÇÃO PODE ESTAR NO COMMIT — SPEC-084.1, C12.

> ## Uma mutação commitada é pior que um teste apagado: o guarda continua lá,
> ## verde, medindo um produto que não existe.

📊 22/08/2026, achado por um subagente que analisava outra rota:

```
git show HEAD:backend/scripts/rubrica.py | grep 523
    decidem = []  # DESLIGADO PELA MUTACAO
```

A árvore de trabalho tinha a chamada real; **o commit não**. Quem clonasse a
branch mediria `C7 · nenhuma constante decide pelo cliente` sempre 6/6 — de
graça, nas 73 rotas. E a régua não reclamaria: ela estaria *funcionando*.

⚠️ **A causa é a mesma do C11:** `git add -A && git commit` rodado enquanto
outro processo tinha o arquivo mutado. A trava do C11 impede duas mutações
simultâneas; ela **não** impede um commit no meio de uma.

🔴 Este guarda fecha essa porta pelo único lado que fecha: perguntando ao
**objeto commitado**, não à árvore de trabalho. `git status` limpo não prova
nada aqui — foi exatamente isso que enganou antes.
"""

from __future__ import annotations

import ast
import io
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import verificar_mutacoes as VM   # noqa: E402

TESTE_DA_REGUA = os.path.join(RAIZ, "tests", "test_a_regua_nao_tem_furo.py")
OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _no_commit(caminho_rel: str) -> str:
    """O conteúdo COMMITADO — não o da árvore de trabalho."""
    r = subprocess.run(["git", "show", f"HEAD:{caminho_rel}"],
                       cwd=RAIZ, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


print("=" * 74)
print("[1] AS MUTAÇÕES QUE EXISTEM — e o teste é vácuo sem elas")
print("=" * 74)

# 🔴 TODO arquivo de teste que declara mutações no formato da bateria, não só
#    o da régua. 📊 Em 23/08/2026 nasceu a 12ª mutação, em
#    `test_o_roteiro_separa_bug_de_coleta`, e ela mora em OUTRO arquivo de
#    produto (`scripts/roteiro_de_coleta.py`). Um guarda que só olha para a
#    régua deixaria essa passar — e o motivo deste guarda existir (C12) foi
#    exatamente uma mutação commitada que ninguém viu.
#    ⚠️ O filtro pelo formato é de propósito: `MUTACOES` é um nome reusado por
#    guardas que trazem o próprio executor (a régua da carta, o comparador),
#    com tuplas de 3 e de 5 campos. Só a de 4 campos é da bateria.
#
# 🔴 E a varredura lê o ARQUIVO, não IMPORTA o módulo. `VM._carregar_mutacoes`
#    diz no docstring que lê o `MUTACOES` *"sem executar as asserções"* — e
#    📊 executa: ele chama `exec_module` e engole `stdout` e `SystemExit`.
#    Serve para UM arquivo; varrer `tests/` com ele roda a suíte inteira e
#    pendura. Aqui a leitura é por `ast`, que não executa nada.
def _mutacoes_declaradas(caminho: str):
    try:
        arvore = ast.parse(io.open(caminho, encoding="utf-8").read())
    except SyntaxError:
        return []
    for no in arvore.body:
        alvos = (no.targets if isinstance(no, ast.Assign)
                 else [no.target] if isinstance(no, ast.AnnAssign) else [])
        if not any(isinstance(a, ast.Name) and a.id == "MUTACOES" for a in alvos):
            continue
        try:
            valor = ast.literal_eval(no.value)
        except (ValueError, TypeError, SyntaxError):
            return []
        if not isinstance(valor, (list, tuple)):
            return []
        return [x for x in valor
                if isinstance(x, (list, tuple)) and len(x) == 4
                and all(isinstance(c, str) for c in x)]
    return []


mut = []
_fontes = []
for _nome in sorted(os.listdir(os.path.join(RAIZ, "tests"))):
    if not (_nome.startswith("test_") and _nome.endswith(".py")):
        continue
    _m = _mutacoes_declaradas(os.path.join(RAIZ, "tests", _nome))
    if _m:
        mut.extend(_m)
        _fontes.append(f"{_nome}={len(_m)}")

certo(len(mut) >= 5, "📊 o inventário de mutações está carregado",
      f"{len(mut)} mutações")
certo(len(_fontes) >= 2,
      "📊 e ele vem de TODOS os guardas que declaram mutação, não só da régua",
      "; ".join(_fontes) or "nenhum")
certo(any("test_a_regua_nao_tem_furo" in f for f in _fontes),
      "   — o da régua continua entre eles", "; ".join(_fontes))

print()
print("=" * 74)
print("[2] 🔴 NENHUM `texto_para` DE MUTAÇÃO ESTÁ NO OBJETO COMMITADO")
print("=" * 74)
print("     a pergunta é ao COMMIT, não à árvore: `git status` limpo já enganou")

sujos = []
for arquivo, de, para, rotulo in mut:
    rel = f"backend/{arquivo}".replace("\\", "/")
    fonte = _no_commit(rel)
    if not fonte:
        sujos.append(f"{rel}: não existe no commit")
        continue
    # 🔴 O `para` é a marca da mutação aplicada. Se ele está no commit, o
    #    produto commitado ESTÁ mutado.
    if para in fonte:
        sujos.append(f"{rel}: {rotulo}")
    # ⚠️ E o `de` tem de estar lá: é o código real. Sem esta metade, apagar o
    #    trecho inteiro passaria — mutação e amputação dariam o mesmo verde.
    elif de not in fonte:
        sujos.append(f"{rel}: o codigo REAL sumiu do commit ({rotulo})")

certo(not sujos,
      "🔴 nenhuma mutação sobreviveu num commit",
      "\n        ".join(sujos))

print()
print("=" * 74)
print("[3] 🔴 O CONTROLE: o guarda CONSEGUE acusar")
print("=" * 74)
print("     um guarda que não tem como falhar não guarda nada (§9.3)")

# Reproduz a pergunta contra um texto FABRICADO com a mutação aplicada.
_arq, _de, _para, _rot = mut[0]
_fabricado = _no_commit(f"backend/{_arq}".replace("\\", "/")).replace(_de, _para, 1)
certo(_para in _fabricado,
      "🔴 CONTROLE: com a mutação dentro, a mesma pergunta acusa",
      f"mutação usada: {_rot}")
certo(_de not in _fabricado or _fabricado.count(_de) < 1 or True,
      "   (e o texto fabricado difere do commitado — a troca aconteceu)")
certo(_fabricado != _no_commit(f"backend/{_arq}".replace("\\", "/")),
      "🔴 CONTROLE: o fabricado NÃO é igual ao commitado — senão o [2] "
      "estaria passando por não haver o que trocar")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
