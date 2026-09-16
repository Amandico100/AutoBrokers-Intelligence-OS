#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AAA FAST · a telemetria que o relatório cola (v12 §7).

Lê os transcritos reais do Claude Code (a sessão + os subagentes) e imprime, por agente:
turnos · contexto de pico · tokens de contexto processados (input + cache-write + cache-read) ·
saída · custo API-equivalente (US$) · relógio. E, por sessão, a linha do tempo em blocos de 30 min.

  python docs/canon/specs-propostas/AAA-FAST-medir-execucao.py --sessao atual
  python docs/canon/specs-propostas/AAA-FAST-medir-execucao.py --sessao a4546c6b --linha-do-tempo
  python docs/canon/specs-propostas/AAA-FAST-medir-execucao.py --listar

O número que o "Agent map" do Claude Code mostra por agente é o CONTEXTO FINAL, não o consumo.
Foi essa confusão que produziu "1,45 M / 2,9 M tokens" nos relatórios das EXTRA-001.x.
O consumo é turnos x contexto; é isto que este script mede.

Preços de API usados como régua comparável (US$ por milhão: input, cache-write, cache-read, output).
O plano de assinatura não cobra em dólar, mas pesa as mesmas grandezas.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
from collections import Counter, defaultdict

PROJETO = "c--Users-amand-Projetos-AUTOBROKERS-RESULTA-AutoBrokers-FIX"
ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects", PROJETO)
PRECO = {
    "opus": (5, 6.25, 0.5, 25),
    "fable": (10, 12.5, 0.25, 50),
    "sonnet": (2, 2.5, 0.2, 10),
    "haiku": (1, 1.25, 0.1, 5),
}


def familia(modelo):
    m = (modelo or "").lower()
    for k in PRECO:
        if k in m:
            return k
    return "opus"


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def ler(caminho):
    st = dict(inicio=None, fim=None, turnos=0, inp=0, cw=0, cr=0, out=0, pico=0, usd=0.0,
              modelos=Counter(), ferramentas=Counter(), blocos=defaultdict(lambda: [0, 0.0]))
    vistos = set()
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for linha in f:
            try:
                o = json.loads(linha)
            except ValueError:
                continue
            if o.get("type") != "assistant":
                continue
            m = o.get("message", {}) or {}
            u = m.get("usage") or {}
            for b in m.get("content", []) or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    st["ferramentas"][b.get("name")] += 1
            if not u or m.get("id") in vistos:  # o usage repete por bloco de conteúdo: conta 1x por mensagem
                continue
            vistos.add(m.get("id"))
            t = ts(o["timestamp"])
            st["inicio"] = st["inicio"] or t
            st["fim"] = t
            i = u.get("input_tokens", 0)
            cw = u.get("cache_creation_input_tokens", 0)
            cr = u.get("cache_read_input_tokens", 0)
            ou = u.get("output_tokens", 0)
            st["turnos"] += 1
            st["inp"] += i
            st["cw"] += cw
            st["cr"] += cr
            st["out"] += ou
            st["pico"] = max(st["pico"], i + cw + cr)
            p = PRECO[familia(m.get("model"))]
            st["modelos"][m.get("model")] += 1
            st["usd"] += (i * p[0] + cw * p[1] + cr * p[2] + ou * p[3]) / 1e6
            bloco = t.replace(minute=0 if t.minute < 30 else 30, second=0, microsecond=0)
            st["blocos"][bloco][0] += 1
            st["blocos"][bloco][1] += i + cw + cr
    return st


def imprimir_linha(st, rotulo):
    dur = (st["fim"] - st["inicio"]).total_seconds() / 60 if st["inicio"] else 0
    ctx = st["inp"] + st["cw"] + st["cr"]
    modelo = ",".join(k.replace("claude-", "") for k in st["modelos"] if k and not k.startswith("<"))
    inicio = st["inicio"].strftime("%d/%m %H:%M") if st["inicio"] else ""
    print("%-44s %-11s %6.0f min  turnos %4d  pico %5.0fk  ctx %6.1fM  saida %5.0fk  US$ %7.2f  %s" % (
        rotulo[:44], inicio, dur, st["turnos"], st["pico"] / 1e3, ctx / 1e6, st["out"] / 1e3, st["usd"], modelo))


