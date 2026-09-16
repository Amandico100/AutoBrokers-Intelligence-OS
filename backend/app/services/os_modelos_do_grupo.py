"""BLOCO D — os quatro modelos, e a conta das 19h.

O grupo da corretora recebe **quatro coisas e mais nada**:

```
🆘 PRECISO DE AJUDA          o agente pediu humano   (`human_handoff._montar_dossie`)
🚨 NOVO SINISTRO             notícia de negócio      (aqui)
✅ ATENDIMENTO CONCLUÍDO     o fechamento, curto     (aqui)
📊 ATENDIMENTOS REALIZADOS   uma vez por dia, 19h    (aqui)
```

💭 **A copy é ilustrativa** (CLAUDE.md §12.1). O que **não** é ilustrativo:
quais campos existem, quais **não** existem, e a ordem.

🔴 **E o resumo é onde o que foi CALADO reaparece.** Toda mensagem que a guarda
suprimiu vira contagem aqui — as linhas 🤝, 🔕 e ⏱️ existem exatamente para
isso. Nada é perdido; é **adiado** para uma linha (CLAUDE.md §11.1: *deixar
pronto e desligado é aceitável; deixar pronto e não anotado, não*).

⛔ **Nenhuma tabela de métrica nova e nenhum recontar do zero sobre
`messages`**: a fonte é `work_events` do dia, por corretora, pelos tipos que os
BLOCOS A–E gravam.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_TRACO = "─" * 20


# ===========================================================================
# §8.5 — O FORMATO DO LINK, e ele tem guarda próprio
# ===========================================================================
def link_do_whatsapp(telefone: Any) -> str:
    """`https://wa.me/55DDDNÚMERO` — ⛔ sem `+`, sem espaço, sem parêntese.

    🔴 Regras que o guarda G-D1 congela:

    ```
    já vem com 55        → não duplica
    vem com 10 dígitos   → sai assim mesmo. ⛔ NÃO se inventa o nono dígito
    vem vazio / lixo     → devolve "" (e o modelo omite a linha)
    ```

    ⚠️ `_fone_bonito` (`human_handoff.py:463`) continua existindo para o texto
    LEGÍVEL. O link é outra coisa, e os dois convivem no mesmo modelo.
    """
    digitos = re.sub(r"\D", "", str(telefone or ""))
    if not digitos:
        return ""
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    # 55 + DDD(2) + 8 = 12 é o piso; acima de 13 já não é telefone brasileiro.
    if len(digitos) < 12 or len(digitos) > 13:
        return ""
    return "https://wa.me/%s" % digitos


def _linha(rotulo: str, valor: Any) -> Optional[str]:
    texto = str(valor or "").strip()
    return ("*%s:* %s" % (rotulo, texto)) if texto else None


def _juntar(linhas) -> str:
    return "\n".join([l for l in linhas if l is not None])


# ===========================================================================
# §8.2 — 🚨 NOVO SINISTRO
# ===========================================================================
def modelo_novo_sinistro(*, tipo: str = "", segurado: str = "", documento: str = "",
                         apolice: str = "", quando: str = "", resumo: str = "",
                         pontos_de_atencao=(), telefone: Any = "") -> str:
    """✅ Passa pela guarda **sempre** (§5.3): sinistro é notícia de negócio.

    ⚠️ *Pontos de atenção* é o lugar RESERVADO para o checklist por tipo da
    P-PILOTO-04 (colisão, roubo, incêndio, empresarial, condomínio). Esta SPEC
    entrega **o lugar e o mecanismo**; o conteúdo por tipo vem com a base de
    produtos (EXTRA-001.5). 🔴 Enquanto não vier, o campo é preenchido com o
    que a ficha sabe que **falta**, e diz que é isso. ⛔ Não inventar checklist
    clínico sem fonte.
    """
    pessoa = " · ".join([p for p in (str(segurado or "").strip(),
                                     str(documento or "").strip()) if p])
    linhas = [
        "🚨 *NOVO SINISTRO*", _TRACO,
        _linha("Tipo", tipo),
        _linha("Segurado", pessoa),
        _linha("Apólice", apolice),
        _linha("Quando", quando),
    ]
    if str(resumo or "").strip():
        linhas += ["", "*Resumo:* %s" % str(resumo).strip()]
    pontos = [str(p).strip() for p in (pontos_de_atencao or ()) if str(p).strip()]
    if pontos:
        linhas += ["", "*⚠️ Pontos de atenção:*"] + ["• %s" % p for p in pontos]
    wa = link_do_whatsapp(telefone)
    if wa:
        linhas += ["", "*WhatsApp do segurado:* %s" % wa]
    return _juntar(linhas)


# ===========================================================================
# §8.3 — ✅ ATENDIMENTO CONCLUÍDO
# ===========================================================================
def modelo_atendimento_concluido(*, segurado: str = "", servico: str = "",
                                 protocolo: str = "", minutos: Optional[int] = None,
                                 de: str = "", ate: str = "",
                                 por_humano: str = "") -> str:
    """**Curto. Uma mensagem que ninguém precisa abrir.**

    🔴 A atendente aparece pelo NOME; o agente assina 🤖 (D-PILOTO-12, item 5).

    ⛔ Dúvida respondida **não manda nada**: vira número no resumo. Senão o
    modelo ✅ vira o novo ruído — que é o que esta SPEC existe para matar.
    """
    cabeca = " · ".join([p for p in (str(segurado or "").strip(),
                                     str(servico or "").strip()) if p])
    if str(protocolo or "").strip():
        cabeca = (cabeca + " · protocolo %s" % str(protocolo).strip()).strip(" ·")

    quanto = ""
    if minutos is not None and int(minutos) >= 0:
        m = int(minutos)
        quanto = ("%d min" % m) if m < 60 else ("%dh%02d" % (m // 60, m % 60))
    janela = ""
    if de and ate:
        janela = ", das %s às %s" % (de, ate)

    quem = str(por_humano or "").strip()
    if quem:
        corpo = "Resolvido pel%s %s%s%s." % (
            "a" if not quem.lower().startswith(("o ",)) else "o", quem,
            (" em " + quanto) if quanto else "", janela)
        assinatura = ""
    else:
        corpo = "Resolvido%s%s." % ((" em " + quanto) if quanto else "", janela)
        assinatura = " 🤖 agente"

    return _juntar(["✅ *ATENDIMENTO CONCLUÍDO*",
                    cabeca or None,
                    (corpo + assinatura).strip()])


# ===========================================================================
# §8.4 — 📊 ATENDIMENTOS REALIZADOS, às 19h
# ===========================================================================
CLASSE_INCAPACIDADE = "incapacidade"
CLASSE_REGRA = "regra"
CLASSE_DESCONHECIDA = "desconhecido"

#: 🔴 Acima desta fatia de `desconhecido` o resumo NÃO publica a eficiência.
#: ⛔ Um número calculado sobre a minoria classificada é pior que número
#: nenhum, porque PARECE medição.
#:
#: 📊 O limite saiu da medição do BLOCO 0, não de palpite: em 16/09/2026
#: `human_handoff_reason` estava preenchido em **2 de 254** conversas
#: `HUMAN_REQUESTED` e `grep -rn "motivo_classe" backend/app` dava **0**. Com
#: o escritor nascendo nesta SPEC, o acervo do primeiro dia é quase todo
#: `desconhecido` — e o resumo tem de DIZER isso em vez de inventar 100%.
LIMITE_DE_DESCONHECIDOS = 0.30


def eficiencia_do_dia(*, acionamentos_entregues: int, sinistros_com_dossie: int,
                      ajudas_por_incapacidade: int) -> Optional[int]:
    """A fórmula, exatamente como D-PILOTO-13 a fixou — **PURA**.

    ```
                  acionamentos com mensagem enviada ao segurado + sinistros com dossiê
    eficiência = ────────────────────────────────────────────────────────────────────
                  os mesmos + ajudas cujo motivo_classe = 'incapacidade'
    ```

    🔴 Devolve `None` quando o denominador é ZERO. ⚠️ **Denominador zero não é
    0%, é "sem acionamentos hoje"** — um dia só de dúvidas não tem eficiência;
    tem 12 dúvidas.

    ⛔ *Ajuda por regra* fica FORA do denominador, porque contar contra puniria
    o agente por obedecer. E *ajuda sem motivo classificado* fica fora **dos
    dois**, com linha própria (§8.1).
    """
    numerador = int(acionamentos_entregues or 0) + int(sinistros_com_dossie or 0)
    denominador = numerador + int(ajudas_por_incapacidade or 0)
    if denominador <= 0:
        return None
    return int(round(100.0 * numerador / denominador))


def _plural(n: int, um: str, muitos: str) -> str:
    return um if int(n) == 1 else muitos


def modelo_resumo_do_dia(dia: str, c: Dict[str, int]) -> str:
    """O resumo das 19h a partir das CONTAGENS já apuradas — **PURO**.

    ⛔ Dia sem movimento devolve `""`: dia sem nada não manda mensagem dizendo
    que não houve nada.
    """
    movimento = sum(int(c.get(k) or 0) for k in (
        "acionamentos_entregues", "sinistros_com_dossie", "ajudas_incapacidade",
        "ajudas_regra", "ajudas_desconhecidas", "duvidas", "ja_com_a_equipe",
        "calados_pela_janela", "vigia_ura", "vigia_prazo"))
    if movimento <= 0:
        return ""

    ajudas_totais = (int(c.get("ajudas_incapacidade") or 0)
                     + int(c.get("ajudas_regra") or 0)
                     + int(c.get("ajudas_desconhecidas") or 0))
    fatia = (int(c.get("ajudas_desconhecidas") or 0) / ajudas_totais) if ajudas_totais else 0.0

    linhas = ["📊 *ATENDIMENTOS REALIZADOS — %s*" % dia, _TRACO]

    ef = eficiencia_do_dia(
        acionamentos_entregues=int(c.get("acionamentos_entregues") or 0),
        sinistros_com_dossie=int(c.get("sinistros_com_dossie") or 0),
        ajudas_por_incapacidade=int(c.get("ajudas_incapacidade") or 0))
    if ef is None:
        # ⚠️ "sem acionamentos hoje" — e NÃO 0%.
        linhas.append("*Sem acionamentos hoje.*")
    elif fatia > LIMITE_DE_DESCONHECIDOS:
        # 🔴 Acima do limite o número NÃO é publicado.
        linhas.append("*Ainda não dá para medir:* %d de %d %s de ajuda saíram sem "
                      "motivo registrado." % (
                          int(c.get("ajudas_desconhecidas") or 0), ajudas_totais,
                          _plural(ajudas_totais, "pedido", "pedidos")))
    else:
        base = (int(c.get("acionamentos_entregues") or 0)
                + int(c.get("sinistros_com_dossie") or 0))
        linhas.append("*Eficiência: %d%%*  (%d de %d)" % (
            ef, base, base + int(c.get("ajudas_incapacidade") or 0)))

    linhas.append("")
    if c.get("acionamentos_entregues"):
        n = int(c["acionamentos_entregues"])
        linhas.append("✅ %d %s com a mensagem enviada ao segurado" % (
            n, _plural(n, "acionamento", "acionamentos")))
    if c.get("sinistros_com_dossie"):
        n = int(c["sinistros_com_dossie"])
        linhas.append("🚨 %d %s com dossiê entregue" % (
            n, _plural(n, "sinistro", "sinistros")))
    if c.get("ajudas_incapacidade"):
        n = int(c["ajudas_incapacidade"])
        linhas.append("🆘 %d %s precisei de ajuda porque não consegui" % (
            n, _plural(n, "vez", "vezes")))

    fora = []
    if c.get("ajudas_regra"):
        n = int(c["ajudas_regra"])
        fora.append("📋 %d %s por regra" % (n, _plural(n, "passado", "passados")))
    if c.get("ajudas_desconhecidas"):
        n = int(c["ajudas_desconhecidas"])
        fora.append("📋 %d %s sem motivo registrado — a eficiência não %s conta" % (
            n, _plural(n, "ajuda", "ajudas"), _plural(n, "a", "as")))
    if c.get("duvidas"):
        n = int(c["duvidas"])
        fora.append("💬 %d %s respondidas" % (n, _plural(n, "dúvida", "dúvidas")))
    if c.get("ja_com_a_equipe"):
        n = int(c["ja_com_a_equipe"])
        fora.append("🤝 %d %s que a equipe já conduzia" % (
            n, _plural(n, "conversa", "conversas")))
    if c.get("calados_pela_janela"):
        n = int(c["calados_pela_janela"])
        fora.append("🔕 %d %s em que fiquei em silêncio pela janela" % (
            n, _plural(n, "conversa", "conversas")))
    if c.get("vigia_ura") or c.get("vigia_prazo"):
        pedacos = []
        if c.get("vigia_ura"):
            n = int(c["vigia_ura"])
            pedacos.append("%d %s ficaram esperando a URA" % (
                n, _plural(n, "acionamento", "acionamentos")))
        if c.get("vigia_prazo"):
            n = int(c["vigia_prazo"])
            pedacos.append("%d passou do prazo da sessão" % n)
        fora.append("⏱️ " + "; ".join(pedacos))

    if fora:
        linhas += ["", "Fora da conta:"] + fora

    linhas += ["", "🤖 agente"]
    return _juntar(linhas)


# ===========================================================================
# DE ONDE VEM CADA NÚMERO — `work_events` do dia, por corretora
# ===========================================================================
#: 🔴 Um número sem escritor vira **"não medido"**, nunca estimativa.
#: 📊 16/09/2026: `work_events` com `agente.cerebro | agente.sentinela |
#: agente.vigia` → 0 de 0 em toda a base; `handoff.realertado` → 0 (e a causa
#: estava na trava NOT NULL que a migration `20260916_02` removeu).
#: ⛔ Um resumo que inventa um número perde a corretora na primeira semana.
SEM_ESCRITOR: Tuple[str, ...] = ("duvidas",)


async def contagens_do_dia(db, company_id: str, inicio_utc: datetime,
                           fim_utc: datetime) -> Dict[str, int]:
    """As contagens do dia lidas de `work_events`. ⛔ Nunca levanta.

    ⚠️ **A reconciliação é um contrato:** a soma das linhas "fora da conta" tem
    de bater com os `grupo.calado` do dia. Um resumo em que ela não bate é um
    defeito, e o guarda G-D2 mede isso.
    """
    from app.services.o_fim_do_atendimento import _cliente

    c: Dict[str, int] = {
        "acionamentos_entregues": 0, "sinistros_com_dossie": 0,
        "ajudas_incapacidade": 0, "ajudas_regra": 0, "ajudas_desconhecidas": 0,
        "duvidas": 0, "ja_com_a_equipe": 0, "calados_pela_janela": 0,
        "vigia_ura": 0, "vigia_prazo": 0, "calados_total": 0, "truncou": 0,
    }
    # 🔴 PAGINADO, NÃO `.limit(5000)` — guarda `test_ninguem_pede_mais_de_mil_
    # linhas_de_novo`, 16/09/2026. O PostgREST devolve no máximo **1000** linhas
    # por resposta: um `.limit(5000)` num dia movimentado perderia eventos **em
    # silêncio**, e o resumo das 19h publicaria um número menor que a verdade
    # com cara de medição. É exatamente o defeito que esta SPEC existe para não
    # cometer (CLAUDE.md §12.1).
    #
    # ⚠️ E `truncou` viaja junto: quem mostra número para gente PRECISA saber
    # que a leitura parou no teto.
    try:
        from app.leitura_completa import ler_paginado_async

        def _consulta():
            return (_cliente(db).table("work_events")
                    .select("id, event_type, payload_redacted, created_at")
                    .eq("company_id", str(company_id))   # 🔴 §7
                    .gte("created_at", inicio_utc.isoformat())
                    .lt("created_at", fim_utc.isoformat()))

        linhas, truncou = await ler_paginado_async(
            _consulta, chave_unica="id", rotulo="resumo das 19h")
        c["truncou"] = 1 if truncou else 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RESUMO 19h] diário ilegível (%s)", type(exc).__name__)
        return c

    for linha in linhas:
        tipo = str((linha or {}).get("event_type") or "")
        carga = (linha or {}).get("payload_redacted") or {}
        carga = carga if isinstance(carga, dict) else {}
        classe = str(carga.get("motivo_classe") or CLASSE_DESCONHECIDA)
        do_que = str(carga.get("tipo") or "")

        if tipo == "grupo.enviado":
            if do_que == "sinistro":
                c["sinistros_com_dossie"] += 1
            elif do_que == "conclusao":
                c["acionamentos_entregues"] += 1
            elif do_que == "pedido_de_ajuda":
                if classe == CLASSE_INCAPACIDADE:
                    c["ajudas_incapacidade"] += 1
                elif classe == CLASSE_REGRA:
                    c["ajudas_regra"] += 1
                else:
                    c["ajudas_desconhecidas"] += 1
        elif tipo == "grupo.calado":
            c["calados_total"] += 1
            porque = str(carga.get("calou_porque") or "")
            # 🔴 As duas razões são DIFERENTES para quem lê, e por isso são
            #    duas linhas: "a equipe já estava lá" ≠ "a janela me calou".
            if "assumiu" in porque:
                c["ja_com_a_equipe"] += 1
            elif porque and porque != "repetido":
                c["calados_pela_janela"] += 1
        elif tipo in ("vigia.ura_silent", "vigia.human_silent_alert"):
            c["vigia_ura"] += 1
        elif tipo in ("vigia.deadline", "vigia.never_started"):
            c["vigia_prazo"] += 1
    return c


async def montar_o_resumo(db, company_id: str, *, agora=None,
                          tz_nome: Optional[str] = None) -> Tuple[str, Dict[str, int]]:
    """`(texto, contagens)`. Texto vazio = dia sem movimento, e não se manda nada."""
    from app.services.platform_outbound import fuso_da_corretora

    tz = fuso_da_corretora(tz_nome)
    agora = agora or datetime.now(timezone.utc)
    local = agora.astimezone(tz)
    inicio_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio = inicio_local.astimezone(timezone.utc)
    fim = (inicio_local + timedelta(days=1)).astimezone(timezone.utc)

    c = await contagens_do_dia(db, company_id, inicio, fim)
    return modelo_resumo_do_dia(local.strftime("%d/%m"), c), c
