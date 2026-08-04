"""Desconectar é uma pausa, não um esquecimento.

O incidente que este arquivo impede de acontecer de novo
---------------------------------------------------------
Em 29/07/2026 o Observador foi pareado com escopo largo e capturou **2.556
transcrições e 745 sessões de 630 contatos particulares** — porque o telefone
era um celular pessoal, e o padrão do sistema era ver tudo. Foi contido e
revertido no mesmo dia.

📊 Em 04/08/2026, auditando antes de duas corretoras REAIS parearem, a
repetição estava armada — e era pior, porque as duas cairiam em lados opostos
da **mesma ação**:

```
_persist_integration recebia   alert_target=(integration or {}).get(...)
e `integration` vinha de       _integration(), que filtra is_active=True

    AutoFleet   is_active=false  ->  sem memória  ->  setdefault
                                     ->  volta a "insurers_and_clients"
    Resulta     is_active=TRUE   ->  preserva     ->  segue "insurers_only"
```

A da esquerda é o celular que a Regina ia parear. A da direita é o da Saionara —
que baixaria **só conversa de seguradora**, exatamente o oposto do que o produto
precisa para a curadoria e as cartas.

Nenhuma das duas seria uma escolha. Seriam duas consequências acidentais de um
`is_active` num filtro.

O conserto — e o que eu decidi NÃO consertar
---------------------------------------------
**O que consertei: a memória.** `_escopo_lembrado` lê a última escolha de
QUALQUER linha da corretora, ligada ou não. Desconectar não apaga o que ela
decidiu que pode ser gravado.

**O que NÃO consertei: o padrão.** Cheguei a estreitá-lo e voltei atrás.

O argumento para estreitar é bom: o sistema não tem como saber se o telefone
pareado é o de trabalho de uma corretora ou o pessoal de alguém — 📊 não existe
tabela de segurados com telefone neste banco. E os dois erros não custam o
mesmo: gravar de MENOS é recuperável (📊 o `history_sync` reentregou 133 eventos
de 29/07–03/08 numa rajada de 6 minutos), gravar de MAIS não é.

Mas o argumento contra é de PRODUTO, e ele não é meu: com o escopo estreito,
sete dias de observação rendem **zero conversa de atendimento** — e é delas que
saem a curadoria e as cartas. `test_observador_silencio.py` defende isso, com
razão.

Estreitar sozinho seria reduzir escopo em silêncio para comprar segurança
(CLAUDE.md §11). Fica registrado em **P-84** como decisão do Founder, com os
dois custos escritos.

⚠️ E há um detalhe que só a medição mostra: 📊 hoje as TRÊS memórias dizem
`insurers_only` — porque foi assim que a **contenção** de 29/07 as deixou. Uma
emergência virou política sem ninguém decidir. Se ele parear amanhã sem tocar
nisso, nenhuma conversa de segurado será capturada.

O caso [4] é o controle do que EU fiz: prova que a memória não filtra por linha
ligada. Sem ele, a correção seria indistinguível do defeito.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

FALHAS: list[str] = []
ESTREITO = "insurers_only"
LARGO = "insurers_and_clients"


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# --------------------------------------------------------------------------
# Um banco de mentira que responde como o de verdade, para o teste exercitar a
# função REAL — não uma reescrita dela, que concordaria com o autor.
# --------------------------------------------------------------------------
class _Consulta:
    def __init__(self, linhas):
        self._linhas = list(linhas)

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        return _Consulta([l for l in self._linhas if l.get(campo) == valor])

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return type("R", (), {"data": self._linhas})()


def _instalar_banco(linhas):
    """Injeta `app.core.database.get_supabase_client` com as linhas dadas."""
    mod = types.ModuleType("app.core.database")

    class _Cliente:
        def table(self, _nome):
            return _Consulta(linhas)

    mod.get_supabase_client = lambda: type("S", (), {"client": _Cliente()})()
    sys.modules["app.core.database"] = mod


def _carregar():
    caminho = os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                           "pairing_orchestrator.py")
    spec = importlib.util.spec_from_file_location("_pairing_orq", caminho)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_pairing_orq"] = m
    spec.loader.exec_module(m)
    return m


ORQ = _carregar()


def _linha(escopo, ativa, criada):
    alvo = {"observer_scope": escopo, "observer_exclusions": [], "internal_numbers": []} if escopo else None
    return {"company_id": "empresa-1", "provider": "evolution-go", "purpose": "observer",
            "alert_target": alvo, "is_active": ativa, "created_at": criada}


def _lembrado(linhas):
    _instalar_banco(linhas)
    o = ORQ.PairingOrchestrator()
    return asyncio.run(o._escopo_lembrado("empresa-1", "observer"))


# ---------------------------------------------------------------------------

def teste_a_escolha_sobrevive_ao_botao_de_desconectar():
    print("\n[1] A escolha da corretora sobrevive a desconectar")

    # O caso da AutoFleet: escolheu o estreito, depois desconectou.
    lembrado = _lembrado([_linha(ESTREITO, False, "2026-07-29")])
    checar(bool(lembrado) and lembrado.get("observer_scope") == ESTREITO,
           "linha DESLIGADA ainda é memória da escolha",
           f"lembrou={lembrado} — era daqui que a Regina voltaria a gravar tudo")

    # E o caso da Resulta: ligada, escolha preservada do mesmo jeito.
    lembrado = _lembrado([_linha(ESTREITO, True, "2026-07-23")])
    checar(bool(lembrado) and lembrado.get("observer_scope") == ESTREITO,
           "linha LIGADA continua sendo memória",
           "consertar o desligado não pode ter quebrado o ligado")

    # A mais RECENTE vence: quem mudou de ideia mudou de ideia.
    lembrado = _lembrado([_linha(LARGO, False, "2026-08-01"),
                          _linha(ESTREITO, False, "2026-07-01")])
    checar(lembrado.get("observer_scope") == LARGO,
           "entre duas memórias, vale a mais recente",
           f"lembrou={lembrado}")


def teste_ausencia_nao_e_escolha():
    print("\n[2] Linha sem escopo declarado NÃO apaga a escolha anterior")

    # Uma linha nova sem `alert_target` (é como nascem as de attendance) não
    # pode sobrescrever uma escolha explícita mais antiga. Ausência é ausência.
    lembrado = _lembrado([_linha(None, True, "2026-08-04"),
                          _linha(ESTREITO, False, "2026-07-23")])
    checar(bool(lembrado) and lembrado.get("observer_scope") == ESTREITO,
           "linha sem escopo é pulada; a escolha anterior vale",
           f"lembrou={lembrado}")

    # Sem memória nenhuma: devolve None, e aí o padrão decide (caso [3]).
    checar(_lembrado([]) is None, "corretora nova não tem memória")
    checar(_lembrado([_linha(None, True, "2026-08-04")]) is None,
           "linha sem escopo nenhum também não é memória")


def teste_o_padrao_e_uma_decisao_do_founder():
    print("\n[3] O padrão continua o LARGO — e isso é decisão do Founder")
    fonte = open(os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                              "pairing_orchestrator.py"), encoding="utf-8").read()
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    # Eu tentei estreitar isto e voltei atrás. O argumento contra é de PRODUTO:
    # 📊 com o estreito, sete dias de observação rendem ZERO conversa de
    # atendimento — e é delas que saem a curadoria e as cartas. Estreitar por
    # conta própria seria reduzir escopo em silêncio para comprar segurança.
    checar(f'setdefault("observer_scope", "{LARGO}")' in comandos,
           "o padrão do pareamento continua o largo",
           "estreitar sozinho reduziria escopo em silêncio (CLAUDE.md §11)")
    checar("_escopo_lembrado" in comandos,
           "e o que EU podia consertar está consertado: a escolha é lembrada",
           "sem memória, o escopo era decidido por um `is_active` num filtro")


def teste_a_memoria_nao_filtra_por_ligado():
    print("\n[4] CONTROLE — a busca da memória NÃO filtra `is_active`")
    import ast

    fonte = open(os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                              "pairing_orchestrator.py"), encoding="utf-8").read()
    arvore = ast.parse(fonte)
    alvo = next((n for n in ast.walk(arvore)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == "_escopo_lembrado"), None)
    checar(alvo is not None, "_escopo_lembrado existe")
    if alvo is None:
        return

    # O que importa é o FILTRO, não a menção. A primeira versão deste guarda
    # procurava a palavra `is_active` e reprovava porque ela está no `select`,
    # onde serve para INSPECIONAR a coluna. Ler a coluna é certo; filtrar por
    # ela é o defeito. Terceira vez hoje que um detector meu confunde texto com
    # regra — por isso aqui ele lê a árvore e olha só os `.eq(...)`.
    filtros = []
    for no in ast.walk(alvo):
        if (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                and no.func.attr == "eq" and no.args):
            primeiro = no.args[0]
            if isinstance(primeiro, ast.Constant):
                filtros.append(primeiro.value)
    checar("is_active" not in filtros,
           "a consulta da memória não FILTRA por linha ligada",
           f"filtra por: {filtros} — esse filtro era o defeito inteiro")
    checar("company_id" in filtros and "purpose" in filtros,
           "CONTROLE — mas continua filtrando por corretora e propósito",
           f"filtra por: {filtros} — sem isso, a escolha de uma vazaria para outra")

    # CONTRAPROVA do teste: com o filtro de volta, o caso [1] TEM de quebrar.
    # Aqui a prova é direta — o banco de mentira devolve só linha desligada, e
    # a função ainda assim encontra a memória.
    checar(_lembrado([_linha(ESTREITO, False, "2026-07-29")]) is not None,
           "CONTRAPROVA — só com linha desligada, a memória ainda é achada",
           "se um dia voltar a filtrar, este caso fica None e reprova")


def teste_o_persist_usa_a_memoria():
    print("\n[5] E o pareamento realmente CONSULTA a memória")
    import ast

    fonte = open(os.path.join(RAIZ, "backend", "app", "services", "whatsapp",
                              "pairing_orchestrator.py"), encoding="utf-8").read()
    comandos = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("_escopo_lembrado(company_id, purpose)" in comandos,
           "o fluxo de pareamento chama a memória",
           "função que ninguém chama não protege nada")
    # E ela vem ANTES do fallback antigo, senão o antigo continua mandando.
    i_mem = comandos.find("_escopo_lembrado(company_id, purpose)")
    i_velho = comandos.find('(integration or {}).get("alert_target")')
    checar(0 < i_mem < i_velho,
           "e a memória tem precedência sobre a busca que filtra `is_active`",
           f"memoria={i_mem} antigo={i_velho}")


def main() -> int:
    print("=" * 70)
    print("DESCONECTAR NAO APAGA A ESCOLHA DO ESCOPO")
    print("=" * 70)
    for teste in (teste_a_escolha_sobrevive_ao_botao_de_desconectar,
                  teste_ausencia_nao_e_escolha,
                  teste_o_padrao_e_uma_decisao_do_founder,
                  teste_a_memoria_nao_filtra_por_ligado,
                  teste_o_persist_usa_a_memoria):
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
    print("A CORRETORA DECIDE O QUE PODE SER GRAVADO, E O SISTEMA LEMBRA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
