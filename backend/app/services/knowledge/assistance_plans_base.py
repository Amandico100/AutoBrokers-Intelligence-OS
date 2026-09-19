# -*- coding: utf-8 -*-
"""A base GLOBAL de planos e serviços de assistência — o contrato único.

SPEC-EXTRA-001.5 · BLOCO A (unidade A). Este módulo é **o único caminho** de
leitura e escrita de `insurer_assistance_plans` e `insurer_assistance_services`.
As unidades B (a Skill) e C (as ondas de extração) consomem daqui — não do
`.table(...)` direto.

Por que ele existe, e por que é um só
-------------------------------------
Quem responde ao segurado *"seu plano tem carro reserva por 7 dias"* precisa
poder apontar **onde está escrito**. Este módulo é o lugar onde essa exigência
deixa de ser combinado e vira contrato: `propor_*` não aceita linha sem
documento e página, `publicar_*` não aceita publicação sem revisor humano, e
o banco recusa as duas coisas de novo, por CHECK (`servico_tem_fonte`,
`servico_publicado_foi_revisado`). Duas travas para a mesma regra é
redundância deliberada: o código pode ser contornado por um script; o CHECK,
não.

🔴 A BASE É GLOBAL — D-PILOTO-01
--------------------------------
As duas tabelas **não têm `company_id`**, e este módulo **não aceita** um. O
que a apólice da HDI cobre é o mesmo para a Resulta e para a AutoFleet: um
`company_id` aqui criaria a possibilidade de duas corretoras lerem respostas
diferentes sobre a mesma apólice — e de alguém "corrigir" a cobertura para uma
delas só. A prova por máquina é `test_a_base_de_planos_nao_tem_dono.py`
(CLAUDE.md §7).

⚠️ Consequência: a leitura aqui é de **service role**. Não há policy de RLS
para `authenticated` — é o padrão das quatro tabelas globais já vivas
(`normative_documents`, `normative_document_versions`, `portals`, `ura_maps`:
📊 17/09/2026, RLS ligada e ZERO policy em todas).

🔴 A CHAVE É `para="conhecimento"`, e não é detalhe
--------------------------------------------------
`normalize_insurer_key(x, para="corredor")` aplica `_OPERADO_POR`
(`{"itau": "porto"}`) — é a pergunta *"por onde eu ACIONO"*. Esta base responde
outra: *"de QUEM é a regra"*. Uma condição geral do Itaú arquivada sob Porto
faz o agente responder regra da Porto a segurado do Itaú. Por isso todas as
chamadas daqui passam `para="conhecimento"`, e há um guarda que faz `grep`
neste arquivo para provar que nenhuma passa `para="corredor"` (M-A1).

🔴 O QUE É "SEGURADORA CONHECIDA" — um critério só, verificável
--------------------------------------------------------------
`normalize_insurer_key` devolve **o primeiro token** para o que não conhece
(📊 `"seguradora_xyz"` → `"seguradora"`, `corridor_playbooks.py:8262`). Gravar
isso encheria a base de chaves-lixo que ninguém consegue achar depois. O
critério adotado é **um**, e é o mais próximo da verdade viva:

    conhecida  ⇔  a chave está em `set(_INSURER_ALIASES.values())`

Essa tabela é, pelas palavras do próprio código (`corridor_playbooks.py:8195`),
*"a lista de quem É seguradora"*. 📊 17/09/2026 ela tem **29** chaves canônicas.
As alternativas foram medidas e descartadas, e fica escrito por quê:

* `seguradora-coenti.json` (61 siglas da carteira) — 📊 **não** contém `hdi`,
  que tem 8 documentos no corpus e é a seguradora da apólice de referência.
  Usá-la sozinha recusaria a seguradora que mais precisamos.
* `select distinct insurer_key from portals` — só quem tem **portal**; é um
  subconjunto de quem tem condição geral.
* `select distinct insurer_key from normative_documents` — 📊 devolve
  `'susep'`, que é o **regulador**, não uma seguradora. Aceitá-la criaria o
  "plano de assistência da SUSEP".

Quem não passa no critério sai como `SeguradoraDesconhecida`, cuja mensagem
**lista o valor que veio** (nunca `None`, nunca silêncio) — a mesma regra de
`susep_ses_provider.py:92-95`.

O que este módulo NÃO é
-----------------------
Não é normalizador de seguradora (chama o que existe), não é catálogo de
serviços (lê o JSON versionado), não é extrator de PDF (usa o `fitz` de
`insurance_corpus`) e não tem LLM. CLAUDE.md §5.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TABELA_PLANOS = "insurer_assistance_plans"
TABELA_SERVICOS = "insurer_assistance_services"

CURADORIAS = ("rascunho", "proposto", "publicado", "rejeitado")
COBERTURAS = ("sim", "nao", "condicionado")
CONFIANCAS = ("alta", "media", "baixa")
UNIDADES = ("km", "dias", "acionamentos_ano", "reais", "unidades")

#: 🔴 ONDE O VOCABULÁRIO MORA — DENTRO DO PACOTE (SPEC-EXTRA-001.5.1, D1).
#:
#: `backend/app/data/servicos-de-assistencia.json`. É `app/`, logo é **código**,
#: logo entra no `COPY . .` do `backend/Dockerfile`. É o conserto do defeito que
#: manteve a Skill de cobertura DESLIGADA em produção, em silêncio, desde a
#: 001.5 (📊 19/09: `/fila` → 500; o compositor logando
#: `Skill de cobertura indisponível` e caindo no caminho antigo).
#:
#: ⚠️ Um só valor, para o resolvedor e a mensagem de erro não divergirem.
_NO_PACOTE = ("data", "servicos-de-assistencia.json")

#: O caminho RELATIVO do vocabulário a partir da RAIZ DO REPOSITÓRIO — onde o
#: arquivo morava até 19/09/2026. Continua sendo procurado (uma árvore antiga,
#: ou um checkout parcial, ainda pode tê-lo ali), mas hoje o de `docs/` é um
#: **ponteiro** de cinco linhas, não o dado.
#:
#: 🔴 PONTEIRO × CÓPIA — a decisão, com nota (protocolo §9)
#: ```
#: PONTEIRO no `docs/`, dado só no pacote ........ 88   escolhido
#:     uma fonte só (CLAUDE.md §5: consolidar, não duplicar); divergência
#:     IMPOSSÍVEL, não "detectável depois"; custo: quem lê o canon dá um pulo
#: CÓPIA nos dois + guarda de igualdade byte a byte  72
#:     o canon continua lendo o dado direto; mas são DOIS arquivos para editar,
#:     e o guarda só grita DEPOIS que alguém editou um e esqueceu o outro —
#:     é alarme, não impedimento
#: ```
#: E a porta que a escolha fecha: se um dia o resolvedor pegar o ponteiro por
#: engano, `vocabulario_de_servicos` **recusa** (não há chave `servicos`), em vez
#: de carregar um vocabulário vazio que faria `servico_canonico` devolver `None`
#: para tudo — o mesmo silêncio que esta SPEC existe para matar.
_RELATIVO_DO_VOCABULARIO = ("docs", "canon", "providers", "susep",
                            "servicos-de-assistencia.json")


class VocabularioNaoEncontrado(Exception):
    """O JSON do vocabulário não está em lugar nenhum dos caminhos procurados.

    ⚠️ Não herda de `BaseDePlanosRecusa` de propósito: recusa é *"a linha está
    errada"*; isto é *"a instalação está incompleta"*. Quem trata recusa
    devolvendo "não sabemos ainda" ao segurado esconderia uma árvore quebrada
    atrás de uma lacuna de curadoria.

    🔴 A mensagem LISTA os caminhos tentados. 📊 17/09/2026 a bateria de mutação
    da fatia 2 copiou **só `backend/`** para a cópia, e
    `Path(__file__).parents[4]` apontava para fora dela — o módulo quebrava com
    `FileNotFoundError` num caminho que ninguém reconhecia como "faltou o
    `docs/`". Um erro que não diz onde procurou obriga quem lê a reconstruir a
    aritmética de `parents[n]` de cabeça.
    """


def _candidatos_do_vocabulario() -> List[Path]:
    """Os caminhos procurados, na ordem — sem I/O.

    🔴 ⓪ **DENTRO DO PACOTE**, `app/data/` — o único que existe na IMAGEM.
    ① `AUTOBROKERS_REPO_ROOT` (se o ambiente declarar a raiz);
    ② **subindo** a árvore a partir deste arquivo até achar `docs/canon`;
    ③ o caminho histórico `parents[4]`, que continua valendo na árvore normal.

    ⚠️ Subir procurando `docs/canon` (e não contar `parents[n]`) é o que faz o
    módulo funcionar de qualquer `cwd` e sobreviver a mover a pasta um nível.

    🔴 **⓪ VEM PRIMEIRO, E A ORDEM É O CONSERTO.** ①②③ apontam todos para fora
    da imagem (📊 19/09/2026: `backend/Dockerfile` é `WORKDIR /app` + `COPY . .`
    de dentro de `backend/`; `/health` publica `code_files: 396`, que é o número
    de `.py` em `backend/app` — `docs/` não está lá). Deixar ⓪ por último faria a
    árvore de desenvolvimento continuar lendo o `docs/`, e o guarda do contêiner
    passaria a medir uma coisa e produção a rodar outra: a cegueira do §9.1, de
    novo, uma casa adiante.
    """
    import os

    fora: List[Path] = []
    # ⓪ `parents[2]` a partir de `app/services/knowledge/` é `app/`.
    fora.append(Path(__file__).resolve().parents[2].joinpath(*_NO_PACOTE))
    declarada = os.environ.get("AUTOBROKERS_REPO_ROOT")
    if declarada:
        fora.append(Path(declarada).joinpath(*_RELATIVO_DO_VOCABULARIO))
    aqui = Path(__file__).resolve()
    for pai in aqui.parents:
        if (pai / "docs" / "canon").is_dir():
            fora.append(pai.joinpath(*_RELATIVO_DO_VOCABULARIO))
            break
    historico = aqui.parents[4].joinpath(*_RELATIVO_DO_VOCABULARIO) \
        if len(aqui.parents) > 4 else None
    if historico is not None and historico not in fora:
        fora.append(historico)
    return fora


def caminho_do_vocabulario() -> Path:
    """O primeiro candidato que EXISTE. Nenhum existe → erro com a lista."""
    candidatos = _candidatos_do_vocabulario()
    for caminho in candidatos:
        if caminho.is_file():
            return caminho
    raise VocabularioNaoEncontrado(
        "o vocabulário de serviços (%s; mora em backend/%s) não está em nenhum "
        "destes caminhos: %s"
        % ("/".join(_RELATIVO_DO_VOCABULARIO), "app/" + "/".join(_NO_PACOTE),
           [str(c) for c in candidatos])
    )


class _CaminhoDoVocabulario:
    """O que `ARQUIVO_DE_SERVICOS` era — um `Path` — mas resolvido na hora.

    ⚠️ Mantido como objeto (e não como função) porque o módulo já publica
    `ARQUIVO_DE_SERVICOS.name` na mensagem de `propor_servico`, e um guarda da
    fatia 1 depende dela. Trocar por função quebraria o chamador para consertar
    o resolvedor — o remendo ao lado que CLAUDE.md §5 proíbe.
    """

    @property
    def name(self) -> str:
        return _RELATIVO_DO_VOCABULARIO[-1]

    def __fspath__(self) -> str:
        return str(caminho_do_vocabulario())

    def __str__(self) -> str:  # pragma: no cover - conveniência de log
        return str(caminho_do_vocabulario())

    def __repr__(self) -> str:  # pragma: no cover
        return "<vocabulario %s>" % self.name


#: O vocabulário de `servico`. Dado versionado, revisável, diffável — nunca
#: regex escondido no código (§5.2 da SPEC).
ARQUIVO_DE_SERVICOS = _CaminhoDoVocabulario()


# ---------------------------------------------------------------------------
# Erros — a mensagem CARREGA o valor
# ---------------------------------------------------------------------------
class BaseDePlanosRecusa(Exception):
    """Recusa do contrato, ANTES do banco. O banco recusa de novo."""


class SeguradoraDesconhecida(BaseDePlanosRecusa):
    """A chave não é de nenhuma seguradora que conhecemos.

    ⚠️ A mensagem LISTA o valor que veio. Uma recusa que não diz o que recusou
    obriga quem curou a adivinhar, e o caminho mais curto vira inventar a chave.
    """

    def __init__(self, valor: Any, chave_bruta: str = "") -> None:
        self.valor = str(valor)
        self.chave_bruta = chave_bruta
        super().__init__(
            f"seguradora desconhecida: {self.valor!r}"
            + (f" (normalizou para {chave_bruta!r})" if chave_bruta else "")
            + " — não está em _INSURER_ALIASES. Acrescente o alias com o critério"
            " ao lado (corridor_playbooks.py) antes de gravar."
        )


class FonteObrigatoria(BaseDePlanosRecusa):
    """Linha sem documento, sem página >= 1 ou sem `trecho_hash` de 64 hex."""


class RevisorObrigatorio(BaseDePlanosRecusa):
    """Publicar é ato humano. Sem `revisado_por`, não publica."""


# ---------------------------------------------------------------------------
# A chave canônica
# ---------------------------------------------------------------------------
def _aliases_e_normalizador():
    """Importa do módulo QUE JÁ EXISTE. Nunca copia a tabela para cá.

    Import tardio de propósito: `corridor_playbooks` é grande e este módulo é
    importado por caminhos que não precisam dele carregado no import time.
    """
    from ..corridor_playbooks import _INSURER_ALIASES, normalize_insurer_key

    return _INSURER_ALIASES, normalize_insurer_key


def seguradoras_conhecidas() -> frozenset:
    """As chaves canônicas — `set(_INSURER_ALIASES.values())`. 📊 29 em 17/09."""
    aliases, _ = _aliases_e_normalizador()
    return frozenset(aliases.values())


def chave_de_conhecimento(insurer: Any) -> str:
    """A chave sob a qual a regra desta seguradora é arquivada.

    Chama `normalize_insurer_key(..., para="conhecimento")` — a função que já
    existe — e **confere depois** se o resultado é de uma seguradora conhecida
    (ver o docstring do módulo). Desconhecida levanta `SeguradoraDesconhecida`
    com o valor listado; nada é gravado.

    >>> chave_de_conhecimento("Tokio Marine")   # doctest: +SKIP
    'tokio'
    """
    _, normalize = _aliases_e_normalizador()
    bruto = str(insurer or "").strip()
    if not bruto:
        raise SeguradoraDesconhecida("", "")
    chave = normalize(bruto, para="conhecimento")
    if chave not in seguradoras_conhecidas():
        raise SeguradoraDesconhecida(bruto, chave)
    return chave


# ---------------------------------------------------------------------------
# O vocabulário de serviço
# ---------------------------------------------------------------------------
_VOCABULARIO: Optional[Dict[str, Any]] = None


def _norm_texto(texto: Any) -> str:
    """Minúsculas, sem acento, espaço colapsado.

    ⚠️ CLAUDE.md §9.4 (dialeto): esta é a MESMA normalização usada para casar o
    sinônimo e para montar o índice de sinônimos. Duas normalizações diferentes
    para os dois lados dariam zero casamento em silêncio.
    """
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in bruto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def vocabulario_de_servicos() -> Dict[str, Any]:
    """O JSON versionado, lido uma vez. Levanta se o arquivo sumir.

    ⚠️ Não há fallback embutido de propósito: um fallback silencioso faria o
    produto responder com um vocabulário fantasma que ninguém consegue revisar.
    """
    global _VOCABULARIO
    if _VOCABULARIO is None:
        caminho = caminho_do_vocabulario()
        with open(caminho, "r", encoding="utf-8") as fh:
            carregado = json.load(fh)
        # 🔴 VOCABULÁRIO VAZIO É INSTALAÇÃO INCOMPLETA, NÃO VOCABULÁRIO.
        #
        # Desde 19/09 o arquivo de `docs/` é um PONTEIRO (sem a chave
        # `servicos`). Se o resolvedor pegasse o ponteiro por engano, o dict
        # viria vazio e `servico_canonico` devolveria `None` para TODA pergunta
        # — a Skill desligada de novo, e desta vez sem nem uma exceção no log.
        # Um arquivo que existe e não tem serviços é a mesma classe de problema
        # que arquivo nenhum, e recebe o mesmo erro, que LISTA onde procurou.
        if not (carregado.get("servicos") or {}):
            raise VocabularioNaoEncontrado(
                "o arquivo %s existe mas não declara nenhum serviço "
                "(sem a chave `servicos`) — o vocabulário mora em backend/%s"
                % (caminho, "app/" + "/".join(_NO_PACOTE))
            )
        _VOCABULARIO = carregado
    return _VOCABULARIO


def servicos_declarados() -> Tuple[str, ...]:
    return tuple(sorted(vocabulario_de_servicos().get("servicos", {})))


def tipo_do_servico(servico: str) -> Optional[str]:
    """`"assistencia"` ou `"cobertura"`. 🔴 Granizo é COBERTURA, não assistência."""
    item = vocabulario_de_servicos().get("servicos", {}).get(str(servico or ""))
    return item.get("tipo") if item else None


def servico_canonico(texto: Any) -> Optional[str]:
    """Texto do segurado → a chave canônica do serviço, ou `None`.

    Casa por **palavra inteira** sobre o texto normalizado, e o sinônimo mais
    LONGO vence. 🔴 Substring foi descartada com medição: é o defeito que fundiu
    `"caixa seguradora"` em `axa` (`corridor_playbooks.py`, comentário de
    `normalize_insurer_key`); aqui faria `"carro reserva"` casar uma chave que
    tivesse o sinônimo `"carro"`.
    """
    alvo = _norm_texto(texto)
    if not alvo:
        return None
    candidatos: List[Tuple[int, str]] = []
    for chave, item in vocabulario_de_servicos().get("servicos", {}).items():
        for sin in [chave] + list(item.get("sinonimos") or []):
            termo = _norm_texto(sin)
            if not termo:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(termo)}(?![a-z0-9])", alvo):
                candidatos.append((len(termo), chave))
    if not candidatos:
        return None
    return sorted(candidatos, reverse=True)[0][1]


# ---------------------------------------------------------------------------
# A fonte: hash do trecho e conferência da página
# ---------------------------------------------------------------------------
def normalizar_trecho(texto: Any) -> str:
    """A normalização do trecho ANTES do hash. Uma só, para os dois lados.

    ⚠️ Não baixa caixa nem tira acento: o trecho é jurídico e "Franquia" e
    "franquia" podem estar em contextos diferentes. Só colapsa o espaço em
    branco — que é o que o extrator de PDF varia entre versões.
    """
    return re.sub(r"\s+", " ", str(texto or "").replace("\xa0", " ")).strip()


def hash_do_trecho(texto: Any) -> str:
    """sha256 (64 hex) do trecho normalizado. O trecho CRU nunca é copiado."""
    return hashlib.sha256(normalizar_trecho(texto).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConferenciaDePagina:
    """Resultado explícito. `fonte_ausente` NÃO é `False`, e não é `True`.

    🔴 Devolver `False` para "o PDF não está arquivado" ensinaria o curador a
    tratar documento sem fonte como trecho errado — e a apagar a linha certa.
    """

    ok: bool
    motivo: str
    pagina: Optional[int] = None
    total_de_paginas: Optional[int] = None

    def __bool__(self) -> bool:
        return self.ok


def bytes_da_fonte(
    documento_id: str,
    *,
    versao: Optional[int] = None,
    db: Any = None,
    minio: Any = None,
) -> Tuple[Optional[bytes], str]:
    """Os bytes do PDF arquivado, ou `(None, motivo)`. **Um só caminho.**

    🔴 CLAUDE.md §5: `conferir_pagina` (conferência) e `texto_das_paginas`
    (leitura, para o extrator e para a tela) pedem a fonte por AQUI. Duas
    funções baixando o original por conta própria acabariam divergindo na
    escolha da versão — e a conferência passaria a conferir um PDF diferente do
    que a pessoa lê na tela.
    """
    db = db if db is not None else _db()
    consulta = (
        db.table("normative_document_versions")
        .select("version, storage_ref")
        .eq("document_id", str(documento_id))
    )
    if versao is not None:
        consulta = consulta.eq("version", int(versao))
    linhas = (consulta.order("version", desc=True).limit(1).execute()).data or []
    if not linhas:
        return None, "documento_sem_versao"
    if not linhas[0].get("storage_ref"):
        # 🔴 explícito: 📊 33 das 206 versões não têm fonte arquivada (17/09).
        return None, "fonte_ausente"

    from . import acervo_arquivo as AA

    if minio is None:
        try:
            from ..minio_service import get_minio_service

            minio = get_minio_service()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[base-planos] MinIO indisponivel: %s", type(exc).__name__)
            return None, "minio_indisponivel"

    caminho = AA.caminho(str(documento_id), int(linhas[0]["version"]), AA.ORIGINAL)
    try:
        return minio.download_file(caminho).read(), "ok"
    except Exception as exc:  # noqa: BLE001
        logger.info("[base-planos] original ausente (%s): %s", caminho, type(exc).__name__)
        return None, "fonte_ausente"


@dataclass(frozen=True)
class PaginasDoDocumento:
    """O texto das páginas pedidas. `motivo` explica o vazio, sempre."""

    ok: bool
    motivo: str
    total: int = 0
    paginas: Dict[int, str] = None  # type: ignore[assignment]

    def texto(self, pagina: int) -> Optional[str]:
        return (self.paginas or {}).get(int(pagina))


def texto_das_paginas(
    documento_id: str,
    paginas: Optional[List[int]] = None,
    *,
    versao: Optional[int] = None,
    db: Any = None,
    minio: Any = None,
    corpo: Optional[bytes] = None,
) -> PaginasDoDocumento:
    """Lê o PDF arquivado e devolve `{pagina: texto}` — 1-based.

    `paginas=None` lê o documento inteiro (é o que a onda 1 precisa para achar
    as páginas com termos do vocabulário). `corpo` permite reusar bytes já
    baixados, para não bater no MinIO uma vez por página.

    ⛔ Nenhum segundo leitor de PDF: é o mesmo `fitz` de
    `insurance_corpus.extrair_texto_de_pdf` e de `conferir_pagina`.
    """
    if corpo is None:
        corpo, motivo = bytes_da_fonte(documento_id, versao=versao, db=db, minio=minio)
        if corpo is None:
            return PaginasDoDocumento(False, motivo, 0, {})
    try:
        import fitz
    except Exception:  # noqa: BLE001
        return PaginasDoDocumento(False, "sem_extrator_de_pdf", 0, {})
    doc = None
    try:
        doc = fitz.open(stream=corpo, filetype="pdf")
        total = doc.page_count
        alvo = [int(p) for p in (paginas if paginas is not None else range(1, total + 1))]
        fora = {p: doc[p - 1].get_text("text") for p in alvo if 1 <= p <= total}
        return PaginasDoDocumento(True, "ok", total, fora)
    except Exception as exc:  # noqa: BLE001
        return PaginasDoDocumento(False, "pdf_ilegivel:%s" % type(exc).__name__, 0, {})
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:  # noqa: BLE001
                pass


def conferir_pagina(
    documento_id: str,
    pagina: int,
    *,
    trecho: Optional[str] = None,
    trecho_hash: Optional[str] = None,
    versao: Optional[int] = None,
    db: Any = None,
    minio: Any = None,
) -> ConferenciaDePagina:
    """O trecho ESTÁ naquela página do documento arquivado?

    Abre a fonte arquivada (`normative_document_versions.storage_ref` → MinIO,
    por `acervo_arquivo.caminho`), lê a página com o **mesmo `fitz`** que
    `insurance_corpus.extrair_texto_de_pdf` usa (CLAUDE.md §5: nenhum segundo
    leitor de PDF) e confere.

    O trecho é passado pelo CHAMADOR — esta função não extrai nada. Se só vier
    `trecho_hash`, a conferência é por hash do texto da página inteira, que é
    mais fraca e está declarada em `motivo`.

    Motivos possíveis: `confere` · `trecho_nao_esta_na_pagina` ·
    `pagina_inexistente` · `fonte_ausente` · `documento_sem_versao` ·
    `pdf_ilegivel` · `sem_extrator_de_pdf` · `minio_indisponivel` ·
    `sem_trecho_para_conferir`.
    """
    if trecho is None and not trecho_hash:
        return ConferenciaDePagina(False, "sem_trecho_para_conferir")
    try:
        pagina = int(pagina)
    except (TypeError, ValueError):
        return ConferenciaDePagina(False, "pagina_inexistente")
    if pagina < 1:
        return ConferenciaDePagina(False, "pagina_inexistente", pagina)

    corpo, motivo = bytes_da_fonte(documento_id, versao=versao, db=db, minio=minio)
    if corpo is None:
        return ConferenciaDePagina(False, motivo)

    try:
        import fitz  # o MESMO de insurance_corpus.extrair_texto_de_pdf
    except Exception:  # noqa: BLE001
        return ConferenciaDePagina(False, "sem_extrator_de_pdf")

    doc = None
    try:
        doc = fitz.open(stream=corpo, filetype="pdf")
        total = doc.page_count
        if pagina > total:
            return ConferenciaDePagina(False, "pagina_inexistente", pagina, total)
        texto = doc[pagina - 1].get_text("text")
    except Exception as exc:  # noqa: BLE001
        return ConferenciaDePagina(False, f"pdf_ilegivel:{type(exc).__name__}")
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:  # noqa: BLE001
                pass

    da_pagina = normalizar_trecho(texto)
    if trecho is not None:
        bate = normalizar_trecho(trecho) in da_pagina
    else:
        bate = hash_do_trecho(texto) == str(trecho_hash)
    return ConferenciaDePagina(
        bate, "confere" if bate else "trecho_nao_esta_na_pagina", pagina, total
    )


# ---------------------------------------------------------------------------
# O cliente — service role, SEM company_id
# ---------------------------------------------------------------------------
def _db(supabase_client: Any = None) -> Any:
    """O cliente do projeto, do mesmo jeito que `insurance_corpus` faz.

    ⛔ Nenhuma função deste módulo aceita `company_id`. A base é global.
    """
    if supabase_client is not None:
        return getattr(supabase_client, "client", supabase_client)
    from ...core.database import get_supabase_client

    return get_supabase_client().client


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _exigir_fonte(documento_id: Any, pagina: Any, trecho_hash: Any = None) -> int:
    if not documento_id:
        raise FonteObrigatoria("sem documento_id: toda linha aponta a sua origem")
    try:
        pagina = int(pagina)
    except (TypeError, ValueError):
        raise FonteObrigatoria(f"pagina inválida: {pagina!r}") from None
    if pagina < 1:
        raise FonteObrigatoria(f"pagina precisa ser >= 1, veio {pagina!r}")
    if trecho_hash is not None:
        th = str(trecho_hash)
        if len(th) != 64 or not re.fullmatch(r"[0-9a-f]{64}", th):
            raise FonteObrigatoria(
                f"trecho_hash precisa ser sha256 (64 hex), veio {len(th)} char(s)"
            )
    return pagina


def _so_valores(nome: str, valor: Any, permitidos: Tuple[str, ...]) -> str:
    if str(valor) not in permitidos:
        raise BaseDePlanosRecusa(
            f"{nome} inválido: {valor!r} — permitidos {list(permitidos)}"
        )
    return str(valor)


# ---------------------------------------------------------------------------
# Escrita — SEMPRE 'proposto'. Publicar é outro ato, e é humano.
# ---------------------------------------------------------------------------
def propor_plano(
    *,
    insurer: str,
    ramo: str,
    produto: str,
    plano: str,
    nivel: int,
    vigencia_inicio: date,
    documento_id: str,
    pagina: int,
    content_hash: str,
    confianca: str = "media",
    vigencia_fim: Optional[date] = None,
    susep_process: Optional[str] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """Propõe um plano. 🔴 Nasce `curadoria='proposto'`, nunca `publicado`.

    O parâmetro `curadoria` **não existe** de propósito: um extrator que possa
    escolher o estado acaba escolhendo `publicado` — é o pior desfecho desta
    SPEC (§5.2).
    """
    chave = chave_de_conhecimento(insurer)
    pagina = _exigir_fonte(documento_id, pagina)
    if int(nivel) < 1:
        raise BaseDePlanosRecusa(f"nivel precisa ser >= 1, veio {nivel!r}")
    linha = {
        "insurer_key": chave,
        "ramo": _norm_texto(ramo).replace(" ", "_"),
        "produto": str(produto),
        "plano": str(plano),
        "nivel": int(nivel),
        "vigencia_inicio": str(vigencia_inicio),
        "vigencia_fim": str(vigencia_fim) if vigencia_fim else None,
        "susep_process": susep_process,
        "documento_id": str(documento_id),
        "pagina": pagina,
        "confianca": _so_valores("confianca", confianca, CONFIANCAS),
        "curadoria": "proposto",
        "content_hash": str(content_hash),
    }
    r = _db(db).table(TABELA_PLANOS).insert(linha).execute()
    return (r.data or [{}])[0]


def propor_servico(
    *,
    plano_id: str,
    servico: str,
    coberto: str,
    documento_id: str,
    pagina: int,
    trecho: Optional[str] = None,
    trecho_hash: Optional[str] = None,
    limite_valor: Optional[float] = None,
    limite_unidade: Optional[str] = None,
    limite_texto: Optional[str] = None,
    carencia_dias: Optional[int] = None,
    condicao: Optional[str] = None,
    confianca: str = "media",
    db: Any = None,
) -> Dict[str, Any]:
    """Propõe uma linha de serviço. 🔴 Nasce `proposto`, com FONTE obrigatória.

    `trecho` (o texto) ou `trecho_hash` (já calculado). Passando o texto, o hash
    sai de `hash_do_trecho` — o mesmo que `conferir_pagina` usa, para os dois
    lados nunca discordarem de normalização (CLAUDE.md §9.4).
    """
    if trecho_hash is None:
        if trecho is None:
            raise FonteObrigatoria("sem trecho e sem trecho_hash: a linha não tem lastro")
        trecho_hash = hash_do_trecho(trecho)
    pagina = _exigir_fonte(documento_id, pagina, trecho_hash)
    if servico not in servicos_declarados():
        raise BaseDePlanosRecusa(
            f"servico {servico!r} não está no vocabulário "
            f"({ARQUIVO_DE_SERVICOS.name}). Acrescente a chave lá, com sinônimos."
        )
    if limite_valor is not None and not limite_unidade:
        raise BaseDePlanosRecusa(
            f"limite_valor={limite_valor!r} sem limite_unidade: "
            "'200' sozinho vira '200 dias' na cabeça de quem lê"
        )
    if limite_unidade is not None:
        _so_valores("limite_unidade", limite_unidade, UNIDADES)
    linha = {
        "plano_id": str(plano_id),
        "servico": str(servico),
        "coberto": _so_valores("coberto", coberto, COBERTURAS),
        "limite_valor": limite_valor,
        "limite_unidade": limite_unidade,
        "limite_texto": limite_texto,
        "carencia_dias": carencia_dias,
        "condicao": condicao,
        "documento_id": str(documento_id),
        "pagina": pagina,
        "trecho_hash": trecho_hash,
        "confianca": _so_valores("confianca", confianca, CONFIANCAS),
        "curadoria": "proposto",
    }
    r = _db(db).table(TABELA_SERVICOS).insert(linha).execute()
    return (r.data or [{}])[0]


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _exigir_revisor(revisado_por: Any, acao: str) -> str:
    """O revisor é uma PESSOA do sistema, e a prova disso é o formato do id.

    🔴 Aceitar qualquer string aqui faz `revisado_por='robo'` (ou `'system'`, ou
    a string vazia depois de um `str(None)`) passar pelo CHECK do banco, que só
    exige *não nulo*. O nome que fica gravado é a única resposta à pergunta
    *"quem respondeu por 'guincho até 200 km'?"* — e ele tem de apontar para
    alguém que exista.
    """
    bruto = str(revisado_por or "").strip()
    if not bruto:
        raise RevisorObrigatorio(
            "%s sem `revisado_por` é o que esta base existe para impedir: "
            "aprovar o PDF não é aprovar 'guincho até 200 km'" % acao
        )
    if not _UUID_RE.match(bruto):
        raise RevisorObrigatorio(
            "`revisado_por` precisa ser o id do usuário autenticado (uuid), veio %r — "
            "um rótulo livre não aponta para pessoa nenhuma" % bruto
        )
    return bruto


def publicar_servico(servico_id: str, revisado_por: Any, *, db: Any = None) -> Dict[str, Any]:
    """Publica uma linha **e o plano dela**. 🔴 Sem revisor, recusa antes do banco.

    🔴 POR QUE O PLANO VAI JUNTO — e por que isso não é publicar sem gente
    ===================================================================
    A leitura que chega ao segurado (`planos_publicados` → `buscar_servico`)
    parte do PLANO: um serviço `publicado` pendurado num plano `proposto` é
    invisível. O Founder publicava dez linhas pela tela e o segurado continuava
    ouvindo *"ainda não sei"* — o pior desfecho possível, porque o trabalho foi
    feito e não apareceu, e ninguém tem como descobrir por quê.

    ⚠️ A pessoa que publica a linha **leu o plano**: a fila mostra seguradora,
    ramo, produto, plano, nível e a página do plano ao lado do serviço
    (`fila_de_curadoria`). Publicar o plano pai carrega o MESMO `revisado_por` e
    o MESMO `revisado_em` — é o mesmo ato humano, não um segundo ato automático.

    🔴 E só se publica a partir de `proposto`: uma linha `rejeitado` ou
    `rascunho` foi recusada por alguém ou pelo verificador, e republicá-la por um
    clique desfaria a recusa sem que ninguém revisse o motivo.
    """
    revisor = _exigir_revisor(revisado_por, "publicar")
    cliente = _db(db)

    atual = (
        cliente.table(TABELA_SERVICOS).select("*").eq("id", str(servico_id))
        .limit(1).execute()
    ).data or []
    if not atual:
        raise BaseDePlanosRecusa("serviço %r não existe" % str(servico_id))
    estado = str(atual[0].get("curadoria") or "")
    if estado == "publicado":
        # 🔴 RE-PUBLICAR SOBRESCREVERIA QUEM REVISOU.
        #
        # 📊 18/09/2026: o código aceitava `publicado` e o patch trocava
        # `revisado_por`/`revisado_em` — dois cliques na fila e a linha passava a
        # dizer que foi a segunda pessoa quem a leu. `revisado_por` é a prova de
        # proveniência desta base (§14, PROV-O): ele responde *"quem respondeu
        # por 'guincho até 200 km'?"*, e essa resposta não pode mudar sozinha.
        raise BaseDePlanosRecusa(
            "esta linha já está publicada (revisada por %s em %s). Republicar "
            "trocaria quem respondeu por ela; para revisá-la de novo, o caminho é "
            "derrubá-la para `proposto`."
            % (atual[0].get("revisado_por"), str(atual[0].get("revisado_em"))[:10])
        )
    if estado != "proposto":
        raise BaseDePlanosRecusa(
            "só se publica a partir de `proposto`; esta linha está %r. "
            "Desfazer uma recusa é outro ato, e ele passa por quem recusou." % estado
        )

    carimbo = _agora()
    patch = {
        "curadoria": "publicado",
        "revisado_por": revisor,
        "revisado_em": carimbo,
        "updated_at": carimbo,
    }
    r = cliente.table(TABELA_SERVICOS).update(patch).eq("id", str(servico_id)).execute()

    plano_id = atual[0].get("plano_id")
    if plano_id:
        pai = (
            cliente.table(TABELA_PLANOS).select("id, curadoria").eq("id", str(plano_id))
            .limit(1).execute()
        ).data or []
        if pai and str(pai[0].get("curadoria")) == "proposto":
            cliente.table(TABELA_PLANOS).update({
                "curadoria": "publicado",
                "revisado_por": revisor,
                "revisado_em": carimbo,
                "updated_at": carimbo,
            }).eq("id", str(plano_id)).execute()
            logger.info("[base-planos] plano %s publicado junto com o servico", plano_id)
    return (r.data or [{}])[0]


def publicar_plano(plano_id: str, revisado_por: Any, *, db: Any = None) -> Dict[str, Any]:
    """O irmão de `publicar_servico`, para o plano."""
    revisor = _exigir_revisor(revisado_por, "publicar plano")
    patch = {
        "curadoria": "publicado",
        "revisado_por": revisor,
        "revisado_em": _agora(),
        "updated_at": _agora(),
    }
    r = _db(db).table(TABELA_PLANOS).update(patch).eq("id", str(plano_id)).execute()
    return (r.data or [{}])[0]


# ---------------------------------------------------------------------------
# Leitura — só o que está PUBLICADO chega ao segurado
# ---------------------------------------------------------------------------
def _como_data(valor: Any) -> Optional[date]:
    """`date`, `datetime`, ISO ou `dd/mm/aaaa`. Não adivinha o resto."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    bruto = str(valor).strip()
    if "/" in bruto:
        partes = bruto.split("/")
        if len(partes) == 3 and len(partes[2]) == 4:
            try:
                return date(int(partes[2]), int(partes[1]), int(partes[0]))
            except ValueError:
                return None
        return None
    try:
        return datetime.fromisoformat(bruto[:10]).date()
    except ValueError:
        return None


