# -*- coding: utf-8 -*-
"""Cliente do registro oficial da SUSEP — catálogo OData + REP2. SPEC-070 §3.

O que este módulo é, e o que ele não é
--------------------------------------
Ele é um **adaptador de fonte**, do mesmo tipo que `research/firecrawl.py`:
fala com um servidor de fora e devolve dado estruturado. Ele **não** é runtime,
scheduler, executor, registry nem um segundo pipeline de conhecimento — o
CLAUDE.md §5 proíbe isso, e com razão. Quem parte o documento, indexa e grava é
o `insurance_corpus.py`, que continua sendo o único dono desse trabalho e é
quem consome este módulo.

Nada aqui escreve no banco, no Qdrant ou no MinIO. Entra número de processo,
sai `ConsultaProduto`.

Por que a fonte é a SUSEP e não o site da seguradora
----------------------------------------------------
📊 Medido em 08/08/2026 (SPEC-070 §3.4): HDI devolve 500, Allianz devolve 403
para robô, e a Tokio devolve 200 com 1 KB — uma página de erro fingindo
sucesso. O site é marketing; o REP2 é registro legal. E o REP2 diz **qual
versão vale hoje**, que é a pergunta que o acervo não sabia responder: 📊 12 de
13 documentos indexados eram versões revogadas.

A regra da vigência, sem inferência
-----------------------------------
    VIGENTE = produto com Situação "Passível de comercialização"
              + versão com Data de Fim de Comercialização VAZIA

📊 A linha vigente também vem com `font-weight:bold` no HTML. O negrito é
**corroboração, não regra**: a autoridade é a data de fim vazia, porque estilo
de CSS muda numa manutenção do portal e ninguém avisa. Quando os dois
discordam, a divergência é registrada em `divergencia_negrito` em vez de ser
escolhida em silêncio.

As três armadilhas — cada uma tem um guarda com nome
-----------------------------------------------------
**1. HTTP 200 com página vazia.** 📊 8 de 28 consultas em 08/08/2026 devolveram
o formulário em branco com status 200, sem mensagem de erro nenhuma: sem
"Nenhum resultado", sem `alert`, sem nada. Só o bloco "Detalhes do Produto" que
não veio.

    🔴 "Não consegui perguntar" NUNCA pode virar "não mudou".

Esse é o defeito que já custou caro neste projeto — existe um commit na branch
chamado *"não consegui abrir não pode se disfarçar de deve ser legado"*. Por
isso `ConsultaProduto.estado` tem três valores e não dois:

    VIGENTE_ENCONTRADA · PRODUTO_MORTO · INDETERMINADO

e `comparar_com(nossa_data)` devolve `INDETERMINADO` quando não deu para
perguntar — **nunca** `EM_DIA`. Não existe caminho no código que produza
"em dia" por omissão: `EM_DIA` só nasce de uma data vigente lida do HTML.

**2. Validar a contagem, não o status.** 📊 O catálogo tem 31.871 registros.
Um 200 com 12 linhas é falha silenciosa do OData, e `carregar_catalogo`
levanta `CatalogoSuspeito` abaixo de `PISO_REGISTROS`.

**3. O endpoint já mudou de caminho uma vez** (`olinda-ide` → `olinda`) e o host
antigo caiu sem aviso. Por isso `carregar_catalogo` guarda o último dump bom em
disco e sabe voltar para ele — com a data do que serviu, para que ninguém
confunda cache com resposta de hoje.

⚠️ E `$top`, `$filter` e `$skip` devolvem **HTTP 500**. 📊 Reconfirmado em
08/08/2026: três variantes, três 500. Só o dump inteiro funciona.

Medições próprias, 08/08/2026 (reverificação da SPEC-070 §3)
-------------------------------------------------------------
📊 catálogo ......... 200 · 4.542.087 bytes · 1.091 ms · 31.871 registros
📊 REP2 Porto auto .. 200 · 95.861 bytes · 1.828 ms (2ª chamada) · 41 versões
📊 REP2 vazio ....... 200 · 11.545 bytes · 1.152 ms · sem "Detalhes do Produto"
📊 PDF CG144 ........ 200 · 1.601.187 bytes · 833 ms · application/pdf
"""

from __future__ import annotations

import csv
import html as _html
import io
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Optional, Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endereços
# ---------------------------------------------------------------------------

HOST_REP2 = "www2.susep.gov.br"
HOST_DADOS = "dados.susep.gov.br"

BASE_REP2 = f"https://{HOST_REP2}/safe/menumercado/REP2/Produto.aspx"
URL_CONSULTA = f"{BASE_REP2}/Consultar"
URL_DOWNLOAD = f"{BASE_REP2}/DownloadConsultaPublica"

