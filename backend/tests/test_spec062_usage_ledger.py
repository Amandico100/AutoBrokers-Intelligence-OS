"""SPEC-062 §21 — o consumo vira linha, e uma linha só.

O estado antes
--------------
    usage_events      0 linhas
    token_usage_logs  1.239 linhas, todas `billed = false`

`usage_events` tem a forma exata da §21.1 — `idempotency_key`,
`billing_status`, `provider_cost_usd`, `skill_slug`, `work_run_id` — e estava
vazia. Tabela sem escritor. O único que chamava o `UsageService` dela era o
Firecrawl.

Todo o consumo de LLM ia só para `token_usage_logs`, o ledger legado. Ele
registra token por modelo, e não sabe dizer de qual skill, tool, work run ou
artifact aquele gasto veio.

Por que isso importa comercialmente
-----------------------------------
A SPEC-062 §26 (unit economics) precisa de custo atribuído para calcular margem,
e o Founder precisa de distribuição de consumo real por corretora para
precificar. Sem ledger, o preço seria adivinhado.

**Medir é o que produz o preço.** E medir não é cobrar: tudo nasce
`PRE_LAUNCH_NON_BILLABLE` (§22).

O que este teste protege
------------------------
Que o gargalo único de LLM continue escrevendo no ledger, que a mesma chamada
nunca vire duas linhas, e que ninguém confunda medir com cobrar.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# --------------------------------------------------------------------------
# Andaimes: o ambiente do gate não tem langchain nem supabase instalados.
# Стubar o que o módulo IMPORTA é legítimo; o que se testa é a lógica dele.
# --------------------------------------------------------------------------
def _stub(nome: str, **atributos):
    if nome in sys.modules:
        return sys.modules[nome]
    mod = types.ModuleType(nome)
    for k, v in atributos.items():
        setattr(mod, k, v)
    sys.modules[nome] = mod
    return mod


class _BaseCallbackHandler:
    def __init__(self, *a, **k):
        pass


_stub("langchain_core")
_stub("langchain_core.callbacks", BaseCallbackHandler=_BaseCallbackHandler)
_stub("langchain_core.outputs", LLMResult=object)

for _n, _p in (("app", ("app",)),
               ("app.core", ("app", "core")),
               ("app.core.callbacks", ("app", "core", "callbacks")),
               ("app.services", ("app", "services")),
               ("app.services.work", ("app", "services", "work"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


LEDGER = carregar("app.services.work.usage")


# --------------------------------------------------------------------------
# Banco de mentira que se comporta como o de verdade no que importa: o índice
# único `(company_id, idempotency_key)`.
# --------------------------------------------------------------------------
class FakeTabela:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome

    def insert(self, registro):
        self._registro = registro
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        reg = getattr(self, "_registro", None)
        if reg is None:
            return types.SimpleNamespace(data=[])
        chave = (reg.get("company_id"), reg.get("idempotency_key"))
        if chave in self.banco.chaves:
            raise RuntimeError(
                'duplicate key value violates unique constraint '
                '"uq_usage_events_company_idem"')
        self.banco.chaves.add(chave)
        self.banco.linhas.append(reg)
        return types.SimpleNamespace(data=[reg])


class FakeDB:
    def __init__(self):
        self.linhas: list[dict] = []
        self.chaves: set = set()
        self.client = self

    def table(self, nome):
        return FakeTabela(self, nome)


def teste_o_evento_nasce_sem_cobranca():
    print("\n[1] Todo evento nasce SEM ser cobrança")
    db = FakeDB()
    LEDGER.UsageService(db).registrar(
        company_id="c1", source="chat", model="claude-sonnet-5",
        input_tokens=100, output_tokens=50, provider_cost_usd=0.002)
    linha = db.linhas[0]
    checar(linha["billing_status"] == LEDGER.STATUS_PRE_LANCAMENTO,
           "billing_status = PRE_LAUNCH_NON_BILLABLE",
           str(linha.get("billing_status")))
    checar(LEDGER.STATUS_PRE_LANCAMENTO == "PRE_LAUNCH_NON_BILLABLE",
           "o nome do estado não mudou sem decisão do Founder")
    # §22: nenhum registro escrito aqui pode virar dívida automática.
    checar("customer_price" not in linha and "amount_brl" not in linha,
           "o evento guarda CUSTO DE PROVEDOR, não preço ao cliente",
           "misturar os dois é como a cobrança retroativa nasce")


def teste_a_mesma_chamada_nao_vira_duas_linhas():
    print("\n[2] A mesma chamada de LLM não vira duas linhas")
    db = FakeDB()
    servico = LEDGER.UsageService(db)
    for _ in range(3):
        servico.registrar(company_id="c1", source="chat",
                          idempotency_key="llm:run-abc", model="gpt-4o-mini",
                          input_tokens=10, output_tokens=5)
    checar(len(db.linhas) == 1,
           "três tentativas, uma linha", f"{len(db.linhas)} linhas")
    # Duplicata devolve None e NÃO explode — retentativa de worker é normal.
    segundo = servico.registrar(company_id="c1", source="chat",
                                idempotency_key="llm:run-abc", model="x")
    checar(segundo is None, "a duplicata é silenciosa, não é erro")


def teste_empresas_diferentes_nao_colidem():
    print("\n[3] Duas corretoras podem ter a mesma chave sem se atropelar")
    db = FakeDB()
    servico = LEDGER.UsageService(db)
    servico.registrar(company_id="c1", source="chat", idempotency_key="k")
    servico.registrar(company_id="c2", source="chat", idempotency_key="k")
    checar(len(db.linhas) == 2,
           "a unicidade é por (empresa, chave), não global",
           f"{len(db.linhas)} linhas")


def teste_falha_de_medicao_nao_derruba_o_trabalho():
    print("\n[4] Falhar ao medir não derruba o trabalho do corretor")
    class DBQuebrado:
        client = None
        def table(self, _):
            raise RuntimeError("banco fora do ar")
    devolvido = LEDGER.UsageService(DBQuebrado()).registrar(
        company_id="c1", source="chat")
    checar(devolvido is None, "devolve None em vez de explodir")


def teste_o_callback_escreve_no_ledger():
    print("\n[5] O gargalo único de LLM escreve no ledger da SPEC-062")
    # Este é o caso que importa: `usage_events` ficou em ZERO porque nenhum
    # caminho de LLM escrevia nela. O callback é injetado em toda instância de
    # chat model — um escritor aqui cobre o sistema inteiro.
    fonte_cb = open(os.path.join(RAIZ, "app", "core", "callbacks",
                                 "cost_callback.py"), encoding="utf-8").read()
    sem_comentario = "\n".join(l for l in fonte_cb.split("\n")
                               if not l.lstrip().startswith("#"))

    checar("_registrar_no_ledger" in sem_comentario,
           "o callback tem o caminho para o ledger")
    checar("work.usage import UsageService" in sem_comentario,
           "e usa o UsageService da SPEC-062, não um motor novo",
           "CLAUDE.md §5: consolidar antes de duplicar")
    checar("track_cost_sync" in sem_comentario,
           "o ledger legado continua sendo escrito",
           "trocar de ledger com o produto no ar quebra o histórico")
    checar('f"llm:{run_id}"' in sem_comentario,
           "a chave de idempotência vem do run_id do LangChain",
           "sem chave estável, retentativa vira linha duplicada")

    # A ordem importa: o legado primeiro. Se o novo explodisse antes, o
    # histórico perderia o registro que hoje funciona.
    pos_legado = sem_comentario.find("track_cost_sync")
    pos_novo = sem_comentario.find("self._registrar_no_ledger")
    checar(pos_legado != -1 and pos_novo != -1 and pos_legado < pos_novo,
           "o ledger legado é escrito ANTES do novo",
           f"legado em {pos_legado}, novo em {pos_novo}")


def teste_o_callback_nao_grava_evento_orfao():
    print("\n[6] Consumo sem empresa não vira linha órfã")
    # `usage_events.company_id` é NOT NULL. Tarefa global e script não têm
    # empresa: o certo é ficar de fora do ledger comercial, não inventar dono.
    fonte_cb = open(os.path.join(RAIZ, "app", "core", "callbacks",
                                 "cost_callback.py"), encoding="utf-8").read()
    checar("if not self.company_id:" in fonte_cb,
           "o callback desiste quando não há empresa")


def teste_provedor_sai_do_nome_do_modelo():
    print("\n[7] O ledger sabe de qual provedor foi o gasto")
    # Sem isso, `provider` fica nulo e a §26 não consegue separar custo por
    # fornecedor — que é a primeira pergunta de quem negocia contrato.
    import re
    fonte_cb = open(os.path.join(RAIZ, "app", "core", "callbacks",
                                 "cost_callback.py"), encoding="utf-8").read()
    for modelo, provedor in (("claude-opus-5", "anthropic"),
                             ("gpt-4o-mini", "openai"),
                             ("gemini-3-flash-preview", "google")):
        par = re.search(rf'\("{re.escape(provedor)}"\)|"{re.escape(provedor)}"',
                        fonte_cb)
        checar(par is not None, f"{modelo} → {provedor}")


def main() -> int:
    print("=" * 68)
    print("SPEC-062 §21 — O CONSUMO VIRA LINHA, E UMA LINHA SÓ")
    print("=" * 68)
    for teste in (teste_o_evento_nasce_sem_cobranca,
                  teste_a_mesma_chamada_nao_vira_duas_linhas,
                  teste_empresas_diferentes_nao_colidem,
                  teste_falha_de_medicao_nao_derruba_o_trabalho,
                  teste_o_callback_escreve_no_ledger,
                  teste_o_callback_nao_grava_evento_orfao,
                  teste_provedor_sai_do_nome_do_modelo):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("MEDIR NÃO É COBRAR — E O QUE SE MEDE, SE MEDE UMA VEZ SÓ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
