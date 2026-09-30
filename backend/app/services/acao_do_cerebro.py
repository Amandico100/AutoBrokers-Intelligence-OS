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

F1: a bancada o usa. F2/F3 (SPEC-122): o produto usa `decidir` na SOMBRA do cérebro (o fim
deste módulo), e a regra do `sem_chute` vale nas duas.
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
# 🔴 A CHAVE (`cerebro_modos`, migration 20260930_02): por corretora × seguradora × ramo, com
#    `off` e `sombra`. Sem linha = `off`. Governada no BANCO (CLAUDE.md §5: env não é
#    autoridade); quem liga é o Founder.

#: Os modos que existem. ⛔ `on` NÃO está aqui, e a razão é a de `MODO_ON_RECUSADO`.
MODOS = ("off", "sombra")
MODO_ON_RECUSADO = (
    "o modo `on` (a V2 decidindo o que vai à seguradora) está RECUSADO: a bancada da SPEC-122 "
    "(30/09/2026) não aprovou nenhuma variante — G1 exige zero erro grave e a melhor (V2) teve 4 "
    "em 32 armadilhas. Ligar exige a regra da proposta (2 semanas ou 50 telas reais em sombra sem "
    "erro grave, medidas nas linhas `cerebro.sombra`) e uma decisão do Founder numa SPEC.")
#: O `service_type` do ledger (`token_usage_logs`) — o custo da sombra é medido à parte.
SERVICE_TYPE_SOMBRA = "cerebro_sombra"
#: O evento na linha do tempo do acionamento.
EVENTO_SOMBRA = "cerebro.sombra"
VARIANTE_DA_SOMBRA = "V2"
_TTL_DA_CHAVE_S = 60.0
_TETO_DA_CHAMADA_S = 60.0
_DEDUPE_S = 7 * 24 * 3600


class ModoRecusado(ValueError):
    """O modo pedido não existe ou está recusado (o `on`)."""


def validar_modo(modo: Any) -> str:
    """`off`/`sombra` → ele mesmo. `on` (`ligado`, `ativo`) → ModoRecusado com a razão. Outro → ModoRecusado."""
    m = str(modo or "").strip().lower()
    if m in MODOS:
        return m
    if m in ("on", "ligado", "ativo"):
        raise ModoRecusado(MODO_ON_RECUSADO)
    raise ModoRecusado(f"modo desconhecido {modo!r}: os modos são {', '.join(MODOS)}")


_CACHE_DA_CHAVE: Dict[str, Tuple[float, Dict[Tuple[str, str], str]]] = {}


async def _ler_chaves(company_id: str) -> Dict[Tuple[str, str], str]:
    """{(seguradora, ramo): modo} DESTA corretora. ⛔ Filtro por `company_id` no CÓDIGO (§7)."""
    from app.services import dispatch_router as R

    db = await R._db()
    if db is None:
        return {}
    r = await (db.client.table("cerebro_modos").select("company_id,insurer_key,ramo,modo")
               .eq("company_id", str(company_id)).execute())
    out: Dict[Tuple[str, str], str] = {}
    for linha in (getattr(r, "data", None) or []):
        if str(linha.get("company_id") or "") != str(company_id):
            continue  # cinto: a borda devolveu linha de outra corretora — nunca vale para esta
        chave = (str(linha.get("insurer_key") or "").strip().lower(),
                 str(linha.get("ramo") or "todos").strip().lower())
        try:
            out[chave] = validar_modo(linha.get("modo"))
        except ModoRecusado as e:
            logger.error("[SOMBRA] chave %s/%s recusada — fica `off`: %s", chave[0], chave[1], e)
            out[chave] = "off"
    return out


async def modo_do_cerebro(company_id: str, insurer_key: str, ramo: str) -> str:
    """O modo desta corretora nesta seguradora/ramo: `off` ou `sombra`. Falha → `off` (fechada).

    Precedência: (seguradora, ramo) > (seguradora, 'todos') > `off`. Cache de 60 s por corretora.
    """
    cid = str(company_id or "").strip()
    seg = str(insurer_key or "").strip().lower()
    if not cid or not seg:
        return "off"
    agora = time.monotonic()
    em_cache = _CACHE_DA_CHAVE.get(cid)
    if em_cache is None or agora - em_cache[0] > _TTL_DA_CHAVE_S:
        try:
            chaves = await _ler_chaves(cid)
        except Exception as e:  # noqa: BLE001 — sem banco (ou sem a tabela) a sombra fica desligada
            logger.warning("[SOMBRA] chave ilegível (%s) — `off`", type(e).__name__)
            chaves = {}
        _CACHE_DA_CHAVE[cid] = (agora, chaves)
    else:
        chaves = em_cache[1]
    r = str(ramo or "").strip().lower()
    return chaves.get((seg, r)) or chaves.get((seg, "todos")) or "off"


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
    from app.services.insurer_dispatch_service import _norm_text

    dono = str((sessao or {}).get("work_run_id") or (sessao or {}).get("case_id") or "")
    base = f"{company_id}|{dono}|{' '.join(_norm_text(str(tela or '')).split())}"
    return "cerebro:sombra:%s:%s" % (company_id, hashlib.sha256(base.encode()).hexdigest()[:24])


async def _primeira_vez(chave: str) -> bool:
    """A mesma tela, no mesmo acionamento, grava UMA vez (Redis SET NX; sem Redis, memória)."""
    from app.services import dispatch_router as R

    try:
        redis = await R._redis()
        if redis is not None:
            return bool(await redis.set(chave, "1", ex=_DEDUPE_S, nx=True))
    except Exception as e:  # noqa: BLE001
        logger.warning("[SOMBRA] dedupe sem Redis (%s) — memória do processo", type(e).__name__)
    if chave in R._memory_store:
        return False
    R._memory_store[chave] = "1"
    return True


