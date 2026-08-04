"""SPEC-062 §18 — os SLIs. Mede-se primeiro; promete-se depois.

A regra que este arquivo respeita
---------------------------------
> **§18.1.** SLO sem baseline é chute.

Prometer "99,5% de disponibilidade" antes de saber quanto o sistema entrega
hoje não é meta: é número escolhido porque soa bem. Quando ele é furado — e
será — ninguém sabe se o sistema piorou ou se a promessa nasceu errada.

Então a ordem é: **medir sete dias com tráfego real, e só então propor o SLO.**
A Resulta pareia amanhã. É essa semana que produz a primeira base honesta.

Os contratos que NÃO dependem de baseline (§18.3)
-------------------------------------------------
Alguns números não se negociam com estatística — eles valem zero, sempre:

    cross-tenant .............. zero
    cobrança duplicada ........ zero
    segredo exposto ........... zero
    work run aceito e perdido . zero

Esses não viram SLO com percentual. Viram gate, e já estão no
`broker_outcome_regression_pack`. Medir "quantos vazamentos por semana" seria
aceitar que existe um número tolerável.

Por que gravar é `fire-and-forget`
----------------------------------
Um coletor de métrica que derruba o pedido do corretor é pior que métrica
nenhuma. Toda falha aqui vira log e some.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Nomes canônicos. Ficam aqui e não espalhados em string literal pelo código:
# um SLI com dois nomes é dois SLIs pela metade, e ninguém percebe até o
# gráfico ficar estranho.
CHAT_PRIMEIRA_RESPOSTA = "chat.primeira_resposta_ms"
CHAT_ERRO = "chat.erro"
WHATSAPP_INBOUND = "whatsapp.inbound_ms"
WHATSAPP_OBSERVACAO = "whatsapp.observacao_ms"
WORK_RUN_FILA = "work_run.espera_na_fila_ms"
WORK_RUN_DURACAO = "work_run.duracao_ms"
WORK_RUN_FALHA = "work_run.falha"
ATLAS_TECELAGEM = "atlas.tecelagem_ms"
FERRAMENTA_DURACAO = "tool.duracao_ms"
# Quanto tempo o segurado ficou esperando um humano que já foi chamado. Não é
# latência de máquina: é a espera de uma PESSOA que pediu uma PESSOA. Sem este
# número, `HUMAN_REQUESTED` é um estado que ninguém mede e do qual ninguém sai.
HANDOFF_ESPERA = "handoff.espera_humana_ms"

# Amostragem. Com tráfego alto, gravar 100% das medições produz uma tabela que
# custa mais que o produto. Padrão 1.0 porque hoje o volume é baixo e a
# primeira semana precisa de TODOS os pontos — a base tem de ser densa.
def _taxa() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("SLI_SAMPLE_RATE", "1.0"))))
    except (TypeError, ValueError):
        return 1.0


def _sorteia(chave: str) -> bool:
    """Amostragem determinística pela chave — sem `random`.

    `random` deixaria dois processos discordando sobre o mesmo evento e tornaria
    impossível reproduzir uma janela de medição. O hash da chave dá a mesma
    resposta em qualquer máquina, sempre.
    """
    taxa = _taxa()
    if taxa >= 1.0:
        return True
    if taxa <= 0.0:
        return False
    import hashlib

    h = int(hashlib.sha256(chave.encode("utf-8", "ignore")).hexdigest()[:8], 16)
    return (h % 10_000) < int(taxa * 10_000)


def _cliente() -> Any:
    try:
        from ...core.database import get_supabase_client

        raw = get_supabase_client()
        return getattr(raw, "client", raw)
    except Exception:  # noqa: BLE001
        return None


def registrar(sli: str, valor: float, *, company_id: Optional[str] = None,
              unidade: str = "ms", contexto: Optional[dict] = None) -> None:
    """Grava uma medição. Nunca levanta, nunca atrasa o pedido do corretor."""
    try:
        chave = f"{sli}:{company_id or '-'}:{int(time.time() * 1000)}"
        if not _sorteia(chave):
            return
        db = _cliente()
        if not db:
            return
        db.table("sli_samples").insert({
            "sli": sli,
            "company_id": str(company_id) if company_id else None,
            "valor": float(valor),
            "unidade": unidade,
            # O contexto NUNCA carrega conteúdo de mensagem nem dado do
            # segurado (§19.3). Só o que ajuda a explicar o número: modelo,
            # etapa, se houve retentativa.
            "contexto": _limpar(contexto or {}),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.debug("[SLI] %s não gravado: %s", sli, type(exc).__name__)


_PROIBIDOS = ("text", "texto", "message", "mensagem", "content", "conteudo",
              "prompt", "body", "cpf", "cnpj", "telefone", "phone", "email",
              "nome", "name", "api_key", "token", "secret", "password")


def _limpar(contexto: dict) -> dict:
    """Descarta qualquer chave que possa carregar conteúdo ou dado pessoal.

    §19.3 lista o contexto proibido. A lista é por NOME de campo e é
    deliberadamente exagerada: perder uma dimensão de análise custa uma
    consulta a mais; vazar conteúdo de conversa de segurado numa tabela de
    métrica custa a confiança da corretora.
    """
    limpo: dict = {}
    for k, v in list(contexto.items())[:12]:
        nome = str(k).lower()
        if any(p in nome for p in _PROIBIDOS):
            continue
        if isinstance(v, (int, float, bool)) or v is None:
            limpo[str(k)] = v
        else:
            limpo[str(k)] = str(v)[:80]
    return limpo


@contextmanager
def medir(sli: str, *, company_id: Optional[str] = None,
          contexto: Optional[dict] = None):
    """Cronômetro. Grava a duração ao sair, inclusive quando dá erro.

        with medir(SLI.CHAT_PRIMEIRA_RESPOSTA, company_id=cid):
            ...

    Medir só o caminho feliz produz um p95 lindo e mentiroso: a lentidão mora
    justamente onde as coisas dão errado.
    """
    inicio = time.perf_counter()
    houve_erro = False
    try:
        yield
    except Exception:
        houve_erro = True
        raise
    finally:
        ms = (time.perf_counter() - inicio) * 1000
        registrar(sli, ms, company_id=company_id,
                  contexto={**(contexto or {}), "erro": houve_erro})


def resumo(sli: str, *, dias: int = 7,
           company_id: Optional[str] = None) -> dict:
    """A base para PROPOR um SLO — nunca para prometer um.

    Devolve p50/p95/p99 e diz explicitamente quantas amostras sustentam o
    número. Com poucas amostras, um p99 é ruído com cara de estatística.
    """
    from datetime import datetime, timedelta, timezone

    db = _cliente()
    if not db:
        return {"ok": False, "erro": "sem banco"}

    desde = (datetime.now(timezone.utc) - timedelta(days=max(1, dias))).isoformat()
    try:
        q = (db.table("sli_samples").select("valor")
             .eq("sli", sli).gte("observado_em", desde).limit(50_000))
        if company_id:
            q = q.eq("company_id", str(company_id))
        valores = sorted(float(r["valor"]) for r in (q.execute().data or []))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "erro": type(exc).__name__}

    if not valores:
        return {"ok": True, "sli": sli, "amostras": 0,
                "frase": f"Ainda não há medição de '{sli}' nos últimos {dias} dias."}

    def _p(pct: float) -> float:
        i = min(len(valores) - 1, int(round(pct * (len(valores) - 1))))
        return round(valores[i], 2)

    n = len(valores)
    # Abaixo de 100 amostras, um p99 é literalmente o pior de um punhado de
    # medições. Dizer isso evita que alguém transforme ruído em promessa.
    confiavel = n >= 100

    return {
        "ok": True, "sli": sli, "periodo_dias": dias, "amostras": n,
        "p50": _p(0.50), "p95": _p(0.95), "p99": _p(0.99),
        "min": round(valores[0], 2), "max": round(valores[-1], 2),
        "base_confiavel": confiavel,
        "frase": (
            f"'{sli}': p50 {_p(0.50):.0f}, p95 {_p(0.95):.0f}, p99 {_p(0.99):.0f} "
            f"em {n} amostras."
            + ("" if confiavel else
               " Poucas amostras para propor SLO — um p99 sobre menos de 100 "
               "medições é ruído com cara de estatística.")),
    }
