# -*- coding: utf-8 -*-
"""A RÉGUA DO PÓS-ACIONAMENTO — SPEC-097.1 U4/R8.

Duas linhas, uma unidade:

    resolvido_pelo_agente   carta ∨ estado ∨ handoff PÓS com dossiê COMPLETO
    resolvido_sem_humano    carta ∨ estado

🧑 A primeira é a meta do Founder (*"entregar para o humano é um status em que
o agente não tem mais o que fazer"*). A segunda fica publicada ao lado para
que o esforço humano continue visível — 📊 e porque a taxonomia tem um TETO
aritmético: 27 dos 283 turnos com intenção do acervo são humanos por desenho,
o que dá **94,7 %** (com J contando como estado) ou **90,5 %** (sem J). Nem no
melhor caso uma régua honesta chega a 95 % pelo caminho sem humano.

🔴 **A régua chama o MOTOR** (CLAUDE.md §9.4). O classificador de turno, o mapa
de cartas e a lista de situações humanas são IMPORTADOS de
`app.atendimento.pos_acionamento` — os MESMOS objetos que o prompt do agente e
o dossiê do handoff usam (o guarda prova a identidade por `is`). Um
classificador próprio aqui mediria o classificador próprio, e não o produto.

⛔ **Sem LLM em ponto nenhum.** A cascata é regex e o mapa é um dicionário:
custo zero, resultado reproduzível.

Uso::

    cd backend
    PYTHONIOENCODING=utf-8 python scripts/regua_0971.py            # o acervo
    PYTHONIOENCODING=utf-8 python scripts/regua_0971.py --fixture  # sem banco
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app.atendimento.pos_acionamento import (  # noqa: E402
    SEM_INTENCAO,
    SITUACOES_PARA_HUMANO,
    _norm,
    classificar_turno,
    e_atendimento_de_seguro,
    mapa_de_cartas,
    vai_para_humano,
)

#: 🔴 Os rótulos que só o ESTADO ESCRITO resolve — não há carta que responda
#: *"e o meu caso?"*. ⚠️ `J` está aqui porque a SPEC precisa publicar o teto
#: **com** e **sem** ele (E8): pedir que a corretora cobre a seguradora é uma
#: pergunta que o estado responde ("já estamos cobrando desde …").
ROTULOS_DE_ESTADO = ("A", "H", "G", "J")

#: 📊 O TETO ARITMÉTICO da taxonomia medida (E8) — publicado AO LADO do número,
#: nunca no lugar dele.
TETO = {"com_J": 94.7, "sem_J": 90.5,
        "fonte": "reality-report-0971.md §2 · 283 turnos com intenção · 27 humanos por desenho"}


def _dossie_completo(turno: Any) -> bool:
    """O handoff PÓS só CONTA quando o dossiê está inteiro (R8).

    ⛔ Sem esta linha, *"foi para humano"* viraria carimbo de resolvido: bastaria
    o agente desistir para a régua subir (CLAUDE.md §9.5).
    """
    dossie = (turno or {}).get("dossie") or {}
    if not isinstance(dossie, dict):
        return False
    return bool(str(dossie.get("o_que_fazer") or "").strip()
                and str(dossie.get("onde_parou") or "").strip())


def _conversas_descartadas(turnos: Iterable[Dict[str, Any]]) -> set:
    """R11 — a conversa inteira é o que se aceita ou se descarta, não o turno.

    ⚠️ **A unidade aqui é a CONVERSA de propósito.** 📊 56,3 % das mensagens
    têm ≤ 24 caracteres: julgar `"Ta!"` isoladamente descartaria o fio inteiro
    do segurado parado no acostamento. Quem carrega o vocabulário é a conversa.
    """
    por_conversa: Dict[str, List[str]] = {}
    for turno in turnos:
        chave = str((turno or {}).get("conversa") or (turno or {}).get("conversation_id") or "")
        por_conversa.setdefault(chave, [])
        por_conversa[chave].extend(str(m or "") for m in (turno.get("mensagens") or []))
    return {chave for chave, msgs in por_conversa.items()
            if not e_atendimento_de_seguro({"mensagens": msgs})}


def medir(turnos: Iterable[Dict[str, Any]], mapa: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """As duas réguas sobre uma lista de turnos. **PURA — sem banco e sem LLM.**

    `mapa=None` usa o mapa do módulo; `mapa={}` é a LINHA DE CONTROLE, e é ela
    que dá direito à conclusão: se o número não cair sem as cartas, as cartas
    não eram a causa (CLAUDE.md §9.2).
    """
    if mapa is None:
        mapa = mapa_de_cartas()
    lista = [t for t in (turnos or []) if isinstance(t, dict) and t.get("mensagens") is not None]
    descartadas = _conversas_descartadas(lista)

    r = {"denominador": 0, "descartados": 0, "resolvido_por_carta": 0,
         "estado_REAL": 0, "estado_SIMULADO": 0, "handoff_pos": 0,
         "resolvido_sem_humano": 0, "resolvido_pelo_agente": 0,
         "para_humano": 0, "para_humano_sem_dossie": 0,
         "por_rotulo": {}, "teto": TETO}

    agente_simulado = 0
    for turno in lista:
        chave = str(turno.get("conversa") or turno.get("conversation_id") or "")
        if chave in descartadas:
            # ⛔ R11: nunca vira carta, nunca entra no denominador — e é CONTADO.
            r["descartados"] += 1
            continue

        rotulo = classificar_turno(turno.get("mensagens") or [])
        r["por_rotulo"][rotulo] = int(r["por_rotulo"].get(rotulo) or 0) + 1
        if rotulo in SEM_INTENCAO:
            continue
        r["denominador"] += 1

        humano_por_desenho = vai_para_humano(rotulo)
        # ⚠️ Uma carta NÃO resolve o que é humano por desenho. C6 existe para o
        #    prestador que não chegou — mas ela é o que o agente DIZ enquanto
        #    passa o caso, não um substituto da pessoa (R9).
        carta = None if humano_por_desenho else mapa.get(rotulo)

        estado_simulado = rotulo in ROTULOS_DE_ESTADO
        estado_real = bool(estado_simulado and turno.get("espera_ativa"))
        if carta:
            r["resolvido_por_carta"] += 1
        if estado_real:
            r["estado_REAL"] += 1
        if estado_simulado:
            r["estado_SIMULADO"] += 1

        sem_humano = bool(carta) or estado_real
        sem_humano_sim = bool(carta) or estado_simulado
        if sem_humano:
            r["resolvido_sem_humano"] += 1

        handoff = humano_por_desenho and _dossie_completo(turno)
        if handoff and not sem_humano:
            r["handoff_pos"] += 1
        if sem_humano or handoff:
            r["resolvido_pelo_agente"] += 1
        elif humano_por_desenho:
            r["para_humano_sem_dossie"] += 1
        if sem_humano_sim or handoff:
            agente_simulado += 1

    r["para_humano"] = r["denominador"] - r["resolvido_pelo_agente"]
    base = r["denominador"] or 1
    r["pct_real"] = round(100.0 * r["resolvido_pelo_agente"] / base, 1)
    r["pct_simulado"] = round(100.0 * agente_simulado / base, 1)
    r["pct_sem_humano"] = round(100.0 * r["resolvido_sem_humano"] / base, 1)
    return r


# ===========================================================================
# O ACERVO — só SELECT, zero PII na saída
#
# 📊 A regra de reconhecimento do acionamento é a do `reality-report-0971.md`
# §0.4, e ela foi medida em **Postgres**. ⚠️ CLAUDE.md §9.4: um padrão medido
# com um motor e aplicado com outro é um padrão sobre outra coisa — por isso
# aqui a normalização é a MESMA (`_norm`: minúsculas + acentos removidos, o
# `translate` do SQL) e todo `.` roda com `re.S`, porque no Postgres o ponto
# casa `\n` e em Python NÃO casa.
# ===========================================================================

TENANTS = (
    ("Resulta Seguros", "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab", r"^\+?55?48"),
    ("AutoFleet", "6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a", None),
)

_T0 = re.compile(
    r"protocolo[^a-z0-9]{0,12}[a-z]?[0-9]{5,}"
    r"|segue o protocolo|protocolo:|aqui esta seu protocolo"
    r"|foi acionad|acionamos|acionei o|abrimos o (sinistro|atendimento|chamado)"
    r"|sinistro (foi )?(aberto|registrado)"
    r"|agendamento confirmado|atendimento foi agendado|servico (foi )?agendado"
    r"|previsao de ate [0-9]+ *(min|hora)|estamos buscando um prestador"
    r"|prestador (ja )?(esta|foi) (a caminho|em deslocamento|designado)"
    r"|aguarde a chegada do prestador", re.S)


def _turnos_da_conversa(mensagens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """R1 — a rajada do cliente sem resposta no meio vira UM turno."""
    t0 = None
    for m in mensagens:
        if str(m.get("role")) == "assistant" and _T0.search(_norm(m.get("content"))):
            t0 = str(m.get("created_at") or "")
            break
    if t0 is None:
        return []
    turnos: List[Dict[str, Any]] = []
    rajada: List[str] = []
    for m in mensagens:
        if str(m.get("created_at") or "") <= t0:
            continue
        if str(m.get("role")) == "user":
            rajada.append(str(m.get("content") or ""))
        elif rajada:
            turnos.append({"mensagens": list(rajada)})
            rajada = []
    if rajada:
        turnos.append({"mensagens": list(rajada)})
    return turnos


def _ler_acervo() -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    cliente = get_supabase_client().client
    turnos: List[Dict[str, Any]] = []
    for nome, empresa, filtro_fone in TENANTS:
        conversas = (cliente.table("conversations")
                     .select("id, company_id, user_phone")
                     .eq("company_id", empresa).limit(2000).execute().data or [])
        if filtro_fone:
            padrao = re.compile(filtro_fone)
            conversas = [c for c in conversas
                         if padrao.search(str(c.get("user_phone") or ""))]
        for conversa in conversas:
            msgs = (cliente.table("messages")
                    .select("role, content, created_at")
                    .eq("conversation_id", conversa["id"])
                    .order("created_at").limit(1000).execute().data or [])
            for i, turno in enumerate(_turnos_da_conversa(msgs)):
                turno["conversa"] = "%s:%s" % (nome[:3].lower(), conversa["id"])
                # ⛔ `espera_ativa` é FALSO no acervo inteiro, e é um FATO:
                #    📊 `work_waits` tem zero linhas na vida (E10). A régua diz
                #    isso em voz alta em vez de simular estado que não houve.
                turno["espera_ativa"] = False
                turnos.append(turno)
    return turnos


def _imprimir(rotulo: str, r: Dict[str, Any]) -> None:
    print("")
    print("  %s" % rotulo)
    print("  " + "-" * 68)
    print("  denominador (turnos com intenção) ....... %5d" % r["denominador"])
    print("  descartados por R11 (pessoal/colega) .... %5d" % r["descartados"])
    print("  resolvido_por_carta ..................... %5d" % r["resolvido_por_carta"])
    print("  estado_REAL   (espera escrita) .......... %5d   📊 hoje ZERO no acervo (E10)"
          % r["estado_REAL"])
    print("  estado_SIMULADO (💭 se a U1 já rodasse) .. %5d" % r["estado_SIMULADO"])
    print("  handoff PÓS com dossiê completo ......... %5d" % r["handoff_pos"])
    print("  para_humano_sem_dossie .................. %5d" % r["para_humano_sem_dossie"])
    print("  para_humano (o que sobra) ............... %5d" % r["para_humano"])
    print("  " + "-" * 68)
    print("  resolvido_pelo_agente ................... %5d   %5.1f %%"
          % (r["resolvido_pelo_agente"], r["pct_real"]))
    print("  resolvido_sem_humano .................... %5d   %5.1f %%"
          % (r["resolvido_sem_humano"], r["pct_sem_humano"]))
    print("  💭 com estado SIMULADO .................. %s   %5.1f %%"
          % ("     ", r["pct_simulado"]))
    print("  📊 teto de desenho: %.1f %% (com J) · %.1f %% (sem J) — %s"
          % (r["teto"]["com_J"], r["teto"]["sem_J"], r["teto"]["fonte"]))


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    print("=" * 72)
    print("  A RÉGUA DO PÓS-ACIONAMENTO — SPEC-097.1 U4/R8")
    print("=" * 72)

    if "--fixture" in argv:
        caminho = os.path.join(RAIZ, "tests", "fixtures", "turnos_0971.json")
        bruto = json.load(io.open(caminho, encoding="utf-8"))
        turnos = [t for t in bruto if isinstance(t, dict) and "turno" in t]
        origem = "FIXTURE 💭 sintética (%s)" % os.path.basename(caminho)
    else:
        try:
            turnos = _ler_acervo()
            origem = "📊 ACERVO REAL (Resulta/DDD-48 + AutoFleet), só SELECT"
        except Exception as erro:  # noqa: BLE001
            print("\n  ⛔ o acervo não pôde ser lido: %s: %s"
                  % (type(erro).__name__, erro))
            print("     (rode com `--fixture` para medir sem banco)")
            return 2

    print("\n  origem: %s" % origem)
    print("  turnos reconstruídos: %d" % len(turnos))
    _imprimir("COM AS CARTAS", medir(turnos))
    _imprimir("🔴 CONTROLE — a MESMA passada com o mapa de cartas VAZIO",
              medir(turnos, mapa={}))
    print("\n  ⚠️ O controle é o que dá direito à conclusão: se o número não cai")
    print("     sem as cartas, não foram elas que resolveram (CLAUDE.md §9.2).")
    print("  ⛔ Zero PII: esta saída só tem CONTAGENS.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