def vigente_em(plano: Dict[str, Any], quando: Optional[date]) -> bool:
    """O plano valia naquela data? `vigencia_fim` nulo = ainda vale.

    🔴 A regra é a MESMA do elo SUSEP (`assistance_plans_susep_link`):
    `inicio <= data < fim`. Duas regras de vigência no mesmo produto dariam
    respostas diferentes para a mesma apólice conforme o caminho — e a que
    chegasse ao segurado seria a do acaso.
    """
    if quando is None:
        return True
    inicio = _como_data(plano.get("vigencia_inicio"))
    fim = _como_data(plano.get("vigencia_fim"))
    if inicio is not None and quando < inicio:
        return False
    if fim is not None and quando >= fim:
        return False
    return True


def planos_publicados(
    insurer_key: str, ramo: str, produto: Optional[str] = None, *,
    data_emissao: Any = None, db: Any = None,
) -> List[Dict[str, Any]]:
    """Os planos publicados, **ordenados por `nivel`** (1 = o mais básico).

    `data_emissao` filtra pela vigência do plano — a apólice de 2023 é regida
    pela condição de 2023 (§7.2). Sem data, valem os vigentes **hoje**: um plano
    já substituído não pode responder por um contrato novo só porque continua na
    tabela.
    """
    q = (
        _db(db)
        .table(TABELA_PLANOS)
        .select("*")
        .eq("insurer_key", chave_de_conhecimento(insurer_key))
        .eq("ramo", _norm_texto(ramo).replace(" ", "_"))
        .eq("curadoria", "publicado")
    )
    if produto:
        q = q.eq("produto", str(produto))
    linhas = (q.order("nivel").execute()).data or []

    # 🔴 DATA ILEGÍVEL NÃO É "HOJE" — é DESCONHECIDA.
    #
    # 📊 18/09/2026: `_como_data("maio de 2023") or date.today()` fazia uma data
    # que o parser não entende degradar, em silêncio, para a condição de HOJE — e
    # o agente respondia sobre uma apólice de 2023 com o plano atual, com toda a
    # confiança. É o defeito que a abertura de `insurance_corpus.py` descreve.
    # Data AUSENTE continua valendo os planos vigentes hoje: aí não há o que
    # errar, ninguém afirmou uma data.
    if data_emissao not in (None, "") and _como_data(data_emissao) is None:
        logger.info("[base-planos] data de emissao ilegivel: nao respondo por vigencia")
        return []

    quando = _como_data(data_emissao) or date.today()
    return [p for p in linhas if vigente_em(p, quando)]


