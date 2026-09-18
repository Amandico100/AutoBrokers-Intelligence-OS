# -*- coding: utf-8 -*-
"""A Skill que responde *"tem carro reserva? cobre granizo? quantos km de guincho?"*.

SPEC-EXTRA-001.5 · BLOCO B. Módulo **puro**: sem LLM, sem I/O próprio, sem
cliente de banco montado aqui. Recebe a base pelo contrato da unidade A
(`assistance_plans_base`) e a apólice já lida pela porta da 001.1. Quem a chama
é `policy_answer_composer` — **um caminho só** (§6, forma 90).

🔴 O DEFEITO QUE ELA CONSERTA, MEDIDO
=====================================
📊 17/09/2026, `compose_policy_answer_with_meta` sobre uma apólice residencial
com assistência confirmada:

```
"ele tem carro reserva?"              -> nem entra no ramo de assistência
                                         (`_ASSIST_INTENT_RE` não casa) e a
                                         resposta é o resumo da apólice
"a assistência cobre carro reserva?"  -> "Sim — ... os serviços incluídos são:
                                         eletricista, chaveiro, hidráulica/
                                         encanador."
```

O segundo é pior que o primeiro: é um **"sim"** a uma pergunta sobre um serviço
que a regra nem conhece. `assistance_policy.py` sabe TRÊS serviços residenciais
e nada mais; qualquer outro vira "sim" por tabela. Esta Skill troca isso por um
dos cinco estados, com o documento e a página ao lado.

OS CINCO ESTADOS — E O SEXTO, QUE NÃO É ESTADO DA BASE
======================================================
```
coberto            a linha publicada diz `sim`
nao_coberto        a linha publicada diz `nao`          -> sempre com documento e página
condicionado       a linha diz `condicionado` + condição
nao_contratado     o plano dele não inclui, e um plano SUPERIOR publicado inclui
nao_sabemos_ainda  não há linha publicada, OU o plano não foi identificado
-------------------------------------------------------------------------------
fonte_indisponivel  FALHA: a base ou a apólice não abriram. TEXTO PRÓPRIO.
```

🔴 **`nao_sabemos_ainda` é acerto; "não" sem lastro é proibido** (§6.2). Os dois
primeiros defeitos que o guarda M-B1 impede são, nesta ordem: o desconhecido
virando "não cobre" (custa ao segurado um acionamento a que ele tinha direito) e
`fonte_indisponivel` saindo com o texto de `nao_sabemos_ainda` (esconde uma
queda de infraestrutura atrás de uma lacuna de curadoria, e ninguém vai
consertar o que parece falta de dado).

🔴 O PLANO VEM DA APÓLICE, NUNCA DO CHUTE (M-B4)
================================================
Plano não identificado → `nao_sabemos_ainda`. **Nunca** "o plano padrão da
seguradora", nunca o nível 1 porque é o mais comum. `EstadoDoPlano` da porta
(`policy_data_provider.py:491-507`) já diz isso com três estados; esta Skill os
LÊ, não os recria (CLAUDE.md §5).

O FALLBACK, COM MARCA
=====================
Sem linha publicada, apólice residencial com assistência confirmada e o serviço
sendo um dos TRÊS que `assistance_policy.py` conhece → a regra antiga responde,
marcada `origem='regra_generica'`, `confianca='baixa'`, e o texto diz que é
padrão de mercado e **não o contrato dele**. Para qualquer outro serviço a
resposta é `nao_sabemos_ainda` — é aí que o "sim" errado morre.

⚠️ **Um vencedor só** (M-B5): a base quando há linha publicada, o fallback
quando não há. Nunca os dois.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..knowledge import assistance_plans_base as BASE

logger = logging.getLogger(__name__)

#: Os cinco + o sexto. A ordem é a de §6.2 e não é decorativa: o sexto está
#: separado por linha porque ele NÃO é resposta da base, é falha.
ESTADOS = ("coberto", "nao_coberto", "condicionado", "nao_contratado", "nao_sabemos_ainda")
FALHA = "fonte_indisponivel"

#: 🔴 A ponte com a regra antiga. `assistance_policy.STANDARD_SERVICES` usa três
#: chaves próprias; o vocabulário usa as suas. Escrever a tradução aqui, à vista,
#: é o que impede o fallback de responder por um serviço que ele não conhece —
#: e é exatamente o "sim" medido acima.
_SERVICO_DO_FALLBACK = {
    "eletricista": "eletricista",
    "chaveiro_residencial": "chaveiro",
    "encanador": "hidraulica_encanador",
}

#: Só para o TEXTO. A chave canônica continua sendo a do vocabulário.
_ROTULO = {
    "guincho": "guincho",
    "carro_reserva": "carro reserva",
    "chaveiro": "chaveiro",
    "chaveiro_residencial": "chaveiro residencial",
    "vidros": "vidros",
    "eletricista": "eletricista",
    "encanador": "encanador",
    "hospedagem": "hospedagem",
    "taxi": "táxi",
    "borracheiro": "borracheiro",
    "pane_seca": "pane seca",
    "troca_de_pneu": "troca de pneu",
    "bateria": "bateria",
    "granizo": "granizo",
    "alagamento": "alagamento",
}


def rotulo_do_servico(servico: str) -> str:
    return _ROTULO.get(str(servico or ""), str(servico or "").replace("_", " "))


class FonteIndisponivel(Exception):
    """A base não respondeu. Não é 'não cobre' e não é 'não sabemos ainda'."""


@dataclass(frozen=True)
class VereditoDeCobertura:
    """O que a Skill devolve. Tudo o que o texto AFIRMA está aqui como campo.

    ⚠️ §14 da proposta (Citations da API Anthropic): a citação é **campo
    estruturado** — `documento_id` + `pagina` —, não prosa dentro do texto. O
    texto é montado A PARTIR deles; a tela, o registro e o guarda leem os campos.
    """

    estado: str
    servico: str
    texto: str
    tipo: Optional[str] = None
    insurer_key: Optional[str] = None
    seguradora: Optional[str] = None
    ramo: Optional[str] = None
    produto: Optional[str] = None
    plano: Optional[str] = None
    nivel: Optional[int] = None
    plano_id: Optional[str] = None
    documento_id: Optional[str] = None
    pagina: Optional[int] = None
    limite_valor: Optional[float] = None
    limite_unidade: Optional[str] = None
    limite_texto: Optional[str] = None
    carencia_dias: Optional[int] = None
    condicao: Optional[str] = None
    gancho: Optional[Dict[str, Any]] = None
    origem: str = "nenhuma"
    confianca: str = "baixa"
    motivo: Optional[str] = None
    servicos_da_base: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def tem_fonte(self) -> bool:
        return bool(self.documento_id) and bool(self.pagina)

    def para_registro(self) -> Dict[str, Any]:
        """O dict que vai ao `input_summary`/saída de `tool_invocations`.

        🔴 **Nenhum argumento cru** (§9 da SPEC): a pergunta do corretor pode
        conter CPF, telefone e placa. O que entra aqui é a PROCEDÊNCIA — estado,
        seguradora canônica, plano, documento, página — e o documento aparece
        como presença (`{"documento": "presente"}`), nunca como conteúdo.
        """
        return {
            "estado": self.estado,
            "servico": self.servico,
            "tipo": self.tipo,
            "insurer_key": self.insurer_key,
            "ramo": self.ramo,
            "produto": self.produto,
            "plano": self.plano,
            "nivel": self.nivel,
            "plano_id": self.plano_id,
            "documento_id": self.documento_id,
            "pagina": self.pagina,
            "documento": "presente" if self.documento_id else "ausente",
            "origem": self.origem,
            "confianca": self.confianca,
            "gancho": bool(self.gancho),
        }


# ---------------------------------------------------------------------------
# O texto — e a regra de §6.2 que nenhuma frase de "não" escapa
# ---------------------------------------------------------------------------
def _citacao(seguradora: Optional[str], pagina: Optional[int]) -> str:
    """*"(Condições gerais da HDI, p. 23.)"* — o lastro, sempre no mesmo formato.

    🔴 Sem página não há citação, e sem citação **não se diz "não"**. Por isso
    esta função devolve vazio em vez de inventar "(condições gerais)": uma
    citação sem página é indistinguível, para quem lê, de uma com página.
    """
    if not pagina:
        return ""
    quem = str(seguradora or "").strip()
    return " (Condições gerais da %s, p. %s.)" % (quem, pagina) if quem else " (Condições gerais, p. %s.)" % pagina


def _limite_em_palavras(linha: Dict[str, Any]) -> str:
    texto = str(linha.get("limite_texto") or "").strip()
    if texto:
        return texto
    valor, unidade = linha.get("limite_valor"), str(linha.get("limite_unidade") or "").strip()
    if valor is None or not unidade:
        # 🔴 valor sem unidade não vira texto: "200" sozinho vira "200 dias" na
        # cabeça de quem lê (a mesma recusa de `propor_servico`).
        return ""
    numero = int(valor) if float(valor) == int(float(valor)) else valor
    if unidade == "reais":
        return "até R$ %s" % numero
    legivel = {"km": "km", "dias": "dias", "acionamentos_ano": "acionamentos por ano",
               "unidades": "unidades"}.get(unidade, unidade)
    return "%s %s" % (numero, legivel)


def _frase_do_gancho(gancho: Optional[Dict[str, Any]]) -> str:
    if not gancho:
        return ""
    quem = str(gancho.get("atendente") or "").strip()
    # 🔴 D-PILOTO-12: quem cuida do caso é a ATENDENTE do card Equipe. Sem nome,
    # "nossa equipe" — nunca o nome do agente, que é escolha da corretora e não
    # é uma pessoa que possa orçar nada.
    pessoa = quem or "nossa equipe"
    limite = str(gancho.get("limite") or "").strip()
    return (
        " O plano acima (%s) tem%s — %s pode avaliar a troca na renovação."
        % (gancho.get("plano_superior"), (" %s" % limite) if limite else "", pessoa)
    )


def _texto(estado: str, *, servico: str, seguradora: Optional[str], plano: Optional[str],
           pagina: Optional[int], limite: str = "", condicao: Optional[str] = None,
           gancho: Optional[Dict[str, Any]] = None, generica: bool = False,
           motivo: Optional[str] = None) -> str:
    rot = rotulo_do_servico(servico)
    quem = str(seguradora or "a seguradora").strip()
    cita = _citacao(seguradora, pagina)

    if estado == FALHA:
        # 🔴 TEXTO PRÓPRIO — M-B1 par 2. Nem "não cobre", nem "não sabemos": não
        # OLHAMOS. Quem lê precisa saber que a informação existe e não chegou.
        return (
            "Não consegui abrir a apólice agora para conferir %s. "
            "Não é um 'não' — é uma falha minha de consulta. Tento de novo em instantes."
            % rot
        )
    if estado == "nao_sabemos_ainda":
        return (
            "Ainda não tenho as condições da %s para esse produto na base, "
            "então não vou afirmar nem que tem nem que não tem %s. "
            "Posso confirmar com a seguradora — quer que eu abra?" % (quem, rot)
        )
    if estado == "coberto":
        if generica:
            return (
                "Pelo padrão de mercado de assistência 24h residencial, %s costuma estar incluído. "
                "⚠️ Isso é o padrão, não o contrato dele: ainda não tenho as condições gerais da %s "
                "na base para confirmar limite e carência." % (rot, quem)
            )
        corpo = "Tem sim: %s" % rot
        if limite:
            corpo += " — %s" % limite
        return corpo + "." + cita
    if estado == "condicionado":
        corpo = "Tem, mas com condição: %s" % rot
        if condicao:
            corpo += " — %s" % str(condicao).strip().rstrip(".")
        if limite:
            corpo += " (%s)" % limite
        return corpo + "." + cita
    if estado == "nao_coberto":
        # 🔴 §6.2: toda frase que diz "não" carrega documento e página.
        return ("No plano dele, não. O %s da %s não inclui %s."
                % (plano or "plano contratado", quem, rot)) + cita + _frase_do_gancho(gancho)
    if estado == "nao_contratado":
        return ("O plano dele é o %s, que não inclui %s."
                % (plano or "plano contratado", rot)) + cita + _frase_do_gancho(gancho)
    return "Não consegui classificar a resposta (%s)." % (motivo or estado)


# ---------------------------------------------------------------------------
# O motor
# ---------------------------------------------------------------------------
def _seguradora_legivel(insurer_key: Optional[str], cru: Any) -> str:
    bruto = str(cru or "").strip()
    try:
        from ..policy_answer_composer import humanize_insurer

        legivel = humanize_insurer(bruto or insurer_key or "")
        if legivel:
            return legivel
    except Exception:  # noqa: BLE001 — o rótulo nunca derruba a resposta
        pass
    return bruto or str(insurer_key or "")


def _plano_superior_que_cobre(
    *, insurer_key: str, ramo: str, produto: Optional[str], nivel: Optional[int],
    servico: str, db: Any, atendente: Optional[str],
) -> Optional[Dict[str, Any]]:
    """O gancho de §6.3 — e a trava dele.

    🔴 O gancho só existe quando **existe** um plano publicado de nível maior no
    mesmo produto **e** a linha desse serviço nele diz `sim`. Com o nível
    máximo, o gancho é mentira: promete ao segurado uma troca que não tem para
    onde ir. Par de controle no M-B3.
    """
    if nivel is None:
        return None
    superiores = [
        p for p in BASE.planos_publicados(insurer_key, ramo, produto, db=db)
        if int(p.get("nivel") or 0) > int(nivel)
    ]
    for plano in sorted(superiores, key=lambda p: int(p.get("nivel") or 0)):
        linha = BASE.buscar_servico(
            insurer_key, ramo, str(plano.get("produto")), str(plano.get("plano")), servico, db=db
        )
        if linha and str(linha.get("coberto")) == "sim":
            return {
                "plano_superior": plano.get("plano"),
                "nivel": int(plano.get("nivel") or 0),
                "servico_no_superior": servico,
                "limite": _limite_em_palavras(linha),
                "documento_id": linha.get("documento_id"),
                "pagina": linha.get("pagina"),
                "atendente": atendente,
            }
    return None


def _pertence(nome: str, texto: str) -> bool:
    """O nome do plano aparece no texto, por PALAVRA INTEIRA.

    🔴 Substring foi descartada com medição e o motivo está em
    `assistance_plans_base.servico_canonico`: é o defeito que fundiu
    `"caixa seguradora"` em `axa`. Aqui, um plano chamado `"Ouro"` casaria
    dentro de `"Ouropreto"`, e o segurado receberia a cobertura de outro plano.
    """
    alvo = BASE._norm_texto(texto)
    termo = BASE._norm_texto(nome)
    if not alvo or len(termo) < 3:
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(termo)}(?![a-z0-9])", alvo))


def identificar_plano(
    *,
    insurer_key: str,
    ramo: str,
    produto: Optional[str] = None,
    fatos_da_apolice: Optional[List[Dict[str, Any]]] = None,
    texto_do_documento: Optional[str] = None,
    nome_no_sistema: Optional[str] = None,
    planos_publicados: Optional[List[Dict[str, Any]]] = None,
    documento_da_condicao: Optional[str] = None,
    data_emissao: Any = None,
    db: Any = None,
) -> Dict[str, Any]:
    """Qual dos planos PUBLICADOS desta seguradora é o do segurado?

    🔴 A pergunta é fechada de propósito: os candidatos são **os planos que a
    base publicou**, e a resposta é o nome de um deles ou nada. O contrário —
    ler um nome do PDF e criar um plano com ele — inventaria cobertura para um
    plano que ninguém curou.

    Três origens, nesta ordem, e cada uma diz de onde veio:

    ```
    documento_oficial   o bloco de assistência que o PDF da apólice traz
                        (policy_document_evidence_service.py:230-318)
    documento_oficial   o texto integral da apólice, quando o bloco não nomeia
    sistema_de_gestao   `tabela_itens` — 📊 traz o NOME do plano e nada mais
                        (policy_data_provider.py:498)
    ```

    🔴 Nenhuma casou → `estado="nao_sabemos_ainda"`. **Nunca** o nível 1 porque
    é o mais comum, nunca "o padrão da seguradora" (M-B4). E o nome mais LONGO
    vence, porque `"Completo"` e `"Auto Completo"` coexistem em catálogo e o
    curto casa dentro do longo.
    """
    candidatos = planos_publicados
    if candidatos is None:
        candidatos = BASE.planos_publicados(insurer_key, ramo, produto,
                                            data_emissao=data_emissao, db=db)
    nada = {"plano": None, "nivel": None, "estado": "nao_sabemos_ainda",
            "origem": "nenhuma", "documento_id": None, "pagina": None}
    if not candidatos:
        return nada

    # 🔴 A CONDIÇÃO GERAL DESTE CONTRATO, quando a onda 2 a encontrou pelo
    # processo SUSEP impresso na apólice. Havendo planos publicados a partir
    # DAQUELE documento, são só eles os candidatos: um plano homônimo de outro
    # produto registrado da mesma seguradora responderia a cobertura errada.
    # ⚠️ Nenhum plano daquele documento → os candidatos continuam sendo todos, e
    # a `origem` continua dizendo de onde veio o casamento. Reduzir a zero aqui
    # transformaria "ainda não curamos aquele documento" em "não sabemos nada".
    if documento_da_condicao:
        do_documento = [p for p in candidatos
                        if str(p.get("documento_id")) == str(documento_da_condicao)]
        if do_documento:
            candidatos = do_documento

    do_bloco = " \n".join(
        str(f.get("label") or "")
        for f in (fatos_da_apolice or [])
        if isinstance(f, dict) and f.get("fact_type") == "assistance"
    )
    fontes = (
        ("documento_oficial", do_bloco),
        ("documento_oficial", str(texto_do_documento or "")),
        ("sistema_de_gestao", str(nome_no_sistema or "")),
    )
    for origem, texto in fontes:
        if not str(texto or "").strip():
            continue
        casaram = [p for p in candidatos if _pertence(str(p.get("plano") or ""), texto)]
        if not casaram:
            continue
        if len(casaram) > 1:
            # 🔴 DOIS NOMES NA MESMA APÓLICE NÃO SÃO UM VENCEDOR.
            # 📊 *"...plano Essencial contratado. Conheça também o Completo."* —
            # o nome mais LONGO vencia, e o segurado do Essencial passava a
            # receber a cobertura do Completo. Texto ambíguo é lacuna, não
            # empate: quem desempata é a pessoa, não o comprimento da string.
            logger.info("[cobertura] %s planos nomeados no mesmo texto: nao escolho",
                        len(casaram))
            return dict(nada, motivo="dois_planos_no_texto")
        vencedor = casaram[0]
        return {
            "plano": vencedor.get("plano"),
            "nivel": vencedor.get("nivel"),
            "estado": "contratado",
            "origem": origem,
            "plano_id": vencedor.get("id"),
            "documento_id": vencedor.get("documento_id"),
            "pagina": vencedor.get("pagina"),
        }

    # 🔴 O PLANO ÚNICO DA CONDIÇÃO GERAL — decisão do gerente (nota 85), escrita.
    #
    # 📊 18/09/2026: **25 dos 38** planos propostos pela onda 1 chamam-se
    # "Plano único", porque a condição geral não nomeia pacote nenhum — ela
    # descreve UMA assistência. Exigir o nome no texto da apólice faz esses 25
    # nunca casarem, e a base publicada continua invisível ao segurado.
    #
    # A regra é fechada em três travas, e é a conjunção delas que a torna
    # segura — nenhuma sozinha bastaria:
    #   ① existe EXATAMENTE UM plano publicado para (seguradora, ramo, produto)
    #      vigente na emissão — com dois, escolher seria adivinhar;
    #   ② a condição geral daquele contrato foi encontrada pelo PROCESSO SUSEP
    #      impresso na própria apólice (onda 2) — não por semelhança;
    #   ③ o plano publicado veio DAQUELE documento.
    #
    # Falhando qualquer uma: `nao_sabemos_ainda`. É o que M-B4 continua guardando.
    if documento_da_condicao and len(candidatos) == 1:
        unico = candidatos[0]
        if str(unico.get("documento_id")) == str(documento_da_condicao):
            return {
                "plano": unico.get("plano"),
                "nivel": unico.get("nivel"),
                "estado": "contratado",
                "origem": "plano_unico_da_condicao_geral",
                "confianca": "media",
                "plano_id": unico.get("id"),
                "documento_id": unico.get("documento_id"),
                "pagina": unico.get("pagina"),
            }
    return nada


def responder_cobertura(
    *,
    pergunta: Any,
    apolice: Optional[Dict[str, Any]] = None,
    db: Any = None,
    atendente: Optional[str] = None,
    permitir_fallback: bool = True,
) -> Optional[VereditoDeCobertura]:
    """A pergunta + a apólice → um veredito, ou `None`.

    `None` significa *"isto não é uma pergunta de cobertura"* — o serviço não foi
    identificado no vocabulário — e o chamador segue o fluxo antigo. Não é um
    estado, e por isso não é um dos cinco.

    `apolice` (o que a porta da 001.1 já sabe, nada além):
    ```
    insurer            cru, como veio da fonte     ramo       "residencial" | "auto" | ...
    produto            "Residencial Total"          plano      o nome do plano, ou None
    nivel              int, ou None                 estado_do_plano  EstadoDoPlano da porta
    residencial        bool (o fallback exige)      assistencia_confirmada  bool
    ```
    """
    texto_da_pergunta = str(pergunta or "")
    apolice = apolice if isinstance(apolice, dict) else {}

    servico = BASE.servico_canonico(texto_da_pergunta)
    if not servico:
        return None  # 🔴 não é pergunta de cobertura: o fluxo antigo continua
    tipo = BASE.tipo_do_servico(servico)  # "assistencia" | "cobertura" (granizo!)

    ramo = str(apolice.get("ramo") or "").strip()
    produto = apolice.get("produto")
    plano = str(apolice.get("plano") or "").strip() or None
    nivel = apolice.get("nivel")
    estado_do_plano = str(apolice.get("estado_do_plano") or "nao_sabemos_ainda")

    def _sem_saber(motivo: str, insurer_key: Optional[str] = None,
                   seguradora: Optional[str] = None) -> VereditoDeCobertura:
        quem = seguradora or _seguradora_legivel(insurer_key, apolice.get("insurer"))
        return VereditoDeCobertura(
            estado="nao_sabemos_ainda", servico=servico, tipo=tipo,
            insurer_key=insurer_key, seguradora=quem, ramo=ramo or None,
            produto=produto, plano=plano, nivel=nivel, origem="nenhuma",
            confianca="baixa", motivo=motivo,
            texto=_texto("nao_sabemos_ainda", servico=servico, seguradora=quem,
                         plano=plano, pagina=None),
        )

    # ① a seguradora. Desconhecida NÃO é "não cobre": é lacuna de base.
    try:
        insurer_key = BASE.chave_de_conhecimento(apolice.get("insurer"))
    except BASE.SeguradoraDesconhecida as exc:
        logger.info("[cobertura] seguradora fora do censo: %s", exc.valor)
        return _sem_saber("seguradora_desconhecida")

    seguradora = _seguradora_legivel(insurer_key, apolice.get("insurer"))

    # ② 🔴 M-B4: o plano vem da APÓLICE. Sem plano identificado, acaba aqui —
    #    e acaba ANTES de qualquer consulta, para não haver tentação de
    #    "pegar o de nível 1, que é o mais comum".
    #
    #    ⚠️ Antes de desistir, a Skill tenta IDENTIFICAR o plano contratado
    #    contra os planos PUBLICADOS (unidade C, item 4). 📊 Sem isto,
    #    `_plano_do_pack` devolve `nao_sabemos_ainda` em 100 % dos casos reais e
    #    a base publicada nunca é alcançada. A identificação não inventa plano:
    #    ou o nome de um plano publicado está escrito na apólice, ou não está.
    #
    #    🔴 E DUAS TRAVAS QUE O M-B4 IMPÕE, e que valem mais que a conveniência:
    #    ① `nao_contratado` **não** é reaberto — a porta não está em dúvida ali,
    #       ela sabe que o plano não foi contratado; reabrir seria trocar um
    #       "não" fundamentado por um casamento de nome.
    #    ② o nome que vem do SISTEMA DE GESTÃO (`tabela_itens`) sozinho **não**
    #       identifica. 📊 É exatamente o caso que a porta marca
    #       `nao_sabemos_ainda` COM o nome presente (`policy_data_provider.py:498`:
    #       o campo traz o nome e nada mais — sem vigência, sem confirmação de
    #       contratação). `identificar_plano` aceita essa origem para quem já
    #       tenha a confirmação; a Skill não a passa.
    #    Por isso a identificação só roda com EVIDÊNCIA DO DOCUMENTO na mão — e,
    #    sem ela, a base nem chega a ser consultada.
    #    ⚠️ "Evidência do documento" inclui o ELO SUSEP: quando a condição geral
    #    deste contrato foi encontrada pelo processo impresso na apólice, o
    #    documento falou — mesmo que não nomeie pacote nenhum (o caso dos 25
    #    "Plano único").
    _tem_documento = (bool(apolice.get("fatos")) or bool(apolice.get("texto_do_documento"))
                      or bool(apolice.get("documento_da_condicao")))
    if ramo and estado_do_plano == "nao_sabemos_ainda" and _tem_documento:
        try:
            achado = identificar_plano(
                insurer_key=insurer_key, ramo=ramo, produto=produto,
                fatos_da_apolice=apolice.get("fatos"),
                texto_do_documento=apolice.get("texto_do_documento"),
                documento_da_condicao=apolice.get("documento_da_condicao"),
                data_emissao=apolice.get("data_emissao"),
                db=db,
            )
        except Exception as exc:  # noqa: BLE001 — identificar nunca derruba a resposta
            logger.info("[cobertura] identificacao indisponivel: %s", type(exc).__name__)
            achado = {"estado": "nao_sabemos_ainda"}
        if achado.get("estado") == "contratado":
            plano, nivel, estado_do_plano = achado["plano"], achado.get("nivel"), "contratado"
            logger.info("[cobertura] plano identificado pela origem %s", achado.get("origem"))

    if estado_do_plano != "contratado" or not plano or not ramo:
        # 🔴 sem plano identificado NÃO é o fim: a regra governada da casa
        # responde pelos três serviços residenciais, marcada como genérica
        # (§6.4). Sem isto o fallback é inalcançável — 📊 a porta devolve
        # `nao_sabemos_ainda` em 100 % dos casos reais, e a função acabava aqui.
        if permitir_fallback:
            generico = _fallback_residencial(
                servico=servico, tipo=tipo, apolice=apolice,
                insurer_key=insurer_key, seguradora=seguradora)
            if generico is not None:
                return generico
        return _sem_saber("plano_nao_identificado", insurer_key, seguradora)

    # ③ a base. Exceção aqui é FALHA, nunca resposta.
    try:
        linha = BASE.buscar_servico(insurer_key, ramo, str(produto or ""), plano, servico, db=db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cobertura] base indisponível: %s", type(exc).__name__)
        return VereditoDeCobertura(
            estado=FALHA, servico=servico, tipo=tipo, insurer_key=insurer_key,
            seguradora=seguradora, ramo=ramo, produto=produto, plano=plano, nivel=nivel,
            origem="nenhuma", confianca="baixa", motivo=type(exc).__name__,
            texto=_texto(FALHA, servico=servico, seguradora=seguradora, plano=plano, pagina=None),
        )

    if linha is not None:
        coberto = str(linha.get("coberto") or "")
        limite = _limite_em_palavras(linha)
        gancho = None
        if coberto == "nao":
            try:
                gancho = _plano_superior_que_cobre(
                    insurer_key=insurer_key, ramo=ramo, produto=produto, nivel=nivel,
                    servico=servico, db=db, atendente=atendente)
            except Exception as exc:  # noqa: BLE001 — o gancho nunca derruba a resposta
                logger.info("[cobertura] gancho indisponível: %s", type(exc).__name__)
        estado = {"sim": "coberto", "nao": "nao_coberto",
                  "condicionado": "condicionado"}.get(coberto, "nao_sabemos_ainda")
        if estado == "nao_sabemos_ainda":
            return _sem_saber("coberto_fora_do_vocabulario:%s" % coberto, insurer_key, seguradora)
        return VereditoDeCobertura(
            estado=estado, servico=servico, tipo=tipo, insurer_key=insurer_key,
            seguradora=seguradora, ramo=ramo, produto=produto, plano=plano, nivel=nivel,
            plano_id=linha.get("plano_id"), documento_id=linha.get("documento_id"),
            pagina=linha.get("pagina"), limite_valor=linha.get("limite_valor"),
            limite_unidade=linha.get("limite_unidade"), limite_texto=linha.get("limite_texto"),
            carencia_dias=linha.get("carencia_dias"), condicao=linha.get("condicao"),
            gancho=gancho, origem="base", confianca=str(linha.get("confianca") or "media"),
            servicos_da_base=[{"servico": servico, "rotulo": rotulo_do_servico(servico),
                               "coberto": coberto}],
            texto=_texto(estado, servico=servico, seguradora=seguradora, plano=plano,
                         pagina=linha.get("pagina"), limite=limite,
                         condicao=linha.get("condicao"), gancho=gancho),
        )

    # ④ sem linha no plano contratado. Um plano SUPERIOR cobre? -> nao_contratado.
    try:
        contratado = [
            p for p in BASE.planos_publicados(insurer_key, ramo, produto, db=db)
            if str(p.get("plano")) == plano
        ]
        gancho = _plano_superior_que_cobre(
            insurer_key=insurer_key, ramo=ramo, produto=produto, nivel=nivel,
            servico=servico, db=db, atendente=atendente)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cobertura] base indisponível (plano superior): %s", type(exc).__name__)
        return VereditoDeCobertura(
            estado=FALHA, servico=servico, tipo=tipo, insurer_key=insurer_key,
            seguradora=seguradora, ramo=ramo, produto=produto, plano=plano, nivel=nivel,
            origem="nenhuma", confianca="baixa", motivo=type(exc).__name__,
            texto=_texto(FALHA, servico=servico, seguradora=seguradora, plano=plano, pagina=None),
        )

    if gancho and contratado:
        # 🔴 O lastro aqui é a linha do PLANO contratado (documento + página do
        # plano, que a base exige de toda linha): é ela que prova que o plano
        # dele foi lido e que o serviço não está nele.
        p = contratado[0]
        return VereditoDeCobertura(
            estado="nao_contratado", servico=servico, tipo=tipo, insurer_key=insurer_key,
            seguradora=seguradora, ramo=ramo, produto=produto, plano=plano,
            nivel=int(p.get("nivel") or 0) if p.get("nivel") is not None else nivel,
            plano_id=p.get("id"), documento_id=p.get("documento_id"), pagina=p.get("pagina"),
            gancho=gancho, origem="base", confianca="media",
            servicos_da_base=[{"servico": servico, "rotulo": rotulo_do_servico(servico),
                               "coberto": "nao"}],
            texto=_texto("nao_contratado", servico=servico, seguradora=seguradora, plano=plano,
                         pagina=p.get("pagina"), gancho=gancho),
        )

    # ⑤ o FALLBACK, com marca. ⛔ UM lugar decide (CLAUDE.md §5): é a MESMA
    #    função que responde quando o plano não foi identificado.
    if permitir_fallback:
        generico = _fallback_residencial(
            servico=servico, tipo=tipo, apolice=apolice,
            insurer_key=insurer_key, seguradora=seguradora)
        if generico is not None:
            return generico

    # ⑥ 🔴 e para TODO o resto: não sabemos ainda. Nunca "sim".
    return _sem_saber("sem_linha_publicada", insurer_key, seguradora)


def _fallback_residencial(
    *, servico: str, tipo: Optional[str], apolice: Dict[str, Any],
    insurer_key: Optional[str], seguradora: Optional[str],
) -> Optional[VereditoDeCobertura]:
    """§6.4 — a regra antiga responde, MARCADA, mesmo sem plano identificado.

    🔴 POR QUE ESTE CAMINHO ESTAVA MORTO
    ====================================
    📊 18/09/2026: o fallback só era alcançado depois da trava do plano, e a
    porta devolve `nao_sabemos_ainda` em 100 % dos casos reais — a função
    encerrava antes. A apólice residencial com assistência confirmada ouvia
    *"ainda não sei se tem eletricista"*, sendo que a regra governada da casa
    afirma que tem, e afirmava antes desta SPEC existir. A 001.5 tinha tirado
    uma resposta certa do ar.

    ⚠️ **Um vencedor só** (M-B5): a base vem SEMPRE primeiro. Esta função só é
    chamada quando não há linha publicada que responda — nunca em paralelo.

    A marca é o que o mantém honesto: `origem='regra_generica'`,
    `confianca='baixa'`, e o texto diz que é padrão de mercado e **não o
    contrato dele**. Fora dos três serviços, `None` — é aí que o "sim" errado de
    `assistance_policy.py` morre.
    """
    if not _SERVICO_DO_FALLBACK.get(servico):
        return None
    if not (bool(apolice.get("residencial")) and bool(apolice.get("assistencia_confirmada"))):
        return None
    from ..assistance_policy import RULE_ID, RULE_VERSION

    return VereditoDeCobertura(
        estado="coberto", servico=servico, tipo=tipo, insurer_key=insurer_key,
        seguradora=seguradora, ramo=str(apolice.get("ramo") or "") or None,
        produto=apolice.get("produto"), plano=None, nivel=None,
        origem="regra_generica", confianca="baixa",
        motivo="%s v%s" % (RULE_ID, RULE_VERSION),
        texto=_texto("coberto", servico=servico, seguradora=seguradora, plano=None,
                     pagina=None, generica=True),
    )