# ⚠️ O caminho já mudou de `olinda-ide` para `olinda` uma vez, e o host antigo
# caiu sem aviso. Se este 404ar, o candidato seguinte é o primeiro lugar a
# olhar — mas nunca troque sem medir a contagem (armadilha 2).
URL_CATALOGO = (
    f"https://{HOST_DADOS}/olinda/servico/produtos/versao/v1/odata/"
    "DadosProdutos?$format=text/csv"
)

# O PDF do CG140 tem 1,6 MB; o teto do guard padrão (5 MB) cortaria condições
# gerais grandes. 40 MB cobre o catálogo de 4,5 MB e sobra para o maior PDF.
TETO_RESPOSTA_BYTES = 40_000_000


def _guard():
    """Carrega o `egress_guard` da SPEC-054 — só quando há saída de verdade.

    A importação é tardia de propósito. `app.core.__init__` puxa a
    configuração inteira (pydantic-settings, Supabase, chaves), e o parser
    desta casa precisa ser importável **sem nada disso** para que o teste possa
    alimentá-lo com o HTML real e conferir os três estados offline. Se o
    parser só rodasse com o ambiente de produção montado, o controle da
    página vazia deixaria de ser barato — e o controle que custa caro é o que
    para de ser rodado.

    Nenhuma chamada de rede escapa daqui: as três funções que saem
    (`consultar`, `baixar`, `carregar_catalogo`) passam por este guard.
    """
    from app.core import egress_guard as eg
    politica = eg.EgressPolicy.from_iterable(
        [HOST_REP2, HOST_DADOS], max_response_bytes=TETO_RESPOSTA_BYTES)
    return eg, politica

TIMEOUT_CONEXAO = 10.0
TIMEOUT_LEITURA = 120.0     # 📊 a primeira consulta do dia levou 10,7 s
TIMEOUT_CATALOGO = 180.0    # 4,5 MB

# 📊 31.871 registros em 08/08/2026. O piso existe para que um 200 com 12
# linhas nunca passe por catálogo. Ver armadilha 2.
PISO_REGISTROS = 30_000

COLUNAS_CATALOGO = ("tipoproduto", "entnome", "cnpj", "numeroprocesso", "ramo", "subramo")

SITUACAO_VIVA = "passível de comercialização"


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

class SusepIndisponivel(RuntimeError):
    """Rede, timeout ou erro do portal. Sempre tratável pelo chamador."""


class CatalogoSuspeito(RuntimeError):
    """200 com poucas linhas. Ver armadilha 2 — status não é evidência."""


# ---------------------------------------------------------------------------
# O número de processo
# ---------------------------------------------------------------------------

# 5 dígitos . 6 dígitos / 4 dígitos - 2 dígitos = 17 dígitos.
FORMATO_CANONICO = re.compile(r"^\d{5}\.\d{6}/\d{4}-\d{2}$")
DIGITOS_ESPERADOS = 17


@dataclass(frozen=True)
class Processo:
    """O que sabemos sobre um número de processo antes de perguntar à SUSEP.

    📊 3 de 31 processos gravados em `normative_documents` não casam com o
    formato canônico. Dois problemas diferentes, com destinos diferentes:

        porto  auto         `15414.100.233/2004-59`  ponto a mais → normaliza
        tokio  auto         `15414.100335/2004`      faltam 2 dígitos
        tokio  empresarial  `15414.900584/2018`      faltam 2 dígitos

    O primeiro se conserta sozinho: 17 dígitos, só a pontuação errada.
    Os outros dois não têm o dígito verificador — e **inventar dígito é pior
    que não ter**, porque um processo válido de outro produto responde 200 e o
    acervo passa a acompanhar o contrato errado. Eles saem daqui como
    `precisa_reparo=True` e vão para `reparar_pelo_catalogo`.
    """

    bruto: str
    formatado: Optional[str]
    digitos: str
    motivo: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.formatado is not None

    @property
    def precisa_reparo(self) -> bool:
        return self.formatado is None


def analisar_processo(bruto: Optional[str]) -> Processo:
    """Normaliza para `NNNNN.NNNNNN/AAAA-DD` — só dígitos, 17 posições."""
    cru = (bruto or "").strip()
    digitos = re.sub(r"\D", "", cru)

    if not digitos:
        return Processo(cru, None, "", "sem_digitos")
    if len(digitos) < DIGITOS_ESPERADOS:
        return Processo(cru, None, digitos,
                        f"faltam_{DIGITOS_ESPERADOS - len(digitos)}_digitos")
    if len(digitos) > DIGITOS_ESPERADOS:
        return Processo(cru, None, digitos,
                        f"sobram_{len(digitos) - DIGITOS_ESPERADOS}_digitos")

    formatado = f"{digitos[:5]}.{digitos[5:11]}/{digitos[11:15]}-{digitos[15:]}"
    return Processo(cru, formatado, digitos, None)


def normalizar_processo(bruto: Optional[str]) -> Optional[str]:
    """Atalho: devolve o número canônico, ou `None` quando não dá para consertar."""
    return analisar_processo(bruto).formatado


