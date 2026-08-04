"""O aviso de que o Atlas mudou precisa CHEGAR — e ele nunca chegou.

O que a auditoria encontrou
----------------------------
📊 04/08/2026, `backend/app/services/atlas/route_sentinel.py`:

```python
integ = svc.get_platform_whatsapp_integration()   # sem argumento
```

E a assinatura é `get_platform_whatsapp_integration(self, company_id: str)`.

**Todo disparo levantava `TypeError`**, o `except` logo abaixo engolia, e o
alerta de *"o menu da seguradora mudou de forma que exige revisão"* **nunca
chegou ao Founder — nem uma vez.**

Por que isso importa AGORA
---------------------------
O Founder pediu, com todas as letras:

> *"As rotas também precisam ser melhoradas se tiver alguma coisa nova. Mas não
> pode ter entendimento errado ou criar rotas erradas ou estragar rotas do Atlas
> que estão certas. Garanta que as descobertas e melhorias sejam sempre
> respeitadas — e o Atlas seja melhorado e nunca piorado."*

Duas coisas protegem isso, e só uma delas estava funcionando:

📊 **A primeira funciona:** o Atlas acumula e versiona. `ura_maps` tem **253**
mapas `superseded` preservados contra 10 `observed` vivos, e o Tecelão declara
*"merge ACUMULATIVO… ambíguo não é chutado — vira aresta inferida de baixa
confiança"*. O que estava certo não é apagado.

🔴 **A segunda estava morta:** quando a estrutura muda de um jeito que exige
**revisão humana**, alguém tem de ser avisado. Esse alguém nunca soube.

Com os WhatsApps das corretoras conectando, conversas novas vão remodelar rotas.
Sem este aviso, uma mudança que precisa de olho humano passa em silêncio — e a
diferença entre "o Atlas aprendeu" e "o Atlas se confundiu" só uma pessoa vê.

A regra que este arquivo guarda
--------------------------------
> **Um alerta que não sai não é alerta.** E um `except` que engole a falha do
> alerta transforma "ninguém foi avisado" em "tudo certo".
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []
METODO = "get_platform_whatsapp_integration"


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _arvores():
    base = os.path.join(RAIZ, "backend", "app")
    for pasta, _, arquivos in os.walk(base):
        for arq in arquivos:
            if not arq.endswith(".py"):
                continue
            caminho = os.path.join(pasta, arq)
            try:
                yield caminho, ast.parse(open(caminho, encoding="utf-8").read())
            except SyntaxError:
                continue


# ---------------------------------------------------------------------------

def teste_ninguem_pede_canal_sem_dizer_de_quem():
    print("\n[1] Ninguém pede o canal de plataforma sem dizer de qual corretora")

    culpados: list[str] = []
    chamadas = 0
    for caminho, arvore in _arvores():
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                    and no.func.attr == METODO):
                chamadas += 1
                if not no.args and not no.keywords:
                    culpados.append(f"{os.path.relpath(caminho, RAIZ)}:{no.lineno}")

    checar(chamadas > 0, "o teste encontrou chamadas para conferir",
           "zero significa que o detector parou de enxergar")
    checar(not culpados, f"todas as {chamadas} chamadas passam a corretora",
           f"sem argumento: {culpados} — cada uma é um alerta que nunca sai")


def teste_a_sentinela_resolve_o_canal_dela():
    print("\n[2] A Sentinela do Atlas tem como achar um canal")
    caminho = os.path.join(RAIZ, "backend", "app", "services", "atlas", "route_sentinel.py")
    fonte = open(caminho, encoding="utf-8").read()
    arvore = ast.parse(fonte)

    resolvedor = next((n for n in ast.walk(arvore)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and n.name == "_canal_de_plataforma"), None)
    checar(resolvedor is not None, "existe um resolvedor de canal",
           "o Atlas é global — a rota é da seguradora, não de uma corretora, "
           "então não há company_id no escopo para passar")

    alerta = next((n for n in ast.walk(arvore)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == "_alert_founder"), None)
    checar(alerta is not None, "o alerta existe")
    if alerta is None:
        return

    chamadas = [f.func.id for f in ast.walk(alerta)
                if isinstance(f, ast.Call) and isinstance(f.func, ast.Name)]
    checar("_canal_de_plataforma" in chamadas, "e o alerta usa o resolvedor")

    # 🔴 O `except` não pode voltar a transformar "não saiu" em silêncio total.
    trecho = ast.get_source_segment(fonte, alerta) or ""
    checar("SEM canal" in trecho or "não saiu" in trecho,
           "e quando não há canal, isso é REGISTRADO",
           "silêncio sobre o silêncio foi como este defeito durou tanto")


def teste_o_observador_continua_proibido_de_falar():
    print("\n[3] CONTROLE — o resolvedor NÃO pode furar a regra do silêncio")
    caminho = os.path.join(RAIZ, "backend", "app", "services", "atlas", "route_sentinel.py")
    fonte = open(caminho, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    resolvedor = next((n for n in ast.walk(arvore)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and n.name == "_canal_de_plataforma"), None)
    if resolvedor is None:
        checar(False, "o resolvedor existe")
        return

    chamadas = [f.func.attr for f in ast.walk(resolvedor)
                if isinstance(f, ast.Call) and isinstance(f.func, ast.Attribute)]
    # Ele tem de passar pelo mesmo portão de sempre, que já aplica `pode_enviar`
    # e nunca devolve o número do observador.
    checar(METODO in chamadas,
           "o resolvedor passa pelo portão que aplica `pode_enviar`",
           "consultar `integrations` na mão pegaria o observador, que deve calar")

    # E o portão realmente aplica.
    servico = open(os.path.join(RAIZ, "backend", "app", "services",
                                "integration_service.py"), encoding="utf-8").read()
    corpo = servico.split(f"def {METODO}", 1)[-1].split("\n    def ", 1)[0]
    checar("pode_enviar" in corpo,
           "CONTROLE — e o portão continua aplicando `pode_enviar`",
           "se um dia parar, este alerta sairia pelo número que deve ficar mudo")


def teste_o_atlas_acumula_em_vez_de_substituir():
    print("\n[4] O Atlas melhora sem apagar o que estava certo")
    tecelao = open(os.path.join(RAIZ, "backend", "app", "services", "atlas",
                                "weaver.py"), encoding="utf-8").read()

    checar("Merge ACUMULATIVO" in tecelao or "acumulativo" in tecelao.lower(),
           "o Tecelão declara merge acumulativo",
           "substituir apagaria descoberta boa a cada nova conversa")
    checar("ambíguo não é chutado" in tecelao or "ambiguo nao e chutado" in tecelao,
           "e recusa chutar o que está ambíguo",
           "chutar é como uma rota certa vira uma rota errada")

    # CONTRAPROVA do detector: ele TEM de acusar um arquivo que não diz isso.
    checar("Merge ACUMULATIVO" not in open(
        os.path.join(RAIZ, "backend", "app", "services", "atlas",
                     "route_sentinel.py"), encoding="utf-8").read(),
        "CONTRAPROVA — o detector não acha a frase em qualquer arquivo",
        "se achasse, o caso [4] passaria por acidente")


def main() -> int:
    print("=" * 70)
    print("O ALERTA QUE NAO SAI NAO E ALERTA")
    print("=" * 70)
    for teste in (teste_ninguem_pede_canal_sem_dizer_de_quem,
                  teste_a_sentinela_resolve_o_canal_dela,
                  teste_o_observador_continua_proibido_de_falar,
                  teste_o_atlas_acumula_em_vez_de_substituir):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O ATLAS MELHORA, E QUEM PRECISA REVISAR FICA SABENDO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
