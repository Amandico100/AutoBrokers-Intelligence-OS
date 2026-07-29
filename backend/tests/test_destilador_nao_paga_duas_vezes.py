"""A mesma sessão não pode ser cobrada indefinidamente pelo mesmo erro.

O que aconteceu em 28/07/2026
-----------------------------
O Destilador fez **3.445 chamadas** ao modelo e produziu **1.111 destilações**.
As outras 2.334 não foram sessões diferentes: foram as MESMAS sessões, tentadas
rodada após rodada. US$ 15 dos US$ 22 gastos compraram o mesmo erro repetido.

A causa raiz: o Claude Sonnet 5 passou a **pensar por padrão**. O 4.6 não
pensava quando ninguém pedia; o 5 decide sozinho. Com pensamento, o LangChain
devolve `content` como LISTA de blocos:

    [{"type": "thinking", ...}, {"type": "text", "text": "{...json...}"}]

O código antigo fazia `str(content)` — que numa lista devolve a REPRESENTAÇÃO
da lista, com colchetes e aspas Python. `_parse_json` recusava, e a sessão
ficava sem a marca `distilled`.

Como o pensamento é adaptativo, o modelo pensava só nas conversas difíceis:
32% passavam, 68% falhavam. Isso é o pior formato possível de defeito — sem
erro, sem alarme, com resultado parcial que parece progresso.

As duas travas que este teste protege
-------------------------------------
1. **Ler o texto, não a lista** (`_texto_da_resposta`) — conserta a causa.
2. **Parar de insistir depois de três recusas** — a causa seguinte, ainda
   desconhecida, não vai custar os mesmos US$ 15. Perder uma sessão é barato;
   pagar por ela para sempre sem ninguém ver, não.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

# O `app/__init__.py` real arrasta o mundo (openai, pydantic_settings). O
# destilador não precisa de nada disso: todos os imports pesados dele estão
# DENTRO das funções. Carregamos o arquivo de verdade sobre pacotes de fachada
# — nunca uma cópia da lógica, que envelheceria em silêncio e daria verde
# testando código que não está em produção.
for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.core", ("app", "core"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m

_banco = types.ModuleType("app.core.database")
_banco.get_supabase_client = lambda: None      # cada teste troca pelo seu falso
sys.modules["app.core.database"] = _banco

_spec = importlib.util.spec_from_file_location(
    "app.services.attendance_distiller",
    os.path.join(RAIZ, "app", "services", "attendance_distiller.py"))
DIST = importlib.util.module_from_spec(_spec)
sys.modules["app.services.attendance_distiller"] = DIST
_spec.loader.exec_module(DIST)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ---------------------------------------------------------------- fake mínimo
class _Consulta:
    def __init__(self, linhas):
        self._linhas = linhas

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def range(self, ini, fim):
        return _Consulta(self._linhas[ini:fim + 1])

    def execute(self):
        return type("R", (), {"data": list(self._linhas)})()


class _Cliente:
    def __init__(self, linhas):
        self._linhas = linhas

    def table(self, _nome):
        return _Consulta(self._linhas)


class _Db:
    def __init__(self, linhas):
        self.client = _Cliente(linhas)


def teste_le_o_texto_e_nao_a_lista_de_blocos():
    print("\n[1] O modelo pensa; a resposta vem em blocos; lemos o TEXTO")
    _texto_da_resposta = DIST._texto_da_resposta

    class R:
        pass

    pensou = R()
    pensou.content = [
        {"type": "thinking", "thinking": "deixa eu ver o ramo dessa conversa"},
        {"type": "text", "text": '{"ramo": "auto", "servico": "sinistro"}'},
    ]
    lido = _texto_da_resposta(pensou)
    checar(lido == '{"ramo": "auto", "servico": "sinistro"}',
           "o bloco de texto sai limpo, sem o de pensamento", repr(lido))
    checar("thinking" not in (lido or ""),
           "o raciocínio NÃO entra no JSON",
           "era isto que fazia `_parse_json` recusar 68% das respostas")

    simples = R()
    simples.content = '{"ramo": "vida"}'
    checar(_texto_da_resposta(simples) == '{"ramo": "vida"}',
           "e a resposta sem pensamento continua funcionando")

    vazio = R()
    vazio.content = [{"type": "thinking", "thinking": "..."}]
    checar(_texto_da_resposta(vazio) is None,
           "resposta só com pensamento devolve None, não a lista inteira",
           "devolver texto lixo faria a sessão ser marcada com dado inválido")


def teste_sessao_que_recusou_tres_vezes_sai_da_fila():
    print("\n[2] Depois de três recusas, a sessão para de ser cobrada")
    database = sys.modules["app.core.database"]
    dist = DIST

    linhas = [
        {"id": "nova", "summary": {}},
        {"id": "falhou-1x", "summary": {"distill_falhas": 1}},
        {"id": "falhou-2x", "summary": {"distill_falhas": 2}},
        {"id": "parada", "summary": {"distill_falhas": dist.LIMITE_DE_FALHAS}},
        {"id": "parada-ha-tempo", "summary": {"distill_falhas": 9}},
        {"id": "ja-destilada", "summary": {"distilled": {"ramo": "auto"}}},
    ]
    original = database.get_supabase_client
    database.get_supabase_client = lambda: _Db(linhas)
    try:
        fila = [s["id"] for s in dist._load_undistilled_sync(50)]
    finally:
        database.get_supabase_client = original

    checar("nova" in fila, "sessão nunca tentada entra na fila")
    checar("falhou-1x" in fila and "falhou-2x" in fila,
           "uma ou duas recusas ainda merecem nova tentativa",
           "pode ter sido instabilidade do modelo")
    checar("parada" not in fila and "parada-ha-tempo" not in fila,
           "na terceira, sai da fila", f"fila={fila}")
    checar("ja-destilada" not in fila, "e a já destilada nunca volta")
    checar(dist.LIMITE_DE_FALHAS == 3, "o limite é três",
           f"está {dist.LIMITE_DE_FALHAS}")


def teste_a_recusa_e_registrada_antes_de_desistir():
    print("\n[3] Toda recusa deixa marca — senão o contador nunca sobe")
    import inspect

    dist = DIST

    fonte = inspect.getsource(dist._destilar_sessao)
    # O recorte é o trecho entre `if not data:` e o `return` que o encerra —
    # medir por distância em caracteres pegaria o corpo do sucesso e daria
    # verde sem motivo.
    i = fonte.find("if not data:", fonte.find("if not data and not raw:") + 1)
    ramo = fonte[i:fonte.find("return", i)] if i >= 0 else ""
    checar(bool(ramo), "o caminho da resposta ilegível existe")
    checar("distill_falhas" in ramo, "ele incrementa o contador de recusas")
    checar("_save_session_summary_sync" in ramo,
           "e GRAVA antes de desistir",
           "sem gravar, o contador reinicia em zero toda rodada e a sessão "
           "é cobrada para sempre — o defeito de US$ 15")
    checar("+ 1" in ramo or "+1" in ramo, "somando à contagem anterior")


def teste_chamada_que_nao_respondeu_nao_conta_recusa():
    print("\n[3b] Crédito acabado não é culpa da sessão")
    import inspect

    fonte = inspect.getsource(DIST._destilar_sessao)
    i = fonte.find("if not data and not raw:")
    ramo = fonte[i:fonte.find("if not data:", i)] if i >= 0 else ""
    checar(bool(ramo),
           "existe caminho separado para `raw` vazio",
           "sem ele, credito acabado no meio da rodada parava a sessao para "
           "sempre — 350 conversas em 30/07/2026")
    checar("distill_falhas" not in ramo,
           "e ele NAO incrementa o contador de recusas")
    checar("return" in ramo, "so devolve, deixando a sessao na fila")


def teste_o_texto_util_continua_gerando_carta():
    print("\n[4] A trava não pode comer sessão boa")
    _parse_json, _texto_da_resposta = DIST._parse_json, DIST._texto_da_resposta

    class R:
        pass

    r = R()
    r.content = [
        {"type": "thinking", "thinking": "conversa de guincho"},
        {"type": "text",
         "text": 'Segue: {"ramo": "auto", "servico": "assistencia", '
                 '"fatos_reutilizaveis": ["Guincho cobre 200km"]}'},
    ]
    dado = _parse_json(_texto_da_resposta(r))
    checar(bool(dado), "resposta com pensamento E preâmbulo vira JSON",
           "é o formato real que 68% das chamadas produziram")
    checar((dado or {}).get("ramo") == "auto", "com o ramo certo")
    checar(len((dado or {}).get("fatos_reutilizaveis") or []) == 1,
           "e o fato que vira carta no RAG chega inteiro")


def main() -> int:
    print("=" * 70)
    print("A MESMA SESSÃO NÃO PODE SER COBRADA DUAS VEZES PELO MESMO ERRO")
    print("=" * 70)
    for teste in (teste_le_o_texto_e_nao_a_lista_de_blocos,
                  teste_sessao_que_recusou_tres_vezes_sai_da_fila,
                  teste_a_recusa_e_registrada_antes_de_desistir,
                  teste_chamada_que_nao_respondeu_nao_conta_recusa,
                  teste_o_texto_util_continua_gerando_carta):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O ERRO CUSTA UMA VEZ, NÃO PARA SEMPRE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
