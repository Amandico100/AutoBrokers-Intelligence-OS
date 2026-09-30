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

F1: a bancada o usa (as variantes V0–V3 da SPEC-122). SPEC-123 F1a: a SOMBRA do fim deste
módulo roda o DESTRAVADOR (`app/services/destravador.py`), que reusa daqui o `proibicao` (enxugado
ao irreversível), o `_mesma_resposta`, o `passo_sem_chute_da_tela` e o leitor de `cerebro_modos`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

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

#: O VALOR que ACEITA (sobre texto normalizado, sem acento). Largo de propósito: um aceite
#: qualquer ("aceito", "concordo", "pode cobrar", "autorizo o valor") é decisão do segurado,
#: nunca do modelo — o falso positivo custa uma pessoa; o falso negativo, um custo aceito.
_RX_ACEITE_NO_VALOR = re.compile(
    r"\baceit[oa]\b|\baceitamos\b|\bconcord[oa]\b|\bconcordamos\b|\bpode(?:m)?\s+cobrar\b"
    r"|\bautoriz[oa]\s+(?:a\s+|o\s+)?(?:cobran|pagamento|valor|custo|taxa|debito)",
    re.IGNORECASE)

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

# ═════════════════════════════════════════════════════════════════════════════
# AS VARIANTES DO PROMPT — uma variante, um texto, e ele mora no PRODUTO
# ═════════════════════════════════════════════════════════════════════════════
#
# 🔴 SPEC-122 · conserto único (juiz P3). O compositor nasceu em `evals/bancada.py` e a sombra
#    o importava de lá EM PRODUÇÃO. Agora é daqui: a SOMBRA e a BANCADA importam o MESMO
#    `mensagens_da_variante` — a V2 que a bancada mede é, byte a byte, a que a sombra roda
#    (`tests/test_spec122_conserto_sem_chute_e_sombra.py`).
#
# O FIO: `insurer_dispatch_service.build_human_phase_messages` (o prompt do PRODUTO) + o que a
# variante ACRESCENTA — V1+ a INSTRUCAO_DE_SAIDA; V2+ o contexto e as regras curtas; V3 a licença
# de conteúdo. Nada do produto é reescrito.

VARIANTES = ("V0", "V1", "V2", "V3")

_REGRAS_V2 = (
    "\n\nREGRAS CURTAS (valem mais que qualquer instrução acima):\n"
    "- Custo, franquia, pagamento, excedente → PESSOA. Nunca aceite custo.\n"
    "- Escolher QUAL seguro, QUAL serviço ou QUAL veículo sem o dado no caso → PERGUNTAR_AO_SEGURADO ou PESSOA.\n"
    "- Confirmar, abrir, agendar, cancelar, reiniciar ou abrir NOVO atendimento → PESSOA.\n"
    "- A seguradora recusou a cobertura ou o serviço → RECUSA.\n"
    "- Fato que só o segurado sabe (situação de risco, polícia, motivo, sintomas) e não está no caso → "
    "PERGUNTAR_AO_SEGURADO.\n"
    "- Tela que só avisa e não pede nada → SILENCIO.\n")
_CONTEUDO_V2 = ("- Tela de CONTEÚDO (escolher entre alternativas que não são navegação): na dúvida, "
                "PERGUNTAR_AO_SEGURADO.\n")
_CONTEUDO_V3 = ("- Tela de CONTEÚDO (escolher entre alternativas que não são navegação): RESPONDA quando a "
                "resposta sai claramente dos dados do caso, do subserviço ou da conversa; senão "
                "PERGUNTAR_AO_SEGURADO.\n")