# ---------------------------------------------------------------------------
# A lista explícita de reparo
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PendenciaDeReparo:
    """Um processo que não normaliza, com o que basta para achá-lo no catálogo.

    🔴 Isto não é decoração: é a diferença entre "o produto sumiu" e "o número
    está truncado no nosso banco". Sem esta lista, os dois somem do mesmo jeito
    — em silêncio.
    """

    insurer_key: str
    product_line: str
    gravado: str
    entnome: str          # como aparece em `entnome` no catálogo
    ramo_prefixo: str     # o código oficial do ramo, ex.: "05"
    motivo: str


PENDENCIAS_DE_REPARO: tuple[PendenciaDeReparo, ...] = (
    PendenciaDeReparo(
        insurer_key="tokio", product_line="auto",
        gravado="15414.100335/2004",
        entnome="TOKIO MARINE SEGURADORA S.A.", ramo_prefixo="05",
        motivo="gravado sem o dígito verificador — 15 dígitos, faltam 2",
    ),
    PendenciaDeReparo(
        insurer_key="tokio", product_line="empresarial",
        gravado="15414.900584/2018",
        entnome="TOKIO MARINE SEGURADORA S.A.", ramo_prefixo="01",
        motivo="gravado sem o dígito verificador — 15 dígitos, faltam 2",
    ),
)


@dataclass(frozen=True)
class Reparo:
    pendencia: PendenciaDeReparo
    candidatos: tuple[dict, ...]

    @property
    def resolvido(self) -> bool:
        """Só há reparo quando o catálogo aponta para **um** processo.

        Dois candidatos é ambiguidade, e ambiguidade aqui significa indexar o
        contrato de outro produto. Nesse caso a pendência continua aberta.
        """
        return len(self.candidatos) == 1

    @property
    def processo(self) -> Optional[str]:
        return self.candidatos[0]["numeroprocesso"] if self.resolvido else None


def reparar_pelo_catalogo(pendencia: PendenciaDeReparo,
                          catalogo: Sequence[dict]) -> Reparo:
    """Acha o processo truncado no catálogo — pelos dígitos, conferindo o nome.

    O truncamento é sempre no fim (o dígito verificador), então os dígitos que
    temos são **prefixo** dos 17 verdadeiros. O prefixo sozinho já basta na
    prática, mas o nome da seguradora e o ramo entram como confirmação: se o
    prefixo casar com um produto de outra companhia, é outro produto.

    📊 Medido em 08/08/2026 contra o dump de 31.871 registros — os dois casos
    da Tokio devolvem **exatamente um** candidato cada:
        15414.100335/2004 → 15414.100335/2004-74   (auto, ramo 05)
        15414.900584/2018 → 15414.900584/2018-68   (empresarial, ramo 01)
    E 📊 os dois recuperados respondem no REP2 com página cheia (57 KB e 42 KB),
    contra 11,5 KB de página vazia dos truncados.
    """
    alvo = re.sub(r"\D", "", pendencia.gravado)
    nome = pendencia.entnome.strip().upper()

    achados = []
    for linha in catalogo or ():
        numero = (linha.get("numeroprocesso") or "").strip()
        if not re.sub(r"\D", "", numero).startswith(alvo):
            continue
        if nome and (linha.get("entnome") or "").strip().upper() != nome:
            continue
        if pendencia.ramo_prefixo and not (linha.get("ramo") or "").strip().startswith(
                pendencia.ramo_prefixo):
            continue
        achados.append(dict(linha))

    return Reparo(pendencia, tuple(achados))


# ---------------------------------------------------------------------------
# O resultado da consulta
# ---------------------------------------------------------------------------

VIGENTE_ENCONTRADA = "vigente_encontrada"
PRODUTO_MORTO = "produto_morto"
INDETERMINADO = "indeterminado"

ESTADOS = (VIGENTE_ENCONTRADA, PRODUTO_MORTO, INDETERMINADO)

# Veredito de atraso. 🔴 Note que não existe valor "sem alteração" para o caso
# de não ter dado para perguntar — esse caso é `INDETERMINADO`, sempre.
EM_DIA = "em_dia"
ATRASADO = "atrasado"


@dataclass(frozen=True)
class Versao:
    """Uma linha da tabela "Versões"."""

    arquivo: str
    inicio: Optional[str]          # dd/mm/aaaa como veio do portal
    fim: Optional[str]
    download_id: Optional[str]
    negrito: bool = False

    @property
    def vigente(self) -> bool:
        """Data de Fim vazia. É a regra, e não depende de estilo de CSS."""
        return not (self.fim or "").strip()

    @property
    def url_download(self) -> Optional[str]:
        return f"{URL_DOWNLOAD}/{self.download_id}" if self.download_id else None

    @property
    def inicio_iso(self) -> Optional[str]:
        return _para_iso(self.inicio)


