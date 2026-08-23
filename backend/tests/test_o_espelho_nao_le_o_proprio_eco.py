# -*- coding: utf-8 -*-
"""🔴 C13 — O ESPELHO LIA O PRÓPRIO ECO E CHAMAVA DE PALAVRA DO CLIENTE.

📊 22/08/2026, auditando os apelidos do encanador. `tubulacao` marcava 3 vezes,
e as TRÊS eram isto:

```
o que vc ve nessa imagem?
[contexto visual — imagem enviada pelo cliente]:
a imagem mostra uma tubulação...
```

🔴 É **o próprio Claude descrevendo uma foto**, gravado como mensagem
`role='user'`. O Espelho contava a descrição que a IA escreveu como se fosse a
palavra do segurado — e o item da E8 pagava 4 pontos por isso.

⚠️ A segunda fonte é a mesma armadilha um nível acima: **tela de URA colada no
chat**. `hidraulica` marcava 6, e duas eram o menu da Porto colado.
📊 É exatamente o falso positivo que o C6 já nomeia (`lavadora` × "Lavadora de
louças") — movido do corpus para o Espelho.

⚠️ **E a contaminação é PEQUENA no total (13 textos distintos em 10.457) e
CONCENTRADA nos termos técnicos**, que são justamente os que viram apelido.
Filtrar 0,1% muda o veredito de vários apelidos — é por isso que a porcentagem
não é o número que importa.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M   # noqa: E402

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


print("=" * 74)
print("[1] O FILTRO EXISTE E RECONHECE AS DUAS FONTES DE ECO")
print("=" * 74)

certo(hasattr(M, "_e_eco"), "🔴 o leitor sabe distinguir eco de palavra de cliente")

# 📊 As frases REAIS que o acervo tinha, e o que cada uma é.
ECO = [
    ("o que vc ve nessa imagem? [contexto visual — imagem enviada pelo "
     "cliente]: a imagem mostra uma tubulacao", "a IA descrevendo uma foto"),
    ("como eu posso te ajudar? servicos para veiculo assistencia "
     "emergencial como: guincho, tecnico, chaveiro", "menu da URA colado"),
    ("vamos la! informe o tipo de servico: *1 -* servicos emergenciais",
     "menu da URA colado"),
]
for texto, oque in ECO:
    certo(M._e_eco(M._norm(texto)), f"🔴 reconhece: {oque}", texto[:60])

# 🔴 O CONTROLE que dá direito à conclusão: frase REAL de cliente NÃO é eco.
#    Sem esta metade, um filtro que apagasse tudo passaria igual.
CLIENTE = [
    "to com problema de vazamento",
    "estamos com um vazamento de torneira.",
    "meu carro nao esta pegando, acho que e a bateria",
    "preciso de um chaveiro, tranquei a chave dentro de casa",
]
for texto in CLIENTE:
    certo(not M._e_eco(M._norm(texto)),
          f"🔴 CONTROLE: NÃO é eco — {texto[:48]}")

print()
print("=" * 74)
print("[2] 📊 O EFEITO MEDIDO — e ele é concentrado, não diluído")
print("=" * 74)

if not M.tem_banco():
    print("  ⚠️ sem banco aqui — as contagens abaixo não rodam.")
else:
    esp = M.vocabulario_do_espelho(recarregar=True)
    certo(len(esp) > 10000, "📊 o Espelho segue com volume real",
          f"{len(esp)} mensagens")
    certo(not any(M._e_eco(t) for t in esp),
          "🔴 e NENHUMA mensagem de eco sobrou nele")

    # 📊 O caso que abriu o conserto: `tubulacao` era 3, e as 3 eram da IA.
    certo(sum(1 for t in esp if "tubulacao" in t) == 0,
          "🔴 `tubulacao` cai de 3 para ZERO — as três eram texto da IA",
          f"restaram {sum(1 for t in esp if 'tubulacao' in t)}")
    # 🔴 CONTROLE: e um termo com palavra REAL de cliente sobrevive.
    #    Se este caísse junto, o filtro seria censura, não procedência.
    n_vaz = sum(1 for t in esp if "vazamento" in t)
    certo(n_vaz >= 8,
          "🔴 CONTROLE: `vazamento` SOBREVIVE — o filtro é por procedência, "
          "não apaga o vocabulário",
          f"{n_vaz} mensagens (era 14, das quais 3 eram da IA)")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
