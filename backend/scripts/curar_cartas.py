"""Curadoria das cartas de conhecimento: junta o repetido, barra o arriscado.

Por que isto existe
-------------------
O Destilador extraiu 1.441 cartas das conversas reais da Resulta. Lidas uma a
uma, a qualidade é alta — fato de processo, sem PII, do tamanho certo. Mas
existe um problema que só aparece olhando o conjunto:

    "Após a data limite de pagamento, a apólice entra em processo de cancelamento"
    "Após a data limite do boleto, a apólice entra em processo de cancelamento"
    "Após o prazo limite de pagamento, a apólice entra em processo de cancelamento"
    "Após o prazo limite sem pagamento, a apólice entra em processo de cancelamento"
    "Caso o boleto não seja pago até a data limite, a apólice entra em processo…"

Vinte cartas dizendo a mesma coisa. No RAG isso é veneno: o agente busca
"prazo de pagamento", recebe vinte quase-cópias e gasta todo o orçamento de
contexto com uma ideia só — o conhecimento diverso é sufocado justamente
quando mais importa.

O `card_hash` só junta texto IDÊNTICO. Ninguém escreve a mesma frase duas
vezes; escreve a mesma IDEIA de vinte jeitos.

Como junta, sem gastar modelo
-----------------------------
Assinatura por conteúdo: minúsculas, sem acento, sem palavra vazia, radical
curto de cada palavra. Duas cartas com ≥55% de palavras significativas em
comum são a mesma ideia.

O limiar foi CALIBRADO, não escolhido. Medindo dez pares rotulados à mão:

    quase-cópias reais ....... 0,75 · 0,67 · 0,54 · 0,50 · 0,27
    ideias distintas ......... 0,18 · 0,17 · 0,15 · 0,15 · 0,07

Não existe corte que separe as duas listas: o par de 0,27 diz a mesma coisa
("a atualização do cartão só vale depois da baixa da parcela") com palavras
diferentes — isso é semântica, não vocabulário.

Então o corte fica em 0,55: três vezes acima do pior falso positivo. Pega o
bloco gritante — as vinte cartas de "após o prazo a apólice é cancelada" — e
**deixa passar as quase-cópias sutis de propósito**. Juntar dois fatos
diferentes apaga conhecimento; deixar uma cópia a mais só ocupa espaço.

Para pegar as sutis é preciso comparar por SIGNIFICADO (embeddings), e o
sistema já embeda toda carta ao publicar — custaria menos de um centavo. Fica
como segunda passada, com o limiar calibrado sobre estes mesmos pares.

Fica a mais informativa do grupo — a que tem mais palavras próprias e nomeia
a seguradora. As outras viram `superseded`: não são erradas, são redundantes,
e continuam auditáveis.

O que é barrado
---------------
Carta com promessa ABSOLUTA sobre dinheiro ou cobertura. "sem possibilidade de
recuperação", "nunca é coberto", "sempre é pago": o atendimento de seguro tem
exceção para quase tudo, e um agente que repete um absoluto errado faz a
corretora prometer o que não pode cumprir.

Uso
---
    python scripts/curar_cartas.py            # só relata, não altera nada
    python scripts/curar_cartas.py --aplicar  # aplica no banco
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LIMIAR = 0.55

_VAZIAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "ou", "em", "no",
    "na", "nos", "nas", "um", "uma", "uns", "umas", "para", "por", "com", "sem",
    "que", "se", "ao", "aos", "as", "the", "ser", "sao", "e", "ha", "pode",
    "podem", "deve", "devem", "ate", "apos", "quando", "caso", "mesmo", "sobre",
    "entre", "mais", "menos", "muito", "pouco", "ja", "nao", "sim", "seu", "sua",
    "seus", "suas", "este", "esta", "isso", "comum", "possivel", "necessario",
}

# Promessa que não admite exceção. Em seguro quase tudo tem exceção, e um
# agente repetindo um absoluto errado faz a corretora prometer o que não pode.
_ABSOLUTO = re.compile(
    r"sem possibilidade de|nunca (?:e|é|sera|será) (?:coberto|pago|aceito|possivel|possível)"
    r"|sempre (?:e|é) (?:coberto|pago|aceito|garantido)"
    r"|em hipotese alguma|em hipótese alguma|jamais|impossivel recuperar|impossível recuperar"
    r"|garantidamente|sem excecao|sem exceção",
    re.IGNORECASE)


def _sem_acento(t: str) -> str:
    n = unicodedata.normalize("NFKD", t)
    return "".join(c for c in n if not unicodedata.combining(c))


def assinatura(texto: str) -> frozenset:
    """As palavras que carregam o SENTIDO da carta, em radical curto."""
    limpo = _sem_acento(str(texto or "")).lower()
    limpo = re.sub(r"[^a-z0-9\s]", " ", limpo)
    palavras = [p for p in limpo.split() if len(p) > 2 and p not in _VAZIAS]
    # radical curto: "cancelamento", "cancelada", "cancelar" -> "cancel"
    return frozenset(p[:6] for p in palavras)


def parecidas(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _riqueza(c: Dict[str, Any]) -> Tuple[int, int, int]:
    """Quem representa o grupo: nomeia a seguradora, tem mais conteúdo próprio
    e é mais específica. Nessa ordem."""
    return (1 if c.get("insurer_key") else 0,
            len(assinatura(c["card_text"])),
            len(c["card_text"]))


def agrupar(cartas: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Grupos de cartas que dizem a mesma coisa.

    Comparação por bloco de primeira-palavra-significativa para não fazer
    1.441² comparações — as quase-cópias sempre compartilham vocabulário.
    """
    por_palavra: Dict[str, List[int]] = defaultdict(list)
    assinaturas = [assinatura(c["card_text"]) for c in cartas]
    for i, sig in enumerate(assinaturas):
        for p in list(sig)[:6]:
            por_palavra[p].append(i)

    dono: Dict[int, int] = {}

    def raiz(i: int) -> int:
        while dono.get(i, i) != i:
            i = dono[i]
        return i

    for indices in por_palavra.values():
        if len(indices) > 400:      # palavra genérica demais para ser pista
            continue
        for pos, i in enumerate(indices):
            for j in indices[pos + 1:]:
                if parecidas(assinaturas[i], assinaturas[j]) >= LIMIAR:
                    ri, rj = raiz(i), raiz(j)
                    if ri != rj:
                        dono[rj] = ri

    grupos: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for i, c in enumerate(cartas):
        grupos[raiz(i)].append(c)
    return list(grupos.values())


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    cartas: List[Dict[str, Any]] = []
    inicio = 0
    while True:
        lote = (db.client.table("knowledge_cards")
                .select("id, card_text, insurer_key, ramo, category")
                .eq("status", "pending_review")
                .order("created_at", desc=False)
                .range(inicio, inicio + 999).execute().data) or []
        cartas.extend(lote)
        if len(lote) < 1000:
            break
        inicio += 1000

    print(f"\n{len(cartas)} cartas em revisão\n")

    barradas = [c for c in cartas if _ABSOLUTO.search(c["card_text"])]
    ids_barrados = {c["id"] for c in barradas}
    print(f"BARRADAS por promessa absoluta: {len(barradas)}")
    for c in barradas[:12]:
        print(f"   · {c['card_text'][:118]}")

    restantes = [c for c in cartas if c["id"] not in ids_barrados]
    grupos = agrupar(restantes)
    grupos.sort(key=len, reverse=True)

    guardar, dispensar = [], []
    for g in grupos:
        g.sort(key=_riqueza, reverse=True)
        guardar.append(g[0])
        dispensar.extend(g[1:])

    print(f"\n{len(restantes)} cartas -> {len(guardar)} ideias distintas "
          f"({len(dispensar)} quase-cópias juntadas)\n")
    print("OS MAIORES GRUPOS (fica a primeira):")
    for g in grupos[:6]:
        if len(g) < 3:
            break
        print(f"\n   [{len(g)} cartas]  {g[0]['card_text'][:104]}")
        for c in g[1:4]:
            print(f"        ~ {c['card_text'][:96]}")

    if not aplicar:
        print("\n(nada foi alterado — rode com --aplicar)")
        return 0

    def _marcar(ids: List[str], status: str) -> int:
        feitos = 0
        for i in range(0, len(ids), 100):
            db.client.table("knowledge_cards").update({"status": status}) \
                .in_("id", ids[i:i + 100]).execute()
            feitos += len(ids[i:i + 100])
        return feitos

    n1 = _marcar([c["id"] for c in barradas], "rejected_absoluto") if barradas else 0
    n2 = _marcar([c["id"] for c in dispensar], "superseded") if dispensar else 0
    print(f"\nAPLICADO: {n1} barradas, {n2} juntadas, {len(guardar)} seguem para aprovação")
    return 0


if __name__ == "__main__":
    sys.exit(main())
