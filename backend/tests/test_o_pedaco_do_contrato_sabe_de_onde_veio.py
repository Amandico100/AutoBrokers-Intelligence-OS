"""Um pedaco de condicao geral tem de dizer de quem e, de onde saiu, e caber sozinho.

Rodar: PYTHONIOENCODING=utf-8 python backend/tests/test_o_pedaco_do_contrato_sabe_de_onde_veio.py

A HISTORIA
----------
O acervo tinha 11.409 pedacos de condicoes gerais no indice. Medido em
08/08/2026, sobre os PDFs reais de Porto, Bradesco, Mapfre, Tokio e Azul:

  📊  67% terminavam no meio de uma frase
  📊  41% comecavam no meio de uma frase
  📊  91% nao diziam de que secao do contrato sairam
  📊  75% nao diziam de que seguradora eram — 29 de 11.409 tinham etiqueta

Nao era um defeito, eram quatro empilhados, e o de baixo era o extrator.
O PyPDF2 colapsa a pagina inteira numa linha so — 📊 519 linhas contra as
11.064 do PyMuPDF no mesmo CG140. Sem linha nao ha titulo; sem titulo nao ha
secao; sem secao o corte so pode ser por regua de caracteres, que e o que corta
frase no meio. E o cabecalho de procedencia era concatenado ANTES de picar,
entao ele ficava no pedaco 0 e mais nenhum.

O caso que resume tudo: no e-Residencial do Bradesco a frase
"Ate 02 (duas) utilizacoes durante a vigencia do seguro" aparece 📊 27 vezes,
em 27 assistencias diferentes. Fora da secao, um pedaco com essa frase e
indistinguivel dos outros 26 — e o limite que o segurado pergunta ("linha
branca") esta, no documento, escrito sob `4.2. CONSERTO LINHA MARROM`.
Responder isso sem o caminho e responder errado com cara de documento oficial.

A LINHA DE CONTROLE (CLAUDE.md 9.2)
-----------------------------------
Todo bloco abaixo roda o MESMO texto por dois cortadores: o novo, por secao, e
uma regua de 1.000 caracteres que imita o que existia antes. O novo tem de
passar; a regua tem de REPROVAR. Sem esse par, um cortador que devolvesse o
documento inteiro num pedaco so passaria em quase tudo, e ninguem notaria.
"""

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


