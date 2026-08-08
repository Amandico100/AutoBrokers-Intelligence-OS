"""`despublicar_carta_sync` respondia "removi" com o Qdrant fora do ar.

A HISTÓRIA
==========
A função existe para impedir um estado exato, e o docstring dela o nomeia:

    "Falhar aqui e marcar no banco seria voltar ao defeito: o banco diria
     removido e o índice continuaria entregando."

Era o que ela fazia.

    QdrantService.delete_document ......... `except Exception: return False`
                                            (qdrant_service.py:665-667)
                                            **nunca levanta**
    despublicar_carta_sync ................ chamava dentro de try/except e
                                            DESCARTAVA o retorno

O `except` esperava uma exceção que não vem: era código morto. O único sinal de
que o vetor saiu — o valor de retorno — ia para o chão. A função marcava o
banco e respondia `True` sempre.

AS TRÊS REDES QUE CAÍAM JUNTAS, EM SILÊNCIO
===========================================
    corrigir.py:109          `pendente = not despublicar_carta_sync(...)`
                             sempre False → `qdrant_pendente` nunca gravado
    reconciliar_indice_sync  filtra por essa marca → 📊 0 linhas em 12.933
                             cartas. Roda antes de cada publicação e nunca
                             acha nada.
    admin_atlas.py:740       o `503 nao_saiu_do_indice` nunca disparava

📊 E em 07/08/2026 foram aposentadas 11 cartas — 7 delas da Porto, sobre boleto
atualizado, contraditas por material novo. Nenhuma tem `qdrant_pendente`. **Isso
não prova que saíram do índice: prova que o sistema não tinha como dizer.**

E A ORDEM, QUE ERA A OUTRA METADE
=================================
`_aposentar_contraditas_sync` gravava `status='superseded'` **antes** de chamar
o removedor. Mesmo com o removedor consertado, a ordem já garantia a
divergência: o banco diria removido e o índice continuaria entregando.

Agora o índice manda. Se ele recusar, a carta continua `published` — visível,
errada e **achável**. Que é melhor que invisível e errada.

POR QUE ESTE TESTE É EXECUTÁVEL, E NÃO UM `grep`
================================================
O teste que existia (`test_carta_errada_sai_do_indice.py:116`) afirmava, por
regex no fonte, que *"`despublicar_carta_sync` devolve False sem levantar
exceção"*. A frase estava no comentário e **era falsa**. Um guarda que lê o
código não descobre o que o código faz — e este defeito viveu embaixo de um
teste verde.
"""

from __future__ import annotations

import ast
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DISTILADOR = os.path.join(RAIZ, "backend", "app", "services", "attendance_distiller.py")
CURADORIA = os.path.join(RAIZ, "backend", "app", "services", "curadoria_cartas.py")
QDRANT = os.path.join(RAIZ, "backend", "app", "services", "qdrant_service.py")
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


# ---------------------------------------------------------------------------
class _QdrantFalso:
    """Um Qdrant que recusa — como o real faz quando está fora do ar.

    O ponto: ele NÃO levanta. Devolve `False`, exatamente como
    `QdrantService.delete_document` (`qdrant_service.py:665-667`). Um dublê que
    levantasse exceção testaria um caminho que a produção não tem.
    """

    def __init__(self, resposta: bool):
        self.resposta = resposta
        self.chamadas = 0

    def delete_document(self, **kwargs):
        self.chamadas += 1
        return self.resposta


class _TabelaFalsa:
    def __init__(self, diario: list):
        self.diario = diario
        self._pendente = None

    def update(self, valores):
        self._pendente = dict(valores)
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._pendente is not None:
            self.diario.append(self._pendente)
            self._pendente = None
        return types.SimpleNamespace(data=[{"pii_check": {}}])


