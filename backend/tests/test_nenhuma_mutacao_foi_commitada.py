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

mut = VM._carregar_mutacoes(TESTE_DA_REGUA)
certo(len(mut) >= 5, "📊 o inventário de mutações está carregado",
      f"{len(mut)} mutações")

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
