"""Filtrar por faceta ou por tema não pode apagar quem não tem o rótulo.

O QUE ESTE ARQUIVO GUARDA
=========================
`faceta` e `temas` ganharam LEITOR na SPEC-072 Bloco 1 — fechando P-142 e P-177.
Os dois já tinham escritor e índice; nenhum filtrava nada.

E um filtro novo sobre um índice heterogêneo é a forma mais fácil de destruir um
RAG em silêncio: ele não dá erro, não aparece no log, e a busca continua
devolvendo resultado — só que menos. 📊 Medido em 15/08/2026:

    12.534 das 17.928 cartas publicadas (69,9%)  não têm `faceta`  — e nunca terão
     4.083 das 17.928                   (22,8%)  não têm `temas`
     1.139 dos  6.797 pedaços de contrato (16,8%) têm `faceta=None`

Um `must` puro (`faceta == "documento"`) apagaria **70% do índice**. A P-142 já
tinha escrito o aviso para o campo irmão — *"sem o segundo braço ele apaga as
12.063 cartas, que não têm essa chave e nunca terão"*.

POR QUE O TESTE APLICA O FILTRO, EM VEZ DE OLHAR A FORMA DELE
==============================================================
Afirmar `"IsEmptyCondition" in corpo` prova que a string existe, não que o ponto
sobrevive. E monkeypatchar `IsEmptyCondition = None` **não** produz um filtro de
um braço: produz `None`, o filtro inteiro abandonado (degradação segura) — o
oposto do que se quer testar.

Então este arquivo captura o `Filter` que `search_similar` monta de verdade e o
**executa** contra um acervo de mentira com as proporções medidas acima. A
mutação tira o braço `IsEmptyCondition` do filtro capturado e mostra o apagão em
número.

A LINHA DE CONTROLE (CLAUDE.md §9.2)
=====================================
    faceta='documento'  ×  faceta=None      → sem pedido, nenhum ponto some
    dois braços         ×  um braço só      → 12.534 e 4.083 somem
    tema pedido         ×  tema não pedido  → idem

O par é o que dá direito à conclusão.

⚠️ O QUE ESTE TESTE **NÃO** COBRE
==================================
Ele executa a semântica do `Filter` reimplementada em `_casa()`, não o Qdrant.
Isso prova que **o filtro montado tem a forma certa e o efeito certo sobre um
acervo conhecido** — não que o Qdrant o interprete assim. O que ancora a
reimplementação na realidade é ela ser a mesma que os dois filtros irmãos
(`_filtro_de_seguradora`, `_filtro_de_namespace`) já usam em produção há uma
semana, com o mesmo `Filter(should=[FieldCondition, IsEmptyCondition])`.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# ─────────────────────────────────────────────────────────────────────────────
# Os modelos do qdrant-client, como dublês com semântica explícita. O pacote não
# está instalado nesta máquina (`requirements.txt:37` pede >=1.11.0, e todo
# teste da casa o stuba) — e explícito aqui vale mais que genérico, porque é
# sobre estas classes que `_casa()` decide.
# ─────────────────────────────────────────────────────────────────────────────
class _Obj:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


_NOMES = ("Distance", "FieldCondition", "Filter", "Fusion", "FusionQuery",
          "MatchAny", "MatchValue", "PayloadSchemaType", "PointStruct", "Prefetch",
          "SparseVector", "SparseVectorParams", "VectorParams", "IsEmptyCondition",
          "PayloadField", "HasIdCondition")
_M = types.ModuleType("qdrant_client.models")
for _n in _NOMES:
    setattr(_M, _n, type(_n, (_Obj,), {}))
_M.PayloadSchemaType = types.SimpleNamespace(KEYWORD="keyword", BOOL="bool")
_QC = types.ModuleType("qdrant_client")
_QC.QdrantClient = type("QdrantClient", (_Obj,), {})
_QC.models = _M
sys.modules["qdrant_client"] = _QC
sys.modules["qdrant_client.models"] = _M

for _n, _p in (("app", ("app",)), ("app.core", ("app", "core")),
               ("app.services", ("app", "services"))):
    if _n not in sys.modules:
        _mod = types.ModuleType(_n)
        _mod.__path__ = [os.path.join(RAIZ, *_p)]
        _mod.__package__ = _n
        sys.modules[_n] = _mod

_cfg = types.ModuleType("app.core.config")
_cfg.settings = types.SimpleNamespace(QDRANT_HOST="x", QDRANT_PORT=6333,
                                      QDRANT_API_KEY=None, OPENAI_API_KEY="x")
sys.modules["app.core.config"] = _cfg


def _carregar(nome: str, *partes: str):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(RAIZ, *partes))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


QS = _carregar("app.services.qdrant_service", "app", "services", "qdrant_service.py")
KS = _carregar("app.services.knowledge_scope", "app", "services", "knowledge_scope.py")


# ─────────────────────────────────────────────────────────────────────────────
# A semântica do Qdrant que este filtro usa — e só ela.
# ─────────────────────────────────────────────────────────────────────────────
def _casa(cond, ponto: dict) -> bool:
    nome = type(cond).__name__
    if nome == "Filter":
        must = list(getattr(cond, "must", None) or [])
        should = list(getattr(cond, "should", None) or [])
        if must and not all(_casa(c, ponto) for c in must):
            return False
        if should and not any(_casa(c, ponto) for c in should):
            return False
        return True
    if nome == "FieldCondition":
        valor = ponto.get(cond.key)
        m = cond.match
        # ⚠️ O Qdrant compara valor contra campo-ARRAY elemento a elemento: uma
        # condição escalar casa quando QUALQUER elemento casa. Reimplementar só
        # `valor == m.value` deixaria esta simulação MAIS ESTRITA que a produção
        # — e um teste mais estrito que a realidade passa por engano quando o
        # código está errado do outro lado.
        if type(m).__name__ == "MatchValue":
            if isinstance(valor, list):
                return m.value in valor
            return valor == m.value
        if type(m).__name__ == "MatchAny":
            if isinstance(valor, list):
                return bool(set(valor) & set(m.any))
            return valor in list(m.any)
        return False
    if nome == "IsEmptyCondition":
        valor = ponto.get(cond.is_empty.key)
        return valor is None or valor == [] or valor == ""
    return True


def _sobrevivem(filtro, acervo) -> list:
    return [p for p in acervo if filtro is None or _casa(filtro, p)]


def _um_braco_so(filtro):
    """A MUTAÇÃO: tira o `IsEmptyCondition` de todo braço aninhado."""
    if filtro is None:
        return None
    novos = []
    for cond in list(getattr(filtro, "must", None) or []):
        if type(cond).__name__ == "Filter":
            should = [c for c in (getattr(cond, "should", None) or [])
                      if type(c).__name__ != "IsEmptyCondition"]
            novos.append(_M.Filter(should=should))
        else:
            novos.append(cond)
    return _M.Filter(must=novos, should=getattr(filtro, "should", None),
                     must_not=getattr(filtro, "must_not", None))


# ─────────────────────────────────────────────────────────────────────────────
# O acervo de mentira, com as proporções MEDIDAS em 15/08/2026.
# ─────────────────────────────────────────────────────────────────────────────
PUBLICADAS = 17_928
SEM_FACETA = 12_534          # cartas de conversa: a chave é omitida, não vazia
SEM_TEMAS = 4_083
PEDACOS = 6_797
PEDACOS_SEM_FACETA = 1_139


def _acervo() -> list:
    # ⚠️ `curation_status` e `scope` entram porque o filtro real os exige
    # (`curation_published_only=True`). A primeira versão desta fixture não os
    # tinha, e a LINHA DE CONTROLE pegou: com faceta=None e temas=None,
    # sobreviveram ZERO de 24.725 pontos. Sem o controle, eu teria lido "o filtro
    # de faceta apaga tudo" e consertado o lugar errado.
    pontos = []
    for i in range(PUBLICADAS):
        p = {"namespace": "cards", "curation_status": "published",
             "scope": "global:autobrokers"}
        if i >= SEM_FACETA:
            p["faceta"] = "documento" if i % 3 == 0 else "exclusao"
        if i >= SEM_TEMAS:
            p["temas"] = ["documentacao"] if i % 3 == 0 else ["cobranca_boleto"]
        pontos.append(p)
    for i in range(PEDACOS):
        p = {"namespace": "normative", "curation_status": "published",
             "scope": "global:autobrokers"}
        if i >= PEDACOS_SEM_FACETA:
            p["faceta"] = "documento" if i % 4 == 0 else "escopo"
        pontos.append(p)
    return pontos


ACERVO = _acervo()


def _filtro_montado(**kw):
    """O `Filter` que `search_similar` monta DE VERDADE, capturado."""
    svc = QS.QdrantService.__new__(QS.QdrantService)
    capturado = {}

    class _Cliente:
        def collection_exists(self, *a, **k):
            return True

        def query_points(self, **kw2):
            capturado.update(kw2)
            return types.SimpleNamespace(points=[])

    svc.client = _Cliente()
    svc.search_similar(company_id="c1", query_embedding=[0.1] * 8,
                       collection_name="autobrokers_global", agent_id=None,
                       curation_published_only=True, **kw)
    return capturado.get("query_filter")


# ═════════════════════════════════════════════════════════════════════════════
def teste_os_dois_bracos_existem_no_filtro_montado() -> None:
    print("\n[1] o filtro que search_similar monta tem os dois braços")
    f = _filtro_montado(faceta="documento", temas=["documentacao"])
    must = list(getattr(f, "must", None) or [])
    aninhados = [c for c in must if type(c).__name__ == "Filter"]

    def braços(chave):
        for c in aninhados:
            should = list(getattr(c, "should", None) or [])
            campos = {getattr(getattr(x, "is_empty", None), "key", None)
                      or getattr(x, "key", None) for x in should}
            if chave in campos:
                return should
        return []

    for chave in ("faceta", "temas"):
        s = braços(chave)
        checar(len(s) == 2, f"`{chave}` tem exatamente 2 braços", f"veio {len(s)}")
        checar(any(type(x).__name__ == "FieldCondition" for x in s),
               f"`{chave}` — braço positivo é FieldCondition")
        checar(any(type(x).__name__ == "IsEmptyCondition" for x in s),
               f"`{chave}` — braço de ausência é IsEmptyCondition")


def teste_quem_nao_tem_o_rotulo_sobrevive() -> None:
    """UM FILTRO POR VEZ. Os dois são `must`, ou seja, ANDed entre si.

    ⚠️ A primeira versão deste teste pediu os dois juntos e cobrou "as 13.673
    sem faceta continuam". Sobraram 8.039 — e a conclusão óbvia ("o braço de
    ausência da faceta falhou") era FALSA: quem tirou as outras 5.634 foi o
    filtro de TEMA, porque uma carta sem faceta pode ter `temas=['cobranca']`.
    Dois fatores variando, conclusão sem dono (CLAUDE.md §9.2).
    """
    print("\n[2] com dois braços, ninguém some — um filtro por vez")

    so_faceta = _sobrevivem(_filtro_montado(faceta="documento"), ACERVO)
    sem_faceta = [p for p in so_faceta if "faceta" not in p]
    checar(len(sem_faceta) == SEM_FACETA + PEDACOS_SEM_FACETA,
           f"só faceta: as {SEM_FACETA + PEDACOS_SEM_FACETA:,} sem o rótulo ficam",
           f"sobraram {len(sem_faceta):,}")
    checar(all(p.get("faceta") in (None, "documento") for p in so_faceta),
           "e nenhuma de OUTRA faceta passa — o filtro filtra")
    checar(len(so_faceta) < len(ACERVO), "não é decoração",
           f"{len(so_faceta):,} de {len(ACERVO):,}")

    so_temas = _sobrevivem(_filtro_montado(temas=["documentacao"]), ACERVO)
    sem_temas = [p for p in so_temas if "temas" not in p]
    checar(len(sem_temas) == SEM_TEMAS + PEDACOS,
           f"só temas: as {SEM_TEMAS:,} sem tema + os {PEDACOS:,} de contrato ficam",
           f"sobraram {len(sem_temas):,}")
    checar(all("documentacao" in (p.get("temas") or ["documentacao"])
               for p in so_temas),
           "e nenhuma de OUTRO tema passa")

    juntos = _sobrevivem(_filtro_montado(faceta="documento",
                                         temas=["documentacao"]), ACERVO)
    checar(len(juntos) <= min(len(so_faceta), len(so_temas)),
           "os dois juntos são um AND — nunca devolvem mais que cada um sozinho",
           f"{len(juntos):,} vs faceta={len(so_faceta):,} temas={len(so_temas):,}")
    checar(any(p.get("faceta") == "documento" for p in juntos),
           "e as cartas de documento continuam lá")


def teste_controle_sem_pedido_nao_ha_filtro() -> None:
    """LINHA DE CONTROLE: um fator só — a pergunta não pede faceta nem tema."""
    print("\n[3] CONTROLE — sem pedido, o índice inteiro responde")
    f = _filtro_montado(faceta=None, temas=None)
    vivos = _sobrevivem(f, ACERVO)
    checar(len(vivos) == len(ACERVO),
           "CONTROLE: nenhum ponto some quando nada é pedido",
           f"{len(vivos):,} de {len(ACERVO):,}")


def teste_a_mutacao_apaga_o_indice() -> None:
    """MUTAÇÃO: um braço só — e o apagão tem de aparecer em NÚMERO."""
    print("\n[4] MUTAÇÃO — tirar o braço 'OU ausente'")
    f = _filtro_montado(faceta="documento", temas=["documentacao"])
    vivos_dois = _sobrevivem(f, ACERVO)
    vivos_um = _sobrevivem(_um_braco_so(f), ACERVO)

    perdidos = len(vivos_dois) - len(vivos_um)
    print(f"      dois braços: {len(vivos_dois):,} pontos")
    print(f"      um braço só: {len(vivos_um):,} pontos")
    print(f"      APAGADOS:    {perdidos:,}")

    checar(perdidos > 0, "o braço de ausência tem efeito — o guarda pode falhar",
           "se zero, o teste não guarda nada")
    checar(not any("faceta" not in p for p in vivos_um),
           "MUTAÇÃO: com um braço só, NENHUM ponto sem faceta sobrevive")
    checar(not any("temas" not in p for p in vivos_um),
           "nem nenhum sem tema")

    # UM FATOR POR VEZ, para o número ter dono.
    so_faceta = _filtro_montado(faceta="documento")
    apagados_faceta = len([p for p in _sobrevivem(so_faceta, ACERVO)
                           if "faceta" not in p])
    print(f"      só o filtro de faceta apagaria: {apagados_faceta:,}")
    checar(apagados_faceta == SEM_FACETA + PEDACOS_SEM_FACETA,
           f"o braço da FACETA sozinho salva {SEM_FACETA:,} cartas + "
           f"{PEDACOS_SEM_FACETA:,} trechos de contrato",
           f"contei {apagados_faceta:,}")
    checar(not any("faceta" not in p
                   for p in _sobrevivem(_um_braco_so(so_faceta), ACERVO)),
           "e sem ele os mesmos somem, todos")

    so_tema = _filtro_montado(temas=["documentacao"])
    apagados_tema = len([p for p in _sobrevivem(so_tema, ACERVO)
                         if "temas" not in p])
    print(f"      só o filtro de tema apagaria:   {apagados_tema:,}")
    checar(apagados_tema == SEM_TEMAS + PEDACOS,
           f"o braço do TEMA sozinho salva {SEM_TEMAS:,} cartas + "
           f"{PEDACOS:,} trechos de contrato (que nunca terão tema)",
           f"contei {apagados_tema:,}")


def teste_a_degradacao_e_segura() -> None:
    print("\n[5] sem IsEmptyCondition no cliente, o filtro INTEIRO cai")
    svc = QS.QdrantService.__new__(QS.QdrantService)
    guardado = QS.IsEmptyCondition
    try:
        QS.IsEmptyCondition = None
        checar(svc._filtro_de_faceta("documento") is None,
               "faceta: abandona o filtro, não vira um braço só")
        checar(svc._filtro_de_temas(["documentacao"]) is None,
               "temas: idem")
    finally:
        QS.IsEmptyCondition = guardado
    checar(svc._filtro_de_faceta("documento") is not None,
           "e volta a existir quando o cliente tem a condição (controle)")
    checar(svc._filtro_de_faceta(None) is None, "sem pedido, sem filtro")
    checar(svc._filtro_de_temas([]) is None, "lista vazia não vira filtro")


def teste_a_pergunta_vira_pedido() -> None:
    print("\n[6] a pergunta do segurado vira o pedido de faceta e tema")
    checar(KS.faceta_da_pergunta("quais documentos preciso mandar?") == "documento",
           "'quais documentos' → faceta=documento")
    checar(KS.temas_da_pergunta("quais documentos preciso mandar?") == ["documentacao"],
           "e → temas=['documentacao']",
           f"veio {KS.temas_da_pergunta('quais documentos preciso mandar?')!r}")
    checar(KS.faceta_da_pergunta("meu carro bateu, e agora?") is None,
           "CONTROLE: pergunta sem documento → None, e nada é filtrado")
    checar(KS.faceta_da_pergunta("") is None, "texto vazio → None")

    # 🔴 A decisão de projeto que este teste existe para congelar.
    checar(KS.faceta_da_pergunta("a apólice cobre vidro?") is None,
           "pergunta de COBERTURA não vira faceta=escopo",
           "escopo e exclusao são um PAR: filtrar por um esconde o outro")
    checar(KS.faceta_da_pergunta("por que negaram meu sinistro?") is None,
           "e pergunta de recusa não vira faceta=exclusao")
    checar(set(KS._APELIDOS_DE_FACETA.values()) == {"documento"},
           "só UMA das 8 facetas filtra — e o porquê está escrito no código",
           f"veio {set(KS._APELIDOS_DE_FACETA.values())}")


def teste_os_dois_caminhos_globais_tem_a_regra() -> None:
    print("\n[7] os DOIS caminhos globais passam faceta e temas")
    for arq in ("search_service.py", "langchain_service.py"):
        with open(os.path.join(RAIZ, "app", "services", arq), encoding="utf-8") as fh:
            codigo = fh.read()
        codigo = "\n".join(l for l in codigo.split("\n")
                           if not l.strip().startswith("#"))
        checar("faceta_da_pergunta(" in codigo, f"{arq} chama faceta_da_pergunta")
        checar("temas_da_pergunta(" in codigo, f"{arq} chama temas_da_pergunta")
        checar(re.search(r"faceta=\w+", codigo) is not None,
               f"{arq} repassa faceta= ao build_global_search_kwargs")
        checar(re.search(r"temas=\w+", codigo) is not None,
               f"{arq} repassa temas=")

    with open(os.path.join(RAIZ, "app", "services", "knowledge_scope.py"),
              encoding="utf-8") as fh:
        ks = fh.read()
    checar('kwargs["faceta"]' in ks and 'kwargs["temas"]' in ks,
           "build_global_search_kwargs monta as duas chaves")
    checar(("temas", "keyword") in [(c, str(s).lower()) for c, s in QS._INDICES_DE_PAYLOAD]
           or any(c == "temas" for c, _ in QS._INDICES_DE_PAYLOAD),
           "`temas` tem índice de payload — filtro sem índice é varredura")

    with open(os.path.join(RAIZ, "app", "services", "attendance_distiller.py"),
              encoding="utf-8") as fh:
        ad = fh.read()
    checar('"temas": card["temas"]' in ad,
           "e `temas` tem ESCRITOR — sem ele o filtro seria no-op")
    checar('if card.get("temas")' in ad,
           "omitido quando vazio, nunca gravado como []",
           "[] seria GRAVADO e o braço IsEmptyCondition não o alcançaria")


def main() -> int:
    print(__doc__.split("\n")[0])
    print("=" * 70)
    teste_os_dois_bracos_existem_no_filtro_montado()
    teste_quem_nao_tem_o_rotulo_sobrevive()
    teste_controle_sem_pedido_nao_ha_filtro()
    teste_a_mutacao_apaga_o_indice()
    teste_a_degradacao_e_segura()
    teste_a_pergunta_vira_pedido()
    teste_os_dois_caminhos_globais_tem_a_regra()

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("TUDO VERDE — o filtro filtra, e quem não tem rótulo continua respondendo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
