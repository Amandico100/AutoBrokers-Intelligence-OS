"""
InfoCap Policy Lookup Tool (SPEC-014 C1 slice 3).

Read-only Core tool scoped to the broker company. Connection selection is not
implemented here: the backend InfoCap endpoints own the canonical tenant
connection resolution so Chat, detail and probe share the same rule.
"""

import logging
import os
import re
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Papéis que falam com o CLIENTE FINAL (segurado) — a resposta é uma CONVERSA,
# não um relatório de apólice para o corretor (incidente 2026-07-11: o guard de
# formatação do copiloto substituía as falas do atendente pelo resumo canônico).
_CLIENT_FACING_ROLES = ("attendance", "insured_external")

# Intenção de ramo deduzida do pedido do cliente (para escolher a apólice certa
# sem perguntar: serviço de CARRO nunca é atendido por apólice de celular/vida).
#
# 🔴 SPEC-EXTRA-001.1 BLOCO B §6.3: `chaveiro` está nos DOIS regex. 📊 Medido em
# 14/09/2026, antes desta mudança: `"preciso de um chaveiro, fiquei trancado
# fora de casa"` devolvia **"auto"** — porque a função testava AUTO primeiro e
# RETORNAVA na primeira condição que casasse. Chaveiro de casa é residencial;
# chaveiro de carro é auto; a palavra sozinha **não decide**.
_AUTO_INTENT_RE = re.compile(
    r"guincho|reboque|bateria|pneu|chaveiro|socorro|pane|\bcarro\b|ve[íi]culo|moto\b|estepe|motor", re.IGNORECASE
)
_RESI_INTENT_RE = re.compile(
    r"resid[êe]nc|\bcasa\b|apartamento|encanador|eletricista|vazamento|telhado|fechadura da porta"
    r"|eletrodom[ée]stic|chaveiro",
    re.IGNORECASE,
)
_COND_INTENT_RE = re.compile(r"condom[íi]nio|s[íi]ndico|[áa]rea comum", re.IGNORECASE)
_VIDA_INTENT_RE = re.compile(r"seguro de vida|ap[óo]lice de vida|vida em grupo|\bvida\b", re.IGNORECASE)

#: A ordem é ESTÁVEL de propósito: duas famílias sinalizadas produzem sempre o
#: mesmo par, e o desempate é explícito — nunca "a primeira que casou".
_RAMOS_SINALIZADOS = (
    ("auto", _AUTO_INTENT_RE),
    ("resi", _RESI_INTENT_RE),
    ("cond", _COND_INTENT_RE),
    ("vida", _VIDA_INTENT_RE),
)

#: O DESEMPATE por contexto. ⚠️ Estes regex não repetem as palavras de serviço:
#: eles dizem ONDE o problema está. "chaveiro" + "fora de casa" é residencial;
#: "chaveiro" + "chave do carro" é auto.
_CONTEXTO_DE_RAMO = {
    "auto": re.compile(r"\bcarro\b|ve[íi]culo|autom[óo]vel|\bmoto\b|na estrada|na rodovia|garagem|placa\b", re.IGNORECASE),
    "resi": re.compile(r"porta de casa|fora de casa|em casa|minha casa|de casa|apartamento|resid[êe]nc", re.IGNORECASE),
    "cond": re.compile(r"condom[íi]nio|s[íi]ndico|[áa]rea comum", re.IGNORECASE),
    "vida": re.compile(r"seguro de vida|ap[óo]lice de vida|vida em grupo", re.IGNORECASE),
}


def _ramos_sinalizados(query: Optional[str]) -> tuple:
    """TODAS as famílias de ramo que o pedido sinaliza — não a primeira.

    🔴 Devolver a primeira é o defeito: acrescentar `chaveiro` ao regex de resi
    sem mudar isto não mudaria nada, porque AUTO é testado antes (proposta §6.3,
    a armadilha que o M-B3 existe para pegar).
    """
    texto = str(query or "")
    return tuple(familia for familia, regex in _RAMOS_SINALIZADOS if regex.search(texto))


def _desempatar_pelo_contexto(query: Optional[str], familias) -> Optional[str]:
    """Entre as famílias sinalizadas, a que o CONTEXTO da frase confirma.

    `None` quando nenhuma ou mais de uma se confirma — e `None` aqui significa
    *"ainda não sei"*, o que manda a decisão para a contagem de vigentes e, se
    nem ela resolver, para uma pergunta feita UMA vez.
    """
    texto = str(query or "")
    confirmadas = [f for f in familias
                   if f in _CONTEXTO_DE_RAMO and _CONTEXTO_DE_RAMO[f].search(texto)]
    return confirmadas[0] if len(confirmadas) == 1 else None


def _product_hint_from_query(query: Optional[str]) -> Optional[str]:
    """A família de ramo do pedido, já DESEMPATADA — ou `None`.

    ⛔ Não retorna mais na primeira condição que casa (proposta §6.3).
    """
    familias = _ramos_sinalizados(query)
    if not familias:
        return None
    if len(familias) == 1:
        return familias[0]
    return _desempatar_pelo_contexto(query, familias)


#: Os status em que a fonte NÃO isolou uma apólice — e em que a porta decide.
_STATUS_SEM_ESCOLHA = ("ambiguous_policy", "policy_number_ambiguous", "multiple_matches")


#: Como a ORIGEM de uma linha se diz ao corretor. 🔴 Nunca o nome do fornecedor
#: (§3.2): o que o corretor lê é "o sistema de gestão da corretora" e "o
#: documento oficial da apólice".
_ORIGEM_EM_PORTUGUES = {
    "sistema_de_gestao": "cadastro do sistema de gestao",
    "documento_oficial": "documento oficial da apolice",
    "catalogo": "catalogo do AutoBrokers",
    "manual": "registro manual",
}


def _pagina_da_cobertura(cobertura: Any) -> Optional[int]:
    """A página do documento, quando o extrator a devolveu. `None` é legítimo."""
    for nome in ("limite", "franquia", "premio"):
        campo = getattr(cobertura, nome, None)
        pagina = (getattr(campo, "detalhe", None) or {}).get("pagina")
        if isinstance(pagina, int):
            return pagina
    return None


def _origem_em_portugues(cobertura: Any) -> str:
    """`Cobertura.origens` → a frase que vai ao lado da linha.

    🔴 É esta frase que responde *"de onde veio esse número?"* — a pergunta que
    o §19 da proposta obriga a resposta a responder. Uma linha sem origem é
    exatamente o que o modelo canônico do BLOCO A proibiu de existir.
    """
    origens = tuple(getattr(cobertura, "origens", ()) or ())
    nomes = [_ORIGEM_EM_PORTUGUES.get(o, o) for o in origens]
    if not nomes:
        return "origem nao declarada"
    texto = " + ".join(nomes)
    pagina = _pagina_da_cobertura(cobertura)
    if pagina and "documento_oficial" in origens:
        texto += " (p. %d)" % pagina
    return texto


def _linhas_do_veredito(cobertura: Any, client_facing: bool = False) -> list:
    """O veredito determinístico da Skill, no briefing — SPEC-EXTRA-001.5 §6.

    🔴 POR QUE A LLM PRECISA DISTO ESCRITO
    ======================================
    O rascunho seguro já traz a frase certa, e o guard já anula uma resposta
    que a contrarie. Mas anular é o pior desfecho possível: o corretor recebe o
    resumo canônico no lugar de uma conversa. Dar o veredito à LLM **antes** de
    ela redigir troca "consertar depois" por "não errar" — e o estado
    `nao_sabemos_ainda` é o que mais precisa disso, porque é o único que a LLM
    tem tentação de "melhorar" para um sim.
    """
    if not isinstance(cobertura, dict) or not cobertura.get("estado"):
        return []
    estado = str(cobertura.get("estado"))
    linhas = [
        "veredito_de_cobertura (DETERMINISTICO, lido da base de planos — "
        "NAO contrarie, NAO suavize, NAO transforme em 'sim'):",
        f"- servico_perguntado: {cobertura.get('servico')} ({cobertura.get('tipo') or '-'})",
        f"- estado: {estado}",
        f"- plano_contratado: {cobertura.get('plano') or 'nao identificado'}"
        + (f" (nivel {cobertura.get('nivel')})" if cobertura.get("nivel") else ""),
        f"- seguradora: {cobertura.get('insurer_key') or '-'} · produto: {cobertura.get('produto') or '-'}",
        f"- origem: {cobertura.get('origem')} · confianca: {cobertura.get('confianca')}",
    ]
    # 🔴 SPEC-EXTRA-001.5.1 (C5) — A FONTE NÃO VIAJA NO BRIEFING DO SEGURADO.
    #
    # A linha `fonte: documento … pagina …` é um TEXTO que o modelo tende a
    # repetir, e repeti-la na conversa do WhatsApp é exatamente o defeito D10.
    # Dar a instrução ("nao cite") SEM tirar o dado seria pedir ao modelo que
    # ignorasse o que está escrito à frente dele: o dado sai, e a instrução fica.
    # ⚠️ O veredito, o estado e a origem FICAM — é deles que sai o "nao afirme
    # o que a base nega", que vale nos dois canais.
    if client_facing:
        linhas.append(
            "- 🔴 CLIENTE FINAL: NUNCA cite documento, pagina, 'condicoes gerais' "
            "nem numero de clausula. A fonte e a corretora, e ela ja conferiu."
        )
    else:
        linhas.insert(
            -1,
            f"- fonte: documento {cobertura.get('documento')} · pagina {cobertura.get('pagina') or '-'}",
        )
    if estado in ("nao_coberto", "nao_contratado"):
        # ⚠️ O MESMO fato, a MESMA recusa de inventar — e duas exigências
        # opostas sobre a CITAÇÃO, porque o lastro do corretor é a página e o
        # lastro do segurado é a corretora ter conferido.
        linhas.append(
            "- 🔴 esta resposta diz NAO: ofereca na MESMA mensagem levar o caso a "
            "equipe da corretora ('posso pedir pra alguem da equipe ver o que da "
            "pra fazer no seu caso?'). NAO diga documento nem pagina."
            if client_facing else
            "- 🔴 esta resposta diz NAO: ela TEM de citar o documento e a pagina acima. "
            "Um 'nao' sem lastro custa ao segurado um acionamento a que ele tinha direito."
        )
    if estado == "nao_sabemos_ainda":
        linhas.append(
            "- 🔴 'nao sabemos ainda' NAO e 'nao cobre'. Diga que vai confirmar para "
            "nao passar informacao errada — SEM prazo, SEM falar de base, sistema "
            "ou condicoes gerais."
            if client_facing else
            "- 🔴 'nao sabemos ainda' NAO e 'nao cobre'. Diga que a condicao geral dessa "
            "seguradora ainda nao esta na base e ofereca confirmar com a seguradora."
        )
    if estado == "fonte_indisponivel":
        linhas.append(
            "- 🔴 isto e FALHA de consulta, nao resposta: diga que nao conseguiu abrir agora."
        )
    if cobertura.get("gancho"):
        linhas.append(
            "- existe plano superior que cobre: cite a atendente do card Equipe, "
            "NUNCA preco e NUNCA promessa de que a seguradora aceita."
        )
    linhas.append("")
    return linhas


