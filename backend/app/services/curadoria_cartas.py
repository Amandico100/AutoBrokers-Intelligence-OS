"""Da carta crua ao RAG: junta o repetido, barra o absoluto, publica o resto.

Por que isto roda sozinho
-------------------------
O Founder não é especialista em seguros e não tem como ler 1.441 fatos um a
um — e em 29/07/2026 chegam as centenas da AutoFleet. A revisão que importa
aqui é a de PII, e ela é **determinística**: `templatize` mascara na extração,
a LLM é instruída a não citar pessoa, e `_card_pii_clean` reconfere no momento
exato da publicação. Três camadas, nenhuma dependendo de alguém lembrar.

O que sobra para o humano é o que só o humano decide: rejeitar um fato que ele
sabe estar errado. Isso continua em /admin/espelho, e rejeitar tira do RAG.

As três coisas que este módulo faz
----------------------------------
**1. Junta o que diz a mesma coisa.** O `card_hash` só pega texto idêntico.
Ninguém escreve a mesma frase duas vezes — escreve a mesma ideia de vinte
jeitos:

    "Quando o pagamento EM cartão não é autorizado, a seguradora gera boleto…"
    "Quando o pagamento NO cartão não é autorizado, a seguradora gera boleto…"

No RAG isso é veneno: o agente busca "cartão recusado", recebe quinze
quase-cópias e gasta todo o orçamento de contexto com uma ideia só.

O limiar de 0,47 foi MEDIDO amostrando a faixa par a par: em 0,45 apareceu um
falso positivo real ("boletos são enviados ao segurado" × "alterações de forma
de pagamento"). E só junta dentro da MESMA seguradora — "a HDI gera boleto"
não é a mesma informação que a genérica, é ela que dá confiança ao agente
quando o segurado é da HDI.

**2. Barra promessa absoluta.** Em seguro quase tudo tem exceção. Um agente
repetindo "sem possibilidade de recuperação" faz a corretora prometer o que
não pode cumprir — ainda mais quando existe outra carta dizendo que
comprovante permite pedir reanálise.

**3. Publica com CONTEXTO no próprio texto.** O chunk vai para o Qdrant como

    (hdi / auto / cobrança) Quando a parcela do cartão não é autorizada…

O assunto entra no texto de propósito: a busca é híbrida, e o BM25 casa por
palavra exata. Sem "cobrança" ali, uma pergunta sobre boleto disputa espaço em
igualdade com uma carta de vistoria que por acaso menciona pagamento.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LIMIAR = 0.47

_VAZIAS = {
    "as", "os", "das", "dos", "ele", "ela", "com", "sem", "que", "ser", "sao",
    "tem", "uma", "uns", "umas", "para", "por", "nao", "sim", "seu", "sua",
    "seus", "suas", "este", "esta", "isso", "pode", "podem", "deve", "devem",
    "ate", "apos", "quando", "caso", "mesmo", "sobre", "entre", "mais", "menos",
    "muito", "pouco", "comum", "possivel", "necessario", "the", "and", "esse",
    "essa", "como", "onde", "qual", "quais", "todo", "toda", "todos", "todas",
    "apenas", "tambem",
}

_ABSOLUTO = re.compile(
    r"sem possibilidade de|nunca (?:e|é|sera|será) (?:coberto|pago|aceito|possivel|possível)"
    r"|sempre (?:e|é) (?:coberto|pago|aceito|garantido)|em hip[óo]tese alguma|jamais"
    r"|imposs[íi]vel recuperar|garantidamente|sem exce[çc][ãa]o",
    re.IGNORECASE)

# O ASSUNTO DA CARTA, em uma palavra que o corretor realmente digita.
#
# Ordem = prioridade. "Boleto de sinistro" é assunto de sinistro; "boleto da
# parcela" é cobrança. Quem vem primeiro ganha, e o específico vem antes do
# genérico de propósito.
_ASSUNTOS: List[Tuple[str, re.Pattern]] = [
    ("sinistro", re.compile(r"sinistro|regulad|perito|vistoria de dano|colis|batida|roubo|furto", re.I)),
    ("assistencia", re.compile(r"guincho|chaveiro|encanador|eletricista|desentup|pane seca|reboque"
                               r"|assist[êe]ncia|prestador|carro reserva|t[áa]xi", re.I)),
    ("cobranca", re.compile(r"boleto|parcela|cobran|pagamento|cart[ãa]o|pix|d[ée]bito autom"
                            r"|inadimpl|vencimento|juros|fatura|qrcode|carn[êe]", re.I)),
    ("cancelamento", re.compile(r"cancelament|cancelad|cancelar|rescis", re.I)),
    ("apolice", re.compile(r"ap[óo]lice|endosso|vig[êe]ncia|cobertura|franquia|renova"
                           r"|proposta|emiss[ãa]o", re.I)),
    ("vistoria", re.compile(r"vistoria|laudo|inspe[çc]", re.I)),
    ("documentos", re.compile(r"documento|cnh|crlv|comprovante|boletim de ocorr[êe]ncia|nota fiscal", re.I)),
]


def assunto_da_carta(texto: str) -> str:
    """Em que gaveta esta carta mora. Determinístico, sem modelo."""
    for nome, rx in _ASSUNTOS:
        if rx.search(str(texto or "")):
            return nome
    return "processo"


def _sem_acento(t: str) -> str:
    n = unicodedata.normalize("NFKD", str(t or ""))
    return "".join(c for c in n if not unicodedata.combining(c))


def assinatura(texto: str) -> frozenset:
    limpo = re.sub(r"[^a-z0-9\s]", " ", _sem_acento(texto).lower())
    return frozenset(p[:6] for p in limpo.split() if len(p) > 2 and p not in _VAZIAS)


def parecidas(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _riqueza(c: Dict[str, Any]) -> Tuple[int, int]:
    return (len(assinatura(c.get("card_text") or "")), len(c.get("card_text") or ""))


def escolher_representantes(cartas: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """(ficam, sao_copias). Só junta cartas da MESMA seguradora."""
    por_seg: Dict[Optional[str], List[Dict[str, Any]]] = {}
    for c in cartas:
        por_seg.setdefault(c.get("insurer_key"), []).append(c)

    ficam: List[str] = []
    copias: List[str] = []
    for grupo in por_seg.values():
        grupo = sorted(grupo, key=_riqueza, reverse=True)
        guardadas: List[frozenset] = []
        for c in grupo:
            sig = assinatura(c.get("card_text") or "")
            if len(sig) < 3:
                ficam.append(c["id"])       # curta demais para comparar: fica
                continue
            if any(parecidas(sig, g) >= LIMIAR for g in guardadas):
                copias.append(c["id"])
            else:
                guardadas.append(sig)
                ficam.append(c["id"])
    return ficam, copias


def curar_sync(aplicar: bool = True) -> Dict[str, Any]:
    """Junta as quase-cópias e barra os absolutos. Sem LLM, sem custo."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    cartas: List[Dict[str, Any]] = []
    inicio = 0
    while True:
        lote = (db.client.table("knowledge_cards")
                .select("id, card_text, insurer_key, ramo")
                .eq("status", "pending_review")
                .order("created_at", desc=False)
                .range(inicio, inicio + 999).execute().data) or []
        cartas.extend(lote)
        if len(lote) < 1000:
            break
        inicio += 1000

    barradas = [c["id"] for c in cartas if _ABSOLUTO.search(c.get("card_text") or "")]
    proibidos = set(barradas)
    ficam, copias = escolher_representantes([c for c in cartas if c["id"] not in proibidos])

    if aplicar:
        for ids, status in ((barradas, "rejected_absoluto"), (copias, "superseded")):
            for i in range(0, len(ids), 100):
                db.client.table("knowledge_cards").update({"status": status}) \
                    .in_("id", ids[i:i + 100]).execute()

    return {"lidas": len(cartas), "barradas": len(barradas),
            "juntadas": len(copias), "ideias_distintas": len(ficam), "aplicado": aplicar}