def existe_linha_publicada(
    insurer_key: str, ramo: str, servico: str, produto: Optional[str] = None, *,
    data_emissao: Any = None, db: Any = None,
) -> bool:
    """Há QUALQUER linha publicada deste serviço nesta seguradora/ramo/produto?

    🔴 É a pergunta que autoriza (ou proíbe) o fallback genérico. Quando a base
    **já sabe** o que aquela seguradora diz sobre eletricista, responder *"pelo
    padrão de mercado costuma estar incluído"* é trocar o contrato pela média do
    mercado — e a linha publicada pode dizer exatamente o contrário.

    ⚠️ Em QUALQUER plano, de propósito: a pergunta não é *"o plano dele tem"*
    (isso é `buscar_servico`), é *"nós temos o que essa seguradora diz"*.
    """
    cliente = _db(db)
    planos = planos_publicados(insurer_key, ramo, produto,
                               data_emissao=data_emissao, db=cliente)
    if not planos:
        return False
    achadas = (
        cliente.table(TABELA_SERVICOS)
        .select("id")
        .in_("plano_id", [str(p["id"]) for p in planos])
        .eq("servico", str(servico))
        .eq("curadoria", "publicado")
        .limit(1)
        .execute()
    ).data or []
    return bool(achadas)


def buscar_servico(
    insurer_key: str,
    ramo: str,
    produto: str,
    plano: str,
    servico: str,
    *,
    data_emissao: Any = None,
    db: Any = None,
) -> Optional[Dict[str, Any]]:
    """A linha publicada deste serviço, neste plano — ou `None`.

    🔴 `None` significa *"não sabemos ainda"*, nunca *"não cobre"*. Quem
    transforma `None` em texto é a unidade B, e o guarda M-B1 prova a diferença.

    🔴 E `None` TAMBÉM quando sobra mais de um plano com o mesmo nome vigente na
    data: `planos[0]` escolhia por ordem de nível, isto é, por acaso. Duas
    vigências do mesmo plano dizem coisas diferentes sobre o mesmo serviço, e
    responder a do acaso é o pior dos dois mundos — parece certeza.
    """
    cliente = _db(db)
    planos = [
        p
        for p in planos_publicados(insurer_key, ramo, produto,
                                   data_emissao=data_emissao, db=cliente)
        if str(p.get("plano")) == str(plano)
    ]
    if len(planos) > 1:
        logger.info("[base-planos] %s planos homonimos vigentes: nao escolho por acaso",
                    len(planos))
        return None
    if not planos:
        return None
    r = (
        cliente.table(TABELA_SERVICOS)
        .select("*")
        .eq("plano_id", planos[0]["id"])
        .eq("servico", str(servico))
        .eq("curadoria", "publicado")
        .limit(1)
        .execute()
    ).data or []
    return r[0] if r else None