@dataclass(frozen=True)
class ConsultaProduto:
    """O que o REP2 respondeu — inclusive quando não respondeu nada."""

    estado: str
    processo: str
    motivo: Optional[str] = None
    sociedade: Optional[str] = None
    ramo_codigo: Optional[str] = None
    ramo_nome: Optional[str] = None
    subramo: Optional[str] = None
    situacao: Optional[str] = None
    versoes: tuple[Versao, ...] = ()
    vigente: Optional[Versao] = None
    divergencia_negrito: bool = False
    http_status: Optional[int] = None
    duracao_ms: int = 0
    bytes_recebidos: int = 0

    @property
    def produto_vivo(self) -> bool:
        return (self.situacao or "").strip().lower() == SITUACAO_VIVA

    def comparar_com(self, nossa_data: Any) -> str:
        """Compara a versão que temos com a vigente. **Nunca conclui por omissão.**

        🔴 Este é o método que a armadilha 1 tenta corromper. Se a consulta não
        trouxe versão vigente — página vazia, rede caída, portal fora do ar —
        a resposta é `INDETERMINADO`. Um `EM_DIA` só sai daqui quando existe
        uma data vigente lida do HTML **e** ela não é posterior à nossa.

        Sem data nossa, também é `INDETERMINADO`: não sabemos o que temos, e
        "não sei o que tenho" não é "está em dia".
        """
        if self.estado == PRODUTO_MORTO:
            return PRODUTO_MORTO
        if self.estado != VIGENTE_ENCONTRADA or self.vigente is None:
            return INDETERMINADO

        deles = _para_data(self.vigente.inicio)
        nossa = _para_data(nossa_data)
        if deles is None or nossa is None:
            return INDETERMINADO
        return ATRASADO if deles > nossa else EM_DIA

    def vigencia_para_o_acervo(self) -> Optional[dict]:
        """As datas publicadas, na forma que o `insurance_corpus` grava.

        Existe para que só haja **uma** tradução entre o HTML do REP2 e as
        colunas de `normative_document_versions`. Duas cópias dessa tradução
        envelheceriam separadas, e a que ninguém olha é sempre a que mente.

        🔴 Devolve `None` — e não um dicionário de `None`s — quando não houve
        resposta. Um dicionário vazio seria escrito por cima do que já está
        gravado e apagaria vigência boa com o resultado de uma consulta que
        não aconteceu. É a armadilha 1 na camada de escrita.

            effective_from     Data de Início da versão vigente (ISO)
            effective_until    Data de Fim dela — sempre None, é o que a
                               define como vigente; a coluna existe para o dia
                               em que ela deixar de ser
            version_label      o nome do arquivo na tabela de Versões
            susep_version_id   o id de download, que é como se busca o PDF
            fim_da_anterior    a Data de Fim publicada para a versão que esta
                               substituiu — é ela que fecha a linha antiga com
                               a data do regulador em vez de "hoje"
        """
        if self.estado != VIGENTE_ENCONTRADA or self.vigente is None:
            return None

        fechadas = [(_para_data(v.fim), v) for v in self.versoes if not v.vigente]
        fechadas = [(d, v) for d, v in fechadas if d is not None]
        anterior = max(fechadas, key=lambda par: par[0])[1] if fechadas else None

        return {
            "effective_from": self.vigente.inicio_iso,
            "effective_until": _para_iso(self.vigente.fim),
            "version_label": self.vigente.arquivo or None,
            "susep_version_id": self.vigente.download_id,
            "fim_da_anterior": _para_iso(anterior.fim) if anterior else None,
            "fonte": "susep_rep2",
        }


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------

def _para_data(valor: Any) -> Optional[date]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    return None


def _para_iso(valor: Any) -> Optional[str]:
    d = _para_data(valor)
    return d.isoformat() if d else None


# ---------------------------------------------------------------------------
# O parser do HTML
# ---------------------------------------------------------------------------
#
# Sem bs4 e sem lxml — nenhum dos dois está instalado, e o HTML do REP2 é saída
# regular de ASP.NET. Regex sobre uma estrutura estável é honesto aqui; o que
# não seria honesto é depender do layout sem um marcador que prove que a página
# veio cheia. Esse marcador é `MARCA_PRODUTO`.

# Se este bloco não vier, não houve resposta — mesmo com HTTP 200.
MARCA_PRODUTO = "Detalhes do Produto"
MARCA_VERSOES = "Vers"          # <legend>Versões</legend>, com entidade HTML

_RE_TAG = re.compile(r"<[^>]+>")
_RE_LINHA = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_RE_CELULA = re.compile(r"<t[dh]([^>]*)>(.*?)</t[dh]>", re.S | re.I)
_RE_DOWNLOAD = re.compile(r"DownloadConsultaPublica/(\d+)")
_RE_NEGRITO = re.compile(r"font-weight\s*:\s*bold", re.I)
# ⚠️ O link de download carrega `<span class="invisivel">Download</span>`, que
# é texto para leitor de tela. Sem tirar a âncora, todo nome de arquivo sai
# como "… CG144_Susep.pdf Download" — e o nome do arquivo é a chave por onde
# se reconhece a versão em `normative_document_versions`.
_RE_ANCORA = re.compile(r"<a\b.*?</a>", re.S | re.I)


