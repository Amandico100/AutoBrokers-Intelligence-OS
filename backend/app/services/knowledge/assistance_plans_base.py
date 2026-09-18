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

#: O caminho RELATIVO do vocabulário dentro do repositório. Um só, para o
#: resolvedor e para a mensagem de erro não poderem divergir.
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

    ① `AUTOBROKERS_REPO_ROOT` (se o ambiente declarar a raiz);
    ② **subindo** a árvore a partir deste arquivo até achar `docs/canon`;
    ③ o caminho histórico `parents[4]`, que continua valendo na árvore normal.

    ⚠️ Subir procurando `docs/canon` (e não contar `parents[n]`) é o que faz o
    módulo funcionar de qualquer `cwd` e sobreviver a mover a pasta um nível.
    """
    import os

    fora: List[Path] = []
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
        "o vocabulário de serviços (%s) não está em nenhum destes caminhos: %s"
        % ("/".join(_RELATIVO_DO_VOCABULARIO), [str(c) for c in candidatos])
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
        with open(caminho_do_vocabulario(), "r", encoding="utf-8") as fh:
            _VOCABULARIO = json.load(fh)
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


def publicar_servico(servico_id: str, revisado_por: Any, *, db: Any = None) -> Dict[str, Any]:
    """Publica uma linha. 🔴 Sem revisor, recusa ANTES do banco — e o banco recusa de novo."""
    if not revisado_por:
        raise RevisorObrigatorio(
            "publicar sem `revisado_por` é o que esta base existe para impedir: "
            "aprovar o PDF não é aprovar 'guincho até 200 km'"
        )
    patch = {
        "curadoria": "publicado",
        "revisado_por": str(revisado_por),
        "revisado_em": _agora(),
        "updated_at": _agora(),
    }
    r = _db(db).table(TABELA_SERVICOS).update(patch).eq("id", str(servico_id)).execute()
    return (r.data or [{}])[0]


def publicar_plano(plano_id: str, revisado_por: Any, *, db: Any = None) -> Dict[str, Any]:
    """O irmão de `publicar_servico`, para o plano."""
    if not revisado_por:
        raise RevisorObrigatorio("publicar plano sem `revisado_por`")
    patch = {
        "curadoria": "publicado",
        "revisado_por": str(revisado_por),
        "revisado_em": _agora(),
        "updated_at": _agora(),
    }
    r = _db(db).table(TABELA_PLANOS).update(patch).eq("id", str(plano_id)).execute()
    return (r.data or [{}])[0]


# ---------------------------------------------------------------------------
# Leitura — só o que está PUBLICADO chega ao segurado
# ---------------------------------------------------------------------------
def planos_publicados(
    insurer_key: str, ramo: str, produto: Optional[str] = None, *, db: Any = None
) -> List[Dict[str, Any]]:
    """Os planos publicados, **ordenados por `nivel`** (1 = o mais básico)."""
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
    return (q.order("nivel").execute()).data or []


def buscar_servico(
    insurer_key: str,
    ramo: str,
    produto: str,
    plano: str,
    servico: str,
    *,
    db: Any = None,
) -> Optional[Dict[str, Any]]:
    """A linha publicada deste serviço, neste plano — ou `None`.

    🔴 `None` significa *"não sabemos ainda"*, nunca *"não cobre"*. Quem
    transforma `None` em texto é a unidade B, e o guarda M-B1 prova a diferença.
    """
    cliente = _db(db)
    planos = [
        p
        for p in planos_publicados(insurer_key, ramo, produto, db=cliente)
        if str(p.get("plano")) == str(plano)
    ]
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
    if not revisado_por:
        raise RevisorObrigatorio("rejeitar sem `revisado_por`")
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
        "revisado_por": str(revisado_por),
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