def existe_plano_superior(plano: Dict[str, Any], *, db: Any = None) -> bool:
    """Há plano publicado de nível maior no mesmo produto?

    É o que autoriza o gancho comercial *"existe um plano acima do seu"*. Com o
    nível máximo, o gancho é mentira — M-B3 tem o par de controle.
    """
    if not plano:
        return False
    irmaos = planos_publicados(
        plano.get("insurer_key", ""), plano.get("ramo", ""), plano.get("produto"), db=db
    )
    return any(int(p.get("nivel") or 0) > int(plano.get("nivel") or 0) for p in irmaos)


def cobertura_por_seguradora_e_ramo(*, db: Any = None) -> Dict[Tuple[str, str], Dict[str, int]]:
    """A régua da unidade D: `{(insurer_key, ramo): {planos_…, servicos_…}}`.

    🔴 CONTA SEGURADORA × RAMO, nunca linhas. 40 linhas de um ramo só não são
    cobertura: são um ramo só, bem descrito. Contar linhas faria a régua mentir
    para cima — é o defeito que M-D1 guarda.

    ⛔ Não aceita `company_id` (a base é global). Chamar duas vezes, de duas
    corretoras, dá o MESMO resultado — e é isso que M-A4 prova.
    """
    cliente = _db(db)
    planos = (
        cliente.table(TABELA_PLANOS)
        .select("id, insurer_key, ramo")
        .eq("curadoria", "publicado")
        .execute()
    ).data or []
    por_plano = {str(p["id"]): (str(p["insurer_key"]), str(p["ramo"])) for p in planos}

    fora: Dict[Tuple[str, str], Dict[str, int]] = {}
    for chave in por_plano.values():
        fora.setdefault(chave, {"planos_publicados": 0, "servicos_publicados": 0})
        fora[chave]["planos_publicados"] += 1

    if por_plano:
        servicos = (
            cliente.table(TABELA_SERVICOS)
            .select("plano_id")
            .eq("curadoria", "publicado")
            .in_("plano_id", list(por_plano))
            .execute()
        ).data or []
        for s in servicos:
            chave = por_plano.get(str(s.get("plano_id")))
            if chave:
                fora[chave]["servicos_publicados"] += 1
    return fora