for _n in ("app", "app.services", "app.services.knowledge", "app.services.research"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []

_ARQUIVO = RAIZ / "app" / "services" / "knowledge" / "insurance_corpus.py"
_spec = importlib.util.spec_from_file_location(
    "app.services.knowledge.insurance_corpus", _ARQUIVO)
corpus = importlib.util.module_from_spec(_spec)
sys.modules["app.services.knowledge.insurance_corpus"] = corpus
_spec.loader.exec_module(corpus)

DOC = {
    "insurer_name": "Bradesco Seguros", "insurer_key": "bradesco",
    "product_line": "residencial", "doc_kind": "condicoes_gerais",
    "title": "Bradesco e-Residencial — Condições Gerais (mar/2025)",
}
SUSEP = "15414.638130/2022-49"
VIGENCIA = "2025-03-01"


# ---------------------------------------------------------------------------
# O cortador que existia antes: regua de 1.000 caracteres, cabecalho na frente.
# Nao e caricatura — e o `RecursiveCharacterTextSplitter(chunk_size=1000)` que
# estava em `_ingerir_sync`, reduzido ao essencial para nao depender do
# langchain aqui.
# ---------------------------------------------------------------------------
def picar_por_regua(doc: dict, texto: str, susep: str, vigencia: str,
                    tamanho: int = 1000) -> list[str]:
    cabecalho = (f"# {doc['title']}\n**Seguradora:** {doc['insurer_name']}\n"
                 f"**Processo SUSEP:** {susep}\n**Vigência:** {vigencia}\n\n---\n\n")
    inteiro = cabecalho + texto.replace("\f", "\n")
    return [inteiro[i:i + tamanho] for i in range(0, len(inteiro), tamanho)]


def _corpo(pedaco: str) -> str:
    linhas = pedaco.split("\n")
    return "\n".join(linhas[2:]).strip() if len(linhas) > 2 else ""


def _caminho(pedaco: str) -> str:
    linhas = pedaco.split("\n")
    return linhas[1].strip() if len(linhas) > 1 else ""


# ---------------------------------------------------------------------------
# As pecas reais do documento, reproduzidas com a MESMA forma que o PDF entrega:
# numero orfao numa linha, titulo na seguinte; mobilia no rodape de cada pagina;
# sumario com pontinhos; e a frase do limite repetida em secoes diferentes.
# ---------------------------------------------------------------------------
def _pagina(numero: int, miolo: str) -> str:
    return miolo.strip("\n") + (
        f"\n\n{numero}\nVersão: Março/2025\nBradesco Seguro e-Residencial\n"
        f"Processo SUSEP Nº: 15414.638130/2022-49")


SUMARIO = """
ASSISTÊNCIA LINHA BRANCA E LINHA MARROM ------------------------------------------------- 89
1.
OBJETO E DEFINIÇÕES --------------------------------------------------------------------- 89
4.
OS SERVIÇOS ----------------------------------------------------------------------------- 93
4.1.
CONSERTO LINHA BRANCA ------------------------------------------------------------------- 93
4.2.
CONSERTO LINHA MARROM ------------------------------------------------------------------- 94
5.
LIMITE DE DURAÇÃO DA ASSISTÊNCIA -------------------------------------------------------- 94
6.
LIMITE TERRITORIAL DA ASSISTÊNCIA ------------------------------------------------------- 95
7.
EXCLUSÕES ------------------------------------------------------------------------------- 96
8.
DISPOSIÇÕES FINAIS ---------------------------------------------------------------------- 97
"""

CORPO_1 = """
ASSISTÊNCIA RESIDENCIAL
4.14.
LOCAÇÃO DE ELETROELETRÔNICOS (LINHA MARROM)
Se, em consequência de evento Emergencial os eletroeletrônicos que guarnecem a
residência ficarem inutilizados, a Assistência Residencial providenciará a locação de
outro equipamento com a mesma funcionalidade para uso provisório.
São considerados aparelhos de linha Marrom televisores, aparelhos de som, aparelhos de
DVD, computadores e videogames.
4.14.1.
Limites de Utilização
Limitado a 7 dias por evento, você pode alugar eletroeletrônicos com um valor máximo
total de até R$ 150,00 (cento e cinquenta reais) por evento;
Até 02 (duas) utilizações durante a vigência do seguro.
"""

CORPO_2 = """
ASSISTÊNCIA LINHA BRANCA E LINHA MARROM
4.
OS SERVIÇOS
Para todos os serviços da Assistência Linha Branca e Linha Marrom, a responsabilidade da
Assistência se limita à organização e credenciamento de Prestadores.
4.1.
CONSERTO LINHA BRANCA
Se solicitado pelo Usuário, a Assistência providenciará o envio de Prestador para reparo
de eletrodomésticos do tipo Linha Branca.
Os custos de troca ou substituição de qualquer peça serão de responsabilidade do Usuário.
IMPORTANTE: PARA APARELHOS COM FABRICAÇÃO SUPERIOR A 5 (CINCO) ANOS, PODERÁ
OCORRER A INDISPONIBILIDADE DE EXECUÇÃO DO SERVIÇO DEVIDO À FALTA DE PEÇAS DE
REPOSIÇÃO.
4.2.
CONSERTO LINHA MARROM
Se solicitado pelo Usuário, a Assistência providenciará o envio de Prestador para reparo
de eletroeletrônicos do tipo Linha Marrom.
4.2.1.
Limites de Utilização
Limitado a R$ 350,00 (trezentos e cinquenta reais) de mão de obra exclusivamente para
coifas e depuradores;
Até 02 (duas) utilizações durante a vigência do seguro.
"""

CORPO_3 = """
ASSISTÊNCIA PET
4.9.
CONSULTA VETERINÁRIA EMERGENCIAL
A Assistência Pet providenciará a consulta veterinária emergencial do animal doméstico.
4.9.1.
Limites de Utilização
Até 02 (duas) utilizações durante a vigência do seguro.
"""

TABELA = """
CLÁUSULAS DE CARRO RESERVA 26 (A, B, C, E, F, G, H, I, J, K, L, M, U, V, W, X)
2.
Garantias e limites de utilização por evento
2.1.
Para o carro reserva – locação:
Cláusulas
Tipo de Locadora
Essencial
Completo
Referenciada
26C
26J
26A
26H
Porte do veículo locado
Básico Médio Básico Médio
Perda Parcial
630
882
1350
1890
Indenização Integral
630
882
1350
1890
Notas
(1)
(2)
(1)
(2)
(1) Valores expressos em reais, considerando o Limite diário R$ 90,00.
(2) Valores expressos em reais, considerando o Limite diário R$ 126,00.
"""


# Uma frase de CONTEUDO que se repete em 8 paginas, sempre no MEIO delas. E o
# sosia da mobilia: repete tanto quanto um rodape, e nao e rodape.
LINHA_QUE_REPETE = ("A franquia deverá ser paga pelo segurado diretamente à oficina "
                    "que reparou o veículo.")

# Uma secao grande de verdade — ~4.500 caracteres. Sem ela, todas as secoes do
# documento de teste caberiam num pedaco so e o empacotador nunca seria exercido.
SECAO_GRANDE = "7. EXCLUSÕES\n" + "\n".join(
    f"Fica excluída da cobertura a hipótese número {n}, bem como qualquer evento "
    f"que dela decorra, direta ou indiretamente, ainda que a Assistência tenha "
    f"sido previamente acionada pelo Usuário e ainda que o Prestador já tenha se "
    f"deslocado até o Domicílio informado no Cadastro, observados os termos, "
    f"condições e limites destas Condições Gerais."
    for n in range(1, 11))


def _enchimento(k: int) -> str:
    linhas = [f"Parágrafo de enchimento {k}.{j}, que existe apenas para dar corpo "
              f"e páginas ao documento de teste." for j in range(16)]
    linhas.insert(8, LINHA_QUE_REPETE)
    return "\n".join(linhas)


def documento_de_teste() -> str:
    """As paginas do documento, separadas pela marca de pagina."""
    paginas = [_pagina(88, SUMARIO), _pagina(89, CORPO_1), _pagina(90, CORPO_2),
               _pagina(91, CORPO_3), _pagina(92, TABELA), _pagina(93, SECAO_GRANDE)]
    # A mobilia so e mobilia quando repete: mais paginas, mesmo rodape.
    paginas += [_pagina(94 + k, _enchimento(k)) for k in range(8)]
    # E cinco paginas curtas em que a MESMA frase de conteudo cai na borda. E o
    # caso dificil: ela repete em 5 paginas na faixa do rodape, exatamente como
    # mobilia. O que a salva e a proporcao — a maioria das ocorrencias dela esta
    # no meio das outras paginas.
    paginas += [_pagina(102 + k, f"{LINHA_QUE_REPETE}\nObservação curta {k}.")
                for k in range(5)]
    return corpus.MARCA_DE_PAGINA.join(paginas)


# ---------------------------------------------------------------------------
def bloco_1_o_extrator():
    print("\n[1] O extrator e o PyMuPDF, e a pagina continua sendo pagina")

    fonte = _ARQUIVO.read_text(encoding="utf-8")
    checar("from PyPDF2" not in fonte and "PdfReader(" not in fonte,
           "o corpus normativo nao IMPORTA mais PyPDF2",
           "📊 519 linhas contra 11.064 no mesmo CG140")
    requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    checar("PyMuPDF" in requisitos, "PyMuPDF esta em requirements.txt",
           "dependencia declarada, nao implicita")

    # Um `fitz` de mentira: nao toca disco nem rede, e dedura como foi chamado.
    chamada = {}

    class _Pagina:
        def __init__(self, texto):
            self._t = texto

        def get_text(self, modo):
            chamada["modo"] = modo
            return self._t

    class _Documento:
        def __init__(self, paginas):
            self._p = [_Pagina(t) for t in paginas]

        def __iter__(self):
            return iter(self._p)

        def close(self):
            chamada["fechou"] = True

    falso = types.ModuleType("fitz")

    def _abrir(stream=None, filetype=None):
        chamada["filetype"] = filetype
        return _Documento(["PAGINA UM\nlinha dois", "PAGINA DOIS\nlinha dois"])

    falso.open = _abrir
    sys.modules["fitz"] = falso

    texto, erro = corpus.extrair_texto_de_pdf(b"%PDF-1.7 qualquer coisa")
    checar(erro is None and texto is not None, "extraiu sem erro", str(erro))
    checar(chamada.get("modo") == "text" and chamada.get("filetype") == "pdf",
           "leu pagina a pagina com get_text('text')", str(chamada))
    checar(texto.count(corpus.MARCA_DE_PAGINA) == 1,
           "as paginas voltam SEPARADAS pela marca de pagina",
           "e a limpeza de rodape depende disso")
    checar(corpus._hash(texto) == corpus._hash(texto.replace("\f", "\n")),
           "CONTROLE — a marca de pagina NAO muda o hash de conteudo",
           "senao todo documento pareceria ter mudado na origem")

    # CONTROLE: extrator que estoura devolve motivo, nao derruba o worker.
    def _explodir(stream=None, filetype=None):
        raise RuntimeError("pdf corrompido")

    falso.open = _explodir
    texto, erro = corpus.extrair_texto_de_pdf(b"%PDF-1.7")
    checar(texto is None and (erro or "").startswith("pdf_ilegivel"),
           "CONTROLE — PDF ilegivel devolve motivo e nao levanta", str(erro))

    sys.modules.pop("fitz", None)


# ---------------------------------------------------------------------------
def bloco_2_a_limpeza():
    print("\n[2] A limpeza da §4.2, na ordem exata")

    linhas = corpus.limpar(documento_de_teste())
    junto = "\n".join(linhas)

    checar("4.2. CONSERTO LINHA MARROM" in junto,
           "numero orfao grudou no titulo da linha seguinte",
           "📊 o Bradesco quebra `4.2.` e `CONSERTO LINHA MARROM` em duas linhas")
    checar(junto.count("CONSERTO LINHA MARROM") == 1,
           "o sumario foi descartado — a secao nao aparece duas vezes",
           "📊 uma linha de indice competindo com a clausula de verdade")
    checar("Versão: Março/2025" not in junto and "Processo SUSEP Nº" not in junto,
           "a mobilia de rodape saiu",
           "repetida em 14 paginas, sempre na borda")
    checar("\n89\n" not in f"\n{junto}\n" and "\n92\n" not in f"\n{junto}\n",
           "o numero de pagina saiu — ele anda de 1 em 1",
           "88, 89, 90 … 101")

    # ⚠️ AS TRES LINHAS DE CONTROLE QUE IMPEDEM A LIMPEZA DE COMER CONTEUDO.
    checar(junto.count(LINHA_QUE_REPETE) == 13,
           "CONTROLE — frase de conteudo repetida em 13 paginas sobreviveu inteira",
           f"8 no meio + 5 na borda; achadas {junto.count(LINHA_QUE_REPETE)}")

    # CONTROLE do passo 4: documento SEM paginacao. Os numeros soltos das
    # tabelas ficam na borda da pagina e nao formam progressao nenhuma — quem
    # remover "o numero da borda" sem exigir a progressao come a resposta.
    sem_paginacao = corpus.MARCA_DE_PAGINA.join([
        "Tabela de limites\n630\nLimite diário R$ 90,00.",
        "Outra tabela\n882\nLimite diário R$ 126,00.",
        "Mais uma tabela\n1350\nLimite diário R$ 180,00.",
    ])
    solto = "\n".join(corpus.limpar(sem_paginacao))
    checar("630" in solto and "882" in solto and "1350" in solto,
           "CONTROLE — sem progressao de paginas, nenhum numero e removido",
           solto.replace("\n", " | "))
    checar(junto.count("Até 02 (duas) utilizações durante a vigência do seguro.") == 3,
           "CONTROLE — e a frase identica em 3 secoes diferentes tambem",
           "📊 ela aparece 27x no e-Residencial; apaga-la apagaria 27 respostas")
    checar("\n630\n" in f"\n{junto}\n" and "\n882\n" in f"\n{junto}\n",
           "CONTROLE — valor puramente numerico de tabela sobreviveu",
           "📊 `630` e `882` sao a resposta de carro reserva da Porto")


# ---------------------------------------------------------------------------
def bloco_3_os_titulos():
    print("\n[3] Os titulos da §4.3, com as duas guardas medidas")

    linhas = corpus.limpar(documento_de_teste())
    titulos = corpus.detectar_titulos(linhas)
    textos = {t for _, t in titulos.values()}

    checar("4.2. CONSERTO LINHA MARROM" in textos,
           "`4.2. CONSERTO LINHA MARROM` e titulo", "e o caminho depende dele")
    caixas_altas = [t for t in textos if "IMPORTANTE" in t or "REPOSIÇÃO" in t
                    or "INDISPONIBILIDADE" in t]
    checar(not caixas_altas,
           "⚠️ duas linhas de CAIXA-ALTA seguidas sao paragrafo, nao titulo",
           f"📊 sem esta guarda o aviso apagava a linha marrom do caminho: {caixas_altas}")

    # ⚠️ A monotonicidade: um pico isolado nao pode condenar o resto do arquivo.
    corpo = ("CLÁUSULA 109 – COBERTURA DA PELÍCULA PPF\n"
             "A lista de coberturas cita esta cláusula antes de o contrato começar.\n"
             "CLÁUSULA 20 – REEMBOLSO DE DESPESAS EXTRAORDINÁRIAS\n"
             "Mediante pagamento de prêmio adicional, a seguradora reembolsa despesas.\n"
             "CLÁUSULA 76R – DANOS A VIDROS E RETROVISORES\n"
             "Em caso de quebra ou trinca, a seguradora garantirá a troca do vidro.\n"
             "CLÁUSULA 89A – DANOS A RODA, PNEU E SUSPENSÃO\n"
             "Esta cobertura garante ao segurado substituição da roda e do pneu.\n")
    raizes = [t for n, t in corpus.detectar_titulos(corpus.limpar(corpo)).values() if n == 1]
    checar(any("76R" in t for t in raizes) and any("89A" in t for t in raizes),
           "um numero alto citado fora de ordem nao mata as clausulas seguintes",
           f"📊 no CG140 a `CLÁUSULA 109` aparece 1.000 linhas antes do corpo: {raizes}")
    checar(not any("109" in t for t in raizes),
           "e o pico solto e ele que cai fora", str(raizes))

    # CONTROLE DO MECANISMO: sem o pico, a sequencia inteira e aceita. Se este
    # falhasse, a guarda estaria recusando tudo e o teste acima seria vazio.
    sem_pico = corpo.split("CLÁUSULA 20", 1)[1]
    raizes_2 = [t for n, t in
                corpus.detectar_titulos(corpus.limpar("CLÁUSULA 20" + sem_pico)).values()
                if n == 1]
    checar(len(raizes_2) == 3,
           "CONTROLE — sem o pico, as tres clausulas em ordem sao aceitas",
           str(raizes_2))


# ---------------------------------------------------------------------------
def bloco_4_o_corte():
    print("\n[4] O corte por secao: bloco inteiro, nunca ao meio")

    pedacos = corpus.montar_pedacos(DOC, documento_de_teste(), SUSEP, VIGENCIA)
    checar(bool(pedacos), "o documento virou pedacos", str(len(pedacos)))

    fim = [p for p in pedacos if not _corpo(p).rstrip().endswith(
        (".", ";", ":", "!", "?", ")", '"'))]
    checar(len(fim) <= max(1, len(pedacos) // 4),
           "quase nenhum pedaco termina no meio de uma frase",
           f"📊 antes eram 67% — aqui {len(fim)} de {len(pedacos)}")

    so_titulo = [p for p in pedacos if len(_corpo(p)) < 40]
    checar(not so_titulo, "nenhum pedaco e so titulo", str(so_titulo[:1]))

    grandes = [p for p in pedacos if len(_corpo(p)) > corpus.TETO_PEDACO]
    # Um bloco maior que o teto vira pedaco sozinho — e permitido, e o preco de
    # nunca dividir bloco. O que nao pode e haver muitos.
    checar(len(grandes) <= 1, "no maximo um bloco estourou o teto sozinho",
           f"teto={corpus.TETO_PEDACO} · {[len(_corpo(p)) for p in grandes]}")

    # A secao grande e empacotada em BLOCOS ate ~1.400, teto 2.200 — e nao um
    # pedaco por paragrafo. ~4.500 caracteres cabem em 3 a 4 pedacos.
    grande = [p for p in pedacos if "EXCLUSÕES" in _caminho(p)]
    media = sum(len(_corpo(p)) for p in grande) / max(1, len(grande))
    checar(len(grande) >= 2, "a secao grande virou varios pedacos", str(len(grande)))
    checar(media >= 900,
           "e cada um deles chega perto do alvo — o empacotador enche antes de cortar",
           f"média={media:.0f} · alvo={corpus.ALVO_PEDACO} teto={corpus.TETO_PEDACO}")
    checar(all(len(_corpo(p)) <= corpus.TETO_PEDACO for p in grande),
           "e nenhum deles passou do teto", str([len(_corpo(p)) for p in grande][:6]))

    # A tabela e ATOMICA e traz as notas de rodape junto. A checagem e feita na
    # REGIAO, nao no pedaco: se dependesse do empacotamento, uma secao pequena
    # esconderia o defeito juntando tabela e notas por acaso.
    linhas = corpus.limpar(documento_de_teste())
    titulos = corpus.detectar_titulos(linhas)
    regioes = corpus.regioes_de_tabela(linhas, titulos)
    dentro = ["\n".join(linhas[i:f]) for i, f in regioes.items()]
    grade = [d for d in dentro if "630" in d and "882" in d]
    checar(len(grade) == 1, "a grade da tabela e UMA regiao atomica", str(len(dentro)))
    if grade:
        checar("Limite diário R$ 90,00" in grade[0] and "R$ 126,00" in grade[0],
               "⚠️ e as notas de rodape estao DENTRO da mesma regiao",
               "📊 sem a nota, `630` e numero sem unidade")
    com_tabela = [p for p in pedacos if "630" in p and "882" in p]
    checar(len(com_tabela) == 1, "e ela cai num pedaco so", str(len(com_tabela)))

    # CONTROLE: a regua de 1.000 caracteres REPROVA nas mesmas checagens.
    regua = picar_por_regua(DOC, documento_de_teste(), SUSEP, VIGENCIA)
    fim_regua = [p for p in regua if not p.rstrip().endswith(
        (".", ";", ":", "!", "?", ")", '"'))]
    checar(len(fim_regua) > len(regua) // 2,
           "CONTROLE — a regua de 1.000 corta frase no fim na MAIORIA dos pedacos",
           f"{len(fim_regua)} de {len(regua)}")
    meio_regua = [p for p in regua if p[:1].islower()]
    checar(bool(meio_regua),
           "CONTROLE — e comeca pedaco no meio da frase",
           f"{len(meio_regua)} de {len(regua)}: {meio_regua[0][:48] if meio_regua else ''}")


# ---------------------------------------------------------------------------
def bloco_5_o_cabecalho():
    print("\n[5] O cabecalho e montado DEPOIS de picar — em TODO pedaco")

    pedacos = corpus.montar_pedacos(DOC, documento_de_teste(), SUSEP, VIGENCIA)
    com_etiqueta = [p for p in pedacos if p.startswith("[Bradesco Seguros · residencial")]
    checar(len(com_etiqueta) == len(pedacos),
           "TODO pedaco comeca com a etiqueta da seguradora",
           f"📊 antes eram 29 de 11.409 — aqui {len(com_etiqueta)} de {len(pedacos)}")
    checar(all("SUSEP 15414.638130/2022-49" in p for p in pedacos),
           "e todo pedaco carrega o processo SUSEP")
    checar(all("vigência 01/03/2025" in p for p in pedacos),
           "e a vigencia, em data legivel",
           "apolice antiga e regida pela condicao da emissao")
    com_caminho = [p for p in pedacos if _caminho(p)]
    checar(len(com_caminho) == len(pedacos),
           "e o caminho da secao de onde ele saiu",
           f"📊 antes 91% nao sabiam — aqui {len(pedacos) - len(com_caminho)}")

    # O teto de 400 do caminho.
    fundo = ["RAIZ " + "A" * 200, "MEIO " + "B" * 200, "OUTRO " + "C" * 200,
             "FOLHA " + "D" * 200]
    curto = corpus._caminho_em_texto(fundo)
    checar(len(curto) <= corpus.TETO_CAMINHO, "caminho longo respeita o teto de 400",
           str(len(curto)))
    checar(curto.startswith("RAIZ ") and "FOLHA " in curto and " > … > " in curto,
           "e o que sobra e raiz + … + folha", curto[:80])

    # CONTROLE: a regua com o cabecalho na frente etiqueta UM pedaco so. E a
    # medicao de 29 em 11.409 sendo reproduzida em miniatura.
    regua = picar_por_regua(DOC, documento_de_teste(), SUSEP, VIGENCIA)
    etiquetados = [p for p in regua if "Bradesco Seguros" in p]
    checar(len(etiquetados) <= 2,
           "CONTROLE — cabecalho concatenado ANTES de picar so marca o comeco",
           f"{len(etiquetados)} de {len(regua)} pedacos")

    fonte = _ARQUIVO.read_text(encoding="utf-8")
    codigo = [linha for linha in fonte.splitlines()
              if linha.strip().startswith("conteudo = cabecalho")]
    checar(not codigo,
           "CONTROLE — e a concatenacao nao voltou ao codigo",
           "era a linha que deixava 11.380 pedacos sem dono")


# ---------------------------------------------------------------------------
def bloco_6_a_pergunta_que_so_o_caminho_responde():
    print("\n[6] O limite da linha branca — a pergunta que so o caminho responde")

    pedacos = corpus.montar_pedacos(DOC, documento_de_teste(), SUSEP, VIGENCIA)
    limite = "Até 02 (duas) utilizações durante a vigência do seguro."
    candidatos = [p for p in pedacos if limite in p]
    checar(len(candidatos) == 3,
           "os tres limites identicos continuam no acervo, cada um no seu lugar",
           f"{len(candidatos)}")

    caminhos = [_caminho(p) for p in candidatos]
    checar(len({c for c in caminhos}) == 3,
           "e os tres tem caminhos DIFERENTES",
           "📊 sem isso, 27 frases iguais e uma resposta ao acaso")

    marrom = [c for c in caminhos if "CONSERTO LINHA MARROM" in c]
    checar(len(marrom) == 1,
           "o limite de 2 acionamentos de conserto esta sob CONSERTO LINHA MARROM",
           f"⚠️ e NAO sob linha branca: {marrom}")
    checar(not any("CONSERTO LINHA BRANCA" in c for c in caminhos),
           "⚠️ e nenhum caminho o atribui a linha branca",
           "responder 2 acionamentos para linha branca e responder errado")
    pet = [c for c in caminhos if "PET" in c.upper()]
    checar(len(pet) == 1, "e o da assistencia pet nao se confunde com nenhum dos dois",
           str(pet))

    # A televisao: a definicao de linha marrom e a secao que a contem.
    tv = [p for p in pedacos if "aparelhos de linha Marrom televisores" in p]
    checar(len(tv) == 1 and "MARROM" in _caminho(tv[0]).upper(),
           "e a televisao cai na secao de linha marrom",
           _caminho(tv[0]) if tv else "nenhum pedaco")

    # CONTROLE: pela regua, o mesmo limite fica indistinguivel.
    regua = picar_por_regua(DOC, documento_de_teste(), SUSEP, VIGENCIA)
    com_limite = [p for p in regua if limite in p]
    sabem_a_secao = [p for p in com_limite if "CONSERTO LINHA MARROM" in p]
    checar(len(sabem_a_secao) < len(com_limite),
           "CONTROLE — pela regua, pelo menos um deles nao sabe de que secao veio",
           f"{len(sabem_a_secao)} de {len(com_limite)} sabem")


# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 78)
    print("O pedaco do contrato sabe de onde veio — SPEC-067 LOTE 0, itens 1-3")
    print("=" * 78)
    bloco_1_o_extrator()
    bloco_2_a_limpeza()
    bloco_3_os_titulos()
    bloco_4_o_corte()
    bloco_5_o_cabecalho()
    bloco_6_a_pergunta_que_so_o_caminho_responde()

    print("\n" + "=" * 78)
    if _PROBLEMAS:
        print(f"REPROVADO — {len(_PROBLEMAS)} problema(s):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("APROVADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
