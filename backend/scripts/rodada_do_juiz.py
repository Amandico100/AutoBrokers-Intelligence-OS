#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AAA v13 (em teste, D-PROTO-10) · T1 — a trava das DUAS RODADAS, por máquina.

📊 Em 19 SPECs as rodadas 3+ renderam 4 achados ao custo de ≈ 600 min, todos no MESMO ponto cego
(`docs/canon/specs-propostas/AUDITORIA-AAA-E-JEV-2026-09-19.md`). Na 3ª rodada o defeito é o CARD (o FIO
estava errado), não o código. A regra existia em texto (§3.1, §8) e não segurou a EXTRA-001.5.1 (5 rodadas).

O gerente chama ESTE script antes de montar qualquer pacote de julgamento. Ele é o único que incrementa.

  python backend/scripts/rodada_do_juiz.py abrir  --spec EXTRA-001.5.2 --faixa-min 150
  python backend/scripts/rodada_do_juiz.py julgar            # 1ª e 2ª passam; a 3ª sai com código 2
  python backend/scripts/rodada_do_juiz.py fio-reescrito     # só depois de reescrever O FIO no card: zera
  python backend/scripts/rodada_do_juiz.py estado            # rodada, minutos corridos, e se passou de 1,5× a faixa
"""
import argparse
import datetime as dt
import json
import os
import sys

ESTADO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".aaa-card.json")
TETO_DE_RODADAS = 2


def _agora():
    return dt.datetime.now(dt.timezone.utc)


def _ler():
    if not os.path.exists(ESTADO):
        return None
    with open(ESTADO, encoding="utf-8") as f:
        return json.load(f)


def _gravar(d):
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("acao", choices=("abrir", "julgar", "fio-reescrito", "estado"))
    p.add_argument("--spec")
    p.add_argument("--faixa-min", type=int, default=150)
    a = p.parse_args(argv)

    if a.acao == "abrir":
        if not a.spec:
            print("abrir exige --spec")
            return 1
        _gravar({"spec": a.spec, "inicio": _agora().isoformat(), "faixa_min": a.faixa_min,
                 "rodada": 0, "fios_reescritos": 0})
        print("card aberto: %s · faixa %d min · teto %d rodadas" % (a.spec, a.faixa_min, TETO_DE_RODADAS))
        return 0

    d = _ler()
    if d is None:
        print("sem card aberto (rode `abrir`)")
        return 1
    corridos = (_agora() - dt.datetime.fromisoformat(d["inicio"])).total_seconds() / 60.0
    estourou = corridos > 1.5 * d["faixa_min"]

    if a.acao == "julgar":
        if d["rodada"] >= TETO_DE_RODADAS:
            print("⛔ T1: %s já teve %d rodadas de julgamento. A 3ª é PROIBIDA: o defeito é o CARD. Reescreva O FIO, "
                  "registre, e rode `fio-reescrito`." % (d["spec"], d["rodada"]))
            return 2
        d["rodada"] += 1
        _gravar(d)
        print("rodada %d de %d autorizada" % (d["rodada"], TETO_DE_RODADAS))
    elif a.acao == "fio-reescrito":
        d["rodada"] = 0
        d["fios_reescritos"] += 1
        _gravar(d)
        print("FIO reescrito (%dª vez): rodadas zeradas" % d["fios_reescritos"])
    print("%s · rodada %d/%d · %.0f min de %d%s" % (
        d["spec"], d["rodada"], TETO_DE_RODADAS, corridos, d["faixa_min"],
        " · ⚠️ T2: passou de 1,5× a faixa — entregue o verde, o resto é handoff" if estourou else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
