"""Ninguém volta a pedir mais de mil linhas achando que vai recebê-las.

POR QUE ESTE ARQUIVO EXISTE
===========================
O PostgREST devolve no máximo **1.000 linhas por resposta** e ignora o
`.limit(N)` pedido acima disso — sem erro, sem log, sem sintoma. Em 06/08/2026
uma auditoria encontrou 28 lugares no backend pedindo mais que isso e recebendo
1.000 caladamente. Os cinco que mexiam com dinheiro e com memória do agente
foram corrigidos.

Mas consertar 5 e deixar a porta aberta é como este problema nasceu.

📊 O repositório já tinha, ANTES da auditoria, três arquivos com comentários
longos e precisos sobre exatamente este defeito — `weaver.py` (28/07),
`curadoria_cartas.py` e `attendance_distiller.py` (05/08). Nenhum virou regra.
**A lição foi aprendida três vezes e migrou zero vezes.** Daqui a três meses
alguém escreve `.limit(9000)` de boa-fé, e a auditoria inteira recomeça.

Este teste é a migração da lição (CLAUDE.md §9.3). Ele reprova quando aparece
um pedido acima de mil linhas sem paginação e sem justificativa escrita.

COMO PASSAR NESTE TESTE
=======================
Três caminhos, todos legítimos:

1. **Pagine** — use `app.leitura_completa.ler_paginado`. É o certo quando
   você precisa mesmo de todas as linhas.
2. **Some no banco** — se você só quer um número, `count`/`sum` no Postgres é
   uma ida em vez de N.
3. **Declare que é um recorte** — se pegar as N mais recentes é o que você quer
   mesmo, escreva `# recorte:` na linha de cima dizendo por quê. O teste aceita,
   e o próximo leitor entende que foi decisão e não descuido.

O QUE ESTE TESTE **NÃO** FAZ
============================
Não persegue os limites que protegem custo. `.limit(80)` de mensagens que vão
para a LLM ler é teto de token, não descuido — e mexer nele aumenta a conta.
Por isso o gatilho é 1.000: abaixo disso o servidor entrega o que se pediu, e o
número é uma decisão de quem escreveu.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(RAIZ, "backend", "app")
_PROBLEMAS: list = []

# Acima disto o servidor manda 1.000 e não avisa. Abaixo, o `.limit()` é
# obedecido e o número é uma escolha de quem escreveu — que este teste respeita.
TETO_DO_SERVIDOR = 1000

_PEDIDO = re.compile(r"\.limit\(\s*(\d[\d_]*)\s*\)")

# A linha (ou a de cima) que salva um pedido grande.
_PERDAO = ("ler_paginado", ".range(", "# recorte:", "# recorte de", "_TESTE_")


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _arquivos_python():
    for raiz, _dirs, nomes in os.walk(BACKEND):
        if "__pycache__" in raiz:
            continue
        for nome in nomes:
            if nome.endswith(".py"):
                yield os.path.join(raiz, nome)


def _pedidos_grandes() -> list:
    """Cada `.limit(N>1000)` que não tem paginação nem justificativa por perto.

    🔴 LÊ A ÁRVORE DO CÓDIGO, NÃO O TEXTO.
    ======================================
    A primeira versão usava expressão regular sobre as linhas, e acusou três
    lugares que estavam CERTOS: os comentários e docstrings que explicam este
    mesmo defeito citam `.limit(2000)` e `.limit(5000)` como exemplo do que não
    fazer. Um guarda que briga com a documentação do próprio conserto ensina a
    desligá-lo — e um guarda desligado não guarda nada.

    Com AST, prosa não é código: só chamadas de verdade entram.
    """
    import ast

    achados = []
    for caminho in _arquivos_python():
        with open(caminho, encoding="utf-8") as arquivo:
            fonte = arquivo.read()
        linhas = fonte.split("\n")
        try:
            arvore = ast.parse(fonte)
        except SyntaxError:
            # Arquivo que nem compila é problema de outro teste.
            continue
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            alvo = no.func
            if not (isinstance(alvo, ast.Attribute) and alvo.attr == "limit"):
                continue
            if not no.args or not isinstance(no.args[0], ast.Constant):
                continue
            quanto = no.args[0].value
            if not isinstance(quanto, int) or quanto <= TETO_DO_SERVIDOR:
                continue
            i = no.lineno - 1
            # Olha a vizinhança: a paginação e a justificativa costumam estar
            # uma ou duas linhas acima, não coladas no `.limit(`.
            vizinhanca = "\n".join(linhas[max(0, i - 3): i + 2])
            if any(p in vizinhanca for p in _PERDAO):
                continue
            achados.append((os.path.relpath(caminho, RAIZ).replace("\\", "/"),
                            no.lineno, quanto, linhas[i].strip()))
    return achados


# --------------------------------------------------------------------------
# 🟠 A DÍVIDA CONHECIDA — 06/08/2026, P-122 em `docs/canon/PENDENCIAS.md`.
#
# Estes lugares pedem mais de mil linhas e recebem mil. Nenhum deles erra HOJE:
# 📊 as tabelas de inteligência e pesquisa ainda são pequenas
# (`intelligence_signals` = 21 linhas, `intelligence_findings` = 6,
# `research_*` praticamente vazias). Todos agregam ou contam, então no dia em
# que a tabela crescer eles passam a errar em silêncio.
#
# POR QUE ELES CONTINUAM AQUI, E ISSO É DECISÃO E NÃO PREGUIÇA
# ============================================================
# 06/08/2026, decisão do Founder: consertar o que dá dinheiro e o que afeta a
# qualidade da conversa, e NÃO mexer no que ainda não dói — porque cada arquivo
# tocado é uma chance de bug novo, e bug novo atrasa o lançamento.
#
# Esta lista é o contrário de esconder: ela é o que impede que a dívida cresça.
# Um item novo em QUALQUER arquivo reprova o teste; e um item consertado também
# reprova, cobrando a remoção da linha — senão a lista apodrece e vira mais uma
# coisa que ninguém sabe se ainda é verdade.
#
# Contagem por ARQUIVO, não por número de linha: linha muda com qualquer edição
# e o guarda viraria ruído. Arquivo é estável.
_DIVIDA_CONHECIDA = {
    "backend/app/agents/gateway_cutover.py": 1,
    "backend/app/api/admin_atlas.py": 1,
    "backend/app/api/research.py": 4,
    "backend/app/services/intelligence/detectors/qualidade.py": 1,
    "backend/app/services/intelligence/feedback_service.py": 2,
    "backend/app/services/intelligence/rule_engine.py": 5,
    "backend/app/services/observability/sli.py": 1,
    "backend/app/services/regression_sentinel.py": 1,
    "backend/app/services/research/monitor_service.py": 1,
}


def teste_nenhum_pedido_grande_NOVO():
    print("\n[1] Nenhum `.limit()` acima de mil NOVO no backend")
    from collections import Counter

    achados = _pedidos_grandes()
    por_arquivo = Counter(c for c, _l, _q, _t in achados)

    novos = []
    for caminho, linha, quanto, texto in achados:
        if por_arquivo[caminho] > _DIVIDA_CONHECIDA.get(caminho, 0):
            novos.append((caminho, linha, quanto, texto))

    for caminho, linha, quanto, texto in novos:
        checar(False,
               f"{caminho}:{linha} pede {quanto} linhas e recebe {TETO_DO_SERVIDOR}",
               texto[:80])
    if not novos:
        checar(True,
               f"nenhum pedido grande novo (dívida conhecida: "
               f"{sum(_DIVIDA_CONHECIDA.values())} em {len(_DIVIDA_CONHECIDA)} arquivos)",
               "pagine, some no banco, ou escreva `# recorte:` dizendo por quê")


def teste_a_divida_nao_apodrece():
    print("\n[2] A lista de dívida diz a verdade sobre hoje")
    from collections import Counter

    por_arquivo = Counter(c for c, _l, _q, _t in _pedidos_grandes())
    for caminho, quantos in sorted(_DIVIDA_CONHECIDA.items()):
        atual = por_arquivo.get(caminho, 0)
        if atual < quantos:
            checar(False,
                   f"{caminho} melhorou ({quantos} → {atual}) — atualize _DIVIDA_CONHECIDA",
                   "lista que não encolhe com o conserto vira ficção")
    if all(por_arquivo.get(c, 0) == q for c, q in _DIVIDA_CONHECIDA.items()):
        checar(True, "a lista bate exatamente com o que existe no código",
               f"{sum(_DIVIDA_CONHECIDA.values())} pedidos, todos registrados em P-122")


def teste_o_guarda_tem_como_falhar():
    print("\n[2] CONTROLE — o guarda CONSEGUE reprovar")
    # Um guarda que não tem como falhar não guarda nada (CLAUDE.md §9.3).
    # Aqui a varredura roda contra um arquivo de mentira que tem o defeito.
    import tempfile

    global BACKEND
    verdadeiro = BACKEND
    try:
        with tempfile.TemporaryDirectory() as pasta:
            with open(os.path.join(pasta, "descuidado.py"), "w", encoding="utf-8") as f:
                f.write('linhas = db.table("x").select("*").limit(5000).execute()\n')
            BACKEND = pasta
            checar(len(_pedidos_grandes()) == 1,
                   "CONTROLE — um `.limit(5000)` solto É encontrado",
                   "sem isto, o teste [1] passaria por não procurar nada")

            # E o perdão funciona: o mesmo pedido, paginado, não acusa.
            with open(os.path.join(pasta, "descuidado.py"), "w", encoding="utf-8") as f:
                f.write("linhas, _ = ler_paginado(\n"
                        '    lambda: db.table("x").select("*"),\n'
                        '    chave_unica="id", teto=5000)\n'
                        'outro = db.table("y").select("*").limit(5000).execute()\n')
            checar(len(_pedidos_grandes()) == 0,
                   "CONTROLE — e o mesmo número, com `ler_paginado` por perto, passa",
                   "senão o guarda brigaria com o próprio conserto")

            # E o recorte declarado passa.
            with open(os.path.join(pasta, "descuidado.py"), "w", encoding="utf-8") as f:
                f.write("# recorte: as 2.000 mais recentes bastam para o gráfico\n"
                        'linhas = db.table("x").select("*").limit(2000).execute()\n')
            checar(len(_pedidos_grandes()) == 0,
                   "CONTROLE — recorte declarado por escrito passa",
                   "decisão explicada não é descuido")

            # CONTROLE do CONTROLE — abaixo de mil não é assunto deste teste.
            with open(os.path.join(pasta, "descuidado.py"), "w", encoding="utf-8") as f:
                f.write('msgs = db.table("m").select("*").limit(80).execute()\n')
            checar(len(_pedidos_grandes()) == 0,
                   "CONTROLE — `.limit(80)` (teto de token) NÃO é acusado",
                   "perseguir isso aumentaria a conta de IA, que é o oposto do objetivo")
    finally:
        BACKEND = verdadeiro


def main() -> int:
    print("=" * 70)
    print("NINGUÉM PEDE MAIS DE MIL LINHAS DE NOVO")
    print("=" * 70)
    teste_nenhum_pedido_grande_NOVO()
    teste_a_divida_nao_apodrece()
    teste_o_guarda_tem_como_falhar()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        print("\nComo resolver: pagine com `app.leitura_completa.ler_paginado`,")
        print("some no banco, ou escreva `# recorte:` explicando a decisão.")
        return 1
    print("TUDO VERDE — a porta que abriu 28 buracos está fechada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