# ---------------------------------------------------------------------------
# Manutenção — §7.4: o documento mudou, a linha volta para a fila
# ---------------------------------------------------------------------------
def derrubar_para_proposto(
    documento_id: str, motivo: str = "content_hash mudou", *, db: Any = None
) -> Dict[str, int]:
    """As linhas `publicado` daquele documento voltam a `proposto`, com o motivo.

    🔴 **Não apaga e não deixa publicado em silêncio** (SPEC §7.4). A resposta de
    ontem pode ter sido certa e a de hoje já não ser: a linha continua existindo
    (com o trecho e a página que a originaram), mas sai do caminho que chega ao
    segurado até que uma pessoa a revise de novo.

    🔴 `revisado_por`/`revisado_em` são **preservados**, e o motivo é gravado em
    `condicao` com o prefixo `[revisar]`. A escolha está escrita porque a
    alternativa (limpar o revisor) apagaria a informação de quem tinha aprovado
    a linha — que é justamente quem deve ser chamado para reconferir. E o CHECK
    `servico_publicado_foi_revisado` só vale para `curadoria='publicado'`, de
    modo que manter o revisor numa linha `proposto` não fere trava nenhuma.

    Devolve `{"planos": n, "servicos": n}` — contagem, nunca conteúdo.
    """
    cliente = _db(db)
    carimbo = "[revisar %s] %s" % (_agora()[:10], str(motivo or "").strip())
    fora = {"planos": 0, "servicos": 0}

    planos = (
        cliente.table(TABELA_PLANOS)
        .select("id")
        .eq("documento_id", str(documento_id))
        .eq("curadoria", "publicado")
        .execute()
    ).data or []
    for p in planos:
        cliente.table(TABELA_PLANOS).update(
            {"curadoria": "proposto", "updated_at": _agora()}
        ).eq("id", str(p["id"])).execute()
        fora["planos"] += 1

    servicos = (
        cliente.table(TABELA_SERVICOS)
        .select("id, condicao")
        .eq("documento_id", str(documento_id))
        .eq("curadoria", "publicado")
        .execute()
    ).data or []
    for s in servicos:
        antiga = str(s.get("condicao") or "").strip()
        cliente.table(TABELA_SERVICOS).update(
            {
                "curadoria": "proposto",
                "condicao": (carimbo + (" | " + antiga if antiga else "")),
                "updated_at": _agora(),
            }
        ).eq("id", str(s["id"])).execute()
        fora["servicos"] += 1

    if fora["planos"] or fora["servicos"]:
        logger.info(
            "[base-planos] documento %s mudou: %s plano(s) e %s servico(s) voltaram para a fila (%s)",
            documento_id, fora["planos"], fora["servicos"], motivo,
        )
    return fora


