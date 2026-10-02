# -*- coding: utf-8 -*-
"""SPEC-126 U3 · D2 — o MESMO celular pedindo dado/acionamento de muitas apólices.

    D2 (Founder, 02/10/2026): o mesmo celular pedindo acionamento ou informação de
    MAIS DE 2 apólices diferentes em 5 dias → aviso ao grupo de suporte DA corretora
    (possível fraude/roubo de dados), SEM bloquear o atendimento em curso. Por
    `company_id`; nada atravessa corretora.

O RASTRO NÃO É TABELA NOVA (CLAUDE.md §5 — consolidar antes de criar; decisão do
gerente, nota 78). O gravador ÚNICO de chamada de ferramenta já existe:
`nodes._abrir_registro_de_invocacao` → `invocation_recorder.RegistroDeInvocacao` →
`tool_invocations` (`company_id`, `trace_id = "<sessão>|<turno>"`, `created_at`).
A sessão do WhatsApp é `whatsapp:<telefone>:<empresa>:<agente>` (`webhook.py`), então
o TELEFONE já está no rastro. O que faltava era a identidade da APÓLICE: a ferramenta
que consulta devolve `rastro_da_consulta` (pseudônimos HMAC, nunca o número cru) e o
recorder o copia para `output_summary` pela lista fechada de `rastro_seguro`.

📊 Índice que a contagem usa, já existente (02/10/2026,
`select indexdef from pg_indexes where tablename='tool_invocations'`):
`ix_tool_invocations_company_recente (company_id, created_at DESC)` — sem migration.

⛔ Nada aqui bloqueia o atendimento e nada aqui levanta: a contagem e o aviso são
best-effort; quem chama segue o turno com ou sem eles.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

#: constante_justificada: D2 do Founder (SPEC-126 §3, 02/10/2026) — "mais de 2 apólices
#: diferentes". Até 2 é o segurado com auto + casa (ou o parente que aciona UMA vez); a 3ª
#: distinta é o sinal. ⚠️ As do PRÓPRIO titular contam como UMA (D-126-C, nota 88).
LIMITE_DE_APOLICES = 2
#: constante_justificada: D2 do Founder — "em 5 dias". É também a janela da idempotência:
#: o mesmo telefone não gera um segundo aviso enquanto a janela que o disparou vale.
JANELA_DIAS = 5
#: constante_justificada: o teto de linhas lidas por (corretora, telefone) na janela. 💭 Um
#: telefone legítimo faz poucas consultas em 5 dias; passar disto já é, por si, o sinal.
TETO_DE_LINHAS = 500

#: o tipo do aviso na porta única do grupo (`o_grupo_so_o_que_importa.enviar_ao_grupo`).
TIPO_DO_AVISO = "consultas_por_telefone"
#: a chave que a ferramenta devolve e que o recorder copia para `output_summary`.
CHAVE_DO_RASTRO = "rastro_da_consulta"

_HEX24 = re.compile(r"^[0-9a-f]{24}$")
_FINAL = re.compile(r"^\d{1,4}$")
_CAMPOS_DO_RASTRO = ("apolice_hash", "titular_hash", "titular_proprio", "apolice_final")


# --------------------------------------------------------------------------- #
# O pseudônimo — a chave de servidor que o produto JÁ usa para PII
# --------------------------------------------------------------------------- #
def _pseudonimo(company_id: str, tipo: str, valor: str) -> str:
    """HMAC-SHA256 (`policy_context._pseudonimo`, a chave POLICY_CONTEXT_HMAC_KEY/
    ENCRYPTION_KEY), truncado em 24. ⛔ Nunca sha puro: 11 dígitos de CPF são força bruta
    trivial. O `company_id` entra no material: a MESMA apólice tem pseudônimos diferentes
    em duas corretoras (o rastro de uma nunca casa com o da outra)."""
    from app.services.policy_context import _pseudonimo as hmac_do_produto

    return hmac_do_produto("consulta:%s:%s:%s" % (company_id, tipo, valor))


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def rastro_da_apolice(company_id: Any, *, documento: Any = None, numero_apolice: Any = None,
                      proprio: bool = False) -> Optional[Dict[str, Any]]:
    """O rastro de UMA consulta/acionamento: só pseudônimos e o FINAL da apólice. **PURA**
    (salvo a chave do HMAC). `None` sem corretora ou sem nada que identifique a apólice."""
    empresa = str(company_id or "").strip()
    doc = _digitos(documento)
    numero = re.sub(r"[^0-9A-Za-z]", "", str(numero_apolice or "")).upper()
    if not empresa or not (numero or len(doc) in (11, 14)):
        return None
    rastro = {
        "apolice_hash": _pseudonimo(empresa, "apolice", numero) if numero else None,
        "titular_hash": _pseudonimo(empresa, "titular", doc) if len(doc) in (11, 14) else None,
        "titular_proprio": bool(proprio),
        "apolice_final": _digitos(numero)[-4:] if numero else "",
    }
    return rastro_seguro(rastro)


def rastro_seguro(valor: Any) -> Optional[Dict[str, Any]]:
    """A LISTA FECHADA do que pode ir a `tool_invocations.output_summary`. **PURA.**

    ⛔ Cada campo tem FORMA conferida: hash = 24 hex, final = até 4 dígitos, o resto
    booleano. Um CPF cru (11 dígitos) não tem a forma de nenhum deles — e não passa.
    """
    if not isinstance(valor, dict):
        return None
    saida: Dict[str, Any] = {}
    for chave in ("apolice_hash", "titular_hash"):
        v = valor.get(chave)
        if isinstance(v, str) and _HEX24.match(v):
            saida[chave] = v
    if not saida:
        return None
    saida["titular_proprio"] = valor.get("titular_proprio") is True
    final = valor.get("apolice_final")
    saida["apolice_final"] = final if isinstance(final, str) and _FINAL.match(final) else ""
    return saida


def unidade(rastro: Dict[str, Any]) -> Optional[str]:
    """O que conta como UMA apólice. **PURA.**

    D-126-C (nota 88): as apólices do PRÓPRIO titular que fala — o documento dito como
    dele e não desmentido — contam como UMA, pelo titular. As outras, pela apólice; sem
    número de apólice, pelo titular."""
    if not isinstance(rastro, dict):
        return None
    if rastro.get("titular_proprio") and rastro.get("titular_hash"):
        return "t:" + rastro["titular_hash"]
    if rastro.get("apolice_hash"):
        return "a:" + rastro["apolice_hash"]
    if rastro.get("titular_hash"):
        return "t:" + rastro["titular_hash"]
    return None


def telefone_da_sessao(session_id: Any) -> str:
    """O telefone de `whatsapp:{telefone}:{empresa}:{agente}` (`webhook.py`). **PURA.**
    `""` fora do WhatsApp — e sem telefone não há contagem."""
    partes = str(session_id or "").split(":")
    if len(partes) >= 3 and partes[0] == "whatsapp":
        return _digitos(partes[1])
    return ""


# --------------------------------------------------------------------------- #
# A decisão — PURA
# --------------------------------------------------------------------------- #
def decidir(anteriores: Iterable[Dict[str, Any]], atual: Optional[Dict[str, Any]],
            *, limite: int = LIMITE_DE_APOLICES) -> Dict[str, Any]:
    """`{"avisar", "distintas", "linhas"}` — **PURA**.

    `anteriores`: `[{"rastro", "quando"}]` desta corretora e deste telefone, na janela.
    `linhas`: uma por unidade distinta, a mais recente de cada (para o texto do aviso).
    Avisa quando as distintas passam do `limite` — e só se a ATUAL estiver entre elas (a
    consulta que não traz apólice não dispara nada)."""
    todos = [{"rastro": rastro_seguro((i or {}).get("rastro")), "quando": (i or {}).get("quando")}
             for i in list(anteriores or []) + ([{"rastro": atual, "quando": None}] if atual else [])]
    todos = [i for i in todos if i["rastro"]]
    # ⚠️ O MESMO titular/apólice pode aparecer como "próprio" numa linha (a consulta com "meu
    #    cpf") e sem a marca noutra (o acionamento, que não sabe disso): os dois são a MESMA
    #    unidade do titular — senão o segurado se somaria a si mesmo.
    titulares_proprios = {i["rastro"].get("titular_hash") for i in todos
                          if i["rastro"].get("titular_proprio") and i["rastro"].get("titular_hash")}
    apolices_proprias = {i["rastro"].get("apolice_hash"): i["rastro"].get("titular_hash") for i in todos
                         if i["rastro"].get("titular_proprio") and i["rastro"].get("apolice_hash")}

    def _unidade(r: Dict[str, Any]) -> Optional[str]:
        th, ah = r.get("titular_hash"), r.get("apolice_hash")
        if th and th in titulares_proprios:
            return "t:" + th
        if ah and ah in apolices_proprias and apolices_proprias[ah]:
            return "t:" + apolices_proprias[ah]
        return unidade(r)

    por_unidade: Dict[str, Dict[str, Any]] = {}
    for item in todos:
        rastro = item["rastro"]
        chave = _unidade(rastro)
        if not chave:
            continue
        if chave[2:] in titulares_proprios:
            rastro = {**rastro, "titular_proprio": True}
        quando = (item or {}).get("quando")
        guardado = por_unidade.get(chave)
        if guardado is None or (quando and str(quando) > str(guardado.get("quando") or "")):
            por_unidade[chave] = {"rastro": rastro, "quando": quando or (guardado or {}).get("quando")}
    unidade_atual = _unidade(rastro_seguro(atual) or {}) if rastro_seguro(atual) else None
    distintas = len(por_unidade)
    return {"avisar": bool(unidade_atual) and distintas > int(limite),
            "distintas": distintas,
            "linhas": sorted(por_unidade.values(), key=lambda x: str(x.get("quando") or "9"),
                             reverse=True)}


# --------------------------------------------------------------------------- #
# A leitura — por corretora E telefone (CLAUDE.md §7)
# --------------------------------------------------------------------------- #
async def consultas_recentes(db, *, company_id: str, telefone: str,
                             agora: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """`[{"rastro", "quando"}]` deste telefone NESTA corretora, nos últimos `JANELA_DIAS`.

    🔴 Duas travas de tenant: o filtro `company_id` no banco E o cinto em Python (o
    backend usa service role — RLS não protege de filtro esquecido). Nunca levanta."""
    empresa = str(company_id or "").strip()
    fone = _digitos(telefone)
    if not empresa or not fone:
        return []
    desde = ((agora or datetime.now(timezone.utc)) - timedelta(days=JANELA_DIAS)).isoformat()
    prefixo = "whatsapp:%s:" % fone
    try:
        from app.services.o_fim_do_atendimento import _cliente, _executar

        achado = await _executar(_cliente(db).table("tool_invocations")
                                 .select("company_id, trace_id, output_summary, created_at")
                                 .eq("company_id", empresa)             # 🔴 CLAUDE.md §7
                                 .like("trace_id", prefixo + "%")
                                 .gte("created_at", desde)
                                 .order("created_at", desc=True)
                                 .limit(TETO_DE_LINHAS))
        linhas = getattr(achado, "data", None) or []
    except Exception as exc:  # noqa: BLE001 — sem leitura, sem aviso; o turno segue
        logger.warning("[CONSULTAS] rastro ilegível (%s)", type(exc).__name__)
        return []
    saida = []
    for linha in linhas:
        if not isinstance(linha, dict):
            continue
        if str(linha.get("company_id") or "") != empresa:      # 🔴 o cinto
            continue
        if not str(linha.get("trace_id") or "").startswith(prefixo):
            continue
        if str(linha.get("created_at") or "") < desde:
            continue
        rastro = rastro_seguro((linha.get("output_summary") or {}).get(CHAVE_DO_RASTRO)
                               if isinstance(linha.get("output_summary"), dict) else None)
        if rastro:
            saida.append({"rastro": rastro, "quando": linha.get("created_at")})
    return saida


# --------------------------------------------------------------------------- #
# O aviso — pela PORTA ÚNICA do grupo
# --------------------------------------------------------------------------- #
def _fuso():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/Sao_Paulo")
    except Exception:  # noqa: BLE001 — sem tzdata, o horário de Brasília fixo
        return timezone(timedelta(hours=-3))


def _hora(quando: Any, agora: datetime) -> str:
    try:
        t = datetime.fromisoformat(str(quando).replace("Z", "+00:00")) if quando else agora
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t.astimezone(_fuso()).strftime("%d/%m %H:%M")
    except Exception:  # noqa: BLE001
        return "?"


def _fone_legivel(telefone: str) -> str:
    try:
        from app.agents.tools.human_handoff import _fone_bonito

        return _fone_bonito(telefone)
    except Exception:  # noqa: BLE001
        return str(telefone or "")


def texto_do_aviso(telefone: str, linhas: List[Dict[str, Any]],
                   agora: Optional[datetime] = None) -> str:
    """O aviso, em português de gente. ⛔ Apólice só pelo FINAL; nenhum CPF; nenhum nome.

    O telefone vai INTEIRO e legível — é o mesmo que o dossiê do atendimento já mostra
    à equipe (`human_handoff._fone_bonito`): o grupo é da corretora dona e precisa ligar."""
    momento = agora or datetime.now(timezone.utc)
    corpo = []
    for item in linhas:
        r = item.get("rastro") or {}
        if r.get("titular_proprio"):
            o_que = "apólices do próprio titular"
        elif r.get("apolice_final"):
            o_que = "apólice final %s" % r["apolice_final"]
        else:
            o_que = "apólice sem número informado"
        corpo.append("  · %s — %s" % (o_que, _hora(item.get("quando"), momento)))
    return "\n".join([
        "⚠️ Atenção: muitas apólices no mesmo número",
        "━━━━━━━━━━",
        "O número %s pediu dados ou acionamento de %d apólices diferentes nos últimos %d dias:"
        % (_fone_legivel(telefone), len(linhas), JANELA_DIAS),
        *corpo,
        "O atendimento NÃO foi bloqueado. Vale alguém da equipe conferir se é mesmo o segurado "
        "(ou alguém da família dele) — pode ser uso indevido de dados.",
    ])


async def conferir_e_avisar(db, *, company_id: Any, session_id: Any,
                            rastro: Optional[Dict[str, Any]],
                            agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Conta e, se for a vez, avisa UMA vez o grupo DA corretora. **Nunca levanta.**

    `{"avisou", "distintas", "motivo"}`. ⛔ Não bloqueia: o chamador segue o turno."""
    resposta = {"avisou": False, "distintas": 0, "motivo": ""}
    try:
        empresa = str(company_id or "").strip()
        fone = telefone_da_sessao(session_id)
        if not empresa or not fone or not rastro_seguro(rastro):
            resposta["motivo"] = "sem corretora, telefone ou apólice"
            return resposta
        momento = agora or datetime.now(timezone.utc)
        anteriores = await consultas_recentes(db, company_id=empresa, telefone=fone, agora=momento)
        decisao = decidir(anteriores, rastro)
        resposta["distintas"] = decisao["distintas"]
        if not decisao["avisar"]:
            resposta["motivo"] = "abaixo do limite"
            return resposta

        from app.services import o_grupo_so_o_que_importa as G

        # 🔴 IDEMPOTÊNCIA: o marcador da porta, por (corretora, telefone pseudônimo, tipo),
        #    vale a janela inteira. ⚠️ A "conversa" do marcador é o telefone pseudônimo —
        #    nunca vazia (vazia seria uma chave global, CLAUDE.md §7).
        marca = "telefone:" + _pseudonimo(empresa, "telefone", fone)
        if await G.reivindicar_o_envio(empresa, marca, TIPO_DO_AVISO, JANELA_DIAS * 86400):
            resposta["motivo"] = "já avisado nesta janela"
            return resposta
        enviado = await G.enviar_ao_grupo(
            db, company_id=empresa, tipo=TIPO_DO_AVISO,
            texto=texto_do_aviso(fone, decisao["linhas"], momento),
            telefone=fone, dedup=False,
            resumo="%d apólices distintas em %d dias" % (decisao["distintas"], JANELA_DIAS),
            motivo="consultas_por_telefone", motivo_classe="regra")
        resposta["avisou"] = bool((enviado or {}).get("enviado"))
        resposta["motivo"] = str((enviado or {}).get("motivo") or "")
        if not resposta["avisou"]:
            await G.devolver_a_vez_do_grupo(empresa, marca, TIPO_DO_AVISO)
        return resposta
    except Exception as exc:  # noqa: BLE001 — o aviso nunca derruba o turno
        logger.warning("[CONSULTAS] aviso não conferido (%s)", type(exc).__name__)
        resposta["motivo"] = "falha (%s)" % type(exc).__name__
        return resposta
