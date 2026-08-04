"""O WhatsApp de uma corretora nunca resolve para a instância de outra.

O que a auditoria de 04/08/2026 encontrou
------------------------------------------
`_go_resolve` — a função que responde *"qual instância do Evolution Go é desta
corretora?"* — tinha uma rede de segurança que cruzava tenant:

```python
row = await _go_company_channel(company_id, purpose)   # a linha DELA
if row: return row
...
env = _go_env_fallback()                               # a instância GLOBAL
if env: return env
```

📊 `EVOLUTION_GO_INSTANCE_NAME` tem como padrão **`autobrokers-go-teste`** — que
é o nome da linha de attendance **da Resulta**, criada em 15/07.

📊 E a **AutoFleet não tem linha de attendance nenhuma.** Que não é uma anomalia:
é o estado natural de *toda* corretora antes do primeiro pareamento.

> Abrir a tela de WhatsApp da AutoFleet resolvia para a instância da Resulta.
> Status, QR e — o pior — **disconnect**.

E havia um segundo caminho, em `_go_setup`: sem `EVOLUTION_GO_GLOBAL_KEY`, o
pareamento de attendance usava a instância global **e gravava aquele nome na
linha da corretora**. Duas corretoras apontando para o mesmo WhatsApp, com as
conversas das duas no mesmo lugar.

CLAUDE.md §7 não admite exceção. Um fallback que escolhe a instância de outra
empresa quando não acha a sua não é tolerância a falha — é a falha.

Por que este teste lê a ÁRVORE, e não o texto
----------------------------------------------
Procurar `"_go_env_fallback"` como substring acusaria o próprio comentário que
explica por que ela foi aposentada — e reprovaria a documentação por estar
correta. Já me aconteceu duas vezes hoje.

Aqui o arquivo é lido com `ast`: só conta **chamada de verdade**. Comentário,
docstring e menção em string não existem para a árvore.

E o caso [3] é o controle que dá direito à conclusão: a função **continua
existindo**. Apagá-la deixaria o teste da SPEC-047 — que confere o NOME dela
para afirmar que o `env` virou legado — verde por ausência, que é a pior forma
de verde.
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALVO = os.path.join(RAIZ, "backend", "app", "api", "whatsapp_channel.py")
PROIBIDA = "_go_env_fallback"

FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _arvore(caminho: str) -> ast.Module:
    with open(caminho, encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _chamadas(no: ast.AST) -> list[str]:
    """Nomes efetivamente CHAMADOS dentro de um nó. Só `f(...)`."""
    nomes = []
    for filho in ast.walk(no):
        if isinstance(filho, ast.Call):
            alvo = filho.func
            if isinstance(alvo, ast.Name):
                nomes.append(alvo.id)
            elif isinstance(alvo, ast.Attribute):
                nomes.append(alvo.attr)
    return nomes


def _funcao(arvore: ast.Module, nome: str):
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    return None


# ---------------------------------------------------------------------------

def teste_ninguem_chama_a_instancia_global():
    print("\n[1] Nenhuma função chama a instância global do ambiente")
    arvore = _arvore(ALVO)

    culpadas = []
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if no.name == PROIBIDA:
                continue  # a própria definição
            if PROIBIDA in _chamadas(no):
                culpadas.append(f"{no.name}:{no.lineno}")
    checar(not culpadas, "nenhuma função chama _go_env_fallback",
           f"chamam: {culpadas} — cada uma é um caminho de cruzamento de tenant")

    # E o repositório inteiro: ninguém mais pode importá-la.
    outros = []
    for pasta, _, arquivos in os.walk(os.path.join(RAIZ, "backend", "app")):
        for arq in arquivos:
            if not arq.endswith(".py"):
                continue
            caminho = os.path.join(pasta, arq)
            if os.path.abspath(caminho) == os.path.abspath(ALVO):
                continue
            try:
                sub = _arvore(caminho)
            except SyntaxError:
                continue
            if PROIBIDA in _chamadas(sub):
                outros.append(os.path.relpath(caminho, RAIZ))
    checar(not outros, "nenhum outro módulo a chama", f"{outros}")


def teste_sem_linha_da_corretora_e_404_para_os_dois():
    print("\n[2] Sem linha ativa da corretora: 404, para attendance E observer")
    arvore = _arvore(ALVO)
    resolve = _funcao(arvore, "_go_resolve")
    checar(resolve is not None, "_go_resolve existe")
    if resolve is None:
        return

    # Todo caminho de saída sem linha tem de LEVANTAR, nunca devolver instância.
    levanta = [n for n in ast.walk(resolve) if isinstance(n, ast.Raise)]
    checar(bool(levanta), "_go_resolve levanta quando não acha a linha")
    checar(PROIBIDA not in _chamadas(resolve),
           "_go_resolve NÃO consulta a instância global",
           "era daqui que a AutoFleet caía na instância da Resulta")

    # O `attendance` não pode mais ter tratamento diferente do `observer`. A
    # assimetria era o defeito: observer dava 404 e attendance dava a instância
    # de outra empresa.
    fonte = ast.get_source_segment(open(ALVO, encoding="utf-8").read(), resolve) or ""
    corpo = "\n".join(l for l in fonte.split("\n")
                      if not l.strip().startswith("#") and '"""' not in l)
    checar("attendance_channel_not_paired" in corpo and "observer_channel_not_paired" in corpo,
           "os dois propósitos têm o mesmo desfecho: não pareado",
           corpo[-200:])


