# -*- coding: utf-8 -*-
"""Onda 1 — o extrator que PROPÕE e o verificador que só REPROVA.

SPEC-EXTRA-001.5 · BLOCO C (§7.1). É este módulo que tira a base do zero: 📊
17/09/2026 `insurer_assistance_plans` tinha **0 linhas**, e por isso 100 % das
perguntas de cobertura respondiam `nao_sabemos_ainda` — corretamente, porque era
tudo o que a base vazia autorizava dizer.

```
1. o extrator (modelo)      lê a FONTE ARQUIVADA, página a página, e PROPÕE
                            → curadoria='proposto', confianca, trecho_hash, pagina
2. o verificador (máquina)  a página existe? o trecho bate com ELA? o serviço está
                            no vocabulário? limite tem unidade? o nível é único?
                            falhou → 'rascunho' com o motivo — nunca 'proposto'
3. a pessoa                 abre a fila (unidade D), vê o trecho ao lado da linha,
                            publica ou rejeita → 'publicado' + revisado_por
```

🔴 O VERIFICADOR NÃO É O REVISOR: ELE SÓ REPROVA
================================================
Não existe, em lugar nenhum deste arquivo, caminho que leve uma linha a
`publicado`. `publicar_servico`/`publicar_plano` **não são importados aqui** —
de propósito, e o guarda M-C1 lê este arquivo para provar. Um verificador que
promove é a curadoria automática que o CHECK `servico_publicado_foi_revisado`
existe para impedir: aprovar o PDF não é aprovar *"guincho até 200 km"*.

🔴 A FONTE É O PDF ARQUIVADO, NÃO O PEDAÇO INDEXADO
===================================================
📊 BLOCO 0: não há coluna de página em `normative_*` — o chunk indexado perde a
página em `limpar()` (`insurance_corpus.py:367`). Sem página não há citação, e
sem citação a Skill não pode dizer "não" (§6.2). Por isso a leitura é do
original no MinIO, pelo `texto_das_paginas` do contrato da fatia 1 (mesmo
`fitz`, mesmo caminho de acervo — CLAUDE.md §5: nenhum segundo leitor de PDF).

⚠️ DUAS CLASSES DE REPROVAÇÃO, E ELAS TÊM DESTINOS DIFERENTES
=============================================================
O contrato da fatia 1 **já recusa** parte do lixo antes do banco: serviço fora
do vocabulário, limite sem unidade, seguradora desconhecida. Essas propostas
**não chegam a existir como linha** — não há o que mandar para `rascunho`, e
inventar uma linha só para marcá-la reprovada encheria a fila de coisas que
ninguém quer ver. Elas são contadas e registradas em log estruturado.

As outras — página que não existe no PDF, trecho que não está NAQUELA página,
nível repetido no produto — passam pelo contrato e só a conferência da fonte
pega. Essas viram linha e caem para `rascunho` com o motivo, porque é útil que a
pessoa veja *"o modelo propôs isto e a página não confirmou"*.

CUSTO — e por que a filtragem vem ANTES do modelo
=================================================
📊 49 documentos de auto/residencial/condomínio têm fonte arquivada, e um deles
sozinho tem **207 páginas**. Mandar tudo ao modelo seria pagar por milhares de
páginas de definições e glossário. O filtro é textual e roda antes: só vai ao
modelo a página onde algum sinônimo do vocabulário aparece.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from . import assistance_plans_base as BASE

logger = logging.getLogger(__name__)

#: 🔴 Nenhum `publicar_*` é importado aqui. O guarda M-C1 confere por leitura
#: deste arquivo, e a mutação (a) do pacote é justamente acrescentá-lo.
_PROIBIDO_IMPORTAR = ("publicar_servico", "publicar_plano")

MODELO = os.getenv("EXTRATOR_PLANOS_MODEL") or "claude-sonnet-5"
PROVEDOR = os.getenv("EXTRATOR_PLANOS_PROVIDER") or "anthropic"

#: Teto de páginas enviadas ao modelo por documento. 📊 um documento do acervo
#: tem 207 páginas; sem teto, um PDF mal filtrado vira a conta do mês inteiro.
TETO_DE_PAGINAS = int(os.getenv("EXTRATOR_PLANOS_TETO_PAGINAS", "12"))

RAMOS_PADRAO = ("auto", "residencial", "condominio")

_SISTEMA = """Você lê UMA página de uma condição geral de seguro e extrai o que ela
afirma sobre serviços de assistência e coberturas. Você NÃO resume, NÃO
generaliza e NÃO usa conhecimento de mercado: só o que está escrito NESTA página.

Responda SOMENTE um JSON, sem cerca de código, no formato:
{"linhas": [{"produto": "...", "plano": "...", "nivel": 1, "servico": "guincho",
  "coberto": "sim|nao|condicionado", "limite_valor": 200, "limite_unidade":
  "km|dias|acionamentos_ano|reais|unidades", "limite_texto": "...",
  "carencia_dias": 15, "condicao": "...", "trecho": "a frase LITERAL da página",
  "confianca": "alta|media|baixa"}]}

Regras:
- `servico` SÓ pode ser uma destas chaves: {servicos}
- `trecho` é copiado LITERALMENTE da página (sem reescrever, sem cortar palavra).
  Se você não consegue copiar a frase, não proponha a linha.
- `plano` TEM de ser um dos planos da CLÁUSULA DE PLANOS abaixo, copiado
  literalmente. A página fala de um serviço sem dizer de qual plano? Não proponha
  a linha — o plano errado é pior do que linha nenhuma.
- `nivel`: 1 é o mais básico; números maiores são planos mais completos, na ordem
  em que a cláusula de planos os lista.
- `limite_valor` só com `limite_unidade`. Sem unidade, deixe os dois nulos e
  escreva o limite em `limite_texto`.
- o limite só vale com o ESCOPO que o cabeçalho da coluna/linha dá ("por evento",
  "por vigência", "por dia", "utilizações"). Sem escopo legível NESTA página,
  deixe `limite_valor` e `limite_unidade` nulos.
