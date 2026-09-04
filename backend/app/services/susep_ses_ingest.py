# -*- coding: utf-8 -*-
"""A ingestão do SUSEP SES — SPEC-094.1 · BLOCO B. **A primeira fonte EXTERNA.**

🔴 Quem roda isto é o **WORKER**, sob lease com heartbeat, e não o tick: o tick
só AGENDA, com o molde de **PLATAFORMA** (`intelligence.cluster_demand`,
`tick.py:148`, `escopo="plataforma"`). Com o molde por corretora seriam N
downloads do mesmo arquivo público de 571 MB — um por casa, todo domingo.

## O que este módulo faz, e o tamanho de cada coisa

```
571.756.724 bytes   o ZIP inteiro, 40 arquivos          ⛔ nunca em memória
136.068.656 bytes   Ses_seguros.csv, 1.801.731 linhas   ← o único que se lê inteiro
     47.809 bytes   Ses_cias + Ses_ramos + grupos       ← os domínios
     ~poucos MB     o AGREGADO por ano                  ← o que vai ao MinIO
```

📊 Tudo medido em 03/09/2026 e escrito em
[`docs/canon/providers/susep/SES-CENSO.md`](../../../docs/canon/providers/susep/SES-CENSO.md).

## As quatro armadilhas medidas, e onde cada uma é tratada

```
latin-1        🔴 `utf-8` estoura em "PREVIDÊNCIA"        _abrir_membro
vírgula        🔴 `float("350407,58")` levanta ValueError  _numero
padding        🔴 os CÓDIGOS de domínio vêm "04600     "   _codigo
negativo       🔴 `sinistro_ocorrido` pode ser NEGATIVO    Linha.estorno
```

🔴 **O negativo é estorno de provisão, e não ruído.** 📊 Porto, ramo 0520,
202605: −53.790,44. Truncar em zero inventa um sinistro que não houve — então o
valor é PRESERVADO e a linha sai marcada. Quem soma decide; quem lê vê a marca.

⚠️ E a sinistralidade é `sinistro_ocorrido / premio_ganho`: as duas pontas do
MESMO regime de competência. `premio_direto` é emissão e `sinistro_direto` é
pago — misturar regimes devolve um número plausível e errado, e não trava
(CLAUDE.md §9.5).

## Memória: por que a leitura é linha a linha, e não `read()`

`zipfile.ZipFile.open` devolve um **stream** do membro, descomprimido sob
demanda. Ler `Ses_seguros.csv` com `.read()` colocaria 136 MB de bytes mais o
texto decodificado no processo — num contêiner que também serve o chat. O laço
abaixo mantém em memória só o **agregado**, que é `(coenti × damesano × coramo)`
— 💭 poucos MB — e o pico medido está no relatório do BLOCO B.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "URL_DA_BASE", "PREFIXO_NO_MINIO", "MEMBRO_DO_FATO", "MEMBROS_DE_DOMINIO",
    "Linha", "agregar", "escrever_csv", "ingerir", "chave_do_ano",
    "CHAVE_DO_MANIFESTO", "baixar_para_arquivo",
]

#: A fonte. ⛔ Sem login, sem chave, sem contrato — e por isso ela é um conector
#: público, e não uma conexão de tenant (`CAMADAS-DE-CONEXAO.md`).
URL_DA_BASE = "https://www2.susep.gov.br/download/estatisticas/BaseCompleta.zip"

#: Onde o AGREGADO mora. Um prefixo, no bucket único do `MinioService`.
PREFIXO_NO_MINIO = "susep/ses"
CHAVE_DO_MANIFESTO = f"{PREFIXO_NO_MINIO}/manifest.json"

#: 🔴 O ÚNICO membro grande que se abre. Os outros 39 nunca são tocados —
#: `SES_Balanco.csv` sozinho tem 743 MB.
MEMBRO_DO_FATO = "Ses_seguros.csv"
#: Os domínios, que somam 48 KB. `Ses_diversos.csv` traz a competência final.
MEMBROS_DE_DOMINIO = ("Ses_cias.csv", "Ses_ramos.csv", "ses_gruposramos.csv",
                      "Ses_diversos.csv")

#: 💭 De quanto em quanto tempo o laço reporta progresso. Não muda resultado.
_PASSO_DO_LOG = 400_000


def chave_do_ano(ano: Any) -> str:
    return f"{PREFIXO_NO_MINIO}/{ano}.csv"


# --------------------------------------------------------------------------
# As três conversões que o censo mediu
# --------------------------------------------------------------------------
def _codigo(v: Any) -> str:
    """🔴 `.strip()` SEMPRE. 📊 Os códigos das tabelas de domínio vêm com padding
    à direita, largura fixa (`"04600     "`), e no FATO vêm sem. Casar chave sem
    isto devolve **zero linhas, em silêncio** — que é o modo de falha caro."""
    return str(v or "").strip()


def _numero(v: Any) -> float:
    """🔴 Decimal por VÍRGULA. 📊 `float("350407,58")` levanta `ValueError`.

    ⚠️ E o vazio devolve `0.0` **de propósito, e só aqui**: nesta base a célula
    vazia significa *"não houve movimento nesta competência"*, e não *"a fonte
    não expõe"* — a granularidade é `(entidade × mês × ramo)`, e a linha só
    existe porque houve lançamento. O `UNAVAILABLE` do CBIM vale para a carteira
    da corretora, onde a ausência é da FONTE.
    """
    s = str(v or "").strip()
    if not s:
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Linha:
    """Uma célula agregada: entidade × competência × ramo."""

    coenti: str
    damesano: str
    coramo: str
    premio_ganho: float = 0.0
    sinistro_ocorrido: float = 0.0
    estorno: bool = False

    @property
    def ano(self) -> str:
        return self.damesano[:4]


def _abrir_membro(zf: zipfile.ZipFile, nome: str) -> Iterator[List[str]]:
    """As linhas de um membro do ZIP, já em campos. **Stream, nunca `read()`.**

    🔴 `latin-1` e não `utf-8`: 📊 a segunda estoura em "PREVIDÊNCIA". E
    `newline=""`, porque o arquivo é CRLF e o `csv` quer decidir sozinho.
    """
    with zf.open(nome, "r") as bruto:
        texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
        leitor = csv.reader(texto, delimiter=";")
        for campos in leitor:
            if campos:
                yield campos


def _indice(cabecalho: List[str]) -> Dict[str, int]:
    return {_codigo(c).lower(): i for i, c in enumerate(cabecalho)}


def agregar(caminho_zip: str, *, anos: Optional[Iterable[Any]] = None,
            progresso: Any = None) -> Tuple[Dict[str, List[Linha]], Dict[str, Any]]:
    """`({ano: [Linha, ...]}, manifesto)` — lendo o ZIP membro a membro.

    ⛔ **Nunca carrega o CSV inteiro.** O laço é sobre um iterador do membro, e
    o que fica em memória é o dicionário agregado.

    ⚠️ `anos` recorta na ENTRADA e não na saída: 1,8 milhão de linhas cobrem
    199501→202606, e a corretora pergunta sobre os últimos trimestres. Guardar
    trinta anos de estatística para responder três meses é pagar memória por
    nada — mas o default é `None` (tudo), porque a série inteira é o que permite
    a tendência.
    """
    alvo = {str(a) for a in anos} if anos else None
    baldes: Dict[Tuple[str, str, str], Linha] = {}
    lidas = 0
    competencia_final = ""
    membros_lidos: List[str] = []

    with zipfile.ZipFile(caminho_zip) as zf:
        presentes = {i.filename for i in zf.infolist()}
        if MEMBRO_DO_FATO not in presentes:
            raise FalhaDaBase(
                f"o membro {MEMBRO_DO_FATO} nao esta no arquivo "
                f"({len(presentes)} membros) — a base mudou de forma")

        # --- a competência final, do arquivo de 76 bytes -------------------
        #
        # 🔴 Ela é LIDA, e não inferida do maior `damesano`: 📊 a página oficial
        # publica `Data_Final` e é ela que diz até onde o dado está fechado. A
        # defasagem vai ao ponteiro do Evidence Pack, porque quem lê em setembro
        # está comparando com junho.
        if "Ses_diversos.csv" in presentes:
            membros_lidos.append("Ses_diversos.csv")
            for campos in _abrir_membro(zf, "Ses_diversos.csv"):
                if len(campos) >= 2 and "final" in campos[0].strip().lower():
                    competencia_final = _codigo(campos[1])

        membros_lidos.append(MEMBRO_DO_FATO)
        iterador = _abrir_membro(zf, MEMBRO_DO_FATO)
        try:
            cabecalho = next(iterador)
        except StopIteration:
            raise FalhaDaBase(f"{MEMBRO_DO_FATO} esta vazio")
        idx = _indice(cabecalho)
        for exigida in ("damesano", "coenti", "coramo", "premio_ganho",
                        "sinistro_ocorrido"):
            if exigida not in idx:
                raise FalhaDaBase(
                    f"a coluna {exigida!r} sumiu de {MEMBRO_DO_FATO}: "
                    f"{sorted(idx)[:8]}... — o schema da fonte mudou")

        for campos in iterador:
            if len(campos) <= idx["sinistro_ocorrido"]:
                continue
            lidas += 1
            damesano = _codigo(campos[idx["damesano"]])
            if alvo is not None and damesano[:4] not in alvo:
                continue
            chave = (_codigo(campos[idx["coenti"]]), damesano,
                     _codigo(campos[idx["coramo"]]))
            premio = _numero(campos[idx["premio_ganho"]])
            sinistro = _numero(campos[idx["sinistro_ocorrido"]])
            balde = baldes.get(chave)
            if balde is None:
                balde = Linha(coenti=chave[0], damesano=chave[1], coramo=chave[2])
                baldes[chave] = balde
            balde.premio_ganho += premio
            balde.sinistro_ocorrido += sinistro
            # 🔴 O negativo é PRESERVADO e SINALIZADO. Truncar em zero inventa
            # um sinistro que não houve; esconder a marca faz o leitor achar que
            # a seguradora sinistrou pouco, quando ela ESTORNOU provisão.
            if sinistro < 0:
                balde.estorno = True
            if progresso is not None and lidas % _PASSO_DO_LOG == 0:
                progresso(lidas, len(baldes))

        for nome in MEMBROS_DE_DOMINIO:
            if nome in presentes and nome not in membros_lidos:
                # Os domínios entram para o manifesto (nome e tamanho); eles não
                # mudam o agregado — o `coenti` do fato já é a chave.
                membros_lidos.append(nome)

    por_ano: Dict[str, List[Linha]] = {}
    for linha in baldes.values():
        por_ano.setdefault(linha.ano, []).append(linha)
    for ano in por_ano:
        por_ano[ano].sort(key=lambda x: (x.coenti, x.damesano, x.coramo))

    manifesto = {
        "fonte": URL_DA_BASE,
        "competencia_final": competencia_final,
        "linhas_lidas": lidas,
        "celulas": len(baldes),
        "anos": sorted(por_ano),
        "membros_lidos": membros_lidos,
        "agregado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return por_ano, manifesto


class FalhaDaBase(RuntimeError):
    """A base pública mudou de forma. ⚠️ Tipo próprio para que o card do
    trabalhador consiga dizer *"a SUSEP mudou o arquivo"* em vez de `Exception`."""


# --------------------------------------------------------------------------
# A escrita
# --------------------------------------------------------------------------
#: 🔴 As colunas do agregado, nesta ordem. Elas são o CONTRATO entre este
#: ingestor e `providers/susep_ses_provider.py` — e a razão de estarem escritas
#: num lugar só é a de sempre: duas listas divergem no primeiro campo novo.
COLUNAS = ("coenti", "damesano", "coramo", "premio_ganho", "sinistro_ocorrido",
           "estorno")


def escrever_csv(linhas: List[Linha]) -> bytes:
    """O agregado de UM ano, em CSV utf-8 com ponto decimal.

    ⚠️ Ponto, e não vírgula: a convenção de vírgula é da FONTE, e o agregado é
    NOSSO. Propagá-la obrigaria todo leitor futuro a saber de uma decisão da
    SUSEP para ler um arquivo do AutoBrokers.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\n")
    escritor.writerow(COLUNAS)
    for linha in linhas:
        escritor.writerow([linha.coenti, linha.damesano, linha.coramo,
                           repr(round(linha.premio_ganho, 2)),
                           repr(round(linha.sinistro_ocorrido, 2)),
                           "T" if linha.estorno else "F"])
    return buffer.getvalue().encode("utf-8")


