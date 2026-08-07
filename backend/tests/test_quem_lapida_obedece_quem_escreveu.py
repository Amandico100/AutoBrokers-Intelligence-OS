"""O Lapidador reescreve o playbook que está NO AR — com regras de outra época.

A HISTÓRIA
==========
Duas peças escrevem o mesmo playbook:

    attendance_distiller._STAGE2_SYSTEM   escreve pela PRIMEIRA vez (draft)
    prompt_optimizer._REFLECT_SYSTEM      REESCREVE o que já está ATIVO

Em 07/08/2026 o primeiro ganhou três campos novos (`o_que_evitar`,
`fora_do_escopo`, `lastro`) e quatro proibições, cada uma com defeito medido
atrás: espaço em branco em frase de saída, afirmar cobertura, perguntar o que a
corretora já tem, inventar o que o material não ensina.

O segundo não ganhou nada. E ele:

    📊 opera sobre playbooks com status ATIVO — os 12 que estão no ar
    📊 pedia um JSON com 8 chaves — as 3 novas não estavam entre elas

**O que ele omitisse, sumiria.** Os defeitos corrigidos à mão nos ativos (10
frases com espaço em branco, 1 afirmando cobertura) voltariam pela porta dos
fundos — porque quem reescreve não sabia que tinham sido defeitos.

A JANELA, MEDIDA — NÃO A QUE EU TINHA ESCRITO
=============================================
Escrevi primeiro que a janela era de 60 minutos, porque o job está agendado a
cada 3.600s. Está — mas a rodada tem dois portões que eu não tinha lido: só
entre 3h e 10h UTC, e no máximo uma vez por semana. A janela real é **a próxima
madrugada que completar 7 dias**.

📊 E 07/08/2026, nos 18 playbooks do banco: `_mudancas` em **0**. O Lapidador
nunca rodou — os 12 ativos existem desde 29/07. Então o risco não era iminente;
era certo e sem data. O que não muda o conserto, muda o tamanho do susto — e um
número que eu não medi não vira urgência num commit.

A CAUSA NÃO ERA O TEXTO
=======================
Era existirem **duas descrições do mesmo playbook**. Enquanto forem duas, elas
divergem — e a divergência é invisível: os dois prompts continuam válidos,
continuam gerando JSON, e o gate não reprova um playbook por ter campos a
MENOS.

Por isso o conserto não foi reescrever o segundo prompt com as mesmas regras.
Foi fazê-lo **importar** o primeiro. Este teste guarda o import, não o texto:
regra nova escrita no Estágio 2 já nasce valendo para o Lapidador, sem que
ninguém precise lembrar de copiá-la.
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAPIDADOR = os.path.join(RAIZ, "backend", "app", "services", "prompt_optimizer.py")
DISTILADOR = os.path.join(RAIZ, "backend", "app", "services", "attendance_distiller.py")
AGENDADOR = os.path.join(RAIZ, "backend", "app", "tasks", "buffer_processor.py")
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read()


def _regras_do_estagio_2() -> str:
    """O texto do `_STAGE2_SYSTEM`, avaliado — a única fonte das regras."""
    fonte = _ler(DISTILADOR)
    ini = fonte.index("_STAGE2_SYSTEM = (")
    fim = fonte.index("\n)\n", ini) + 2
    espaco: dict = {}
    exec(compile(fonte[ini:fim], "<prompt>", "exec"), espaco)  # noqa: S102
    return espaco["_STAGE2_SYSTEM"]


# ---------------------------------------------------------------------------
def teste_o_lapidador_importa_as_regras_em_vez_de_copiar():
    print("\n[1] Uma fonte, não duas")
    fonte = _ler(LAPIDADOR)

    # AST, não busca de texto: um `REGRAS_DO_PLAYBOOK` citado num comentário
    # ou numa docstring passaria numa busca por substring e não importaria
    # nada. Guarda que aceita menção no lugar de import não guarda nada.
    importa = False
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.ImportFrom) and "attendance_distiller" in (no.module or ""):
            importa = any(a.name == "REGRAS_DO_PLAYBOOK" for a in no.names)
            if importa:
                break
    checar(importa,
           "o Lapidador IMPORTA as regras de quem escreve o playbook",
           "regra nova no Estágio 2 já nasce valendo aqui")

    # E o nome importado existe do outro lado, apontando para o prompt real.
    d = _ler(DISTILADOR)
    checar("REGRAS_DO_PLAYBOOK = _STAGE2_SYSTEM" in d,
           "e o nome existe no distilador, ligado ao prompt de verdade",
           "import de nome que não existe quebra o worker no start")

    # CONTROLE — e ele de fato ENTRA no prompt do Lapidador. Importar e não
    # usar é a mesma divergência com uma linha a mais.
    ini = fonte.index("_REFLECT_SYSTEM = (")
    fim = fonte.index("\n)\n", ini)
    checar("REGRAS_DO_PLAYBOOK" in fonte[ini:fim],
           "CONTROLE — e as regras entram no texto do prompt",
           "import não usado é divergência com uma linha a mais")


def teste_as_regras_novas_chegam_a_quem_reescreve():
    print("\n[2] O que o Lapidador teria apagado")
    regras = _regras_do_estagio_2().lower()

    # Estes três campos são o motivo do conserto: o esquema antigo do
    # Lapidador não os pedia, e o que ele não pede some do playbook ativo.
    for campo in ("o_que_evitar", "fora_do_escopo", "lastro"):
        checar(campo in regras,
               f"`{campo}` está nas regras que o Lapidador recebe",
               "o que ele não pede, some do playbook que está no ar")

    # E as quatro proibições, que o esquema antigo também não trazia.
    checar("condicoes gerais" in regras and "proibido" in regras,
           "a proibição de afirmar cobertura chega a quem reescreve")
    checar("espaco em branco" in regras,
           "a proibição de espaço em branco também")
    checar("nao pode ser pergunta" in regras,
           "e a regra do que a corretora já tem")


def teste_o_lapidador_ainda_e_um_lapidador():
    print("\n[3] Herdar as regras não é virar o outro")
    fonte = _ler(LAPIDADOR)
    ini = fonte.index("_REFLECT_SYSTEM = (")
    fim = fonte.index("\n)\n", ini)
    prompt = fonte[ini:fim].lower()

    # O Lapidador tem um trabalho DIFERENTE: ele parte de um playbook que já
    # existe. Se herdasse as regras e perdesse isso, reescreveria do zero um
    # playbook cujo material de origem ele não está vendo.
    checar("_mudancas" in prompt,
           "continua pedindo o registro do que mudou",
           "é o que o gate e o histórico leem")
    checar("feedback" in prompt,
           "continua sabendo que o material dele é o feedback")
    checar("ja esta no ar" in prompt or "já está no ar" in prompt,
           "e sabe que o playbook já está em produção")
    checar("preserve" in prompt and "lastro" in prompt,
           "preserva o lastro medido sobre atendimentos que não está vendo",
           "reescrever não dá acesso ao material original")

    # CONTROLE — o esquema ANTIGO, com 8 chaves e sem os campos novos, tem de
    # ter sumido. Se as duas listas coexistissem, o modelo seguiria a última.
    checar('\\"sensibilidade\\": \\"...\\", \\"encerramento\\"' not in fonte,
           "CONTROLE — o esquema antigo de 8 chaves sumiu",
           "dois esquemas no mesmo prompt: o modelo obedece um deles")


def teste_ele_roda_sozinho_sobre_o_que_esta_no_ar():
    print("\n[4] CONTROLE — o defeito tinha hora marcada, e qual")
    agendador = _ler(AGENDADOR)
    lapidador = _ler(LAPIDADOR)

    checar("lapidador_check" in agendador,
           "CONTROLE — o Lapidador está no agendador",
           "sem isso o defeito seria teórico; com isso, tinha hora marcada")

    # 🔴 A CADÊNCIA REAL — e ela NÃO é de hora em hora.
    # O job acorda a cada 3.600s, mas a rodada tem dois portões: só entre 3h e
    # 10h UTC, e no máximo uma vez por semana (marcador no Redis). Escrever
    # "a janela era de 60 minutos" seria dramatizar um número que não medi.
    i = agendador.find("lapidador_check")
    checar("seconds=3600" in agendador[max(0, i - 400):i],
           "o job acorda de hora em hora")
    checar("now.hour not in range(3, 10)" in lapidador,
           "mas só age na madrugada BRT")
    checar("_WEEKLY_S = 7 * 86400" in lapidador and "< _WEEKLY_S" in lapidador,
           "e no máximo uma vez por semana",
           "a janela real é a próxima madrugada que completar 7 dias")

    # CONTROLE — o alvo continua sendo o que está ATIVO. Um Lapidador que só
    # mexesse em rascunho não justificaria pressa nenhuma.
    checar('.eq("status", "active")' in lapidador,
           "CONTROLE — e o alvo dele são os playbooks ATIVOS",
           "📊 12 ativos; foi neles que as 10 frases foram corrigidas à mão")


def main() -> int:
    print("=" * 70)
    print("QUEM LAPIDA OBEDECE QUEM ESCREVEU")
    print("=" * 70)
    teste_o_lapidador_importa_as_regras_em_vez_de_copiar()
    teste_as_regras_novas_chegam_a_quem_reescreve()
    teste_o_lapidador_ainda_e_um_lapidador()
    teste_ele_roda_sozinho_sobre_o_que_esta_no_ar()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — uma descrição do playbook, não duas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
