"""SPEC-052 Lote 3 — garantias do Context Assembly 2.0.

A garantia que mais importa está no teste [4]: o conhecimento normativo, sozinho,
nunca confirma cobertura de uma apólice concreta.

    python backend/tests/test_spec052_context_assembly.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FALHAS: list[str] = []

for nome in ("app", "app.agents"):
    if nome not in sys.modules:
        p = types.ModuleType(nome)
        p.__path__ = [os.path.join(RAIZ, *nome.split("."))]
        sys.modules[nome] = p

_spec = importlib.util.spec_from_file_location(
    "app.agents.context_assembly", os.path.join(RAIZ, "app/agents/context_assembly.py"))
ca = importlib.util.module_from_spec(_spec)
ca.__package__ = "app.agents"
sys.modules["app.agents.context_assembly"] = ca
_spec.loader.exec_module(ca)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def teste_saudacao_nao_recupera_nada():
    print("\n[1] Saudação não paga recuperação")
    for t in ["oi", "Bom dia!", "boa tarde", "obrigado", "valeu", "ok",
              "tudo bem?", "Perfeito, obrigado!"]:
        i = ca.classificar(t)
        p = ca.planejar(i)
        checar(i.tipo == ca.CONVERSA and not p.fontes,
               f"'{t}' → nenhuma fonte", f"tipo={i.tipo} fontes={p.fontes}")


def teste_regua_antiga_errava():
    print("\n[2] A régua de 25 caracteres errava nos dois sentidos")
    curta_mas_importante = "cobre vidro?"
    longa_mas_social = "Bom dia! Tudo bem com você?"

    checar(len(curta_mas_importante) < 25 and ca.deve_recuperar(curta_mas_importante),
           f"'{curta_mas_importante}' ({len(curta_mas_importante)} chars) AGORA recupera",
           "a régua antiga ignorava — é pergunta de cobertura")
    checar(len(longa_mas_social) > 25 and not ca.deve_recuperar(longa_mas_social),
           f"'{longa_mas_social}' ({len(longa_mas_social)} chars) AGORA não recupera",
           "a régua antiga disparava RAG completo numa saudação")


def teste_intencao_escolhe_fontes():
    print("\n[3] Cada intenção carrega só o que precisa")
    casos = [
        ("quanto foi a comissão de junho?", ca.ANALISE),
        ("como faço para emitir a 2ª via do boleto?", ca.OPERACAO),
        ("o que mudou na circular da SUSEP?", ca.PESQUISA),
        ("qual a vigência dessa apólice?", ca.FATO_SEGURO),
    ]
    for texto, esperado in casos:
        i = ca.classificar(texto)
        checar(i.tipo == esperado, f"'{texto[:38]}' → {esperado}", f"veio={i.tipo}")

    p = ca.planejar(ca.classificar("quanto foi a comissão de junho?"))
    checar("dados_vivos" in p.fontes,
           "análise busca dados vivos, não só documento")
    checar("rag_global" not in p.fontes,
           "análise NÃO carrega conhecimento global",
           "número da corretora não está em documento curado global")


def teste_cobertura_de_apolice_especifica():
    print("\n[4] Norma sozinha NUNCA confirma cobertura de apólice concreta")

    generica = ca.classificar("o seguro auto cobre vidro?")
    especifica = ca.classificar("a apólice do cliente João cobre vidro?")

    checar(generica.tipo == ca.COBERTURA_APOLICE and not generica.especifica,
           "pergunta de produto é reconhecida como genérica")
    checar(especifica.tipo == ca.COBERTURA_APOLICE and especifica.especifica,
           "pergunta sobre apólice concreta é reconhecida como específica",
           f"especifica={especifica.especifica}")
    checar(especifica.risco == "alto", "risco alto na pergunta específica",
           especifica.risco)

    plano = ca.planejar(especifica)
    checar(plano.exige_apolice, "o plano marca que exige a apólice")

    pacote = ca.montar(plano, {
        "normativo": [{
            "conteudo": "Artigo 12. A cobertura de vidros compreende para-brisa, "
                        "vidros laterais e traseiro, sem franquia.",
            "rotulo": "Condições Gerais", "emissor": "Porto Seguro",
            "vigencia": "2026-01-01"}],
    })
    bloco = pacote.como_bloco()

    checar("NÃO afirme" in bloco,
           "o bloco instrui explicitamente a NÃO confirmar cobertura")
    checar("apólice deste cliente" in bloco,
           "o aviso nomeia o risco: é a apólice do cliente que decide")
    checar("vigente desde 2026-01-01" in bloco,
           "a vigência da condição viaja junto do texto",
           "sem ela o agente responde sobre a versão errada")

    # A pergunta genérica não deve carregar o aviso — ele existe para o caso
    # específico, e repetir em toda pergunta ensinaria o modelo a ignorá-lo.
    pacote2 = ca.montar(ca.planejar(generica), {
        "normativo": [{"conteudo": "Artigo 12. Cobertura de vidros.",
                       "rotulo": "Condições Gerais"}]})
    checar("NÃO afirme" not in pacote2.como_bloco(),
           "pergunta genérica NÃO recebe o aviso",
           "aviso em toda resposta vira ruído e o modelo passa a ignorar")


def teste_precedencia():
    print("\n[5] Precedência da SPEC-052 §6.4 é respeitada")
    plano = ca.planejar(ca.classificar("a apólice do cliente cobre vidro?"))
    plano.fontes = ["evidence_apolice", "dados_vivos", "normativo", "rag_tenant", "rag_global"]

    pacote = ca.montar(plano, {
        "rag_global": "texto do conhecimento global",
        "normativo": "texto da condição geral",
        "evidence_apolice": "texto da apólice do cliente",
        "dados_vivos": "texto do sistema de gestão",
        "rag_tenant": "texto do conhecimento da corretora",
    })
    ordem = [e.fonte for e in pacote.evidencias]
    checar(ordem[0] == "evidence_apolice",
           "a apólice do cliente vem PRIMEIRO", str(ordem))
    checar(ordem.index("dados_vivos") < ordem.index("normativo"),
           "sistema de gestão vem antes da norma")
    checar(ordem.index("normativo") < ordem.index("rag_global"),
           "norma vem antes do conhecimento global")


def teste_orcamento():
    print("\n[6] Orçamento de contexto é respeitado")
    plano = ca.planejar(ca.classificar("qual a vigência dessa apólice?"))
    plano.orcamento = 1_000
    pacote = ca.montar(plano, {"normativo": "x" * 50_000, "rag_tenant": "y" * 50_000})
    checar(pacote.caracteres <= 1_000,
           f"total respeita o orçamento ({pacote.caracteres} <= 1000)")
    checar(len(pacote.como_bloco()) > 0, "mesmo cortado, entrega conteúdo útil")

    plano2 = ca.planejar(ca.classificar("qual a vigência dessa apólice?"))
    pacote2 = ca.montar(plano2, {"normativo": "z" * 50_000})
    checar(pacote2.caracteres <= ca.TETO_POR_FONTE["normativo"],
           "teto por fonte impede uma fonte engolir todo o espaço",
           f"{pacote2.caracteres}")


def teste_deduplicacao():
    print("\n[7] Trecho repetido não ocupa espaço duas vezes")
    texto = ("A cobertura de vidros compreende para-brisa, vidros laterais e "
             "traseiro, sem aplicação de franquia, conforme condições gerais.")
    plano = ca.planejar(ca.classificar("qual a vigência dessa apólice?"))
    plano.fontes = ["normativo", "rag_tenant"]
    pacote = ca.montar(plano, {"normativo": texto, "rag_tenant": texto})
    checar(len(pacote.evidencias) == 1,
           "o mesmo trecho em duas fontes entra uma vez só",
           f"entraram {len(pacote.evidencias)}")
    checar(pacote.evidencias[0].fonte == "normativo",
           "e fica a versão de MAIOR autoridade",
           "duas cópias dariam ao modelo a impressão de duas confirmações")


def teste_plano_ignora_o_que_nao_pediu():
    print("\n[8] O plano manda, não a disponibilidade")
    plano = ca.planejar(ca.classificar("oi, bom dia"))
    pacote = ca.montar(plano, {"rag_global": "documento enorme", "normativo": "outro"})
    checar(not pacote.evidencias,
           "material disponível mas fora do plano NÃO entra",
           "recuperar por estar à mão é como o contexto incha sem melhorar")


def main() -> int:
    print("=" * 68)
    print("SPEC-052 LOTE 3 — CONTEXT ASSEMBLY 2.0")
    print("=" * 68)
    teste_saudacao_nao_recupera_nada()
    teste_regua_antiga_errava()
    teste_intencao_escolhe_fontes()
    teste_cobertura_de_apolice_especifica()
    teste_precedencia()
    teste_orcamento()
    teste_deduplicacao()
    teste_plano_ignora_o_que_nao_pediu()

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
