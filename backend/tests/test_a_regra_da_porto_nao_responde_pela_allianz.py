"""A regra de uma seguradora não responde pela outra.

A HISTÓRIA
==========
O Founder escreveu, antes de o defeito ser achado:

    "Regras da Porto podem não servir para Bradesco ou HDI. Então precisa ser
     tudo categorizado."

📊 07/08/2026: **o sistema já categorizava, e muito bem.** `ramo` e `category`
com ZERO nulos em 12.071 cartas publicadas, 20 seguradoras identificadas. E
jogava a categorização fora na hora de buscar:

    attendance_distiller.py:477   knowledge_extras={"scope", "curation_status",
                                  "namespace"}          ← sem insurer_key
    qdrant_service.search_similar  não tinha parâmetro de seguradora
    knowledge_scope.build_global_search_kwargs(carrier_slug=...)
                                  aceitava e DESCARTAVA — o docstring dizia
                                  "reservados para filtragem fina"

Consequência: as 608 cartas da Allianz disputavam em igualdade qualquer
pergunta sobre a Porto (361 cartas), e nada no sistema registrava a troca. Um
segurado podia receber a regra da companhia errada com a confiança de quem leu
a apólice.

A REGRA, E POR QUE ELA TEM DOIS BRAÇOS
======================================
    "desta seguradora **OU** sem seguradora" — nunca "só desta".

📊 9.727 das 12.071 cartas (**80,6%**) não têm seguradora, e isso está certo:
são fato genérico de mercado ("vistoria complementar antes de liberar o
complemento"), que vale para qualquer companhia.

Um filtro de um braço só cortaria 80,6% do acervo. Trocaria "responde pela
seguradora errada" por "não responde nada" — e o segundo defeito é pior,
porque parece prudência.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _fonte(rel: str) -> str:
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as arquivo:
        return arquivo.read()


def _carregar_escopo():
    """`knowledge_scope` é puro (só typing). Carrega sem trazer o mundo."""
    nome = "_teste_knowledge_scope"
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, "backend", "app", "services", "knowledge_scope.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# --------------------------------------------------------------------------
def teste_a_pergunta_diz_de_qual_seguradora_fala():
    print("\n[1] Reconhecer a companhia na pergunta")
    KS = _carregar_escopo()

    # O dicionário real vive em `corridor_playbooks`, que puxa o pacote inteiro.
    # Dublamos SÓ o dicionário — a função sob teste é a lógica, não a lista.
    falso = types.ModuleType("app.services.corridor_playbooks")
    falso._INSURER_ALIASES = {
        "porto": "porto", "porto seguro": "porto", "portoseguro": "porto",
        "allianz": "allianz", "hdi": "hdi", "azul": "azul",
        "tokio marine": "tokio", "bradesco": "bradesco",
    }
    for pai in ("app", "app.services"):
        if pai not in sys.modules:
            m = types.ModuleType(pai)
            m.__path__ = []
            sys.modules[pai] = m
    sys.modules["app.services.corridor_playbooks"] = falso

    achar = KS.seguradora_da_pergunta
    checar(achar("como faço para pedir boleto atualizado na Porto?") == "porto",
           "acha a Porto numa pergunta de cobrança")
    checar(achar("a Tokio Marine cobre guincho de quantos km?") == "tokio",
           "acha apelido de duas palavras")

    # CONTROLE — pergunta sem companhia NÃO filtra. É a maioria das perguntas,
    # e nelas todo o acervo tem de responder.
    checar(achar("como funciona a vistoria complementar?") is None,
           "CONTROLE — pergunta genérica não filtra nada",
           "é o caso mais comum, e o acervo inteiro responde")
    checar(achar("") is None and achar(None) is None,
           "CONTROLE — vazio e nulo não filtram")

    # CONTROLE — comparação entre duas companhias não pode escolher uma.
    checar(achar("a Porto cobre igual a HDI nesse caso?") is None,
           "CONTROLE — duas companhias na pergunta: não filtra",
           "filtrar por uma esconderia a outra, e a pergunta é sobre as duas")

    # CONTROLE — palavra que CONTÉM o apelido não vale. Sem fronteira de
    # palavra, "azulejo" viraria a seguradora Azul e uma pergunta sobre vidro
    # residencial passaria a ser filtrada por uma companhia de auto.
    checar(achar("quebrou o azulejo do banheiro, tem cobertura?") is None,
           "CONTROLE — 'azulejo' não é a seguradora Azul",
           "apelido curto exige fronteira de palavra")


def teste_o_filtro_tem_dois_bracos():
    print("\n[2] 'Desta seguradora OU sem seguradora' — nunca 'só desta'")
    fonte = _fonte("backend/app/services/qdrant_service.py")
    arvore = ast.parse(fonte)
    corpo = None
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == "_filtro_de_seguradora":
            corpo = ast.get_source_segment(fonte, no)
    checar(corpo is not None, "o filtro de seguradora existe")
    if not corpo:
        return

    checar("should=[" in corpo,
           "os dois braços são um `should` (OU), não um `must` (E)",
           "um `must` de igualdade cortaria as 80,6% de cartas genéricas")
    checar("IsEmptyCondition" in corpo and "insurer_key" in corpo,
           "e o segundo braço é 'sem seguradora'",
           "é ele que preserva o fato genérico de mercado")

    # CONTROLE — sem seguradora na pergunta, NENHUM filtro é montado.
    checar("if not slug:" in corpo and "return None" in corpo,
           "CONTROLE — pergunta sem companhia não monta filtro nenhum")

    # 🔴 DEGRADAÇÃO SEGURA: sem `IsEmptyCondition` o filtro INTEIRO é
    # abandonado. Manter só o primeiro braço criaria um comportamento NOVO e
    # pior (cortar 80,6% do acervo) exatamente quando ninguém está olhando.
    checar("IsEmptyCondition is None" in corpo and corpo.count("return None") >= 2,
           "sem IsEmptyCondition, abandona o filtro inteiro",
           "voltar ao defeito conhecido é melhor que inventar um pior")


def teste_a_classificacao_viaja_ate_o_indice():
    print("\n[3] A etiqueta chega ao Qdrant, não só ao banco")
    dist = _fonte("backend/app/services/attendance_distiller.py")
    trecho = dist.split("knowledge_extras=")[1][:900] if "knowledge_extras=" in dist else ""

    checar('"insurer_key"' in trecho, "`insurer_key` entra no payload do índice")
    checar('"ramo"' in trecho, "`ramo` também")
    checar('"card_category"' in trecho, "e a categoria")

    # CONTROLE — carta sem seguradora NÃO ganha chave vazia. A busca precisa
    # distinguir "não tem seguradora" de "seguradora desconhecida": string
    # vazia quebraria o braço `IsEmptyCondition` e as 80,6% sumiriam.
    checar('if card.get("insurer_key") else {}' in trecho,
           "CONTROLE — sem seguradora, a chave NÃO é gravada vazia",
           "string vazia não é campo ausente, e o filtro depende dessa diferença")


def teste_a_busca_global_passa_a_seguradora():
    print("\n[4] Os dois caminhos de busca usam a regra")
    ks = _fonte("backend/app/services/knowledge_scope.py")
    checar('kwargs["carrier_slug"]' in ks,
           "`build_global_search_kwargs` PASSA o carrier em vez de descartar",
           "por muito tempo ele foi aceito e jogado fora")

    for arquivo, nome in (("backend/app/services/search_service.py", "search_service"),
                          ("backend/app/services/langchain_service.py", "langchain_service")):
        fonte = _fonte(arquivo)
        cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
        checar("seguradora_da_pergunta(" in cmd and "carrier_slug=" in cmd,
               f"{nome} descobre a companhia e a repassa",
               "os dois caminhos chegam à coleção global")


def teste_o_qdrant_aceita_o_parametro():
    print("\n[5] CONTROLE — o parâmetro existe de verdade na assinatura")
    fonte = _fonte("backend/app/services/qdrant_service.py")
    arvore = ast.parse(fonte)
    assinatura = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == "search_similar":
            assinatura = [a.arg for a in no.args.args] + [a.arg for a in no.args.kwonlyargs]

    checar("carrier_slug" in assinatura,
           "`search_similar` aceita `carrier_slug`",
           "sem isto, passar o argumento levantaria TypeError em produção")

    # E o filtro tem de ser APLICADO, não só recebido — foi exatamente esse o
    # defeito original: parâmetro declarado e ignorado.
    corpo = ""
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == "search_similar":
            corpo = ast.get_source_segment(fonte, no) or ""
    checar("_filtro_de_seguradora(carrier_slug)" in corpo
           and "must_conditions.append(filtro_seguradora)" in corpo,
           "CONTROLE — e o filtro entra nas condições da busca",
           "parâmetro recebido e não aplicado foi o defeito de origem")


def main() -> int:
    print("=" * 70)
    print("A REGRA DA PORTO NÃO RESPONDE PELA ALLIANZ")
    print("=" * 70)
    teste_a_pergunta_diz_de_qual_seguradora_fala()
    teste_o_filtro_tem_dois_bracos()
    teste_a_classificacao_viaja_ate_o_indice()
    teste_a_busca_global_passa_a_seguradora()
    teste_o_qdrant_aceita_o_parametro()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — cada seguradora responde pela sua regra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
