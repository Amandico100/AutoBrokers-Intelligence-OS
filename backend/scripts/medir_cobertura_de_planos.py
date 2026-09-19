# -*- coding: utf-8 -*-
"""📊 A régua do BLOCO E — as TRÊS contagens que é tentador juntar.

SPEC-EXTRA-001.5 §9. Rodar de dentro de `backend/`:

    PYTHONIOENCODING=utf-8 python scripts/medir_cobertura_de_planos.py

🔴 POR QUE TRÊS, E NÃO UMA
===========================
```
seguradoras com CG na base   !=   com PLANO publicado   !=   que a corretora USA
```

São três conjuntos diferentes e a diferença entre eles é o trabalho que falta:

* ter a **condição geral indexada** é ter o PDF no acervo. Não é saber o que o
  plano cobre — ninguém leu a tabela ainda.
* ter **plano publicado** é ter a linha revisada por gente, com documento e
  página. É a única das três que responde ao segurado.
* o que a **corretora usa** é a carteira viva. É o denominador: cobrir 100 % de
  quem não aparece na carteira não vale nada.

Juntar as três numa só ("temos 8 seguradoras") produz o número que engana para
cima — e é o defeito que M-D1 guarda do outro lado (contar linhas em vez de
seguradora × ramo).

⛔ Somente SELECT. Nada é escrito.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(".env")

# 🔴 SPEC-EXTRA-001.5.1 (A-bis): o catálogo mora DENTRO do pacote, e quem
# diz onde é o resolvedor do provider — nunca um `parents[n]` escrito aqui.
# Um segundo caminho próprio volta a ler `docs/`, que não existe na imagem.
from app.providers.susep_ses_provider import CAMINHO_DO_MAPA  # noqa: E402

CENSO = Path(CAMINHO_DO_MAPA)

SQL_CG = (
    "select count(distinct insurer_key) from normative_documents "
    "where coalesce(chunk_count,0) > 0 and insurer_key <> 'susep'"
)
SQL_CG_LISTA = (
    "select distinct insurer_key from normative_documents "
    "where coalesce(chunk_count,0) > 0 and insurer_key <> 'susep' order by 1"
)


def _conectar():
    import psycopg

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("⛔ SUPABASE_DB_URL ausente do ambiente. Nada medido.")
        sys.exit(2)
    return psycopg.connect(url, prepare_threshold=None)


def main() -> int:
    from app.services.knowledge import assistance_plans_base as BASE

    print("=" * 78)
    print("📊 COBERTURA DA BASE DE PLANOS — 3 contagens, 3 perguntas diferentes")
    print("=" * 78)

    # ------------------------------------------------------------------ ①
    with _conectar() as c:
        (com_cg,) = c.execute(SQL_CG).fetchone()
        lista_cg = [r[0] for r in c.execute(SQL_CG_LISTA).fetchall()]
    print("\n① seguradoras com CONDIÇÃO GERAL indexada (o PDF está no acervo)")
    print(f"   📊 {com_cg}")
    print(f"   query: {SQL_CG}")
    print(f"   quem:  {', '.join(lista_cg) or '—'}")

    # ------------------------------------------------------------------ ②
    print("\n② seguradoras com PLANO PUBLICADO (linha revisada, com documento e página)")
    try:
        cobertura = BASE.cobertura_por_seguradora_e_ramo()
    except Exception as exc:  # noqa: BLE001
        print(f"   ⛔ base indisponível: {type(exc).__name__} — {exc}")
        cobertura = {}
    seguradoras_com_plano = sorted({k[0] for k in cobertura})
    pares = sorted(cobertura)
    print(f"   📊 {len(seguradoras_com_plano)} seguradora(s) · {len(pares)} par(es) seguradora × ramo")
    print("   query: assistance_plans_base.cobertura_por_seguradora_e_ramo() "
          "(select .. from insurer_assistance_plans where curadoria='publicado')")
    print("   🔴 conta seguradora × RAMO, nunca LINHAS: 40 linhas de um ramo só "
          "não são cobertura, são um ramo só bem descrito (M-D1)")
    for (chave, ramo), n in sorted(cobertura.items()):
        print(f"     - {chave} · {ramo}: {n['planos_publicados']} plano(s) · "
              f"{n['servicos_publicados']} serviço(s)")
    if not cobertura:
        print("     (nenhuma — a base nasce vazia; é o BLOCO C que a preenche)")

    # ------------------------------------------------------------------ ③
    print("\n③ seguradoras que a CORRETORA USA (a carteira viva — o denominador)")
    with open(CENSO, "r", encoding="utf-8") as fh:
        censo = json.load(fh)
    placar = censo.get("placar_das_siglas") or {}
    siglas = censo.get("siglas") or {}
    print(f"   📊 {placar.get('siglas_no_censo')} siglas no censo "
          f"({placar.get('cobertura_de_premio_pct')}% do prêmio medido)")
    print(f"   fonte: {CENSO.relative_to(RAIZ.parent)} (`placar_das_siglas`)")
    print(f"   medido com: {placar.get('medido_com')}")

    # 🔴 O CRUZAMENTO PASSA PELA MESMA NORMALIZAÇÃO DOS DOIS LADOS.
    #
    # 📊 18/09/2026: sem isto, o cruzamento dava 6/2/8 onde o certo é 7/1/7.
    # O censo guarda `tokio_marine` e `seguros_unimed`; a base guarda `tokio` e
    # `unimed`. Comparar as duas grafias faz a Tokio aparecer como "carteira sem
    # CG" — e ela é a seguradora cujo documento já está no acervo. É o defeito
    # de dialeto de CLAUDE.md §9.4, aqui num painel: o número sai errado sem
    # nenhum erro aparecer.
    canonicas = set()
    nao_normalizadas = []
    for v in siglas.values():
        if not (isinstance(v, dict) and v.get("canonica")):
            continue
        bruta = str(v["canonica"])
        try:
            canonicas.add(BASE.chave_de_conhecimento(bruta))
        except BASE.SeguradoraDesconhecida:
            nao_normalizadas.append(bruta)
    canonicas = sorted(canonicas)
    if nao_normalizadas:
        print(f"   ⚠️ {len(nao_normalizadas)} canônica(s) do censo que a base não "
              f"reconhece: {sorted(set(nao_normalizadas))}")
    print(f"   📊 {len(canonicas)} chave(s) canônica(s) distinta(s) por trás das "
          f"{len(siglas)} siglas")

    # ------------------------------------------------------------- o cruzamento
    print("\n" + "-" * 78)
    print("🔴 O CRUZAMENTO — e por que as três NÃO se somam")
    # e o mesmo dialeto do outro lado: `lista_cg` vem do banco, cru.
    cg = set()
    for bruta in lista_cg:
        try:
            cg.add(BASE.chave_de_conhecimento(bruta))
        except BASE.SeguradoraDesconhecida:
            continue
    carteira = set(canonicas)
    plano = set(seguradoras_com_plano)
    print(f"   CG ∩ carteira ......... {len(cg & carteira):>3}  {sorted(cg & carteira)}")
    print(f"   CG fora da carteira ... {len(cg - carteira):>3}  {sorted(cg - carteira)}")
    print(f"   carteira sem CG ....... {len(carteira - cg):>3}")
    print(f"   com PLANO publicado ... {len(plano):>3}  {sorted(plano)}")
    print(f"   ⚠️ 'CG fora da carteira' não é erro: a base é GLOBAL (D-PILOTO-01).")
    print(f"   ⚠️ 'carteira sem CG' é a FILA do BLOCO C, por tamanho de carteira.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