# ---------------------------------------------------------------------------
# A fila de curadoria — o que a tela da unidade D mostra
# ---------------------------------------------------------------------------
def fila_de_curadoria(
    *, limite: int = 50, curadorias: Tuple[str, ...] = ("proposto",), db: Any = None
) -> List[Dict[str, Any]]:
    """As linhas de serviço à espera de gente, com o plano delas junto.

    ⛔ **Não devolve o trecho.** O trecho não é gravado (a base guarda só o
    `trecho_hash`): quem quiser mostrá-lo lê a fonte arquivada na hora, pelo
    mesmo `conferir_pagina`/`texto_da_pagina` — é o que garante que o que a
    pessoa lê na tela é o que está no PDF, e não uma cópia que envelheceu.
    """
    cliente = _db(db)
    linhas: List[Dict[str, Any]] = []
    for estado in curadorias:
        linhas += (
            cliente.table(TABELA_SERVICOS)
            .select("*")
            .eq("curadoria", str(estado))
            .limit(int(limite))
            .execute()
        ).data or []
    if not linhas:
        return []

    ids = {str(l.get("plano_id")) for l in linhas if l.get("plano_id")}
    planos = (
        cliente.table(TABELA_PLANOS).select("*").in_("id", list(ids)).execute()
    ).data or [] if ids else []
    por_id = {str(p["id"]): p for p in planos}

    fora: List[Dict[str, Any]] = []
    for l in linhas[: int(limite)]:
        p = por_id.get(str(l.get("plano_id"))) or {}
        fora.append({
            "id": l.get("id"),
            "insurer_key": p.get("insurer_key"),
            "ramo": p.get("ramo"),
            "produto": p.get("produto"),
            "plano": p.get("plano"),
            "nivel": p.get("nivel"),
            # 🔴 o PLANO aparece na linha porque publicar o serviço publica o
            # plano pai (`publicar_servico`): quem clica precisa ter lido os dois.
            "plano_id": p.get("id"),
            "plano_curadoria": p.get("curadoria"),
            "plano_pagina": p.get("pagina"),
            "vigencia_inicio": p.get("vigencia_inicio"),
            "servico": l.get("servico"),
            "coberto": l.get("coberto"),
            "limite_valor": l.get("limite_valor"),
            "limite_unidade": l.get("limite_unidade"),
            "limite_texto": l.get("limite_texto"),
            "carencia_dias": l.get("carencia_dias"),
            "condicao": l.get("condicao"),
            "confianca": l.get("confianca"),
            "curadoria": l.get("curadoria"),
            "documento_id": l.get("documento_id"),
            "pagina": l.get("pagina"),
            "trecho_hash": l.get("trecho_hash"),
        })
    return fora