async def sombra_do_cerebro(company_id: str, sessao: Dict[str, Any], tela: str,
                            sistema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """UMA tela da fase humana pela V2, em sombra. Devolve o payload gravado, ou None.

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
    if await modo_do_cerebro(cid, seguradora, ramo) != "sombra":
        return None                                   # CONTROLE `off`: nenhuma chamada extra
    if not await _primeira_vez(_chave_de_dedupe(cid, sessao, tela)):
        return None

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.utils import extract_text_from_content
    from app.factories import llm_factory
    # ⚠️ A V2 é a MEDIDA na bancada — o composer é importado de lá, não copiado (uma variante,
    #    um texto). Pendência: mudá-lo para este módulo e a bancada importar daqui.
    from app.services.evals.bancada import mensagens_da_variante
    from app.services.intelligence.redaction_service import mascara_de_tela

    msgs = mensagens_da_variante(VARIANTE_DA_SOMBRA, sessao, tela)
    t0 = time.monotonic()
    resposta = await asyncio.wait_for(
        llm_factory.invocar_com_reserva(
            "dispatch", [SystemMessage(content=msgs["system"]), HumanMessage(content=msgs["user"])],
            company_id=cid, service_type=SERVICE_TYPE_SOMBRA),
        timeout=_TETO_DA_CHAMADA_S)
    latencia_ms = int((time.monotonic() - t0) * 1000)
    bruto = extract_text_from_content(getattr(resposta, "content", None)) or ""
    ida_e_volta = IDS.ida_e_volta_permitida(playbook)
    dec = decidir(bruto, sessao, tela, estruturada=True, ida_e_volta_permitida=ida_e_volta)
    cmp = comparar(sistema, dec, tela)
    sem_chute = dec.get("proibicao") == "passo_sem_chute"
    meta = getattr(resposta, "response_metadata", None) or {}
    payload = {
        "modo": "sombra", "variante": VARIANTE_DA_SOMBRA, "seguradora": seguradora, "ramo": ramo,
        "rota": str(sessao.get("playbook_ref") or "")[:180],
        "tela_hash": _chave_de_dedupe(cid, sessao, tela).rsplit(":", 1)[-1],
        "tela": mascara_de_tela(str(tela))[:600],
        "sistema": {"acao": str(sistema.get("acao") or ""),
                    "valor": mascara_de_tela(str(sistema.get("valor") or ""))[:300]},
        "modelo": {"acao_do_modelo": dec.get("acao_do_modelo"), "acao_final": dec.get("acao_final"),
                   "valor": mascara_de_tela(str(dec.get("valor") or ""))[:300],
                   "motivo": mascara_de_tela(str(dec.get("motivo") or ""))[:200],
                   "formato_ok": bool(dec.get("formato_ok")),
                   "erro_formato": dec.get("erro_formato") or "",
                   "proibicao": dec.get("proibicao") or "", "conferente": dec.get("conferente") or ""},
        "diverge": cmp["diverge"], "divergencia": cmp["em"],
        # 🔴 A tela de `sem_chute` NUNCA conta como acerto, nem em sombra: nela o modelo não decide.
        "sem_chute": sem_chute,
        "conta_como_acerto": (not cmp["diverge"]) and (not sem_chute) and bool(dec.get("formato_ok")),
        # O modelo tentou RESPONDER e o CÓDIGO segurou (D3 / sem_chute): é o grave do modelo NU
        # que a regra de ligar conta, mesmo quando o produto não o deixaria sair.
        "grave_segurado_pelo_codigo": (dec.get("acao_do_modelo") == "RESPONDER"
                                       and dec.get("acao_final") != "RESPONDER"
                                       and bool(dec.get("proibicao"))),
        "ida_e_volta_permitida": ida_e_volta, "latencia_ms": latencia_ms,
        "modelo_real": str(meta.get("model_name") or meta.get("model") or "")[:80],
        "service_type": SERVICE_TYPE_SOMBRA,
    }
    run_id = str(sessao.get("work_run_id") or "")
    if run_id:
        from app.services import dispatch_router as R

        db = await R._db()
        if db is not None:
            await R._evento(db, cid, run_id, EVENTO_SOMBRA,
                            ("O Cérebro V2 decidiu em SOMBRA (nada foi enviado): "
                             + ("DIVERGIU do sistema." if cmp["diverge"] else "igual ao sistema.")),
                            payload=payload, ator="agent")
    else:
        logger.warning("[SOMBRA] sem work_run: a decisão não tem onde ser gravada")
    return payload


#: As tarefas em voo (referência forte: o loop só guarda referência fraca).
_SOMBRAS: set = set()


def agendar_sombra(company_id: str, sessao: Dict[str, Any], tela: str,
                   sistema: Dict[str, Any]) -> Optional["asyncio.Task"]:
    """Agenda a sombra SEM esperar por ela — o turno de produção já decidiu e segue.

    ⛔ Nunca levanta. Sem loop rodando, não agenda (e não há o que medir).
    """
    try:
        tarefa = asyncio.get_running_loop().create_task(
            sombra_do_cerebro(company_id, sessao, tela, sistema))
    except Exception as e:  # noqa: BLE001
        logger.warning("[SOMBRA] não agendada (%s)", type(e).__name__)
        return None
    _SOMBRAS.add(tarefa)
    tarefa.add_done_callback(_SOMBRAS.discard)
    return tarefa