def baixar_para_arquivo(url: str, destino: str, *,
                        tamanho_do_bloco: int = 1 << 20) -> Dict[str, Any]:
    """Baixa em STREAM para disco. `{sha256, bytes, last_modified}`.

    ⛔ 571 MB **nunca** passam pela memória: o corpo é copiado em blocos de 1 MB
    e o `sha256` é calculado no caminho, sem uma segunda leitura do arquivo.

    ⚠️ Esta é a única função deste módulo que toca a rede, e ela só é chamada
    quando `caminho_local` não foi dado — que é como a prova do BLOCO B roda sem
    rede nenhuma, sobre o arquivo que o BLOCO 0 já trouxe.
    """
    import urllib.request

    marca = hashlib.sha256()
    total = 0
    ultima_modificacao = ""
    pedido = urllib.request.Request(url, headers={"User-Agent": "AutoBrokers/094.1"})
    with urllib.request.urlopen(pedido, timeout=600) as resposta:
        ultima_modificacao = str(resposta.headers.get("Last-Modified") or "")
        with open(destino, "wb") as saida:
            while True:
                bloco = resposta.read(tamanho_do_bloco)
                if not bloco:
                    break
                marca.update(bloco)
                total += len(bloco)
                saida.write(bloco)
    return {"sha256": marca.hexdigest(), "bytes": total,
            "last_modified": ultima_modificacao}