def rejeitar_servico(
    servico_id: str, revisado_por: Any, motivo: str, *, db: Any = None
) -> Dict[str, Any]:
    """Rejeita uma linha. 🔴 Exige revisor E motivo.

    ⚠️ Rejeitar sem motivo produz uma fila que ninguém consegue aprender a
    melhorar: o extrator continua propondo o mesmo erro, e a pessoa continua
    recusando à mão, para sempre.
    """
    revisor = _exigir_revisor(revisado_por, "rejeitar")
    if not str(motivo or "").strip():
        raise BaseDePlanosRecusa(
            "rejeitar sem motivo: a fila só melhora se o erro ficar escrito"
        )
    antiga = (
        _db(db).table(TABELA_SERVICOS).select("condicao").eq("id", str(servico_id))
        .limit(1).execute()
    ).data or []
    anterior = str((antiga[0] if antiga else {}).get("condicao") or "").strip()
    patch = {
        "curadoria": "rejeitado",
        "revisado_por": revisor,
        "revisado_em": _agora(),
        "condicao": "[rejeitado] %s" % str(motivo).strip()
                    + (" | " + anterior if anterior else ""),
        "updated_at": _agora(),
    }
    r = _db(db).table(TABELA_SERVICOS).update(patch).eq("id", str(servico_id)).execute()
    return (r.data or [{}])[0]


