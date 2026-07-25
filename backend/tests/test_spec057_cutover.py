"""SPEC-057 Bloco I — garantias do cutover do grafo.

O que se prova: que o Gateway só consegue tirar ferramenta, que falha dele não
derruba o atendimento, e que o modo `off` é literalmente inerte.

    python backend/tests/test_spec057_cutover.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FALHAS: list[str] = []

for nome in ("app", "app.agents", "app.services", "app.services.skills"):
    if nome not in sys.modules:
        p = types.ModuleType(nome)
        p.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = p

_spec = importlib.util.spec_from_file_location(
    "app.agents.gateway_cutover", os.path.join(RAIZ, "app/agents/gateway_cutover.py"))
cut = importlib.util.module_from_spec(_spec)
cut.__package__ = "app.agents"
sys.modules["app.agents.gateway_cutover"] = cut
_spec.loader.exec_module(cut)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


class Tool:
    def __init__(self, name):
        self.name = name


FERRAMENTAS = [Tool(n) for n in (
    "knowledge_base_search", "web_search", "csv_analytics",
    "portal_action", "insurer_dispatch", "human_handoff", "gerar_relatorio")]


def teste_modo_off_e_inerte():
    print("\n[1] Modo 'off' não faz nada")
    os.environ["TOOL_GATEWAY_MODE"] = "off"
    r = cut.avaliar(tools_legado=FERRAMENTAS, supabase_client=object(),
                    company_id="c1", agent_role="core", texto_usuario="oi")
    checar(r.modo == "off" and not r.aplicar, "não avalia e não aplica")
    saida = cut.aplicar(FERRAMENTAS, r)
    checar(saida is FERRAMENTAS, "devolve a MESMA lista, sem cópia nem filtro")


def teste_gateway_so_subtrai():
    print("\n[2] O Gateway só consegue TIRAR ferramenta")
    r = cut.ResultadoCutover(
        modo="on", aplicar=True,
        # Concede uma que o grafo não montou e nega três que ele montou.
        permitidas={"knowledge.search", "analytics.csv", "insurance.policy_lookup"})
    saida = cut.aplicar(FERRAMENTAS, r)
    nomes = {t.name for t in saida}

    checar("portal_action" not in nomes, "ferramenta negada é removida")
    checar("insurer_dispatch" not in nomes, "acionamento de seguradora é removido")
    checar("csv_analytics" in nomes, "ferramenta concedida permanece")
    checar(len(saida) <= len(FERRAMENTAS),
           "a lista nunca cresce — o Gateway não conjura ferramenta",
           f"{len(FERRAMENTAS)} -> {len(saida)}")
    checar(all(any(t is o for o in FERRAMENTAS) for t in saida),
           "toda ferramenta na saída veio da lista original")


def teste_minimo_de_conversa_preservado():
    print("\n[3] O mínimo para conversar nunca é removido")
    r = cut.ResultadoCutover(modo="on", aplicar=True, permitidas={"nada.existe"})
    saida = cut.aplicar(FERRAMENTAS, r)
    nomes = {t.name for t in saida}
    checar("knowledge_base_search" in nomes,
           "busca no conhecimento da corretora sobrevive a qualquer negativa",
           "removê-la não restringe privilégio, quebra o produto")
    checar("human_handoff" in nomes, "transferir para humano sobrevive")


def teste_nunca_devolve_lista_vazia():
    print("\n[4] Nunca entrega um agente sem ferramenta nenhuma")
    so_portal = [Tool("portal_action"), Tool("insurer_dispatch")]
    r = cut.ResultadoCutover(modo="on", aplicar=True, permitidas={"nada"})
    saida = cut.aplicar(so_portal, r)
    checar(len(saida) > 0,
           "com tudo negado, devolve a lista antiga em vez de lista vazia",
           "agente sem ferramenta responde pior; o cutover não pode piorar o produto")


def teste_falha_do_gateway_nao_derruba():
    print("\n[5] Falha do Gateway não derruba o atendimento")
    os.environ["TOOL_GATEWAY_MODE"] = "shadow"

    class DbQuebrado:
        def table(self, *_a, **_k):
            raise RuntimeError("banco fora do ar")

    r = cut.avaliar(tools_legado=FERRAMENTAS, supabase_client=DbQuebrado(),
                    company_id="c1", agent_role="core", texto_usuario="me faz um relatório")
    checar(r.erro is not None, "o erro é capturado e registrado", str(r.erro))
    checar(not r.aplicar, "com erro, NÃO aplica — segue o caminho antigo")
    saida = cut.aplicar(FERRAMENTAS, r)
    checar(len(saida) == len(FERRAMENTAS), "nenhuma ferramenta é perdida por causa do erro")
    os.environ["TOOL_GATEWAY_MODE"] = "off"


def teste_shadow_nao_aplica():
    print("\n[6] Shadow observa, não interfere")
    r = cut.ResultadoCutover(modo="shadow", aplicar=False, permitidas={"knowledge.search"})
    saida = cut.aplicar(FERRAMENTAS, r)
    checar(len(saida) == len(FERRAMENTAS),
           "em shadow, a lista antiga continua valendo mesmo com o Gateway discordando")


def teste_mapa_de_nomes():
    print("\n[7] O nome no LangChain vira a chave do Registry")
    pares = [("web_scrape", "research.web_scrape"),
             ("document_read", "research.document_read"),
             ("gerar_relatorio", "artifacts.generate_report"),
             ("portal_action", "portal.execute")]
    for nome, esperado in pares:
        checar(cut.chave_de_registro(Tool(nome)) == esperado,
               f"'{nome}' → '{esperado}'", cut.chave_de_registro(Tool(nome)))
    checar(cut.chave_de_registro(Tool("ferramenta_nova")) == "ferramenta_nova",
           "nome desconhecido passa direto em vez de virar None",
           "adivinhar por heurística negaria ferramenta certa por diferença de nome")


def teste_criterio_de_virada():
    print("\n[8] O critério para virar a chave é explícito")
    class DbVazio:
        def table(self, *_a, **_k):
            return self
        def select(self, *_a, **_k):
            return self
        def order(self, *_a, **_k):
            return self
        def limit(self, *_a, **_k):
            return self
        def execute(self):
            return type("R", (), {"data": []})()

    p = cut.progresso(DbVazio())
    checar(p.get("ok") and not p.get("pronto_para_virar"),
           "sem decisão registrada, NÃO está pronto para virar", str(p.get("motivo")))


def main() -> int:
    print("=" * 68)
    print("SPEC-057 BLOCO I — CUTOVER DO GRAFO")
    print("=" * 68)
    teste_modo_off_e_inerte()
    teste_gateway_so_subtrai()
    teste_minimo_de_conversa_preservado()
    teste_nunca_devolve_lista_vazia()
    teste_falha_do_gateway_nao_derruba()
    teste_shadow_nao_aplica()
    teste_mapa_de_nomes()
    teste_criterio_de_virada()

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
