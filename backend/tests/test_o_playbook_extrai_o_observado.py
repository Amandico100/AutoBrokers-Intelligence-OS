"""O playbook extrai o que as conversas ensinam — não o atendimento ideal.

A HISTÓRIA
==========
O prompt que gera playbook de conduta abria assim:

    "Você é o melhor treinador de atendimento de corretoras de seguros do
     Brasil. Sintetize o MELHOR playbook — o padrão-ouro que um atendente deve
     seguir nesse serviço."

Um pedido assim não é neutro: **convida o modelo a completar com conhecimento
de mundo tudo o que as conversas não ensinaram.** E foi o que aconteceu.

📊 Medido em 07/08/2026 sobre os 18 playbooks do banco:

    espaço em branco literal em frase de saída   15 frases   10 em ATIVOS
    afirma cobertura                              4 frases    2 em ATIVOS
    pergunta o que a corretora já tem            30 campos   20 em ATIVOS

**Os playbooks ATIVOS estavam piores que os rascunhos.** E `graph.py:806`
injeta a `ficha_coleta` inteira no prompt do agente de atendimento, com
`str(item)` — então a pior frase, de um playbook `active`, iria para o
atendimento com o buraco dentro:

    "Só informar, nunca perguntar: 'Confirmei aqui: você tem cobertura de
     vidros, com participação de R$ [valor] para esse item.'"

Cobertura afirmada + valor + colchete vazio + a instrução de NÃO conferir. E o
campo `sensibilidade` do MESMO playbook manda nunca prometer valor.

A CAUSA MAIS FUNDA: O MATERIAL DE ENTRADA
=========================================
📊 `auto/bateria` foi escrito com 13 sessões das quais **8 tinham score 0**.
Score 0 não é nota baixa: é **"não houve atendimento humano"** — robô da
seguradora, central de prestadora, fragmento. O playbook aprendeu conduta de um
bot, e o prompt nunca soube que o campo `score` existia.

E a seleção do material escolhia por RECÊNCIA:

    auto/vidros    14 das 30 com score 0   média 37,8   (existem 148 com ≥70)
    auto/guincho   12 das 30 com score 0   média 45,5

A régua que fecha isso **já existia na casa** — o prompt do Estágio 1 tem 11
regras boas. 📊 Nenhuma tinha chegado ao Estágio 2.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARQUIVO = os.path.join(RAIZ, "backend", "app", "services", "attendance_distiller.py")
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _fonte() -> str:
    with open(ARQUIVO, encoding="utf-8") as arquivo:
        return arquivo.read()


def _prompt() -> str:
    """O texto do `_STAGE2_SYSTEM`, avaliado — não lido como string bruta."""
    fonte = _fonte()
    ini = fonte.index("_STAGE2_SYSTEM = (")
    fim = fonte.index("\n)\n", ini) + 2
    espaco: dict = {}
    exec(compile(fonte[ini:fim], "<prompt>", "exec"), espaco)  # noqa: S102
    return espaco["_STAGE2_SYSTEM"]


# ---------------------------------------------------------------------------
def teste_o_prompt_pede_o_observado():
    print("\n[1] Observador, não treinador")
    p = _prompt().lower()

    checar("observador" in p and "nao um treinador" in p,
           "o prompt se declara observador",
           "quem 'sintetiza o melhor' preenche lacuna com conhecimento de mundo")
    # ⚠️ "padrao-ouro" CONTINUA no texto — agora como PROIBICAO ("nao escreva
    # 'padrao-ouro'"), nao como pedido. Procurar a palavra solta reprovaria o
    # conserto: e a diferenca entre citar e mandar.
    checar("melhor treinador" not in p and "sintetize o melhor playbook" not in p,
           "CONTROLE — o PEDIDO de inventar sumiu",
           "'melhor treinador' e 'sintetize o MELHOR' eram o convite")
    checar("nao escreva" in p and "padrao-ouro" in p,
           "e 'padrao-ouro' virou proibicao explicita",
           "a palavra ficou; o que mudou foi de que lado dela o modelo esta")
    checar("nao completa" in p or "nao ensina" in p,
           "e diz o que fazer quando o material não ensina")


def teste_as_proibicoes_que_faltavam():
    print("\n[2] As quatro proibições, cada uma com defeito medido")
    p = _prompt().lower()

    checar("condicoes gerais" in p and "proibido" in p,
           "PROIBIDO afirmar cobertura",
           "📊 4 frases afirmavam, 2 em playbooks ATIVOS")
    checar("espaco em branco" in p and "colchetes" in p,
           "PROIBIDO espaço em branco em frase de saída",
           "📊 15 frases; `como_pedir` vai para o prompt do agente")
    checar("score" in p and "nao houve atendimento humano" in p,
           "o `score` entrou, e 0 é 'não houve atendimento'",
           "📊 auto/bateria: 8 de 13 com score 0")
    checar("nao pode ser pergunta" in p,
           "o que a corretora já tem NÃO se pergunta",
           "📊 30 campos perguntavam; a regra estava solta no fim")

    # CONTROLE — a regra do `ja_temos` tem de estar DENTRO da definição do
    # campo, não solta no fim. Foi por estar solta que 17 dos 18 a violaram.
    i_campo = p.find("ja_temos_na_apolice: true quando")
    i_regra = p.find("nao pode ser pergunta")
    checar(0 < i_campo < i_regra < i_campo + 900,
           "CONTROLE — e ela mora DENTRO da definição do campo",
           "regra longe do campo que governa é regra que não se aplica")


def teste_o_contrato_com_o_codigo_nao_quebrou():
    print("\n[3] CONTROLE — o código continua achando o que lê")
    p = _prompt()

    # Estas chaves são lidas por `playbook_gate`, `prompt_optimizer` e
    # `graph._conduta_do_caso`. Um prompt que parasse de pedir qualquer uma
    # delas geraria playbook que o produto não sabe usar.
    for chave in ("objetivo", "acolhimento", "pre_checks", "ficha_coleta",
                  "campo", "como_pedir", "quando", "ja_temos_na_apolice",
                  "sensibilidade", "encerramento", "frases_exemplo"):
        checar(chave in p, f"CONTROLE — o prompt continua pedindo `{chave}`",
               "é lido pelo código")

    for nova in ("o_que_evitar", "fora_do_escopo", "lastro"):
        checar(nova in p, f"e ganhou `{nova}`")


def teste_o_material_de_entrada_e_o_melhor_nao_o_mais_recente():
    print("\n[4] A seleção entrega os melhores atendimentos")
    fonte = _fonte()
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("com_humano.sort(key=_nota, reverse=True)" in cmd,
           "ordena por NOTA, não por recência",
           "📊 auto/vidros recebia média 37,8 existindo 148 sessões com ≥70")
    checar('_nota(d) > 0 and (d.get("resumo_conduta") or [])' in cmd,
           "e descarta o que não teve atendimento humano",
           "score 0 E conduta vazia — os conjuntos não coincidem")

    # 🔴 A ordenação NÃO pode voltar para o banco: `->>` devolve TEXTO e
    # "9" > "70" em ordem lexicográfica. Seria uma ordenação que parece
    # funcionar e entrega o inverso.
    checar('.order("summary->distilled->>score"' not in cmd,
           "CONTROLE — a ordenação NÃO é feita no banco",
           '`->>` devolve texto: "9" seria maior que "70"')

    # CONTROLE — a janela de recência continua existindo. Conduta de um ano
    # atrás pode estar vencida; o filtro é sobre a ESCOLHA dentro dela.
    checar("janela = max(limit * 6, 180)" in cmd and 'order("started_at", desc=True)' in cmd,
           "CONTROLE — e a janela de recência continua",
           "escolher os melhores não é ignorar que conduta envelhece")


def teste_o_piso_de_evidencia():
    print("\n[5] Três conversas não é evidência")
    fonte = _fonte()

    checar("_MIN_SESSIONS_DEFAULT = 12" in fonte,
           "o piso subiu de 3 para 12 atendimentos ÚTEIS",
           "📊 12 é onde o acervo tem um degrau: 8 → 12 → 17")

    # CONTROLE — o piso continua configurável sem deploy, e o número não pode
    # ser tão alto que mate os grupos bons.
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))
    checar("DISTILLER_MIN_SESSIONS" in cmd,
           "CONTROLE — e continua ajustável por ambiente")

    import re
    achado = re.search(r"_MIN_SESSIONS_DEFAULT = (\d+)", fonte)
    valor = int(achado.group(1)) if achado else 0
    checar(3 < valor <= 12,
           "CONTROLE — o piso não é alto a ponto de matar grupo bom",
           f"{valor}: acima de 12 cortaria residencial/chaveiro (12), "
           f"residencial/vidros (17) e auto/pneu (19), que são os bons")


def main() -> int:
    print("=" * 70)
    print("O PLAYBOOK EXTRAI O OBSERVADO")
    print("=" * 70)
    teste_o_prompt_pede_o_observado()
    teste_as_proibicoes_que_faltavam()
    teste_o_contrato_com_o_codigo_nao_quebrou()
    teste_o_material_de_entrada_e_o_melhor_nao_o_mais_recente()
    teste_o_piso_de_evidencia()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o playbook diz o que viu, e diz o que não viu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