def para_rascunho(
    servico_id: str, motivo: str, *, db: Any = None
) -> Dict[str, Any]:
    """O VERIFICADOR reprova: a linha vai para `rascunho` COM o motivo.

    🔴 Este é o único movimento de estado que a máquina faz, e ele é **para
    baixo**. Subir é ato humano (`publicar_servico`) — SPEC §7.1: *"o
    verificador não é o revisor: ele só reprova, nunca aprova"*.
    """
    if not str(motivo or "").strip():
        raise BaseDePlanosRecusa("reprovar sem motivo não ensina nada a ninguém")
    patch = {
        "curadoria": "rascunho",
        "condicao": "[reprovado] %s" % str(motivo).strip(),
        "updated_at": _agora(),
    }
    r = _db(db).table(TABELA_SERVICOS).update(patch).eq("id", str(servico_id)).execute()
    return (r.data or [{}])[0]


def corrigir_vigencia_do_plano(
    plano_id: str, vigencia_inicio: Any, *, motivo: str = "", db: Any = None
) -> Dict[str, Any]:
    """Conserta a `vigencia_inicio` de um plano — **só em `proposto`**.

    🔴 POR QUE ISTO EXISTE, E POR QUE SÓ EM `proposto`
    ==================================================
    📊 18/09/2026: a onda 1 gravou `vigencia_inicio = date.today()` em **38 de
    38** planos. A vigência entra nas chaves únicas: rodar a onda no dia seguinte
    não atualizaria nada — **duplicaria a base inteira**, com duas vigências
    dizendo a mesma coisa sobre o mesmo produto, e a leitura teria de escolher
    uma por acaso (que é o que `buscar_servico` agora se recusa a fazer).

    ⛔ Em linha `publicado`, mudar a vigência mudaria a resposta que já foi
    revisada por uma pessoa, sem que ela soubesse. Se for preciso, o caminho é o
    de sempre: `derrubar_para_proposto` e nova revisão.
    """
    cliente = _db(db)
    atual = (
        cliente.table(TABELA_PLANOS).select("id, curadoria, vigencia_inicio")
        .eq("id", str(plano_id)).limit(1).execute()
    ).data or []
    if not atual:
        raise BaseDePlanosRecusa("plano %r não existe" % str(plano_id))
    if str(atual[0].get("curadoria")) != "proposto":
        raise BaseDePlanosRecusa(
            "vigência só se corrige em `proposto`; este plano está %r — em "
            "`publicado` isso mudaria, sem aviso, uma resposta já revisada"
            % atual[0].get("curadoria")
        )
    nova = _como_data(vigencia_inicio)
    if nova is None:
        raise BaseDePlanosRecusa("vigencia_inicio inválida: %r" % (vigencia_inicio,))
    patch = {"vigencia_inicio": nova.isoformat(), "updated_at": _agora()}
    r = cliente.table(TABELA_PLANOS).update(patch).eq("id", str(plano_id)).execute()
    logger.info("[base-planos] vigencia do plano %s corrigida (%s)", plano_id, motivo or "-")
    return (r.data or [{}])[0]


def renomear_plano_proposto(
    plano_id: str, *, produto: Optional[str] = None, plano: Optional[str] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """Normaliza `produto`/`plano` de uma linha **`proposto`**.

    📊 A onda 1 gravou `produto` com nome de arquivo ("… CC-RESIDENCIAL POP.pdf")
    e com caixas diferentes para a mesma coisa ('Mapfre condominio' ×
    'Mapfre Condominio'). Duas caixas do mesmo produto são dois produtos para a
    chave — e o gancho *"existe um plano acima do seu"* nunca acha o superior,
    porque ele está no "outro" produto.
    """
    cliente = _db(db)
    atual = (
        cliente.table(TABELA_PLANOS).select("id, curadoria").eq("id", str(plano_id))
        .limit(1).execute()
    ).data or []
    if not atual:
        raise BaseDePlanosRecusa("plano %r não existe" % str(plano_id))
    if str(atual[0].get("curadoria")) != "proposto":
        raise BaseDePlanosRecusa("renomear só em `proposto`, está %r" % atual[0].get("curadoria"))
    patch: Dict[str, Any] = {"updated_at": _agora()}
    if produto:
        patch["produto"] = str(produto)
    if plano:
        patch["plano"] = str(plano)
    r = cliente.table(TABELA_PLANOS).update(patch).eq("id", str(plano_id)).execute()
    return (r.data or [{}])[0]


def plano_para_rascunho(plano_id: str, motivo: str, *, db: Any = None) -> Dict[str, Any]:
    """O irmão de `para_rascunho`, para o PLANO. Só desce; nunca sobe."""
    if not str(motivo or "").strip():
        raise BaseDePlanosRecusa("reprovar plano sem motivo não ensina nada a ninguém")
    patch = {"curadoria": "rascunho", "updated_at": _agora()}
    r = _db(db).table(TABELA_PLANOS).update(patch).eq("id", str(plano_id)).execute()
    logger.info("[base-planos] plano %s -> rascunho: %s", plano_id, motivo)
    return (r.data or [{}])[0]
