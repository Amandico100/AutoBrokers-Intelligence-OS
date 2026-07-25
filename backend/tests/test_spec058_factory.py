"""SPEC-058 — garantias da Auxiliary & Routine Factory.

A garantia central é [2]: o sistema não cria Agent para tudo. Inflação de
Agents é o erro mais caro que uma plataforma agêntica comete, e a SPEC-058 §5.3
proíbe — proibição sem teste é recomendação.

    python backend/tests/test_spec058_factory.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FALHAS: list[str] = []

for nome in ("app", "app.services", "app.services.auxiliaries"):
    if nome not in sys.modules:
        p = types.ModuleType(nome)
        p.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = p

_spec = importlib.util.spec_from_file_location(
    "app.services.auxiliaries.factory",
    os.path.join(RAIZ, "app/services/auxiliaries/factory.py"))
fac = importlib.util.module_from_spec(_spec)
fac.__package__ = "app.services.auxiliaries"
sys.modules["app.services.auxiliaries.factory"] = fac
_spec.loader.exec_module(fac)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def teste_pii_nunca_atravessa():
    print("\n[1] PII não atravessa a fronteira da corretora")
    bruto = ("Preciso cobrar o João, CPF 123.456.789-01, telefone (48) 99156-9402, "
             "email joao@empresa.com.br, apólice nº 4471-XY, placa MKJ-4471")
    limpo = fac.redigir(bruto)
    for vazamento in ("123.456.789-01", "99156-9402", "joao@empresa.com.br", "MKJ-4471"):
        checar(vazamento not in limpo, f"'{vazamento}' foi removido", limpo[:90])
    checar("[CPF]" in limpo and "[TELEFONE]" in limpo,
           "as marcas de redação ficam no lugar",
           "o funil de demanda é lido pela plataforma, não pela corretora")


def teste_nao_cria_agent_para_tudo():
    print("\n[2] O sistema NÃO cria Agent para tudo")
    pedidos = [
        "me faz um relatório de comissões agora",
        "todo dia de manhã me manda os boletos vencendo",
        "acompanhe as renovações que vencem essa semana",
        "quero ver quanto vendi esse mês",
        "me avise quando um cliente não responder por 3 dias",
        "monta uma apresentação pro cliente hoje",
        "toda semana me manda o resumo da carteira",
    ]
    padroes = [fac.classificar_padrao(p).padrao for p in pedidos]
    agents = [p for p in padroes if p == fac.AGENT]
    checar(not agents,
           f"nenhum dos {len(pedidos)} pedidos comuns virou Agent",
           f"viraram: {agents}")

    for p in padroes:
        checar(p in (fac.ONE_SHOT, fac.ROTINA, fac.AUXILIAR, fac.WORKFLOW, fac.EXECUTOR),
               f"padrão '{p}' é um dos baratos")


def teste_arvore_escolhe_o_mais_barato():
    print("\n[3] A árvore para no primeiro padrão que serve")
    casos = [
        ("me faz um relatório agora", fac.ONE_SHOT),
        ("todo dia me manda os boletos vencendo", fac.ROTINA),
        ("cuide de toda a cobrança da carteira", fac.AUXILIAR),
        ("toda semana: primeiro cotar, depois aprovação, só então enviar", fac.WORKFLOW),
    ]
    for texto, esperado in casos:
        d = fac.classificar_padrao(texto, tem_skill=True)
        checar(d.padrao == esperado, f"'{texto[:42]}' → {esperado}",
               f"veio={d.padrao} ({d.motivo})")


def teste_ambiguo_assume_o_barato():
    print("\n[4] Sem clareza, assume o mais barato e pergunta")
    d = fac.classificar_padrao("preciso de ajuda com os clientes")
    checar(d.padrao == fac.ONE_SHOT,
           "pedido vago NÃO vira Auxiliar nem Agent",
           f"veio={d.padrao} — adivinhar para cima cria estrutura que ninguém pediu")
    checar("me diga" in d.mensagem_humana.lower() or "quiser" in d.mensagem_humana.lower(),
           "a mensagem pergunta em vez de assumir", d.mensagem_humana[:70])
    checar(d.confianca < 0.5, "e a confiança registrada é baixa", str(d.confianca))


def teste_custo_crescente():
    print("\n[5] O custo relativo cresce na ordem certa")
    c = fac.CUSTO_RELATIVO
    checar(c[fac.ONE_SHOT] < c[fac.ROTINA] < c[fac.AUXILIAR] < c[fac.AGENT],
           "one-shot < rotina < auxiliar < agent")
    checar(c[fac.AGENT] == max(c.values()),
           "Agent é o mais caro da tabela",
           "e por isso o último da árvore, não o primeiro")


def teste_fingerprint_agrupa_a_mesma_dor():
    print("\n[6] A mesma dor de corretoras diferentes tem a mesma assinatura")
    a = fac.fingerprint("queria que alguém acompanhasse os boletos vencidos")
    b = fac.fingerprint("Preciso acompanhar os boletos que venceram")
    c = fac.fingerprint("acompanhe boletos vencidos por favor")
    checar(a == b == c,
           "três formas de pedir a mesma coisa colapsam numa assinatura",
           "sem isso, dez corretoras pedindo o mesmo viram dez itens de backlog")

    d = fac.fingerprint("me manda o relatório de sinistros do mês")
    checar(a != d, "pedidos diferentes têm assinaturas diferentes")


def teste_fingerprint_ignora_pii():
    print("\n[7] A assinatura não muda por causa do nome do cliente")
    a = fac.fingerprint("cobrar o cliente João, CPF 111.222.333-44")
    b = fac.fingerprint("cobrar o cliente Maria, CPF 555.666.777-88")
    checar(a == b,
           "o mesmo pedido para clientes diferentes agrupa junto",
           "senão cada cobrança viraria uma 'necessidade' distinta")


def teste_reuso_antes_de_criar():
    print("\n[8] Resolver antes de criar")

    class Db:
        def __init__(self, dados):
            self.dados, self.nome, self.f = dados, None, {}
        def table(self, n):
            self.nome, self.f = n, {}
            return self
        def select(self, *_a, **_k):
            return self
        def eq(self, c, v):
            self.f[c] = v
            return self
        def limit(self, *_a):
            return self
        def order(self, *_a, **_k):
            return self
        def execute(self):
            linhas = self.dados.get(self.nome, [])
            r = [x for x in linhas if all(x.get(k) == v for k, v in self.f.items())]
            return type("R", (), {"data": r})()

    f = fac.AuxiliaryFactory(Db({
        "tenant_auxiliaries": [{"id": "a1", "company_id": "c1", "slug": "cobranca-boletos",
                                "name": "Cobrança de boletos", "status": "active",
                                "template_id": "t1"}],
        "routines": [], "auxiliary_templates": [],
    }))
    achado = f.procurar_existente("c1", "queria acompanhar cobrança de boletos vencidos")
    checar(achado is not None and achado["tipo"] == "tenant_auxiliary",
           "encontra o Auxiliar que a corretora JÁ tem instalado", str(achado))
    checar("já tem" in fac._mensagem_de_reuso(achado).lower(),
           "e a mensagem diz isso em vez de propor instalar de novo",
           fac._mensagem_de_reuso(achado)[:80])

    vazio = fac.AuxiliaryFactory(Db({"tenant_auxiliaries": [], "routines": [],
                                     "auxiliary_templates": []}))
    checar(vazio.procurar_existente("c1", "algo que nao existe em lugar nenhum") is None,
           "e devolve None quando realmente não existe nada")


def main() -> int:
    print("=" * 68)
    print("SPEC-058 — AUXILIARY & ROUTINE FACTORY")
    print("=" * 68)
    teste_pii_nunca_atravessa()
    teste_nao_cria_agent_para_tudo()
    teste_arvore_escolhe_o_mais_barato()
    teste_ambiguo_assume_o_barato()
    teste_custo_crescente()
    teste_fingerprint_agrupa_a_mesma_dor()
    teste_fingerprint_ignora_pii()
    teste_reuso_antes_de_criar()

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  X {f}")
        return 1
    print("TODAS AS GARANTIAS VERIFICADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
