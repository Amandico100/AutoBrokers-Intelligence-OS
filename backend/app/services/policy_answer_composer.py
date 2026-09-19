"""Compositor humano de resposta de apólice (SPEC-016 E4).

Módulo PURO. Transforma o resultado canônico da leitura de apólice em uma
resposta de copiloto: direta, com fonte, sem jargão técnico e sem inventar.

Regras:
- resposta direta primeiro (a pergunta do corretor manda);
- fonte citada: item estruturado da InfoCap ou documento oficial com página;
- ausência honesta quando a fonte não confirmar;
- opções numeradas em ambiguidade (número humano, seguradora, produto, vigência);
- NUNCA expor termos internos: nosnum, locator, codfil, evidence pack, DTO;
- fail-closed preservado em identity_mismatch (nenhum dado da apólice).

O texto produzido vira o `rendered_safe_answer` do Policy Response Contract —
o output guard existente continua sendo o mecanismo de imposição.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from app.services.assistance_policy import apply_residential_assistance_policy, policy_rule_facts
# ⚠️ `fonte_canonica` e a metade LEITORA da renomeacao expand-first da
# SPEC-EXTRA-001.1 §5.3: o compositor aceita o valor NOVO
# (`sistema_de_gestao`/`documento_oficial`) E o antigo
# (`infocap_structured`/`official_document`), que ainda chega de quem nao
# migrou. 🔴 Sem isto, a renomeacao apagaria a lista de coberturas da
# resposta em silencio — que e o defeito que ela existe para consertar.
from app.services.policy_facts import (
    extract_policy_facts,
    fonte_canonica,
    has_confirmed_assistance,
)

_INVALID_NUMBERS = {"", "0", "none", "null", "-"}

# 🔴 SPEC-EXTRA-001.5 §0.3 — O ELO, medido em 17/09/2026 sobre este arquivo:
#
#   "ele tem carro reserva?"             -> NÃO casa este regex. A pergunta nem
#                                           entra no ramo de assistência, e a
#                                           resposta é o resumo da apólice.
#   "a assistência cobre carro reserva?" -> casa, e responde
#                                           "Sim — ... eletricista, chaveiro,
#                                           hidráulica/encanador."
#
# O segundo é o defeito de PRODUTO: um "sim" a um serviço que a regra não
# conhece. 📊 94 mensagens do acervo perguntam por carro reserva.
#
# ⚠️ O regex FICA — ele é a porta de "tem assistência 24h?", que não nomeia
# serviço nenhum e continua caindo no caminho antigo. O que muda é que ele
# deixou de ser a ÚNICA porta: `servico_canonico` (o vocabulário versionado)
# abre a dela, e quem responde daí é a Skill.
_ASSIST_INTENT_RE = re.compile(
    r"assist[êe]ncia|eletricista|chaveiro|encanador|hidr[áa]ulic|24\s*h", re.IGNORECASE
)
_COVERAGE_INTENT_RE = re.compile(r"cobertura|coberturas|garantia|garantias|\bcobre\b|coberto|coberta", re.IGNORECASE)
_DEDUCTIBLE_INTENT_RE = re.compile(r"franquia", re.IGNORECASE)
_INSTALLMENT_INTENT_RE = re.compile(r"parcela", re.IGNORECASE)


def _norm(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


# SPEC-016.1 D7 — abreviações comuns dos providers de gestão → nome humano.
# Melhor esforço de exibição: quando não conhecido, mantém o valor da fonte.
_INSURER_LABELS = {
    "alli": "Allianz", "allianz": "Allianz",
    "port": "Porto Seguro", "porto": "Porto Seguro",
    "brad": "Bradesco", "bradesco": "Bradesco",
    "zuri": "Zurich", "zurich": "Zurich",
    "toki": "Tokio Marine", "tokm": "Tokio Marine",
    "sula": "SulAmérica", "mapf": "Mapfre", "hdi": "HDI",
    "itau": "Itaú", "azul": "Azul Seguros", "sanc": "Sancor",
    "sompo": "Sompo", "libe": "Yelum (ex-Liberty)", "liberty": "Yelum (ex-Liberty)",
    "yelum": "Yelum",
}
_PRODUCT_LABELS = {
    "resi": "Residencial", "residencial": "Residencial",
    "auto": "Auto", "automovel": "Auto",
    "vida": "Vida", "vind": "Vida Individual",
    "cons": "Consórcio", "cond": "Condomínio",
    "empr": "Empresarial", "viag": "Viagem", "saud": "Saúde",
}


def humanize_insurer(value: Any) -> str:
    raw = str(value or "").strip()
    return _INSURER_LABELS.get(_norm(raw), raw)


def humanize_product(value: Any) -> str:
    raw = str(value or "").strip()
    return _PRODUCT_LABELS.get(_norm(raw), raw)


def _display_number(record: Dict[str, Any]) -> str:
    number = str(record.get("policy_number") or record.get("numapo") or "").strip()
    if _norm(number) in _INVALID_NUMBERS:
        # Nunca vazar placeholder técnico para o cliente: sem número na fonte,
        # a escolha é pela POSIÇÃO da lista (1, 2, 3...).
        return "sem número na fonte — responda pela posição da lista"
    return number


def _policy_header(selected: Dict[str, Any]) -> str:
    insurer = humanize_insurer(selected.get("insurer_key") or selected.get("insurer_detected"))
    product = humanize_product(selected.get("product") or selected.get("product_detected"))
    parts = [p for p in (product, insurer and f"({insurer})") if p]
    return " ".join(parts) if parts else "a apólice consultada"


def _client_line(result: Dict[str, Any]) -> Optional[str]:
    name = str(result.get("client_name") or "").strip()
    doc = str(result.get("client_document") or "").strip()
    if not name and not doc:
        return None
    pieces = [p for p in (name, doc and f"CPF/CNPJ {doc}") if p]
    return "Cliente: " + " — ".join(pieces) + "."


def _structured_assistance_labels(facts: List[Dict[str, Any]]) -> List[str]:
    return [
        str(f.get("label") or "").strip()
        for f in facts
        if f.get("fact_type") == "assistance" and fonte_canonica(f.get("source")) == "sistema_de_gestao" and f.get("label")
    ]


def _document_assistance_citations(facts: List[Dict[str, Any]]) -> List[str]:
    citations = []
    for f in facts:
        if f.get("fact_type") != "assistance" or fonte_canonica(f.get("source")) != "documento_oficial":
            continue
        detail = f.get("source_detail") or {}
        page = detail.get("page")
        snippet = str(detail.get("snippet") or "").strip()
        if page and snippet:
            citations.append(f'documento oficial da apólice, página {page}: "{snippet}"')
    return citations


def _service_labels(services: List[str]) -> str:
    labels = {"eletricista": "eletricista", "chaveiro": "chaveiro", "hidraulica_encanador": "hidráulica/encanador"}
    return ", ".join(labels.get(s, s) for s in services)


def _compose_assistance_answer(
    result: Dict[str, Any],
    pack: Dict[str, Any],
    facts: List[Dict[str, Any]],
    policy_result: Dict[str, Any],
) -> str:
    lines: List[str] = []
    if policy_result.get("applied"):
        sources: List[str] = []
        structured = _structured_assistance_labels(facts)
        if structured:
            sources.append(f'item estruturado da fonte: "{structured[0]}"')
        sources.extend(_document_assistance_citations(facts)[:1])
        source_text = "; ".join(sources) if sources else "fonte da apólice"
        lines.append(
            f"Sim — esta apólice residencial tem assistência confirmada ({source_text})."
        )
        lines.append(
            f"Pela política padrão de Assistência 24h residencial, os serviços incluídos são: {_service_labels(policy_result.get('services') or [])}."
        )
    elif has_confirmed_assistance(facts):
        structured = _structured_assistance_labels(facts)
        doc_citations = _document_assistance_citations(facts)
        source_text = structured[0] if structured else (doc_citations[0] if doc_citations else "fonte da apólice")
        lines.append(f'Sim — a apólice registra assistência confirmada ({source_text}).')
        lines.append(
            "Como não é uma apólice residencial, os serviços exatos dependem do plano contratado — posso detalhar pelo documento oficial se precisar."
        )
    else:
        lines.append(
            "Não encontrei confirmação de assistência nesta apólice: a fonte não retornou itens estruturados de assistência nesta consulta."
        )
        if pack.get("official_document_source_available") and not pack.get("document_evidence_ready"):
            lines.append(
                "Existe o documento oficial da apólice disponível — se quiser, eu busco e verifico a assistência direto nele."
            )
        else:
            lines.append(
                "Para confirmar com segurança, posso verificar o documento oficial da apólice assim que ele estiver disponível."
            )
    return "\n".join(lines)


def _compose_coverage_answer(pack: Dict[str, Any], facts: List[Dict[str, Any]]) -> str:
    coverage_facts = [f for f in facts if f.get("fact_type") == "coverage"]
    structured = [f for f in coverage_facts if fonte_canonica(f.get("source")) == "sistema_de_gestao"]
    lines: List[str] = []
    if structured:
        lines.append("As coberturas registradas na apólice são:")
        lines.append("")
        for f in structured[:40]:
            amount = f.get("value")
            detail = f.get("source_detail") or {}
            entry = f"- **{f.get('label')}**" + (f" — limite {amount}" if amount else "")
            extras = []
            if detail.get("participation"):
                extras.append(f"franquia {detail['participation']}")
            if detail.get("premium"):
                extras.append(f"prêmio {detail['premium']}")
            if extras:
                entry += " (" + " · ".join(extras) + ")"
            lines.append(entry)
    else:
        doc_facts = [f for f in coverage_facts if fonte_canonica(f.get("source")) == "documento_oficial"]
        if doc_facts:
            lines.append("Coberturas registradas no documento oficial da apólice:")
            lines.append("")
            for f in doc_facts[:20]:
                detail = f.get("source_detail") or {}
                amount = f.get("value")
                participation = detail.get("participation")
                entry = f"- **{f.get('label')}**" + (f" — {amount}" if amount else "")
                if participation:
                    entry += f" (participação: {participation})"
                lines.append(entry)
        else:
            lines.append(
                "A fonte confirmou a apólice, mas não retornou itens estruturados de cobertura nesta consulta — não vou listar cobertura sem essa evidência."
            )
            if pack.get("official_document_source_available"):
                lines.append("Posso verificar o documento oficial da apólice para trazer as coberturas com página e trecho.")
    return "\n".join(lines)


def _compose_operational_summary(result: Dict[str, Any], pack: Dict[str, Any]) -> str:
    selected = result.get("selected") or result.get("policy") or {}
    header = _policy_header({**selected, **pack})
    number = _display_number({**pack, **selected})
    # Situação pelo que IMPORTA: vigência real por data. Status administrativo
    # cru da fonte ("Recebido e não entregue ao cliente") é ruído interno que
    # confunde — só entra quando agrega (cancelada).
    vigencia_real = _real_vigencia({**pack, **selected})
    valid_from = selected.get("valid_from") or pack.get("valid_from") or "-"
    valid_to = selected.get("valid_to") or pack.get("valid_to") or "-"
    holder = str(selected.get("holder_name") or "").strip()
    lines = [
        f"Encontrei a apólice **{number}** — {header}.",
        "",
        f"- **Situação:** {vigencia_real}",
        f"- **Vigência:** {valid_from} a {valid_to}",
    ]
    if holder:
        lines.append(f"- **Titular:** {holder}")
    return "\n".join(lines)


def _is_installment_open(item: Dict[str, Any]) -> bool:
    paid = item.get("paid_at")
    return paid is None or not str(paid).strip()


def _format_amount(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.upper().startswith("R$") else f"R$ {text}"


def _compose_installments_answer(pack: Dict[str, Any], question_text: str) -> str:
    installments = [i for i in (pack.get("installments") or []) if isinstance(i, dict)]
    if not installments:
        return "A fonte não retornou parcelas estruturadas para esta apólice nesta consulta."
    open_items = [i for i in installments if _is_installment_open(i)]
    paid_count = len(installments) - len(open_items)
    lines = [
        f"A apólice tem **{len(installments)}** parcela(s) registradas: **{len(open_items)} em aberto** e {paid_count} paga(s)."
    ]
    if open_items:
        lines.append("")
        lines.append("**Parcelas em aberto:**")
        for item in open_items[:15]:
            due = str(item.get("due_date") or "data não informada").strip()
            amount = _format_amount(item.get("due_amount"))
            number = item.get("installment_number")
            prefix = f"Parcela {number} — " if number not in (None, "") else ""
            lines.append(f"- {prefix}vencimento {due}" + (f" — {amount}" if amount else ""))
    else:
        lines.append("")
        lines.append("Todas as parcelas registradas constam como pagas.")
    return "\n".join(lines)


def _parse_br_date(value: Any):
    from datetime import datetime

    text = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except Exception:  # noqa: BLE001
            continue
    return None


#: A tradução entre a porta e o vocabulário desta função. 🔴 `DESCONHECIDA`
#: (sem datas na fonte) continua caindo em "vigente" porque é o que esta função
#: sempre fez: aqui "vigente" significa *"não está PROVADO que venceu"*, e virar
#: "vencida" por falta de data esconderia a apólice do corretor.
_SITUACAO_PARA_VIGENCIA = {
    "CANCELADA": "cancelada", "VENCIDA": "vencida", "FUTURA": "futura",
    "VIGENTE": "vigente", "DESCONHECIDA": "vigente",
}


def _real_vigencia(match: Dict[str, Any], hoje=None) -> str:
    """Vigência REAL calculada pelas datas — a fonte marca 'ativo' até em
    apólice vencida há anos (bug visto no teste do founder 2026-07-10).

    🔴 SPEC-EXTRA-001.1 BLOCO B: a REGRA sempre esteve certa; o LUGAR é que
    estava errado — ela rodava aqui, depois de o conector já ter respondido
    `ambiguous_policy`, e só para quem chegava ao compositor. Agora ela mora na
    porta (`classificar_vigencia`), e esta função **delega**. Duas cópias da
    mesma regra divergiriam, e é o defeito nº 1 deste projeto (CLAUDE.md §5).
    """
    from app.providers.policy_data_provider import classificar_vigencia

    status = str(match.get("policy_status") or "").strip().lower()
    cancelado = "cancel" in status or bool(match.get("cancelled"))
    vigencia = classificar_vigencia(
        match.get("valid_from"), match.get("valid_to"), cancelado, hoje=hoje
    )
    return _SITUACAO_PARA_VIGENCIA.get(vigencia.situacao, "vigente")


def _compose_options(matches: List[Dict[str, Any]], hoje=None, historico_oculto=None) -> str:
    # Vigência real primeiro; vencidas/canceladas NUNCA aparecem como opção
    # quando existe apólice vigente (só confundem o cliente).
    #
    # ⚠️ Desde o BLOCO B as `matches` que chegam aqui já vêm FILTRADAS pela porta
    # (só vigentes, só do ramo). A conta local daria `hidden = 0` e a frase "há N
    # no histórico" sumiria — por isso `historico_oculto`, quando a porta o
    # informa, VENCE a conta local: ele conhece as apólices que a resposta nem
    # chegou a trazer (truncamento da fonte incluído).
    enriched = [(m, _real_vigencia(m, hoje)) for m in matches]
    vigentes = [(m, v) for m, v in enriched if v in ("vigente", "futura")]
    shown = vigentes if vigentes else enriched
    hidden = len(enriched) - len(shown)
    if historico_oculto is not None:
        try:
            hidden = max(hidden, int(historico_oculto))
        except (TypeError, ValueError):
            pass

    if len(shown) == 1:
        m, vig = shown[0]
        number = _display_number(m)
        insurer = humanize_insurer(m.get("insurer_key")) or "-"
        product = humanize_product(m.get("product")) or "-"
        suffix = f" (há {hidden} apólice(s) antiga(s)/vencida(s) no histórico)" if hidden else ""
        return (
            f"Localizei a apólice vigente do cliente: **{number}** — {insurer} · {product} · "
            f"vigência {m.get('valid_from') or '-'} a {m.get('valid_to') or '-'} ({vig}).{suffix}"
        )

    lines = [
        "Encontrei mais de uma apólice. Qual delas você quer? Responda com o número da apólice:",
        "",
    ]
    for idx, (match, vig) in enumerate(shown[:10], start=1):
        number = _display_number(match)
        insurer = humanize_insurer(match.get("insurer_key")) or "-"
        product = humanize_product(match.get("product")) or "-"
        valid_from = match.get("valid_from") or "-"
        valid_to = match.get("valid_to") or "-"
        lines.append(f"{idx}. **{number}** — {insurer} · {product} · vigência {valid_from} a {valid_to} ({vig})")
    # Vencidas/canceladas ficam fora da lista em silêncio — anunciar "ocultei X
    # apólices" é ruído interno que não ajuda ninguém (feedback founder 11/07).
    return "\n".join(lines)


def _apolice_para_a_skill(result: Dict[str, Any], pack: Dict[str, Any],
                          facts: List[Dict[str, Any]], db: Any = None) -> Dict[str, Any]:
    """O que a Skill precisa saber da apólice — nada além, e nada inventado.

    🔴 O `plano` vem de `PlanoDeAssistencia` da PORTA (001.1,
    `policy_data_provider.py:491-507`), com o `EstadoDoPlano` que ela já
    calculou. A Skill NÃO deduz plano; sem plano identificado ela responde
    `nao_sabemos_ainda` (M-B4), e é por isso que o `estado_do_plano` viaja
    junto: sem ele, "nome do plano presente" seria lido como "plano
    contratado", que é exatamente o que a porta se recusa a afirmar.

    ⚠️ A reconciliação pode não estar disponível (📊 hoje
    `apolice_documental_do_pack` devolve `None` em produção). Isso deixa o plano
    desconhecido — que é `nao_sabemos_ainda`, não falha.
    """
    selected = result.get("selected") or result.get("policy") or {}
    plano, nivel, estado = None, None, "nao_sabemos_ainda"
    try:
        from app.providers.infocap_policy_provider import apolice_reconciliada_do_pack

        apolice = apolice_reconciliada_do_pack(pack)
        do_plano = getattr(apolice, "plano_de_assistencia", None)
        if do_plano is not None:
            estado = str(getattr(do_plano, "estado", "nao_sabemos_ainda"))
            nome = getattr(do_plano, "nome", None)
            if nome is not None and getattr(nome, "tem_valor", False):
                plano = str(nome.valor)
            campo_nivel = getattr(do_plano, "nivel", None)
            if campo_nivel is not None and getattr(campo_nivel, "tem_valor", False):
                try:
                    nivel = int(campo_nivel.valor)
                except (TypeError, ValueError):
                    nivel = None
    except Exception as exc:  # noqa: BLE001 — a porta nunca derruba o compositor
        logger.info("[composer] plano de assistência indisponível: %s", type(exc).__name__)

    # 🔴 A VAGA QUE O BLOCO C PREENCHE — e por que ela existe já.
    #
    # 📊 17/09/2026: `_plano_do_pack` (`infocap_policy_provider.py:273-287`)
    # devolve SEMPRE `estado="nao_sabemos_ainda"`, porque `tabela_itens` dá o
    # NOME do plano e nada mais. Ou seja: hoje, em produção, toda pergunta de
    # cobertura cai em `nao_sabemos_ainda` — e isso está CERTO, é o que a base
    # vazia autoriza dizer.
    #
    # `pack["assistance_plan"]` é onde a identificação do plano entra quando
    # ela existir (BLOCO C: SUSEP da apólice → condição geral → plano). ⚠️ Hoje
    # NINGUÉM escreve esta chave em produção; ela é lida aqui para que o dia em
    # que alguém escrever não exija mexer no caminho vivo de novo.
    do_pack = pack.get("assistance_plan")
    if isinstance(do_pack, dict):
        plano = str(do_pack.get("plano") or "").strip() or plano
        estado = str(do_pack.get("estado") or estado)
        try:
            nivel = int(do_pack["nivel"]) if do_pack.get("nivel") is not None else nivel
        except (TypeError, ValueError):
            pass

    # 🔴 O QUE A UNIDADE C ACRESCENTA — e por que cada campo está aqui.
    #
    # `texto_do_documento` e `fatos`: é do PDF OFICIAL da apólice que sai o nome
    # do plano contratado (`policy_document_evidence_service.py:230-318` já
    # extrai o bloco de assistência). Sem eles a Skill não tem como identificar
    # plano nenhum, e 📊 100 % das respostas continuariam `nao_sabemos_ainda`.
    #
    # `data_emissao` e `documento_da_condicao`: a condição geral que rege ESTE
    # contrato é a vigente NA EMISSÃO, não a de hoje (§7.2). Quem resolve isso é
    # `assistance_plans_susep_link`, pelo processo SUSEP impresso na própria
    # apólice — e é ele que amarra os planos publicados ao documento certo.
    documento = pack.get("official_policy_document_evidence") or {}
    texto_do_documento = str(documento.get("document_text") or "")
    data_emissao = selected.get("valid_from") or pack.get("valid_from")

    susep, documento_da_condicao = None, None
    if texto_do_documento:
        try:
            from app.services.knowledge.assistance_plans_susep_link import (
                condicao_geral_da_apolice,
            )

            condicao = condicao_geral_da_apolice(texto_do_documento, data_emissao, db=db)
            if condicao is not None:
                susep = condicao.susep_process
                documento_da_condicao = condicao.documento_id
        except Exception as exc:  # noqa: BLE001 — o elo nunca derruba o compositor
            logger.info("[composer] elo SUSEP indisponível: %s", type(exc).__name__)

    return {
        "insurer": selected.get("insurer_key") or pack.get("insurer_detected"),
        "ramo": pack.get("line_kind_detected") or selected.get("product") or pack.get("product_detected"),
        "produto": selected.get("product") or pack.get("product_detected"),
        "plano": plano,
        "nivel": nivel,
        "estado_do_plano": estado,
        "residencial": _is_residential_para_fallback(pack),
        "assistencia_confirmada": has_confirmed_assistance(facts),
        "fatos": facts,
        "texto_do_documento": texto_do_documento,
        "data_emissao": str(data_emissao) if data_emissao else None,
        "susep_process": susep,
        "documento_da_condicao": documento_da_condicao,
    }


def _is_residential_para_fallback(pack: Dict[str, Any]) -> bool:
    """Delega ao dono da regra. ⛔ Uma segunda cópia divergiria (CLAUDE.md §5)."""
    from app.services.assistance_policy import _is_residential

    return bool(_is_residential(pack))


def compose_policy_answer(*, question: str, result: Dict[str, Any]) -> str:
    """Compõe a resposta operacional humana para o resultado canônico."""
    return compose_policy_answer_with_meta(question=question, result=result)["text"]


def compose_policy_answer_with_meta(
    *, question: str, result: Dict[str, Any],
    db: Any = None, atendente: Optional[str] = None,
    client_facing: bool = False,
) -> Dict[str, Any]:
    """Como compose_policy_answer, mas retorna também os metadados da política
    de assistência para o Policy Response Contract da tool (E4b).

    🔴 SPEC-EXTRA-001.5 BLOCO B: é aqui, e SÓ aqui, que a base de planos entra
    no caminho vivo (§6, forma 90). Nenhuma tool nova é registrada em
    `graph.py`: a pergunta de cobertura já chega por `InfocapPolicyLookupTool`,
    e uma segunda porta para a mesma pergunta seria motor paralelo no chamador
    — o lugar onde ele não aparece no diff da tabela.

    🔴 SPEC-EXTRA-001.5.1 (D10) — **`client_facing` DIZ PARA QUEM SE FALA.**
    O veredito é UM; o texto é DOIS. `client_facing=True` (o atendente no
    WhatsApp) leva `texto_para_o_segurado`; `False` (o copiloto do corretor)
    leva o texto com a fonte. ⛔ A Skill continua PURA: ela não sabe por onde a
    resposta sai — ela devolve os dois e quem escolhe é este módulo, que é o
    único lugar onde o canal e o veredito estão na mesma mão.

    ⚠️ E os DOIS viajam no `meta` (`texto_para_o_corretor`,
    `texto_para_o_segurado`): o que não foi escolhido serve para AUDITORIA e
    para o guarda — nunca para envio.

    🔴 **UM VENCEDOR SÓ** (M-B5): quando a base responde, o retorno traz
    `cobertura` + `assistencia_da_base` e `assistance_policy` fica `None`;
    quando o fallback responde, é o inverso. Nunca os dois — dois vencedores
    dariam ao guard de `nodes.py` duas regras contraditórias sobre o mesmo
    texto.
    """
    result = result if isinstance(result, dict) else {}
    status = str(result.get("status") or "").strip()
    question_text = str(question or "")
    para_o_cliente = bool(client_facing)

    def _plain(text: str) -> Dict[str, Any]:
        return {"text": text, "assistance_policy": None,
                "cobertura": None, "assistencia_da_base": None,
                "texto_para_o_corretor": None, "texto_para_o_segurado": None,
                "client_facing": para_o_cliente}

    if status == "identity_mismatch":
        return _plain(
            "A identidade da apólice não foi confirmada com segurança. "
            "Por proteção, não vou exibir detalhes, cobertura, parcelas ou documento desta consulta. "
            "Me confirme o CPF/nome do cliente e o número da apólice para eu validar de novo."
        )
    if status in ("not_found", "policy_number_not_found"):
        return _plain("Não localizei apólice com esses dados na fonte da corretora. Confira o número ou me passe CPF/nome do cliente.")
    if status in ("multiple_matches", "ambiguous_customer"):
        return _plain("Encontrei mais de um cliente possível para esse termo. Me confirme o CPF ou o nome completo para eu seguir com segurança.")
    if status in ("ambiguous_policy", "policy_number_ambiguous"):
        text = _compose_options(result.get("matches") or [],
                                historico_oculto=result.get("historico_oculto"))
        client = _client_line(result)
        return _plain(text + (f"\n{client}" if client else ""))
    if status in ("blocked_not_configured", "blocked_missing_credentials"):
        return _plain("A conexão com o sistema de gestão ainda não está totalmente configurada para a sua corretora. Verifique a conexão em Personalização → Conectores.")
    if status == "ambiguous_connection":
        return _plain("Há mais de uma conexão ativa com o sistema de gestão. É preciso limpar as conexões duplicadas antes da consulta.")
    if status == "source_limited":
        return _plain("A fonte respondeu, mas não consegui isolar uma apólice única. Me passe o CPF, o nome completo do cliente ou o número da apólice.")
    if status == "client_found":
        base = "Localizei o cliente, mas nenhuma apólice vinculada foi retornada pela fonte nesta consulta."
        client = _client_line(result)
        return _plain(base + (f"\n{client}" if client else ""))
    if status != "found":
        return _plain("Não consegui concluir a consulta na fonte da corretora agora. Tente novamente em instantes.")

    pack = result.get("policy_evidence_pack") or {}
    facts = extract_policy_facts(pack)
    policy_result = apply_residential_assistance_policy(pack, facts)
    # 🔴 001.5 §6.4: o `pack` vai junto para o fact da regra deixar de nascer
    # órfão (`policy_locator_hash = None` fixo até 17/09/2026).
    facts = facts + policy_rule_facts(policy_result, pack)

    # 🔴 A BASE DE PLANOS — SPEC-EXTRA-001.5 BLOCO B.
    #
    # A porta é o VOCABULÁRIO (`servico_canonico`), não o regex: é ele que faz
    # "tem carro reserva?", "cobre granizo?" e "quantos km de guincho?" serem a
    # mesma pergunta para o sistema. Serviço não identificado → `None`, e o
    # fluxo antigo segue exatamente como era.
    veredito = None
    try:
        from app.services.skills.cobertura_e_assistencia import responder_cobertura

        veredito = responder_cobertura(
            pergunta=question_text,
            apolice=_apolice_para_a_skill(result, pack, facts, db=db),
            db=db, atendente=atendente,
        )
    except Exception as exc:  # noqa: BLE001 — a Skill nunca derruba o compositor
        logger.warning("[composer] Skill de cobertura indisponível: %s", type(exc).__name__)

    if veredito is not None:
        # 🔴 O CANAL ESCOLHE O TEXTO — e é a ÚNICA coisa que ele escolhe. O
        # veredito, o estado, a origem e a página são os mesmos nos dois lados.
        body = veredito.texto_para_o_segurado if para_o_cliente else veredito.texto
        if (not para_o_cliente) and veredito.origem == "regra_generica" and policy_result.get("statement"):
            # O fallback respondeu: a frase dele vai junto, porque é ela que o
            # contrato exige na resposta final (`assistance_policy_applied`).
            body = body + "\n" + str(policy_result["statement"])
        # ⚠️ Cobertura (granizo, alagamento) e assistência caem na mesma Skill,
        # mas a cobertura tem uma SEGUNDA fonte que a assistência não tem: as
        # coberturas estruturadas da apólice. Quando a base ainda não sabe, o
        # que já se sabia continua sendo dito — a lacuna da base não pode
        # apagar o que a fonte da corretora já entregava.
        # ⛔ E a lista estruturada NÃO entra no canal do segurado: ela cita
        #    "documento oficial, página N", que é exatamente o que o §5-C proíbe
        #    de chegar ao WhatsApp. No copiloto do corretor ela continua entrando.
        if (not para_o_cliente) and veredito.estado == "nao_sabemos_ainda" and veredito.tipo == "cobertura":
            extra = _compose_coverage_answer(pack, facts)
            if extra and any(f.get("fact_type") == "coverage" for f in facts):
                body = body + "\n\n" + extra
    elif _ASSIST_INTENT_RE.search(question_text):
        body = _compose_assistance_answer(result, pack, facts, policy_result)
    elif _COVERAGE_INTENT_RE.search(question_text):
        body = _compose_coverage_answer(pack, facts)
    elif _DEDUCTIBLE_INTENT_RE.search(question_text):
        deductibles = [f for f in facts if f.get("fact_type") == "deductible"]
        if deductibles:
            lines = ["Sobre franquia, a fonte registra:"]
            for f in deductibles[:5]:
                detail = f.get("source_detail") or {}
                page = detail.get("page")
                lines.append(f"- {f.get('label')}" + (f' (documento oficial, página {page})' if page else ""))
            body = "\n".join(lines)
        else:
            body = "A fonte não retornou franquia estruturada nesta consulta — não vou estimar valor sem evidência."
    elif _INSTALLMENT_INTENT_RE.search(question_text):
        body = _compose_installments_answer(pack, question_text)
    else:
        body = ""

    summary = _compose_operational_summary(result, pack)
    client = _client_line(result)
    parts = [body, summary if not body else None, client]
    # Pergunta específica: corpo primeiro + linha curta de contexto no fim.
    if body:
        header_line = summary.splitlines()[0] if summary else ""
        parts = [body, f"_{header_line}_" if header_line else None, None]
    if para_o_cliente and veredito is not None and body:
        # 🔴 No WhatsApp, o VEREDITO É A MENSAGEM — SPEC-EXTRA-001.5.1 (C1).
        #
        # 📊 19/09/2026, medido por este mesmo guarda: com a linha de contexto
        # colada no fim, a resposta ao segurado ia a **4 frases e 190
        # caracteres** e voltava a dizer "apólice 1234567890 — Auto Perfil
        # (HDI)". O teto da 001.2 é 3 frases e 450 caracteres, e a palavra
        # "apólice" é jargão de cozinha no meio de uma conversa de WhatsApp.
        #
        # ⚠️ A linha de contexto FICA para o corretor: lá ela responde "de qual
        # apólice você está falando?", que é uma pergunta que o corretor faz e
        # o segurado não.
        parts = [body, None, None]
    # 🔴 UM VENCEDOR SÓ — M-B5.
    #
    # `assistance_policy` é o que faz o contrato exigir "eletricista + chaveiro
    # + encanador" na resposta final (`infocap_tool.py:1097` → `nodes.py:344`).
    # Deixá-lo ligado quando a BASE respondeu faria o guard anular a resposta
    # certa sobre carro reserva por não conter a palavra "encanador" — que é
    # precisamente o defeito que §6.4 manda evitar.
    cobertura = veredito.para_registro() if veredito is not None else None
    da_base = None
    if veredito is not None and veredito.origem == "base":
        da_base = list(veredito.servicos_da_base)
        policy_result = None
    elif veredito is not None and veredito.origem == "nenhuma":
        # A Skill respondeu "não sabemos ainda" ou "não consegui abrir": o
        # fallback NÃO respondeu, então não pode exigir nada do texto.
        policy_result = None

    return {
        "text": "\n\n".join(p for p in parts if p),
        "assistance_policy": policy_result,
        "cobertura": cobertura,
        "assistencia_da_base": da_base,
        "facts": facts,
        # ⚠️ AUDITORIA, nunca envio: os DOIS textos viajam, e o `client_facing`
        # diz qual deles virou `text`. É com eles que o guarda prova que a
        # mesma verdade foi dita de duas formas — e é com eles que se confere,
        # depois de um incidente, o que o segurado leu.
        "texto_para_o_corretor": (veredito.texto if veredito is not None else None),
        "texto_para_o_segurado": (veredito.texto_para_o_segurado
                                  if veredito is not None else None),
        "client_facing": para_o_cliente,
    }