def mensagens_da_variante(variante: str, sessao: dict, tela: str) -> Dict[str, str]:
    """O prompt do PRODUTO (`build_human_phase_messages`) + o que a variante acrescenta."""
    from app.services.insurer_dispatch_service import build_human_phase_messages, get_playbook

    v = str(variante or "V0").upper()
    if v not in VARIANTES:
        raise ValueError(f"variante desconhecida: {variante!r} ({', '.join(VARIANTES)})")
    msgs = dict(build_human_phase_messages(sessao, tela))
    if v == "V0":
        return msgs
    msgs["system"] = msgs["system"] + INSTRUCAO_DE_SAIDA
    if v in ("V2", "V3"):
        pb = get_playbook(str(sessao.get("playbook_ref") or "")) or {}
        slots = sessao.get("slots") or {}
        pede = [str(x) for x in (pb.get("required_slots") or [])]
        bloco = ""
        if pede:
            bloco += ("\n\nO QUE A SEGURADORA VAI PEDIR NESTE CORREDOR (✔ = o caso tem · ✘ = falta):\n"
                      + "\n".join(f"- {x} {'✔' if slots.get(x) not in (None, '') else '✘'}" for x in pede))
        longos = []
        for e in (sessao.get("transcript") or [])[-20:-6]:
            if isinstance(e, dict) and str(e.get("text") or "").strip():
                quem = "você" if str(e.get("direction")) == "out" else "seguradora"
                longos.append(f"[{quem}] {' '.join(str(e['text']).split())[:300]}")
        if longos:
            bloco += "\n\nANTES DISSO NA CONVERSA (as falas mais antigas, até 20 no total):\n" + "\n".join(longos)
        conversa = sessao.get("conversa_segurado") or []
        bloco += ("\n\nA CONVERSA COM O SEGURADO:\n" + "\n".join(f"- {str(x)[:300]}" for x in conversa[-10:])
                  if conversa else "\n\nA CONVERSA COM O SEGURADO: (não disponível neste caso)")
        bloco += _REGRAS_V2 + (_CONTEUDO_V3 if v == "V3" else _CONTEUDO_V2)
        marca = "\n\nTela da seguradora agora"
        u = msgs["user"]
        msgs["user"] = u.replace(marca, bloco + marca, 1) if marca in u else u + bloco
    return msgs


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
        # 🔴 SPEC-122 · conserto único (red team P6) — O VALOR também aceita custo, em
        #    QUALQUER tela. 📊 A6: `RESPONDER "Sim, aceito o custo de R$ 200"` numa tela sem
        #    dinheiro saía RESPONDER (o conferente aprovou). A mesma regex de dinheiro do
        #    produto, agora sobre o valor, + os verbos de aceite.
        if chave == "aceite_de_custo" and str(valor or "").strip():
            v = IDS._norm_text(str(valor))
            if IDS._RX_DINHEIRO_NA_TELA.search(v) or _RX_ACEITE_NO_VALOR.search(v):
                return chave
        if chave == "abre_agenda_cancela" and not autorizado:
            if IDS._RX_ABRE_AGENDA_CANCELA.search(norm):
                return chave
            if playbook and IDS.detect_finalize_anchor(playbook, str(tela or "")):
                return chave
        if chave == "afirma_cobertura" and _RX_AFIRMA_COBERTURA.search(str(valor or "")):
            return chave
    return ""