def _texto(bruto: str) -> str:
    """Tira tags, resolve entidades e normaliza espaço — inclusive `&nbsp;`."""
    limpo = _RE_TAG.sub(" ", bruto or "")
    limpo = _html.unescape(limpo).replace("\xa0", " ")
    return re.sub(r"\s+", " ", limpo).strip()


def _campo(pagina: str, rotulo: str) -> Optional[str]:
    """Lê `<strong>...Rótulo:</strong>valor`.

    ⚠️ O portal prefixa alguns rótulos com lixo: o número do processo vem como
    `CCC Número do Processo:` e a sociedade como `DDD Sociedade:`. Por isso a
    busca é por *sufixo* do rótulo, não por igualdade.
    """
    for m in re.finditer(r"<strong>(.*?)</strong>([^<]*)", pagina, re.S | re.I):
        nome = _texto(m.group(1)).rstrip(":").strip().lower()
        if nome.endswith(rotulo.lower()):
            return _texto(m.group(2)) or None
    return None


def _ramo(bruto: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """`05 | AUTOMÓVEL - CASCO` → `("05", "AUTOMÓVEL - CASCO")`.

    O ramo vem numerado da SUSEP e é assim que ele é gravado (SPEC-070 §5.2):
    criar vocabulário paralelo ao do regulador é divergência de graça.
    """
    if not bruto:
        return None, None
    if "|" in bruto:
        codigo, _, nome = bruto.partition("|")
        return codigo.strip() or None, nome.strip() or None
    return None, bruto.strip() or None


def _versoes(pagina: str) -> list[Versao]:
    achadas: list[Versao] = []
    for linha in _RE_LINHA.findall(pagina):
        celulas = _RE_CELULA.findall(linha)
        if len(celulas) < 3:
            continue
        atributos = [c[0] for c in celulas]
        valores = [_texto(c[1]) for c in celulas]
        if "<th" in linha.lower():
            continue
        download = _RE_DOWNLOAD.search(linha)
        arquivo = _texto(_RE_ANCORA.sub(" ", celulas[0][1]))
        if not arquivo and not download:
            continue
        achadas.append(Versao(
            arquivo=arquivo,
            inicio=valores[1] or None,
            fim=valores[2] or None,
            download_id=download.group(1) if download else None,
            negrito=bool(_RE_NEGRITO.search(atributos[0] or "")),
        ))
    return achadas


def interpretar_consulta(pagina: Optional[str], processo: str, *,
                         http_status: Optional[int] = None,
                         duracao_ms: int = 0) -> ConsultaProduto:
    """Lê o HTML do REP2 e devolve um dos três estados. **Função pura.**

    Ser pura é o que permite alimentá-la com a resposta vazia real da Tokio num
    teste offline e exigir que ela não diga "sem alteração" — que é o controle
    que dá direito a confiar nos outros casos.
    """
    texto = pagina or ""
    tamanho = len(texto.encode("utf-8", "replace"))
    comum = dict(processo=processo, http_status=http_status,
                 duracao_ms=duracao_ms, bytes_recebidos=tamanho)

    if not texto.strip():
        return ConsultaProduto(INDETERMINADO, motivo="resposta_vazia", **comum)

    # 🔴 Armadilha 1. Status 200, formulário devolvido, nenhuma mensagem de
    # erro — e nenhum produto. 📊 11.545 bytes contra 95.861 do caso cheio.
    if MARCA_PRODUTO not in texto:
        return ConsultaProduto(INDETERMINADO, motivo="pagina_sem_detalhes_do_produto",
                               **comum)

    situacao = _campo(texto, "situação do produto")
    sociedade = _campo(texto, "sociedade")
    codigo, nome = _ramo(_campo(texto, "ram"))
    subramo = _campo(texto, "subram")

    versoes = tuple(_versoes(texto))
    if not versoes:
        return ConsultaProduto(INDETERMINADO, motivo="tabela_de_versoes_ausente",
                               sociedade=sociedade, ramo_codigo=codigo, ramo_nome=nome,
                               subramo=subramo, situacao=situacao, **comum)

    viva = (situacao or "").strip().lower() == SITUACAO_VIVA
    if not viva:
        return ConsultaProduto(PRODUTO_MORTO, motivo=f"situacao={situacao!r}",
                               sociedade=sociedade, ramo_codigo=codigo, ramo_nome=nome,
                               subramo=subramo, situacao=situacao, versoes=versoes,
                               **comum)

    abertas = [v for v in versoes if v.vigente]
    if not abertas:
        # Produto vivo e nenhuma versão em aberto. Não é "não mudou": é uma
        # combinação que a regra não prevê, e chutar aqui é o começo do erro.
        return ConsultaProduto(INDETERMINADO,
                               motivo="produto_vivo_sem_versao_em_aberto",
                               sociedade=sociedade, ramo_codigo=codigo, ramo_nome=nome,
                               subramo=subramo, situacao=situacao, versoes=versoes,
                               **comum)

    # Mais de uma em aberto: fica a de início mais recente, e o motivo diz que
    # havia mais — o número some, a informação não.
    escolhida = max(abertas, key=lambda v: (_para_data(v.inicio) or date.min))
    motivo = None if len(abertas) == 1 else f"{len(abertas)}_versoes_em_aberto"

    negrito = [v for v in versoes if v.negrito]
    divergencia = bool(negrito) and escolhida not in negrito

    return ConsultaProduto(VIGENTE_ENCONTRADA, motivo=motivo, sociedade=sociedade,
                           ramo_codigo=codigo, ramo_nome=nome, subramo=subramo,
                           situacao=situacao, versoes=versoes, vigente=escolhida,
                           divergencia_negrito=divergencia, **comum)


# ---------------------------------------------------------------------------
# O cliente HTTP
# ---------------------------------------------------------------------------

class Rep2Client:
    """Consulta e download. Toda saída passa pelo `egress_guard` da SPEC-054."""

    def __init__(self, *, timeout: float = TIMEOUT_LEITURA):
        self._timeout = timeout

    def _cliente(self, timeout: float):
        import httpx
        return httpx.Client(
            timeout=httpx.Timeout(connect=TIMEOUT_CONEXAO, read=timeout,
                                  write=TIMEOUT_CONEXAO, pool=TIMEOUT_CONEXAO),
            follow_redirects=True,
            headers={"User-Agent": "AutoBrokers/1.0 (acervo de condicoes gerais)"},
        )

    # -- consulta ----------------------------------------------------------

    def consultar(self, processo_bruto: str) -> ConsultaProduto:
        """Pergunta ao REP2. Falha de rede vira `INDETERMINADO`, nunca exceção solta.

        🔴 O chamador desta função decide se um documento nosso está vencido.
        Uma exceção escapando daqui vira `except: pass` no primeiro lote com
        pressa, e aí "não perguntei" e "não mudou" viram a mesma coisa.
        """
        analise = analisar_processo(processo_bruto)
        if not analise.ok:
            return ConsultaProduto(
                INDETERMINADO, processo=analise.bruto,
                motivo=f"processo_malformado:{analise.motivo}",
            )

        processo = analise.formatado
        eg, politica = _guard()
        eg.check_url(URL_CONSULTA, politica)
        inicio = time.monotonic()
        try:
            with self._cliente(self._timeout) as cli:
                resp = cli.post(URL_CONSULTA,
                                files={"numeroProcesso": (None, processo)})
        except Exception as exc:  # noqa: BLE001
            ms = int((time.monotonic() - inicio) * 1000)
            logger.warning("[susep] consulta falhou: %s", type(exc).__name__)
            return ConsultaProduto(INDETERMINADO, processo=processo,
                                   motivo=f"rede:{type(exc).__name__}", duracao_ms=ms)

        ms = int((time.monotonic() - inicio) * 1000)
        if resp.status_code >= 400:
            return ConsultaProduto(INDETERMINADO, processo=processo,
                                   motivo=f"http_{resp.status_code}",
                                   http_status=resp.status_code, duracao_ms=ms)

        return interpretar_consulta(resp.text, processo,
                                    http_status=resp.status_code, duracao_ms=ms)

    # -- download ----------------------------------------------------------

    def baixar(self, download_id: str) -> tuple[bytes, str]:
        """Baixa o PDF de uma versão. Devolve `(bytes, nome_do_arquivo)`.

        Confere o `%PDF` no começo: 📊 a Tokio já devolveu 200 com 1 KB de
        página de erro (SPEC-070 §3.4), e um "PDF" que é HTML vira um documento
        vazio no acervo sem que ninguém veja.
        """
        url = f"{URL_DOWNLOAD}/{str(download_id).strip()}"
        eg, politica = _guard()
        eg.check_url(url, politica)
        try:
            with self._cliente(self._timeout) as cli:
                resp = cli.get(url)
        except Exception as exc:  # noqa: BLE001
            raise SusepIndisponivel(f"download falhou: {type(exc).__name__}") from exc

        if resp.status_code != 200:
            raise SusepIndisponivel(f"download HTTP {resp.status_code}")

        corpo = resp.content
        if not corpo.startswith(b"%PDF"):
            raise SusepIndisponivel(
                f"resposta nao e PDF ({len(corpo)} bytes, "
                f"{resp.headers.get('content-type')!r})")

        nome = _nome_do_anexo(resp.headers.get("content-disposition")) \
            or f"susep_{download_id}.pdf"
        return corpo, nome


def _nome_do_anexo(disposicao: Optional[str]) -> Optional[str]:
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disposicao or "", re.I)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# O catálogo
# ---------------------------------------------------------------------------