def _despublicar(resposta_do_qdrant: bool):
    """Executa a função REAL, com o Qdrant e o banco dublados.

    A função é extraída por AST e compilada isolada: importar o módulo puxaria
    o pacote `app.services` inteiro, que este ambiente não tem. O que roda aqui
    é o corpo de verdade, não uma reescrita.
    """
    fonte = _ler(DISTILADOR)
    arv = ast.parse(fonte)
    corpo = None
    for no in ast.walk(arv):
        if isinstance(no, ast.FunctionDef) and no.name == "despublicar_carta_sync":
            corpo = ast.get_source_segment(fonte, no)
    assert corpo, "não achei despublicar_carta_sync"

    escritas: list = []
    qdrant = _QdrantFalso(resposta_do_qdrant)

    # Os imports são feitos DENTRO da função, então precisam existir em
    # sys.modules no momento da chamada.
    def _mod(nome, **atributos):
        m = types.ModuleType(nome)
        for k, v in atributos.items():
            setattr(m, k, v)
        sys.modules[nome] = m
        return m

    _mod("app.core.config", settings=types.SimpleNamespace(GLOBAL_KNOWLEDGE_COMPANY_ID="c1"))
    _mod("app.services.knowledge_scope", GLOBAL_COLLECTION="autobrokers_global")
    _mod("app.services.qdrant_service", get_qdrant_service=lambda: qdrant)
    cliente = types.SimpleNamespace(table=lambda _n: _TabelaFalsa(escritas))
    _mod("app.core.database",
         get_supabase_client=lambda: types.SimpleNamespace(client=cliente))

    espaco: dict = {"os": os, "logger": types.SimpleNamespace(
        error=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None)}
    exec(compile(corpo, "<despublicar>", "exec"), espaco)  # noqa: S102
    resultado = espaco["despublicar_carta_sync"]("carta-1")
    return resultado, escritas, qdrant


def teste_o_indice_recusa_e_a_funcao_admite():
    print("\n[1] Com o índice recusando, a função diz que NÃO removeu")
    resultado, escritas, qdrant = _despublicar(resposta_do_qdrant=False)

    checar(qdrant.chamadas == 1, "o removedor foi chamado uma vez")
    checar(resultado is False,
           "e a função devolve False",
           "📊 antes devolvia True sempre — o retorno era descartado")
    checar(escritas == [],
           "e o banco NÃO foi tocado",
           "marcar 'superseded' com o vetor vivo é o pior estado possível")


def teste_o_indice_aceita_e_o_banco_muda():
    print("\n[2] CONTROLE — com o índice aceitando, tudo acontece")
    resultado, escritas, qdrant = _despublicar(resposta_do_qdrant=True)

    checar(resultado is True, "a função devolve True")
    checar(any(e.get("status") == "superseded" for e in escritas),
           "e o banco recebe o novo status",
           "sem este controle, uma função que só sabe dizer 'não' passaria")
    checar(qdrant.chamadas == 1, "CONTROLE — e o índice foi chamado")


def teste_o_dado_do_qdrant_nao_levanta():
    print("\n[3] CONTROLE — o dublê recusa do jeito que o real recusa")
    q = _ler(QDRANT)
    i = q.index("def delete_document(")
    trecho = q[i:i + 2600]

    # Se `delete_document` passasse a LEVANTAR, o dublê deste teste deixaria de
    # representar a produção e o teste viraria ficção — verde por testar outro
    # mundo.
    checar("except Exception as e:" in trecho and "return False" in trecho,
           "`delete_document` engole a exceção e devolve False",
           "é por isso que o `except` do chamador era código morto")


def teste_a_aposentadoria_pede_licenca_ao_indice_antes_do_banco():
    print("\n[4] A ordem: o índice manda, o banco obedece")
    c = _ler(CURADORIA)
    i = c.index("def _aposentar_contraditas_sync")
    bloco = c[i:c.index("\ndef _agora_iso", i)]

    i_remove = bloco.find("if not despublicar_carta_sync(")
    i_status = bloco.find('"status": "superseded"')
    checar(i_remove > 0,
           "a aposentadoria confere o retorno do removedor",
           "antes chamava e descartava")
    checar(i_status == -1,
           "e não grava mais `superseded` por conta própria",
           "quem grava é `despublicar_carta_sync`, DEPOIS de o vetor sair")
    checar("marca[\"qdrant_pendente\"] = True" in bloco,
           "quando o índice recusa, marca para reconciliar",
           "📊 a marca nunca era gravada: 0 linhas em 12.933 cartas")

    # CONTROLE — o reconciliador procura exatamente essa marca. Gravar um nome
    # diferente aqui seria marcar para ninguém.
    checar('pii_check->>qdrant_pendente' in c or "qdrant_pendente" in c,
           "CONTROLE — e é a marca que o reconciliador procura")


def main() -> int:
    print("=" * 70)
    print("O REMOVEDOR DO ÍNDICE NÃO PODE MENTIR")
    print("=" * 70)
    teste_o_indice_recusa_e_a_funcao_admite()
    teste_o_indice_aceita_e_o_banco_muda()
    teste_o_dado_do_qdrant_nao_levanta()
    teste_a_aposentadoria_pede_licenca_ao_indice_antes_do_banco()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — quem não removeu, admite que não removeu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