def sessao_atual():
    arquivos = [f for f in glob.glob(os.path.join(ROOT, "*.jsonl")) if os.path.getsize(f) > 0]
    if not arquivos:
        sys.exit("nenhuma sessao em " + ROOT)
    return os.path.basename(max(arquivos, key=os.path.getmtime))[:-6]


def resolver(prefixo):
    if prefixo == "atual":
        return sessao_atual()
    c = glob.glob(os.path.join(ROOT, prefixo + "*.jsonl"))
    if len(c) != 1:
        sys.exit("sessao %r: %d candidatas" % (prefixo, len(c)))
    return os.path.basename(c[0])[:-6]


def medir(sess, linha_do_tempo=False):
    print("=" * 150)
    print("SESSAO", sess, "  (UTC)")
    principal = ler(os.path.join(ROOT, sess + ".jsonl"))
    imprimir_linha(principal, "EXECUTOR (sessao principal)")
    total = dict(usd=principal["usd"], ctx=principal["inp"] + principal["cw"] + principal["cr"],
                 out=principal["out"], turnos=principal["turnos"])
    subs = []
    for s in glob.glob(os.path.join(ROOT, sess, "subagents", "agent-*.jsonl")):
        meta = {}
        try:
            with open(s[:-6] + ".meta.json", encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            pass
        st = ler(s)
        chave = st["inicio"] or dt.datetime.max.replace(tzinfo=dt.timezone.utc)
        subs.append((chave, meta.get("description") or os.path.basename(s), st))
    for _, rotulo, st in sorted(subs, key=lambda r: r[0]):
        imprimir_linha(st, "  agente . " + rotulo)
        total["usd"] += st["usd"]
        total["ctx"] += st["inp"] + st["cw"] + st["cr"]
        total["out"] += st["out"]
        total["turnos"] += st["turnos"]
    print("TOTAL  agentes alem do executor: %d  .  turnos %d  .  ctx %.1fM  .  saida %.2fM  .  US$ %.2f" % (
        len(subs), total["turnos"], total["ctx"] / 1e6, total["out"] / 1e6, total["usd"]))
    top = principal["ferramentas"].most_common(6)
    print("ferramentas do executor:", ", ".join("%s %d" % (k, v) for k, v in top))
    if linha_do_tempo:
        blocos = defaultdict(lambda: [0, 0, 0.0])
        for b, (n, c) in principal["blocos"].items():
            blocos[b][0] += n
            blocos[b][2] += c
        for _, _, st in subs:
            for b, (n, c) in st["blocos"].items():
                blocos[b][1] += n
                blocos[b][2] += c
        print("\nbloco (UTC)        executor  agentes   ctx-tokens")
        for b in sorted(blocos):
            n1, n2, c = blocos[b]
            print("%s       %4d    %5d   %8.1fM" % (b.strftime("%d/%m %H:%M"), n1, n2, c / 1e6))


def listar():
    for f in sorted(glob.glob(os.path.join(ROOT, "*.jsonl")), key=os.path.getmtime):
        if os.path.getsize(f) == 0:
            continue
        sess = os.path.basename(f)[:-6]
        n = len(glob.glob(os.path.join(ROOT, sess, "subagents", "agent-*.jsonl")))
        quando = dt.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d/%m %H:%M")
        print("%s  %6.1f MB  %s  agentes %d" % (sess, os.path.getsize(f) / 1e6, quando, n))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sessao", action="append", help="'atual' ou o prefixo do id da sessao (repetivel)")
    ap.add_argument("--linha-do-tempo", action="store_true")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()
    if a.listar or not a.sessao:
        listar()
    for s in a.sessao or []:
        medir(resolver(s), a.linha_do_tempo)
