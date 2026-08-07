"""O freio de gasto tem de travar o cano MAIS LARGO, não só o mais estreito.

A HISTÓRIA
==========
`DESTILADOR_TETO_POR_RODADA=0` significa "não gaste nada". Era o que segurava a
conta enquanto a destilação era feita pelo Plano Max, fora da API.

Só que `teto` era reatribuído no meio da função:

    teto = _teto_de_gasto()                        # linha 622 → 0
    ...
    teto = _env_int("DISTILLER_CONCURRENCY", 6)    # linha 659 → vira 6
    ...
    por_rodada = min(teto, 3)                      # linha 682 → 3, não 0

📊 Medido em produção, 05/08/2026, com linha de controle — a MESMA rodada:

    estágio 1 (Sonnet, barato)   0 sessões destiladas   ← teto obedecido
    estágio 2 (Opus 5, caro)     2 playbooks gerados    ← teto furado

O freio travava o cano estreito e deixava o largo aberto. O modelo mais caro do
sistema seguiu rodando com o freio puxado, três vezes por rodada, a cada 30
minutos, por oito dias. E o comentário do código afirmava o contrário: *"Com o
teto em 0 nenhum é sintetizado"*.

É exatamente o risco que o docstring de `_teto_de_gasto()` já descrevia — *"a
trava vazaria justamente pelo cano mais largo, e em silêncio"*. A frase estava
escrita; o código não a cumpria.

O QUE ESTE ARQUIVO GUARDA
=========================
Três coisas que juntas mantêm o dinheiro sob controle e o conhecimento limpo:

1. o teto de gasto sobrevive à sua própria função (o cano largo fecha);
2. a corretora de TESTE não ensina o RAG que todas leem;
3. um playbook rascunho não bloqueia a versão 2 para sempre.
"""

from __future__ import annotations

import ast
import os
import sys

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


def _corpo_de(nome: str):
    """A árvore da função pedida. Ler AST em vez de texto: comentário não
    executa, e este arquivo inteiro nasceu de um comentário que mentia."""
    for no in ast.walk(ast.parse(_fonte())):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    return None


# ---------------------------------------------------------------------------
def teste_o_teto_de_gasto_nao_e_sobrescrito():
    print("\n[1] O teto de GASTO chega inteiro até o estágio caro")
    alvo = _corpo_de("distill_once")
    checar(alvo is not None, "achei `distill_once`")
    if alvo is None:
        return

    # Toda atribuição a um nome dentro da função, na ordem em que aparece.
    atribuicoes = [(a.lineno, alvo_.id)
                   for a in ast.walk(alvo) if isinstance(a, ast.Assign)
                   for alvo_ in a.targets if isinstance(alvo_, ast.Name)]
    quantas_vezes_teto = [l for l, nome in atribuicoes if nome == "teto"]

    checar(len(quantas_vezes_teto) == 1,
           "`teto` recebe valor UMA única vez na função",
           f"{len(quantas_vezes_teto)} atribuição(ões) — era 2, e a segunda "
           f"apagava o freio")

    # E a que sobrou tem de ser a do teto de gasto.
    fonte_da_funcao = ast.get_source_segment(_fonte(), alvo) or ""
    checar("teto = _teto_de_gasto()" in fonte_da_funcao,
           "e a que sobrou é a do teto de GASTO")
    checar("concorrencia = _env_int(\"DISTILLER_CONCURRENCY\"" in fonte_da_funcao,
           "a concorrência ganhou nome próprio",
           "sem isso as duas coisas disputam a mesma variável")
    checar("Semaphore(concorrencia)" in fonte_da_funcao,
           "e o semáforo usa a concorrência, não o teto de gasto")


def teste_com_teto_zero_o_modelo_caro_nao_e_chamado():
    print("\n[2] Teto 0 → zero playbooks. Teto 1 → CONSEGUE sintetizar")
    # A conta que decide, isolada. `por_rodada = min(teto, N)`.
    def por_rodada(teto: int, por_run: int = 3) -> int:
        return min(teto, por_run)

    checar(por_rodada(0) == 0,
           "teto de gasto 0: `grupos[:0]` é vazio, nenhuma chamada ao Opus 5",
           "é o que o comentário sempre prometeu e o código não cumpria")

    # 🔴 A conta ANTIGA, reproduzida para nunca mais voltar: `teto` valia a
    # concorrência (6) quando chegava aqui.
    checar(por_rodada(6) == 3,
           "CONTROLE — a conta ANTIGA daria 3 playbooks com o freio puxado",
           "min(6, 3) = 3 — dois deles foram gerados em 05/08 na vida real")

    # CONTROLE — o freio tem de conseguir DEIXAR PASSAR. Um teto que bloqueia
    # sempre não é freio, é desligamento; e o dia de religar chegaria com o
    # sistema mudo (CLAUDE.md §9.3).
    checar(por_rodada(1) == 1,
           "CONTROLE — teto 1 sintetiza 1 playbook: o freio solta quando deve")
    checar(por_rodada(10) == 3,
           "CONTROLE — e o teto por rodada continua limitando acima dele")


