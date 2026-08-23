# -*- coding: utf-8 -*-
"""🔴 A TECLA CERTA NA FORMA ERRADA É UMA TECLA QUE NÃO EXISTE.

📊 23/08/2026, ONDA C. Duas derivações devolviam **número** para telas que não
têm número nenhum:

```
pane_detalhe_opcao      hdi + yelum   "5"  ->  a tela é LISTA: "Problemas no motor"
pneus_quantidade_opcao  hdi + yelum   "1"  ->  a tela é BOTÃO: "Apenas um pneu"
```

🔴 E o que a URA faz com isso está no próprio acervo:

> *"Não entendi. Lembre-se que, para responder, você precisa selecionar o botão
> indicando a opção escolhida."*

A sessão que recebeu essa tela (`697abd09`) terminou em *"vamos te encaminhar
para um de nossos analistas"*. **Formato errado não é resposta ruim: é
atendimento perdido** — e o corredor não percebe, porque para ele a tecla foi
enviada.

⚠️ E era invisível para todos os outros guardas: a derivação ACERTAVA a
decisão (era mesmo o motor, era mesmo um pneu só). Só a FORMA estava errada, e
nenhum item da régua olha para a forma.

🔴 Este guarda não confere as duas que já foram consertadas — ele confere
**todas**, e a cada derivação nova. É a diferença entre corrigir um caso e
fechar a porta da classe inteira.

⚠️ A convenção de cada seguradora é medida no PRÓPRIO corredor: se as respostas
constantes dele são majoritariamente números, ele é numerado; se são rótulos,
ele é de rótulo. Não há lista escrita à mão para divergir do código.
"""

from __future__ import annotations

import ast
import collections
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import importlib.util as _ilu  # noqa: E402


def _mod(nome, arquivo):
    sp = _ilu.spec_from_file_location(
        nome, os.path.join(RAIZ, "app", "services", arquivo))
    m = _ilu.module_from_spec(sp)
    sys.modules[nome] = m
    sp.loader.exec_module(m)
    return m


CP = _mod("app.services.corridor_playbooks", "corridor_playbooks.py")
IDS = _mod("app.services.insurer_dispatch_service", "insurer_dispatch_service.py")

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _forma(valor: str) -> str:
    return "numero" if re.fullmatch(r"\d+", str(valor).strip()) else "rotulo"


def convencao_do_corredor(pb) -> str:
    """Numerado ou de rótulo — medido nas respostas CONSTANTES do próprio."""
    num = rot = 0
    for p in pb.get("ura_steps") or []:
        r = str(p.get("reply") or "")
        if not r or "{" in r:
            continue
        (num, rot) = (num + 1, rot) if _forma(r) == "numero" else (num, rot + 1)
    return "numero" if num > rot else "rotulo"


CONV = {ref: convencao_do_corredor(pb) for ref, pb in CP._PLAYBOOKS.items()}


def valores_derivados():
    """`{slot: {valores literais que a derivação atribui}}`, lidos da FONTE.

    ⚠️ Lido do código, não de uma cópia: uma lista escrita à mão aqui seria a
    segunda verdade que diverge na próxima edição (§9.4).
    """
    # ⚠️ 🔴 POR AST, NAO POR REGEX DE LINHA. A primeira versao deste leitor
    #    usava `slots["x_opcao"] = (.+)` e lia so o RESTO DA LINHA — entao uma
    #    atribuicao quebrada em duas linhas
    #
    #        slots["pneus_quantidade_opcao"] = (
    #            "Mais de um pneu" if varios else "Apenas um pneu")
    #
    #    devolvia ZERO valores, e a tecla saia da auditoria em silencio.
    #    🔴 Um guarda que perde o caso por causa de uma quebra de linha e pior
    #       que guarda nenhum: ele da o VERDE. Foi assim que ele nasceu, e por
    #       isso a leitura agora e estrutural.
    caminho = os.path.join(RAIZ, "app", "services", "insurer_dispatch_service.py")
    arvore = ast.parse(open(caminho, encoding="utf-8").read())
    fora = collections.defaultdict(set)
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.FunctionDef)
                and no.name == "_derivar_teclas_do_caso"):
            continue
        for filho in ast.walk(no):
            if not isinstance(filho, ast.Assign):
                continue
            for alvo in filho.targets:
                if not (isinstance(alvo, ast.Subscript)
                        and isinstance(alvo.value, ast.Name)
                        and alvo.value.id == "slots"
                        and isinstance(alvo.slice, ast.Constant)
                        and str(alvo.slice.value).endswith("_opcao")):
                    continue
                for v in ast.walk(filho.value):
                    if (isinstance(v, ast.Constant)
                            and isinstance(v.value, str) and v.value):
                        fora[str(alvo.slice.value)].add(v.value)
    return fora


