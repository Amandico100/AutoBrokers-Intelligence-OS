"""Corpus normativo de seguros. SPEC-057 §Bloco H.

O problema
----------
Condição geral de apólice é o **mesmo documento** para todas as corretoras e
todos os segurados. Lê-la a cada pergunta custa crédito por leitura, demora
dezenas de segundos e — o pior — pode devolver respostas diferentes para
corretoras diferentes conforme o dia em que o PDF foi lido. Documento normativo
tem de dar a mesma resposta para todo mundo.

A forma
-------
Lê-se **uma vez**, no nível da plataforma, e o conteúdo entra no conhecimento
global que já existe. A partir daí toda corretora consulta de graça, pela
`knowledge.global.search` que já está no Registry. Um agente reconfere
periodicamente e, quando o conteúdo muda, registra uma versão nova.

Isto não é um RAG paralelo. A coleção Qdrant global, o serviço de ingestão e a
busca já existiam; o que faltava era o **catálogo** — o que está lá dentro, de
onde veio, de que versão e até quando vale.

O detalhe que impede isto de virar passivo
------------------------------------------
Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não
pela de hoje. Um cache que guarda "a condição atual" e responde sobre uma
apólice antiga pode estar confiantemente errado sobre cobertura — e o corretor
repete isso para o cliente. Por isso toda resposta deste corpus carrega a
vigência junto, e o texto ingerido começa com ela.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

COLECAO_GLOBAL = "autobrokers_global"
MAX_TENTATIVAS = 4
INTERVALO_PADRAO_DIAS = 45

# Número de processo SUSEP: 5 dígitos . 6 dígitos / 4 dígitos - 2 dígitos.
# É a identidade legal do documento — duas versões da mesma norma compartilham
# o número, e é isso que permite encadear versões em vez de tratá-las como
# documentos diferentes.
_RE_SUSEP = re.compile(r"\b(\d{5}\.\d{6}/\d{4}-\d{2})\b")
_RE_PROCESSO_SOLTO = re.compile(
    r"processo\s+SUSEP\s*n?[º°.]?\s*([\d.\-/]{10,25})", re.I)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _hash(texto: str) -> str:
    # Normaliza espaço antes do hash: PDF re-renderizado muda quebra de linha
    # sem mudar uma vírgula do conteúdo, e isso geraria "mudou" toda semana.
    normalizado = re.sub(r"\s+", " ", texto or "").strip()
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def extrair_susep(texto: str) -> Optional[str]:
    m = _RE_SUSEP.search(texto or "")
    if m:
        return m.group(1)
    m = _RE_PROCESSO_SOLTO.search(texto or "")
    return m.group(1).strip() if m else None


def extrair_vigencia(texto: str) -> Optional[str]:
    """Procura uma data de vigência declarada no próprio documento."""
    padroes = [
        r"vig[êe]ncia\s+a\s+partir\s+de\s+(\d{2}/\d{2}/\d{4})",
        r"em\s+vigor\s+desde\s+(\d{2}/\d{2}/\d{4})",
        r"atualizad[ao]\s+em\s+(\d{2}/\d{2}/\d{4})",
    ]
    for p in padroes:
        m = re.search(p, texto or "", re.I)
        if m:
            try:
                d, mth, y = m.group(1).split("/")
                return f"{y}-{mth}-{d}"
            except Exception:  # noqa: BLE001
                continue
    return None


# ==========================================================================
# O MOTOR QUE PICA UMA CONDIÇÃO GERAL — SPEC-067 §4
# ==========================================================================
#
# O defeito que este bloco conserta, medido em 08/08/2026 sobre os PDFs reais
# do acervo:
#
#   📊 57% dos pedaços terminavam no meio de uma frase
#   📊 46% começavam no meio de uma frase
#   📊 69% não diziam de que seção do contrato saíram
#   📊 76% não diziam de que seguradora eram — 29 de 11.409 tinham etiqueta
#
# Eram quatro defeitos empilhados, e o de baixo era o extrator: o PyPDF2
# colapsa a página inteira numa linha só. Sem linha não existe título; sem
# título não existe seção; sem seção o corte só pode ser por contagem de
# caracteres — que é o que corta frase no meio.
#
# A ordem aqui não é estética. Cada passo depende do anterior:
#
#   páginas (fitz)  →  limpeza  →  tabelas  →  títulos  →  seções  →  pedaços
#
# E o cabeçalho é montado **depois** de picar, pedaço a pedaço. Concatenar
# antes e picar depois põe a etiqueta só no pedaço 0 — que é exatamente o que
# o código antigo fazia, e o motivo de 11.380 pedaços de contrato circularem
# sem dizer de quem eram.

ALVO_PEDACO = 1400
TETO_PEDACO = 2200
MINIMO_CORPO = 180
TETO_CAMINHO = 400

# Separador de página. `\f` é whitespace para o `re.sub(r"\s+")` do `_hash`,
# então marcar a página NÃO muda o hash de conteúdo — documento que não mudou
# na origem continua não mudando aqui.
MARCA_DE_PAGINA = "\f"

# Um número sozinho numa linha: `4.`, `4.2`, `4.2.1.`. Exige ponto — sem essa
# exigência o número de página (`68`) viraria "órfão" e grudaria no rodapé
# seguinte, e aí nem a mobília nem o número de página seriam mais reconhecíveis.
_SO_NUMERO = re.compile(r"^(\d{1,2}(?:\.\d{1,3})+\.?|\d{1,2}\.)$")
_SO_MARCADOR = re.compile(r"^(?:[•▪◦●·*»›-]|[–—]|\(?[a-zA-Z]{1,2}\)|\d{1,2}\))$")
_LINHA_DE_SUMARIO = re.compile(r"[.\-–—_·]{4,}\s*\d{1,4}$")
_PURO_NUMERO = re.compile(r"^\d{1,4}$")

_RE_MARKDOWN = re.compile(r"^(#{1,6})\s+(\S.*)$")
_RE_RAIZ = re.compile(
    r"^[►▶•\s]*(CL[ÁA]USULA|CAP[ÍI]TULO|SE[ÇC][ÃA]O|ANEXO|T[ÍI]TULO)\b[\s:.\-–—]*"
    r"([IVXLCDM]+|\d+)?\s*([A-Z])?", re.I)
_RE_NUMERADO = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){0,3})\.?\s+(\S.*)$")
# Peças que também são RAIZ, mas não trazem numeração. Só valem em caixa-alta e
# em linha curta: 📊 sem essa exigência, "condições gerais do seguro
# estabelecem…" no meio de um parágrafo abriria uma seção nova. Existem porque
# o CG140 volta a `CONDIÇÕES GERAIS` depois das cláusulas — e sem isto o
# caminho continuava dizendo "Cláusula 103" trinta páginas depois dela acabar.
_RE_RAIZ_SEM_NUMERO = re.compile(
    r"^(CONDI[ÇC][ÕO]ES\s+(GERAIS|ESPECIAIS)|DISPOSI[ÇC][ÕO]ES\s+GERAIS|GLOSS[ÁA]RIO)\b")
_INICIO_DE_BLOCO = re.compile(
    r"^(?:[•▪◦●·*]|[-–—]\s|\(?[a-zA-Z]{1,2}\)\s|\d{1,2}\)\s|\d{1,2}(?:\.\d{1,3})*\.\s)")
_NOTA_DE_RODAPE = re.compile(r"^(?:\(\s*\d+\s*\)|\(?\*+\)?|\*|Obs\b|Nota|Notas|Fonte)", re.I)
_FIM_DE_FRASE = (".", ";", ":", "!", "?", "”", '"', "»", ")")

# Nível 8 da §4.3: o título de faceta que a Circular SUSEP 621/2021 obriga.
# Só entra quando a linha é EXATAMENTE isso — não é busca de substring, senão
# metade das frases do contrato viraria título.
_TITULO_DE_FACETA = {
    "riscos cobertos", "riscos excluidos", "riscos excluídos", "exclusoes",
    "exclusões", "bens nao compreendidos", "bens não compreendidos",
    "limites de utilizacao", "limites de utilização", "limite de utilizacao",
    "limite de utilização", "franquia", "franquias", "carencia", "carência",
    "prazos", "prazo de comunicacao", "prazo de comunicação", "documentos",
    "documentacao", "documentação", "definicoes", "definições", "glossario",
    "glossário", "reintegracao", "reintegração", "objeto do seguro",
    "ambito geografico", "âmbito geográfico", "vigencia", "vigência",
}
_SECAO_DESCARTAVEL = {"sumario", "sumário", "indice", "índice",
                      "indice remissivo", "índice remissivo"}


def extrair_texto_de_pdf(corpo: bytes) -> tuple[Optional[str], Optional[str]]:
    """PDF → texto com as PÁGINAS marcadas. Devolve (texto, None) ou (None, erro).

    Página a página, em ordem, com `page.get_text("text")`. A marca de página
    não é enfeite: as duas regras de limpeza que mais sujeira tiram — mobília
    de rodapé e número de página — só funcionam se souberem onde a página
    começa e termina. Sem isso, "linha repetida 5 vezes" apagaria
    📊 as 27 ocorrências de "Até 2 (duas) utilizações durante a vigência" do
    Bradesco, que são 27 assistências diferentes e não são mobília nenhuma.
    """
    try:
        import fitz
    except Exception:  # noqa: BLE001 — sem o extrator, o crawler ainda existe
        return None, "sem_extrator_de_pdf"

    documento = None
    try:
        documento = fitz.open(stream=corpo, filetype="pdf")
        paginas = [pagina.get_text("text") for pagina in documento]
    except Exception as exc:  # noqa: BLE001
        return None, f"pdf_ilegivel:{type(exc).__name__}"
    finally:
        if documento is not None:
            try:
                documento.close()
            except Exception:  # noqa: BLE001
                pass
    return MARCA_DE_PAGINA.join(paginas), None


def _em_paginas(texto: str) -> list[list[str]]:
    """Texto → páginas → linhas, com espaço normalizado."""
    bruto = (texto or "").replace("\r\n", "\n").replace("\r", "\n")
    paginas = bruto.split(MARCA_DE_PAGINA)
    return [[re.sub(r"[ \t\xa0]+", " ", linha).strip() for linha in p.split("\n")]
            for p in paginas]


def _juntar_orfaos(linhas: list[str]) -> list[str]:
    """Passo 1 da §4.2: número (ou marcador) sozinho gruda na linha seguinte.

    📊 O Bradesco quebra assim: `4.2.` numa linha, `CONSERTO LINHA MARROM` na
    outra. Separados, o primeiro é um título sem nome e o segundo é um
    parágrafo em caixa-alta. Juntos, são a seção que distingue o limite da
    linha marrom do limite da linha branca — a diferença entre responder certo
    e responder uma das 27 frases idênticas do documento.
    """
    saida: list[str] = []
    i, total = 0, len(linhas)
    while i < total:
        atual = linhas[i].strip()
        e_numero = bool(_SO_NUMERO.match(atual))
        e_marcador = (not e_numero) and bool(_SO_MARCADOR.match(atual))
        if atual and (e_numero or e_marcador):
            j = i + 1
            while j < total and not linhas[j].strip() and j <= i + 2:
                j += 1
            if j < total and linhas[j].strip():
                proxima = linhas[j].strip()
                if e_marcador or len(proxima) <= 140:
                    saida.append(f"{atual} {proxima}")
                    i = j + 1
                    continue
        saida.append(linhas[i])
        i += 1
    return saida


def _faixa_de_mobilia(pagina: list[str], topo: int = 6, rodape: int = 6) -> set[int]:
    """As posições onde cabeçalho e rodapé moram: começo e fim da página.

    📊 Seis linhas no topo, e não três, porque o cabeçalho da Mapfre tem seis:
    título do produto, número de página, duas de endereço, site e
    "Classificação: Uso Interno". Com uma faixa de três, as três últimas
    sobravam e grudavam no meio da frase seguinte — o pedaço passava a começar
    com "São Paulo/SP • CEP 04794-000".
    """
    cheias = [i for i, linha in enumerate(pagina) if linha.strip()]
    return set(cheias[:topo]) | set(cheias[-rodape:])


def _remover_mobilia(paginas: list[list[str]], minimo: int = 5) -> list[list[str]]:
    """Passo 3 da §4.2: linha repetida em ≥5 páginas, na borda da página.

    ⚠️ Linha puramente numérica fica de fora — é o passo 4 que cuida dela.
    📊 Sem essa exceção, os valores `630` e `882` da tabela de carro reserva da
    Porto somem do documento, e a única resposta que existe sobre carro reserva
    sai do acervo junto.

    ⚠️ E "repetida" não basta: a linha tem de repetir **na borda**. 📊 "Até 2
    (duas) utilizações durante a vigência do seguro" aparece 27 vezes no
    e-Residencial do Bradesco, em 27 assistências diferentes. É conteúdo, e
    conteúdo mora no meio da página — por isso a maioria das ocorrências tem de
    estar na faixa para a linha ser considerada mobília.
    """
    faixas = [_faixa_de_mobilia(p) for p in paginas]
    contagem: dict[str, int] = {}
    total_geral: dict[str, int] = {}
    for pagina, faixa in zip(paginas, faixas):
        vistas = set()
        for i, linha in enumerate(pagina):
            texto = linha.strip()
            if not texto or _PURO_NUMERO.match(texto) or len(texto) > 160:
                continue
            total_geral[texto] = total_geral.get(texto, 0) + 1
            if i in faixa:
                vistas.add(texto)
        for texto in vistas:
            contagem[texto] = contagem.get(texto, 0) + 1
    mobilia = {t for t, c in contagem.items()
               if c >= minimo and c >= 0.6 * total_geral.get(t, c)}
    if not mobilia:
        return paginas
    return [[linha for i, linha in enumerate(pagina)
             if not (i in faixa and linha.strip() in mobilia)]
            for pagina, faixa in zip(paginas, faixas)]


def _remover_numero_de_pagina(paginas: list[list[str]],
                              minimo: int = 8) -> list[list[str]]:
    """Passo 4 da §4.2: número de página só sai quando ANDA DE 1 EM 1.

    O deslocamento (`valor - índice da página`) tem de ser o mesmo ao longo do
    arquivo. Um número solto numa tabela não forma progressão com nada, e por
    isso sobrevive.
    """
    faixas = [_faixa_de_mobilia(p) for p in paginas]
    votos: dict[int, int] = {}
    for k, (pagina, faixa) in enumerate(zip(paginas, faixas)):
        for i in faixa:
            texto = pagina[i].strip()
            if _PURO_NUMERO.match(texto):
                deslocamento = int(texto) - k
                votos[deslocamento] = votos.get(deslocamento, 0) + 1
    if not votos:
        return paginas
    deslocamento, quantos = max(votos.items(), key=lambda par: par[1])
    if quantos < minimo:
        return paginas
    saida = []
    for k, (pagina, faixa) in enumerate(zip(paginas, faixas)):
        fora = {i for i in faixa
                if _PURO_NUMERO.match(pagina[i].strip())
                and int(pagina[i].strip()) - k == deslocamento}
        saida.append([linha for i, linha in enumerate(pagina) if i not in fora])
    return saida


def _remover_sumario(paginas: list[list[str]], minimo: int = 8,
                     folga: int = 25) -> list[list[str]]:
    """Passo 2 da §4.2 — e a REGIÃO inteira do sumário, não só as linhas com pontinhos.

    📊 A `CLÁUSULA 76R` aparece 2× no CG140: uma no índice, outra no corpo.
    Indexar as duas põe uma linha de sumário competindo com a cláusula de
    verdade. Mas o índice também quebra linha: `CLÁUSULA 76 – DANOS A VIDROS E
    RETROVISORES, LANTERNAS E FARÓIS – REDE` vem SEM pontinhos, e a linha
    seguinte é que os tem.

    🔴 E essa sobra não era ruído inofensivo. O índice cita a `CLÁUSULA 109`
    antes de o contrato começar; a guarda de monotonicidade então recusava
    TODA cláusula de número menor pelo resto do arquivo, e 📊 os 607 pedaços do
    CG140 saíram com a mesma raiz falsa — "CLÁUSULA 109 – COBERTURA DA PELÍCULA
    PPF" — inclusive os do vidro e os do pneu. Um caminho errado mente com mais
    convicção do que caminho nenhum.

    Por isso a região: onde há ≥8 linhas de índice próximas umas das outras,
    tudo entre a primeira e a última é índice.
    """
    plano: list[tuple[int, int]] = []
    for p, pagina in enumerate(paginas):
        for i in range(len(pagina)):
            plano.append((p, i))
    marcas = [k for k, (p, i) in enumerate(plano)
              if _LINHA_DE_SUMARIO.search(paginas[p][i].strip())]

    apagar: set[tuple[int, int]] = set()
    grupo: list[int] = []
    for k in marcas + [None]:  # type: ignore[list-item]
        if grupo and (k is None or k - grupo[-1] > folga):
            if len(grupo) >= minimo:
                apagar.update(plano[grupo[0]:grupo[-1] + 1])
            grupo = []
        if k is not None:
            grupo.append(k)
    apagar.update(plano[k] for k in marcas)

    return [[linha for i, linha in enumerate(pagina) if (p, i) not in apagar]
            for p, pagina in enumerate(paginas)]


def limpar(texto: str) -> list[str]:
    """A §4.2 inteira, **nesta ordem exata**. Devolve as linhas limpas."""
    paginas = _em_paginas(texto)
    paginas = [_juntar_orfaos(p) for p in paginas]
    paginas = _remover_sumario(paginas)
    paginas = _remover_mobilia(paginas)
    paginas = _remover_numero_de_pagina(paginas)
    return [linha for pagina in paginas for linha in pagina]


def _e_caixa_alta(linha: str) -> bool:
    letras = [c for c in linha if c.isalpha()]
    return len(letras) >= 3 and not any(c.islower() for c in letras)


def _titulo_curto(texto: str) -> bool:
    """Título é rótulo, não frase. Frase que termina em ponto não é título."""
    limpo = texto.strip()
    return bool(limpo) and len(limpo) <= 110 and not limpo.endswith((".", ";", ","))


def detectar_titulos(linhas: list[str]) -> dict[int, tuple[int, str]]:
    """Os 8 níveis da §4.3, com as duas guardas que foram medidas.

    ⚠️ **Duas linhas de CAIXA-ALTA seguidas são parágrafo, não título.**
    📊 Sem essa guarda o aviso `IMPORTANTE: PARA APARELHOS COM FABRICAÇÃO
    SUPERIOR A 5 (CINCO) ANOS...` do Bradesco vira título e empurra
    `4.2. CONSERTO LINHA MARROM` para fora do caminho — que é justamente o que
    distingue o limite da linha marrom do da linha branca.

    ⚠️ **Número de cláusula tem de ser monotônico.** Candidato que retrocede é
    descartado. 📊 O Allianz escreve `Cláusula 9 – …` no meio de uma frase, e
    um detector ingênuo morde a isca e reabre a cláusula 9 dentro da 47.
    Ânexo/Capítulo zeram o contador, porque 📊 a numeração reinicia em cada
    anexo — existem dois `4.1.1` no mesmo arquivo.
    """
    cheias = [i for i, linha in enumerate(linhas) if linha.strip()]

    # Quem é caixa-alta "solta" — o que ainda não foi reclamado por um padrão
    # mais forte. É sobre este conjunto que a guarda das duas linhas roda.
    solta: set[int] = set()
    for i in cheias:
        linha = linhas[i].strip()
        if (_e_caixa_alta(linha) and len(linha) <= 160
                and not _RE_RAIZ.match(linha) and not _RE_NUMERADO.match(linha)
                and not _RE_MARKDOWN.match(linha)):
            solta.add(i)

    def _continua_embaixo(k: int) -> bool:
        """A linha seguinte começa em minúscula? Então a de cima não terminou.

        📊 A Mapfre numera PARÁGRAFO, não seção: `2.1. As coberturas contratadas
        são aquelas discriminadas na apólice de seguro, respeitadas as regras` /
        `estabelecidas nestas condições gerais…`. Sem esta guarda, o parágrafo
        inteiro virava título, o caminho ficava com 100 caracteres de contrato
        dentro e o corpo do pedaço começava em `estabelecidas` — 📊 70% dos
        pedaços da Mapfre começavam no meio da frase por causa disto.
        """
        if k + 1 >= len(cheias):
            return False
        proxima = linhas[cheias[k + 1]].strip()
        return bool(proxima) and proxima[:1].islower()

    titulos: dict[int, tuple[int, str]] = {}
    ultima_clausula = 0
    for k, i in enumerate(cheias):
        linha = linhas[i].strip()
        if len(linha) > 200:
            continue

        marca = _RE_MARKDOWN.match(linha)
        if marca:
            titulos[i] = (min(len(marca.group(1)), 8), marca.group(2).strip())
            continue

        raiz = _RE_RAIZ.match(linha)
        if raiz and _titulo_curto(linha):
            palavra = raiz.group(1).upper()
            if palavra.startswith("CL"):
                bruto = raiz.group(2) or ""
                if not bruto.isdigit():
                    continue  # "CLÁUSULA" sem número não abre seção
                numero = int(bruto)
                if numero < ultima_clausula:
                    continue  # a isca do meio da frase
                ultima_clausula = numero
            else:
                ultima_clausula = 0  # anexo reinicia a numeração
            titulos[i] = (1, linha)
            continue

        if (_RE_RAIZ_SEM_NUMERO.match(linha) and _e_caixa_alta(linha)
                and len(linha) <= 60 and not _continua_embaixo(k)):
            ultima_clausula = 0
            titulos[i] = (1, linha)
            continue

        numerado = _RE_NUMERADO.match(linha)
        if numerado and _titulo_curto(numerado.group(2)) and not _continua_embaixo(k):
            profundidade = len(numerado.group(1).split("."))
            titulos[i] = (min(3 + profundidade, 7), linha)
            continue

        if i in solta:
            anterior = cheias[k - 1] if k else None
            seguinte = cheias[k + 1] if k + 1 < len(cheias) else None
            if (anterior in solta) or (seguinte in solta):
                continue  # duas caixas-altas seguidas: é parágrafo
            if _continua_embaixo(k):
                continue
            nivel = 2 if re.match(r"^ASSIST[ÊE]NCIA\b", linha, re.I) else 3
            titulos[i] = (nivel, linha)
            continue

        chave = linha.strip(" .:–—-").lower()
        if chave in _TITULO_DE_FACETA and len(linha) <= 60 and not _continua_embaixo(k):
            titulos[i] = (8, linha)

    return _demover_listas(linhas, titulos)


def _demover_listas(linhas: list[str],
                    titulos: dict[int, tuple[int, str]]) -> dict[int, tuple[int, str]]:
    """Item de lista numerada não é seção — é corpo.

    📊 A Mapfre enumera as 32 coberturas adicionais uma por linha
    (`2.3.1. Acessórios…`, `2.3.2. Tacógrafo…`). Cada uma casa o padrão de
    título numerado, e cada uma abriria uma seção **sem corpo** — que a §4.3
    manda não indexar. A lista inteira sumiria do acervo.

    O sinal que distingue: título de verdade tem corpo embaixo. Título sem
    corpo nenhum, seguido de um irmão ou de alguém mais raso, é item de lista.
    Vira corpo da seção que o contém — `2.3. Coberturas Adicionais`.
    """
    fronteiras = sorted(titulos)
    for k, i in enumerate(fronteiras):
        nivel = titulos[i][0]
        if nivel < 4:
            continue  # raiz e caixa-alta são estrutura, não lista
        proxima = fronteiras[k + 1] if k + 1 < len(fronteiras) else len(linhas)
        if any(linhas[j].strip() for j in range(i + 1, proxima)):
            continue  # tem corpo: é seção de verdade
        if proxima < len(linhas) and titulos[proxima][0] <= nivel:
            titulos.pop(i)
    return titulos


def regioes_de_tabela(linhas: list[str], titulos: dict[int, tuple[int, str]],
                      minimo: int = 6) -> dict[int, int]:
    """§4.5 — a tabela é bloco ATÔMICO: não se detecta título nem se corta dentro.

    Uma região de tabela é uma corrida de linhas curtas, com pelo menos três
    bem curtas (célula, valor, código). Linha de título quebra a corrida — a
    grade começa depois do rótulo dela, não em cima dele.

    E as notas de rodapé vão junto. 📊 Sem `(1) Valores expressos em reais,
    considerando o Limite diário R$ 90,00`, o `630` da tabela de carro reserva
    é número sem unidade, e a resposta "quantos dias de carro reserva eu tenho"
    deixa de existir no documento.
    """
    regioes: dict[int, int] = {}
    total = len(linhas)
    i = 0
    while i < total:
        if not linhas[i].strip() or i in titulos:
            i += 1
            continue
        j, vazias_seguidas, corrida = i, 0, []
        while j < total and j not in titulos:
            texto = linhas[j].strip()
            if not texto:
                vazias_seguidas += 1
                if vazias_seguidas >= 2:
                    break
                j += 1
                continue
            if len(texto) > 60:
                break
            vazias_seguidas = 0
            corrida.append(texto)
            j += 1
        curtinhas = sum(1 for c in corrida if len(c) <= 12)
        if len(corrida) >= minimo and curtinhas >= 3:
            fim = j
            while fim > i and not linhas[fim - 1].strip():
                fim -= 1
            regioes[i] = _absorver_notas(linhas, fim, titulos)
            i = regioes[i]
        else:
            i = max(j, i + 1)
    return regioes


def _absorver_notas(linhas: list[str], fim: int,
                    titulos: dict[int, tuple[int, str]], teto: int = 8) -> int:
    """Estica a região da tabela até engolir `(1)`, `*`, `Obs.` e `Nota`."""
    total, absorvidas = len(linhas), 0
    i = fim
    while i < total and absorvidas < teto:
        while i < total and not linhas[i].strip():
            i += 1
        if i >= total or i in titulos or not _NOTA_DE_RODAPE.match(linhas[i].strip()):
            break
        # A nota inteira, incluindo as linhas em que ela continua.
        i += 1
        while (i < total and linhas[i].strip() and i not in titulos
               and not linhas[i - 1].strip().endswith(_FIM_DE_FRASE)
               and not _NOTA_DE_RODAPE.match(linhas[i].strip())):
            i += 1
        absorvidas += 1
        fim = i
    return fim


def _blocos(linhas: list[str], inicio: int, fim: int,
            regioes: dict[int, int]) -> list[str]:
    """Corpo de uma seção → blocos. **Bloco nunca é dividido.**

    Um bloco é um parágrafo, uma alínea, ou uma tabela inteira. O PDF quebra a
    linha onde a página acaba, não onde a frase acaba: por isso as linhas são
    remontadas até o fim de frase de verdade. É o que leva
    📊 "começa no meio da frase" de 46% para perto de zero.
    """
    blocos: list[str] = []
    i = inicio
    while i < fim:
        if i in regioes:
            corpo = [linha.strip() for linha in linhas[i:regioes[i]] if linha.strip()]
            if corpo:
                blocos.append("\n".join(corpo))
            i = regioes[i]
            continue
        linha = linhas[i].strip()
        if not linha:
            i += 1
            continue
        junto = [linha]
        i += 1
        while i < fim and i not in regioes:
            proxima = linhas[i].strip()
            if not proxima or _INICIO_DE_BLOCO.match(proxima):
                break
            if junto[-1].endswith(_FIM_DE_FRASE):
                break
            junto.append(proxima)
            i += 1
        blocos.append(" ".join(junto))
    return blocos


def _empacotar(blocos: list[str]) -> list[str]:
    """§4.3 — seção pequena vira um pedaço; seção grande vira blocos inteiros."""
    blocos = [b for b in blocos if b.strip()]
    if not blocos:
        return []
    inteiro = "\n\n".join(blocos)
    if len(inteiro) <= TETO_PEDACO:
        return [inteiro]

    pedacos: list[list[str]] = []
    atual: list[str] = []
    tamanho = 0
    for bloco in blocos:
        custo = len(bloco) + 2
        if atual and tamanho + custo > TETO_PEDACO:
            pedacos.append(atual)
            atual, tamanho = [], 0
        atual.append(bloco)
        tamanho += custo
        if tamanho >= ALVO_PEDACO:
            pedacos.append(atual)
            atual, tamanho = [], 0
    if atual:
        pedacos.append(atual)

    # Corpo curto demais não se sustenta sozinho: funde com o vizinho.
    juntos = ["\n\n".join(p) for p in pedacos]
    i = 1
    while i < len(juntos):
        if len(juntos[i]) < MINIMO_CORPO:
            juntos[i - 1] = juntos[i - 1] + "\n\n" + juntos[i]
            juntos.pop(i)
        else:
            i += 1
    if len(juntos) > 1 and len(juntos[0]) < MINIMO_CORPO:
        juntos[1] = juntos[0] + "\n\n" + juntos[1]
        juntos.pop(0)
    return juntos


def partir_documento(texto: str) -> list[dict]:
    """Texto de um documento normativo → pedaços com o CAMINHO de cada um.

    Devolve `[{"caminho": [...], "corpo": "..."}]`. Pedaço só-título nunca sai
    daqui: seção sem corpo não é conhecimento, é sumário com outro nome.
    """
    linhas = limpar(texto)
    if not linhas:
        return []
    titulos = detectar_titulos(linhas)
    regioes = regioes_de_tabela(linhas, titulos)
    # Título que caiu dentro de uma tabela não é título (§4.5).
    for inicio, fim in regioes.items():
        for i in range(inicio, fim):
            titulos.pop(i, None)

    fronteiras = sorted(titulos)
    caminho = [""] * 9
    saida: list[dict] = []

    def fechar(trilha: list[str], inicio: int, fim: int) -> None:
        folha = (trilha[-1] if trilha else "").strip(" .:–—-").lower()
        if folha in _SECAO_DESCARTAVEL:
            return
        for corpo in _empacotar(_blocos(linhas, inicio, fim, regioes)):
            saida.append({"caminho": list(trilha), "corpo": corpo})

    inicio_do_corpo = 0
    trilha_atual: list[str] = []
    for k, i in enumerate(fronteiras):
        fechar(trilha_atual, inicio_do_corpo, i)
        nivel, texto_do_titulo = titulos[i]
        caminho[nivel] = texto_do_titulo
        for mais_fundo in range(nivel + 1, 9):
            caminho[mais_fundo] = ""
        trilha_atual = [c for c in caminho[1:] if c]
        inicio_do_corpo = i + 1
    fechar(trilha_atual, inicio_do_corpo, len(linhas))
    return saida


def _caminho_em_texto(caminho: list[str], teto: int = TETO_CAMINHO) -> str:
    """§4.4 — o caminho, com teto. Estourou: raiz + … + folha."""
    partes = [re.sub(r"\s+", " ", p).strip() for p in caminho if p and p.strip()]
    if not partes:
        return ""
    inteiro = " > ".join(partes)
    if len(inteiro) <= teto:
        return inteiro
    if len(partes) <= 2:
        return inteiro[:teto].rstrip()
    return f"{partes[0]} > … > {partes[-1]}"[:teto].rstrip()


def _data_legivel(iso: Optional[str]) -> str:
    bruto = (iso or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", bruto)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return bruto or "não declarada"


def montar_etiqueta(doc: dict, susep: Optional[str],
                    vigencia: Optional[str]) -> str:
    """A primeira linha de TODO pedaço: de quem é, de que ramo, de quando.

    🔴 Montada **por pedaço**, depois de picar. Concatenar o cabeçalho antes e
    picar depois deixa a etiqueta só no pedaço 0 — 📊 29 de 11.409 pedaços a
    tinham, e os outros 11.380 eram frases sobre "a apólice" que qualquer
    agente atribuiria à seguradora errada com a confiança de um documento
    oficial.
    """
    partes = [str(doc.get("insurer_name") or doc.get("insurer_key") or "").strip()]
    if doc.get("product_line"):
        partes.append(str(doc["product_line"]))
    if doc.get("title"):
        partes.append(re.sub(r"\s+", " ", str(doc["title"])).strip())
    partes.append(f"vigência {_data_legivel(vigencia)}")
    if susep:
        partes.append(f"SUSEP {susep}")
    return "[" + " · ".join(p for p in partes if p) + "]"


def montar_pedacos(doc: dict, texto: str, susep: Optional[str],
                   vigencia: Optional[str]) -> list[str]:
    """O texto de um documento vira os pedaços que vão para o índice."""
    etiqueta = montar_etiqueta(doc, susep, vigencia)
    saida: list[str] = []
    for pedaco in partir_documento(texto):
        corpo = (pedaco["corpo"] or "").strip()
        if not corpo:
            continue
        caminho = _caminho_em_texto(pedaco["caminho"])
        saida.append(f"{etiqueta}\n{caminho}\n{corpo}" if caminho
                     else f"{etiqueta}\n{corpo}")
    return saida


# Seguradoras que operam no Brasil, por domínio e por nome. Serve para dizer
# de quem é o documento a partir da URL ou do texto.
SEGURADORAS = {
    "porto": ("Porto Seguro", ("portoseguro.com", "porto.com.br", "porto seguro")),
    "allianz": ("Allianz Seguros", ("allianz.com.br", "allianz")),
    "bradesco": ("Bradesco Seguros", ("bradescoseguros.com", "bradesco seguros")),
    "sulamerica": ("SulAmérica", ("sulamerica.com", "sulamérica", "sulamerica")),
    "tokio": ("Tokio Marine", ("tokiomarine.com", "tokio marine", "tokio_marine")),
    "hdi": ("HDI Seguros", ("hdiseguros.com", "hdi seguros")),
    "mapfre": ("Mapfre", ("mapfre.com", "mapfre")),
    # Liberty Seguros virou Yelum em 2024. Documento antigo continua valendo e
    # continua hospedado no dominio antigo — as duas pistas apontam para a
    # mesma seguradora, senao a condicao geral de ontem vira orfa.
    # O dominio real e yelumseguros.com.br — "yelum.com.br" e so a marca e nao
    # resolve. Descoberto ao verificar as URLs de verdade; supor o dominio pelo
    # nome teria recusado todo documento legitimo da seguradora.
    "yelum": ("Yelum Seguradora", ("yelumseguros.com.br", "yelum",
                                   "libertyseguros.com", "liberty seguros")),
    "zurich": ("Zurich", ("zurich.com", "zurich")),
    "azul": ("Azul Seguros", ("azulseguros.com", "azul seguros")),
    "itau": ("Itaú Seguros", ("itau.com.br/seguros", "itaú seguros")),
    "suhai": ("Suhai Seguradora", ("suhaiseguradora.com", "suhai")),
    "aliro": ("Aliro Seguros", ("aliro.com.br", "aliro")),
    "susep": ("SUSEP", ("susep.gov.br", "gov.br/susep")),
    "cnseg": ("CNseg", ("cnseg.org.br",)),
}

# O regulador NÃO é uma seguradora. Ele ocupa a coluna `insurer_key` porque a
# tabela só tem esse lugar para guardar a origem, mas 📊 os 5 documentos e 198
# chunks marcados assim — Resoluções CNSP 484/2025, 478/2024, 464/2024,
# 460/2023 e a Circular SUSEP 710/2024 — valem para TODAS as companhias.
#
# Quem filtra conhecimento por seguradora tem de tratar este valor como
# "sem seguradora", nunca como mais uma delas: etiquetá-lo esconderia a norma
# do regulador de toda pergunta sobre qualquer companhia.
_REGULADOR = "susep"

RAMOS = {
    "auto": ("seguro auto", "automóvel", "automovel", "veículo", "veiculo", "casco"),
    "frota": ("frota",),
    "residencial": ("residencial", "residência", "residencia"),
    "vida": ("seguro de vida", "vida em grupo", "prestamista"),
    "previdencia": ("previdência", "previdencia", "pgbl", "vgbl"),
    "saude": ("saúde", "saude", "odontológico", "odontologico"),
    "empresarial": ("empresarial", "patrimonial", "riscos nomeados", "compreensivo"),
    "condominio": ("condomínio", "condominio"),
    "viagem": ("viagem",),
    "responsabilidade_civil": ("responsabilidade civil", "d&o", "e&o"),
    "engenharia": ("riscos de engenharia", "obras civis"),
    "garantia": ("seguro garantia", "fiança locatícia", "fianca locaticia"),
    "transporte": ("transporte", "carga", "rctr", "rctr-c"),
    "agro": ("agrícola", "agricola", "rural", "penhor rural"),
}

TIPOS = {
    "condicoes_gerais": ("condições gerais", "condicoes gerais", "condições-gerais"),
    "condicoes_especiais": ("condições especiais", "condicoes especiais"),
    "manual_do_segurado": ("manual do segurado", "guia do segurado", "cartilha"),
    "circular_susep": ("circular susep", "circular nº", "resolução cnsp", "resolucao cnsp"),
    "nota_tecnica": ("nota técnica atuarial", "nota tecnica atuarial"),
    "tabela_coberturas": ("tabela de coberturas", "quadro de coberturas"),
}


def classificar(titulo: str, texto: str, url: str) -> Optional[dict]:
    """Decide se um documento é normativo e de quem ele é.

    Devolve `None` para tudo que não se reconhece. Ser conservador aqui é
    deliberado: um falso negativo custa uma leitura a mais; um falso positivo
    injeta ruído no conhecimento que todas as corretoras consultam.
    """
    alvo = f"{titulo} {url} {(texto or '')[:6000]}".lower()

    doc_kind = None
    for chave, pistas in TIPOS.items():
        if any(p in alvo for p in pistas):
            doc_kind = chave
            break
    # Sem número de processo SUSEP e sem título normativo, não é norma.
    if not doc_kind:
        if extrair_susep(texto or ""):
            doc_kind = "condicoes_gerais"
        else:
            return None

    insurer_key = insurer_name = None
    for chave, (nome, pistas) in SEGURADORAS.items():
        if any(p in alvo for p in pistas):
            insurer_key, insurer_name = chave, nome
            break
    if not insurer_key:
        return None

    ramo = "geral"
    for chave, pistas in RAMOS.items():
        if any(p in alvo for p in pistas):
            ramo = chave
            break

    return {
        "insurer_key": insurer_key, "insurer_name": insurer_name,
        "product_line": ramo, "doc_kind": doc_kind,
        "titulo_sugerido": f"{doc_kind.replace('_', ' ').title()} — {insurer_name} ({ramo})",
    }


def _ingerir_sync(doc: dict, conteudo: str, susep: Optional[str],
                  vigencia: Optional[str]) -> int:
    """Chunk → embeddings → Qdrant global. Espelha `global_knowledge_seed`.

    Roda em thread porque embedding e upsert são bloqueantes, e o worker que
    chama isto também atende trabalho do corretor.

    O corte é o da SPEC-067 §4: por SEÇÃO, com o cabeçalho montado pedaço a
    pedaço **depois** de picar. O que havia antes era um
    `RecursiveCharacterTextSplitter` de 1.000 caracteres sobre o texto colapsado
    do PyPDF2 — corte por régua, num texto sem linha. 📊 Resultado medido:
    57% dos pedaços terminavam no meio de uma frase e 76% não diziam de que
    seguradora eram.
    """
    import os

    from ...core.config import settings
    from ..knowledge_scope import GLOBAL_COLLECTION, SCOPE_GLOBAL_AUTOBROKERS
    from ..qdrant_service import get_qdrant_service

    chunks = montar_pedacos(doc, conteudo, susep, vigencia)
    if not chunks:
        return 0

    from langchain_openai import OpenAIEmbeddings

    dense = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY
    ).embed_documents(chunks)

    sparse = None
    try:
        from fastembed import SparseTextEmbedding

        sparse = list(SparseTextEmbedding(model_name="Qdrant/bm25").embed(chunks))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[corpus] sparse indisponivel (%s) — seguindo dense-only",
                       type(exc).__name__)

    qdrant = get_qdrant_service()
    # SPEC-067 item 7 — O ID DIZ DE QUE VERSÃO SÃO OS PONTOS.
    #
    # Ele deixa de ser calculado aqui e passa a vir de quem sabe a versão:
    # `ingerir()`, que consultou `normative_document_versions` ANTES de mandar
    # indexar. `norm-{id}` sem sufixo continua sendo o padrão de emergência
    # porque 📊 os 11.409 pontos de hoje têm exatamente esse formato.
    doc_id = doc.get("_qdrant_doc_id") or f"norm-{doc['id']}"
    anteriores = [d for d in (doc.get("_qdrant_doc_ids_anteriores") or [])
                  if d and d != doc_id]
    company = (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() or "autobrokers-global"

    ok = qdrant.insert_embeddings(
        company_id=company,
        document_id=doc_id,
        embeddings=dense,
        chunks=chunks,
        metadata={
            "document_name": doc["title"],
            "source": "normative_corpus",
            "chunk_type": "markdown",
            "insurer_key": doc["insurer_key"],
            "insurer_name": doc["insurer_name"],
            "product_line": doc["product_line"],
            "doc_kind": doc["doc_kind"],
            "susep_process": susep or "",
            "effective_from": vigencia or "",
            "source_url": doc["source_url"],
        },
        sparse_embeddings=sparse,
        collection_name=GLOBAL_COLLECTION,
        agent_id=None,
        knowledge_extras={
            "scope": SCOPE_GLOBAL_AUTOBROKERS,
            "curation_status": "published",
            "namespace": "normative",
            "version": (susep or doc["id"])[:12],
            # 🔴 A ETIQUETA TEM DE FICAR ONDE O FILTRO PROCURA — 07/08/2026.
            #
            # `insurer_key` também está em `metadata`, acima, e continua lá para
            # quem lê o chunk. Mas `insert_embeddings` promove à RAIZ do payload
            # apenas o que vem por `knowledge_extras` (`qdrant_service.py:250`),
            # e `_filtro_de_seguradora` casa `insurer_key` **na raiz**
            # (`qdrant_service.py:388`).
            #
            # O filtro tem um braço `IsEmptyCondition`: chave ausente na raiz
            # significa "fato genérico de mercado", e passa em qualquer
            # pergunta. Então 📊 11.211 chunks de condições gerais — Porto
            # 3.089, Bradesco 2.632, Allianz 1.694, Mapfre 1.430, Tokio 1.299,
            # Azul 1.067 — atravessavam como genéricos.
            #
            # E são o pior material possível para escapar: uma carta genérica é
            # fato de mercado; uma condição geral é o CONTRATO de uma companhia.
            # A pergunta "a Porto cobre alagamento?" recebia de volta a cláusula
            # da Allianz, com a confiança de um documento oficial.
            #
            # 📊 O filtro cobria 2.340 de ~23.472 pontos do índice (10,0%).
            #
            # ⚠️ E `susep` NÃO é uma seguradora. 📊 São 5 documentos e 198
            # chunks — Resoluções CNSP 484/2025, 478/2024, 464/2024, 460/2023 e
            # a Circular SUSEP 710/2024 — e uma norma do regulador vale para
            # TODAS as companhias. Etiquetá-la como se fosse uma delas a
            # esconderia de toda pergunta sobre qualquer outra: seria trocar um
            # vazamento por um apagão, e o apagão é pior porque é silencioso.
            # Ela fica sem etiqueta, que é o que "genérico" quer dizer aqui.
            **({"insurer_key": doc["insurer_key"]}
               if doc.get("insurer_key") and doc["insurer_key"] != _REGULADOR else {}),
            **({"product_line": doc["product_line"]} if doc.get("product_line") else {}),
        },
    )
    if not ok:
        return 0

    # 🔴 EXPAND, DEPOIS CONTRACT — SPEC-067 item 7.
    #
    # A remoção da versão anterior acontece AGORA, depois de a nova estar no
    # índice. Até 08/08/2026 era o contrário: `delete_document` rodava ANTES do
    # upsert, sobre o MESMO id, porque todas as versões dividiam `norm-{id}`.
    #
    # O que isso custava, e não era só a D-Acervo-02:
    #
    #   · existia uma janela em que o documento tinha ZERO pontos. Se a
    #     ingestão morresse no meio — e 📊 vinte e três documentos morreram no
    #     meio em 05/08 — o documento sumia da busca enquanto
    #     `normative_documents.status` continuava dizendo `ingested`.
    #   · o defeito era SILENCIOSO. Nada distingue "não achei porque não está
    #     no contrato" de "não achei porque o índice está vazio".
    #
    # Nesta ordem o pior caso vira "duas versões na busca por um ciclo" —
    # visível, contável, e a versão certa continua lá.
    for antigo in anteriores:
        try:
            qdrant.delete_document(company, antigo, collection_name=GLOBAL_COLLECTION)
            logger.info("[corpus] versao anterior retirada do indice: %s", antigo)
        except Exception as exc:  # noqa: BLE001
            # O tipo E a mensagem. Um `except` que engole o motivo foi o que
            # transformou um erro de digitação em oito dias de silêncio.
            logger.warning("[corpus] a versao anterior %s NAO saiu do indice "
                           "(%s: %s) — a busca pode devolver as duas ate a "
                           "proxima rodada", antigo, type(exc).__name__, exc)
    return len(chunks)


class InsuranceCorpusService:
    """Catálogo e ingestão do corpus normativo — nível plataforma."""

    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self._raw = supabase_client

    # ------------------------------------------------------------------
    # Consulta — o caminho que o agente usa
    # ------------------------------------------------------------------

    def ja_temos(self, url: str) -> Optional[dict]:
        """O documento desta URL já está no corpus e ingerido?"""
        r = (self.db.table("normative_documents")
             .select("id, title, insurer_name, product_line, doc_kind, susep_process, "
                     "version_label, effective_from, effective_until, status, "
                     "chunk_count, last_checked_at")
             .eq("source_url", url).maybe_single().execute()).data
        return r if r and r.get("status") == "ingested" else None

    def catalogo(self, *, insurer_key: Optional[str] = None,
                 product_line: Optional[str] = None, limite: int = 200) -> list[dict]:
        q = (self.db.table("normative_documents")
             .select("id, insurer_key, insurer_name, product_line, doc_kind, title, "
                     "susep_process, version_label, effective_from, status, "
                     "chunk_count, last_checked_at, next_check_at")
             .eq("status", "ingested"))
        if insurer_key:
            q = q.eq("insurer_key", insurer_key)
        if product_line:
            q = q.eq("product_line", product_line)
        return (q.order("insurer_name").limit(limite).execute()).data or []

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def registrar(self, *, insurer_key: str, insurer_name: str, product_line: str,
                  doc_kind: str, title: str, source_url: str,
                  susep_process: Optional[str] = None,
                  version_label: Optional[str] = None,
                  effective_from: Optional[str] = None,
                  check_interval_days: int = INTERVALO_PADRAO_DIAS,
                  notes: Optional[str] = None) -> dict:
        """Cadastra um documento como candidato. Não busca nada ainda."""
        registro = {
            "insurer_key": insurer_key, "insurer_name": insurer_name,
            "product_line": product_line, "doc_kind": doc_kind,
            "title": title, "source_url": source_url,
            "susep_process": susep_process, "version_label": version_label,
            "effective_from": effective_from,
            "check_interval_days": max(1, min(check_interval_days, 365)),
            "notes": notes, "status": "discovered",
            "next_check_at": _agora().isoformat(),
        }
        r = (self.db.table("normative_documents")
             .upsert(registro, on_conflict="source_url").execute()).data
        return (r or [{}])[0]

    def propor_candidato(self, *, url: str, titulo: str, texto: str) -> Optional[dict]:
        """Registra um documento lido ao vivo como candidato ao corpus.

        Filtra antes de propor. Sem filtro, todo PDF que qualquer agente abrisse
        entraria na fila de curadoria e o corpus normativo viraria lixeira —
        e um corpus poluído é pior que um corpus pequeno, porque a busca passa
        a devolver ruído com a mesma confiança que devolve norma.

        Nunca ingere sozinho: entra como `discovered`, esperando curadoria.
        Documento normativo alimenta o cérebro de TODAS as corretoras; isso não
        se decide por acaso de navegação.
        """
        classificacao = classificar(titulo, texto, url)
        if not classificacao:
            return None

        ja = (self.db.table("normative_documents").select("id, status")
              .eq("source_url", url).maybe_single().execute()).data
        if ja:
            return ja

        registro = {
            "insurer_key": classificacao["insurer_key"],
            "insurer_name": classificacao["insurer_name"],
            "product_line": classificacao["product_line"],
            "doc_kind": classificacao["doc_kind"],
            "title": (titulo or classificacao["titulo_sugerido"])[:300],
            "source_url": url,
            "susep_process": extrair_susep(texto),
            "effective_from": extrair_vigencia(texto),
            "status": "discovered",
            "next_check_at": _agora().isoformat(),
            "notes": "descoberto por leitura ao vivo — aguardando curadoria",
        }
        try:
            r = (self.db.table("normative_documents")
                 .upsert(registro, on_conflict="source_url").execute()).data
            logger.info("[corpus] candidato registrado: %s (%s)",
                        registro["title"][:60], classificacao["insurer_name"])
            return (r or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[corpus] candidato nao registrado: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------
    # Ingestão
    # ------------------------------------------------------------------

    async def ingerir(self, documento_id: str, *,
                      company_id_custeio: Optional[str] = None,
                      vigencia_susep: Optional[dict] = None) -> dict:
        """Busca o documento, compara com a última versão e ingere se mudou.

        `company_id_custeio` só existe porque `usage_events` exige um tenant.
        O evento sai marcado como `platform_corpus`: é custo da plataforma, não
        da corretora que porventura disparou. Cobrar de uma corretora a leitura
        de um documento que serve a todas seria cobrar a primeira a chegar.

        `vigencia_susep` é a vigência **já lida do registro oficial** — o que a
        SPEC-067 §3.2 chama de "a regra sem inferência". Chaves, todas ISO ou
        None::

            effective_from    Data de Início de Comercialização
            effective_until   Data de Fim (vazia = ainda comercializado)
            version_label     o nome do arquivo na tabela de Versões
            susep_version_id  o id de download
            fim_da_anterior   a Data de Fim publicada para a versão que esta
                              substitui — e SÓ ela fecha `effective_until` da
                              anterior

        Ausente, a vigência cai para o que o próprio documento declara, e se
        nem isso houver, para `indeterminado`. **Nunca para um palpite.**
        """
        doc = (self.db.table("normative_documents").select("*")
               .eq("id", documento_id).maybe_single().execute()).data
        if not doc:
            return {"ok": False, "motivo": "documento_inexistente"}

        # Zera o carregador de bytes ANTES de ir à rede. Sem isto, um documento
        # cujo download falhasse herdaria o PDF do documento anterior desta
        # mesma instância — e o acervo guardaria o arquivo errado sob o nome
        # certo, que é a pior forma de estar errado.
        self._pdf_baixado = None

        self.db.table("normative_documents").update({
            "status": "fetching", "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()

        texto, erro = await self._buscar(doc["source_url"], company_id_custeio)

        # HTTP 402 = credito do provedor esgotado. Nao e defeito do documento e
        # nao pode gastar tentativa: marcar como `unreachable` faria o corpus
        # desistir de documentos perfeitamente validos por causa da fatura, e
        # ninguem descobriria o motivo real depois.
        if erro == "HTTP 402":
            # `.isoformat()` NAS TRES. E a ausencia dele em duas foi o que
            # encalhou o corpus por oito dias.
            #
            # 📊 Autopsia de 05/08/2026. Este tratador nasceu em `d20868c`
            # (25/07 21:25 -03) para impedir exatamente o encalhe que ele
            # passou a causar. Os 23 documentos travaram 1h37 depois.
            #
            # A cadeia: `ingerir()` marca `fetching` ANTES de ir a rede (l. 389).
            # O 402 chega. Este UPDATE monta o dicionario com dois `datetime`
            # CRUS ao lado de um `.isoformat()`. O httpx serializa o corpo com
            # `json.dumps(..., allow_nan=False)` e SEM `default=` — entao
            # estoura `TypeError: Object of type datetime is not JSON
            # serializable`. A excecao sobe, escapa de `ingerir()`, escapa de
            # `reconferir_pendentes()` e morre num `logger.warning` que imprime
            # so o NOME da excecao. O status fica `fetching` — e `vencidos()`
            # (l. 654) procura em ('ingested','discovered','unreachable').
            # `fetching` nao esta la. Invisivel para sempre.
            #
            # 📊 As outras ONZE gravacoes de data neste arquivo usam
            # `.isoformat()`. Eram estas duas, e so estas duas.
            #
            # A licao que fica: **o tratador de erro tambem e codigo, e ele roda
            # justamente quando ninguem esta olhando.** Um `except` que engole o
            # tipo da excecao sem a mensagem transforma um erro de digitacao em
            # oito dias de silencio.
            self.db.table("normative_documents").update({
                "status": doc.get("status") or "discovered",
                "fetch_error": "credito do Firecrawl esgotado — aguardando plano",
                "last_checked_at": _agora().isoformat(),
                "next_check_at": (_agora() + timedelta(hours=6)).isoformat(),
                "updated_at": _agora().isoformat(),
            }).eq("id", documento_id).execute()
            logger.warning(
                "[corpus] CREDITO DO FIRECRAWL ESGOTADO (HTTP 402). %d documento(s) "
                "aprovado(s) continuam na fila e serao retomados quando houver credito.",
                len(self.vencidos(limite=50)))
            return {"ok": False, "motivo": "credito_esgotado", "bloqueante": True}

        if not texto:
            tentativas = int(doc.get("fetch_attempts") or 0) + 1
            # Backoff: documento fora do ar não pode ser tentado todo ciclo.
            atraso = min(2 ** tentativas, 30)
            self.db.table("normative_documents").update({
                "status": "unreachable" if tentativas >= MAX_TENTATIVAS else "discovered",
                "fetch_error": erro, "fetch_attempts": tentativas,
                "last_checked_at": _agora().isoformat(),
                "next_check_at": (_agora() + timedelta(days=atraso)).isoformat(),
                "updated_at": _agora().isoformat(),
            }).eq("id", documento_id).execute()
            return {"ok": False, "motivo": erro, "tentativas": tentativas}

        novo_hash = _hash(texto)
        if doc.get("content_hash") == novo_hash and doc.get("status") == "ingested":
            self._marcar_conferido(documento_id, doc, mudou=False)
            # `chunks: 0` de proposito: nada foi ingerido agora. Devolver a
            # contagem antiga faria o resumo contar de novo o que ja estava la.
            return {"ok": True, "mudou": False, "primeira": False, "chunks": 0}

        susep = doc.get("susep_process") or extrair_susep(texto)
        vig = self._vigencia_da_versao(doc, texto, vigencia_susep)
        vigencia = vig["effective_from"]

        # A VERSÃO É DECIDIDA ANTES DE INDEXAR — SPEC-067 item 7.
        #
        # Até 08/08/2026 esta consulta vinha DEPOIS da ingestão, e por isso o
        # número da versão não podia entrar no id dos pontos. Subi-la é o que
        # torna possível `norm-{id}-v{n}`: quem grava no índice precisa saber
        # qual versão está gravando, e isso é um fato do banco, não do Qdrant.
        anteriores = (self.db.table("normative_document_versions")
                      .select("id, version, qdrant_doc_id, superseded_at")
                      .eq("document_id", documento_id)
                      .order("version", desc=True).execute()).data or []
        n = int((anteriores[0].get("version") if anteriores else 0) or 0) + 1
        primeira = n == 1
        doc_id_novo = f"norm-{documento_id}-v{n}"

        # `norm-{id}` sem sufixo é o esquema legado, e é o id REAL dos 11.409
        # pontos de hoje — não um palpite: é o que `_ingerir_sync` calculava.
        # Linha antiga sem `qdrant_doc_id` (o backfill da migration 02 não
        # rodou ainda) cai nele, e a transição funciona nas duas ordens.
        doc = dict(doc)
        doc["_qdrant_doc_id"] = doc_id_novo
        doc["_qdrant_doc_ids_anteriores"] = [
            (a.get("qdrant_doc_id") or f"norm-{documento_id}") for a in anteriores]

        chunks = await self._ingerir_no_global(doc, texto, susep, vigencia)
        if chunks <= 0:
            self.db.table("normative_documents").update({
                "fetch_error": "ingestao devolveu zero chunks",
                "last_checked_at": _agora().isoformat(),
                "updated_at": _agora().isoformat(),
            }).eq("id", documento_id).execute()
            return {"ok": False, "motivo": "ingestao_vazia"}

        arquivo = await self._guardar_a_fonte(documento_id, n, texto)

        # 🔴 FECHAR A ANTERIOR VEM ANTES DE ABRIR A NOVA.
        #
        # A ordem não é estética: `normative_versao_aberta_uk` (migration 01) é
        # um índice único parcial sobre `document_id where superseded_at is
        # null`. Inserir primeiro estouraria a constraint. E é essa constraint
        # que transforma "quem fecha a anterior" de intenção em obrigação —
        # 📊 o encadeamento existia em código desde 25/07 e `superseded_at`
        # está preenchido em ZERO de 29, porque nada obrigava.
        #
        # ⚠️ `superseded_at` e `effective_until` NÃO são a mesma data.
        #   superseded_at   = fato NOSSO: capturamos uma versão mais nova.
        #   effective_until = fato da SUSEP: a comercialização terminou em X.
        # Um produto some da lista do REP2 sem que exista Data de Fim
        # publicada. Escrever `effective_until = ontem` nesse caso seria
        # publicar como registro oficial um número que inventamos — a escada de
        # inferência que a SPEC-067 §3.2 proíbe. Sem a data deles, fecha-se só
        # o nosso lado.
        if not primeira:
            fechamento: dict[str, Any] = {"superseded_at": _agora().isoformat()}
            if vig.get("fim_da_anterior"):
                fechamento["effective_until"] = vig["fim_da_anterior"]
                fechamento["vigencia_fonte"] = "susep_rep2"
            self.db.table("normative_document_versions").update(fechamento) \
                .eq("document_id", documento_id).lt("version", n) \
                .is_("superseded_at", "null").execute()

        self.db.table("normative_document_versions").insert({
            "document_id": documento_id, "version": n, "content_hash": novo_hash,
            "byte_size": len(texto.encode("utf-8")), "chunk_count": chunks,
            "excerpt": texto[:1500],
            "change_summary": ("primeira captura" if primeira
                               else "conteúdo alterado na origem"),
            # onde os pedaços desta versão moram (item 7)
            "qdrant_doc_id": doc_id_novo, "qdrant_collection": COLECAO_GLOBAL,
            # a vigência, na versão, que é onde ela é verdade (item 6)
            "effective_from": vig["effective_from"],
            "effective_until": vig["effective_until"],
            "version_label": vig["version_label"],
            "susep_version_id": vig["susep_version_id"],
            "vigencia_fonte": vig["fonte"],
            # onde o original e o texto moram (item 4)
            **{k: v for k, v in arquivo.items() if k != "erros"},
        }).execute()

        self.db.table("normative_documents").update({
            "status": "ingested", "content_hash": novo_hash,
            "byte_size": len(texto.encode("utf-8")), "chunk_count": chunks,
            "qdrant_collection": COLECAO_GLOBAL,
            "susep_process": susep,
            # ESPELHO da versão vigente — a verdade está na linha da versão.
            # 📊 `effective_until` e `version_label` estavam NULL em 35 de 35
            # porque ninguém escrevia aqui. Agora escreve um só lugar, e ele é
            # o mesmo que escreveu a versão.
            "effective_from": vig["effective_from"],
            "effective_until": vig["effective_until"],
            "version_label": vig["version_label"],
            "fetch_error": None, "fetch_attempts": 0,
            "last_checked_at": _agora().isoformat(),
            "last_change_at": _agora().isoformat(),
            "next_check_at": (_agora() + timedelta(
                days=int(doc.get("check_interval_days") or INTERVALO_PADRAO_DIAS))).isoformat(),
            "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()

        logger.info("[corpus] '%s' v%s ingerido — %s chunks%s · vigencia %s (%s)"
                    " · original %s",
                    doc["title"][:60], n, chunks,
                    "" if primeira else " (MUDOU na origem)",
                    vig["effective_from"] or "indeterminada", vig["fonte"],
                    "guardado" if arquivo.get("storage_ref") else "NAO guardado")
        return {"ok": True, "mudou": not primeira, "primeira": primeira,
                "versao": n, "chunks": chunks, "susep": susep, "vigencia": vigencia,
                "qdrant_doc_id": doc_id_novo,
                "vigencia_fonte": vig["fonte"],
                "arquivado": bool(arquivo.get("arquivado_em")),
                "arquivo_erros": arquivo.get("erros") or {}}

    # ------------------------------------------------------------------
    # Vigência e arquivo — os dois escritores que faltavam
    # ------------------------------------------------------------------

    @staticmethod
    def _vigencia_da_versao(doc: dict, texto: str,
                            susep: Optional[dict]) -> dict:
        """De onde saem as datas desta versão, e com que confiança.

        Três degraus, e **nenhum deles infere uma data que não foi publicada**:

        1. `susep_rep2` — Data de Início e Data de Fim da tabela de Versões do
           REP2 (SPEC-067 §3.2). É registro legal, e ganha de tudo.
        2. `texto_do_documento` — a data que o próprio PDF declara
           (`extrair_vigencia`). Menos confiável: é o que a seguradora escreveu
           na capa, e 📊 22 de 35 documentos têm só isso.
        3. `indeterminado` — não sabemos. Que é o que a §3.3 manda registrar
           quando a consulta volta vazia, e **nunca** "não mudou".

        ⚠️ O terceiro degrau não é um degrau de inferência: ele não produz
        data nenhuma. A diferença entre "não sei" e "deve ser X" é a diferença
        entre um acervo e um chute com carimbo.

        `susep` é o dicionário pronto que o parser do REP2 entrega:
        `{effective_from, effective_until, version_label, susep_version_id,
        fim_da_anterior}` — todos ISO ou None. Ele é montado a partir de
        `susep_rep2.Versao` (`inicio_iso`, `fim`, `arquivo`, `download_id`), e
        montá-lo é trabalho de quem consulta, não deste módulo: aqui a data já
        chega pronta.
        """
        susep = susep or {}
        if susep.get("effective_from") or susep.get("effective_until"):
            return {
                "effective_from": susep.get("effective_from"),
                "effective_until": susep.get("effective_until"),
                "version_label": susep.get("version_label"),
                "susep_version_id": susep.get("susep_version_id"),
                "fim_da_anterior": susep.get("fim_da_anterior"),
                "fonte": "susep_rep2",
            }

        do_texto = doc.get("effective_from") or extrair_vigencia(texto)
        return {
            "effective_from": do_texto,
            # 🔴 NUNCA preenchido fora da SUSEP. Uma data de fim inventada
            # tiraria da busca um documento que ainda vale.
            "effective_until": None,
            "version_label": doc.get("version_label"),
            "susep_version_id": None,
            "fim_da_anterior": None,
            "fonte": "texto_do_documento" if do_texto else "indeterminado",
        }

    async def _guardar_a_fonte(self, documento_id: str, versao: int,
                               texto: str) -> dict:
        """Põe o original e o texto no MinIO. Nunca derruba a ingestão.

        📊 `storage_ref` estava preenchido em 0 de 29 e o texto-fonte do acervo
        vivia só dentro do Qdrant, picado — o que inverte o CLAUDE.md §6.

        Arquivar é guarda, não entrega: se o MinIO estiver fora, o documento
        ainda tem de ser indexado. Mas a falha fica visível — `arquivado_em`
        continua NULL, o motivo vai no log e no dicionário devolvido, e
        `normative_versao_sem_arquivo_idx` continua listando esta versão.
        """
        import asyncio

        from .acervo_arquivo import guardar_versao

        # Os bytes que `_baixar_pdf_direto` capturou nesta rodada. Ausentes
        # quando a origem não é PDF (crawler devolve markdown) — e aí só o
        # texto é guardado, o que é diferente de falhar.
        bruto = getattr(self, "_pdf_baixado", None) or {}
        try:
            return await asyncio.to_thread(
                guardar_versao, documento_id, versao,
                texto=texto,
                pdf_bytes=bruto.get("bytes"),
                media_type=bruto.get("media_type"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[corpus] arquivamento falhou para %s v%s: %s: %s",
                           documento_id, versao, type(exc).__name__, exc)
            return {"storage_ref": None, "text_storage_ref": None,
                    "source_bytes": None, "source_media_type": None,
                    "arquivado_em": None,
                    "erros": {"arquivar": f"{type(exc).__name__}: {exc}"}}

    async def _baixar_pdf_direto(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """PDF público é ARQUIVO. Baixar arquivo não precisa de crawler.

        📊 Medido em 05/08/2026: os 10 documentos parados no corpus — HDI, Tokio,
        Azul e dois do Bradesco — têm TODOS uma URL de PDF direta. Estavam
        esperando crédito do Firecrawl para uma tarefa que um GET resolve. O
        crédito faz falta para DESCOBRIR documento novo; para baixar o que já
        foi descoberto, não.

        Devolve (texto, None) no sucesso e (None, motivo) na falha — nunca
        levanta. Quem chama já sabe cair no crawler quando isto não serve.
        """
        import httpx

        # Cabeçalho de navegador: 📊 dois destes documentos já falharam com 408 e
        # 500. Servidor de seguradora costuma recusar cliente sem User-Agent, e
        # essa recusa é indistinguível de "o arquivo não existe" para quem só lê
        # o código de status.
        cabecalhos = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
            "Accept": "application/pdf,*/*",
        }
        try:
            async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as cli:
                r = await cli.get(url, headers=cabecalhos)
            if r.status_code != 200:
                return None, f"HTTP {r.status_code}"
            corpo = r.content or b""
            # 🔴 SPEC-067 item 4 — A ÚNICA LINHA QUE SALVA O ORIGINAL.
            #
            # Até aqui os bytes morriam nesta função: 📊 `storage_ref` NULL em
            # 29 de 29, e o texto-fonte do acervo passou a existir só dentro do
            # Qdrant, picado. `_guardar_a_fonte()` lê daqui e põe no MinIO.
            #
            # ⚠️ Se você está reescrevendo esta função (item 1, PyPDF2 →
            # PyMuPDF): LEVE ESTA LINHA JUNTO. Sem ela o arquivamento degrada
            # em silêncio — o texto continua sendo guardado e o PDF não, e a
            # URL da HDI já devolve 500. `test_o_acervo_guarda_a_fonte_e_a_
            # versao.py` confere que ela existe.
            self._pdf_baixado = {"bytes": corpo, "media_type": "application/pdf"}
        except Exception as exc:  # noqa: BLE001
            return None, type(exc).__name__

        # Teto de tamanho: condição geral gorda tem ~5 MB. Acima de 60 MB é outra
        # coisa (portal inteiro, vídeo, erro), e ler isso na memória do worker
        # derruba o processo por um documento que provavelmente nem serve.
        if len(corpo) > 60 * 1024 * 1024:
            return None, "arquivo_grande_demais"
        if not corpo.startswith(b"%PDF"):
            # Não é PDF de verdade: pode ser uma página de erro com extensão
            # .pdf na URL. Devolver isso ao crawler é o certo — ele renderiza.
            return None, "nao_e_pdf"

        # PyMuPDF, nunca PyPDF2 — §4.1 da SPEC-067. Não é preferência de
        # biblioteca: é a diferença entre ter e não ter estrutura de página.
        # 📊 No mesmo CG140, PyPDF2 devolve 519 linhas e PyMuPDF 11.064; e uma
        # auditoria anterior concluiu, com esse texto colapsado na mão, que
        # "cortar por seção é impossível". Era o extrator, não o documento.
        texto, erro = extrair_texto_de_pdf(corpo)
        if erro:
            return None, erro

        # A MESMA régua do crawler, e ela existe pelo mesmo motivo: PDF escaneado
        # extrai quase nada, e ingerir isso põe no corpus um documento que
        # PARECE presente e não responde nada. Conta sem a marca de página:
        # um PDF de 40 páginas em branco tem 40 marcas e nenhum conteúdo.
        if len((texto or "").replace(MARCA_DE_PAGINA, "").strip()) < 400:
            return None, "conteudo_insuficiente"
        return texto, None

    async def _buscar(self, url: str, company_id: Optional[str]
                      ) -> tuple[Optional[str], Optional[str]]:
        # PDF DIRETO PRIMEIRO, e o crawler como segunda opção.
        #
        # A ordem não é preferência: é o que destrava 10 documentos sem gastar
        # um centavo. Se o GET não servir (página HTML, arquivo protegido,
        # escaneado), cai no crawler exatamente como antes — nada foi tirado.
        if ".pdf" in str(url or "").lower():
            texto, motivo = await self._baixar_pdf_direto(url)
            if texto:
                logger.info("[corpus] PDF baixado direto (sem crawler): %s", str(url)[:80])
                return texto, None
            logger.info("[corpus] GET direto nao serviu (%s) — tentando o crawler", motivo)

        from ..research.firecrawl import FirecrawlClient, configurado

        if not configurado():
            return None, "firecrawl_nao_configurado"
        cli = FirecrawlClient(self._raw, company_id=company_id)
        try:
            r = await cli.scrape(url, timeout_ms=90_000, skill="platform.corpus")
        except Exception as exc:  # noqa: BLE001
            return None, type(exc).__name__
        if not r.ok or not isinstance(r.dados, dict):
            return None, r.erro or "falha"
        texto = (r.dados.get("markdown") or "").strip()
        if len(texto) < 400:
            # PDF que devolve quase nada normalmente é imagem escaneada. Ingerir
            # isso poluiria o corpus com um documento vazio que parece presente.
            return None, "conteudo_insuficiente"
        return texto, None

    async def _ingerir_no_global(self, doc: dict, texto: str,
                                 susep: Optional[str], vigencia: Optional[str]) -> int:
        """Entrega ao serviço de ingestão que já existe. Nada novo aqui.

        🔴 **O cabeçalho de procedência NÃO é concatenado aqui.** Ele é montado
        por `montar_pedacos`, pedaço a pedaço, DEPOIS do corte.

        O que existia neste lugar era `conteudo = cabecalho + texto`: um bloco
        de identificação grudado na frente do documento inteiro, e o splitter
        picando o resultado. 📊 Custo medido em 08/08/2026: 29 pedaços de
        11.409 carregavam a etiqueta. Os outros 11.380 eram frases sobre "a
        apólice", sem seguradora, sem ramo e sem vigência — o material perfeito
        para o agente responder da Porto citando a cláusula da Allianz.

        A ordem certa é barata e não tem meio-termo: **picar primeiro,
        etiquetar depois.**
        """
        # Mesmas primitivas do seed global (global_knowledge_seed): mesma
        # coleção, mesmo escopo, mesmo serviço Qdrant. Só o `namespace` muda,
        # de 'canon' para 'normative'. Um segundo caminho de ingestão global
        # significaria dois corpora divergindo em silêncio.
        try:
            import asyncio

            return await asyncio.to_thread(
                _ingerir_sync, doc, texto, susep, vigencia)
        except Exception as exc:  # noqa: BLE001
            logger.error("[corpus] ingestao falhou: %s", type(exc).__name__)
            return 0

    def _marcar_conferido(self, documento_id: str, doc: dict, *, mudou: bool) -> None:
        dias = int(doc.get("check_interval_days") or INTERVALO_PADRAO_DIAS)
        self.db.table("normative_documents").update({
            "status": "ingested",
            "last_checked_at": _agora().isoformat(),
            "next_check_at": (_agora() + timedelta(days=dias)).isoformat(),
            "fetch_error": None, "fetch_attempts": 0,
            "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()

    # ------------------------------------------------------------------
    # Descoberta
    # ------------------------------------------------------------------

    async def descobrir(self, *, insurer_key: str, site: str,
                        limite: int = 60) -> dict:
        """Varre o site de uma seguradora atrás de documentos normativos.

        Propõe, não ingere. Nenhuma URL entra no corpus por descoberta
        automática: o que este método faz é substituir a busca manual por uma
        lista de candidatos que alguém confirma. Documento normativo alimenta o
        cérebro de todas as corretoras — a decisão de incluir é humana.
        """
        from ..research.firecrawl import FirecrawlClient, configurado

        if not configurado():
            return {"ok": False, "motivo": "firecrawl_nao_configurado", "candidatos": 0}

        nome = SEGURADORAS.get(insurer_key, (insurer_key.title(), ()))[0]
        cli = FirecrawlClient(self._raw, company_id=None)
        try:
            r = await cli.map_site(site, limite=max(20, min(limite * 8, 400)))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "motivo": type(exc).__name__, "candidatos": 0}
        if not r.ok:
            return {"ok": False, "motivo": r.erro or "falha", "candidatos": 0}

        urls = r.dados if isinstance(r.dados, list) else (r.dados or {}).get("links") or []
        propostos = 0
        for item in urls:
            u = item if isinstance(item, str) else (item or {}).get("url")
            if not u:
                continue
            baixo = u.lower()
            # Filtra pela URL antes de gastar leitura: só o que se parece com
            # norma vira candidato. Ler cada página do site para descobrir o
            # que é norma custaria mais do que o corpus economiza.
            if not any(p in baixo for p in (
                    "condicoes", "condições", "condicao", "geral", "manual",
                    "circular", "regulamento", "cartilha")):
                continue
            if not baixo.endswith((".pdf", ".html", "/")) and "." in baixo.rsplit("/", 1)[-1]:
                continue

            c = classificar("", "", u)
            if not c:
                continue
            try:
                self.db.table("normative_documents").upsert({
                    "insurer_key": insurer_key, "insurer_name": nome,
                    "product_line": c["product_line"], "doc_kind": c["doc_kind"],
                    "title": c["titulo_sugerido"], "source_url": u,
                    "status": "discovered", "next_check_at": _agora().isoformat(),
                    "notes": f"descoberto varrendo {site} — aguardando curadoria",
                }, on_conflict="source_url").execute()
                propostos += 1
            except Exception:  # noqa: BLE001
                continue

        logger.info("[corpus] descoberta em %s: %d candidato(s)", site, propostos)
        return {"ok": True, "candidatos": propostos, "urls_varridas": len(urls),
                "creditos": r.creditos}

    def aprovar(self, documento_id: str, *, user_id: Optional[str] = None,
                interval_days: Optional[int] = None) -> dict:
        """Curadoria: libera o candidato para ingestão."""
        patch: dict[str, Any] = {
            "approved_at": _agora().isoformat(), "approved_by": user_id,
            "next_check_at": _agora().isoformat(), "updated_at": _agora().isoformat(),
        }
        if interval_days:
            patch["check_interval_days"] = max(1, min(int(interval_days), 365))
        r = (self.db.table("normative_documents").update(patch)
             .eq("id", documento_id).execute()).data
        return (r or [{}])[0]

    def rejeitar(self, documento_id: str, *, motivo: str = "",
                 user_id: Optional[str] = None) -> bool:
        r = (self.db.table("normative_documents").update({
            "status": "rejected", "notes": motivo or "rejeitado na curadoria",
            "approved_by": user_id, "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()).data
        return bool(r)

    def candidatos(self, limite: int = 100) -> list[dict]:
        """Fila de curadoria."""
        r = (self.db.table("normative_documents")
             .select("id, insurer_name, product_line, doc_kind, title, source_url, "
                     "susep_process, notes, created_at")
             .eq("status", "discovered").is_("approved_at", "null")
             .order("created_at", desc=True).limit(limite).execute())
        return r.data or []

    # ------------------------------------------------------------------
    # Reconferência periódica
    # ------------------------------------------------------------------

    def vencidos(self, limite: int = 8) -> list[dict]:
        """Documentos cuja reconferência já venceu — só os aprovados.

        `approved_at` não-nulo é a trava que faz a curadoria valer alguma coisa.
        Sem ela, qualquer PDF descoberto por varredura entraria no cérebro de
        todas as corretoras no ciclo seguinte do worker, e a fila de curadoria
        seria decorativa.
        """
        r = (self.db.table("normative_documents")
             .select("id, title, insurer_name, source_url, next_check_at, status")
             .in_("status", ["ingested", "discovered", "unreachable"])
             .not_.is_("approved_at", "null")
             .lte("next_check_at", _agora().isoformat())
             .order("next_check_at").limit(limite).execute())
        achados = list(r.data or [])
        if len(achados) < limite:
            achados.extend(self._orfaos_de_fetching(limite - len(achados)))
        return achados

    # Quanto tempo um documento pode ficar em `fetching` antes de ser orfao.
    # Uma ingestao real leva segundos. Duas horas nao e margem — e certeza.
    HORAS_ATE_SER_ORFAO = 2

    def _orfaos_de_fetching(self, limite: int) -> list[dict]:
        """Documentos que morreram ENTRE marcar `fetching` e responder.

        📊 O buraco que isto fecha, medido em 05/08/2026: vinte e tres
        documentos aprovados ficaram presos em `fetching` por **oito dias**,
        invisiveis. `ingerir()` marca esse estado ANTES de ir a rede; se o
        processo morre no meio — deploy, timeout, ou o `TypeError` que este
        mesmo commit conserta — o documento fica num estado que **nenhuma
        consulta procura**.

        É a terceira vez que este repositorio aprende a mesma licao. A primeira
        foi a reconciliacao de acionamento orfao; a segunda, o vigia de
        handoff. A frase que fica:

            **Um estado que so e observado quando NASCE nao e observado.**

        Por que isto nao inunda o log quando falta credito: `ingerir()` devolve
        `bloqueante: True` no 402, e `reconferir_pendentes` PARA o ciclo no
        primeiro. Entao recuperar vinte e tres orfaos custa **uma** tentativa
        por rodada, nao vinte e tres — e o tratador de 402, agora que ele
        completa, move cada um para `discovered` com nova janela de seis horas.
        """
        if limite <= 0:
            return []
        limite_de_idade = (_agora() - timedelta(hours=self.HORAS_ATE_SER_ORFAO)).isoformat()
        try:
            r = (self.db.table("normative_documents")
                 .select("id, title, insurer_name, source_url, next_check_at, status")
                 .eq("status", "fetching")
                 .not_.is_("approved_at", "null")
                 .lt("updated_at", limite_de_idade)
                 .order("updated_at").limit(limite).execute())
        except Exception as exc:  # noqa: BLE001 — orfao nao pode derrubar a rodada
            logger.warning("[corpus] varredura de orfaos falhou: %s: %s",
                           type(exc).__name__, exc)
            return []
        orfaos = list(r.data or [])
        if orfaos:
            logger.warning(
                "[corpus] %d documento(s) presos em `fetching` ha mais de %dh "
                "foram reencontrados", len(orfaos), self.HORAS_ATE_SER_ORFAO)
        return orfaos

    async def reconferir_pendentes(self, *, limite: int = 5,
                                   company_id_custeio: Optional[str] = None) -> dict:
        """Passa nos documentos vencidos. Chamado pelo worker que já existe.

        Limite baixo de propósito: reconferência é trabalho de fundo e não pode
        competir com o trabalho que o corretor está esperando.
        """
        pendentes = self.vencidos(limite)
        if not pendentes:
            return {"conferidos": 0, "mudaram": 0}

        novos, mudaram, conferidos, falhas = 0, 0, 0, 0
        bloqueado = False
        for d in pendentes:
            r = await self.ingerir(d["id"], company_id_custeio=company_id_custeio)
            conferidos += 1
            if r.get("bloqueante"):
                # Credito esgotado: parar o ciclo. Insistir nos proximos so
                # produz mais 402 e enche o log de erro que nao e erro.
                bloqueado = True
                break
            if r.get("ok"):
                if r.get("mudou"):
                    mudaram += 1
                    logger.warning("[corpus] MUDOU na origem: %s (%s) — versao %s",
                                   d["title"][:70], d["insurer_name"], r.get("versao"))
                elif r.get("chunks"):
                    novos += 1
            else:
                falhas += 1
                logger.warning("[corpus] falhou: %s — %s", d["title"][:60], r.get("motivo"))

        return {"conferidos": conferidos, "novos": novos, "mudaram": mudaram,
                "falhas": falhas, "bloqueado_por_credito": bloqueado}
