# -*- coding: utf-8 -*-
"""🔴 MEDIR UMA ROTA **ESCREVE** NO ARQUIVO DO CORREDOR — SPEC-084.1, C11.

> ## Duas medições ao mesmo tempo deixavam o produto com uma âncora MORTA.

`medir_rota.py` chama `verificar_mutacoes` em toda medição, e cada mutação
grava em `corridor_playbooks.py` e restaura. Uma medição sozinha é segura.

🔴 **Duas não eram.** 📊 Em 22/08/2026, quatro subagentes mediram rotas em
paralelo enquanto a sessão principal media outra. As restaurações correram umas
por cima das outras e o corredor ficou assim:

```
- "anchor": r"(?:informe|confirme) o n[úu]mero da residência"
+ "anchor": r"informe o n[úu]mero da residência"
```

⚠️ `confirme` é a redação que a URA **usa** — a mutação existe justamente para
provar isso. O produto ficou com a âncora morta, e só foi pego por um
`git status` de rotina.

📊 E um dos subagentes viu o sintoma sem saber a causa: *"esta listagem mostra 5
telas órfãs, mas a chamada anterior mostrou 3"*. Medição que muda de resposta
entre duas chamadas não é ruído — é a árvore se movendo debaixo de quem mede.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import verificar_mutacoes as VM   # noqa: E402

CORREDOR = os.path.join(RAIZ, "app", "services", "corridor_playbooks.py")
OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _hash(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


print("=" * 74)
print("[1] A TRAVA EXISTE E É DE ARQUIVO")
print("=" * 74)
print("     os concorrentes são PROCESSOS separados (subagente, sessão, CI):")
print("     um lock de thread não os enxergaria")

certo(hasattr(VM, "_TRAVA") and hasattr(VM, "_tomar_a_trava"),
      "🔴 o mutador tem trava exclusiva de arquivo", getattr(VM, "_TRAVA", None))
certo(not os.path.exists(VM._TRAVA),
      "📊 e ela está SOLTA agora (senão alguma medição morreu segurando)",
      VM._TRAVA)

print()
print("=" * 74)
print("[2] 🔴 O SEGUNDO ESPERA — não entra junto")
print("=" * 74)

fd = VM._tomar_a_trava()
try:
    erro = []

    def tentar():
        try:
            VM._tomar_a_trava(espera=1.0)
            erro.append("ENTROU")
        except VM.MutadorOcupado:
            erro.append("esperou e desistiu")
        except Exception as e:                      # noqa: BLE001
            erro.append(f"outro erro: {e!r}")

    t = threading.Thread(target=tentar)
    t.start()
    t.join(timeout=20)
    certo(erro == ["esperou e desistiu"],
          "🔴 com a trava tomada, a segunda medição NÃO entra",
          str(erro))
finally:
    VM._soltar_a_trava(fd)

certo(not os.path.exists(VM._TRAVA),
      "🔴 e a trava é devolvida no `finally` — nunca fica órfã")

print()
print("=" * 74)
print("[3] 🔴 O CONTROLE: duas medições DE VERDADE, ao mesmo tempo")
print("=" * 74)
print("     é a prova que importa — sem ela, o de cima testa só o cadeado")

h0 = _hash(CORREDOR)
CMD = [sys.executable, os.path.join(RAIZ, "scripts", "medir_rota.py"),
       "--seguradora", "allianz", "--ramo", "residencial",
       "--servico", "maquina_de_lavar", "--com-espelho"]
# ⚠️ `--com-espelho` nao e detalhe: sem ele a rota da 100/102 e o script
#    sai com 1, que e o VEREDITO "nao e AAA" -- nao um erro. Com o Espelho ela
#    e 106/106, e ai exit 0 volta a significar "rodou inteiro".
env = dict(os.environ, PYTHONIOENCODING="utf-8")
p1 = subprocess.Popen(CMD, cwd=RAIZ, env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
p2 = subprocess.Popen(CMD, cwd=RAIZ, env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
r1, r2 = p1.wait(), p2.wait()

certo(r1 == 0 and r2 == 0,
      "as duas medições concorrentes TERMINARAM sem erro", f"{r1} e {r2}")
certo(_hash(CORREDOR) == h0,
      "🔴 e o corredor saiu IDÊNTICO, byte a byte — nenhuma mutação vazou",
      "🔴 UMA MUTAÇÃO FICOU NO PRODUTO. Rode `git diff` no corredor AGORA.")
certo(not os.path.exists(VM._TRAVA),
      "🔴 e nenhum dos dois deixou a trava para trás")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
