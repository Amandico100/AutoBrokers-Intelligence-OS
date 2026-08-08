# -*- coding: utf-8 -*-
"""O acervo guarda a fonte, e o índice sabe de que versão veio cada pedaço.

Dois defeitos, uma causa
------------------------
📊 Medido em 08/08/2026:

    normative_document_versions.storage_ref preenchido ....  0 de 29
    pontos `normative` no Qdrant .......................... 11.409
    `insurance_corpus` usava `doc_id = f"norm-{doc['id']}"` — o MESMO id para
    todas as versões — e chamava `delete_document(doc_id)` ANTES de inserir.

O PDF era baixado, lido em memória e descartado. O texto extraído não era
gravado em lugar nenhum.

    O texto-fonte do acervo existia em um único lugar: dentro do Qdrant,
    picado em 11.409 pedaços.

Isso inverte o CLAUDE.md §6 ("Qdrant: índice derivado e reconstruível") — ele
não era derivado, era o original. E como o id não distinguia versões, a única
cópia podia ser apagada por uma captura nova. 📊 A URL da HDI devolve 500 e a
da Allianz devolve 403: documento apagado do índice sem cópia é documento
perdido.

O que este arquivo guarda
-------------------------
1. `guardar_versao` põe o original E o texto no MinIO, em caminhos que a
   própria função sabe remontar para ler de volta.
2. Falha ao arquivar **não derruba a ingestão** — e também não finge sucesso.
3. O id dos pontos carrega a versão, e as versões anteriores são endereçadas
   pelo que o banco guardou (com o esquema legado como padrão real, não chute).
4. 🔴 O upsert vem ANTES do delete. Essa ordem é a diferença entre "duas
   versões na busca por um ciclo" (visível) e "nenhuma versão na busca"
   (silencioso) — e 📊 vinte e três documentos já morreram no meio da ingestão
   em 05/08/2026.

Cada afirmação tem CONTROLE ao lado (CLAUDE.md §9.2).
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import os
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ALVO = RAIZ / "app" / "services" / "knowledge" / "insurance_corpus.py"

for _n in ("app", "app.services", "app.services.knowledge", "app.services.research"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


arquivo = _carregar("app.services.knowledge.acervo_arquivo",
                    RAIZ / "app" / "services" / "knowledge" / "acervo_arquivo.py")
corpus = _carregar("app.services.knowledge.insurance_corpus", ALVO)

FALHAS: list = []


def checar(condicao: bool, nome: str, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok    {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X     {nome}  {detalhe}")


DOC_ID = "3f2b9c14-0a7e-4d55-9b31-6c8f0e2a1d47"
PDF = b"%PDF-1.7\nconteudo de mentira que nao e lido por ninguem aqui\n"


# ── um MinIO de mentira que registra o que recebe ────────────────────────────
#
# Ele grava DE VERDADE num dicionário. É isso que dá direito de afirmar "não
# guardou" quando não guardou: sem um duplo que consiga guardar, "não guardou" e
# "o duplo não sabe ver" são a mesma frase.

class MinioDeMentira:
    def __init__(self, explodir_em=()):
        self.objetos: dict = {}
        self.explodir_em = set(explodir_em)

    def put_bytes(self, object_name, data, content_type="application/octet-stream"):
        if any(m in object_name for m in self.explodir_em):
            raise RuntimeError(f"MinIO fora do ar para {object_name}")
        self.objetos[object_name] = (data, content_type)
        return object_name

    def download_file(self, object_name):
        import io

        if object_name not in self.objetos:
            raise FileNotFoundError(object_name)
        return io.BytesIO(self.objetos[object_name][0])


# ── 1. o original e o texto ganham endereço ──────────────────────────────────

def teste_o_pdf_e_o_texto_sao_guardados_e_relidos():
    print("\n[1] 📊 storage_ref estava em 0 de 29 — agora tem onde ficar")
    m = MinioDeMentira()
    r = arquivo.guardar_versao(DOC_ID, 3, texto="o texto inteiro do contrato",
                               pdf_bytes=PDF, media_type="application/pdf",
                               minio=m)
    checar(r["storage_ref"] == f"acervo-normativo/{DOC_ID}/v3/original.pdf",
           "o original tem endereço, com a versão no caminho", str(r["storage_ref"]))
    checar(r["text_storage_ref"] == f"acervo-normativo/{DOC_ID}/v3/texto.txt",
           "o texto também", str(r["text_storage_ref"]))
    checar(r["source_bytes"] == len(PDF),
           "e o tamanho do ARQUIVO é registrado separado do tamanho do texto",
           str(r["source_bytes"]))
    checar(r["arquivado_em"] is not None and not r["erros"],
           "a data de arquivamento é escrita e não há erro", str(r))
    checar(m.objetos[r["storage_ref"]][0] == PDF,
           "os bytes que chegaram são os bytes que ficaram")

    # CONTROLE — o caminho é remontável. Guardar sem saber ler é gastar disco;
    # é por esta porta que o reprocessamento alcança o documento cuja URL morreu.
    de_volta = arquivo.ler_texto(DOC_ID, 3, minio=m)
    checar(de_volta == "o texto inteiro do contrato",
           "CONTROLE: o texto volta pelo mesmo caminho que o escreveu",
           repr(de_volta))

    # CONTROLE 2 — a versão faz parte do endereço. Sem isto, a versão 4
    # sobrescreveria a 3 e o arquivo teria o mesmo defeito do índice.
    checar(arquivo.caminho(DOC_ID, 4, arquivo.ORIGINAL)
           != arquivo.caminho(DOC_ID, 3, arquivo.ORIGINAL),
           "CONTROLE 2: versões diferentes, endereços diferentes")

    # CONTROLE 3 — o prefixo NÃO se parece com um company_id. Acervo normativo
    # não tem dono (D-Acervo-01); num caminho de tenant ele viraria material de
    # uma corretora.
    checar(arquivo.PREFIXO == "acervo-normativo" and "-" in arquivo.PREFIXO
           and len(arquivo.PREFIXO) != 36,
           "CONTROLE 3: o prefixo do acervo não é um uuid de corretora",
           arquivo.PREFIXO)


def teste_falhar_ao_arquivar_nao_derruba_e_nao_finge():
    print("\n[2] Arquivar é guarda, não entrega — mas a falha fica visível")
    m = MinioDeMentira(explodir_em=("original.pdf",))
    r = arquivo.guardar_versao(DOC_ID, 1, texto="texto", pdf_bytes=PDF, minio=m)
    checar(r["storage_ref"] is None, "o original não foi guardado", str(r["storage_ref"]))
    checar("original" in r["erros"] and "RuntimeError" in r["erros"]["original"],
           "e o motivo REAL fica registrado, com tipo e mensagem",
           str(r["erros"]))
    checar(r["text_storage_ref"] is not None,
           "o texto, que deu certo, continua guardado", str(r["text_storage_ref"]))

    # CONTROLE 1 — falha total NÃO marca `arquivado_em`. Marcar a data numa
    # tentativa que falhou faria a fila de reprocessamento
    # (`normative_versao_sem_arquivo_idx`) parecer resolvida.
    tudo_ruim = MinioDeMentira(explodir_em=("original.pdf", "texto.txt"))
    r2 = arquivo.guardar_versao(DOC_ID, 1, texto="texto", pdf_bytes=PDF,
                                minio=tudo_ruim)
    checar(r2["arquivado_em"] is None and len(r2["erros"]) == 2,
           "CONTROLE: falhando tudo, `arquivado_em` fica NULO e há 2 motivos",
           str(r2))

    # CONTROLE 2 — dando tudo certo, a data É escrita. Sem esta linha, "fica
    # nulo quando falha" seria indistinguível de "nunca é escrita".
    r3 = arquivo.guardar_versao(DOC_ID, 1, texto="texto", pdf_bytes=PDF,
                                minio=MinioDeMentira())
    checar(r3["arquivado_em"] is not None,
           "CONTROLE 2: com tudo certo, a data é escrita", str(r3["arquivado_em"]))

    # CONTROLE 3 — origem sem PDF (o crawler devolve markdown) guarda só o
    # texto, SEM erro. "Não havia arquivo" é diferente de "falhou".
    r4 = arquivo.guardar_versao(DOC_ID, 1, texto="markdown", pdf_bytes=None,
                                minio=MinioDeMentira())
    checar(r4["storage_ref"] is None and not r4["erros"]
           and r4["text_storage_ref"] is not None,
           "CONTROLE 3: sem PDF, só o texto — e isso não é falha", str(r4))


def teste_a_linha_que_salva_o_original_continua_no_lugar():
    print("\n[3] 🔴 A costura com o extrator — item 1 e item 4 no mesmo arquivo")
    fonte = ALVO.read_text(encoding="utf-8")
    checar("self._pdf_baixado = {" in fonte,
           "`_baixar_pdf_direto` ainda entrega os bytes para o arquivamento",
           "se sumiu, o PDF volta a ser descartado — e a URL da HDI já dá 500")
    checar("_pdf_baixado = None" in fonte,
           "e o carregador é zerado antes de cada rodada",
           "sem isso um download falho herdaria o PDF do documento anterior")

    # CONTROLE — a busca CONSEGUE não achar. Sem isto, um arquivo lido vazio
    # passaria em tudo acima.
    checar("self._pdf_baixado_que_nao_existe" not in fonte,
           "CONTROLE: a conferência sabe dizer NÃO")

    # CONTROLE 2 — quem LÊ a costura também está lá. Uma ponta sem a outra é
    # um byte guardado que ninguém arquiva.
    checar('getattr(self, "_pdf_baixado", None)' in fonte,
           "CONTROLE 2: `_guardar_a_fonte` lê a costura", "a outra ponta sumiu")


# ── 2. o id versionado ───────────────────────────────────────────────────────

def _servico(db, capturado):
    s = corpus.InsuranceCorpusService(db)

    async def _buscar(_u, _c):
        return "CONDIÇÕES GERAIS " * 60, None

    async def _global(doc, _t, _s, _v):
        capturado.append(dict(doc))
        return 42

    async def _guardar(_i, _n, _t):
        return {"storage_ref": None, "text_storage_ref": None,
                "source_bytes": None, "source_media_type": None,
                "arquivado_em": None, "erros": {}}

    s._buscar, s._ingerir_no_global, s._guardar_a_fonte = _buscar, _global, _guardar
    return s


def teste_o_id_dos_pontos_carrega_a_versao():
    print("\n[4] 📊 hoje 11.409 pontos dividem o id `norm-{uuid}`")
    from test_a_vigencia_mora_na_versao import BancoDeMentira, _versao  # noqa: E402

    vistos: list = []
    db = BancoDeMentira(versoes=[_versao(1)])
    r = asyncio.run(_servico(db, vistos).ingerir(DOC_ID))
    checar(vistos[0]["_qdrant_doc_id"] == f"norm-{DOC_ID}-v2",
           "a versão 2 grava num id só dela", str(vistos[0]["_qdrant_doc_id"]))
    checar(r["qdrant_doc_id"] == f"norm-{DOC_ID}-v2",
           "e o resultado devolve o endereço, para quem for auditar", str(r))

    checar(vistos[0]["_qdrant_doc_ids_anteriores"] == [f"norm-{DOC_ID}"],
           "a anterior é endereçada pelo esquema LEGADO — que é o id real dos "
           "11.409 pontos, não um chute",
           str(vistos[0]["_qdrant_doc_ids_anteriores"]))

    # CONTROLE 1 — quando o banco JÁ sabe o endereço (backfill da migration 02
    # aplicado, ou versão gravada pelo escritor novo), é ele que vale. Sem esta
    # linha, o padrão legado esconderia um endereço correto.
    vistos2: list = []
    db2 = BancoDeMentira(versoes=[_versao(2, qdrant_doc_id=f"norm-{DOC_ID}-v2")])
    asyncio.run(_servico(db2, vistos2).ingerir(DOC_ID))
    checar(vistos2[0]["_qdrant_doc_ids_anteriores"] == [f"norm-{DOC_ID}-v2"],
           "CONTROLE: com endereço no banco, o padrão legado não é usado",
           str(vistos2[0]["_qdrant_doc_ids_anteriores"]))
    checar(vistos2[0]["_qdrant_doc_id"] == f"norm-{DOC_ID}-v3",
           "CONTROLE 2: e a nova é a v3", str(vistos2[0]["_qdrant_doc_id"]))

    # CONTROLE 3 — a primeira captura não tem anterior para apagar. Um
    # apagador que dispara sempre apagaria o que acabou de escrever.
    vistos3: list = []
    db3 = BancoDeMentira(versoes=[])
    asyncio.run(_servico(db3, vistos3).ingerir(DOC_ID))
    checar(vistos3[0]["_qdrant_doc_ids_anteriores"] == [],
           "CONTROLE 3: primeira captura, nada a retirar do índice",
           str(vistos3[0]["_qdrant_doc_ids_anteriores"]))
    checar(vistos3[0]["_qdrant_doc_id"] == f"norm-{DOC_ID}-v1",
           "CONTROLE 4: e ela é a v1", str(vistos3[0]["_qdrant_doc_id"]))


def teste_os_ponteiros_do_arquivo_chegam_na_linha_da_versao():
    print("\n[6] Guardar sem anotar onde é o mesmo que não guardar")
    from test_a_vigencia_mora_na_versao import BancoDeMentira, _versao  # noqa: E402

    REFS = {"storage_ref": f"acervo-normativo/{DOC_ID}/v2/original.pdf",
            "text_storage_ref": f"acervo-normativo/{DOC_ID}/v2/texto.txt",
            "source_bytes": 4096, "source_media_type": "application/pdf",
            "arquivado_em": "2026-08-08T12:00:00+00:00", "erros": {}}

    db = BancoDeMentira(versoes=[_versao(1)])
    s = corpus.InsuranceCorpusService(db)

    async def _buscar(_u, _c):
        return "CONDIÇÕES GERAIS " * 60, None

    async def _global(_d, _t, _s, _v):
        return 42

    async def _guardar(_i, _n, _t):
        return dict(REFS)

    s._buscar, s._ingerir_no_global, s._guardar_a_fonte = _buscar, _global, _guardar
    r = asyncio.run(s.ingerir(DOC_ID))

    nova = db.gravadas("insert", "normative_document_versions")[0][2]
    checar(nova.get("storage_ref") == REFS["storage_ref"],
           "o endereço do original vai para a linha da versão",
           str(nova.get("storage_ref")))
    checar(nova.get("text_storage_ref") == REFS["text_storage_ref"],
           "o do texto também", str(nova.get("text_storage_ref")))
    checar(nova.get("arquivado_em") == REFS["arquivado_em"]
           and nova.get("source_bytes") == 4096,
           "e a data e o tamanho do arquivo junto", str(nova.get("arquivado_em")))
    checar("erros" not in nova,
           "mas os ERROS não vão para o banco — não existe coluna para eles",
           str(list(nova.keys())))
    checar(r.get("arquivado") is True,
           "e quem chamou fica sabendo que foi arquivado", str(r.get("arquivado")))

    # CONTROLE — quando o arquivamento falha, os ponteiros ficam NULOS e o
    # resultado diz que NÃO arquivou. Sem esta linha, o teste acima passaria
    # igual se `ingerir()` copiasse qualquer dicionário para dentro do insert.
    db2 = BancoDeMentira(versoes=[_versao(1)])
    s2 = corpus.InsuranceCorpusService(db2)

    async def _falhou(_i, _n, _t):
        return {"storage_ref": None, "text_storage_ref": None,
                "source_bytes": None, "source_media_type": None,
                "arquivado_em": None, "erros": {"original": "RuntimeError: fora"}}

    s2._buscar, s2._ingerir_no_global, s2._guardar_a_fonte = _buscar, _global, _falhou
    r2 = asyncio.run(s2.ingerir(DOC_ID))
    nova2 = db2.gravadas("insert", "normative_document_versions")[0][2]
    checar(nova2.get("storage_ref") is None and r2.get("arquivado") is False,
           "CONTROLE: falhando, o ponteiro fica nulo e o resultado admite",
           str(r2.get("arquivado")))
    checar(r2.get("arquivo_erros") == {"original": "RuntimeError: fora"},
           "CONTROLE 2: e o motivo real sobe para quem chamou",
           str(r2.get("arquivo_erros")))


def teste_insere_antes_de_apagar():
    print("\n[5] 🔴 Expand, depois contract — a janela vazia deixa de existir")
    arvore = ast.parse(ALVO.read_text(encoding="utf-8"))
    alvo = next((n for n in ast.walk(arvore)
                 if isinstance(n, ast.FunctionDef) and n.name == "_ingerir_sync"), None)
    checar(alvo is not None, "`_ingerir_sync` foi encontrado na árvore sintática")
    if alvo is None:
        return

    def _linhas(nome):
        return sorted(c.func.attr and c.lineno
                      for c in ast.walk(alvo)
                      if isinstance(c, ast.Call)
                      and isinstance(c.func, ast.Attribute)
                      and c.func.attr == nome)

    # 🔴 `_ingerir_sync` tem de LER o id que `ingerir()` calculou. Sem esta
    # guarda, uma mutação que devolvesse `doc_id = f"norm-{doc['id']}"` aqui
    # dentro passava — 📊 e passou, na rodada de mutação de 08/08/2026: os
    # testes só olhavam o dicionário que chega em `_ingerir_no_global`, que é
    # um duplo. O valor calculado só vale se o consumidor o consome.
    lidos = [n.args[0].value for n in ast.walk(alvo)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "get" and n.args
             and isinstance(n.args[0], ast.Constant)]
    checar("_qdrant_doc_id" in lidos,
           "`_ingerir_sync` LÊ o id versionado que `ingerir()` calculou",
           f"chaves lidas: {lidos} — se sumiu, o id volta a ser o mesmo para "
           "todas as versões e a nova apaga a anterior")
    checar("_qdrant_doc_ids_anteriores" in lidos,
           "e lê também a lista do que precisa sair do índice", str(lidos))

    # CONTROLE — o coletor CONSEGUE não achar.
    checar("_uma_chave_que_ninguem_le" not in lidos,
           "CONTROLE: o coletor de chaves devolve só o que existe")

    insercoes, remocoes = _linhas("insert_embeddings"), _linhas("delete_document")
    checar(len(insercoes) == 1 and len(remocoes) == 1,
           "há exatamente uma inserção e uma remoção — nenhum delete extra "
           "sobrou antes dela",
           f"insert={insercoes} delete={remocoes}")
    if not (insercoes and remocoes):
        return
    checar(insercoes[0] < remocoes[0],
           "a INSERÇÃO acontece antes da REMOÇÃO",
           f"insert na linha {insercoes[0]}, delete na {remocoes[0]} — "
           "nesta ordem existe uma janela em que o documento some da busca")

    # CONTROLE — o localizador CONSEGUE não achar. Sem esta linha, um `_linhas`
    # quebrado devolveria [] para tudo e a comparação nunca reprovaria... e a
    # guarda acima seria decoração.
    checar(_linhas("uma_chamada_que_nao_existe") == [],
           "CONTROLE: o localizador devolve vazio para o que não existe")

    # CONTROLE 2 — a remoção percorre os endereços das versões anteriores, e
    # não o da própria. Sem isto, a ordem certa apagaria o que acabou de entrar.
    fonte = ALVO.read_text(encoding="utf-8")
    checar("for antigo in anteriores:" in fonte,
           "CONTROLE 2: a remoção é sobre `anteriores`, não sobre `doc_id`")
    checar('if d and d != doc_id' in fonte,
           "CONTROLE 3: e o id da versão nova é excluído da lista a apagar")


def main() -> int:
    print("=" * 74)
    print("O ACERVO GUARDA A FONTE, E O ÍNDICE SABE DE QUE VERSÃO VEIO O PEDAÇO")
    print("=" * 74)
    for teste in (teste_o_pdf_e_o_texto_sao_guardados_e_relidos,
                  teste_falhar_ao_arquivar_nao_derruba_e_nao_finge,
                  teste_a_linha_que_salva_o_original_continua_no_lugar,
                  teste_o_id_dos_pontos_carrega_a_versao,
                  teste_os_ponteiros_do_arquivo_chegam_na_linha_da_versao,
                  teste_insere_antes_de_apagar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X     {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O PDF FICA, O TEXTO FICA, E A VERSÃO NOVA NÃO APAGA A ANTERIOR ÀS CEGAS")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