def teste_o_pareamento_nao_compartilha_instancia():
    print("\n[3] Parear sem chave global é 503 — nunca instância compartilhada")
    with open(ALVO, encoding="utf-8") as fh:
        fonte = fh.read()
    arvore = _arvore(ALVO)
    setup = _funcao(arvore, "_go_setup")
    checar(setup is not None, "_go_setup existe")
    if setup is None:
        return

    checar(PROIBIDA not in _chamadas(setup),
           "_go_setup NÃO usa a instância global",
           "gravava o nome global na linha da corretora — duas empresas, um WhatsApp")

    trecho = ast.get_source_segment(fonte, setup) or ""
    checar("EVOLUTION_GO_GLOBAL_KEY" in trecho,
           "e a mensagem de erro diz o que configurar",
           "503 mudo faz o Founder achar que quebrou, não que falta chave")


def teste_o_controle_a_funcao_continua_existindo():
    print("\n[4] CONTROLE — a função continua existindo (verde por ausência é pior)")
    arvore = _arvore(ALVO)
    checar(_funcao(arvore, PROIBIDA) is not None,
           "_go_env_fallback ainda está declarada",
           "o teste da SPEC-047 confere o NOME dela para afirmar que o env "
           "virou legado; apagá-la deixaria aquele teste verde por ausência")

    # CONTRAPROVA do detector: ele TEM de acusar uma chamada de verdade. Sem
    # isto, um detector quebrado passaria neste arquivo inteiro.
    falso = ast.parse("def f():\n    return _go_env_fallback()\n")
    checar(PROIBIDA in _chamadas(_funcao(falso, "f")),
           "CONTRAPROVA — o detector acusa uma chamada real",
           "prova que o silêncio do caso [1] vem de não haver chamada")

    # E que ele NÃO acusa menção em comentário/docstring — o erro que eu já
    # cometi duas vezes hoje, reprovando código correto por causa do texto.
    so_texto = ast.parse('def g():\n    """fala de _go_env_fallback."""\n    x = "_go_env_fallback"\n    return x\n')
    checar(PROIBIDA not in _chamadas(_funcao(so_texto, "g")),
           "CONTRAPROVA — comentário e string NÃO contam como chamada")


def teste_o_caminho_feliz_continua_de_pe():
    print("\n[5] CONTROLE — quem TEM linha ativa continua sendo resolvido")
    arvore = _arvore(ALVO)
    canal = _funcao(arvore, "_go_company_channel")
    checar(canal is not None, "_go_company_channel existe")
    if canal is None:
        return

    fonte = open(ALVO, encoding="utf-8").read()
    trecho = ast.get_source_segment(fonte, canal) or ""
    # A consulta tem de continuar amarrada na corretora e no propósito.
    for exigido, porque in (('"company_id", company_id', "filtra pela corretora"),
                            ('"purpose"', "filtra pelo propósito"),
                            ('"is_active", True', "só linha ativa")):
        checar(exigido in trecho, f"a consulta {porque}", exigido)

    resolve = _funcao(arvore, "_go_resolve")
    checar("_go_company_channel" in _chamadas(resolve),
           "e _go_resolve continua consultando a linha da corretora",
           "fechar o fallback não pode ter fechado o caminho certo junto")


def main() -> int:
    print("=" * 70)
    print("O CANAL DE UMA CORRETORA NAO E DE OUTRA")
    print("=" * 70)
    for teste in (teste_ninguem_chama_a_instancia_global,
                  teste_sem_linha_da_corretora_e_404_para_os_dois,
                  teste_o_pareamento_nao_compartilha_instancia,
                  teste_o_controle_a_funcao_continua_existindo,
                  teste_o_caminho_feliz_continua_de_pe):
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
    print("NENHUMA CORRETORA OPERA O WHATSAPP DE OUTRA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