def _sha256_do_arquivo(caminho: str, tamanho_do_bloco: int = 1 << 20) -> Tuple[str, int]:
    marca = hashlib.sha256()
    total = 0
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(tamanho_do_bloco), b""):
            marca.update(bloco)
            total += len(bloco)
    return marca.hexdigest(), total


def ingerir(*, minio: Any, caminho_local: Optional[str] = None,
            url: str = URL_DA_BASE, anos: Optional[Iterable[Any]] = None,
            progresso: Any = None) -> Dict[str, Any]:
    """Baixa (ou reusa o arquivo local), agrega e grava SÓ o agregado no MinIO.

    🔴 `caminho_local` existe para que a prova rode **sem rede** sobre o arquivo
    que o censo do BLOCO 0 já baixou — e para que uma reingestão não puxe 571 MB
    de novo. Quando ele é dado, nada sai na rede.

    Devolve o manifesto gravado, que é o que o card do trabalhador
    **Censo SUSEP** lê para dizer quando o dado do mercado foi atualizado.
    """
    temporario = None
    try:
        if caminho_local and os.path.exists(caminho_local):
            caminho = caminho_local
            marca, tamanho = _sha256_do_arquivo(caminho)
            origem = {"sha256": marca, "bytes": tamanho, "last_modified": "",
                      "de": "arquivo local"}
        else:
            temporario = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            temporario.close()
            caminho = temporario.name
            origem = dict(baixar_para_arquivo(url, caminho), de=url)

        por_ano, manifesto = agregar(caminho, anos=anos, progresso=progresso)

        objetos = []
        for ano, linhas in sorted(por_ano.items()):
            chave = chave_do_ano(ano)
            minio.put_bytes(chave, escrever_csv(linhas), "text/csv")
            objetos.append({"ano": ano, "objeto": chave, "celulas": len(linhas)})

        manifesto = dict(manifesto, **{
            "sha256_do_zip": origem.get("sha256", ""),
            "bytes_do_zip": origem.get("bytes", 0),
            "last_modified": origem.get("last_modified", ""),
            "origem": origem.get("de", ""),
            "objetos": objetos,
        })
        minio.put_bytes(
            CHAVE_DO_MANIFESTO,
            json.dumps(manifesto, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json")
        logger.info("[SES] %d celula(s) em %d ano(s); competencia final %s",
                    manifesto["celulas"], len(objetos),
                    manifesto.get("competencia_final") or "?")
        return manifesto
    finally:
        # ⚠️ O temporário morre mesmo em falha. 571 MB esquecidos em `/tmp` num
        # contêiner é o tipo de defeito que só aparece no terceiro domingo.
        if temporario is not None:
            try:
                os.unlink(temporario.name)
            except OSError:
                pass


# ==========================================================================
# O WORKFLOW — a tomada, no MESMO registro da SPEC-055
# ==========================================================================
#
# ⚠️ Aqui é só a TOMADA: o corpo são as funções puras acima, testáveis sem Work
# Run montado. É o mesmo desenho de `claims_shadow_digest` (workflows.py:314).
try:  # pragma: no cover - o registro depende do pacote de workflows
    from app.services.intelligence.workflows import registrar_workflow  # type: ignore
    from app.services.work.workflows import executar_passo  # type: ignore
except Exception:  # noqa: BLE001
    registrar_workflow = None  # type: ignore
    executar_passo = None  # type: ignore


if registrar_workflow is not None:  # pragma: no branch

    @registrar_workflow("intelligence.susep_ses_ingest")
    async def ingerir_susep_ses(ctx: dict) -> str:
        """Batch de PLATAFORMA, semanal. ⛔ Nenhum dado de corretora entra aqui.

        🔴 Escopo `plataforma` e cadência de 168 h: a estatística pública é UMA
        para todas as corretoras. Com o molde por tenant seriam N downloads do
        mesmo arquivo, e a Nª corretora pagaria a mesma banda que a primeira.
        """
        from app.services.minio_service import MinioService

        payload = (ctx.get("input_payload") or {}) if isinstance(ctx, dict) else {}

        async def _ingerir() -> Any:
            import asyncio

            return await asyncio.to_thread(
                ingerir,
                minio=MinioService(),
                caminho_local=payload.get("caminho_local"),
                url=payload.get("url") or URL_DA_BASE,
                anos=payload.get("anos"))

        r = await executar_passo(ctx, step_key="ingerir", ordinal=1,
                                 nome="Baixar e agregar o censo do mercado",
                                 step_type="analysis", fn=_ingerir)
        r = r or {}
        return ("%s celula(s) do mercado em %d ano(s); competencia final %s."
                % (r.get("celulas", 0), len(r.get("objetos") or ()),
                   r.get("competencia_final") or "?"))
