# -*- coding: utf-8 -*-
"""SPEC-116 U11 — a BANCADA E2E pela linha de comando.

Roda o MOTOR REAL de um papel com um ou mais BRAÇOS (provider:model[:effort])
sobre o corpus mascarado (`tests/corpus/bancada/<papel>/casos.jsonl`), k vezes,
e imprime por braço: pass@1 · pass^k · pass^k do subconjunto crítico · custo por
sucesso · p50/p95 · acerto de tool/args · efeitos duplicados · recuperação após
falha · BLOCKED_BY_INFRA.

    cd backend
    # linha de controle (CLAUDE.md §9.2): o relatório TEM de separar os dois
    python scripts/bancada.py --papel atendimento --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
    # braço real (depois da costura F5b), só o subconjunto crítico, com teto
    python scripts/bancada.py --papel atendimento --braco anthropic:claude-sonnet-5-5:medium --critico --k 3 --teto-usd 5 --gravar
    # a costura (F5b): 2 braços reais + a linha de controle no MESMO grupo
    python scripts/bancada.py --papel atendimento --nivel N1 --braco anthropic:claude-sonnet-5-5:low --braco openai:gpt-6-luna:low --k 1 --casos atd-n1-cpf-guincho,atd-n1-humano-cancelar --gravar --teto-usd 0.50 --por-caso
    python scripts/bancada.py --papel atendimento --nivel N1 --braco dublê:perfeito --braco dublê:burro --k 1 --casos atd-n1-cpf-guincho,atd-n1-humano-cancelar --gravar --grupo <o grupo acima>
    # ler de novo um relatório
    python scripts/bancada.py --relatorio <grupo_bancada | arquivo.json>
    # carregar o corpus na Eval Fabric (datasets/versões/casos; idempotente)
    python scripts/bancada.py --carregar-corpus --gravar
    # SPEC-122 F1 — o CÉREBRO (variante V0..V3), teto POR PROVEDOR lido do ledger:
    python scripts/bancada.py --papel cerebro --variante V1 --braco anthropic:claude-opus-5-5 --k 1         --teto-provedor 1.90 --ledger-desde 2026-09-30T00:00:00+00:00 --saida tests/corpus/bancada/RESULTADOS/x.json
    python scripts/bancada.py --resumo-cerebro tests/corpus/bancada/RESULTADOS/cerebro_*.json
    # SPEC-123 F2a — o DESTRAVADOR (o MESMO prompt para todo braço; 2ª opinião de OUTRO provedor;
    # teto POR PROVEDOR lido do ledger e relido durante a rodada):
    python scripts/bancada.py --papel destravador --braco openai:gpt-6.1-sol:high --braco-segunda anthropic:claude-sonnet-5-5 --k 1 --so-grupo T --so-grupo D --teto-provedor 1.60 --ledger-desde 2026-09-30T00:00:00+00:00 --saida tests/corpus/bancada/RESULTADOS/destravador_x.json
    python scripts/bancada.py --resumo-destravador "tests/corpus/bancada/RESULTADOS/destravador_*.json"
    # F5a — re-julgar sem modelo (e, com --redecidir, pela política de hoje):
    python scripts/bancada.py --resumo-destravador "tests/corpus/bancada/RESULTADOS/destravador_R*.json" --recalcular

    # SPEC-124 F2 — a VISÃO com gabarito por campo (o teto da FATIA = só as linhas details.papel='visao'):
    python scripts/bancada.py --papel visao_campos --braco openai:gpt-6-luna:medium --k 1 --teto-provedor 0.45 --ledger-desde 2026-10-01T00:00:00+00:00 --ledger-papel visao --saida <scratch>/visao_luna.json
    python scripts/bancada.py --resumo-visao "<scratch>/visao_*.json"

    # SPEC-125 S0 — a CONVERSA (segurado simulado ⇄ agente de atendimento REAL; teto = ledger details.papel='conversa'):
    python scripts/bancada.py --papel conversa --braco openai:gpt-6-luna:low --braco-segurado openai:gpt-6-luna:low --cenarios C14 --k 1 --teto-provedor 0.05 --ledger-desde 2026-10-01T00:00:00+00:00 --saida <scratch>/conv.json
    python scripts/bancada.py --resumo-conversa "<scratch>/conv*.json" [--recalcular]

`--ensaio` (padrão) NÃO toca o banco: grava só um JSON local e diz onde.
`--gravar` escreve em `eval_runs`/`eval_case_results` (exige a migration
20260923_03 aplicada). O teto em US$ vem de `--teto-usd` ou de BANCADA_TETO_USD
(padrão 100) e é conferido ANTES de cada chamada ao modelo; braço sem preço no
catálogo é RECUSADO (a bancada não inventa preço).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Bancada E2E da SPEC-116 (Eval Fabric estendida).")
    p.add_argument("--papel", help="atendimento · chat_principal · cobranca · portal_decisao · dispatch · "
                                   "memoria · visao · hyde · extrator_planos · juiz · transcricao")
    p.add_argument("--braco", action="append", default=[],
                   help="provider:model[:effort] (repetível). `dublê:perfeito` e `dublê:burro` = linha de controle")
    p.add_argument("--k", type=int, default=3, help="tentativas por caso (pass^k)")
    p.add_argument("--nivel", default="N1", choices=("N1", "N2"))
    p.add_argument("--casos", default=None, help="filtro por trecho da chave do caso (vários: separados por vírgula)")
    p.add_argument("--grupo", default=None, help="grupo_bancada a reusar (ex.: pôr a linha de controle no MESMO grupo dos braços reais)")
    p.add_argument("--por-caso", action="store_true", help="imprime uma linha por tentativa (resultado, custo, tokens, latência)")
    p.add_argument("--critico", action="store_true", help="só o subconjunto crítico")
    p.add_argument("--teto-usd", type=float, default=None, help="teto de gasto da rodada (padrão: env BANCADA_TETO_USD ou 100)")
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--gravar", action="store_true", help="grava em eval_runs/eval_case_results")
    modo.add_argument("--ensaio", action="store_true", help="(padrão) nada no banco; só relatório local em JSON")
    p.add_argument("--saida", default=None, help="caminho do JSON local (modo ensaio)")
    p.add_argument("--relatorio", default=None, help="reimprime a tabela de um grupo_bancada ou de um arquivo .json")
    p.add_argument("--carregar-corpus", action="store_true", help="corpus → eval_datasets/versions/cases")
    p.add_argument("--verboso", action="store_true")
    p.add_argument("--variante", default=None, help="SPEC-122: V0 (prompt de hoje) · V1 (+saída estruturada) · "
                                                    "V2 (+contexto) · V3 (+conteúdo) — só no papel cerebro")
    p.add_argument("--teto-provedor", type=float, default=None,
                   help="SPEC-122: teto em US$ do PROVEDOR do braço, descontado o que o ledger "
                        "(token_usage_logs, service_type='bancada') já registrou desde --ledger-desde")
    p.add_argument("--ledger-desde", default=None, help="início da conta do ledger (ISO 8601)")
    p.add_argument("--resumo-cerebro", nargs="+", default=None, help="SPEC-122: tabela braço × variante de JSONs")
    # SPEC-123 F2a — o DESTRAVADOR
    p.add_argument("--braco-segunda", default=None,
                   help="SPEC-123: provider:model do braço da 2ª OPINIÃO (papel destravador; OUTRO provedor)")
    p.add_argument("--so-grupo", action="append", default=[], help="SPEC-123: T · D · A · B (repetível)")
    p.add_argument("--resumo-destravador", nargs="+", default=None,
                   help="SPEC-123: métricas por braço (acerto, graves, faixas de nota, limiar, 2ª opinião, G4)")
    p.add_argument("--recalcular", action="store_true",
                   help="SPEC-123 F5a: com --resumo-destravador, RE-JULGA cada resultado gravado pelo juiz e o "
                        "gabarito de hoje (sem modelo; os arquivos não mudam)")
    p.add_argument("--ledger-papel", default=None,
                   help="SPEC-124: com --teto-provedor, conta no ledger SÓ as linhas da bancada com "
                        "details.papel = este (o teto de UMA fatia; relido durante a rodada)")
    p.add_argument("--resumo-visao", nargs="+", default=None,
                   help="SPEC-124: acerto por campo, custo/documento e latência por braço (papel visao_campos)")
    # SPEC-125 S0 — a CONVERSA
    p.add_argument("--cenarios", default=None, help="SPEC-125: ids dos cenários da conversa (C1,C13,R1) ou trechos da chave")
    p.add_argument("--braco-segurado", default=None,
                   help="SPEC-125: provider:model[:effort] do SEGURADO SIMULADO e do juiz barato "
                        "(padrão openai:gpt-6-luna:low; `duble:burro` = só as falas fixas, sem juiz LLM)")
    p.add_argument("--agente-id", default=None,
                   help="SPEC-125: usa o prompt REAL deste agente (SELECT, fora da borda; nunca liga) no lugar do molde")
    p.add_argument("--resumo-conversa", nargs="+", default=None,
                   help="SPEC-125: pass@1/pass^k, falhas por checagem, nota do juiz, custo agente × segurado")
    p.add_argument("--redecidir", action="store_true",
                   help="SPEC-123 F5a: com --recalcular, passa a proposta gravada de novo pela POLÍTICA de hoje")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO if a.verboso else logging.CRITICAL)
    if not a.verboso:
        logging.disable(logging.WARNING)

    # As chaves dos provedores e do banco moram no .env (como no app/main.py).
    # ⛔ Nunca impressas; `override=False`: o ambiente de quem chama vence.
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(RAIZ, ".env"), override=False)
    except ImportError:  # pragma: no cover
        pass

    from app.services.evals import bancada as B

    if a.relatorio:
        if os.path.exists(a.relatorio):
            print(B.relatorio_de_arquivo(a.relatorio))
        else:
            print(B.relatorio_do_banco(a.relatorio))
        return 0

    if a.resumo_cerebro:
        import glob
        import json as _json

        arqs = sorted({f for padrao in a.resumo_cerebro for f in glob.glob(padrao)})
        resumo = B.resumo_do_cerebro(arqs)
        print(B.tabela_do_cerebro(resumo))
        for rot, m in resumo.items():
            if m["graves"] or m["graves_do_modelo_nu"]:
                print(f"\n{rot}\n  GRAVES (depois do parser/conferente): {m['graves'] or '—'}"
                      f"\n  graves do modelo NU (antes de D3):    {m['graves_do_modelo_nu'] or '—'}")
        if a.saida:
            Path(a.saida).write_text(_json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    if a.resumo_visao:
        import glob
        import json as _json

        arqs = sorted({f for padrao in a.resumo_visao for f in glob.glob(padrao)})
        resumo = B.resumo_da_visao(arqs, rejulgar=bool(a.recalcular))
        if a.recalcular:
            print("RE-JULGADO sem modelo: juiz e gabarito de hoje sobre as respostas gravadas")
        print(B.tabela_da_visao(resumo))
        if a.saida:
            Path(a.saida).write_text(_json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    if a.resumo_conversa:
        import glob
        import json as _json

        arqs = sorted({f for padrao in a.resumo_conversa for f in glob.glob(padrao)})
        resumo = B.resumo_da_conversa(arqs, rejulgar=bool(a.recalcular))
        if a.recalcular:
            print("RE-JULGADO sem modelo: as checagens de hoje sobre as transcrições gravadas")
        print(B.tabela_da_conversa(resumo))
        if a.saida:
            Path(a.saida).write_text(_json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    if a.resumo_destravador:
        import glob
        import json as _json

        arqs = sorted({f for padrao in a.resumo_destravador for f in glob.glob(padrao)})
        if a.recalcular or a.redecidir:
            arqs = B.recalcular_destravador(arqs, redecidir=bool(a.redecidir))
            print("RECALCULADO sem modelo: juiz e gabarito de hoje"
                  + (" + a POLÍTICA de hoje sobre a proposta gravada" if a.redecidir else ""))
        resumo = B.resumo_do_destravador(arqs)
        print(B.tabela_do_destravador(resumo))
        pd = B.prompts_divergentes(arqs)
        print(f"\nMESMO PROMPT (D4): {pd['casos']} casos · {len(pd['divergentes'])} com system DIFERENTE entre braços"
              + (f": {', '.join(pd['divergentes'][:10])}" if pd["divergentes"] else ""))
        if a.saida:
            Path(a.saida).write_text(_json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    if a.carregar_corpus:
        info = B.carregar_corpus(gravar=bool(a.gravar))
        for papel, i in info.items():
            print(f"{papel:<16} v{i['versao']}  casos={i['casos']:<3} novos={i['novos']:<3} "
                  f"divergentes={i['divergentes']}" + ("" if a.gravar else "  (ensaio: nada gravado)"))
        return 0

    if not a.papel or not a.braco:
        p.error("--papel e ao menos um --braco são obrigatórios (ou use --relatorio / --carregar-corpus)")

    teto = a.teto_usd
    orcamentos = None
    if a.papel == "conversa":
        return _rodar_conversa(a, p, B)
    if a.papel == "destravador":
        # 🔴 SPEC-123: o teto é POR PROVEDOR (o do braço E o da 2ª opinião), lido do LEDGER e relido
        #    durante a rodada (`OrcamentoDoLedger`) — a rodada para SOZINHA antes de estourar.
        if a.teto_provedor is None or not a.ledger_desde:
            p.error("--papel destravador exige --teto-provedor e --ledger-desde (o teto do Founder é por provedor)")
        provs = {B.Braco.de(x).provider for x in a.braco}
        if a.braco_segunda:
            b2 = B.Braco.de(a.braco_segunda)
            if b2.provider in provs and not b2.e_duble:
                p.error("a 2ª opinião tem de ser de OUTRO provedor (D3 do Founder)")
            provs.add(b2.provider)
        orcamentos = {}
        for prov in sorted(provs):
            if prov == "duble":
                continue
            o = B.OrcamentoDoLedger(prov, a.teto_provedor, a.ledger_desde)
            print(f"ledger {prov} desde {a.ledger_desde}: US$ {o.inicial:.4f} · teto {a.teto_provedor:.2f} · "
                  f"resta {o.teto_usd:.4f}")
            if o.teto_usd <= 0:
                print(f"⛔ teto do provedor {prov} já atingido no ledger — nada roda")
                return 2
            orcamentos[prov] = o
        rel = B.rodar_bancada(a.papel, a.braco, k=a.k, nivel=a.nivel, gravar=bool(a.gravar),
                              teto_usd=teto if teto is not None else 100.0, filtro=a.casos,
                              grupo_bancada=a.grupo, segunda=a.braco_segunda, orcamentos=orcamentos,
                              grupos=a.so_grupo or None)
        print(rel.tabela())
        if a.por_caso:
            for r in rel.resultados:
                v = (r.rastro.get("estado") or {}).get("veredito_destravador") or {}
                print(f"  {r.braco:<30} {r.chave:<44} t{r.tentativa} {v.get('classe', r.resultado):<16} "
                      f"acao={v.get('acao_final')} nota={v.get('nota')} US$ {r.custo_usd:.5f} {r.latencia_ms} ms"
                      + (f" · {r.erro[:120]}" if r.erro else ""))
        print(f"\ngrupo_bancada: {rel.grupo_bancada} · tentativas: {len(rel.resultados)}")
        print(f"ensaio (nada no banco) · relatório local: {rel.salvar(a.saida)}")
        return 2 if rel.parada and rel.parada.startswith("teto_usd") else 0
    if a.teto_provedor is not None:
        # 🔴 lei do Founder (SPEC-122): US$ por PROVEDOR, lido do LEDGER, parando sozinho
        provs = {B.Braco.de(x).provider for x in a.braco}
        if len(provs) != 1 or not a.ledger_desde:
            p.error("--teto-provedor exige braços de UM provedor e --ledger-desde")
        prov = provs.pop()
        if a.ledger_papel:
            # 🔴 SPEC-124: o teto da FATIA — só o que ela gastou (details.papel), relido a cada 10 reservas
            # o cliente do LEDGER é capturado AQUI, fora da borda (a releitura roda DENTRO de
            # `dubles.borda_isolada`, onde `get_supabase_client` é o dublê — a lição da F5a da 123)
            from app.core.database import get_supabase_client

            cli_ledger = get_supabase_client()
            o = B.OrcamentoDoLedger(prov, a.teto_provedor, a.ledger_desde,
                                    ler=lambda pv, d: B.gasto_do_ledger_do_papel(pv, d, a.ledger_papel,
                                                                                 cliente=cli_ledger))
            print(f"ledger {prov} papel={a.ledger_papel} desde {a.ledger_desde}: US$ {o.inicial:.4f} · "
                  f"teto {a.teto_provedor:.2f} · resta {o.teto_usd:.4f}")
            if o.teto_usd <= 0:
                print("⛔ teto da fatia já atingido no ledger — nada roda")
                return 2
            rel = B.rodar_bancada(a.papel, a.braco, k=a.k, nivel=a.nivel, gravar=bool(a.gravar),
                                  teto_usd=o.teto_usd, filtro=a.casos, critico=a.critico,
                                  grupo_bancada=a.grupo, orcamentos={prov: o})
            print(rel.tabela())
            for r in rel.resultados if a.por_caso else []:
                print(f"  {r.braco:<34} {r.chave:<34} t{r.tentativa} {r.resultado:<16} US$ {r.custo_usd:.6f} "
                      f"{r.latencia_ms} ms" + (f" · {r.erro[:140]}" if r.erro else ""))
            print(f"\ngrupo_bancada: {rel.grupo_bancada} · tentativas: {len(rel.resultados)}")
            print(f"ensaio (nada no banco) · relatório local: {rel.salvar(a.saida)}")
            return 2 if rel.parada and rel.parada.startswith("teto_usd") else 0
        gasto = B.gasto_do_ledger(prov, a.ledger_desde)
        resta = round(a.teto_provedor - gasto, 6)
        print(f"ledger {prov} desde {a.ledger_desde}: US$ {gasto:.4f} · teto {a.teto_provedor:.2f} · resta {resta:.4f}")
        if resta <= 0:
            print("⛔ teto do provedor já atingido no ledger — nada roda")
            return 2
        teto = resta if teto is None else min(teto, resta)
    rel = B.rodar_bancada(a.papel, a.braco, k=a.k, nivel=a.nivel, gravar=bool(a.gravar),
                          teto_usd=teto, filtro=a.casos, critico=a.critico, grupo_bancada=a.grupo,
                          variante=a.variante)
    print(rel.tabela())
    if a.por_caso:
        print()
        for r in rel.resultados:
            t = r.tokens or {}
            print(f"  {r.braco:<34} {r.chave:<40} t{r.tentativa} {r.resultado:<16} "
                  f"US$ {r.custo_usd:.6f} in={t.get('in', 0)} out={t.get('out', 0)} "
                  f"rac={t.get('raciocinio', 0)} {r.latencia_ms} ms · chamadas={r.rastro.get('chamadas_ao_modelo')}"
                  + (f" · {r.erro[:140]}" if r.erro else ""))
    print(f"\ngrupo_bancada: {rel.grupo_bancada} · casos: {len({r.chave for r in rel.resultados})} "
          f"· tentativas: {len(rel.resultados)}")
    if a.gravar:
        print(f"gravado: {len(rel.runs)} eval_run(s) — releia com --relatorio {rel.grupo_bancada}")
    else:
        print(f"ensaio (nada no banco) · relatório local: {rel.salvar(a.saida)}")
    return 2 if rel.parada and rel.parada.startswith("teto_usd") else 0


def _rodar_conversa(a, p, B) -> int:
    """SPEC-125 S0 — a conversa inteira. 🔴 O teto é POR PROVEDOR, lido do LEDGER (só `details.papel='conversa'`)
    com o cliente capturado AQUI, fora da borda de dublês, e relido durante a rodada: ela para sozinha."""
    if a.teto_provedor is None or not a.ledger_desde:
        p.error("--papel conversa exige --teto-provedor e --ledger-desde (o teto é lido do ledger)")
    seg = a.braco_segurado or B.BRACO_DO_SEGURADO_PADRAO
    casos = B.carregar_cenarios_da_conversa(a.cenarios or a.casos)
    if not casos:
        p.error("nenhum cenário casou com --cenarios")
    if a.agente_id:
        from app.core.database import get_supabase_client

        linha = (get_supabase_client().client.table("agents")
                 .select("agent_system_prompt, name, config, agent_role").eq("id", a.agente_id).limit(1).execute().data or [])
        if not linha or linha[0].get("agent_role") != "attendance":
            p.error("--agente-id: agente de atendimento não encontrado")
        for c in casos:
            c["entrada"]["agente"] = {k: linha[0].get(k) for k in ("agent_system_prompt", "name", "config")}
        print(f"prompt REAL do agente (só leitura): {len(linha[0].get('agent_system_prompt') or '')} chars")
    provs = {B.Braco.de(x).provider for x in a.braco} | {B.Braco.de(seg).provider}
    orcamentos = B.orcamentos_da_conversa(sorted(provs), a.teto_provedor, a.ledger_desde)
    for prov, o in orcamentos.items():
        print(f"ledger {prov} papel=conversa desde {a.ledger_desde}: US$ {o.inicial:.4f} · teto {a.teto_provedor:.2f} · "
              f"resta {o.teto_usd:.4f}")
        if o.teto_usd <= 0:
            print(f"⛔ teto do provedor {prov} já atingido no ledger — nada roda")
            return 2
    rel = B.rodar_bancada("conversa", a.braco, casos=casos, k=a.k, nivel="N3", gravar=False,
                          teto_usd=a.teto_provedor, grupo_bancada=a.grupo, segunda=seg, orcamentos=orcamentos)
    print(rel.tabela())
    for r in rel.resultados:
        est = (r.rastro.get("estado") or {})
        falhos = [v["evaluator_slug"] for v in r.vereditos if not v["passou"]]
        seg_c = (r.rastro.get("segunda") or {}).get("custo_usd") or 0
        print(f"  {r.braco:<30} {r.chave:<36} t{r.tentativa} {r.resultado:<16} turnos={len(est.get('transcricao') or [])} "
              f"US$ agente {r.custo_usd - seg_c:.5f} + segurado/juiz {seg_c:.5f} · {r.latencia_ms} ms"
              + (f" · falhou: {', '.join(falhos)}" if falhos else "") + (f" · {r.erro[:140]}" if r.erro else ""))
        if a.por_caso:
            for t in est.get("transcricao") or []:
                print(f"     t{t['turno']} SEGURADO: {' | '.join(t['segurado'])[:300]}")
                print(f"     t{t['turno']} AGENTE ({t['baloes']} balão/ões, tools={t['tools']}): {t['agente'][:500]}")
            if est.get("juiz_llm"):
                print(f"     JUIZ LLM: {est['juiz_llm'].get('resumo')}")
    for prov, o in orcamentos.items():
        print(f"ledger {prov} papel=conversa, RELIDO depois da rodada: US$ {float(o.ler(prov, a.ledger_desde)):.6f}")
    print(f"\ngrupo_bancada: {rel.grupo_bancada} · tentativas: {len(rel.resultados)}")
    print(f"ensaio (nada no banco) · relatório local: {rel.salvar(a.saida)}")
    return 2 if rel.parada and rel.parada.startswith("teto_usd") else 0


if __name__ == "__main__":
    sys.exit(main())