def donos(slot):
    """Os corredores que EXIGEM esta tecla."""
    return {ref for ref, pb in CP._PLAYBOOKS.items()
            for p in (pb.get("ura_steps") or [])
            if slot in (p.get("requires") or [])
            or str(p.get("reply") or "") == "{" + slot + "}"}


def conflitos(valores):
    fora = []
    for slot, vals in sorted(valores.items()):
        formas = {_forma(v) for v in vals}
        ds = donos(slot)
        if not ds:
            continue
        for ref in sorted(ds):
            if CONV[ref] not in formas:
                fora.append((slot, ref, sorted(formas), CONV[ref], sorted(vals)[:3]))
    return fora


VALORES = valores_derivados()

print("=" * 74)
print("[1] A AUDITORIA TEM MATÉRIA — e ela é grande o bastante para valer")
print("=" * 74)

certo(len(VALORES) >= 15,
      "📊 a derivação preenche teclas suficientes para a auditoria valer",
      f"{len(VALORES)} teclas: {sorted(VALORES)[:6]}...")
certo(len({c for c in CONV.values()}) == 2,
      "📊 e o produto TEM as duas convenções — senão a pergunta seria vazia",
      f"{collections.Counter(CONV.values())}")

print()
print("=" * 74)
print("[2] 🔴 NENHUMA TECLA DERIVADA SAI NA FORMA ERRADA")
print("=" * 74)

RUINS = conflitos(VALORES)
for slot, ref, formas, conv, exemplos in RUINS:
    print(f"        🔴 {slot} -> {formas} mas `{ref}` é de {conv}: {exemplos}")
certo(not RUINS,
      "🔴 toda tecla derivada sai na forma que a seguradora dona entende",
      f"{len(RUINS)} conflito(s)")

# 🔴 As duas que motivaram este guarda, nomeadas — para que um conserto que as
#    desfaça caia com o nome delas, e não numa contagem genérica.
for slot, esperado in (("pane_detalhe_opcao", "Problemas no motor"),
                       ("pneus_quantidade_opcao", "Apenas um pneu")):
    certo(esperado in VALORES.get(slot, set()),
          f"🔴 `{slot}` responde pelo RÓTULO — a tela não tem número",
          f"valores: {sorted(VALORES.get(slot, set()))[:4]}")

print()
print("=" * 74)
print("[3] 🔴 O CONTROLE: esta auditoria CONSEGUE acusar")
print("=" * 74)
print("     (um guarda que não tem como falhar não guarda nada — §9.3)")

# 🔴 Injeta um conflito FABRICADO: `pane_detalhe_opcao` valendo "5" num
#    corredor de rótulo. Se a auditoria não acusar isto, ela não acusaria o
#    defeito real — e o verde de cima não valeria nada.
FALSO = {k: set(v) for k, v in VALORES.items()}
FALSO["pane_detalhe_opcao"] = {"5"}
acusa = conflitos(FALSO)
certo(any(c[0] == "pane_detalhe_opcao" for c in acusa),
      "🔴 CONTROLE: com o número de volta, a auditoria ACUSA",
      f"acusou {[c[0] for c in acusa]}")

# 🔴 CONTROLE DO CONTROLE: e ela NÃO acusa o corredor numerado, que está certo.
FALSO2 = {k: set(v) for k, v in VALORES.items()}
FALSO2["problema_eletrico_opcao"] = {"1"}
certo(not any(c[0] == "problema_eletrico_opcao" for c in conflitos(FALSO2)),
      "🔴 CONTROLE: e o número CONTINUA certo onde a URA é numerada — a "
      "auditoria não é uma cruzada contra números")

print()
print("=" * 74)
print("[4] E o MOTOR devolve mesmo o que a auditoria leu na fonte")
print("=" * 74)

# 🔴 §9.4: a auditoria acima lê a FONTE. Esta parte chama a função.
for relato, slot, esperado in (
        ("furei um pneu na br-101", "pneus_quantidade_opcao", "Apenas um pneu"),
        ("furei dois pneus no buraco", "pneus_quantidade_opcao", "Mais de um pneu"),
        ("o motor está falhando e batendo pino", "pane_detalhe_opcao",
         "Problemas no motor"),
        ("o carro parou e eu não sei o que é", "pane_detalhe_opcao", "Não sei")):
    d = {"problema_descricao": relato}
    IDS._derivar_teclas_do_caso(d)
    certo(d.get(slot) == esperado, f"{slot} <- {relato[:34]!r} = {esperado!r}",
          f"veio {d.get(slot)!r}")

# 🔴 CONTROLE: a MESMA decisão, na forma NUMÉRICA, para quem é numerado.
d = {"problema_descricao": "furei dois pneus no buraco"}
IDS._derivar_teclas_do_caso(d)
certo(d.get("pneus_furados_opcao") == "2",
      "🔴 CONTROLE: a alfa/allianz recebem a MESMA decisão em NÚMERO — a "
      "decisão é uma só, o que muda é a forma", f"veio {d.get('pneus_furados_opcao')!r}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