def _linhas_das_coberturas(apolice: Any) -> list:
    """As coberturas RECONCILIADAS, uma linha cada, com origem e divergência."""
    from app.providers.policy_data_provider import Indisponivel, reais

    linhas = []
    for cobertura in (getattr(apolice, "coberturas", ()) or ())[:60]:
        bits = []
        if cobertura.limite.tem_valor:
            bits.append("limite %s" % reais(cobertura.limite.valor))
        if cobertura.franquia.tem_valor:
            valor = cobertura.franquia.valor
            if not isinstance(valor, Indisponivel):
                bits.append("franquia %s" % valor)
        if cobertura.premio.tem_valor:
            bits.append("premio %s" % reais(cobertura.premio.valor))
        sufixo = " — " + " · ".join(bits) if bits else ""
        linhas.append("- %s%s — origem: %s" % (cobertura.rotulo, sufixo,
                                               _origem_em_portugues(cobertura)))
        for divergencia in cobertura.divergencias:
            linhas.append("    · as duas fontes discordam — %s (diga as duas; nao escolha por conta)"
                          % divergencia.como_frase())
    return linhas


def _linha_do_cadastro_incompleto(apolice: Any) -> Optional[str]:
    """O `Sinal("cadastro_incompleto")` em PROSA, não em código de erro."""
    from app.providers.policy_data_provider import reais

    sinal = apolice.sinal("cadastro_incompleto") if hasattr(apolice, "sinal") else None
    if sinal is None:
        return None
    detalhe = sinal.detalhe or {}
    do_cadastro = int(detalhe.get("coberturas_do_cadastro") or 0)
    total = len(getattr(apolice, "coberturas", ()) or ())
    return (
        "aviso_sobre_o_cadastro: o cadastro do sistema de gestao tem %d das %d coberturas "
        "que o documento oficial mostra; faltam %s (%s%%) do premio liquido no cadastro. "
        "As coberturas acima JA estao reconciliadas — responda por elas, e nao pelo cadastro."
        % (do_cadastro, total, reais(detalhe.get("diferenca_reais")),
           str(detalhe.get("diferenca_pct") or "-"))
    )


def _linha_da_familia_de_acionamento(insurer_key: Any) -> Optional[str]:
    """A família de acionamento da seguradora — **do CATÁLOGO, não do prompt**.

    🔴 SPEC-EXTRA-001.1 §5.4: *"Liberty e Yelum são a MESMA seguradora"* e
    *"Itaú = grupo Porto"* moravam no texto do briefing (`infocap_tool.py:453`,
    item 5). No prompt a regra vale **só enquanto o modelo obedecer**; no
    arquivo revisado ela vale sempre, e muda por revisão datada de gente.
    """
    try:
        from app.providers.susep_ses_provider import UNKNOWN, familia_de_acionamento

        familia = familia_de_acionamento(insurer_key)
        if not familia or familia == UNKNOWN:
            return None
        from app.providers.susep_ses_provider import linha_de_acionamento

        linha = linha_de_acionamento(insurer_key) or {}
        corredor = str(linha.get("corredor") or familia)
        # Só a PRIMEIRA oração do critério: o resto é a justificativa da revisão,
        # e ela mora no arquivo — o briefing carrega o motivo, não o parecer.
        criterio = str(linha.get("criterio") or "").strip()
        criterio = criterio.split(";")[0].split(":")[0].split(". ")[0].strip()
        return "seguradora_para_acionamento: %s%s" % (
            corredor, (" (%s)" % criterio) if criterio else "")
    except Exception as e:  # noqa: BLE001 — o catálogo nunca derruba a consulta
        logger.warning("[InfocapPolicyLookupTool] familia de acionamento indisponivel: %s",
                       type(e).__name__)
        return None


def _match_product_kind(match: Dict[str, Any]) -> Optional[str]:
    from app.services.policy_answer_composer import humanize_product

    label = str(humanize_product(match.get("product")) or "").strip().lower()
    if label.startswith("auto"):
        return "auto"
    if label.startswith("resid"):
        return "resi"
    return None


class InfocapLookupInput(BaseModel):
    document: Optional[str] = Field(default=None, description="CPF/CNPJ do cliente.")
    name: Optional[str] = Field(default=None, description="Nome do cliente, quando nao houver CPF/CNPJ.")
    policy_number: Optional[str] = Field(default=None, description="Numero humano da apolice informado pelo corretor.")
    policy_ref: Optional[str] = Field(
        default=None,
        # 🔴 G1b da fronteira (SPEC-EXTRA-001.1 §3.2): a descricao do argumento e
        # TEXTO QUE CHEGA AO MODELO. Ate 14/09/2026 ela ensinava o formato interno
        # do fornecedor — e o modelo repetia o formato ao corretor. A referencia e
        # OPACA de proposito: quem a monta e a porta (`parse_policy_locator_ref`).
        description="Referencia tecnica opaca da apolice, devolvida pela consulta anterior. Repasse-a como veio; nunca a construa nem a exiba.",
    )
    document_evidence_requested: Optional[bool] = Field(
        default=None,
        # 🔴 §8.1: o campo continua no esquema porque modelos antigos e chamadas
        # em curso ainda o enviam — mas ele NAO decide mais nada. O documento
        # oficial e lido sempre que esta ferramenta e chamada. Uma descricao que
        # continuasse dizendo "use true quando..." ensinaria o modelo a achar
        # que existe um caso em que o PDF nao e lido (CLAUDE.md §12.1).
        description="Ignorado: o documento oficial da apolice e sempre lido nesta consulta.",
    )


#: 🔴 SPEC-EXTRA-001.1 §8.1 — O DOCUMENTO OFICIAL É LIDO SEMPRE.
#:
#: ```
#: a pergunta é SOBRE APÓLICE?  →  o documento oficial é lido. Ponto.
#: ```
#:
#: E "sobre apólice" é decidido pelo **DESTINO DA CHAMADA**, não pelo texto: se
#: esta ferramenta foi chamada, a pergunta é de apólice. 📊 Medido em 14/09/2026:
#: o gatilho anterior era `policy_document_evidence_requested(user_query)`, uma
#: lista de palavras sobre a última mensagem — e *"[CPF]"* (q1 do corpus) e
#: *"qual cobertura o segurado [CNPJ] tem na apolice?"* (q4) **não casavam**,
#: então o PDF não era lido justamente nas perguntas que dependem dele.
#:
#: ⚠️ `policy_document_evidence_requested(question, explicit=False)` CONTINUA
#: existindo e continua sendo por palavra: outros chamadores (que não são a
#: tool de apólice) dependem dela. O que muda é que a tool passa `explicit`.
#:
#: 📊 O que torna isto barato, MEDIDO e não suposto: o documento fica guardado
#: no `DocumentService` por `corretora + locator`, e a segunda leitura da mesma
#: apólice NÃO baixa o PDF de novo —
#: `tests/test_infocap_official_policy_evidence_pipeline.py:201-202` afirma
#: *"cache miss busca PDF uma vez"* e *"cache hit nao faz novo fetch"*, as duas
#: com `fetcher.calls == 1`.
#: ⚠️ E o cache é DURÁVEL, não de 180 s: os 180 s são do `/itens` no Redis
#: (`infocap_connector.py`, `_fetch_policy_items`) — outra coisa.
#:
#: 🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2) mora fora daqui: *"quantos clientes
#: eu tenho?"* não chama esta ferramenta, e por isso não lê documento nenhum.
#: `test_o_documento_e_lido_sempre_que_a_pergunta_e_de_apolice.py` mede as duas
#: pontas — 7 de 7 pela tool, 0 de 1 no controle.
_LER_SEMPRE_O_DOCUMENTO = True


def _internal_key() -> Optional[str]:
    return os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")