- Nada nesta página sobre assistência/cobertura → {"linhas": []}.
- `coberto: "nao"` SÓ quando a página nega o serviço/cobertura EM SI ("não há
  cobertura para alagamento", "este plano não inclui carro reserva"). Uma
  EXCLUSÃO DE RISCO dentro de OUTRA cobertura ("riscos excluídos: inundação por
  transbordamento de rios", numa cláusula de Vendaval/Granizo) NÃO é um "não" do
  serviço: é `coberto: "condicionado"`, com a cláusula copiada em `condicao`.

CLÁUSULA DE PLANOS deste documento (a âncora, lida na primeira passada):
{ancora}
"""

#: 🔴 NÃO É MAIS UM FALLBACK. 📊 19/09/2026: 60 das 81 linhas propostas pela onda
#: 1 nasceram em "Plano único" — e 48 delas foram CORRIGIR ou RECUSAR. O nome
#: continua aqui só para os testes e scripts que o nomeiam ao contar o estrago;
#: nenhum caminho deste módulo o usa para batizar plano nenhum (unidade A).
_PLANO_PADRAO = "Plano único"


# ---------------------------------------------------------------------------
# A · A CLÁUSULA DE PLANOS É A ÂNCORA, E VEM PRIMEIRO
# ---------------------------------------------------------------------------
@dataclass
class Ancora:
    """A cláusula que ENUMERA os planos do documento. Sem ela não se propõe.

    📊 19/09/2026, o que a ausência dela custou: o manual **Bradesco Auto tem 9
    planos** (118, 108, 113, 112, 106, 21, 41, 15, 16) e virou um só; a HDI tem a
    Cláusula 2 (Essencial/Especial 1/Especial 2/VIP); a Tokio tem Básico/
    Completo/Vip no item 9.5.9. Os três viraram *"Plano único"*, e a linha
    passava a dizer do plano de todo mundo o que valia só para um.
    """

    planos: List[str]
    pagina: int
    clausula: str
    trecho: str


#: "Plano Vip", "Plano Básico", "Plano nº 118". O nome tem de começar com
#: maiúscula ou dígito — senão "plano contratado" e "plano de assistência"
#: entrariam como nomes de plano.
#
# ⚠️ CLAUDE.md §9.4 (dialeto): `re.IGNORECASE` NÃO serve aqui — a palavra
# "plano" precisa casar em qualquer caixa, mas o NOME tem de começar com
# maiúscula ou dígito. Com a flag global, "plano contratado pelo segurado"
# entraria como plano chamado "contratado".
_NOME_DE_PLANO = re.compile(
    r"\b[Pp][Ll][Aa][Nn][Oo]s?[ \t]+(?:n[ºo°][ \t]*)?"
    r"((?:[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][\wÁÂÃÀÉÊÍÓÔÕÚÜÇáâãàéêíóôõúüç]{1,18}|\d{1,4})"
    r"(?:[ \t]+(?:[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][\wÁÂÃÀÉÊÍÓÔÕÚÜÇáâãàéêíóôõúüç]{1,18}|\d{1,3}))?)",
)
# ⚠️ `[ \t]`, nunca `\s`: 📊 o título *"9.5.9.1 Plano Completo"* seguido da linha
# *"Hospedagem: R$100,00…"* virava um plano chamado "Completo Hospedagem" — o
# `\s` atravessa a quebra de linha, e o nome do plano nunca atravessa.

#: Palavras que vêm depois de "plano" e NÃO são nome de plano.
_NAO_E_NOME_DE_PLANO = frozenset((
    "contratado", "contratada", "contratados", "escolhido", "segurado", "seguro",
    "unico", "de", "do", "da", "dos", "das", "e", "ou", "em", "para", "com",
    "sem", "que", "no", "na", "acima", "abaixo", "referido", "citado", "sera",
    "tem", "inclui", "assistencia", "cobertura", "coberturas", "servicos",
    "servico", "vigente", "atual", "anterior", "superior", "inferior", "o", "a",
))

#: O número da cláusula ("9.5.9.2", "Cláusula 2", "COBERTURA 03").
_NUMERO_DE_CLAUSULA = re.compile(
    r"(?m)^\s*(?:(?:cl[áa]usula|item)\s+)?((?:\d{1,3}\.){1,4}\d{0,3}|\d{1,3}\.)\s",
    re.IGNORECASE,
)
_CLAUSULA_NOMEADA = re.compile(r"(?mi)^\s*(cl[áa]usula\s+\d{1,3}[ªo°]?)\b")


def _nomes_de_plano_na_pagina(texto: str) -> List[str]:
    """Os nomes de plano que a PÁGINA enumera, na ordem em que aparecem."""
    vistos: List[str] = []
    for m in _NOME_DE_PLANO.finditer(str(texto or "")):
        nome = re.sub(r"\s+", " ", m.group(1)).strip(" .,:;-")
        primeira = BASE._norm_texto(nome.split(" ")[0])
        if primeira in _NAO_E_NOME_DE_PLANO or not nome:
            continue
        # "Plano Básico de Assistência" -> "Básico"; a segunda palavra só entra
        # quando ela também parece nome ("Especial 1", "Vip Premium").
        partes = nome.split(" ")
        if len(partes) == 2 and BASE._norm_texto(partes[1]) in _NAO_E_NOME_DE_PLANO:
            nome = partes[0]
        if len(nome) < 2 or len(nome) > TETO_DO_NOME_DO_PLANO:
            continue
        if not any(BASE._norm_texto(nome) == BASE._norm_texto(v) for v in vistos):
            vistos.append(nome)
    return vistos


def _clausula_antes_de(texto: str, posicao: int) -> str:
    """O número da cláusula mais próxima ANTES daquela posição da página."""
    antes = str(texto or "")[: max(0, int(posicao))]
    numeros = list(_NUMERO_DE_CLAUSULA.finditer(antes))
    if numeros:
        return numeros[-1].group(1).strip(" .")
    nomeadas = list(_CLAUSULA_NOMEADA.finditer(antes))
    return nomeadas[-1].group(1).strip() if nomeadas else ""


def paginas_candidatas_a_ancora(paginas: Dict[int, str], teto: int = 3) -> List[int]:
    """As páginas que ENUMERAM planos — filtro TEXTUAL, antes de qualquer token.

    ⚠️ CLAUDE.md §9.4 (custo): a âncora que precisa do modelo manda 3 páginas, não
    207. O critério é quantos nomes DIFERENTES a página enumera: a cláusula de
    planos cita todos, e a página que menciona "o plano contratado" de passagem
    não cita nenhum.
    """
    placar: List[Tuple[int, int, int]] = []
    for pagina, texto in (paginas or {}).items():
        bruto = str(texto or "")
        quantos = len(_nomes_de_plano_na_pagina(bruto))
        mencoes = len(re.findall(r"(?i)\bplanos?\b", bruto))
        # ⚠️ 2 menções, não 3: 📊 a Cláusula 2 da HDI ("Dos Produtos e Planos" +
        # "conforme o plano de assistência contratado") tem exatamente DUAS, e é
        # o caso em que o texto não resolve e o modelo precisa ver a página.
        if quantos >= 2 or mencoes >= 2:
            placar.append((quantos, mencoes, int(pagina)))
    placar.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return [p for _, _, p in placar[: int(teto)]]


_ANCORA_SISTEMA = """Você recebe páginas de uma condição geral de seguro e procura
UMA coisa só: a cláusula que ENUMERA os planos/pacotes de assistência do
documento (ex.: "Plano Básico, Plano Completo e Plano Vip", a tabela de níveis,
a Cláusula 2 com Essencial/Especial 1/Especial 2/VIP, a lista de códigos 118,
108, 113).

Responda SOMENTE um JSON, sem cerca de código:
{"planos": ["Básico", "Completo", "Vip"], "pagina": 27, "clausula": "9.5.9",
 "trecho": "a frase LITERAL da página que enumera os planos"}

Regras:
- cada nome em `planos` é copiado LITERALMENTE da página `pagina`. Não traduza,
  não complete, não acrescente plano que a página não nomeia.
- `pagina` é uma das páginas mostradas.
- nenhuma das páginas enumera planos → {"planos": []}.
"""


def localizar_ancora_de_planos(paginas: Dict[int, str], modelo: Any = None) -> Optional[Ancora]:
    """A 1ª passada: a cláusula de planos do documento, ou `None`.

    🔴 `None` é uma RECUSA, e o chamador NÃO propõe nada (unidade A da
    SPEC-EXTRA-001.5.2). O antigo default *"Plano único"* é o que produziu 📊 60
    das 81 linhas conferidas em 19/09/2026 — 48 delas erradas.

    O texto vem primeiro e o modelo só entra quando o texto não resolve (custo):
    📊 a cláusula da Tokio ("Plano Básico, Plano Completo, Plano Vip") e a lista
    do Bradesco ("Plano nº 118") casam por regex; a Cláusula 2 da HDI
    ("Essencial, Especial 1, Especial 2 e VIP", sem a palavra "plano" antes de
    cada nome) não casa — e é para ela que o modelo existe.

    ⚠️ E o que o modelo devolve passa por VERIFICAÇÃO DE MÁQUINA: cada nome tem
    de existir LITERALMENTE na página que ele citou. Sem isso, a âncora inventada
    seria pior do que a ausência dela — ela batizaria todas as linhas.
    """
    candidatas = paginas_candidatas_a_ancora(paginas or {})
    for pagina in candidatas:
        texto = str((paginas or {}).get(pagina) or "")
        nomes = _nomes_de_plano_na_pagina(texto)
        if len(nomes) >= 2:
            m = _NOME_DE_PLANO.search(texto)
            pos = m.start() if m else 0
            linha = texto[max(0, texto.rfind("\n", 0, pos) + 1):]
            return Ancora(
                planos=nomes,
                pagina=int(pagina),
                clausula=_clausula_antes_de(texto, pos),
                trecho=re.sub(r"\s+", " ", linha.split("\n")[0]).strip()[:400],
            )
    if modelo is None or not candidatas:
        return None

    from langchain_core.messages import HumanMessage, SystemMessage

    corpo = "\n\n".join(
        "=== Página %s ===\n%s" % (p, str((paginas or {}).get(p) or "")[:6000])
        for p in candidatas
    )
    try:
        resposta = modelo.invoke([SystemMessage(content=_ANCORA_SISTEMA),
                                  HumanMessage(content=corpo)])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[onda1] ancora: chamada ao modelo falhou: %s", type(exc).__name__)
        return None
    dados = _json_da_resposta(_texto_da_resposta(resposta))
    propostos = [str(x).strip() for x in (dados.get("planos") or []) if str(x).strip()]
    try:
        pagina = int(dados.get("pagina") or 0)
    except (TypeError, ValueError):
        pagina = 0
    if pagina not in candidatas:
        logger.warning("[onda1] ancora: o modelo citou pagina fora das candidatas")
        return None
    alvo = BASE._norm_texto((paginas or {}).get(pagina) or "")
    # 🔴 A VERIFICAÇÃO DE MÁQUINA, nome a nome.
    confirmados = [n for n in propostos if BASE._norm_texto(n) and BASE._norm_texto(n) in alvo]
    if len(confirmados) < 2:
        logger.warning("[onda1] ancora: %s nome(s) do modelo confirmados na pagina %s",
                       len(confirmados), pagina)
        return None
    trecho = str(dados.get("trecho") or "").strip()
    if trecho and BASE.normalizar_trecho(trecho) not in BASE.normalizar_trecho(
            (paginas or {}).get(pagina) or ""):
        trecho = ""
    return Ancora(planos=confirmados, pagina=pagina,
                  clausula=str(dados.get("clausula") or "").strip(), trecho=trecho[:400])


def plano_da_ancora(bruto: Any, ancora: Optional[Ancora]) -> Optional[str]:
    """O nome do plano da proposta, **como a âncora o escreve**, ou `None`.

    Casa por normalização (`Plano Vip` ≡ `vip` ≡ `VIP`) e aceita o nome como
    pedaço do nome da âncora (`Assistência 24 Horas - Plano Vip` → `Vip`), porque
    o modelo copia o título inteiro da seção com frequência.
    """
    nome = nome_de_plano_valido(bruto)
    if nome is None or ancora is None:
        return None
    alvo = BASE._norm_texto(nome)
    for candidato in ancora.planos:
        c = BASE._norm_texto(candidato)
        if not c:
            continue
        if alvo == c or re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(c), alvo):
            return candidato
    return None


def caminho_da_clausula(
    texto_pagina: str, trecho: str, *, ancora: Optional[Ancora] = None,
    plano: Optional[str] = None, servico: Optional[str] = None,
) -> str:
    """`"9.5.9.2 › Plano Vip › Carro Reserva"` — de onde a linha saiu.

    Unidade B: a linha carrega o ESCOPO de onde a frase foi lida. É o que
    permite ver, sem abrir o PDF, que um `alagamento = nao` saiu de dentro da
    cláusula de Vendaval/Granizo — o padrão 1 dos cinco medidos.
    """
    texto = str(texto_pagina or "")
    pos = texto.find(str(trecho or "")[:60]) if trecho else -1
    if pos < 0:
        alvo, agulha = BASE.normalizar_trecho(texto), BASE.normalizar_trecho(trecho)[:60]
        pos = alvo.find(agulha) if agulha else -1
        if pos >= 0:
            texto = alvo
    partes: List[str] = []
    numero = _clausula_antes_de(texto, pos if pos >= 0 else len(texto))
    if not numero and ancora is not None:
        numero = ancora.clausula
    if numero:
        partes.append(numero)
    if plano:
        partes.append("Plano %s" % plano if not BASE._norm_texto(plano).startswith("plano")
                      else str(plano))
    titulo = titulo_da_secao(texto, pos)
    if titulo:
        partes.append(titulo)
    elif servico:
        partes.append(str(servico))
    return " › ".join(partes)


#: O TÍTULO da seção onde a frase está: "COBERTURA 03 - VENDAVAL…",
#: "II. Carro Reserva", "10. COBERTURA ADICIONAL DE VENDAVAL, GRANIZO".
_TITULO_DE_SECAO = re.compile(
    r"(?m)^\s*(?:(?:(?:\d{1,3}\.){0,4}\d{0,3}|[IVXLC]{1,5})[.)]?\s+)?"
    r"((?:COBERTURA|CL[ÁA]USULA|CONDI[ÇC][ÃA]O ESPECIAL|GARANTIA)[^\n]{0,90}"
    r"|[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][^\n]{2,60})\s*$"
)


def titulo_da_secao(texto: str, posicao: int) -> str:
    """O título da seção imediatamente ANTES daquela posição, ou string vazia."""
    antes = str(texto or "")[: max(0, int(posicao))] if posicao and posicao > 0 else ""
    if not antes:
        return ""
    titulos = list(_TITULO_DE_SECAO.finditer(antes))
    if not titulos:
        return ""
    bruto = re.sub(r"\s+", " ", titulos[-1].group(1)).strip(" .:-")
    return bruto[:90]


# ---------------------------------------------------------------------------
# Seleção das páginas — texto antes do modelo
# ---------------------------------------------------------------------------
def termos_do_vocabulario() -> List[str]:
    """Todos os sinônimos, normalizados pela MESMA `_norm_texto` da base.

    ⚠️ CLAUDE.md §9.4 (dialeto): normalizar aqui de um jeito e lá de outro daria
    zero casamento em silêncio — e a onda 1 "não encontraria nada" em 49 PDFs.
    """
    termos: List[str] = []
    for chave, item in BASE.vocabulario_de_servicos().get("servicos", {}).items():
        for sin in [chave] + list(item.get("sinonimos") or []):
            t = BASE._norm_texto(sin).replace("_", " ")
            if len(t) >= 4:
                termos.append(t)
    return sorted(set(termos), key=len, reverse=True)


def paginas_com_vocabulario(paginas: Dict[int, str], teto: int = TETO_DE_PAGINAS) -> List[int]:
    """As páginas onde algum termo do vocabulário aparece, as mais densas antes.

    A densidade (quantos termos DIFERENTES a página cita) é o critério porque a
    página de tabela de assistência cita muitos, e a página que menciona
    "chaveiro" de passagem cita um.
    """
    termos = termos_do_vocabulario()
    placar: List[Tuple[int, int]] = []
    for pagina, texto in paginas.items():
        alvo = BASE._norm_texto(texto)
        if not alvo:
            continue
        quantos = sum(1 for t in termos if t in alvo)
        if quantos:
            placar.append((quantos, int(pagina)))
    placar.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, p in placar[: int(teto)]]


# ---------------------------------------------------------------------------
# O modelo — o cliente que o projeto JÁ tem
# ---------------------------------------------------------------------------
def _texto_da_resposta(result: Any) -> str:
    """O TEXTO, não a repr da lista de blocos.

    📊 A mesma armadilha custou US$ 0,45 e 11 chamadas ao Opus 5 sem salvar nada
    (`attendance_distiller.py:105-126`): quando o modelo pensa, `content` é uma
    LISTA de blocos e `str()` devolve a repr, que nenhum leitor de JSON encaixa.
    """
    bruto = getattr(result, "content", None)
    if isinstance(bruto, str):
        return bruto.strip()
    if isinstance(bruto, list):
        partes = [str(b.get("text")) for b in bruto
                  if isinstance(b, dict) and b.get("type") == "text" and b.get("text")]
        return "\n".join(partes).strip()
    return str(bruto or "").strip()


def _json_da_resposta(texto: str) -> Dict[str, Any]:
    s = (texto or "").strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[4:] if s.lower().startswith("json") else s
    inicio, fim = s.find("{"), s.rfind("}")
    if inicio < 0 or fim <= inicio:
        return {}
    try:
        return json.loads(s[inicio:fim + 1])
    except Exception:  # noqa: BLE001
        return {}


def montar_modelo() -> Optional[Any]:
    """O cliente já configurado do projeto (`LLMFactory`). Sem chave → `None`.

    🔴 `None` não é erro: é o modo `--dry-run` forçado, e o CLI **declara**. O
    pior desfecho seria a onda 1 "rodar" sem modelo e reportar zero propostas
    como se o acervo não tivesse nada.
    """
    try:
        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory

        chave = get_api_key_for_provider(PROVEDOR, MODELO)
        if not chave:
            return None
        return LLMFactory.create_llm(
            company_config={},
            agent_data={"llm_provider": PROVEDOR, "llm_model": MODELO},
            api_key=chave,
            company_id=str(os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or ""),
            agent_id=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[onda1] modelo indisponivel: %s", type(exc).__name__)
        return None


def propostas_da_pagina(
    texto: str, pagina: int, *, produto_padrao: str, llm: Any,
    ancora: Optional[Ancora] = None,
) -> List[Dict[str, Any]]:
    """Uma página → as linhas que o modelo PROPÕE. `llm=None` → nada.

    🔴 A ÂNCORA VAI NO PROMPT (unidade A): sem a lista de planos à vista, o
    modelo batiza a linha com o que a página tiver à mão — e foi assim que 📊 60
    das 81 linhas nasceram em *"Plano único"*.
    """
    if llm is None or not str(texto or "").strip():
        return []
    from langchain_core.messages import HumanMessage, SystemMessage

    if ancora is None:
        texto_da_ancora = ("(nenhuma cláusula de planos foi localizada — NÃO proponha linha "
                           "nenhuma)")
    else:
        texto_da_ancora = "planos: %s\ncláusula %s, página %s\n%s" % (
            ", ".join(ancora.planos), ancora.clausula or "(sem número)",
            ancora.pagina, ancora.trecho)
    # ⚠️ `.format` NÃO serve aqui: o prompt mostra um JSON de exemplo, e cada
    # chave dele seria lida como campo de formatação (`KeyError: '"linhas"'`).
    sistema = (_SISTEMA.replace("{servicos}", ", ".join(BASE.servicos_declarados()))
                       .replace("{ancora}", texto_da_ancora))
    usuario = (
        "Produto (como o documento se chama): %s\nPágina %s do documento.\n\n---\n%s\n---"
        % (produto_padrao, pagina, str(texto)[:12000])
    )
    try:
        resposta = llm.invoke([SystemMessage(content=sistema), HumanMessage(content=usuario)])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[onda1] chamada ao modelo falhou p.%s: %s", pagina, type(exc).__name__)
        return []
    dados = _json_da_resposta(_texto_da_resposta(resposta))
    linhas = dados.get("linhas") if isinstance(dados, dict) else None
    fora: List[Dict[str, Any]] = []
    for l in linhas or []:
        if isinstance(l, dict):
            l = dict(l)
            l["pagina"] = int(pagina)
            fora.append(l)
    return fora


# ---------------------------------------------------------------------------
# Normalização de `produto` e `plano` — a chave da base depende deles
# ---------------------------------------------------------------------------
#: Extensões que o título do documento carrega e que NÃO são nome de produto.
_EXTENSOES = (".pdf", ".docx", ".doc", ".txt", ".html", ".htm")

#: Teto do nome do plano. 📊 18/09/2026: 4 dos 38 planos propostos passavam de 60
#: caracteres porque o modelo copiou a LISTA de coberturas como se fosse o nome
#: do pacote ("Cobertura Basica + Vendaval + Danos Eletricos + ...").
TETO_DO_NOME_DO_PLANO = 60


def produto_canonico(bruto, ramo=""):
    """O nome do produto, limpo — e sempre na MESMA caixa.

    📊 18/09/2026, o que a onda 1 gravou, e por que cada pedaço existe aqui:
      · "Bradesco Seguro Residencial CC-RESIDENCIAL POP.pdf" — nome de ARQUIVO;
      · 'Mapfre condominio' × 'Mapfre Condominio' — a MESMA coisa, duas chaves.

    A segunda é a pior. A chave da base inclui o produto, então as duas caixas
    viram dois produtos, cada um com um plano de nível 1 — e o gancho *"existe um
    plano acima do seu"* **nunca** acha o superior, porque ele mora no "outro"
    produto. O defeito é silencioso: a resposta sai completa, só falta a oferta.
    """
    texto = str(bruto or "").strip()
    baixo = texto.lower()
    for ext in _EXTENSOES:
        if baixo.endswith(ext):
            texto = texto[: -len(ext)]
            break
    # o resto do nome de arquivo ("CC-RESIDENCIAL POP") sai junto
    texto = re.sub(r"\s*[-_]?\b(?:CC|CG|CP)[-_][A-Z0-9 _-]+$", "", texto)
    texto = re.sub(r"[_-]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip(" .-")
    if not texto:
        texto = str(ramo or "Produto")
    palavras = []
    for w in texto.split(" "):
        palavras.append(w if (w.isupper() and len(w) <= 4) else w.capitalize())
    return " ".join(palavras)[:120]


# ---------------------------------------------------------------------------
# C · NÚMERO DE TABELA VEM COM A COLUNA, OU NÃO VEM
# ---------------------------------------------------------------------------
#: O escopo que o cabeçalho da coluna/linha dá ao número. 📊 19/09/2026, as 4
#: linhas de limite marcadas CORRIGIR erraram todas por aqui: "R$ 300,00" da HDI
#: é *por evento*, e existe um segundo número, *por vigência*, na mesma célula.
ESCOPOS_DE_LIMITE = {
    "por_evento": r"por\s+(?:evento|sinistro|ocorr[êe]ncia|acionamento|pane)",
    "por_vigencia": r"(?:por|na|durante\s+a|ao\s+ano\s+de)\s+vig[êe]ncia|por\s+ano|anual",
    "por_dia": r"por\s+di[aá]ria|por\s+dia\b|di[áa]rias?\b",
    "por_utilizacao": r"utiliza[çc][õo]es|interven[çc][õo]es|acionamentos\b|eventos\b",
    "por_passageiro": r"por\s+passageiro",
}
_ESCOPOS_COMPILADOS = {k: re.compile(v, re.IGNORECASE) for k, v in ESCOPOS_DE_LIMITE.items()}

#: Quantos caracteres ao redor do trecho ainda contam como "o cabeçalho da
#: coluna". A tabela do PDF vira texto corrido, e o cabeçalho fica a uma ou duas
#: linhas de distância — não a uma página.
JANELA_DO_CABECALHO = 400


def escopos_do_limite(texto_pagina: str, trecho: str) -> List[str]:
    """Os escopos legíveis para o número: `["por_evento", "por_vigencia"]`.

    Procura no TRECHO e, se lá não houver, na vizinhança dele na página — que é
    onde o cabeçalho da coluna cai quando a tabela vira texto.
    """
    achados: List[str] = []
    do_trecho = BASE.normalizar_trecho(trecho or "")
    pagina = BASE.normalizar_trecho(texto_pagina or "")
    pos = pagina.find(do_trecho[:60]) if do_trecho else -1
    vizinhanca = do_trecho
    if pos >= 0:
        ini = max(0, pos - JANELA_DO_CABECALHO)
        vizinhanca = pagina[ini: pos + len(do_trecho) + JANELA_DO_CABECALHO]
    for nome, rx in _ESCOPOS_COMPILADOS.items():
        if rx.search(do_trecho) or rx.search(vizinhanca):
            achados.append(nome)
    return achados


def aplicar_escopo_do_limite(proposta: Dict[str, Any], texto_pagina: str) -> Dict[str, Any]:
    """O limite fica **com o escopo**, ou fica VAZIO dizendo por quê (unidade C).

    🔴 Apagar o número não é perder informação: *"R$ 300,00"* sem saber se é por
    evento ou por vigência é um número que a pessoa vai repetir ao segurado como
    se fosse o teto — e a HDI tem os DOIS, com valores diferentes.
    """
    p = dict(proposta or {})
    if p.get("limite_valor") is None:
        return p
    achados = escopos_do_limite(texto_pagina, str(p.get("trecho") or ""))
    if achados:
        p["limite_escopo"] = achados
        rotulos = ", ".join(a.replace("_", " ") for a in achados)
        texto = str(p.get("limite_texto") or "").strip()
        if rotulos.split(",")[0] not in BASE._norm_texto(texto):
            p["limite_texto"] = ("%s (%s)" % (texto, rotulos)).strip() if texto else rotulos
        return p
    bruto = "%s %s" % (p.get("limite_valor"), p.get("limite_unidade") or "")
    p["limite_texto"] = (
        "não gravado: a página %s traz \"%s\" sem cabeçalho de coluna que diga o "
        "escopo (por evento · por vigência · por dia · utilizações)"
        % (p.get("pagina"), bruto.strip())
    )
    p["limite_valor"] = None
    p["limite_unidade"] = None
    p["limite_escopo"] = []
    return p


# ---------------------------------------------------------------------------
# D · O PRODUTO E A VERSÃO VÊM DA CAPA
# ---------------------------------------------------------------------------
@dataclass
class Capa:
    """O que a PRIMEIRA página diz que o documento é. `None` = a capa não diz."""

    produto: Optional[str] = None
    versao: Optional[str] = None
    origem: str = "capa"


#: "Versão 3.2", "v41", "versao: 2.9", "Ed. 07/2023 - V1.2".
#
# ⚠️ o `_` antes do `V` é o caso REAL do acervo: 📊 `Seguro Residencial
# Conteudo_V1.2`. `\bv` não casa depois de `_` (o underscore é caractere de
# palavra), e era assim que a versão do cadastro passava batida.
_VERSAO = re.compile(
    r"(?i)(?:vers[ãa]o|ed\.?\s*v|\bv|_v)\s*[.:]?\s*(\d{1,3}(?:\.\d{1,3})?)\b")

#: Linhas da capa que NÃO são nome de produto.
_LIXO_DE_CAPA = re.compile(
    r"(?i)^(?:condi[çc][õo]es\s+(?:gerais|contratuais)|processo\s+susep|susep|"
    r"sumario|[íi]ndice|p[áa]gina\s*\d+|vers[ãa]o\b|www\.|\d+\s*$|cnpj|"
    r"sac\b|ouvidoria)"
)


def capa_do_documento(paginas: Dict[int, str]) -> Capa:
    """Produto e versão lidos da CAPA — nunca do nome do arquivo (unidade D).

    📊 19/09/2026, 4 das 81 linhas gravaram nome de ARQUIVO como produto
    (`Seguro Residencial Conteudo_V1.2`, um nome terminando em travessão solto), e
    2 declararam uma versão que o PDF desmente (Mapfre Auto v34 sendo v41,
    Mapfre Residencial v2.9 sendo 3.2).

    A versão é procurada na primeira página e no RODAPÉ das últimas — que é onde
    a condição geral costuma carimbá-la.
    """
    if not paginas:
        return Capa()
    numeros = sorted(int(p) for p in paginas)
    primeira = str(paginas.get(numeros[0]) or "")
    produto = None
    for linha in [l.strip() for l in primeira.splitlines()]:
        limpo = re.sub(r"\s+", " ", linha).strip(" .-—–|")
        if len(limpo) < 6 or len(limpo) > 90 or _LIXO_DE_CAPA.match(limpo):
            continue
        if not re.search(r"[A-Za-zÁ-úÀ-ÿ]{3}", limpo):
            continue
        produto = _VERSAO.sub("", limpo).strip(" .-—–_|")
        break
    versao = None
    rodapes = [primeira] + [str(paginas.get(n) or "")[-800:] for n in numeros[-3:]]
    for fonte in rodapes:
        m = _VERSAO.search(fonte)
        if m:
            versao = m.group(1)
            break
    return Capa(produto=produto or None, versao=versao)


def versao_declarada(texto: Any) -> Optional[str]:
    """A versão que o CADASTRO afirma (o título do documento), ou `None`."""
    m = _VERSAO.search(str(texto or ""))
    return m.group(1) if m else None


def _mesma_versao(a: Optional[str], b: Optional[str]) -> bool:
    def _n(v):
        partes = [int(x) for x in str(v).split(".")] if v else []
        while len(partes) < 2:
            partes.append(0)
        return tuple(partes[:2])

    return bool(a) and bool(b) and _n(a) == _n(b)


# ---------------------------------------------------------------------------
# E · COBERTURA NÃO É ASSISTÊNCIA
# ---------------------------------------------------------------------------
#: 📊 19/09/2026: 15 linhas da base usam a chave `vidros` — 7 residencial, 6 auto
#: e 2 condomínio. Quebra de vidros RESIDENCIAL é cobertura contratada (com
#: prêmio adicional), não serviço de assistência 24 h; em AUTO é assistência de
#: verdade. A mesma chave dizia as duas coisas (P-001.5.1-VIDROS-RESIDENCIAL).
SERVICO_POR_RAMO = {
    ("vidros", "residencial"): "vidros_residencial",
    ("vidros", "condominio"): "vidros_residencial",
}


def servico_do_ramo(servico: Any, ramo: Any) -> str:
    """A chave do serviço NESTE ramo. `vidros` residencial → `vidros_residencial`."""
    chave = str(servico or "")
    return SERVICO_POR_RAMO.get((chave, BASE._norm_texto(ramo).replace(" ", "_")), chave)


def nome_de_plano_valido(bruto):
    """O nome do plano, ou `None` quando o que veio não é nome de plano.

    🔴 `None` é uma RECUSA, não um default: trocar por "Plano único" esconderia
    que o modelo não achou pacote nenhum naquela página, e a linha entraria na
    fila como se alguém tivesse lido um nome.
    """
    texto = re.sub(r"\s+", " ", str(bruto or "")).strip(" .-")
    if not texto:
        return None
    if len(texto) > TETO_DO_NOME_DO_PLANO:
        return None
    if texto.count("+") >= 2 or texto.count(",") >= 2 or texto.count(";") >= 1:
        return None
    return texto


def vigencia_do_documento(documento_id, doc, db):
    """A vigência do PLANO é a da VERSÃO do documento — nunca `date.today()`.

    🔴 📊 18/09/2026: a onda gravou `date.today()` em **38 de 38** planos. A
    vigência entra nas chaves únicas da base: rodar a onda amanhã não atualizaria
    nada — criaria uma segunda base inteira, com duas vigências dizendo a mesma
    coisa sobre o mesmo produto. E a apólice de 2023 passaria a ser respondida
    por um plano que "começou a valer" no dia em que o extrator rodou.

    Fontes, na ordem e todas medidas: `normative_document_versions.effective_from`
    (📊 26 de 27 preenchidos) → `normative_documents.effective_from` →
    `created_at`. Nenhuma delas → `None`, e o documento é PULADO: o contrato da
    fatia 1 exige vigência, e inventá-la é o defeito que se está consertando.
    """
    try:
        versoes = (
            db.table("normative_document_versions")
            .select("version, effective_from")
            .eq("document_id", str(documento_id))
            .execute()
        ).data or []
    except Exception:  # noqa: BLE001
        versoes = []
    for v in sorted(versoes, key=lambda x: int(x.get("version") or 0), reverse=True):
        if v.get("effective_from"):
            return str(v["effective_from"])[:10]
    for campo in ("effective_from", "created_at"):
        if doc.get(campo):
            return str(doc[campo])[:10]
    return None


# ---------------------------------------------------------------------------
# O VERIFICADOR — máquina, sem LLM, e só para baixo
# ---------------------------------------------------------------------------
@dataclass
class Reprovacao:
    """Motivo nomeado. `insere` diz se a linha ainda chega a existir."""

    motivo: str
    insere: bool = False


#: A FORMA da cláusula de exclusão de risco — "riscos excluídos", "não estão
#: cobertos os danos decorrentes de…". Ela fala do RISCO dentro de uma cobertura.
_E_EXCLUSAO_DE_RISCO = re.compile(
    r"risco[s]?\s+excluid|exclus[õo]e?s|n[ãa]o\s+est[ãa]o\s+cobert|"
    r"n[ãa]o\s+(?:ser[ãa]o\s+)?indeniza|excetuad|ressalvad",
    re.IGNORECASE,
)

#: E a FORMA de negar o serviço EM SI — que é o único "não" que a base aceita.
_NEGA_O_SERVICO = re.compile(
    r"n[ãa]o\s+(?:h[áa]|possui|inclui|cobre|contempla|disp[õo]e|oferece)|"
    r"servi[çc]o\s+n[ãa]o\s+(?:dispon|inclu|cobert)|sem\s+(?:direito|cobertura)\s+a",
    re.IGNORECASE,
)

#: Os motivos, com destino. `insere=True` = a linha entra e cai para `rascunho`.
MOTIVOS = {
    "sem_trecho": Reprovacao("o modelo não copiou o trecho da página"),
    "servico_fora_do_vocabulario": Reprovacao("serviço fora do vocabulário"),
    "coberto_invalido": Reprovacao("`coberto` não é sim/nao/condicionado"),
    "limite_sem_unidade": Reprovacao("limite com valor e sem unidade"),
    "seguradora_desconhecida": Reprovacao("seguradora fora das chaves canônicas"),
    "nivel_duplicado": Reprovacao("dois planos com o mesmo nível no produto"),
    "nome_de_plano_invalido": Reprovacao("o 'plano' era uma lista de coberturas"),
    "nivel_nao_contiguo": Reprovacao("nível pula um número no produto"),
    "exclusao_de_risco_nao_e_nao_do_servico": Reprovacao(
        "exclusão de risco dentro de outra cobertura virou 'nao' do serviço", insere=True),
    # 🔴 `insere=False` de propósito: a linha sem plano da âncora **não tem onde
    # existir** — o serviço pendura no plano, e criar um plano para marcá-lo
    # reprovado seria recriar o "Plano único" pela porta dos fundos. Ela é
    # CONTADA por motivo, como as recusas do contrato.
    "plano_fora_da_ancora": Reprovacao(
        "o plano proposto não está na cláusula de planos do documento"),
    "nao_veio_de_clausula_de_outro_servico": Reprovacao(
        "o 'nao' foi lido dentro da cláusula de OUTRO serviço/cobertura", insere=True),
    "pagina_inexistente": Reprovacao("página não existe no PDF arquivado", insere=True),
    "trecho_nao_esta_na_pagina": Reprovacao("o trecho não está NAQUELA página", insere=True),
}


def verificar(
    proposta: Dict[str, Any],
    *,
    insurer: str,
    documento_id: str,
    niveis_por_produto: Dict[str, Dict[int, str]],
    db: Any = None,
    minio: Any = None,
    ancora: Optional[Ancora] = None,
    texto_da_pagina: str = "",
) -> Optional[str]:
    """`None` = passou. String = o motivo da reprovação. 🔴 NUNCA publica.

    A conferência da página chama **`BASE.conferir_pagina`** — o motor da fatia
    1 sobre o PDF real (CLAUDE.md §9.4). Reimplementar a comparação aqui
    provaria que o regex casa, não que a fonte confirma; e é exatamente a
    mutação (b) do pacote (*"pular `conferir_pagina`"*).
    """
    trecho = str(proposta.get("trecho") or "").strip()
    if len(trecho) < 12:
        return "sem_trecho"
    # 🔴 "NÃO" SECO TIRADO DE UMA CLÁUSULA DE EXCLUSÃO É UM "NÃO" ERRADO.
    #
    # 📊 18/09/2026, 2 de 6 linhas da amostra: a cláusula *"riscos excluídos:
    # inundação decorrente de transbordamento de rios"*, que está DENTRO da
    # cobertura de Vendaval/Granizo, virou `alagamento = nao` do plano inteiro.
    # O segurado com cobertura de alagamento por outra causa ouviria "não cobre"
    # — o pior erro desta SPEC, porque ele desiste de acionar um direito que tem.
    #
    # A recusa é do VERIFICADOR (máquina) e não só da instrução ao modelo: a
    # instrução pede, o verificador garante.
    if str(proposta.get("coberto")) == "nao" and _E_EXCLUSAO_DE_RISCO.search(trecho) \
            and not _NEGA_O_SERVICO.search(trecho):
        return "exclusao_de_risco_nao_e_nao_do_servico"
    # 🔴 B · O ESCOPO DA CLÁUSULA MANDA NO VEREDITO — e ele é lido da PÁGINA.
    #
    # A regra acima pega a FORMA da frase ("riscos excluídos…"). Esta pega o
    # LUGAR dela: um `nao` de `alagamento` lido de dentro de *"COBERTURA 03 —
    # VENDAVAL, FURACÃO, CICLONE, TORNADO E GRANIZO"* fala do granizo, não do
    # alagamento — e nenhuma palavra da frase denuncia isso. 📊 4 das 16 linhas
    # RECUSADAS em 19/09/2026 eram exatamente esta classe.
    if str(proposta.get("coberto")) == "nao" and texto_da_pagina:
        titulo = titulo_da_secao(
            texto_da_pagina,
            BASE.normalizar_trecho(texto_da_pagina).find(BASE.normalizar_trecho(trecho)[:60]),
        )
        dono = BASE.servico_canonico(titulo) if titulo else None
        meu = str(proposta.get("servico") or "")
        # ⚠️ `vidros` e `vidros_residencial` são o MESMO dono (unidade E): o
        # título da seção nunca traz o sufixo de ramo, e sem esta comparação por
        # prefixo a linha residencial de vidros seria reprovada pela própria
        # cláusula de onde ela saiu.
        parecidos = bool(dono) and bool(meu) and (dono in meu or meu in dono)
        if dono and meu and dono != meu and not parecidos:
            return "nao_veio_de_clausula_de_outro_servico"
    if str(proposta.get("servico") or "") not in BASE.servicos_declarados():
        return "servico_fora_do_vocabulario"
    if str(proposta.get("coberto") or "") not in BASE.COBERTURAS:
        return "coberto_invalido"
    if proposta.get("limite_valor") is not None and not proposta.get("limite_unidade"):
        return "limite_sem_unidade"
    if proposta.get("limite_unidade") and str(proposta["limite_unidade"]) not in BASE.UNIDADES:
        return "limite_sem_unidade"
    try:
        BASE.chave_de_conhecimento(insurer)
    except BASE.SeguradoraDesconhecida:
        return "seguradora_desconhecida"

    produto = produto_canonico(proposta.get("produto"))
    # 🔴 A · O PLANO VEM DA ÂNCORA, e não do que a página deixou à mão.
    # Sem âncora não se chega aqui pelo caminho do motor (`processar_documento`
    # recusa antes); um chamador direto que não a passe continua com a regra
    # antiga, que é a do nome válido.
    if ancora is not None:
        plano = plano_da_ancora(proposta.get("plano"), ancora)
        if plano is None:
            return ("nome_de_plano_invalido"
                    if nome_de_plano_valido(proposta.get("plano")) is None
                    else "plano_fora_da_ancora")
    else:
        plano = nome_de_plano_valido(proposta.get("plano"))
        if plano is None:
            return "nome_de_plano_invalido"
    try:
        nivel = int(proposta.get("nivel") or 1)
    except (TypeError, ValueError):
        nivel = 1
    dono = niveis_por_produto.setdefault(produto, {}).get(nivel)
    if dono is not None and dono != plano:
        return "nivel_duplicado"
    # 🔴 NÍVEIS CONTÍGUOS — e a escolha é RECUSAR, não renumerar.
    # 📊 bradesco/auto saiu com [1, 3] e sem o 2. Renumerar mudaria em silêncio o
    # que a condição geral diz sobre a ordem dos pacotes, e é o nível que decide
    # quem é "o plano acima do seu" na oferta comercial. Um buraco na numeração é
    # sinal de que uma página não foi lida — isso a pessoa precisa ver, não que
    # alguém tenha fechado o buraco por ela.
    ja = sorted(niveis_por_produto.get(produto, {}))
    if ja and nivel > max(ja) + 1:
        return "nivel_nao_contiguo"

    conferencia = BASE.conferir_pagina(
        documento_id, proposta.get("pagina"), trecho=trecho, db=db, minio=minio
    )
    if not conferencia.ok:
        if conferencia.motivo in ("pagina_inexistente", "trecho_nao_esta_na_pagina"):
            return conferencia.motivo
        # fonte_ausente / minio_indisponivel / pdf_ilegivel não são culpa da
        # proposta: são falha de infraestrutura, e tratá-las como reprovação
        # ensinaria a fila a culpar o modelo por um MinIO fora do ar.
        return "fonte_%s" % conferencia.motivo

    niveis_por_produto.setdefault(produto, {})[nivel] = plano
    return None


# ---------------------------------------------------------------------------
# A onda
# ---------------------------------------------------------------------------
@dataclass
class ResumoDoDocumento:
    documento_id: str
    insurer_key: Optional[str]
    ramo: Optional[str]
    paginas_lidas: int = 0
    paginas_ao_modelo: int = 0
    propostas: int = 0
    planos_propostos: int = 0
    servicos_propostos: int = 0
    rascunhos: int = 0
    recusadas: Dict[str, int] = field(default_factory=dict)
    motivo: str = "ok"
    #: 🔴 unidade A: a cláusula de planos localizada (ou `None`, e nada é proposto).
    ancora: Optional[Ancora] = None
    planos_da_ancora: int = 0
    #: ⚠️ unidade D: divergência de versão é ALERTA, não silêncio.
    alertas: List[str] = field(default_factory=list)
    produto_da_capa: Optional[str] = None
    versao_da_capa: Optional[str] = None

    def recusar(self, motivo: str) -> None:
        self.recusadas[motivo] = self.recusadas.get(motivo, 0) + 1


class _MinioComCache:
    """Baixa o original UMA vez por documento e serve todas as conferências.

    ⚠️ Sem isto, `conferir_pagina` baixaria o PDF inteiro por proposta: 📊 um
    documento de 207 páginas com 10 propostas seriam 10 downloads do mesmo
    arquivo. O cache é do TRANSPORTE — a conferência continua sendo a do motor.
    """

    def __init__(self, real: Any) -> None:
        self._real = real
        self._cache: Dict[str, bytes] = {}

    def download_file(self, caminho: str):
        import io

        if caminho not in self._cache:
            self._cache[caminho] = self._real.download_file(caminho).read()
        return io.BytesIO(self._cache[caminho])


def documentos_alvo(
    *, ramos: Tuple[str, ...] = RAMOS_PADRAO, documento_id: Optional[str] = None, db: Any = None
) -> List[Dict[str, Any]]:
    """Os documentos indexados, dos ramos pedidos, COM fonte arquivada.

    📊 17/09/2026: auto 20 · residencial 22 · condomínio 7 = **49** com fonte.
    Documento sem `storage_ref` não entra: sem original, não há página nem
    trecho conferível — e uma linha sem fonte é o que a fatia 1 recusa.
    """
    cliente = db if db is not None else _cliente()
    q = cliente.table("normative_documents").select(
        "id, insurer_key, insurer_name, product_line, doc_kind, title, susep_process, content_hash"
    ).eq("status", "ingested")
    docs = (q.execute()).data or []
    if documento_id:
        docs = [d for d in docs if str(d.get("id")) == str(documento_id)]
    else:
        docs = [d for d in docs if str(d.get("product_line")) in set(ramos)]
    com_fonte = []
    for d in docs:
        versoes = (
            cliente.table("normative_document_versions")
            .select("version, storage_ref")
            .eq("document_id", str(d["id"]))
            .execute()
        ).data or []
        if any(v.get("storage_ref") for v in versoes):
            com_fonte.append(d)
    return com_fonte


def processar_documento(
    doc: Dict[str, Any], *, aplicar: bool, llm: Any, db: Any = None, minio: Any = None
) -> ResumoDoDocumento:
    """Um documento: lê, filtra, propõe, verifica e (se `aplicar`) grava."""
    cliente = db if db is not None else _cliente()
    resumo = ResumoDoDocumento(
        documento_id=str(doc.get("id")),
        insurer_key=doc.get("insurer_key"),
        ramo=doc.get("product_line"),
    )
    if minio is None:
        try:
            from ..minio_service import get_minio_service

            minio = _MinioComCache(get_minio_service())
        except Exception as exc:  # noqa: BLE001
            resumo.motivo = "minio_indisponivel:%s" % type(exc).__name__
            return resumo

    lidas = BASE.texto_das_paginas(resumo.documento_id, db=cliente, minio=minio)
    if not lidas.ok:
        resumo.motivo = lidas.motivo
        return resumo
    resumo.paginas_lidas = lidas.total

    paginas = lidas.paginas or {}

    # 🔴 D · A CAPA, ANTES DE TUDO: o produto é o que a PRIMEIRA PÁGINA diz, não o
    # nome do arquivo (📊 4 das 81 linhas gravaram nome de arquivo como produto).
    capa = capa_do_documento(paginas)
    resumo.produto_da_capa = capa.produto
    resumo.versao_da_capa = capa.versao
    do_cadastro = versao_declarada(doc.get("title"))
    if capa.versao and do_cadastro and not _mesma_versao(capa.versao, do_cadastro):
        resumo.alertas.append(
            "versao_da_capa_diverge_do_cadastro: capa=%s cadastro=%s"
            % (capa.versao, do_cadastro))
    produto_padrao = (capa.produto
                      or str(doc.get("title") or doc.get("product_line") or "Produto"))

    # 🔴 A · A PRIMEIRA PASSADA É A ÂNCORA. Sem ela, o documento NÃO vai ao
    # modelo — e isso é economia além de correção: a página não lida não é paga.
    ancora = localizar_ancora_de_planos(paginas, modelo=llm)
    resumo.ancora = ancora
    if ancora is None:
        resumo.motivo = "clausula_de_planos_nao_localizada"
        return resumo
    resumo.planos_da_ancora = len(ancora.planos)
    ordem_do_plano = {BASE._norm_texto(n): i + 1 for i, n in enumerate(ancora.planos)}

    alvo = paginas_com_vocabulario(paginas)
    resumo.paginas_ao_modelo = len(alvo)

    ramo = str(doc.get("product_line") or "")
    propostas: List[Dict[str, Any]] = []
    for pagina in alvo:
        texto_da_pagina = paginas.get(pagina, "")
        for p in propostas_da_pagina(texto_da_pagina, pagina,
                                     produto_padrao=produto_padrao, llm=llm, ancora=ancora):
            # E · a chave do serviço depende do RAMO (vidros residencial é
            # cobertura, vidros de auto é assistência).
            p["servico"] = servico_do_ramo(p.get("servico"), ramo)
            # C · o número só fica com o escopo que o cabeçalho der.
            p = aplicar_escopo_do_limite(p, texto_da_pagina)
            # A · o plano é o da âncora, escrito como a âncora o escreve; e o
            # NÍVEL é a ordem dela, não o palpite do modelo.
            da_ancora = plano_da_ancora(p.get("plano"), ancora)
            if da_ancora:
                p["plano"] = da_ancora
                p["nivel"] = ordem_do_plano.get(BASE._norm_texto(da_ancora), p.get("nivel") or 1)
            p["produto"] = p.get("produto") or produto_padrao
            # B · e cada proposta carrega DE ONDE saiu.
            p["caminho_da_clausula"] = caminho_da_clausula(
                texto_da_pagina, str(p.get("trecho") or ""), ancora=ancora,
                plano=p.get("plano"), servico=p.get("servico"))
            propostas.append(p)
    resumo.propostas = len(propostas)
    if not propostas:
        return resumo

    niveis: Dict[str, Dict[int, str]] = {}
    aprovadas: List[Dict[str, Any]] = []
    reprovadas: List[Tuple[Dict[str, Any], str]] = []
    for p in propostas:
        motivo = verificar(
            p, insurer=str(doc.get("insurer_key") or doc.get("insurer_name") or ""),
            documento_id=resumo.documento_id, niveis_por_produto=niveis,
            db=cliente, minio=minio, ancora=ancora,
            texto_da_pagina=paginas.get(int(p.get("pagina") or 0), ""),
        )
        if motivo is None:
            aprovadas.append(p)
        else:
            resumo.recusar(motivo)
            reprovadas.append((p, motivo))

    if not aplicar:
        return resumo

    planos_criados: Dict[Tuple[str, str], str] = {}

    vigencia = vigencia_do_documento(resumo.documento_id, doc, cliente)
    if vigencia is None:
        resumo.motivo = "documento_sem_vigencia"
        return resumo

    def _plano_id(p: Dict[str, Any]) -> Optional[str]:
        produto = produto_canonico(p.get("produto") or produto_padrao,
                                   doc.get("product_line"))
        # 🔴 sem `_PLANO_PADRAO` aqui: o plano é o da âncora, e a proposta que
        # não casou com ela nem chega a este ponto (o verificador a reprovou).
        nome = plano_da_ancora(p.get("plano"), ancora)
        if nome is None:
            resumo.recusar("plano_fora_da_ancora")
            return None
        chave = (produto, nome)
        if chave in planos_criados:
            return planos_criados[chave]
        try:
            linha = BASE.propor_plano(
                insurer=str(doc.get("insurer_key") or doc.get("insurer_name") or ""),
                ramo=str(doc.get("product_line") or ""),
                produto=produto, plano=nome,
                nivel=int(p.get("nivel") or 1),
                vigencia_inicio=vigencia,
                documento_id=resumo.documento_id, pagina=int(p["pagina"]),
                content_hash=str(doc.get("content_hash") or ""),
                confianca=str(p.get("confianca") or "media")
                if str(p.get("confianca") or "") in BASE.CONFIANCAS else "media",
                susep_process=doc.get("susep_process"), db=cliente,
            )
        except BASE.BaseDePlanosRecusa as exc:
            logger.warning("[onda1] plano recusado pelo contrato: %s", type(exc).__name__)
            resumo.recusar("plano_recusado_pelo_contrato")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("[onda1] plano recusado pelo banco: %s", type(exc).__name__)
            resumo.recusar("plano_recusado_pelo_banco:%s" % type(exc).__name__)
            return None
        planos_criados[chave] = str(linha.get("id"))
        resumo.planos_propostos += 1
        return planos_criados[chave]

    # 🔴 UMA LINHA POR (plano, serviço) — o banco tem `uq_ias_servico` e recusa a
    # segunda. 📊 A primeira rodada em produção morreu exatamente aqui: o mesmo
    # serviço aparece em páginas diferentes do mesmo PDF (a tabela e o texto que
    # a explica), e as duas propostas são legítimas. Fica a de MAIOR confiança —
    # e, no empate, a primeira, que é a página mais densa (a tabela).
    _ordem = {"alta": 0, "media": 1, "baixa": 2}
    aprovadas = sorted(aprovadas, key=lambda x: _ordem.get(str(x.get("confianca")), 1))
    vistos = set()
    unicas = []
    for p in aprovadas:
        chave = (str(p.get("produto") or ""), str(p.get("plano") or ""), str(p.get("servico")))
        if chave in vistos:
            resumo.recusar("servico_repetido_no_plano")
            continue
        vistos.add(chave)
        unicas.append(p)
    aprovadas = unicas

    for p in aprovadas:
        pid = _plano_id(p)
        if not pid:
            continue
        try:
            BASE.propor_servico(
                plano_id=pid, servico=str(p["servico"]), coberto=str(p["coberto"]),
                documento_id=resumo.documento_id, pagina=int(p["pagina"]),
                trecho=str(p.get("trecho") or ""),
                limite_valor=p.get("limite_valor"), limite_unidade=p.get("limite_unidade"),
                limite_texto=p.get("limite_texto"), carencia_dias=p.get("carencia_dias"),
                condicao=p.get("condicao"),
                confianca=str(p.get("confianca") or "media")
                if str(p.get("confianca") or "") in BASE.CONFIANCAS else "media",
                db=cliente,
            )
            resumo.servicos_propostos += 1
        except BASE.BaseDePlanosRecusa as exc:
            logger.warning("[onda1] servico recusado pelo contrato: %s", type(exc).__name__)
            resumo.recusar("servico_recusado_pelo_contrato")
        except Exception as exc:  # noqa: BLE001
            # 🔴 O BANCO também recusa (é a segunda trava, de propósito). Uma
            # recusa dele é uma linha perdida, não uma onda perdida: sem este
            # ramo, o primeiro `uq_ias_servico` matava os 49 documentos.
            logger.warning("[onda1] servico recusado pelo banco: %s", type(exc).__name__)
            resumo.recusar("servico_recusado_pelo_banco:%s" % type(exc).__name__)

    # As reprovadas que o contrato ainda aceita viram linha e caem para
    # `rascunho` COM o motivo — para a pessoa ver o que o modelo tentou.
    for p, motivo in reprovadas:
        if not MOTIVOS.get(motivo, Reprovacao(motivo)).insere:
            continue
        pid = _plano_id(p)
        if not pid:
            continue
        try:
            linha = BASE.propor_servico(
                plano_id=pid, servico=str(p["servico"]), coberto=str(p["coberto"]),
                documento_id=resumo.documento_id, pagina=int(p["pagina"]),
                trecho=str(p.get("trecho") or ""), condicao=p.get("condicao"),
                confianca="baixa", db=cliente,
            )
            BASE.para_rascunho(str(linha.get("id")), motivo, db=cliente)
            resumo.rascunhos += 1
        except Exception as exc:  # noqa: BLE001
            resumo.recusar("rascunho_recusado:%s" % type(exc).__name__)
    return resumo


def _cliente() -> Any:
    from ...core.database import get_supabase_client

    return get_supabase_client().client


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Onda 1 da SPEC-EXTRA-001.5: propõe linhas de assistência a partir "
                    "da fonte arquivada. NUNCA publica."
    )
    parser.add_argument("--documento", help="um documento só, por id")
    parser.add_argument("--ramos", default=",".join(RAMOS_PADRAO))
    parser.add_argument("--limite", type=int, default=0, help="quantos documentos no máximo")
    parser.add_argument("--dry-run", action="store_true",
                        help="lê, filtra, propõe e verifica — e NÃO grava nada")
    parser.add_argument("--aplicar", action="store_true",
                        help="grava as aprovadas como 'proposto' (nunca 'publicado')")
    args = parser.parse_args(argv)

    # O CLI roda fora do processo da API, que é quem normalmente carrega o
    # `.env`. Sem isto, `get_api_key_for_provider` não acha a chave e a onda
    # "roda" sem modelo — o desfecho mais enganoso possível (§12.1).
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
    except Exception:  # noqa: BLE001
        pass

    aplicar = bool(args.aplicar) and not bool(args.dry_run)
    llm = montar_modelo()
    if llm is None:
        print("[onda1] SEM MODELO configurado — rodando em modo LEITURA "
              "(páginas e filtro), nenhuma proposta será gerada.")
    ramos = tuple(r.strip() for r in str(args.ramos).split(",") if r.strip())
    docs = documentos_alvo(ramos=ramos, documento_id=args.documento)
    if args.limite:
        docs = docs[: int(args.limite)]
    print("[onda1] %s documento(s) · modo=%s · modelo=%s"
          % (len(docs), "APLICAR" if aplicar else "dry-run", MODELO if llm else "nenhum"))

    total = {"planos": 0, "servicos": 0, "rascunhos": 0, "propostas": 0}
    por_chave: Dict[str, Dict[str, int]] = {}
    recusas: Dict[str, int] = {}
    for d in docs:
        r = processar_documento(d, aplicar=aplicar, llm=llm)
        chave = "%s/%s" % (r.insurer_key, r.ramo)
        alvo = por_chave.setdefault(chave, {"planos": 0, "servicos": 0, "rascunhos": 0})
        alvo["planos"] += r.planos_propostos
        alvo["servicos"] += r.servicos_propostos
        alvo["rascunhos"] += r.rascunhos
        total["planos"] += r.planos_propostos
        total["servicos"] += r.servicos_propostos
        total["rascunhos"] += r.rascunhos
        total["propostas"] += r.propostas
        for m, n in r.recusadas.items():
            recusas[m] = recusas.get(m, 0) + n
        print("  %-28s paginas=%-4s ao_modelo=%-3s propostas=%-3s planos=%-3s servicos=%-3s "
              "rascunhos=%-3s %s"
              % (chave, r.paginas_lidas, r.paginas_ao_modelo, r.propostas,
                 r.planos_propostos, r.servicos_propostos, r.rascunhos,
                 "" if r.motivo == "ok" else "[%s]" % r.motivo))

    print("\n[onda1] por seguradora x ramo:")
    for chave in sorted(por_chave):
        print("   %-28s %s" % (chave, por_chave[chave]))
    print("[onda1] TOTAL %s" % total)
    print("[onda1] recusadas por motivo: %s" % (recusas or "nenhuma"))
    print("[onda1] 🔴 linhas publicadas por este processo: 0 (publicar é ato humano, §7.1)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())