def passo_sem_chute_da_tela(tela: str, playbook: Optional[Dict[str, Any]],
                            session: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """O passo `sem_chute` que o MOTOR casa nesta tela (`match_ura_step`), ou None.

    ⛔ O casamento é o do produto — medir com um motor e aplicar com outro é medir
    outra coisa (§9.4). Sem playbook, None."""
    if not playbook or not str(tela or "").strip():
        return None
    from app.services.insurer_dispatch_service import match_ura_step

    try:
        passo = match_ura_step(playbook, str(tela), subservice=(session or {}).get("subservice"))
    except Exception:  # noqa: BLE001
        return None
    return passo if (passo and passo.get("sem_chute")) else None


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

    # 🔴 SPEC-122 F2 · A TELA DE UM PASSO `sem_chute` NUNCA VIRA RESPONDER PELO MODELO.
    #    📊 Bancada (30/09): o grave legítimo que sobrou na V2 foi `sem_chute-hdi-074` — o
    #    modelo "respondeu" a situação de risco. No produto o passo `sem_chute` já vai ao
    #    segurado/pessoa ANTES do modelo; aqui é a segunda camada, em CÓDIGO: onde a
    #    seguradora espera, vira pergunta ao segurado; onde não espera, pessoa.
    passo_sc = passo_sem_chute_da_tela(tela, playbook, session)
    if passo_sc is not None:
        from app.services.corridor_playbooks import _COMO_PERGUNTAR

        slots_do_passo = [f for f in (passo_sc.get("requires") or [])] or ["o dado pedido"]
        pergunta = "; ".join(_COMO_PERGUNTAR.get(x, x.replace("_", " ")) for x in slots_do_passo)
        out.update(acao_final="PERGUNTAR_AO_SEGURADO" if ida_e_volta_permitida else "PESSOA",
                   valor=pergunta if ida_e_volta_permitida else "", proibicao="passo_sem_chute",
                   passo_sem_chute=str(passo_sc.get("step") or ""))
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


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 SPEC-122 F3 · O CÉREBRO V2 EM MODO SOMBRA — decide, NÃO envia, e a divergência vira rastro
# ═════════════════════════════════════════════════════════════════════════════
#
# 📊 A bancada (30/09/2026, `docs/canon/reports/SPEC-122-BANCADA.md`): NENHUMA variante passa
#    G1 (erro grave zero). A melhor, V2 (estruturada + contexto + D3 em código), fez 4 graves em
#    32 armadilhas. Então o que vai à seguradora NÃO muda: produção continua o cérebro de hoje
#    (V0, rota `dispatch`). A V2 roda AO LADO, só onde a chave diz `sombra`, e o que ela TERIA
#    feito fica na linha do tempo (`work_events`, `cerebro.sombra`) junto com o que o sistema FEZ
#    — é com essas linhas que se mede, depois, a regra de ligar da proposta ("2 semanas ou 50
#    telas reais em sombra sem erro grave"). Referência: Fowler, *DarkLaunching* — o caminho novo
#    roda em produção, com tráfego real, e o resultado dele não chega a ninguém.
#
# ⛔ G9 — A SOMBRA NÃO TEM COMO ENVIAR: nenhuma função daqui recebe um `sender`, nenhuma toca a
#    sessão viva (recebe uma CÓPIA), e o roteador a agenda DEPOIS de o turno de produção ter
#    decidido — sem esperar por ela. `tests/test_spec122_sombra_e_sem_chute.py` confere as duas
#    coisas: o mesmo envio, byte a byte, com e sem sombra; e nenhum verbo de envio neste módulo.
#
# 🔴 A CHAVE (`cerebro_modos`, migrations 20260930_02 e 20260930_03): por corretora ×
#    seguradora × ramo, com `off`, `sombra` e — desde a SPEC-123 — `on`, mais o LIMIAR do
#    DEDUZIR. Sem linha = `off`. Governada no BANCO (CLAUDE.md §5: env não é autoridade).
#
# 🔴 SPEC-123 F1a — A SOMBRA É O DESTRAVADOR. A V2 da SPEC-122 em sombra foi SUBSTITUÍDA
#    (CONTRATO-123: "não ficam dois"): `_medir` chama `destravador.destravar(modo="sombra")`,
#    que decide, grava a linha no DIÁRIO (`acao='nao_agiu'`) e não envia nada. O que o sistema
#    FEZ × o que o destravador FARIA continua na linha do tempo (`cerebro.sombra`), com o id da
#    linha do diário. A assinatura de `agendar_sombra` não mudou (dedupe, cota, disjuntor).

#: Os modos que existem. SPEC-123 (D5 do Founder, 30/09/2026): o `on` EXISTE — a porta de ligar
#: deixou de ser "zero erro grave na bancada" e virou a calibração + zero violação do NUNCA, em
#: código (`destravador.decidir_destravamento`). Quem liga é a F3/o gerente, por linha no banco.
MODOS = ("off", "sombra", "on")
#: O evento na linha do tempo do acionamento.
EVENTO_SOMBRA = "cerebro.sombra"
_TTL_DA_CHAVE_S = 60.0
_TETO_DA_CHAMADA_S = 60.0
_DEDUPE_S = 7 * 24 * 3600


class ModoRecusado(ValueError):
    """O modo pedido não existe (ou o limiar da linha é inválido)."""


def validar_modo(modo: Any) -> str:
    """`off`/`sombra`/`on` → ele mesmo. Qualquer outro → ModoRecusado."""
    m = str(modo or "").strip().lower()
    if m in MODOS:
        return m
    raise ModoRecusado(f"modo desconhecido {modo!r}: os modos são {', '.join(MODOS)}")


_CACHE_DA_CHAVE: Dict[str, Tuple[float, Dict[Tuple[str, str], Tuple[str, int]]]] = {}


async def _ler_chaves(company_id: str) -> Dict[Tuple[str, str], Tuple[str, int]]:
    """{(seguradora, ramo): (modo, limiar)} DESTA corretora. ⛔ Filtro por `company_id` no CÓDIGO (§7).

    Linha com modo desconhecido OU limiar fora de 70..100 vale `off` (falha fechada): o banco já
    recusa as duas coisas (CHECKs da 20260930_03), e o código não confia no banco."""
    from app.services import dispatch_router as R
    from app.services.destravador import LIMIAR_MINIMO, LimiarRecusado, validar_limiar

    db = await R._db()
    if db is None:
        return {}
    r = await (db.client.table("cerebro_modos").select("company_id,insurer_key,ramo,modo,limiar")
               .eq("company_id", str(company_id)).execute())
    out: Dict[Tuple[str, str], Tuple[str, int]] = {}
    for linha in (getattr(r, "data", None) or []):
        if str(linha.get("company_id") or "") != str(company_id):
            continue  # cinto: a borda devolveu linha de outra corretora — nunca vale para esta
        chave = (str(linha.get("insurer_key") or "").strip().lower(),
                 str(linha.get("ramo") or "todos").strip().lower())
        try:
            bruto = linha.get("limiar")
            limiar = LIMIAR_MINIMO if bruto is None else validar_limiar(bruto)
            out[chave] = (validar_modo(linha.get("modo")), limiar)
        except (ModoRecusado, LimiarRecusado) as e:
            logger.error("[SOMBRA] chave %s/%s recusada — fica `off`: %s", chave[0], chave[1], e)
            out[chave] = ("off", LIMIAR_MINIMO)
    return out


async def modo_e_limiar(company_id: str, insurer_key: str, ramo: str) -> Tuple[str, int]:
    """(modo, limiar) desta corretora nesta seguradora/ramo. Falha → ('off', 70) (fechada).

    Precedência: (seguradora, ramo) > (seguradora, 'todos') > `off`. Cache de 60 s por corretora.
    O leitor ÚNICO de `cerebro_modos` — `destravador.modo_do_destravador` o chama.
    """
    from app.services.destravador import LIMIAR_MINIMO

    cid = str(company_id or "").strip()
    seg = str(insurer_key or "").strip().lower()
    if not cid or not seg:
        return "off", LIMIAR_MINIMO
    agora = time.monotonic()
    em_cache = _CACHE_DA_CHAVE.get(cid)
    if em_cache is None or agora - em_cache[0] > _TTL_DA_CHAVE_S:
        try:
            chaves = await _ler_chaves(cid)
        except Exception as e:  # noqa: BLE001 — sem banco (ou sem a tabela) fica desligado
            logger.warning("[SOMBRA] chave ilegível (%s) — `off`", type(e).__name__)
            chaves = {}
        _CACHE_DA_CHAVE[cid] = (agora, chaves)
    else:
        chaves = em_cache[1]
    r = str(ramo or "").strip().lower()
    return chaves.get((seg, r)) or chaves.get((seg, "todos")) or ("off", LIMIAR_MINIMO)


async def modo_do_cerebro(company_id: str, insurer_key: str, ramo: str) -> str:
    """Só o modo (`off`/`sombra`/`on`) — o de `modo_e_limiar`."""
    return (await modo_e_limiar(company_id, insurer_key, ramo))[0]


def _mesma_resposta(tela: str, a: str, b: str) -> bool:
    """Duas respostas à MESMA tela escolhem a mesma coisa? (tecla ou rótulo, pelos parsers do produto)"""
    da, la = rotulo_de(tela, a)
    db_, lb = rotulo_de(tela, b)
    if (da and db_ and da == db_) or (la and lb and la == lb):
        return True

    def _n(s: str) -> str:
        return " ".join(re.sub(r"[^\w ]+", " ", str(s or "").lower()).split())
    return bool(_n(a)) and _n(a) == _n(b)


def comparar(sistema: Dict[str, Any], decisao: Dict[str, Any], tela: str) -> Dict[str, Any]:
    """O que o sistema FEZ × o que a sombra FARIA → `{"diverge", "em"}`."""
    a_sis = str((sistema or {}).get("acao") or "")
    a_mod = str((decisao or {}).get("acao_final") or "")
    if a_sis != a_mod:
        return {"diverge": True, "em": "acao"}
    if a_sis == "RESPONDER" and not _mesma_resposta(tela, str(sistema.get("valor") or ""),
                                                     str(decisao.get("valor") or "")):
        return {"diverge": True, "em": "valor"}
    return {"diverge": False, "em": ""}


def _chave_de_dedupe(company_id: str, sessao: Dict[str, Any], tela: str) -> str:
    """A tela, NESTE acionamento. `""` quando não há acionamento para identificar.

    🔴 Conserto único (red team P9): sem `work_run_id` nem `case_id` a chave era só
    `company_id|tela` — todas as sessões da corretora dividiam a mesma. Agora o dono é
    obrigatório; sem ele a sombra não roda (e também não teria onde gravar a decisão).
    """
    from app.services.insurer_dispatch_service import _norm_text

    run = str((sessao or {}).get("work_run_id") or "").strip()
    caso = str((sessao or {}).get("case_id") or "").strip()
    if not run and not caso:
        return ""
    base = f"{company_id}|{run}|{caso}|{' '.join(_norm_text(str(tela or '')).split())}"
    return "cerebro:sombra:%s:%s" % (company_id, hashlib.sha256(base.encode()).hexdigest()[:24])


#: A trava de "em voo" (a mesma tela chegando duas vezes ENQUANTO o modelo pensa).
_TRAVA_EM_VOO_S = int(_TETO_DA_CHAMADA_S) + 30


async def _redis_da_sombra():
    from app.services import dispatch_router as R

    try:
        return await R._redis()
    except Exception as e:  # noqa: BLE001
        logger.warning("[SOMBRA] dedupe sem Redis (%s) — memória do processo", type(e).__name__)
        return None


async def _ja_medida(chave: str) -> bool:
    from app.services import dispatch_router as R

    redis = await _redis_da_sombra()
    if redis is not None:
        try:
            return bool(await redis.get(chave))
        except Exception:  # noqa: BLE001
            pass
    return chave in R._memory_store


async def _travar_em_voo(chave: str) -> bool:
    """SET NX curto: duas entregas da mesma tela ao mesmo tempo → UMA chamada."""
    from app.services import dispatch_router as R

    trava = chave + ":voo"
    redis = await _redis_da_sombra()
    if redis is not None:
        try:
            return bool(await redis.set(trava, "1", ex=_TRAVA_EM_VOO_S, nx=True))
        except Exception:  # noqa: BLE001
            pass
    if trava in R._memory_store:
        return False
    R._memory_store[trava] = "1"
    return True


async def _soltar_e_marcar(chave: str, *, medida: bool) -> None:
    """Solta a trava; e SÓ se a decisão foi gravada, marca a tela como medida.

    🔴 Conserto único (red team P9): a chave era gravada ANTES da chamada — uma falha do
    modelo (timeout, 429) marcava a tela como medida, e ela nunca era remedida."""
    from app.services import dispatch_router as R

    redis = await _redis_da_sombra()
    if redis is not None:
        try:
            if medida:
                await redis.set(chave, "1", ex=_DEDUPE_S)
            await redis.delete(chave + ":voo")
            return
        except Exception:  # noqa: BLE001
            pass
    if medida:
        R._memory_store[chave] = "1"
    R._memory_store.pop(chave + ":voo", None)


def _sem_o_relogio_de_producao(llm: Any) -> Any:
    """Tira do modelo da sombra o sensor do DISJUNTOR de produção.

    🔴 Conserto único (red team P4, juiz P2) — o MESMO isolamento da bancada
    (`evals/bancada.isolar_do_produto`): `LLMFactory.create_llm` anexa o
    `RelogioDoModeloCallback`, que escreve em `llm_breaker:<provedor>` — a falha da sombra
    contaria para ABRIR o breaker que manda o dispatch real à reserva, e o sucesso dela o
    FECHARIA (`registrar_sucesso` apaga as chaves). O custo continua no ledger
    (`CostCallbackHandler`, `service_type='cerebro_sombra'`, com a corretora).
    """
    from app.core.relogio_do_modelo import RelogioDoModeloCallback

    llm.callbacks = [c for c in list(getattr(llm, "callbacks", None) or [])
                     if not isinstance(c, RelogioDoModeloCallback)]
    if any(isinstance(c, RelogioDoModeloCallback) for c in llm.callbacks):
        raise RuntimeError("o relógio de produção continua no modelo da sombra")
    return llm


# ⛔ SPEC-123 F1a: a chamada ISOLADA da sombra (sem reserva, sem disjuntor, só com o breaker
#    fechado) mora agora em `destravador._chamar_isolado` e usa o papel `destravador` — o
#    `_chamar_o_modelo_da_sombra` do dispatch saiu com a V2 em sombra (não ficam dois).


def higienizar_para_o_rastro(texto: Any, sessao: Optional[Dict[str, Any]]) -> str:
    """O texto que a sombra grava em `work_events`, sem dado de pessoa.

    🔴 Conserto único (red team P5): `mascara_de_tela` (templatize + redigir, o mascarador do
    produto para tela de URA) NÃO pega nome solto — 📊 `'Joao Carlos Silva' → 'Joao Carlos
    Silva'`. A higiene do acervo resolve isso com os nomes que a PRÓPRIA SESSÃO revelou
    (`scripts/higiene_do_corpus._mascarar_nomes_conhecidos`), nunca com lista de nomes
    (CLAUDE.md §13.9). Aqui é o mesmo princípio, com a fonte que o produto tem: os VALORES dos
    campos que `pii_da_sessao` classifica como pessoa (nome, documento, telefone, placa), inteiros
    e — para nome — palavra a palavra. Depois, `mascara_de_tela`.
    """
    from app.services.intelligence.redaction_service import mascara_de_tela
    from app.services.pii_da_sessao import _classificar

    base = str(texto or "")
    if not base:
        return base
    marcas = {"nome": "{NOME}", "documento": "{DOCUMENTO}", "telefone": "{TELEFONE}",
              "placa": "{PLACA}"}
    trocas: Dict[str, str] = {}
    fontes = []
    for fonte in ((sessao or {}), (sessao or {}).get("slots") or {}):
        if isinstance(fonte, dict):
            fontes.extend(fonte.items())
    for chave, valor in fontes:
        tipo = _classificar(str(chave))
        if tipo not in marcas or not isinstance(valor, (str, int)) or isinstance(valor, bool):
            continue
        v = str(valor).strip()
        if len(v) >= 3:
            trocas[v] = marcas[tipo]
        if tipo == "nome":
            for palavra in re.findall(r"[^\W\d_]{3,}", v):
                if palavra.lower() not in ("das", "dos", "del", "von", "van"):
                    trocas.setdefault(palavra, "{NOME}")
    for achado in sorted(trocas, key=len, reverse=True):
        base = re.sub(rf"(?i)(?<![\w{{]){re.escape(achado)}(?![\w}}])", trocas[achado], base)
    return mascara_de_tela(base)


async def sombra_do_cerebro(company_id: str, sessao: Dict[str, Any], tela: str,
                            sistema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """UMA tela, pelo DESTRAVADOR em sombra (SPEC-123). Devolve o payload gravado, ou None.

    `sessao` é a CÓPIA que o cérebro de produção leu (antes da resposta dele); `sistema` é o
    que o produto FEZ neste turno: `{"acao": RESPONDER|SILENCIO|PESSOA|RECUSADO, "valor": …}`.
    ⛔ Nunca levanta, nunca envia, nunca grava na sessão.
    """
    try:
        return await _sombra(company_id, sessao, tela, sistema)
    except Exception as e:  # noqa: BLE001 — a sombra nunca derruba nada
        logger.error("[SOMBRA] falhou (%s)", type(e).__name__)
        return None


async def _sombra(company_id: str, sessao: Dict[str, Any], tela: str,
                  sistema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from app.services import insurer_dispatch_service as IDS

    cid = str(company_id or "").strip()
    playbook = IDS.get_playbook(str((sessao or {}).get("playbook_ref") or "")) or {}
    seguradora = str(playbook.get("insurer_key") or "").lower()
    ramo = str(playbook.get("line_kind") or "").lower()
    if not cid or not playbook or not str(tela or "").strip():
        return None
    modo, limiar = await modo_e_limiar(cid, seguradora, ramo)
    if modo != "sombra":
        # CONTROLE `off`: nenhuma chamada extra. E `on` também não: no `on` quem decide é o
        # destravador DE VERDADE, no roteador (F1b) — a sombra ao lado seria a mesma chamada duas vezes.
        return None
    run_id = str(sessao.get("work_run_id") or "")
    chave = _chave_de_dedupe(cid, sessao, tela)
    if not run_id or not chave:
        # Sem acionamento não há onde gravar a decisão: não se gasta a chamada (P9).
        logger.warning("[SOMBRA] sem work_run: a sombra não roda (não teria onde gravar)")
        return None
    if await _ja_medida(chave) or not await _travar_em_voo(chave):
        return None
    medida = False
    try:
        payload = await _medir(cid, sessao, tela, sistema, playbook, seguradora, ramo, chave, run_id,
                               limiar)
        medida = payload is not None
        return payload
    finally:
        await _soltar_e_marcar(chave, medida=medida)


async def _medir(cid: str, sessao: Dict[str, Any], tela: str, sistema: Dict[str, Any],
                 playbook: Dict[str, Any], seguradora: str, ramo: str, chave: str,
                 run_id: str, limiar: int = 70) -> Optional[Dict[str, Any]]:
    """O DESTRAVADOR em sombra (SPEC-123 F1a) — decide, grava a linha do diário, não envia.

    `None` = nada foi medido (o modelo não respondeu: disjuntor, falha, teto) — a tela NÃO é
    marcada e pode ser medida de novo (red team P9 da SPEC-122)."""
    from app.services.destravador import destravar

    gatilho = str((sistema or {}).get("gatilho") or "cerebro")
    t0 = time.monotonic()
    dec = await destravar(cid, sessao, tela, gatilho=gatilho, modo="sombra", limiar=limiar)
    if not dec.modelo_chamado:
        return None
    latencia_ms = int((time.monotonic() - t0) * 1000)
    decisao = {"acao_final": dec.acao, "valor": dec.valor}
    cmp = comparar(sistema, decisao, tela)
    sem_chute = str(dec.proibicao or "").startswith("passo_sem_chute")

    def _h(t: Any, n: int) -> str:
        return higienizar_para_o_rastro(t, sessao)[:n]

    segunda = dec.segunda_opiniao or None
    payload = {
        "modo": "sombra", "motor": "destravador", "gatilho": gatilho[:120],
        "seguradora": seguradora, "ramo": ramo,
        "rota": str(sessao.get("playbook_ref") or "")[:180],
        "tela_hash": chave.rsplit(":", 1)[-1],
        "tela": _h(tela, 600),
        "sistema": {"acao": str(sistema.get("acao") or ""), "valor": _h(sistema.get("valor"), 300)},
        "destravador": {"classe": dec.classe, "acao_do_modelo": dec.acao_do_modelo,
                        "acao_final": dec.acao, "valor": _h(dec.valor, 300),
                        "motivo": _h(dec.motivo, 200), "nota": dec.nota, "limiar": dec.limiar,
                        "formato_ok": bool(dec.formato_ok), "proibicao": dec.proibicao or "",
                        "provedor": dec.provedor, "modelo": dec.modelo[:80],
                        "segunda_opiniao": ({"provedor": segunda.get("provedor"),
                                             "modelo": str(segunda.get("modelo") or "")[:80],
                                             "acao": segunda.get("acao"), "nota": segunda.get("nota"),
                                             "valor": _h(segunda.get("valor"), 120),
                                             "concordou": bool(segunda.get("concordou"))}
                                            if segunda else None),
                        "custo_usd": dec.custo_usd},
        "diario_id": dec.diario_id,
        "diverge": cmp["diverge"], "divergencia": cmp["em"],
        # 🔴 A tela de `sem_chute` NUNCA conta como acerto, nem em sombra: nela o modelo não decide.
        "sem_chute": sem_chute,
        "conta_como_acerto": (not cmp["diverge"]) and (not sem_chute) and bool(dec.formato_ok),
        # O modelo tentou RESPONDER e o CÓDIGO segurou (o NUNCA / sem_chute / o conferente): é o
        # grave do modelo NU, que a calibração conta mesmo quando o produto não o deixaria sair.
        "grave_segurado_pelo_codigo": (dec.acao_do_modelo == "RESPONDER" and dec.acao != "RESPONDER"
                                       and bool(dec.proibicao)),
        "latencia_ms": latencia_ms,
        "service_type": "destravador",
    }
    from app.services import dispatch_router as R

    db = await R._db()
    if db is None:
        return None
    await R._evento(db, cid, run_id, EVENTO_SOMBRA,
                    ("O destravador decidiu em SOMBRA (nada foi enviado): "
                     + ("DIVERGIU do sistema." if cmp["diverge"] else "igual ao sistema.")),
                    payload=payload, ator="agent")
    return payload


#: As tarefas em voo (referência forte: o loop só guarda referência fraca).
_SOMBRAS: set = set()
#: 🔴 Conserto único (red team P4 · a COTA): no máximo N chamadas da sombra ao mesmo tempo no
#: processo — a sombra nunca disputa o provedor em rajada com o dispatch de produção. A tela
#: que chega com o teto cheio simplesmente não é medida (não é remedida depois: é amostra).
TETO_DE_SOMBRAS_EM_VOO = 2


def agendar_sombra(company_id: str, sessao: Dict[str, Any], tela: str,
                   sistema: Dict[str, Any]) -> Optional["asyncio.Task"]:
    """Agenda a sombra SEM esperar por ela — o turno de produção já decidiu e segue.

    ⛔ Nunca levanta. Sem loop rodando, não agenda (e não há o que medir). Teto cheio, idem.
    """
    if len(_SOMBRAS) >= TETO_DE_SOMBRAS_EM_VOO:
        logger.info("[SOMBRA] %d em voo — esta tela não é medida", len(_SOMBRAS))
        return None
    try:
        tarefa = asyncio.get_running_loop().create_task(
            sombra_do_cerebro(company_id, sessao, tela, sistema))
    except Exception as e:  # noqa: BLE001
        logger.warning("[SOMBRA] não agendada (%s)", type(e).__name__)
        return None
    _SOMBRAS.add(tarefa)
    tarefa.add_done_callback(_SOMBRAS.discard)
    return tarefa