class InfocapPolicyLookupTool(BaseTool):
    name: str = "infocap_policy_lookup"
    description: str = (
        "Apolices da propria corretora no sistema de gestao dela: dados do segurado e do risco, COBERTURAS ITEM A ITEM "
        "com limite/LMI, FRANQUIA e PREMIO de cada uma, premio total, vigencia, parcelas/boletos e, "
        "quando a fonte entrega o PDF da apolice, o TEXTO do documento oficial para o que nao e estruturado. "
        "Busque por CPF/CNPJ, nome do segurado, numero da apolice ou policy_ref. "
        "SEMPRE chame esta ferramenta antes de dizer que nao tem cobertura, franquia, premio ou detalhe de apolice — "
        "nunca responda 'nao consigo buscar essa informacao' sem ter chamado. Nao inventa o que a fonte nao trouxer."
    )
    args_schema: Type[BaseModel] = InfocapLookupInput

    company_id: str = ""
    provider_key: str = "infocap"  # SPEC-016 E5: provider de gestão da corretora (porta PolicyDataProvider)
    # SPEC-017 P3 — exposição por papel: Core interno = dados completos;
    # attendance (segurado)/auxiliar = mascarado (G20/S04/S05).
    agent_role: str = "core"

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, agent_role: str = "core", **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.agent_role = str(agent_role or "core").strip().lower() or "core"

    @property
    def _unmasked(self) -> bool:
        return self.agent_role in ("", "core")

    @staticmethod
    def _doc_para_o_publico(doc: Any, unmasked: bool) -> Optional[str]:
        """O CPF só aparece por inteiro para quem é de dentro da corretora.

        SPEC-063 Bloco A. O tool já sabia distinguir o público desde
        `_client_facing` — mas `_summarize` e `_summarize_detail` são
        `@staticmethod` e nunca receberam essa informação. Resultado: os dois
        renderizadores de fallback imprimiam `CPF/CNPJ: {doc}` cru, inclusive no
        caminho que fala com o SEGURADO pelo WhatsApp.

        Consertar só o prompt teria deixado este caminho aberto — e quem
        consertasse acharia que tinha resolvido. Por isso o corte é aqui, no
        lugar que escreve, e não numa instrução que o modelo pode ignorar.

        Para o segurado o documento vira sufixo: ele confirma identidade sem
        expor o número numa conversa que pode ser encaminhada.
        """
        s = "".join(ch for ch in str(doc or "") if ch.isdigit())
        if not s:
            return None
        if unmasked:
            return str(doc)
        return f"•••{s[-4:]}" if len(s) >= 4 else "•••"

    @property
    def _client_facing(self) -> bool:
        return self.agent_role in _CLIENT_FACING_ROLES

    async def _quem_cuida(self, db: Any, user_query: Optional[str]) -> Optional[str]:
        """O nome da atendente desta corretora, ou `None`. **Nunca levanta.**

        🔴 SPEC-EXTRA-001.5.1 (D11). ⛔ NENHUMA regra nova e NENHUM nome escrito
        em código: a fonte é `nome_de_quem_vai_atender`
        (`o_fim_do_atendimento.py:2392`), que já é a autoridade de "quem recebe o
        caso" no prompt do atendimento e já aplica a regra fechada de
        `atendente_de_plantao` — **exatamente UM** membro ativo não-owner da
        corretora vira nome; zero ou vários viram `None`, e `None` vira
        "nossa equipe" no texto. Um segundo critério aqui seria uma segunda
        verdade sobre a mesma pessoa (CLAUDE.md §5).

        ⚠️ E a consulta só acontece quando a pergunta É de cobertura: o
        vocabulário responde isso em memória, sem tocar no banco. Sem esta
        porta, toda consulta de apólice pagaria dois `select` por uma linha de
        texto que nem vai aparecer.
        """
        try:
            from app.services.knowledge.assistance_plans_base import servico_canonico

            if not servico_canonico(str(user_query or "")):
                return None
        except Exception as exc:  # noqa: BLE001 — sem vocabulário, sem nome
            logger.warning("[InfocapPolicyLookupTool] vocabulario indisponivel: %s",
                           type(exc).__name__)
            return None
        try:
            from app.services.o_fim_do_atendimento import nome_de_quem_vai_atender

            return await nome_de_quem_vai_atender(db, self.company_id)
        except Exception as exc:  # noqa: BLE001 — o nome nunca derruba a consulta
            logger.warning("[InfocapPolicyLookupTool] equipe indisponivel: %s",
                           type(exc).__name__)
            return None

    async def _arun(
        self,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_number: Optional[str] = None,
        policy_ref: Optional[str] = None,
        document_evidence_requested: Optional[bool] = None,
        user_query: Optional[str] = None,
        force_document_evidence_refresh: bool = False,
        selected_policy_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not document and not name and not policy_number and not policy_ref:
            return {"content": "Informe CPF/CNPJ, nome do cliente, numero da apolice, ou um policy_ref para detalhar a apolice.", "found": False}
        key = _internal_key()
        if not key:
            return {"content": "Consulta ao sistema de gestao da corretora indisponivel: configuracao interna ausente.", "found": False}
        try:
            from app.core.database import create_async_supabase_client

            db = await create_async_supabase_client()

            # SPEC-016 E5: a tool fala com a PORTA PolicyDataProvider, nunca com o
            # conector concreto. InfoCap é o provider piloto; Quiver futuro entra
            # pela mesma porta.
            from app.providers.policy_data_provider import (
                get_policy_data_provider,
                parse_policy_locator_ref,
            )

            provider = get_policy_data_provider(self.provider_key)
            if provider is None:
                return {"content": "Nenhum provider de apolices configurado para a corretora.", "found": False}

            if policy_ref and not parse_policy_locator_ref(str(policy_ref)):
                # P0.1: referência simples enviada pela LLM é número humano.
                policy_number = str(policy_ref)
                policy_ref = None

            if policy_ref:
                det = await provider.detail(
                    company_id=self.company_id,
                    policy_ref=str(policy_ref),
                    user_query=user_query,
                    document_evidence_requested=_LER_SEMPRE_O_DOCUMENTO,
                    force_document_evidence_refresh=bool(force_document_evidence_refresh),
                    unmasked=self._unmasked,
                    db=db,
                    internal_key=key,
                )
                content, assistance_policy, rendered, meta = self._render_content(
                    det, user_query, detail=True,
                    atendente=await self._quem_cuida(db, user_query))
                contract = self._build_policy_response_contract(det, rendered, assistance_policy, client_facing=self._client_facing, meta=meta)
                await self._lacuna_vira_tarefa(db, meta, user_query)
                return {"content": content, "data": det, "found": bool(det.get("ok")),
                        "policy_response_contract": contract,
                        "cobertura": (meta or {}).get("cobertura")}

            result = await provider.lookup(
                company_id=self.company_id,
                document=document or None,
                name=name or None,
                policy_number=policy_number or None,
                user_query=user_query,
                document_evidence_requested=_LER_SEMPRE_O_DOCUMENTO,
                force_document_evidence_refresh=bool(force_document_evidence_refresh),
                unmasked=self._unmasked,
                db=db,
                internal_key=key,
            )
            # 🔴 A ESCOLHA acontece na PORTA, e vale para TODOS OS PAPÉIS.
            # `self._client_facing` saiu daqui de propósito (SPEC-EXTRA-001.1
            # §6.3, correção 1): o que muda entre o Chat Principal e o
            # atendimento é a REDAÇÃO da resposta, nunca QUAL apólice é a certa.
            # 📊 Era por isso que o corretor recebia a lista e o segurado não.
            if not policy_number and str(result.get("status") or "") in _STATUS_SEM_ESCOLHA:
                picked, escolha = await self._escolher_pela_porta(
                    provider, result,
                    cliente_ref=(document or name or ""),
                    user_query=user_query,
                    selected_policy_number=selected_policy_number,
                    db=db, key=key,
                )
                if picked:
                    result = await provider.lookup(
                        company_id=self.company_id,
                        document=document or None,
                        name=name or None,
                        policy_number=picked,
                        user_query=user_query,
                        document_evidence_requested=_LER_SEMPRE_O_DOCUMENTO,
                        force_document_evidence_refresh=bool(force_document_evidence_refresh),
                        unmasked=self._unmasked,
                        db=db,
                        internal_key=key,
                    )
                if escolha is not None:
                    self._anotar_a_escolha(result, escolha)
            elif policy_number and str(result.get("status") or "") == "policy_number_ambiguous":
                # 🔴 A PORTA POR ONDE A VENCIDA AINDA VIRAVA OPCAO. O ramo acima
                # so roda quando o corretor NAO informou numero — e
                # `policy_number_ambiguous` so acontece quando ele informou. 📊
                # Ate 14/09/2026 os `matches` deste status iam CRUS do conector
                # para o briefing, com `policy_status` do fornecedor, e o guarda
                # de `nodes.py` obrigava a listar todos: uma apolice vencida ha
                # anos voltava a ser oferecida como opcao.
                result = await self._desempatar_pelo_numero(
                    provider, result, user_query=user_query, db=db, key=key,
                    force_refresh=bool(force_document_evidence_refresh),
                )
            # ⚠️ `policies_all` e a lista INTEIRA que a DECISAO usou (§6.1). Ela
            # ja fez o trabalho dela: deixa-la no `data` so engordaria o que
            # chega ao modelo — com a v2 desligada, `nodes.py` serializa o `data`
            # inteiro — e duplicaria `matches` linha por linha.
            result.pop("policies_all", None)
            # FICHA do atendimento: para apólice AUTO, placa/veículo/contato vêm
            # da fonte (o atendente NUNCA pede placa ao cliente). Vale para TODOS
            # os papéis — o Chat Principal (corretor) também precisa desses dados
            # (12/07: "cadê os dados do veículo" — a ficha era só client_facing).
            if str(result.get("status") or "") == "found":
                await self._enrich_vehicle(result, provider, document, db, key)
            content, assistance_policy, rendered, meta = self._render_content(
                result, user_query, detail=False,
                atendente=await self._quem_cuida(db, user_query))
            contract = self._build_policy_response_contract(result, rendered, assistance_policy, client_facing=self._client_facing, meta=meta)
            await self._lacuna_vira_tarefa(db, meta, user_query)
            # 🔴 SPEC-EXTRA-001.5 BLOCO E: a `cobertura` (estado · seguradora ·
            # plano · documento · página) viaja no RETORNO da tool, e é dali que
            # `invocation_recorder` a resume para `tool_invocations`. Nenhum
            # segundo registro (CLAUDE.md §5) e nenhum argumento cru: o dict vem
            # de `VereditoDeCobertura.para_registro()`, que não carrega texto.
            return {"content": content, "data": result, "found": bool(result.get("ok")),
                    "policy_response_contract": contract,
                    "cobertura": (meta or {}).get("cobertura")}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[InfocapPolicyLookupTool] erro: {type(e).__name__}")
            return {"content": "Nao consegui consultar o sistema de gestao da corretora agora. Tente novamente em instantes.", "found": False, "error": type(e).__name__}

    def _run(
        self,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_number: Optional[str] = None,
        policy_ref: Optional[str] = None,
        document_evidence_requested: Optional[bool] = None,
        user_query: Optional[str] = None,
        force_document_evidence_refresh: bool = False,
    ) -> Dict[str, Any]:
        return {"content": "Consulta ao sistema de gestao da corretora deve ser executada de forma assincrona.", "found": False}

    async def _escolher_pela_porta(
        self,
        provider,
        result: Dict[str, Any],
        *,
        cliente_ref: str,
        user_query: Optional[str],
        selected_policy_number: Optional[str],
        db,
        key: str,
    ):
        """A lista INTEIRA pela porta → `escolher_apolice` → (numero, Escolha).

        🔴 A tool **não** classifica vigência e **não** escolhe: ela só chama.
        A regra é `classificar_vigencia` + `escolher_apolice`, em
        `app/providers/policy_data_provider.py` (CLAUDE.md §5 — motor paralelo
        é proibido).

        ⚠️ `resposta_do_lookup=result` evita a SEGUNDA viagem à fonte: o
        adaptador recebe de volta a resposta que ele mesmo produziu.
        """
        from app.providers.policy_data_provider import escolher_apolice, numero_humano_de
        from app.services.policy_answer_composer import humanize_insurer, humanize_product

        lista = await provider.listar_apolices(
            company_id=self.company_id,
            cliente_ref=cliente_ref,
            incluir_vencidas=True,          # a escolha PRECISA ver as vencidas (§6.2)
            db=db, internal_key=key,
            resposta_do_lookup=result,
        )
        if not lista.itens and lista.total <= 0:
            return None, None

        # ② A FICHA do atendimento vence a dedução: se o caso já confirmou uma
        #    apólice e ela continua na lista, é ela — sem perguntar de novo.
        da_ficha = str(selected_policy_number or "").strip()
        if da_ficha:
            for item in lista.itens:
                if numero_humano_de(item, ausente="") == da_ficha:
                    return da_ficha, None

        ramo = self._ramo_do_pedido(user_query, lista)
        escolha = escolher_apolice(
            lista, ramo=ramo,
            humanizar_seguradora=humanize_insurer, humanizar_ramo=humanize_product,
        )
        if escolha.status == "found" and escolha.apolice is not None:
            numero = numero_humano_de(escolha.apolice, ausente="")
            if numero:
                logger.info(
                    "[InfocapPolicyLookupTool] apolice %s auto-selecionada pela porta (papel=%s)",
                    numero[:6] + "***", self.agent_role,
                )
                return numero, escolha
            # Sem número humano não há como repedir o detalhe: a escolha vira
            # pergunta em vez de virar chute.
            return None, escolha
        return None, escolha

    async def _desempatar_pelo_numero(
        self, provider, result: Dict[str, Any], *,
        user_query: Optional[str], db, key: str, force_refresh: bool,
    ) -> Dict[str, Any]:
        """O número humano casou com mais de uma apólice — e a VENCIDA sai.

        🔴 A regra é a MESMA de `ambiguous_policy`: `classificar_vigencia` +
        `escolher_apolice`, na porta. A tool não classifica e não escolhe.

        ⚠️ Aqui o desempate NÃO pode ser "chame de novo com o número": o número
        é justamente o que está ambíguo. Quem isola a apólice é a REFERÊNCIA
        opaca (`apolice_ref`), pelo `detail` — o mesmo caminho que a tool já usa
        quando o modelo devolve um `policy_ref`.

        ⛔ E quando não sobra nenhuma vigente, o status **não** vira
        `sem_vigente`: a frase da §6.2 diz *"deste cliente"*, e esta lista é a
        das apólices com o mesmo NÚMERO, não a do cliente. O que muda é a
        situação impressa, que passa a ser a da DATA.
        """
        from app.providers.policy_data_provider import escolher_apolice, opcoes_em_texto
        from app.services.policy_answer_composer import humanize_insurer, humanize_product

        try:
            lista = await provider.listar_apolices(
                company_id=self.company_id, cliente_ref="",
                incluir_vencidas=True, db=db, internal_key=key,
                resposta_do_lookup=result,
            )
        except Exception as e:  # noqa: BLE001 — a porta nunca derruba a consulta
            logger.warning("[InfocapPolicyLookupTool] desempate pelo numero indisponivel: %s",
                           type(e).__name__)
            return result
        if not lista.itens:
            return result

        escolha = escolher_apolice(
            lista, ramo=self._ramo_do_pedido(user_query, lista),
            humanizar_seguradora=humanize_insurer, humanizar_ramo=humanize_product,
        )
        if escolha.status == "found" and escolha.apolice is not None and escolha.apolice.apolice_ref:
            det = await provider.detail(
                company_id=self.company_id,
                policy_ref=str(escolha.apolice.apolice_ref),
                user_query=user_query,
                document_evidence_requested=_LER_SEMPRE_O_DOCUMENTO,
                force_document_evidence_refresh=force_refresh,
                unmasked=self._unmasked, db=db, internal_key=key,
            )
            if isinstance(det, dict) and det.get("ok"):
                det["auto_selected_reason"] = escolha.auto_selected_reason or (
                    "o número informado aparece em mais de uma apólice, e esta é a única "
                    "que está valendo hoje")
                return det

        # Não deu para escolher UMA: as opções continuam, mas JÁ CLASSIFICADAS.
        refs = {a.apolice_ref for a in (escolha.opcoes or lista.itens)}
        crus = [m for m in (result.get("policies_all") or result.get("matches") or [])
                if isinstance(m, dict)]
        filtradas = [m for m in crus if str(m.get("policy_locator_ref") or "") in refs]
        if filtradas:
            result["matches"] = filtradas
        result["opcoes_vigentes_em_texto"] = opcoes_em_texto(escolha.opcoes or lista.itens)
        return result

    def _ramo_do_pedido(self, user_query: Optional[str], lista) -> Optional[str]:
        """A família de ramo do pedido: ① explícito ③ as 3 últimas humanas
        ④ o serviço — e o desempate pelo número de VIGENTES por ramo.

        📊 `"chaveiro"` sozinho, num cliente com 1 auto e 1 residencial
        vigentes, não tem como ser resolvido por texto: aí — e só aí — se
        pergunta, UMA vez (proposta §6.3).
        """
        from app.providers.policy_data_provider import familia_de_ramo

        familias = _ramos_sinalizados(user_query)
        if not familias:
            return None
        if len(familias) == 1:
            return familias[0]
        pelo_contexto = _desempatar_pelo_contexto(user_query, familias)
        if pelo_contexto:
            return pelo_contexto
        # Desempate final: quantas VIGENTES o cliente tem de cada família?
        com_vigente = [
            f for f in familias
            if any(familia_de_ramo(a.ramo) == f for a in lista.vigentes)
        ]
        return com_vigente[0] if len(com_vigente) == 1 else None

    @staticmethod
    def _anotar_a_escolha(result: Dict[str, Any], escolha) -> None:
        """O que a porta decidiu entra no `data` — e por isso no briefing.

        🔴 `historico_oculto` é o que torna a ocultação HONESTA: o corretor vê
        que existe histórico e sabe pedir. Esconder sem dizer é o defeito que a
        §6.1 fecha.
        """
        from app.providers.policy_data_provider import numero_humano_de

        result["historico_oculto"] = int(getattr(escolha, "historico_oculto", 0) or 0)
        if escolha.status == "found" and escolha.auto_selected_reason:
            result["auto_selected_reason"] = escolha.auto_selected_reason
        if escolha.status == "sem_vigente":
            # ⛔ A resposta NÃO é "não encontrei" (§6.2): o cliente TEM
            # histórico, e dizer que não há nada faz o corretor refazer a busca.
            result["status"] = "sem_vigente"
            result["ok"] = False
            result["matches"] = []
            result["frase_sem_vigente"] = escolha.frase_sem_vigente
            if escolha.ultima_vigente is not None:
                ultima = escolha.ultima_vigente
                result["ultima_vigente"] = {
                    "policy_number": numero_humano_de(ultima, ausente=""),
                    "insurer_key": ultima.seguradora.nome_listado,
                    "product": ultima.ramo.abreviatura,
                    "valid_to": ultima.vigencia.fim.strftime("%d/%m/%Y") if ultima.vigencia.fim else None,
                }
        elif escolha.status == "ambiguous_policy":
            # 🔴 As opções JÁ FILTRADAS: só vigentes, só do ramo quando houver.
            # Vencida nunca vira opção.
            refs = {a.apolice_ref for a in escolha.opcoes}
            crus = [m for m in (result.get("policies_all") or result.get("matches") or [])
                    if isinstance(m, dict)]
            filtradas = [m for m in crus if str(m.get("policy_locator_ref") or "") in refs]
            result["matches"] = filtradas or result.get("matches") or []
            # 🔴 §7.1: o TEXTO das opções vem da PORTA, sobre as `ApoliceNaLista`
            # já classificadas — e por isso a situação é a da DATA, nunca o
            # `policy_status` cru do fornecedor (📊 3 residenciais "ativo", uma só
            # vigente). O briefing imprime este texto; ele nunca é remontado lá.
            from app.providers.policy_data_provider import opcoes_em_texto

            result["opcoes_vigentes_em_texto"] = opcoes_em_texto(escolha.opcoes)

    async def _enrich_vehicle(self, result: Dict[str, Any], provider, document: Optional[str], db, key: str) -> None:
        """FICHA do atendimento: anexa placa/veículo da apólice AUTO selecionada
        (porta provider.vehicle — a mesma do portal de vidros). Best-effort."""
        try:
            selected = result.get("selected") or result.get("policy") or {}
            # 🔴 §5.1.1: o `hasattr(provider, "vehicle")` SAIU. `vehicle` esta
            # no `Protocol` (depreciado) e o registry RECUSA adaptador sem ele.
            if _match_product_kind(selected) != "auto":
                return
            doc = str(document or result.get("client_document") or "").strip()
            number = str(selected.get("policy_number") or selected.get("numapo") or "").strip()
            if not doc:
                return
            info = await provider.vehicle(
                company_id=self.company_id, document=doc,
                policy_number=number or None, db=db, internal_key=key,
            )
            veh = (info or {}).get("vehicle") or {}
            if info.get("ok") and (veh.get("placa") or veh.get("veiculo")):
                result["vehicle_info"] = {
                    "placa": str(veh.get("placa") or "").strip().upper(),
                    "veiculo": str(veh.get("veiculo") or "").strip(),
                }
                # Contato do cliente na fonte (quando a porta devolve) — o
                # corretor pergunta "qual o telefone dele?" no Chat Principal.
                cli = (info or {}).get("client") or {}
                fone = str(cli.get("telefone") or cli.get("phone") or cli.get("celular") or "").strip()
                if fone:
                    result["vehicle_info"]["telefone_cliente"] = fone
        except Exception as e:  # noqa: BLE001 — a ficha nunca derruba a consulta
            logger.warning(f"[InfocapPolicyLookupTool] vehicle enrich falhou: {type(e).__name__}")


    async def _lacuna_vira_tarefa(self, db: Any, meta: Optional[Dict[str, Any]],
                                  user_query: Optional[str]) -> None:
        """O que a Skill NÃO soube responder vira tarefa — SPEC-EXTRA-001.5.1 (D12).

        🔴 O chamador é a TOOL, não a Skill nem o compositor, e por um motivo:
        ela é o único lugar deste caminho que tem `company_id`, o CANAL
        (`_client_facing`) e um cliente de banco na mão ao mesmo tempo. A Skill
        continua **pura** (CLAUDE.md §5: nenhum I/O nasce dentro dela) e o
        compositor continua sem saber de que corretora é a pergunta.

        ⛔ **Nunca derruba a consulta.** O serviço já trata as próprias falhas;
        este `try` é o cinto de segurança do import.
        """
        try:
            from app.services.lacunas_de_conhecimento import registrar_lacuna

            await registrar_lacuna(
                db=db, company_id=self.company_id,
                canal=("segurado" if self._client_facing else "corretor"),
                cobertura=(meta or {}).get("cobertura"),
                pergunta=user_query)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[InfocapPolicyLookupTool] lacuna nao registrada: %s",
                           type(exc).__name__)

    def _render_content(self, data: Dict[str, Any], user_query: Optional[str], detail: bool,
                        atendente: Optional[str] = None):
        """SPEC-016.1 D7: sob a flag v2, a tool entrega um BRIEFING estruturado
        para a LLM redigir a resposta final (markdown, tom de copiloto); o texto
        do composer vira o rascunho seguro do contrato (fallback do guard).

        Retorna (content_para_llm, assistance_policy, rendered_fallback, meta).

        🔴 O quarto item é o `meta` INTEIRO do compositor — e existe por causa
        da SPEC-EXTRA-001.5: o veredito de cobertura (`meta["cobertura"]`, com
        estado, plano, documento e página) e `assistencia_da_base` precisam
        chegar ao CONTRATO e ao RETORNO da tool. Passar só `assistance_policy`,
        como antes, obrigaria a recompor a resposta para descobrir de onde ela
        veio — e recompor é a porta de entrada de um segundo motor."""
        # 🔴 §6.2: sem apólice vigente, a resposta é a frase da porta — nunca
        # "não encontrei" e nunca uma lista de opções vazia. O compositor não
        # conhece este estado (ele é novo), então o curto-circuito vem ANTES
        # dele, e o mesmo texto vira `content` e `rendered`.
        frase = str((data or {}).get("frase_sem_vigente") or "").strip()
        if frase:
            return frase, None, frase, None
        try:
            from app.core.feature_flags import policy_intelligence_v2_enabled

            if policy_intelligence_v2_enabled():
                from app.services.policy_answer_composer import compose_policy_answer_with_meta

                # 🔴 SPEC-EXTRA-001.5.1 (D10/D11): o CANAL e a ATENDENTE entram
                # aqui, e só aqui. `self._client_facing` já existia e já dizia
                # com quem se fala; até 19/09/2026 ele não chegava ao compositor,
                # e o segurado recebia no WhatsApp o texto do corretor — com a
                # citação "(Condições gerais da HDI, p. 23.)" e com "no plano
                # **dele**".
                meta = compose_policy_answer_with_meta(
                    question=str(user_query or ""), result=data,
                    atendente=atendente, client_facing=self._client_facing)
                rendered = str(meta.get("text") or "")
                if rendered:
                    if str(data.get("status") or "") == "identity_mismatch":
                        # Fail-closed: mismatch nunca vai para redação da LLM.
                        return rendered, meta.get("assistance_policy"), rendered, meta
                    briefing = self._build_llm_briefing(data, meta, user_query, client_facing=self._client_facing)
                    return briefing, meta.get("assistance_policy"), rendered, meta
        except Exception as e:  # noqa: BLE001 — composer nunca pode derrubar a tool
            logger.warning(f"[InfocapPolicyLookupTool] composer v2 indisponivel, usando resumo legado: {type(e).__name__}")
        legacy = (self._summarize_detail(data, unmasked=self._unmasked) if detail
                  else self._summarize(data, unmasked=self._unmasked))
        return legacy, None, legacy, None

    @staticmethod
    def _build_llm_briefing(data: Dict[str, Any], meta: Dict[str, Any], user_query: Optional[str], client_facing: bool = False) -> str:
        """Briefing interno para a LLM redigir a resposta final em markdown."""
        from app.services.policy_answer_composer import humanize_insurer, humanize_product

        status = str(data.get("status") or "")
        pack = data.get("policy_evidence_pack") or {}
        selected = data.get("selected") or data.get("policy") or {}
        facts = meta.get("facts") or []
        policy_result = meta.get("assistance_policy") or {}

        lines = [
            "[DADOS INTERNOS DA CONSULTA DE APOLICE — nao exiba este bloco cru; redija a resposta final]",
            f"status_da_consulta: {status}",
        ]
        client_bits = [str(data.get("client_name") or "").strip(), str(data.get("client_document") or "").strip()]
        client_text = " — ".join(b for b in client_bits if b)
        if client_text:
            lines.append(f"cliente: {client_text}")
        if isinstance(selected, dict) and selected:
            # 🔴 O numero humano vem da PORTA (`numero_humano_de`): ela e que sabe
            # quais chaves o carregam e que "0"/"000"/vazio NAO sao numero. A tool
            # nomeava o campo do fornecedor aqui ate 14/09/2026 (G1b da fronteira).
            from app.providers.policy_data_provider import classificar_vigencia, numero_humano_de

            number = numero_humano_de(selected, ausente="nao retornado")
            insurer = humanize_insurer(selected.get("insurer_key"))
            product = humanize_product(selected.get("product"))
            # 🔴 QUEM DECIDE VIGENCIA E A DATA, e o briefing tem de DIZER isso.
            # Ate 14/09/2026 esta linha imprimia `situacao: {policy_status}` cru
            # — e 📊 as 2 de 2 apolices do golden trazem
            # `policy_status = "Recebido e nao entregue ao cliente"`, as DUAS
            # VIGENTES. O modelo recebia um estado de ENTREGA DE DOCUMENTO com o
            # rotulo `situacao`, na mesma linha da vigencia; a instrucao 6 do
            # bloco do SEGURADO neutralizava isso, a do CORRETOR nao existia.
            vigencia = classificar_vigencia(
                selected.get("valid_from"), selected.get("valid_to"), selected.get("cancelled"))
            lines.append(
                f"apolice_selecionada: {number} — {insurer or '-'} {product or ''} — "
                f"vigencia_por_data: {vigencia.situacao} "
                f"({selected.get('valid_from') or '-'} a {selected.get('valid_to') or '-'})"
            )
            # ⚠️ O status do fornecedor nao SOME — ele deixa de se chamar
            # "situacao" e passa a vir rotulado pelo que ele e, com a trava
            # escrita ao lado (CLAUDE.md §12.1: nome que mente sobre o conteudo
            # se conserta no NOME, nao no texto em volta).
            administrativo = str(selected.get("policy_status") or "").strip()
            if administrativo:
                lines.append(
                    f"situacao_administrativa_no_sistema_de_gestao: {administrativo} "
                    "(estado de cadastro/entrega do documento na corretora; NAO decide vigencia "
                    "e NAO se repassa ao cliente)"
                )
            familia = _linha_da_familia_de_acionamento(selected.get("insurer_key"))
            if familia:
                lines.append(familia)
        # 🔴 §6.1: a escolha DIZ POR QUÊ. O motivo é texto humano, escrito pela
        # porta, e ele vai para o modelo junto com a apólice — é o que permite
        # ao corretor contestar a escolha em vez de descobri-la por acaso.
        motivo = str(data.get("auto_selected_reason") or "").strip()
        if motivo:
            lines.append(f"apolice_escolhida_porque: {motivo}")
        oculto = int(data.get("historico_oculto") or 0)
        if oculto:
            lines.append(
                f"historico_oculto: {oculto} (apolices antigas do cliente que NAO entraram nesta resposta; "
                "diga que existem se o corretor perguntar, e nunca as apresente como opcao)"
            )
        # COBERTURAS ITEM A ITEM — o que o corretor pede e o que a fonte entrega
        # em `/itens.garantias`: nome, limite (LMI), franquia e premio de CADA
        # cobertura. Vem antes dos fatos porque e a resposta da pergunta.
        # 🔴 §7.1: as coberturas vem da `Apolice` RECONCILIADA da PORTA — cadastro
        # do sistema de gestao + documento oficial, com a ORIGEM escrita por linha
        # e a divergencia dita quando as duas fontes discordam. Antes de
        # 14/09/2026 o briefing lia `coverage_sections` cru, e por isso a resposta
        # da HDI saia com 6 coberturas quando o documento mostra 10.
        #
        # ⚠️ Enquanto o BLOCO D nao ensina o extrator a ler as duas tabelas reais,
        # `apolice_documental_do_pack` devolve `None` em producao e a apolice cai
        # para as coberturas do cadastro — as MESMAS de antes, agora com origem.
        # Nenhuma linha some por causa disso, e o elo fecha no BLOCO D.
        apolice = None
        if pack:
            try:
                from app.providers.infocap_policy_provider import apolice_reconciliada_do_pack

                apolice = apolice_reconciliada_do_pack(pack)
            except Exception as e:  # noqa: BLE001 — a porta nunca derruba a tool
                logger.warning("[InfocapPolicyLookupTool] reconciliacao indisponivel: %s",
                               type(e).__name__)
        coberturas = tuple(getattr(apolice, "coberturas", ()) or ())
        sections = [s for s in (pack.get("coverage_sections") or []) if isinstance(s, dict)]
        # 🔴 Os sinais que JA tem linha propria neste briefing. A secao
        # `avisos_da_apolice` (abaixo) rende todos os OUTROS: repetir o mesmo
        # aviso duas vezes ensina o corretor a nao ler nenhum.
        ja_ditos: set = set()
        if coberturas:
            lines.append(
                f"coberturas_item_a_item ({len(coberturas)} contratadas, reconciliadas entre o "
                "cadastro do sistema de gestao da corretora e o documento oficial da apolice; "
                "LISTE TODAS na resposta, com limite, franquia e premio de cada):"
            )
            lines.extend(_linhas_das_coberturas(apolice))
            aviso = _linha_do_cadastro_incompleto(apolice)
            if aviso:
                lines.append(aviso)
                ja_ditos.add("cadastro_incompleto")
        elif sections:
            # Caminho de seguranca: a reconciliacao falhou, mas a cobertura existe.
            # Ela NUNCA some da resposta — some a origem, e o modelo e avisado.
            lines.append(
                f"coberturas_item_a_item ({len(sections)} contratadas — fonte: "
                f"{pack.get('coverage_source') or 'sistema de gestao da corretora'}; "
                "LISTE TODAS na resposta, com limite, franquia e premio de cada):"
            )
            for section in sections[:60]:
                bits = [f"limite {section.get('amount')}" if section.get("amount") else None,
                        f"franquia {section.get('deductible')}" if section.get("deductible") else None,
                        f"premio {section.get('premium')}" if section.get("premium") else None]
                suffix = " — " + " · ".join(b for b in bits if b) if any(bits) else ""
                lines.append(f"- {section.get('label')}{suffix}")
        if apolice is not None:
            from app.providers.policy_data_provider import Indisponivel, frase_do_sinal

            forma = apolice.forma_de_pagamento
            if not isinstance(forma, Indisponivel) and str(forma).strip():
                linha_forma = f"forma_de_pagamento: {forma} (lida das PARCELAS)"
                cabecalho = apolice.sinal("cabecalho_divergente")
                if cabecalho is not None:
                    linha_forma += (
                        " — o cabecalho do cadastro diz %s; a das parcelas e a que vale"
                        % (cabecalho.detalhe or {}).get("no_cabecalho", "outra coisa")
                    )
                    ja_ditos.add("cabecalho_divergente")
                lines.append(linha_forma)
            plano = apolice.plano_de_assistencia
            if plano is not None and plano.nome.tem_valor:
                lines.append(
                    "plano_de_assistencia: %s — origem: %s%s"
                    % (plano.nome.valor, _ORIGEM_EM_PORTUGUES.get(plano.nome.origem, plano.nome.origem),
                       " (a fonte deu o NOME do plano, nao a lista de servicos: nao prometa servico "
                       "que nao esteja escrito acima)" if plano.estado == "nao_sabemos_ainda" else "")
                )
            # 🔴 TODOS os sinais da apolice, em prosa. 📊 Medido em 14/09/2026:
            # 3 dos 5 sinais que a porta escreve (`rotulo_ambiguo`,
            # `franquia_em_prosa_sem_dono`, `situacao_de_renovacao`) NAO tinham
            # leitor nenhum — eram gravados no modelo e morriam ali. A pendencia
            # `P-E0011-FRANQUIA-EM-PROSA-SEM-DONO` afirmava que o corretor via o
            # sinal das 3 franquias sem dono da HDI; ele nunca viu.
            #
            # ⚠️ A traducao mora na PORTA (`frase_do_sinal`), nao aqui: o
            # proximo adaptador precisa produzir a MESMA frase. Sinal sem
            # traducao NAO some — cai na frase generica com o proprio codigo.
            avisos = [
                frase_do_sinal(sinal)
                for sinal in (getattr(apolice, "sinais", ()) or ())
                if sinal.codigo not in ja_ditos
            ]
            if avisos:
                lines.append(
                    "avisos_da_apolice (o que o sistema de gestao e o documento nao fecham "
                    "entre si; diga ao corretor o que for relevante para a pergunta dele, "
                    "com estas palavras — nunca invente causa nem minimize):"
                )
                lines.extend("- %s" % aviso for aviso in avisos)
        premium_summary = pack.get("premium_summary") or {}
        if premium_summary:
            money = [
                f"{v.get('label')}: {v.get('value')}"
                for v in premium_summary.values()
                if isinstance(v, dict) and v.get("value")
            ]
            if money:
                lines.append("premio_da_apolice: " + " · ".join(money))
            if premium_summary.get("installments_count"):
                lines.append(
                    f"parcelamento: {premium_summary.get('installments_count')}x"
                    + (f" — {premium_summary.get('payment_method')}" if premium_summary.get("payment_method") else "")
                )
        for risk in (pack.get("risk_objects") or [])[:5]:
            if isinstance(risk, dict) and risk:
                lines.append(
                    "objeto_do_risco: "
                    + " · ".join(f"{k}: {v}" for k, v in risk.items() if v not in (None, ""))
                )
        if facts:
            lines.append("fatos_confirmados (unica fonte permitida de fatos):")
            for fact in facts[:60]:
                detail_info = fact.get("source_detail") or {}
                extra = []
                if detail_info.get("participation"):
                    extra.append(f"franquia/participacao: {detail_info.get('participation')}")
                if detail_info.get("premium"):
                    extra.append(f"premio: {detail_info.get('premium')}")
                if detail_info.get("page"):
                    extra.append(f"fonte: documento oficial, pagina {detail_info.get('page')}")
                suffix = f" ({'; '.join(extra)})" if extra else ""
                value = f" = {fact.get('value')}" if fact.get("value") not in (None, "") else ""
                lines.append(f"- [{fact.get('fact_type')}] {fact.get('label')}{value}{suffix}")
        if policy_result:
            if policy_result.get("applied"):
                lines.append(
                    f"politica_assistencia ({policy_result.get('rule_id')} v{policy_result.get('version')}): APLICADA — "
                    "servicos padrao garantidos: eletricista, chaveiro, hidraulica/encanador"
                )
            else:
                lines.append(f"politica_assistencia: NAO aplicada — motivo: {policy_result.get('reason')}")
        installments = [i for i in (pack.get("installments") or []) if isinstance(i, dict)]
        if installments:
            open_items = [i for i in installments if not str(i.get("paid_at") or "").strip()]
            open_desc = ", ".join(
                f"venc {i.get('due_date') or '?'}" + (f" R$ {i.get('due_amount')}" if i.get("due_amount") else "")
                for i in open_items[:12]
            )
            lines.append(f"parcelas: {len(installments)} registradas; {len(open_items)} em aberto" + (f" ({open_desc})" if open_desc else ""))
        # 🔴 §7.1: LISTAR DEIXA DE SER O PADRAO. O cabecalho `opcoes_de_apolice
        # (liste TODAS…)` saiu em 14/09/2026: ele mandava listar em TODA consulta
        # ambigua, inclusive quando a porta ja sabia qual era a apolice certa.
        # 📊 O acervo de 09-11/09 mediu 7 de 7 perguntas respondidas com "qual
        # delas?" e ZERO respondidas com a unica vigente.
        #
        # A lista so volta quando a porta devolve `ambiguous_policy` — 2+ apolices
        # VIGENTES do MESMO ramo, a unica situacao em que perguntar e legitimo. O
        # texto das opcoes vem da PORTA (`opcoes_em_texto` sobre as opcoes JA
        # filtradas), com a situacao da DATA, nunca o `policy_status` cru.
        matches = data.get("matches") or []
        if status == "ambiguous_policy" and matches:
            lines.append(
                "apolices_vigentes_do_mesmo_ramo (a porta NAO conseguiu escolher: ha mais de uma "
                "vigente do mesmo ramo; peca ao corretor que escolha UMA vez, com os numeros exatos):"
            )
            das_opcoes = str(data.get("opcoes_vigentes_em_texto") or "").strip()
            if das_opcoes:
                lines.extend(das_opcoes.split("\n")[1:])
            else:
                for match in matches[:10]:
                    if not isinstance(match, dict):
                        continue
                    from app.providers.policy_data_provider import numero_humano_de

                    number = numero_humano_de(match)
                    lines.append(
                        f"- {number} — {humanize_insurer(match.get('insurer_key')) or '-'} · "
                        f"{humanize_product(match.get('product')) or '-'} · "
                        f"vigencia {match.get('valid_from') or '-'} a {match.get('valid_to') or '-'}"
                    )
        elif status in ("policy_number_ambiguous", "multiple_matches") and matches:
            # A fonte nao isolou a apolice pelo NUMERO humano informado — aqui a
            # ambiguidade e de identificacao, nao de escolha de apolice vigente.
            from app.providers.policy_data_provider import opcoes_em_texto

            lines.append(
                "apolices_com_o_mesmo_numero (o numero informado apareceu em mais de uma apolice; "
                "peca seguradora, ramo ou vigencia para desempatar):"
            )
            # 🔴 O texto JA CLASSIFICADO pela porta vence o cru. Sem ele, a
            # situacao impressa e o `policy_status` do fornecedor — 📊 "ativo"
            # em apolice vencida ha anos — e o corretor escolhe a errada.
            das_opcoes = str(data.get("opcoes_vigentes_em_texto") or "").strip()
            lines.extend((das_opcoes or opcoes_em_texto(matches)).split("\n")[1:])
        limitations = pack.get("limitations") or []
        if limitations:
            lines.append("limitacoes_da_fonte: " + "; ".join(str(item) for item in limitations[:3]))

        # TEXTO DA APOLICE OFICIAL: quando a InfoCap entrega o PDF, ele vem aqui
        # inteiro (ate o limite de contexto). O que nao esta estruturado —
        # clausula, exclusao, sublimite escrito em prosa — se responde daqui.
        document_text = str(((pack.get("official_policy_document_evidence") or {}).get("document_text")) or "").strip()
        if document_text and not client_facing:
            budget = 24000
            body = document_text[:budget]
            lines.extend([
                "",
                "TEXTO DA APOLICE OFICIAL (documento da seguradora, pagina a pagina — LEIA e responda por aqui "
                "o que nao estiver nos campos estruturados; cite a pagina):",
                body,
                ("[...texto truncado por tamanho — peca para eu reabrir o documento se faltar algo...]"
                 if len(document_text) > budget else ""),
            ])

        vehicle_info = data.get("vehicle_info") or {}
        if vehicle_info.get("placa") or vehicle_info.get("veiculo"):
            linha = (
                f"veiculo_da_apolice: {vehicle_info.get('veiculo') or '-'} — placa {vehicle_info.get('placa') or '-'}"
            )
            if vehicle_info.get("telefone_cliente"):
                linha += f" — telefone do cliente na fonte: {vehicle_info['telefone_cliente']}"
            linha += " (use estes dados; NUNCA peca placa/modelo ao cliente)"
            lines.append(linha)

        if client_facing:
            # ATENDIMENTO AO SEGURADO: isto e uma CONVERSA de WhatsApp, nao um
            # relatorio de apolice. O atendente monta a FICHA e segue o fluxo.
            lines.extend([
                "",
                "COMO USAR (voce e o ATENDENTE falando com o CLIENTE no WhatsApp):",
                "1. NAO despeje este bloco nem faca resumo de apolice: use os dados para SEGUIR o atendimento (frases curtas).",
                "2. Monte sua FICHA do atendimento com: titular, CPF, apolice, seguradora, placa/veiculo. Dai em diante USE a ficha — NAO consulte de novo, NAO pergunte nada que ja esteja aqui ou na conversa.",
                "3. As apolices/seguradoras REAIS deste cliente sao SOMENTE as listadas neste bloco — NUNCA invente seguradora, apolice ou opcao que nao esteja aqui. O NOME do cliente e o do titular acima (ou o que ELE disser) — NUNCA invente nome.",
                "4. Se houver mais de uma apolice vigente: escolha VOCE a coerente com o pedido (servico de CARRO -> apolice AUTO; celular/vida/residencia NUNCA atendem carro) e chame de novo com policy_number. So pergunte ao cliente se houver 2+ apolices do MESMO ramo — e pergunte UMA UNICA VEZ NA CONVERSA INTEIRA: se o cliente JA disse a seguradora (agora ou antes), chame IMEDIATAMENTE com o policy_number da opcao correspondente, SEM re-perguntar. A escolha dele vale ate o fim do atendimento.",
                # 🔴 §5.4: o conhecimento de FAMILIA saiu daqui e virou CATALOGO
                # (`docs/canon/providers/susep/seguradora-coenti.json`, secao
                # `familias_de_acionamento`, lida por `susep_ses_provider`). No
                # prompt ele valia so enquanto o modelo obedecesse; no arquivo
                # revisado ele vale sempre. Quando houver familia declarada, a
                # linha `seguradora_para_acionamento` aparece ACIMA, nos dados.
                "5. Para acionar, use a seguradora indicada em 'seguradora_para_acionamento' quando ela aparecer acima — ela ja considera rebatizacao e grupo economico. Sem essa linha, use a seguradora da apolice como ela veio.",
                "6. Situacao interna da fonte ('recebido e nao entregue', apolices vencidas ocultadas) NAO interessa ao cliente — se a vigencia esta ok, siga direto para resolver o pedido.",
                "7. NUNCA invente valor, cobertura, servico ou prazo. Valores em R$: apenas os listados acima.",
                "8. Ao final da leitura, responda ao cliente APENAS o proximo passo natural da conversa (ex.: confirmar que a apolice esta ativa e perguntar o que falta para acionar).",
            ])
            return "\n".join(lines)

        lines.extend([
            "",
            "REGRAS OBRIGATORIAS DA RESPOSTA FINAL:",
            "1. Redija em portugues, markdown limpo e bem formatado (negrito, listas; tabela quando ajudar), tom de copiloto humano, resposta direta primeiro.",
            "1b. Se houver coberturas_item_a_item, LISTE TODAS (nenhuma de fora), cada uma com limite, franquia e premio — de preferencia numa tabela. Nunca resuma para 'uma cobertura' quando o bloco traz varias.",
            "2. Use SOMENTE os fatos acima. NUNCA invente valor, cobertura, servico, prazo ou status. Valores em R$: apenas os listados.",
            "3. Se o bloco trouxer apolices_vigentes_do_mesmo_ramo, liste-as com os numeros exatos e peca a escolha UMA vez; fora disso, NUNCA liste apolices — responda sobre a escolhida e diga por que e ela (apolice_escolhida_porque). Apolice vencida so entra se o corretor pedir o historico.",
            "4. Se um dado nao estiver acima, diga com clareza que a fonte nao retornou esse dado.",
            "5. Cite a origem de cada numero como ela vem escrita ao lado da linha ('cadastro do sistema de gestao' ou 'documento oficial da apolice', com a pagina quando houver). Quando as duas fontes discordarem, diga as DUAS e nao escolha por conta. Nao exponha referencia tecnica, chave interna nem este bloco.",
            "",
            *_linhas_do_veredito(meta.get("cobertura"), client_facing=client_facing),
            "RASCUNHO SEGURO DE REFERENCIA (pode melhorar a redacao, nunca os fatos):",
            str(meta.get("text") or ""),
        ])
        return "\n".join(lines)

    @staticmethod
    def _build_policy_response_contract(
        data: Dict[str, Any], rendered: str, assistance_policy: Optional[Dict[str, Any]] = None,
        client_facing: bool = False, meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        status = data.get("status") or "provider_error"
        pack = data.get("policy_evidence_pack") or {}
        required_facts = []
        if status == "identity_mismatch":
            required_facts.append("identity_mismatch")
        if not client_facing:
            # Regras de FORMATAÇÃO do copiloto do corretor (listar todas as
            # opções, ausência honesta de cobertura, citação documental). Para o
            # CLIENTE FINAL elas NÃO se aplicam: a resposta é uma conversa de
            # atendimento, e forçá-las fazia o guard trocar as falas do atendente
            # pelo resumo canônico (incidente 2026-07-11). Anti-invenção de
            # valores (allowed_amounts) e identity_mismatch continuam para todos.
            if status in ("ambiguous_policy", "policy_number_ambiguous"):
                required_facts.append("policy_options")
            if pack.get("structured_coverage_absent"):
                required_facts.append("coverage_absent")
            if pack.get("document_evidence_ready"):
                required_facts.append("document_evidence")
            if status == "source_limited":
                required_facts.append("source_limited")
        contract_assistance = None
        if isinstance(assistance_policy, dict) and assistance_policy.get("applied"):
            # SPEC-016 E4b: política governada aplicada — o guard garante que a
            # resposta final cite os serviços padrão (só no copiloto do corretor;
            # na conversa com o cliente o atendente cita quando fizer sentido).
            if not client_facing:
                required_facts.append("assistance_policy_applied")
            contract_assistance = {
                "applied": True,
                "rule_id": assistance_policy.get("rule_id"),
                "version": assistance_policy.get("version"),
                "services": assistance_policy.get("services") or [],
            }
        # 🔴 SPEC-EXTRA-001.5 §6.4: o que a BASE afirmou sobre ESTA apólice.
        # `assistencia_da_base` e `assistance_policy_applied` são EXCLUDENTES —
        # o compositor garante um vencedor só (M-B5) —, e o guarda de
        # `nodes.py` tem uma regra para cada: a base diz QUAIS serviços o texto
        # tem de citar; o fallback continua exigindo os três padrão.
        #
        # ⚠️ Vale nos DOIS canais, inclusive `client_facing`: a regra de
        # FORMATAÇÃO do copiloto não se aplica ao atendimento, mas "não afirmar
        # o que a base nega" não é formatação — é o que chega ao segurado pelo
        # WhatsApp.
        da_base = (meta or {}).get("assistencia_da_base")
        contrato_da_base = None
        if isinstance(da_base, list) and da_base:
            required_facts.append("assistencia_da_base")
            contrato_da_base = da_base
        cobertura = (meta or {}).get("cobertura")

        # SPEC-016.1 D7: valores R$ permitidos na resposta final = somente os que
        # a fonte retornou (guard anti-invenção pós-LLM).
        import json as _json
        import re as _re

        allowed_amounts = sorted(set(_re.findall(r"R\$\s*[\d.][\d.,]*", _json.dumps(data, ensure_ascii=False, default=str))))
        return {
            **({"assistance_policy": contract_assistance} if contract_assistance else {}),
            **({"assistencia_da_base": contrato_da_base} if contrato_da_base else {}),
            **({"cobertura": cobertura} if cobertura else {}),
            "allowed_amounts": allowed_amounts,
            "provider": "infocap",
            "result_kind": status,
            "coverage_evidence_status": pack.get("coverage_evidence_status") or (data.get("coverage_evidence") or {}).get("coverage_evidence_status"),
            # 🔴 SÓ quando a porta devolveu `ambiguous_policy` (2+ VIGENTES do
            # MESMO ramo). Nos demais casos a lista vem VAZIA, e o guarda de
            # `nodes.py` não tem o que exigir: ele continua impedindo o modelo de
            # ESCONDER uma opção legítima, e para de OBRIGAR a listagem quando a
            # apólice já está escolhida (proposta §7.3).
            "policy_options": (
                (data.get("matches") or [])
                if status in ("ambiguous_policy", "policy_number_ambiguous")
                else []
            ),
            "selected_policy": data.get("selected") or data.get("policy") or {},
            "source_limitation": data.get("message") or "; ".join(data.get("blockers") or []),
            "next_allowed_action": (
                "choose_policy"
                if status in ("ambiguous_policy", "policy_number_ambiguous")
                else "fail_closed"
                if status == "identity_mismatch"
                else "use_official_document_evidence_later"
                if pack.get("document_evidence_required") and not pack.get("document_evidence_ready")
                else "answer_from_document_evidence"
                if pack.get("document_evidence_ready")
                else "answer_from_structured_data"
                if status == "found"
                else "retry_or_refine"
            ),
            "rendered_safe_answer": rendered,
            # ⚠️ AUDITORIA, NUNCA ENVIO (SPEC-EXTRA-001.5.1 C2). `rendered` já é
            # o texto DO CANAL — o guarda de `nodes.py` continua ignorante de
            # canal e certo por construção. Este campo guarda o outro lado para
            # que se possa CONFERIR, depois, que os dois disseram a mesma coisa.
            **({"rendered_do_outro_canal": (
                (meta or {}).get("texto_para_o_corretor") if client_facing
                else (meta or {}).get("texto_para_o_segurado"))}
               if (meta or {}).get("cobertura") else {}),
            "required_facts": required_facts,
        }

    @staticmethod
    def _document_evidence_lines(pack: Dict[str, Any]) -> list[str]:
        evidence = (pack.get("official_policy_document_evidence") or {}) if isinstance(pack, dict) else {}
        items = evidence.get("evidence_items") or []
        if not items:
            return []
        lines = [
            "- Evidencia documental da apolice oficial processada:",
        ]
        for item in items[:10]:
            page = item.get("page_number") or "-"
            etype = item.get("evidence_type") or "other"
            text = str(item.get("evidence_text") or "").strip()
            if text:
                lines.append(f"   - Pagina {page} [{etype}]: {text}")
        return lines

    @staticmethod
    def _summarize_detail(d: Dict[str, Any], unmasked: bool = False) -> str:
        if not d.get("ok"):
            st = d.get("status")
            if st in ("blocked_not_configured", "blocked_missing_credentials"):
                return "O sistema de gestao da sua corretora nao esta totalmente configurado."
            if st == "ambiguous_connection":
                return "Ha mais de uma conexao elegivel com o sistema de gestao da corretora. E necessario limpar as conexoes duplicadas antes da consulta."
            if st == "source_limited":
                return "O sistema de gestao da corretora localizou o pedido, mas ainda faltou resolver a apolice em uma opcao unica do catalogo. Informe CPF/nome do segurado ou o numero humano da apolice para eu resolver o detalhe com seguranca."
            if st == "identity_mismatch":
                return "A identidade da apolice nao foi confirmada. Por seguranca, nao vou exibir detalhes nem consultar documento desta apolice."
            if st == "policy_number_not_found":
                return "Nao localizei apolice com esse numero humano no sistema de gestao da corretora."
            if st == "policy_number_ambiguous":
                return "Esse numero humano apareceu em mais de uma apolice. Preciso de seguradora, ramo, vigencia ou cliente para escolher com seguranca."
            return "Nao consegui obter os detalhes dessa apolice no sistema de gestao da corretora agora."
        pack = d.get("policy_evidence_pack") or {}
        secs = pack.get("coverage_sections") or []
        # 🔴 O número humano vem da PORTA. Até 14/09/2026 esta linha importava
        # `_display_policy_number` de `app/api/infocap_connector` — um dos 3
        # imports que quebravam a fronteira (G1a).
        from app.providers.policy_data_provider import numero_humano_de

        num = numero_humano_de(pack)
        titular = pack.get("holder_name") or pack.get("holder_name_masked") or "-"
        lines = [
            "Detalhes da apolice (sistema de gestao da corretora):",
            f"- Seguradora: {pack.get('insurer_detected') or '-'} - Produto: {pack.get('product_detected') or '-'}",
            f"- Numero da apolice: {num} - Titular: {titular}" + (f" - CPF/CNPJ: {_doc}" if (_doc := InfocapPolicyLookupTool._doc_para_o_publico(pack.get("document"), unmasked)) else ""),
            f"- Situacao: {pack.get('policy_status') or '-'} - Vigencia: {pack.get('valid_from') or '-'} a {pack.get('valid_to') or '-'}",
        ]
        if pack.get("installments"):
            lines.append(f"- Parcelas retornadas: {len(pack.get('installments') or [])}")
        if secs:
            lines.append(f"- Coberturas contratadas ({len(secs)}), item a item:")
            for section in secs[:60]:
                bits = [f"limite {section.get('amount')}" if section.get("amount") else None,
                        f"franquia {section.get('deductible')}" if section.get("deductible") else None,
                        f"premio {section.get('premium')}" if section.get("premium") else None]
                suffix = " - " + " · ".join(b for b in bits if b) if any(bits) else ""
                lines.append(f"   - {section.get('label')}{suffix}")
        elif pack.get("document_evidence_ready"):
            lines.extend(InfocapPolicyLookupTool._document_evidence_lines(pack))
        else:
            lines.append("- O sistema de gestao da corretora confirmou a apolice e os dados operacionais, mas nao retornou itens estruturados de cobertura nesta consulta.")
            if pack.get("official_document_source_available"):
                lines.append("- Ha fonte documental oficial disponivel, mas ela ainda nao foi processada nesta consulta.")
        if pack.get("limitations"):
            lines.append("- Observacoes: " + "; ".join(pack.get("limitations")[:3]))
        return "\n".join(lines)

    @staticmethod
    def _summarize(r: Dict[str, Any], unmasked: bool = False) -> str:
        status = r.get("status")
        cli = ""
        if r.get("client_document") or r.get("client_name"):
            _docc = InfocapPolicyLookupTool._doc_para_o_publico(r.get("client_document"), unmasked)
            cli = f"\n- Cliente: {r.get('client_name') or '-'} - CPF/CNPJ: {_docc or '-'}"
        if r.get("ok") and status == "found":
            sel = r.get("selected") or {}
            pack = r.get("policy_evidence_pack") or {}
            from app.providers.policy_data_provider import numero_humano_de

            num = numero_humano_de(sel)
            titular = sel.get("holder_name") or sel.get("holder_name_masked") or "-"
            doc = sel.get("document") or r.get("client_document")
            active_now = sel.get("active_now")
            active_text = (
                "ativa"
                if active_now is True
                else "nao ativa"
                if active_now is False
                else "situacao de vigencia nao confirmada"
            )
            lines = [
                "Apolice localizada no sistema de gestao da corretora:",
                f"- Seguradora: {sel.get('insurer_key') or '-'} - Produto: {sel.get('product') or '-'}",
                f"- Numero da apolice: {num} - Titular: {titular}" + (f" - CPF/CNPJ: {_docp}" if (_docp := InfocapPolicyLookupTool._doc_para_o_publico(doc, unmasked)) else ""),
                f"- Situacao: {sel.get('policy_status') or '-'} ({active_text}) - Vigencia: {sel.get('valid_from') or '-'} a {sel.get('valid_to') or '-'}",
            ]
            if pack.get("structured_coverage_absent"):
                if pack.get("document_evidence_ready"):
                    lines.extend(InfocapPolicyLookupTool._document_evidence_lines(pack))
                else:
                    lines.append("- O sistema de gestao da corretora confirmou a apolice e seus dados operacionais, mas nao retornou itens estruturados de cobertura, franquia ou assistencia nesta consulta. Nao vou concluir cobertura sem essa evidencia.")
                    if pack.get("official_document_source_available"):
                        lines.append("- Existe uma fonte documental oficial disponivel; ela ainda nao foi processada nesta consulta.")
            return "\n".join(lines) + cli
        if status == "sem_vigente":
            return str(r.get("frase_sem_vigente") or "").strip() or (
                "Este cliente tem apolices no sistema de gestao, mas nenhuma vigente hoje. "
                "Quer que eu liste o historico?"
            )
        if status in ("multiple_matches", "ambiguous_customer", "ambiguous_policy", "policy_number_ambiguous"):
            from app.providers.policy_data_provider import opcoes_em_texto

            # 🔴 O texto JA CLASSIFICADO pela porta vence o cru — tambem aqui. Este
            # e o caminho de FALLBACK (flag v2 desligada), e ele chega ao corretor
            # do mesmo jeito. 📊 Sem isto a coluna `Status` imprimia o
            # `policy_status` do fornecedor: "ativo" numa apolice vencida ha anos,
            # e "Recebido e nao entregue ao cliente" numa vigente.
            options = (str(r.get("opcoes_vigentes_em_texto") or "").strip()
                       or opcoes_em_texto(r.get("matches") or []))
            base = "Encontrei mais de uma apolice/cliente para esse termo. Escolha pelo numero humano da apolice antes de detalhar."
            return (base + ("\n" + options if options else "") + cli).strip()
        if status == "identity_mismatch":
            return "A identidade da apolice nao foi confirmada. Por seguranca, nao vou exibir detalhes, cobertura, parcelas ou documento dessa consulta."
        if status == "policy_number_not_found":
            return "Nao localizei apolice com esse numero humano no sistema de gestao da corretora."
        if status in ("not_found", "client_found"):
            return ("Cliente localizado, mas sem apolice/documento vinculado retornado." + cli) if status == "client_found" else "Nao localizei cliente/apolice para esse termo no sistema de gestao da corretora."
        if status == "source_limited":
            return "O sistema de gestao da corretora respondeu, mas nao retornou dados suficientes para selecionar uma apolice unica. Refine com CPF, nome completo ou numero humano da apolice."
        if status in ("blocked_not_configured", "blocked_missing_credentials"):
            return "O sistema de gestao da corretora nao esta totalmente configurado: credencial/base ausente."
        if status == "ambiguous_connection":
            return "Ha mais de uma conexao elegivel com o sistema de gestao da corretora. E necessario limpar as conexoes duplicadas antes da consulta."
        return "Nao foi possivel concluir a consulta ao sistema de gestao da corretora agora."
