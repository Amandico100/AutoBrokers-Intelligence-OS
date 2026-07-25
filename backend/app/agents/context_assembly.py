"""Context Assembly 2.0 — SPEC-052 §6, Lote 3.

O que existia
-------------
O roteador de intenção do sistema era uma régua:

    def should_prefetch_rag(user_message):
        return len(user_message) > 25

"Bom dia, tudo bem?" tem 20 caracteres e não busca nada. "Me manda o telefone
de vocês" tem 28 e dispara recuperação completa. Memória do usuário e da
corretora eram carregadas em toda mensagem, sempre, independentemente de
servirem. É caro no token e ruim na resposta: contexto irrelevante não é
neutro — ele compete com o relevante pela atenção do modelo.

O que entra
-----------
    pergunta
      → classificação de intenção e risco   (léxica, barata, explicável)
      → plano de contexto                    (que fontes, com que orçamento)
      → recuperação just-in-time             (só o que o plano pediu)
      → Evidence Pack com procedência        (fonte, autoridade, vigência)
      → precedência aplicada
      → orçamento respeitado

A regra que mais importa
------------------------
SPEC-052 §6.4: **o RAG global nunca confirma sozinho que uma apólice específica
possui cobertura.**

Isso deixou de ser teórico no momento em que 35 condições gerais entraram no
conhecimento global. Sem esta regra, o agente lê "cobre vidro" na condição geral
da Porto e responde que a apólice do cliente cobre vidro — quando a apólice pode
ter sido emitida sob outra versão, com cláusula excluída ou franquia diferente.
O corretor repete ao cliente, e a corretora responde por isso.

Aqui, quando a pergunta é sobre cobertura de uma apólice concreta e a única
evidência disponível é normativa, o pacote sai marcado `exige_apolice` e carrega
a instrução explícita de não confirmar.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Modo
# --------------------------------------------------------------------------
# Mesma disciplina do cutover do Gateway, e pelo mesmo motivo: isto muda o que
# o modelo recebe. Uma classificação errada que decida "não precisa buscar"
# produz uma resposta pior sem deixar rastro óbvio — o corretor só vê o agente
# ficar burro. Então:
#
#   off      comportamento antigo, íntegro.
#   shadow   o plano é calculado e registrado no log, mas NADA é pulado.
#            Serve para ler o que seria descartado antes de descartar.
#   on       o plano manda.
#
# O padrão é `shadow`: observar sem interferir custa quase nada e é a única
# forma honesta de saber se o classificador acerta no tráfego real.
MODO_OFF, MODO_SHADOW, MODO_ON = "off", "shadow", "on"


def modo() -> str:
    v = str(os.getenv("CONTEXT_ASSEMBLY_MODE", MODO_SHADOW)).strip().lower()
    return v if v in (MODO_OFF, MODO_SHADOW, MODO_ON) else MODO_SHADOW


def CONTEXT_ASSEMBLY_ATIVO() -> bool:
    """Só em `on` o plano decide de fato o que carregar."""
    return modo() == MODO_ON

# --------------------------------------------------------------------------
# Orçamento
# --------------------------------------------------------------------------
# Números escolhidos pelo que cabe sem empurrar o histórico para fora da
# janela. Contexto recuperado que expulsa a conversa piora a resposta mesmo
# sendo relevante.
ORCAMENTO_TOTAL = 14_000
TETO_POR_FONTE = {
    "memoria_usuario": 1_200,
    "memoria_corretora": 1_800,
    "rag_tenant": 5_000,
    "rag_global": 4_000,
    "normativo": 5_500,
    "dados_vivos": 3_000,
}


# --------------------------------------------------------------------------
# Intenção
# --------------------------------------------------------------------------

CONVERSA = "conversa"
FATO_SEGURO = "fato_seguro"
COBERTURA_APOLICE = "cobertura_apolice"
OPERACAO = "operacao"
ANALISE = "analise"
PROCEDIMENTO = "procedimento"
PESQUISA = "pesquisa"

# Saudação, agradecimento e despedida. Não precisam de nada além da conversa —
# e é a fatia mais barata de acertar, porque é a mais frequente.
_RE_SOCIAL = re.compile(
    r"^\s*(oi|ol[áa]|bom dia|boa tarde|boa noite|e a[íi]|opa|tudo bem|tudo bom|"
    r"obrigad[oa]|valeu|brigad[oa]|ok|beleza|certo|entendi|perfeito|show|"
    r"at[ée] mais|tchau|abra[çc]o|bom fim de semana|de nada)"
    r"[\s!.,?…]*$", re.I)

_PISTAS = {
    COBERTURA_APOLICE: (
        "cobre", "cobertura", "est[áa] coberto", "tem direito", "indeniza",
        "franquia", "carência", "carencia", "exclusão", "exclusao", "excluído",
        "excluido", "vale para", "posso acionar", "d[áa] direito",
    ),
    FATO_SEGURO: (
        "apólice", "apolice", "sinistro", "endosso", "vigência", "vigencia",
        "seguradora", "prêmio", "premio", "importância segurada", "susep",
        "condições gerais", "condicoes gerais", "bilhete",
    ),
    OPERACAO: (
        "renovação", "renovacao", "boleto", "cobrança", "cobranca", "2ª via",
        "segunda via", "cadastro", "atualizar", "cancelar", "emitir",
        "acionar", "abrir sinistro", "protocolo",
    ),
    ANALISE: (
        "quanto", "quantos", "relatório", "relatorio", "panorama", "carteira",
        "comissão", "comissao", "faturamento", "produção", "producao",
        "compare", "evolução", "evolucao", "ranking", "total de",
    ),
    PESQUISA: (
        "pesquis", "notícia", "noticia", "mercado", "concorr", "tendência",
        "tendencia", "o que mudou", "nova regra", "circular",
    ),
}

# Interrogativos que denunciam pergunta mesmo sem palavra de domínio.
_RE_PERGUNTA = re.compile(
    r"\b(qual|quais|quanto|quantos|quando|onde|como|por que|porque|"
    r"quem|o que|pode|consegue|tem como)\b", re.I)

# Referência a uma apólice/cliente CONCRETO. É o que separa "o seguro auto
# cobre vidro?" (pergunta de produto) de "a apólice do João cobre vidro?"
# (pergunta que exige a apólice).
_RE_ESPECIFICO = re.compile(
    r"\b(\d{11}|\d{14}|\d{3}\.\d{3}\.\d{3}-\d{2}|"           # CPF/CNPJ
    r"[A-Z]{3}-?\d[A-Z\d]\d{2}|"                              # placa
    r"ap[óo]lice\s+(n[º°.]?\s*)?[\w.\-/]{4,}|"                # apólice nº
    r"do\s+cliente|da\s+cliente|do\s+segurado|da\s+segurada|"
    r"meu\s+cliente|minha\s+cliente|do\s+s[eó]cio)\b", re.I)


@dataclass
class Intencao:
    tipo: str
    risco: str = "baixo"            # baixo | medio | alto
    especifica: bool = False        # cita apólice/cliente concreto?
    confianca: float = 0.0
    sinais: list[str] = field(default_factory=list)

    @property
    def social(self) -> bool:
        return self.tipo == CONVERSA and self.confianca >= 0.9


def classificar(texto: str) -> Intencao:
    """Classificação léxica: barata, determinística e auditável.

    Um LLM decidindo se vale a pena recuperar contexto custa mais do que a
    própria recuperação. E uma decisão que se pode ler é uma decisão que se
    pode corrigir — ao contrário de um embedding.
    """
    t = (texto or "").strip()
    if not t:
        return Intencao(CONVERSA, confianca=1.0, sinais=["vazio"])

    if _RE_SOCIAL.match(t) and len(t) <= 40:
        return Intencao(CONVERSA, confianca=0.95, sinais=["saudação"])

    baixo = t.lower()
    especifica = bool(_RE_ESPECIFICO.search(t))

    pontos: dict[str, float] = {}
    achados: dict[str, list[str]] = {}
    for tipo, pistas in _PISTAS.items():
        for p in pistas:
            if re.search(p, baixo):
                pontos[tipo] = pontos.get(tipo, 0) + 1.0
                achados.setdefault(tipo, []).append(p)

    if not pontos:
        # Sem pista de domínio: pergunta genérica pede conhecimento; frase
        # curta afirmativa não pede nada.
        if _RE_PERGUNTA.search(baixo) or len(t) > 60:
            return Intencao(PROCEDIMENTO, confianca=0.4, sinais=["pergunta genérica"])
        return Intencao(CONVERSA, confianca=0.6, sinais=["sem pista de domínio"])

    tipo = max(pontos, key=lambda k: pontos[k])

    # Cobertura vence tudo: é a pergunta que erra mais caro.
    if COBERTURA_APOLICE in pontos:
        tipo = COBERTURA_APOLICE

    risco = "baixo"
    if tipo == COBERTURA_APOLICE:
        risco = "alto" if especifica else "medio"
    elif tipo in (OPERACAO, FATO_SEGURO):
        risco = "medio"

    return Intencao(
        tipo=tipo, risco=risco, especifica=especifica,
        confianca=min(1.0, 0.45 + 0.18 * pontos[tipo]),
        sinais=achados.get(tipo, [])[:4],
    )


# --------------------------------------------------------------------------
# Plano
# --------------------------------------------------------------------------

@dataclass
class PlanoDeContexto:
    intencao: Intencao
    fontes: list[str] = field(default_factory=list)
    orcamento: int = ORCAMENTO_TOTAL
    esforco: str = "normal"          # rapido | normal | profundo
    exige_apolice: bool = False
    motivo: str = ""

    def quer(self, fonte: str) -> bool:
        return fonte in self.fontes


# Que fontes cada intenção justifica. Recuperação just-in-time da SPEC-052
# §6.3: contexto irrelevante não é neutro, ele compete com o relevante pela
# atenção do modelo.
_PLANO_POR_INTENCAO: dict[str, tuple[list[str], str]] = {
    CONVERSA: ([], "rapido"),
    PROCEDIMENTO: (["memoria_usuario", "rag_tenant"], "normal"),
    FATO_SEGURO: (["rag_tenant", "normativo", "dados_vivos"], "normal"),
    COBERTURA_APOLICE: (["dados_vivos", "normativo", "rag_tenant"], "profundo"),
    OPERACAO: (["memoria_usuario", "dados_vivos", "rag_tenant"], "normal"),
    ANALISE: (["memoria_corretora", "dados_vivos", "rag_tenant"], "profundo"),
    PESQUISA: (["rag_global", "rag_tenant"], "normal"),
}


def planejar(intencao: Intencao, *, tem_memoria: bool = True,
             orcamento: int = ORCAMENTO_TOTAL) -> PlanoDeContexto:
    fontes, esforco = _PLANO_POR_INTENCAO.get(intencao.tipo, (["rag_tenant"], "normal"))
    fontes = list(fontes)

    if not tem_memoria:
        fontes = [f for f in fontes if not f.startswith("memoria")]

    exige = intencao.tipo == COBERTURA_APOLICE and intencao.especifica

    motivo = f"intenção={intencao.tipo} risco={intencao.risco}"
    if intencao.social:
        motivo = "saudação — nenhuma recuperação necessária"
    elif exige:
        motivo += " · pergunta sobre apólice concreta: exige a apólice, não só a norma"

    return PlanoDeContexto(intencao=intencao, fontes=fontes, orcamento=orcamento,
                           esforco=esforco, exige_apolice=exige, motivo=motivo)


# --------------------------------------------------------------------------
# Evidence Pack
# --------------------------------------------------------------------------

# SPEC-052 §6.4 — precedência para fatos de seguro. Número menor manda mais.
PRECEDENCIA = {
    "evidence_apolice": 1,      # a apólice do caso
    "documento_apolice": 2,     # documento oficial daquela apólice
    "dados_vivos": 3,           # sistema de gestão (InfoCap/Quiver)
    "normativo": 4,             # condição do produto, versão correta
    "norma": 5,                 # circular/resolução vigente
    "rag_tenant": 6,            # conhecimento curado da corretora
    "rag_global": 7,            # conhecimento global curado
    "memoria_corretora": 8,
    "memoria_usuario": 9,
}


@dataclass
class Evidencia:
    fonte: str
    conteudo: str
    autoridade: int = 9
    rotulo: str = ""
    vigencia: Optional[str] = None
    emissor: Optional[str] = None
    coletado_em: Optional[str] = None
    url: Optional[str] = None

    def cabecalho(self) -> str:
        partes = [self.rotulo or self.fonte]
        if self.emissor:
            partes.append(self.emissor)
        if self.vigencia:
            partes.append(f"vigente desde {self.vigencia}")
        return " · ".join(partes)


@dataclass
class PacoteDeContexto:
    plano: PlanoDeContexto
    evidencias: list[Evidencia] = field(default_factory=list)
    caracteres: int = 0
    descartadas_por_orcamento: int = 0
    fontes_usadas: list[str] = field(default_factory=list)

    def como_bloco(self) -> str:
        """Serializa para o prompt, em ordem de autoridade."""
        if not self.evidencias:
            return ""

        partes: list[str] = []
        if self.plano.exige_apolice:
            # Esta instrução é a diferença entre um sistema útil e um passivo.
            partes.append(
                "=== ATENÇÃO — PERGUNTA SOBRE UMA APÓLICE ESPECÍFICA ===\n"
                "O material abaixo é NORMATIVO: condição geral do produto, não a "
                "apólice deste cliente. Ele descreve o que o produto normalmente "
                "cobre.\n\n"
                "NÃO afirme que a apólice deste cliente tem ou não tem cobertura "
                "com base apenas nisto. A apólice pode ter sido emitida sob outra "
                "versão da condição, ter cláusula excluída, franquia diferente ou "
                "endosso posterior.\n\n"
                "Responda o que a condição geral prevê, diga de qual versão está "
                "falando, e diga que a confirmação exige consultar a apólice do "
                "cliente.\n"
                "=== FIM DO AVISO ===")

        for e in self.evidencias:
            partes.append(f"[{e.cabecalho()}]\n{e.conteudo}")

        return "\n\n".join(partes)


def montar(plano: PlanoDeContexto, brutos: dict[str, Any]) -> PacoteDeContexto:
    """Monta o pacote: filtra pelo plano, ordena por autoridade, corta no orçamento.

    `brutos` é um dicionário fonte → conteúdo (str) ou lista de dicionários com
    `conteudo` e metadados. O que não estiver no plano é ignorado mesmo que
    tenha vindo — o plano manda, não a disponibilidade.
    """
    pacote = PacoteDeContexto(plano=plano)
    candidatas: list[Evidencia] = []

    for fonte, valor in (brutos or {}).items():
        if not valor or not plano.quer(fonte):
            continue

        autoridade = PRECEDENCIA.get(fonte, 9)
        if isinstance(valor, str):
            candidatas.append(Evidencia(
                fonte=fonte, conteudo=valor.strip(), autoridade=autoridade,
                rotulo=_ROTULO.get(fonte, fonte)))
        elif isinstance(valor, list):
            for item in valor:
                if isinstance(item, dict) and (item.get("conteudo") or item.get("content")):
                    candidatas.append(Evidencia(
                        fonte=fonte,
                        conteudo=str(item.get("conteudo") or item.get("content")).strip(),
                        autoridade=item.get("autoridade") or autoridade,
                        rotulo=item.get("rotulo") or _ROTULO.get(fonte, fonte),
                        vigencia=item.get("vigencia") or item.get("effective_from"),
                        emissor=item.get("emissor") or item.get("insurer_name"),
                        url=item.get("url") or item.get("source_url"),
                    ))
                elif isinstance(item, str) and item.strip():
                    candidatas.append(Evidencia(
                        fonte=fonte, conteudo=item.strip(), autoridade=autoridade,
                        rotulo=_ROTULO.get(fonte, fonte)))

    # Precedência primeiro; conteúdo maior desempata dentro do mesmo nível.
    candidatas.sort(key=lambda e: (e.autoridade, -len(e.conteudo)))
    candidatas = _deduplicar(candidatas)

    usados = 0
    por_fonte: dict[str, int] = {}
    for e in candidatas:
        teto = TETO_POR_FONTE.get(e.fonte, 3_000)
        ja = por_fonte.get(e.fonte, 0)
        if ja >= teto:
            pacote.descartadas_por_orcamento += 1
            continue

        espaco = min(teto - ja, plano.orcamento - usados)
        if espaco < 200:
            # Fatia menor que isso não informa nada e ainda gasta atenção.
            pacote.descartadas_por_orcamento += 1
            continue

        corpo = e.conteudo
        if len(corpo) > espaco:
            # O marcador de corte entra DENTRO do orçamento, não depois dele.
            # Cortar em `espaco` e então anexar " […]" estourava o teto em 5
            # caracteres — pouco, mas um orçamento que estoura não é orçamento,
            # e o erro se acumula a cada fonte.
            marca = " […]"
            corpo = corpo[:max(0, espaco - len(marca))].rsplit(" ", 1)[0] + marca
        e.conteudo = corpo

        pacote.evidencias.append(e)
        usados += len(corpo)
        por_fonte[e.fonte] = ja + len(corpo)
        if e.fonte not in pacote.fontes_usadas:
            pacote.fontes_usadas.append(e.fonte)

        if usados >= plano.orcamento:
            break

    pacote.caracteres = usados
    return pacote


_ROTULO = {
    "memoria_usuario": "Memória do usuário",
    "memoria_corretora": "Memória da corretora",
    "rag_tenant": "Conhecimento da corretora",
    "rag_global": "Conhecimento AutoBrokers",
    "normativo": "Condição normativa",
    "dados_vivos": "Sistema de gestão",
    "evidence_apolice": "Apólice do cliente",
    "documento_apolice": "Documento da apólice",
}


def _deduplicar(evidencias: list[Evidencia], limiar: float = 0.82) -> list[Evidencia]:
    """Remove trechos quase iguais, mantendo o de MAIOR autoridade.

    A lista já vem ordenada por precedência, então o primeiro de cada par é o
    mais autoritativo — e é ele que fica. Sem isto, a mesma cláusula viria da
    condição geral e do conhecimento da corretora, ocupando espaço duas vezes e
    dando ao modelo a impressão de duas confirmações independentes.
    """
    saida: list[Evidencia] = []
    vistos: list[set[str]] = []

    for e in evidencias:
        tokens = {t for t in re.findall(r"\w{4,}", e.conteudo.lower())[:220]}
        if not tokens:
            continue
        repetido = False
        for anterior in vistos:
            if not anterior:
                continue
            inter = len(tokens & anterior)
            if inter / max(1, min(len(tokens), len(anterior))) >= limiar:
                repetido = True
                break
        if not repetido:
            saida.append(e)
            vistos.append(tokens)
    return saida


# --------------------------------------------------------------------------
# Fachada
# --------------------------------------------------------------------------

def deve_recuperar(texto: str) -> bool:
    """Substitui `should_prefetch_rag`. Mesma pergunta, resposta com critério.

    A anterior era `len(texto) > 25`: "bom dia, tudo bem?" não buscava e "me
    manda o telefone de vocês" disparava recuperação completa.
    """
    plano = planejar(classificar(texto))
    return bool(plano.fontes)


def planejar_para(texto: str, *, tem_memoria: bool = True) -> PlanoDeContexto:
    return planejar(classificar(texto), tem_memoria=tem_memoria)
