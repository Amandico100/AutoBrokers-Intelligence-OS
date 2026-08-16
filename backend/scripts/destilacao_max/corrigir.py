"""Troca uma carta errada por uma certa, sem deixar a errada viva em lugar nenhum.

Por que não basta um UPDATE no texto
------------------------------------
`card_hash` é o md5 do próprio texto. Mudar `card_text` sem mudar o hash cria uma
carta cuja identidade não corresponde ao conteúdo — e a próxima destilação que
produzir o texto ANTIGO vai colidir com ela e ser descartada como duplicata.
Pior: o ponto no Qdrant guarda uma cópia do texto no payload e continua
respondendo com a versão errada, porque ninguém reindexa o que não mudou de id.

Então a troca é em duas mãos: a errada sai do índice e é marcada `superseded`;
a certa entra como carta nova, com hash próprio, e o publicador a indexa.

`superseded` e não `rejected_pii`: a carta não vazou nada, ela estava errada.
Guardar o motivo separado importa quando alguém for auditar por que uma carta
sumiu.

Uso
---
    python corrigir.py                 # mostra o que faria
    python corrigir.py --aplicar
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402
from mascarar import _carregar_servico, templatize  # noqa: E402

assunto_da_carta = _carregar_servico("curadoria_cartas").assunto_da_carta

MARCA = "organizacao_30_07_2026"

# id da carta errada -> (motivo, texto que entra no lugar; None = só remove)
TROCAS = {
    # Duas cartas afirmavam percentual de franquia como se fosse fixo, e
    # discordavam entre si sobre a MESMA cobertura: 20% numa, 15% na outra.
    # A discordância é a prova de que o número é da apólice, não da cobertura.
    # O conselho das duas é bom e foi preservado; o número saiu.
    "07886e88-6d28-48dd-a120-f9b4979aeebd": (
        "percentual de franquia afirmado como fixo; contradiz 88efd201 sobre a "
        "mesma cobertura (20% x 15%)",
        "A franquia de impacto de veiculos e um percentual do prejuizo com valor "
        "minimo, e o percentual muda de apolice para apolice: orce o reparo e "
        "compare com a franquia da apolice antes de abrir o aviso, porque abaixo "
        "do minimo nao ha indenizacao e o sinistro fica no historico a toa.",
    ),
    "2b988981-9c48-4090-9d8e-607b98a2f95d": (
        "percentual de franquia de danos eletricos afirmado como fixo",
        "A cobertura de danos eletricos tem franquia em percentual do prejuizo "
        "com valor minimo, e o percentual e o minimo constam da apolice: "
        "confirme os dois antes de abrir o aviso, porque equipamento cujo "
        "conserto fique abaixo do minimo nao gera indenizacao.",
    ),
    # O limite de litros da caixa d'agua veio da fala da atendente (5 mil),
    # enquanto o dado que ela mesma coletou dizia 7.500 por caixa. O subagente
    # registrou a divergencia; a carta ficou com o numero.
    "340ea312-0ec1-4119-86a6-8a370fb7c6f0": (
        "limite de litros afirmado como fixo; a propria conversa mostrava "
        "capacidade diferente da informada",
        "A assistencia de limpeza de caixa d'agua tem limite de capacidade em "
        "litros e o limite e da apolice: confirme a capacidade da caixa e o "
        "limite contratado antes de acionar, e avise o segurado de que o "
        "prestador pode recusar a parte que passar do limite.",
    ),
}


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)

    trocadas = inseridas = 0
    for cid, (motivo, novo) in TROCAS.items():
        # 🔴 O SELECT E A LISTA DO QUE SOBREVIVE — 15/08/2026 (SPEC-072, P-176)
        # ---------------------------------------------------------------------
        # Ele pedia cinco colunas, e faltavam as que carregam a PROCEDENCIA. Dois
        # danos diferentes saiam disso, e valem separados porque a gravidade e
        # outra:
        #
        #  🟢 sem `pii_check`, o `marca = {**(c.get("pii_check") or {}), …}` de
        #     baixo espalhava um dict SEMPRE VAZIO, e o `update` substituia a
        #     coluna inteira por duas chaves — matando `faceta`, `origem` e
        #     `reindexado_em`. Menor porque essa carta esta sendo APOSENTADA no
        #     mesmo update: o que se perde e o rastro de auditoria de uma carta
        #     que ja saiu do indice.
        #
        #  🔴 sem `source_unit_id` (e as duas irmas), a carta SUBSTITUTA nascia
        #     sem caminho de volta ao contrato. Essa e a grave: o lastro E o
        #     produto — sem ele, "a clausula 4.4.2.d diz que nao cobre" vira
        #     "acho que nao cobre". E ela entraria em `publicar_lote_sync` com
        #     `documento_publico=False`, que e o caso que o BLOCO 0 fechou,
        #     reaberto por outra porta.
        #
        # ⚠️ Sao TRES colunas de procedencia, nao uma. `knowledge_cards` tem a FK
        # composta `knowledge_cards_procedencia_coerente_fk (source_version_id,
        # source_document_id)` desde `20260808_03`: propagar so o `unit_id`
        # deixaria a carta com endereco e sem documento.
        atual = (db.table("knowledge_cards")
                 .select("id, card_text, ramo, insurer_key, status, pii_check, "
                         "source_unit_id, source_document_id, source_version_id")
                 .eq("id", cid).limit(1).execute().data or [])
        if not atual:
            print(f"  {cid[:8]} não existe — pulando")
            continue
        c = atual[0]
        print(f"\n  SAI [{c['status']}] {c['card_text'][:88]}")
        print(f"  motivo: {motivo}")
        if novo:
            limpo = templatize(novo) == novo
            print(f"  ENTRA  {novo[:88]}")
            if not limpo:
                print("  !! o texto novo não passa no templatize — NÃO será inserido")
        if not aplicar:
            continue

        # O ponto no Qdrant precisa sair. Este script roda na máquina do
        # desenvolvedor, que não tem a credencial do índice — e tentar de todo
        # jeito e seguir em frente deixaria a carta removida no banco e viva na
        # busca. Então: tenta; se não der, MARCA. `reconciliar_indice_sync`,
        # que roda no servidor antes de cada publicação, termina o serviço.
        pendente = True
        try:
            from app.services.attendance_distiller import despublicar_carta_sync
            pendente = not despublicar_carta_sync(cid, motivo="superseded")
        except Exception as exc:  # noqa: BLE001
            print(f"  ponto fica marcado para o servidor remover: "
                  f"{type(exc).__name__}")

        marca = {**(c.get("pii_check") or {}),
                 "superseded_por": MARCA, "motivo": motivo}
        if pendente:
            marca["qdrant_pendente"] = "true"
        db.table("knowledge_cards").update({
            "status": "superseded", "pii_check": marca,
        }).eq("id", cid).execute()
        trocadas += 1

        if novo and templatize(novo) == novo:
            # A CARTA CORRIGIDA HERDA A PROCEDENCIA DA QUE ELA CORRIGE.
            #
            # Ela e a MESMA afirmacao, escrita direito — nao um fato novo. Herdar
            # `source_*` e a `faceta` e o que a mantem citavel: sem isso, corrigir
            # o conteudo DESTROI a prova, e o pior e que ninguem desconfia, porque
            # a carta nova esta mais certa que a velha.
            #
            # `origem` fica de fora de proposito: ela descreve de que RODADA a
            # carta veio, e esta veio desta correcao, nao daquela.
            marcas_antigas = c.get("pii_check")
            if not isinstance(marcas_antigas, dict):
                marcas_antigas = {}
            procedencia = {k: c.get(k) for k in
                           ("source_unit_id", "source_document_id", "source_version_id")
                           if c.get(k)}
            db.table("knowledge_cards").upsert([{
                "card_hash": hashlib.md5(novo.lower().encode("utf-8")).hexdigest(),
                "card_text": novo, "category": assunto_da_carta(novo),
                "ramo": c.get("ramo") or "outro",
                "insurer_key": c.get("insurer_key"),
                "status": "pending_review",
                **procedencia,
                "pii_check": {"deterministic": True, "llm_instructed": True,
                              "por": MARCA, "corrige": cid,
                              **({"faceta": marcas_antigas["faceta"]}
                                 if marcas_antigas.get("faceta") else {})},
            }], on_conflict="card_hash", ignore_duplicates=True).execute()
            inseridas += 1
            if procedencia:
                print(f"  procedencia herdada: {procedencia.get('source_unit_id')}")

    if aplicar:
        print(f"\n  {trocadas} despublicadas · {inseridas} corrigidas entram como pending_review")
    else:
        print(f"\n  (nada gravado — rode com --aplicar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
