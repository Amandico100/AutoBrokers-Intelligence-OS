"""PDF publico e ARQUIVO. Baixar arquivo nao precisa de crawler pago.

Rodar: python backend/tests/test_pdf_publico_nao_precisa_de_credito.py

A HISTORIA
----------
Dez documentos normativos — condicoes gerais e manuais do segurado da HDI,
Tokio, Azul e Bradesco — ficaram parados no corpus com o motivo gravado no
banco: "credito do Firecrawl esgotado — aguardando plano".

Estavam esperando credito para uma tarefa que um GET resolve. TODOS os dez ja
tinham no banco uma URL de PDF direta. O crawler faz falta para DESCOBRIR
documento novo; para baixar o que ja foi descoberto, nao.

  medido em 05/08/2026, contra as 10 URLs reais do banco
  9 de 10 baixaram por GET direto — 3,9 milhoes de caracteres
  o decimo (condicoes gerais da HDI) devolve HTTP 500 no servidor deles

A LINHA DE CONTROLE (CLAUDE.md 9.2)
-----------------------------------
Um atalho que baixasse tudo e nunca cedesse ao crawler seria pior que o
problema: pagina HTML, PDF escaneado e arquivo protegido PRECISAM do crawler,
que renderiza. Entao cada caso abaixo vem em par — o que o GET resolve, e o
que ele tem de recusar para o crawler assumir.

E o par que fecha: a mesma funcao `_buscar`, com uma URL de PDF que funciona,
NAO pode chamar o crawler; com uma URL de pagina, tem de chamar. Sem esse par,
um atalho quebrado passaria despercebido — o crawler cobriria o erro em
silencio, e so a fatura contaria a verdade.

O QUE MUDOU EM 08/08/2026 (SPEC-067 §4.1)
-----------------------------------------
O extrator deixou de ser o PyPDF2 e passou a ser o PyMuPDF. A licao deste teste
nao mudou uma virgula — o GET resolve, o crawler continua indispensavel para o
que ele nao resolve —, entao o que mudou aqui foi so o dublê: onde havia um
`PyPDF2.PdfReader` de mentira, agora ha um `fitz` de mentira.

O motivo da troca, medido no mesmo PDF (Porto CG140): 📊 PyPDF2 devolve 519
linhas, PyMuPDF devolve 11.064. O PyPDF2 colapsa a pagina inteira numa linha
so — e sem linha nao existe titulo, nem secao, nem corte por secao.

E este teste ganhou um par novo por causa disso: as paginas voltam separadas
pela MARCA DE PAGINA, porque a limpeza de rodape da §4.2 so funciona sabendo
onde cada pagina comeca e acaba.
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FALHAS = []


def checar(nome, condicao, detalhe=None):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FALHAS.append((nome, detalhe))
        print(f"  [X] {nome}{': ' + str(detalhe) if detalhe else ''}")


for _n in ("app", "app.services", "app.services.knowledge", "app.services.research"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []

_spec = importlib.util.spec_from_file_location(
    "app.services.knowledge.insurance_corpus",
    ROOT / "app" / "services" / "knowledge" / "insurance_corpus.py")
corpus = importlib.util.module_from_spec(_spec)
sys.modules["app.services.knowledge.insurance_corpus"] = corpus
_spec.loader.exec_module(corpus)


# --------------------------------------------------------------------------
# Um httpx de mentira: devolve o que o teste mandar, sem tocar a rede.
# --------------------------------------------------------------------------
class _Resposta:
    def __init__(self, status, corpo):
        self.status_code = status
        self.content = corpo


class _ClienteFalso:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None):
        _ClienteFalso.ultimo_cabecalho = headers or {}
        return _ClienteFalso.proxima


def _com_resposta(status, corpo):
    """Instala o httpx falso e devolve o modulo httpx dedurado."""
    falso = types.ModuleType("httpx")
    _ClienteFalso.proxima = _Resposta(status, corpo)
    falso.AsyncClient = _ClienteFalso
    sys.modules["httpx"] = falso
    return falso


def _pdf(texto_por_pagina):
    """Um PDF de mentira: o cabecalho de verdade + marcador para o leitor falso."""
    return b"%PDF-1.4\n" + repr(texto_por_pagina).encode("utf-8")


class _PaginaFalsa:
    def __init__(self, texto):
        self._t = texto

    def get_text(self, _modo="text"):
        return self._t


class _DocumentoFalso:
    def __init__(self, corpo):
        bruto = corpo[len(b"%PDF-1.4\n"):].decode("utf-8")
        self._paginas = [_PaginaFalsa(t) for t in eval(bruto)]  # noqa: S307 — dado do teste

    def __iter__(self):
        return iter(self._paginas)

    def close(self):
        return None


def _instalar_leitor():
    """O extrator de mentira. Hoje e `fitz` (PyMuPDF); ate 08/08/2026 era PyPDF2."""
    mod = types.ModuleType("fitz")
    mod.open = lambda stream=None, filetype=None: _DocumentoFalso(stream)
    sys.modules["fitz"] = mod


def rodar():
    print("== PDF publico nao precisa de credito ==\n")
    _instalar_leitor()
    servico = corpus.InsuranceCorpusService.__new__(corpus.InsuranceCorpusService)
    # `_raw` e o cliente do banco, que o crawler recebe. Sem ele o caminho do
    # crawler MORRE com AttributeError em vez de REPROVAR — e a bateria para no
    # meio, escondendo as checagens seguintes. Foi assim que a mutacao "o atalho
    # some" passou despercebida na primeira rodada.
    servico._raw = None

    LONGO = "CONDICOES GERAIS. Processo SUSEP 15414.900000/2019-00. " + ("clausula " * 120)

    # ------------------------------------------------------------ bloco 1
    print("-- 1. o que o GET resolve --")
    _com_resposta(200, _pdf([LONGO]))
    texto, motivo = asyncio.run(servico._baixar_pdf_direto("https://x.com/cg.pdf"))
    checar("PDF de verdade e longo: baixou", bool(texto) and motivo is None, motivo)
    checar("e o texto extraido chegou inteiro", "SUSEP" in (texto or ""), (texto or "")[:60])
    checar("mandou cabecalho de navegador (servidor de seguradora recusa sem)",
           "User-Agent" in getattr(_ClienteFalso, "ultimo_cabecalho", {}),
           getattr(_ClienteFalso, "ultimo_cabecalho", {}))
    duas = asyncio.run(_duas_paginas(servico, LONGO)) or ""
    checar("varias paginas viram um texto so", len(duas) > len(LONGO),
           "juncao de paginas")
    # 🔴 O par novo de 08/08/2026: as paginas voltam SEPARADAS. A limpeza da
    # §4.2 remove rodape e numero de pagina, e as duas regras precisam saber
    # onde a pagina comeca. Se a marca sumir, elas param de funcionar em
    # silencio — e o pedaco volta a comecar com "C.N.P.J. 61.198.164/0001-60".
    checar("e a fronteira entre elas sobrevive",
           duas.count(corpus.MARCA_DE_PAGINA) == 1,
           f"marcas={duas.count(corpus.MARCA_DE_PAGINA)}")

    # ------------------------------------------------------------ bloco 2
    #
    # O PAR DE CONTROLE. Sem estes, um atalho que dissesse "sim" para tudo
    # passaria no bloco 1 inteiro — e o crawler nunca mais seria chamado, nem
    # onde e o unico que resolve.
    print("\n-- 2. CONTROLE: o que o GET tem de RECUSAR --")
    _com_resposta(200, b"<html>pagina de erro com extensao .pdf na url</html>")
    _, m = asyncio.run(servico._baixar_pdf_direto("https://x.com/mentira.pdf"))
    checar("corpo que nao e PDF: recusa (vai para o crawler)", m == "nao_e_pdf", m)

    _com_resposta(200, _pdf(["", "  ", ""]))
    _, m = asyncio.run(servico._baixar_pdf_direto("https://x.com/escaneado.pdf"))
    checar("PDF escaneado (sem texto): recusa, nao polui o corpus",
           m == "conteudo_insuficiente", m)

    _com_resposta(500, b"")
    _, m = asyncio.run(servico._baixar_pdf_direto("https://x.com/quebrado.pdf"))
    checar("servidor fora do ar: devolve o motivo, nao levanta", m == "HTTP 500", m)

    _com_resposta(200, b"%PDF-1.4\n" + b"x" * (61 * 1024 * 1024))
    _, m = asyncio.run(servico._baixar_pdf_direto("https://x.com/gigante.pdf"))
    checar("arquivo gigante: recusa antes de derrubar o worker",
           m == "arquivo_grande_demais", m)

    # ------------------------------------------------------------ bloco 3
    #
    # O par que da direito a concluir: a MESMA funcao decide sozinha quando o
    # crawler entra. Se ela chamasse o crawler mesmo com o PDF na mao, o
    # bloco 1 continuaria verde e a fatura e que contaria a verdade.
    print("\n-- 3. o crawler so entra quando precisa --")
    chamou = []

    def _fingir_crawler(disponivel):
        mod = types.ModuleType("app.services.research.firecrawl")

        class _Cli:
            def __init__(self, *a, **k):
                pass

            async def scrape(self, url, **k):
                chamou.append(url)
                raise RuntimeError("nao deveria ter sido chamado")

        mod.FirecrawlClient = _Cli
        mod.configurado = lambda: disponivel
        sys.modules["app.services.research.firecrawl"] = mod

    _fingir_crawler(True)
    _com_resposta(200, _pdf([LONGO]))
    texto, motivo = asyncio.run(servico._buscar("https://x.com/cg.pdf", None))
    checar("PDF baixado: o crawler NAO foi chamado", not chamou, chamou)
    checar("e o texto voltou por _buscar", bool(texto) and motivo is None, motivo)

    chamou.clear()
    _fingir_crawler(False)
    texto, motivo = asyncio.run(servico._buscar("https://x.com/uma-pagina-html", None))
    checar("CONTROLE — URL que nao e PDF: cai no crawler (aqui, ausente)",
           texto is None and motivo == "firecrawl_nao_configurado", (texto, motivo))

    chamou.clear()
    _com_resposta(200, b"<html>nao e pdf</html>")
    _fingir_crawler(False)
    texto, motivo = asyncio.run(servico._buscar("https://x.com/mentira.pdf", None))
    checar("CONTROLE — .pdf que falha no GET: cede o lugar ao crawler",
           texto is None and motivo == "firecrawl_nao_configurado", (texto, motivo))

    print(f"\n{'=' * 60}")
    print(f"PASS={PASS} FAIL={FAIL}")
    if FALHAS:
        print("\nFALHAS:")
        for n, d in FALHAS:
            print(f"  - {n}: {d}")
    return 1 if FAIL else 0


async def _duas_paginas(servico, longo):
    _com_resposta(200, _pdf([longo, longo]))
    texto, _ = await servico._baixar_pdf_direto("https://x.com/duas.pdf")
    return texto


if __name__ == "__main__":
    sys.exit(rodar())
