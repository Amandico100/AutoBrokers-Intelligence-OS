"""SPEC-062 §26 — custo é fato, preço é decisão.

Por que este arquivo existe
---------------------------
O Founder pretende cobrar com margem sobre consumo, e não existia nenhum lugar
no sistema que respondesse *"quanto me custa manter esta corretora no ar?"*.
Sem essa resposta, o preço sai de palpite.

O risco que o teste protege
---------------------------
Um relatório de custo erra de duas maneiras, e as duas são caras:

1. **Mostrando preço onde deveria mostrar custo.** `provider_cost` e
   `customer_price` são coisas diferentes (§23.1). Quando um vira o outro sem
   ninguém notar, é assim que cobrança retroativa nasce — o número já está lá,
   parecendo uma fatura.

2. **Truncando em silêncio.** Um custo lido pela metade parece metade do custo.
   Não existe defeito pior num relatório financeiro: ele não parece quebrado,
   parece uma boa notícia.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)),
               ("app.services", ("app", "services")),
               ("app.services.control_plane", ("app", "services", "control_plane"))):
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


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


UE = carregar("app.services.control_plane.unit_economics")

EMPRESAS = [{"id": "c1", "company_name": "Resulta Seguros"},
            {"id": "c2", "company_name": "AutoFleet"}]


# 🔴 O DUBLE CORTA EM 1.000, COMO O SERVIDOR DE VERDADE.
#
# 📊 06/08/2026: o PostgREST devolve no maximo 1.000 linhas por resposta e
# IGNORA o `.limit(N)` pedido acima disso. O `unit_economics` lia com
# `.limit(TETO)`, TETO=5000, e decidia "truncou?" com `len(linhas) >= TETO` —
# conta que dava sempre `1000 >= 5000`, isto e, False. O relatorio declarava
# ativamente que tinha lido tudo, sobre 1.000 de 4.406 eventos reais.
#
# Este duble obedecia o `.limit()` ao pe da letra, e por isso o teste [4] ficava
# VERDE em cima do defeito vivo: aqui vinham 5.000, em producao vinham 1.000.
#
# Agora ele corta como o real, e o modulo pagina. A licao do teste [4] nao
# morreu — ela MIGROU (CLAUDE.md §9.3): continua provando que truncagem nao e
# silenciosa, agora contra o teto que existe de verdade.
TETO_DO_SERVIDOR = 1000


class FakeQ:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self._eq: list[tuple] = []
        self._faixa = None
        self._ordem = None

    def select(self, *_a, **_k):
        return self

    def gte(self, *_a, **_k):
        return self

    def order(self, campo, desc=False, **_k):
        self._ordem = (campo, bool(desc))
        return self

    def range(self, inicio, fim):
        self._faixa = (int(inicio), int(fim))
        return self

    def limit(self, n):
        self._limite = n
        return self

    def eq(self, c, v):
        self._eq.append((c, v))
        return self

    def execute(self):
        if self.tabela in self.banco.quebradas:
            raise RuntimeError("fonte fora do ar")
        linhas = self.banco.linhas.get(self.tabela, [])
        for c, v in self._eq:
            linhas = [l for l in linhas if str(l.get(c)) == str(v)]
        if self._ordem:
            campo, desc = self._ordem
            linhas = sorted(linhas, key=lambda l: str(l.get(campo) or ""), reverse=desc)
        if self._faixa:
            inicio, fim = self._faixa
            linhas = linhas[inicio:fim + 1]
        linhas = linhas[: getattr(self, "_limite", 10_000)]
        return types.SimpleNamespace(data=linhas[:TETO_DO_SERVIDOR])


class FakeDB:
    def __init__(self, eventos=None, legado=None, quebradas=()):
        self.linhas = {"companies": EMPRESAS,
                       "usage_events": eventos or [],
                       "token_usage_logs": legado or []}
        self.quebradas = set(quebradas)
        self.client = self

    def table(self, nome):
        return FakeQ(self, nome)


EV = [{"company_id": "c1", "provider_cost_usd": 0.10, "input_tokens": 1000,
       "output_tokens": 500, "model": "claude-sonnet-5", "source": "chat",
       "skill_slug": "renovacao", "tool_name": None},
      {"company_id": "c2", "provider_cost_usd": 0.02, "input_tokens": 200,
       "output_tokens": 100, "model": "gpt-4o-mini", "source": "chat",
       "skill_slug": None, "tool_name": "buscar_apolice"}]

LEG = [{"company_id": "c1", "total_cost_usd": 0.05, "input_tokens": 400,
        "output_tokens": 200, "model_name": "gpt-4o-mini",
        "service_type": "attendance"}]


def teste_nao_devolve_preco():
    print("\n[1] O relatório entrega CUSTO, e diz que é custo")
    r = UE.EconomiaPorCorretora(FakeDB(EV, LEG)).montar()
    checar("aviso" in r and "provedor" in r["aviso"].lower(),
           "a resposta declara que é custo de provedor", str(r.get("aviso")))
    # A cobrança é por CAMPO, não por palavra: o próprio aviso diz "não tem
    # margem aplicada", e essa frase tem que continuar existindo. Foi o teste
    # que estava errado na primeira versão, não o aviso.
    def chaves(obj, achadas=None):
        achadas = achadas if achadas is not None else set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                achadas.add(str(k).lower())
                chaves(v, achadas)
        elif isinstance(obj, list):
            for x in obj:
                chaves(x, achadas)
        return achadas

    todas = chaves(r)
    for proibido in ("customer_price", "preco_ao_cliente", "preco_brl",
                     "margem", "margin", "sell_multiplier", "valor_a_cobrar"):
        checar(proibido not in todas,
               f"nenhum campo chamado '{proibido}'",
               "misturar custo com preço é como a cobrança retroativa nasce")
    checar(any("custo" in k for k in todas),
           "e os campos de dinheiro se chamam CUSTO")


def teste_soma_as_duas_fontes():
    print("\n[2] As duas fontes entram, e a procedência aparece")
    r = UE.EconomiaPorCorretora(FakeDB(EV, LEG), cotacao_dolar=6.0).montar()
    por_nome = {c["corretora"]: c for c in r["corretoras"]}
    # Resulta: 0.10 (evento) + 0.05 (legado) = 0.15
    checar(abs(por_nome["Resulta Seguros"]["custo_provedor_usd"] - 0.15) < 1e-9,
           "soma ledger novo + legado",
           str(por_nome["Resulta Seguros"]["custo_provedor_usd"]))
    checar(abs(por_nome["Resulta Seguros"]["custo_provedor_brl"] - 0.90) < 1e-6,
           "converte para BRL pela cotação",
           str(por_nome["Resulta Seguros"]["custo_provedor_brl"]))
    checar(r["procedencia"]["usage_events"] == 2
           and r["procedencia"]["token_usage_logs"] == 1,
           "diz quantos registros vieram de cada fonte",
           str(r["procedencia"]))
    checar(r["procedencia"]["atribuicao_fina_disponivel"] is True,
           "declara que há atribuição por skill/tool")


def teste_sem_ledger_novo_avisa():
    print("\n[3] Só com o legado, o relatório AVISA que não há atribuição fina")
    # É o estado de hoje: `usage_events` acabou de ganhar escritor. Sem o
    # aviso, alguém leria "por_fonte" como atribuição por skill quando é só o
    # `service_type` grosso do legado.
    r = UE.EconomiaPorCorretora(FakeDB([], LEG)).montar()
    checar(r["procedencia"]["atribuicao_fina_disponivel"] is False,
           "declara que a atribuição fina não está disponível")
    checar("legado" in r["frase"].lower(),
           "e a frase para humano diz isso", r["frase"])


def teste_truncagem_nao_e_silenciosa():
    print("\n[4] Custo lido pela metade não parece metade do custo")
    muitos = [dict(EV[0]) for _ in range(UE.TETO)]
    r = UE.EconomiaPorCorretora(FakeDB(muitos, [])).montar()
    checar(r["truncado"] is True, "a resposta declara que truncou")
    checar(r["aviso_de_truncagem"] and "MAIOR" in r["aviso_de_truncagem"],
           "e diz que o custo real é MAIOR", str(r.get("aviso_de_truncagem")))

    r2 = UE.EconomiaPorCorretora(FakeDB(EV, LEG)).montar()
    checar(r2["truncado"] is False and r2["aviso_de_truncagem"] is None,
           "e não avisa quando não truncou")


def teste_fonte_fora_do_ar_nao_zera_relatorio():
    print("\n[5] Uma fonte fora do ar não vira 'custo zero'")
    # Zero é uma resposta perigosa: parece que ninguém gastou nada.
    r = UE.EconomiaPorCorretora(FakeDB(EV, LEG, quebradas={"usage_events"})).montar()
    checar(r["total"]["custo_provedor_usd"] > 0,
           "o relatório sai com a fonte que respondeu")
    checar(r["procedencia"]["usage_events"] == 0,
           "e a procedência mostra o buraco", str(r["procedencia"]))


def teste_ordena_pelo_que_custa_mais():
    print("\n[6] Quem custa mais aparece primeiro")
    r = UE.EconomiaPorCorretora(FakeDB(EV, LEG)).montar()
    custos = [c["custo_provedor_usd"] for c in r["corretoras"]]
    checar(custos == sorted(custos, reverse=True),
           "a lista desce do maior para o menor", str(custos))
    checar("Resulta" in r["frase"],
           "e a frase nomeia a maior", r["frase"])


def teste_empresa_removida_nao_some_do_custo():
    print("\n[7] Consumo de corretora removida não desaparece da conta")
    # Se o custo sumisse junto com a linha da empresa, o total ficaria menor
    # que a fatura do fornecedor — e ninguém saberia por quê.
    fantasma = [{"company_id": "c9", "provider_cost_usd": 1.0,
                 "input_tokens": 10, "output_tokens": 5, "model": "x",
                 "source": "chat", "skill_slug": None, "tool_name": None}]
    r = UE.EconomiaPorCorretora(FakeDB(fantasma, [])).montar()
    checar(abs(r["total"]["custo_provedor_usd"] - 1.0) < 1e-9,
           "o custo entra no total")
    checar(any("removida" in c["corretora"] for c in r["corretoras"]),
           "e a linha diz que a corretora não existe mais",
           str([c["corretora"] for c in r["corretoras"]]))


def main() -> int:
    print("=" * 68)
    print("SPEC-062 §26 — CUSTO É FATO, PREÇO É DECISÃO")
    print("=" * 68)
    for teste in (teste_nao_devolve_preco,
                  teste_soma_as_duas_fontes,
                  teste_sem_ledger_novo_avisa,
                  teste_truncagem_nao_e_silenciosa,
                  teste_fonte_fora_do_ar_nao_zera_relatorio,
                  teste_ordena_pelo_que_custa_mais,
                  teste_empresa_removida_nao_some_do_custo):
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
    print("DÁ PARA SABER O QUE CADA CORRETORA CUSTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
