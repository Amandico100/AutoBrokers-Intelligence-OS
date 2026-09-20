# -*- coding: utf-8 -*-
"""🔴 O DUBLÊ NASCE DO BANCO — SPEC-EXTRA-001.7, unidade B.

Gera `tests/corpus/piloto/recorte.json`: um recorte **real** das tabelas do FIO,
ANONIMIZADO na geração. É ele que o teste do fio serve ao medidor no lugar do
banco.

```
cd backend
PYTHONIOENCODING=utf-8 python scripts/gerar_recorte_do_piloto.py \
    --de 2026-09-16 --ate 2026-09-20
```

🔴 **Por que gerado, e nunca escrito à mão:** um dublê inventado prova que o
medidor concorda com a imaginação de quem o escreveu. O que precisa ser provado
é o comportamento do motor sobre a FORMA REAL das linhas — inclusive as chaves
que ninguém lembraria de pôr, e as que ninguém sabia que estavam vazias.

⛔ **O gerador RECUSA gravar** se encontrar padrão de telefone, CPF, placa ou
e-mail no que ia escrever. A anonimização é por INCLUSÃO: só as chaves listadas
aqui atravessam; `content`, `summary`, `detail` livre, `phone`, `user_name` e
`ficha_atendimento` são descartados na origem.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from app.services.o_fim_do_atendimento import (  # noqa: E402
    MOTIVO_EXCECAO_DE_TESTE,
    MOTIVO_NUMERO_DA_CASA,
    MOTIVO_TURNO_PERDIDO,
    classe_do_silencio,
)
from scripts.medir_o_piloto import (  # noqa: E402
    CORRETORAS_PADRAO,
    TITULO_SILENCIO,
    TITULO_SILENCIO_EXCECAO,
    procurar_pii,
)

DESTINO = os.path.join(RAIZ, "tests", "corpus", "piloto", "recorte.json")

#: 🔴 O motivo SINTÉTICO que representa cada classe. ⚠️ Ele não é invenção: é
#: montado a partir das CONSTANTES do motor, e o teste prova que
#: `classe_do_silencio(sintetico) == classe_real`. ⛔ A classe `takeover` é a
#: única sem constante — a frase real dela **começa por nome de pessoa**, e é
#: exatamente por isso que ela não pode ser copiada para cá.
MOTIVO_SINTETICO: Dict[str, str] = {
    "turno_perdido": MOTIVO_TURNO_PERDIDO,
    "pedido_de_pessoa": "o segurado pediu para falar com uma pessoa",
    "falha_ao_ler_o_takeover": "não consegui saber se alguém assumiu",
    "falha_ao_ler_o_historico": "não consegui ler o histórico",
    "excecao_de_teste": MOTIVO_EXCECAO_DE_TESTE,
    "numero_da_casa": MOTIVO_NUMERO_DA_CASA,
    "janela": "a atendente falou nesta conversa; o agente fica em silêncio",
    "takeover": "uma pessoa da equipe assumiu esta conversa",
    "sem_motivo": "",
}


def anon(valor: Any) -> str:
    """O mesmo id vira sempre a mesma chave curta — e nunca volta ao original.

    🔴 **Os grupos de 4 não são enfeite.** 📊 Na primeira geração o gerador se
    RECUSOU a gravar: 38 achados de "telefone/CPF" que eram hashes hexadecimais
    caindo em 10 ou 11 dígitos seguidos (`a07998169118`). Um id anonimizado que
    PARECE telefone envenena todo guarda de PII depois dele — e o jeito de o
    número nunca mais parecer um é quebrar a corrida de dígitos na origem.
    """
    if valor in (None, ""):
        return ""
    bruto = hashlib.sha256(("piloto:" + str(valor)).encode("utf-8")).hexdigest()[:12]
    return "-".join(bruto[i:i + 4] for i in range(0, 12, 4))


def _porque_reduzido(porque: str) -> str:
    """`calou_porque` vira um TOKEN DE CLASSE, sem nome de pessoa nem data.

    🔴 Os três ramos de `contagens_do_dia` são preservados **por construção**:
    `assumiu` → já com a equipe · `repetido` → não conta · o resto → janela.
    """
    texto = str(porque or "")
    if "assumiu" in texto:
        return "a equipe assumiu"
    if texto.strip() == "repetido":
        return "repetido"
    return "a janela calou o agente" if texto.strip() else ""


CHAVES_DO_EVENTO = ("tipo", "motivo_classe", "teto", "lembretes", "tem_dono")


async def gerar(de: str, ate: str, corretoras: Sequence[str]) -> Dict[str, Any]:
    from app.core.database import create_async_supabase_client

    cliente = (await create_async_supabase_client()).client
    inicio, fim = de + "T00:00:00+00:00", ate + "T23:59:59+00:00"
    tabelas: Dict[str, List[dict]] = {k: [] for k in (
        "companies", "conversations", "messages", "platform_sends", "work_runs",
        "agent_activities", "work_events", "conversation_logs")}
    silencios_esperados: List[Dict[str, str]] = []

    for nome in corretoras:
        linhas = (await cliente.table("companies").select("id, company_name")
                  .eq("company_name", nome).limit(2).execute()).data or []
        if not linhas:
            raise SystemExit("⛔ corretora não encontrada: %r" % nome)
        cid = str(linhas[0]["id"])
        tabelas["companies"].append({"id": anon(cid), "company_name": nome})

        conversas = (await cliente.table("conversations")
                     .select("id, status, resolucao_motivo, resolvido_em, "
                             "updated_at, ficha_atendimento")
                     .eq("company_id", cid).gte("updated_at", inicio)
                     .lt("updated_at", fim).limit(400).execute()).data or []
        ids = []
        for c in conversas:
            ficha = c.get("ficha_atendimento")
            ids.append(str(c["id"]))
            tabelas["conversations"].append({
                "id": anon(c["id"]), "company_id": anon(cid),
                "status": c.get("status"),
                "resolucao_motivo": c.get("resolucao_motivo"),
                "resolvido_em": c.get("resolvido_em"),
                "updated_at": c.get("updated_at"),
                # ⛔ A ficha inteira fica no banco. Sai dela um sim/não.
                "ficha_atendimento": {"apolice_confirmada": bool(
                    (ficha or {}).get("apolice_confirmada") is True
                    if isinstance(ficha, dict) else False)},
            })

        for i in range(0, len(ids), 40):
            msgs = (await cliente.table("messages")
                    .select("id, conversation_id, role, payload, created_at")
                    .in_("conversation_id", ids[i:i + 40])
                    .gte("created_at", inicio).lt("created_at", fim)
                    .limit(1000).execute()).data or []
            for m in msgs:
                carga = m.get("payload") if isinstance(m.get("payload"), dict) else {}
                waids = (carga or {}).get("wa_message_ids")
                tabelas["messages"].append({
                    "id": anon(m["id"]),
                    "conversation_id": anon(m.get("conversation_id")),
                    "role": m.get("role"),
                    "created_at": m.get("created_at"),
                    # ⛔ `content` nunca sai do banco. Do payload sobra a ORIGEM,
                    #    a direção e QUANTOS ids de WhatsApp havia — nunca quais.
                    "payload": {
                        "origem": (carga or {}).get("origem"),
                        "direcao": (carga or {}).get("direcao"),
                        "wa_message_ids": ["wa%d" % k for k in range(
                            len(waids) if isinstance(waids, list) else 0)],
                    } if carga else None,
                })

        for tabela, colunas in (
                ("platform_sends", "id, kind, created_at"),
                ("work_runs", "id, runtime_kind, status, created_at"),
                ("conversation_logs", "id, status, response_time_ms, created_at"),
        ):
            for r in ((await cliente.table(tabela).select(colunas)
                       .eq("company_id", cid).gte("created_at", inicio)
                       .lt("created_at", fim).limit(1000).execute()).data or []):
                r = dict(r)
                r["id"] = anon(r["id"])
                r["company_id"] = anon(cid)
                tabelas[tabela].append(r)

        for r in ((await cliente.table("work_events")
                   .select("id, event_type, payload_redacted, created_at")
                   .eq("company_id", cid).gte("created_at", inicio)
                   .lt("created_at", fim).limit(1000).execute()).data or []):
            carga = r.get("payload_redacted")
            carga = carga if isinstance(carga, dict) else {}
            limpa = {k: carga.get(k) for k in CHAVES_DO_EVENTO if k in carga}
            if "calou_porque" in carga:
                limpa["calou_porque"] = _porque_reduzido(carga.get("calou_porque"))
            tabelas["work_events"].append({
                "id": anon(r["id"]), "company_id": anon(cid),
                "event_type": r.get("event_type"),
                "created_at": r.get("created_at"), "payload_redacted": limpa})

        # 🔴 As atividades do período MAIS uma amostra histórica de SILÊNCIOS:
        #    a janela do piloto pode não ter nenhum, e o caminho que leva o
        #    `detail` ao motor precisa existir no dublê para ser provado.
        atividades = ((await cliente.table("agent_activities")
                       .select("id, category, title, detail, created_at")
                       .eq("company_id", cid).gte("created_at", inicio)
                       .lt("created_at", fim).limit(1000).execute()).data or [])
        historicas = ((await cliente.table("agent_activities")
                       .select("id, category, title, detail, created_at")
                       .eq("company_id", cid).eq("title", TITULO_SILENCIO)
                       .limit(20).execute()).data or [])
        vistos = {str(a["id"]) for a in atividades}
        for a in atividades + [h for h in historicas if str(h["id"]) not in vistos]:
            titulo = str(a.get("title") or "")
            detalhe = ""
            if titulo in (TITULO_SILENCIO, TITULO_SILENCIO_EXCECAO):
                # 🔴 A CLASSE é aplicada AQUI, pelo motor, sobre o `detail`
                #    REAL; o que viaja é um motivo sintético da MESMA classe.
                classe = classe_do_silencio(a.get("detail"))
                detalhe = MOTIVO_SINTETICO.get(classe, MOTIVO_SINTETICO["takeover"])
                silencios_esperados.append({"id": anon(a["id"]),
                                            "classe": classe})
            tabelas["agent_activities"].append({
                "id": anon(a["id"]), "company_id": anon(cid),
                "category": a.get("category"), "title": titulo,
                "detail": detalhe, "created_at": a.get("created_at")})

    return {"gerado_em": datetime.now(timezone.utc).isoformat(),
            "de": de, "ate": ate,
            "silencios_esperados": silencios_esperados, "tabelas": tabelas}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="gera o dublê do piloto a partir do banco")
    p.add_argument("--de", required=True)
    p.add_argument("--ate", required=True)
    p.add_argument("--corretora", action="append")
    p.add_argument("--saida", default=DESTINO)
    args = p.parse_args(list(argv) if argv is not None else None)

    from dotenv import load_dotenv

    load_dotenv(os.path.join(RAIZ, ".env"))
    corpo = asyncio.run(gerar(args.de, args.ate,
                              args.corretora or list(CORRETORAS_PADRAO)))
    texto = json.dumps(corpo, ensure_ascii=False, indent=1, sort_keys=True)

    achados = procurar_pii(texto)
    if achados:
        print("⛔ RECUSADO: o recorte contém %d padrão(ões) de dado pessoal: %s"
              % (len(achados), sorted({a[0] for a in achados})))
        return 2

    os.makedirs(os.path.dirname(args.saida), exist_ok=True)
    with io.open(args.saida, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto + "\n")
    print("📊 %s · %d bytes · linhas por tabela: %s"
          % (args.saida, len(texto),
             {k: len(v) for k, v in sorted(corpo["tabelas"].items())}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