def _pasta_cache() -> str:
    caminho = os.getenv("SUSEP_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "autobrokers", "susep")
    os.makedirs(caminho, exist_ok=True)
    return caminho


@dataclass(frozen=True)
class Catalogo:
    linhas: tuple[dict, ...]
    origem: str                    # "rede" ou "cache"
    baixado_em: Optional[str] = None
    bytes_recebidos: int = 0
    duracao_ms: int = 0

    def __len__(self) -> int:
        return len(self.linhas)

    def da_seguradora(self, entnome_parcial: str) -> tuple[dict, ...]:
        alvo = (entnome_parcial or "").strip().upper()
        return tuple(l for l in self.linhas if alvo in (l.get("entnome") or "").upper())


def analisar_catalogo_csv(texto: str) -> tuple[dict, ...]:
    """CSV → linhas, conferindo as colunas. Pura, testável sem rede."""
    leitor = csv.DictReader(io.StringIO(texto))
    faltando = [c for c in COLUNAS_CATALOGO if c not in (leitor.fieldnames or [])]
    if faltando:
        raise CatalogoSuspeito(f"colunas ausentes: {faltando}")
    return tuple(dict(l) for l in leitor)


def conferir_contagem(linhas: Sequence[dict]) -> int:
    """🔴 Armadilha 2 — o guarda que olha a contagem, não o status.

    📊 O dump tem 31.871 registros. Um 200 com 12 linhas é o OData falhando em
    silêncio, e um catálogo de 12 linhas não erra: ele só *não acha* a
    seguradora que se procura, e o lote conclui "essa companhia não tem
    produto". É o mesmo formato de mentira da armadilha 1 — falta de resposta
    passando por resposta.

    Função pura para que o piso possa ser testado sem rede.
    """
    n = len(linhas or ())
    if n < PISO_REGISTROS:
        raise CatalogoSuspeito(
            f"catalogo com {n} registros, piso {PISO_REGISTROS} — "
            "HTTP 200 não é evidência de catálogo inteiro")
    return n


def carregar_catalogo(*, permitir_cache: bool = True) -> Catalogo:
    """Baixa o dump inteiro. **Valida a contagem, não o status.**

    ⚠️ `$top`, `$filter` e `$skip` devolvem HTTP 500 — 📊 reconfirmado em
    08/08/2026 com três variantes. Não tente paginar: não existe página.

    Armadilha 3: o último dump bom fica em disco. Se o endpoint mudar de
    caminho outra vez, o lote continua rodando com um dado que **se apresenta
    como cache**, com a data de quando foi baixado. Cache que se disfarça de
    resposta de hoje é a mesma família de defeito da armadilha 1.
    """
    eg, politica = _guard()
    eg.check_url(URL_CATALOGO, politica)
    inicio = time.monotonic()
    erro: Optional[str] = None
    try:
        import httpx
        with httpx.Client(
            timeout=httpx.Timeout(connect=TIMEOUT_CONEXAO, read=TIMEOUT_CATALOGO,
                                  write=TIMEOUT_CONEXAO, pool=TIMEOUT_CONEXAO),
            follow_redirects=True,
        ) as cli:
            resp = cli.get(URL_CATALOGO)
        if resp.status_code != 200:
            erro = f"HTTP {resp.status_code}"
        else:
            corpo = resp.content
            linhas = analisar_catalogo_csv(corpo.decode("utf-8-sig", "replace"))
            conferir_contagem(linhas)      # 🔴 Armadilha 2: aqui, e não no status
            ms = int((time.monotonic() - inicio) * 1000)
            _guardar_cache(corpo)
            return Catalogo(linhas, "rede", date.today().isoformat(), len(corpo), ms)
    except CatalogoSuspeito as exc:
        erro = str(exc)
    except Exception as exc:  # noqa: BLE001
        erro = f"{type(exc).__name__}: {exc}"

    logger.warning("[susep] catalogo indisponivel: %s", erro)
    if permitir_cache:
        guardado = _ler_cache()
        if guardado is not None:
            logger.warning("[susep] usando o ultimo dump bom, de %s", guardado.baixado_em)
            return guardado
    raise CatalogoSuspeito(erro or "catalogo indisponivel")


def _guardar_cache(corpo: bytes) -> None:
    try:
        pasta = _pasta_cache()
        with open(os.path.join(pasta, "DadosProdutos.csv"), "wb") as fh:
            fh.write(corpo)
        with open(os.path.join(pasta, "DadosProdutos.meta.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"baixado_em": date.today().isoformat(),
                       "bytes": len(corpo)}, fh)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[susep] cache do catalogo nao gravado: %s", type(exc).__name__)


def _ler_cache() -> Optional[Catalogo]:
    try:
        pasta = _pasta_cache()
        caminho = os.path.join(pasta, "DadosProdutos.csv")
        if not os.path.exists(caminho):
            return None
        corpo = open(caminho, "rb").read()
        linhas = analisar_catalogo_csv(corpo.decode("utf-8-sig", "replace"))
        # O mesmo piso: um cache truncado seria pior que cache nenhum, porque
        # já viria carimbado de "último dump bom".
        conferir_contagem(linhas)
        quando = None
        meta = os.path.join(pasta, "DadosProdutos.meta.json")
        if os.path.exists(meta):
            quando = (json.load(open(meta, encoding="utf-8")) or {}).get("baixado_em")
        return Catalogo(linhas, "cache", quando, len(corpo), 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[susep] cache ilegivel: %s", type(exc).__name__)
        return None


# ---------------------------------------------------------------------------
# A pergunta que o lote faz
# ---------------------------------------------------------------------------

@dataclass
class Atraso:
    """Um documento nosso ao lado da versão vigente na SUSEP."""

    insurer_key: Optional[str]
    product_line: Optional[str]
    processo_gravado: str
    processo_consultado: Optional[str]
    nossa_data: Optional[str]
    veredito: str                      # em_dia · atrasado · produto_morto · indeterminado
    consulta: Optional[ConsultaProduto] = None
    origem_do_processo: Optional[str] = None

    @property
    def arquivo_vigente(self) -> Optional[str]:
        return self.consulta.vigente.arquivo if (
            self.consulta and self.consulta.vigente) else None

    @property
    def data_vigente(self) -> Optional[str]:
        return self.consulta.vigente.inicio if (
            self.consulta and self.consulta.vigente) else None

    @property
    def download_id(self) -> Optional[str]:
        return self.consulta.vigente.download_id if (
            self.consulta and self.consulta.vigente) else None


def processo_para_consultar(documento: dict,
                            catalogo: Optional[Sequence[dict]] = None
                            ) -> tuple[Optional[str], Optional[str]]:
    """Qual número perguntar. Devolve `(processo, origem)`.

    `origem` é `"normalizado"` quando os 17 dígitos já estavam lá (só a
    pontuação estava errada) e `"reparado_pelo_catalogo"` quando os dígitos
    faltavam e o catálogo devolveu **um** candidato. `(None, motivo)` quando
    não dá — e nesse caso o motivo vai junto, para que a falha tenha nome.
    """
    bruto = (documento.get("susep_process") or "").strip()
    analise = analisar_processo(bruto)
    if analise.ok:
        return analise.formatado, "normalizado"

    if not catalogo:
        return None, f"malformado:{analise.motivo}"

    for pendencia in PENDENCIAS_DE_REPARO:
        if pendencia.gravado != bruto:
            continue
        reparo = reparar_pelo_catalogo(pendencia, catalogo)
        if reparo.resolvido:
            return reparo.processo, "reparado_pelo_catalogo"
        return None, f"reparo_ambiguo:{len(reparo.candidatos)}_candidatos"

    return None, f"malformado_sem_pendencia:{analise.motivo}"


def medir_atraso(documentos: Iterable[dict], *, cliente: Optional[Rep2Client] = None,
                 catalogo: Optional[Sequence[dict]] = None,
                 pausa_s: float = 0.5) -> list[Atraso]:
    """Para cada documento nosso, pergunta ao REP2 qual é a versão vigente.

    Cada `documento` é uma linha de `normative_documents` com pelo menos
    `susep_process`; `insurer_key`, `product_line` e `effective_from` entram
    quando existem. Passando `catalogo`, os processos truncados da lista de
    reparo são consultados pelo número recuperado — 📊 os dois da Tokio.

    🔴 Um documento que não deu para consultar sai com `indeterminado` e
    continua na lista. Sumir da lista seria a mesma mentira de dizer "em dia":
    quem lê o relatório contaria os que sobraram e concluiria que o resto está
    bem.
    """
    cli = cliente or Rep2Client()
    saida: list[Atraso] = []
    for i, doc in enumerate(documentos or ()):
        bruto = (doc.get("susep_process") or "").strip()
        alvo, origem = processo_para_consultar(doc, catalogo)
        if alvo is None:
            consulta = ConsultaProduto(INDETERMINADO, processo=bruto,
                                       motivo=f"processo_{origem}")
        else:
            consulta = cli.consultar(alvo)
            if pausa_s and i:
                time.sleep(pausa_s)   # portal público e gratuito; não o martele
        nossa = doc.get("effective_from")
        saida.append(Atraso(
            insurer_key=doc.get("insurer_key"),
            product_line=doc.get("product_line"),
            processo_gravado=bruto,
            processo_consultado=alvo,
            origem_do_processo=origem,
            nossa_data=str(nossa) if nossa else None,
            veredito=consulta.comparar_com(nossa),
            consulta=consulta,
        ))
    return saida
