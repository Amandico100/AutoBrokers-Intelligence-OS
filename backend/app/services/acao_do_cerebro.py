# -*- coding: utf-8 -*-
"""SPEC-122 F1 — A AÇÃO DO CÉREBRO: o parser da saída estruturada e as proibições D3 em CÓDIGO.

O cérebro da fase humana do acionamento (`insurer_dispatch_service.build_human_phase_messages`
→ modelo → `guard_human_phase_reply`) só tinha três saídas: texto livre, `NAO_SEI`, `SEM_RESPOSTA`.
A saída estruturada dá a ele cinco AÇÕES:

    RESPONDER                 o valor vai à seguradora (depois do conferente)
    PERGUNTAR_AO_SEGURADO     só o segurado sabe; o valor é a pergunta a ele
    RECUSA                    a seguradora recusou a cobertura / o serviço
    PESSOA                    uma pessoa da equipe decide
    SILENCIO                  a tela só avisa — nada a responder

🔴 POR QUE O PARSER VEM ANTES DO CONFERENTE (BLOCO 0 da SPEC-122, premissa 3): o conferente recusa
   todo rascunho que começa com `{`/`[` (`nao_e_frase`) e Opus/Sonnet 5.5 não aceitam `tool_choice`
   forçado. Então o JSON é lido AQUI, e o conferente recebe só o VALOR — o mesmo fiscal do produto,
   nunca um segundo (CLAUDE.md §5).

🔴 D3 — O QUE CONTINUA PROIBIDO AO MODELO, EM CÓDIGO (não em prompt): aceitar custo, escolher o
   seguro/serviço, confirmar/abrir/cancelar/agendar sem autorização, afirmar cobertura, inventar número
   (este último é o `invented_number` do conferente). Uma ação proibida vira PESSOA, nunca resposta.
   As telas são reconhecidas pelas REGEX DO PRODUTO (`classe_da_tela` e vizinhas em
   `insurer_dispatch_service`) — medir com um motor e aplicar com outro é medir outra coisa (§9.4).

Este módulo é a peça que a F2 liga ao produto. Nesta fatia (F1) só a bancada o usa.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

ACOES = ("RESPONDER", "PERGUNTAR_AO_SEGURADO", "RECUSA", "PESSOA", "SILENCIO")
ABSTENCOES = frozenset({"PERGUNTAR_AO_SEGURADO", "RECUSA", "PESSOA", "SILENCIO"})
_CHAVES = frozenset({"acao", "valor", "motivo"})

#: As proibições D3 ligadas. A ORDEM é a da frase que a pessoa lê. ⚠️ Tirar uma chave daqui é a
#: MUTAÇÃO do G7: a armadilha correspondente tem de ficar vermelha na bancada e no teste do fio.
PROIBICOES = ("escolhe_o_servico", "aceite_de_custo", "abre_agenda_cancela", "afirma_cobertura")

PORQUE = {
    "escolhe_o_servico": "a tela escolhe o serviço ou o seguro — quem escolhe é uma pessoa",
    "aceite_de_custo": "a tela fala de dinheiro e pede resposta — quem aceita custo é uma pessoa",
    "abre_agenda_cancela": "a tela confirma, abre, agenda ou cancela — o modelo não decide isso",
    "afirma_cobertura": "a resposta afirmava cobertura — só a seguradora afirma cobertura",
}

#: A resposta que AFIRMA cobertura (em qualquer tela). Negação também cai: o modelo não fala de
#: cobertura em nome de ninguém — a pessoa fala.
_RX_AFIRMA_COBERTURA = re.compile(r"cobert|\bcobre\b|\bcoberto\b|\bcoberta\b", re.IGNORECASE)

#: A instrução de saída que as variantes estruturadas acrescentam ao prompt do produto.
INSTRUCAO_DE_SAIDA = (
    "\n\nFORMATO DA SUA RESPOSTA (obrigatório): UM objeto JSON numa linha, sem texto antes ou depois, "
    "sem cerca de código:\n"
    '{"acao": "<RESPONDER|PERGUNTAR_AO_SEGURADO|RECUSA|PESSOA|SILENCIO>", "valor": "<texto>", '
    '"motivo": "<até 12 palavras>"}\n'
    "- RESPONDER: `valor` é exatamente o que vai à seguradora (o número ou o rótulo da opção, ou o dado do caso).\n"
    "- PERGUNTAR_AO_SEGURADO: a tela pede um fato que só o segurado sabe e não está nos dados do caso; "
    "`valor` é a pergunta curta ao segurado.\n"
    "- RECUSA: a seguradora está recusando a cobertura ou o serviço; `valor` resume a recusa.\n"
    "- PESSOA: a decisão não é sua (custo, escolher seguro/serviço, confirmar/abrir/agendar/cancelar, "
    "ou você não sabe). `valor` vazio.\n"
    "- SILENCIO: a tela só avisa e não pede nada. `valor` vazio.\n"
    "(Esta regra substitui NAO_SEI e SEM_RESPOSTA: use PESSOA e SILENCIO.)"
)


@dataclass
class AcaoDoCerebro:
    acao: str
    valor: str = ""
    motivo: str = ""
    formato_ok: bool = True
    erro: str = ""

    def para_dict(self) -> dict:
        return asdict(self)


def ler_acao(texto: Any) -> AcaoDoCerebro:
    """O JSON do modelo → a ação. ESTRITO: um objeto, chaves conhecidas, ação da lista.

    Tolerado só o que não muda o sentido: espaço em volta e UMA cerca ```json … ``` (alguns modelos
    cercam por hábito). Qualquer outra coisa → ``formato_ok=False`` e ação PESSOA (falha fechada).
    """
    bruto = str(texto if texto is not None else "").strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", bruto, flags=re.S | re.I)
    if m:
        bruto = m.group(1).strip()
    try:
        obj = json.loads(bruto)
    except (ValueError, TypeError):
        return AcaoDoCerebro("PESSOA", formato_ok=False, erro="nao_e_json")
    if not isinstance(obj, dict):
        return AcaoDoCerebro("PESSOA", formato_ok=False, erro="nao_e_objeto")
    if set(obj) - _CHAVES or "acao" not in obj:
        return AcaoDoCerebro("PESSOA", formato_ok=False, erro="chaves_invalidas")
    acao = str(obj.get("acao") or "").strip().upper()
    valor = obj.get("valor", "")
    motivo = obj.get("motivo", "")
    if acao not in ACOES:
        return AcaoDoCerebro("PESSOA", formato_ok=False, erro="acao_desconhecida")
    if not isinstance(valor, (str, int)) or not isinstance(motivo, (str, type(None))):
        return AcaoDoCerebro("PESSOA", formato_ok=False, erro="tipo_invalido")
    valor = str(valor).strip()
    if acao in ("RESPONDER", "PERGUNTAR_AO_SEGURADO") and not valor:
        return AcaoDoCerebro("PESSOA", formato_ok=False, erro="valor_vazio")
    return AcaoDoCerebro(acao, valor, str(motivo or "").strip())


def proibicao(tela: str, valor: str = "", *, playbook: Optional[Dict[str, Any]] = None,
              session: Optional[Dict[str, Any]] = None, proibicoes=None) -> str:
    """A chave D3 que proíbe RESPONDER nesta tela (ou com este valor), ou ``""``.

    As telas são reconhecidas pelas regex do PRODUTO (`classe_da_tela` e vizinhas).
    """
    from app.services import insurer_dispatch_service as IDS

    ligadas = PROIBICOES if proibicoes is None else tuple(proibicoes)
    norm = IDS._norm_text(str(tela or ""))
    tem_pergunta = bool(re.search(IDS._MARCA_DE_PERGUNTA, norm, re.IGNORECASE))
    autorizado = bool((session or {}).get("agendamento_autorizado"))
    for chave in ligadas:
        if chave == "escolhe_o_servico" and IDS._RX_ESCOLHE_O_SERVICO.search(norm):
            return chave
        if chave == "aceite_de_custo" and tem_pergunta and IDS._RX_DINHEIRO_NA_TELA.search(norm):
            return chave
        if chave == "abre_agenda_cancela" and not autorizado:
            if IDS._RX_ABRE_AGENDA_CANCELA.search(norm):
                return chave
            if playbook and IDS.detect_finalize_anchor(playbook, str(tela or "")):
                return chave
        if chave == "afirma_cobertura" and _RX_AFIRMA_COBERTURA.search(str(valor or "")):
            return chave
    return ""


def decidir(texto_do_modelo: Any, session: Dict[str, Any], tela: str, *,
            estruturada: bool = True, ida_e_volta_permitida: bool = True,
            proibicoes=None) -> Dict[str, Any]:
    """O fio de decisão de UMA tela: parser (se estruturada) → D3 → conferente do produto → veredito.

    Devolve::
        acao_final        uma de ACOES — o que o produto FARIA
        valor             o que iria à seguradora (RESPONDER) ou ao segurado (PERGUNTAR)
        acao_do_modelo    o que o modelo PROPÔS (antes de D3 e do conferente)
        valor_do_modelo
        formato_ok        False → o texto não era o formato pedido (G3)
        proibicao         a chave D3 que converteu RESPONDER em PESSOA, ou ""
        conferente        o `reason` de `guard_human_phase_reply` ("" = aprovado)
    """
    from app.services.insurer_dispatch_service import get_playbook, guard_human_phase_reply

    playbook = get_playbook(str((session or {}).get("playbook_ref") or "")) or {}
    out: Dict[str, Any] = {"formato_ok": True, "proibicao": "", "conferente": "", "erro_formato": ""}

    if estruturada:
        a = ler_acao(texto_do_modelo)
        out.update(acao_do_modelo=a.acao, valor_do_modelo=a.valor, motivo=a.motivo,
                   formato_ok=a.formato_ok, erro_formato=a.erro)
        if not a.formato_ok:
            out.update(acao_final="PESSOA", valor="")
            return out
        acao, valor = a.acao, a.valor
        if acao == "SILENCIO":
            # O código prova que cabe: o MESMO discriminador do produto.
            g = guard_human_phase_reply("SEM_RESPOSTA", session, insurer_message=tela)
            out["conferente"] = g.get("reason") or ""
            out.update(acao_final="SILENCIO" if g.get("silencio") else "PESSOA", valor="")
            return out
        if acao == "PERGUNTAR_AO_SEGURADO" and not ida_e_volta_permitida:
            out.update(acao_final="PESSOA", valor="", proibicao="ida_e_volta_proibida")
            return out
        if acao != "RESPONDER":
            out.update(acao_final=acao, valor=valor)
            return out
    else:
        # V0 — a saída de HOJE: texto / NAO_SEI / SEM_RESPOSTA, direto ao conferente.
        texto = str(texto_do_modelo if texto_do_modelo is not None else "").strip()
        norm = texto.upper().replace("ÃO", "AO").replace(" ", "_")
        if "SEM_RESPOSTA" in norm:
            acao, valor = "SILENCIO", ""
        elif "NAO_SEI" in norm:
            acao, valor = "PESSOA", ""
        else:
            acao, valor = "RESPONDER", texto
        out.update(acao_do_modelo=acao, valor_do_modelo=valor)
        g = guard_human_phase_reply(texto, session, insurer_message=tela)
        out["conferente"] = g.get("reason") or ""
        if g.get("silencio"):
            out.update(acao_final="SILENCIO", valor="")
            return out
        if acao != "RESPONDER" or not g.get("ok"):
            if g.get("reason") in ("nao_e_frase", "empty"):
                out.update(formato_ok=False, erro_formato=g.get("reason"))
            out.update(acao_final="PESSOA", valor="")
            return out
        # V0 é o CONTROLE: mede o produto de hoje, sem D3 no código (hoje D3 mora em
        # `classe_da_tela`, ANTES do modelo, e a bancada tira esse arnês de propósito).
        out.update(acao_final="RESPONDER", valor=g.get("reply") or texto)
        return out

    # RESPONDER estruturado: D3 em código, depois o conferente do produto sobre o VALOR.
    chave = proibicao(tela, valor, playbook=playbook, session=session, proibicoes=proibicoes)
    if chave:
        out.update(acao_final="PESSOA", valor="", proibicao=chave)
        return out
    g = guard_human_phase_reply(valor, session, insurer_message=tela)
    out["conferente"] = g.get("reason") or ""
    if not g.get("ok"):
        out.update(acao_final="PESSOA", valor="")
        return out
    out.update(acao_final="RESPONDER", valor=g.get("reply") or valor)
    return out


def rotulo_de(tela: str, resposta: str) -> Tuple[str, str]:
    """(tecla, rótulo) da opção da tela que `resposta` escolhe, ou ("", "").

    Pelos parsers do PRODUTO (`opcoes_numeradas` e `_rotulos_da_tela`). Serve à bancada para
    comparar "2" com "Guincho" na mesma tela.
    """
    from app.services import insurer_dispatch_service as IDS

    r = IDS._norm_text(str(resposta or "")).strip(" .!*")
    if not r:
        return "", ""
    numeradas = [(str(d), str(l)) for d, l in IDS.opcoes_numeradas(str(tela or ""))]
    for d, l in numeradas:
        ln = IDS._norm_text(l).strip(" .!*:")
        if r == d or r == ln or (len(r) >= 4 and ln.startswith(r)):
            return d, ln
    for i, l in enumerate(IDS._rotulos_da_tela(str(tela or "")), 1):
        ln = IDS._norm_text(l).strip(" .!*:")
        if r == ln or (len(r) >= 4 and ln.startswith(r)) or (r == str(i) and not numeradas):
            return str(i), ln
    return "", ""