def publicar_lote_sync(limite: int = 300) -> Dict[str, Any]:
    """Publica no RAG global as cartas que sobraram da curadoria.

    Uma de cada vez, marcando logo depois: se a rodada cair no meio, o que já
    foi publicado está marcado e a próxima continua de onde parou — nunca
    republica nem deixa metade sem ninguém saber qual metade.
    """
    from app.core.database import get_supabase_client
    from app.services.attendance_distiller import publish_card_sync

    db = get_supabase_client()
    alvo = (db.client.table("knowledge_cards")
            .select("id, card_text, insurer_key, ramo")
            .eq("status", "pending_review")
            .order("created_at", desc=False)
            .limit(max(1, min(int(limite or 300), 2000))).execute().data) or []

    publicadas = falhas = 0
    for c in alvo:
        try:
            if publish_card_sync(c):
                from datetime import datetime, timezone

                db.client.table("knowledge_cards").update(
                    {"status": "published",
                     "published_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", c["id"]).execute()
                publicadas += 1
            else:
                falhas += 1
        except Exception as exc:  # noqa: BLE001 — uma carta ruim não trava o lote
            falhas += 1
            logger.warning("[CARTAS] publicação falhou: %s", type(exc).__name__)

    return {"publicadas": publicadas, "falhas": falhas, "tentadas": len(alvo)}