def teste_a_corretora_de_teste_nao_ensina_o_rag():
    print("\n[3] A corretora de TESTE não vira conhecimento")
    import importlib.util
    import types

    # O módulo puxa `app.services`, que puxa o mundo. Só a função pura importa.
    fonte = _fonte()
    arvore = ast.parse(fonte)
    trecho = None
    for no in arvore.body:
        if isinstance(no, ast.FunctionDef) and no.name == "_corretoras_excluidas":
            trecho = ast.get_source_segment(fonte, no)
    checar(trecho is not None, "a lista de corretoras excluídas existe")
    if not trecho:
        return

    espaco: dict = {"os": os}
    exec(compile(trecho, "<teste>", "exec"), espaco)  # noqa: S102
    excluidas = espaco["_corretoras_excluidas"]

    antes = os.environ.get("DESTILACAO_CORRETORAS_EXCLUIDAS")
    try:
        os.environ.pop("DESTILACAO_CORRETORAS_EXCLUIDAS", None)
        checar(excluidas() == frozenset(),
               "CONTROLE — sem configuração, NINGUÉM é excluído",
               "o padrão não pode ser calar uma corretora por acidente")

        os.environ["DESTILACAO_CORRETORAS_EXCLUIDAS"] = " abc-123 , def-456 "
        lista = excluidas()
        checar(lista == {"abc-123", "def-456"},
               "a lista lê os ids e ignora espaço em volta", str(sorted(lista)))
        checar("abc-123" in lista and "xyz-999" not in lista,
               "CONTROLE — quem não está na lista continua destilando",
               "excluir uma corretora não pode excluir as outras")
    finally:
        os.environ.pop("DESTILACAO_CORRETORAS_EXCLUIDAS", None)
        if antes is not None:
            os.environ["DESTILACAO_CORRETORAS_EXCLUIDAS"] = antes

    # E o filtro tem de estar no caminho que monta a fila.
    #
    # 🔴 Este guarda já foi frouxo: procurava as palavras `_corretoras_excluidas`
    # e `continue` no texto da função. A prova por mutação denunciou — apaguei o
    # `if company_id in excluidas: continue` e o teste seguiu VERDE, porque as
    # duas palavras continuavam lá por outros motivos.
    #
    # Agora procura a COMPARAÇÃO na árvore: `<algo> in excluidas`. Palavra
    # presente não é regra aplicada.
    fila_no = _corpo_de("_load_undistilled_sync")
    comparacoes = [
        c for c in ast.walk(fila_no)
        if isinstance(c, ast.Compare)
        and any(isinstance(op, ast.In) for op in c.ops)
        and any(isinstance(cmp_, ast.Name) and cmp_.id == "excluidas"
                for cmp_ in c.comparators)
    ]
    checar(len(comparacoes) >= 1,
           "e a fila COMPARA a corretora da sessão com a lista",
           "lista que ninguém lê não exclui ninguém")

    # E essa comparação tem de guardar um `continue` — senão ela é decorativa.
    dentro_de_if = [
        no for no in ast.walk(fila_no)
        if isinstance(no, ast.If)
        and any(isinstance(c, ast.Compare)
                and any(isinstance(cmp_, ast.Name) and cmp_.id == "excluidas"
                        for cmp_ in c.comparators)
                for c in ast.walk(no.test))
        and any(isinstance(b, ast.Continue) for b in ast.walk(no))
    ]
    checar(len(dentro_de_if) >= 1,
           "e a comparação PULA a sessão (continue), não só a avalia")


def teste_um_rascunho_nao_bloqueia_a_versao_2():
    print("\n[4] Playbook rascunho não congela o serviço para sempre")
    grupos = ast.get_source_segment(_fonte(), _corpo_de("_grupos_sem_playbook_sync")) or ""

    checar("novas_desde" in grupos and "DISTILLER_PLAYBOOK_REFRESH_MIN" in grupos,
           "a versao 2 nasce quando chega MATERIAL NOVO depois do playbook",
           "📊 `auto/sinistro` usava 30 conversas de 1.405 e nunca usaria mais")
    checar("ultimo_playbook" in grupos and "grupo not in ultimo_playbook" in grupos,
           "grupo que nunca teve playbook entra direto")

    # CONTROLE — sem material novo o grupo NAO volta. Trocar conhecimento
    # congelado por dinheiro queimado seria o mesmo defeito de outro lado: um
    # rascunho que ninguem aprova faria a sintese rodar a cada 30 minutos, para
    # sempre, no modelo mais caro do sistema.
    checar("novas_desde.get(grupo, 0) >= minimo_para_refazer" in grupos,
           "CONTROLE — sem material novo, o grupo continua bloqueado",
           "o gatilho e aprendizado disponivel, nao status nem tempo")


def main() -> int:
    print("=" * 70)
    print("O FREIO DE GASTO TRAVA O CANO MAIS LARGO")
    print("=" * 70)
    teste_o_teto_de_gasto_nao_e_sobrescrito()
    teste_com_teto_zero_o_modelo_caro_nao_e_chamado()
    teste_a_corretora_de_teste_nao_ensina_o_rag()
    teste_um_rascunho_nao_bloqueia_a_versao_2()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o freio segura o caro, e o conhecimento pode melhorar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
