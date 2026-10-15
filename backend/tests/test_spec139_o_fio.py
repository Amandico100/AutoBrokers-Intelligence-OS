# modelo: claude-opus-5-5
"""SPEC-139 · O FIO, lado do banco: o que a migration 20261016_01 gravou é o que o CATÁLOGO lê, e chega limpo à loja.

O fio (SPEC §2) começa no banco: `catalogoDaCorretora` (lib/auxiliaries/catalog.ts) lê `auxiliary_templates` com as
colunas de `COLUNAS_DO_TEMPLATE` + `cover_url, faq, featured_rank`, filtrando `status = 'active'` e `is_active`. Este
teste roda ESSA consulta — as colunas e os filtros são lidos do próprio catalog.ts, nunca reescritos aqui — no banco de
produção, só leitura (`SET TRANSACTION READ ONLY`, só SELECT; a URL nunca é impressa), e confere:

  1. os 15 aplicativos que a migration tocou (lidos do ROLLBACK dela) chegam com Dúvidas bem formadas;
  2. nenhuma frase que a tela mostra fala como máquina ("Este auxiliar", "dry-run", "MVP", "Founder", "endpoint"…);
     "auxiliar de seguros" é o OFÍCIO de uma pessoa (a descrição da Digitação Zero) e não conta;
  3. todo aplicativo que a loja mostra tem a linha dele na paleta das capas (capas/paleta.ts) com o MESMO ícone;
  4. o "Em breve" é decisão, não conteúdo: 9 disponíveis e 9 em breve, como o VERIFY da migration mediu.

LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): as mesmas regras rodam sobre os textos de ANTES (os literais do ROLLBACK da
migration) e TÊM de reprovar — é o que prova que a régua consegue ficar vermelha.

Sem SUPABASE_DB_URL (backend/.env ou ambiente) o teste do banco é PULADO, nunca verde por omissão.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "lib" / "auxiliaries" / "catalog.ts"
PALETA = RAIZ / "components" / "aplicativos" / "casca" / "capas" / "paleta.ts"
MIGRATION = RAIZ / "backend" / "supabase" / "migrations" / "20261016_01_spec139_conteudo_dos_aplicativos.sql"

# o jargão que a migration tirou (o mesmo do VERIFY dela) + "auxiliar" solto
JARGAO = re.compile(
    r"(Este auxiliar|Auxiliar que|Auxiliar read-only|dry-run|\bMVP\b|Founder|espelho da carteira|endpoint|Regulatorio"
    r"|\bauxiliar(?:es)?\b(?! de seguros))",
    re.IGNORECASE,
)
COLUNAS_DE_TEXTO = ("name", "headline", "short_description", "description", "value_promise", "missing_for_launch", "what_it_does")


# ── o que o catálogo lê (do PRÓPRIO catalog.ts) ──────────────────────────────────────────────────────────────────────
def consulta_do_catalogo() -> tuple[list[str], list[tuple[str, str]]]:
    fonte = CATALOGO.read_text(encoding="utf-8")
    m = re.search(r"const COLUNAS_DO_TEMPLATE =\s*((?:'[^']*'\s*\+?\s*)+);", fonte)
    assert m, "COLUNAS_DO_TEMPLATE não encontrado no catalog.ts"
    colunas = [c.strip() for c in "".join(re.findall(r"'([^']*)'", m.group(1))).split(",") if c.strip()]
    novo = re.search(r"\.select\(`\$\{COLUNAS_DO_TEMPLATE\}, ([^`]+)`\)\s*((?:\.eq\('[a-z_]+', [^)]+\)\s*)+)", fonte)
    assert novo, "a leitura com as colunas novas (cover_url, faq…) não está no catalog.ts"
    colunas += [c.strip() for c in novo.group(1).split(",")]
    filtros = re.findall(r"\.eq\('([a-z_]+)', ([^)]+)\)", novo.group(2))
    return colunas, [(c, v.strip()) for c, v in filtros]


def slugs_da_migration() -> list[str]:
    sql = MIGRATION.read_text(encoding="utf-8")
    m = re.search(r"set faq = null, updated_at = now\(\)\s*--\s*where slug in \(([\s\S]*?)\);", sql)
    assert m, "o ROLLBACK da migration não lista os slugs do faq"
    return re.findall(r"'([a-z0-9-]+)'", m.group(1))


def textos_de_antes() -> list[str]:
    """Os literais que o ROLLBACK devolve — os textos de 15/10, ANTES da migration."""
    sql = MIGRATION.read_text(encoding="utf-8")
    rollback = sql.split("-- ROLLBACK", 1)[1]
    return [t.replace("''", "'") for t in re.findall(r"=\s*E?'((?:[^']|'')+)'", rollback)]


def paleta_das_capas() -> dict[str, str]:
    fonte = PALETA.read_text(encoding="utf-8")
    bloco = fonte.split("export const PALETA", 1)[1].split("\n};", 1)[0]
    return dict(re.findall(r"'?([a-z0-9-]+)'?:\s*\{\s*icone:\s*'([A-Za-z]+)'", bloco))


# ── as regras (puras: rodam sobre o banco E sobre o controle) ──────────────────────────────────────────────────────
def frases_de_maquina(linhas: list[dict]) -> list[str]:
    achados = []
    for l in linhas:
        for col in COLUNAS_DE_TEXTO:
            v = l.get(col)
            texto = v if isinstance(v, str) else (str(v) if v is not None else "")
            m = JARGAO.search(texto)
            if m:
                achados.append(f"{l['slug']}.{col}: {m.group(0)!r}")
    return achados


def duvidas_ruins(linhas: list[dict], slugs: list[str]) -> list[str]:
    por_slug = {l["slug"]: l for l in linhas}
    ruins = []
    for s in slugs:
        faq = (por_slug.get(s) or {}).get("faq") or []
        if not faq:
            ruins.append(f"{s}: sem dúvida")
        elif not all(isinstance(d, dict) and isinstance(d.get("pergunta"), str) and d["pergunta"].endswith("?")
                     and isinstance(d.get("resposta"), str) and d["resposta"].strip() for d in faq):
            ruins.append(f"{s}: dúvida malformada")
    return ruins


def test_a_regua_le_o_catalogo_e_a_migration():
    colunas, filtros = consulta_do_catalogo()
    assert {"slug", "icon", "faq", "cover_url", "headline", "description", "missing_for_launch"} <= set(colunas), colunas
    assert ("status", "'active'") in filtros and ("is_active", "true") in filtros, filtros
    slugs = slugs_da_migration()
    assert len(slugs) == 15 and "quem-cobra-menos" not in slugs and "renovacao" not in slugs, slugs
    assert len(paleta_das_capas()) == 18


def test_controle_os_textos_de_antes_reprovam():
    """§9.3: a régua CONSEGUE ficar vermelha — os textos que a migration substituiu reprovam nela."""
    antes = textos_de_antes()
    assert len(antes) >= 5, f"o ROLLBACK tem {len(antes)} literais"
    reprovados = frases_de_maquina([{"slug": f"antes{i}", "description": t} for i, t in enumerate(antes)])
    assert len(reprovados) >= 3, reprovados
    # e o ofício humano não reprova (a exceção é estreita: "auxiliar de seguros", nada mais)
    assert not frases_de_maquina([{"slug": "x", "description": "o trabalho do auxiliar de seguros tem sete verbos"}])
    assert frases_de_maquina([{"slug": "x", "description": "Este auxiliar roda de madrugada"}])
    # a regra de dúvidas reprova o que não tem
    assert duvidas_ruins([{"slug": "a", "faq": []}, {"slug": "b", "faq": [{"pergunta": "sem interrogação", "resposta": "r"}]}],
                         ["a", "b"]) == ["a: sem dúvida", "b: dúvida malformada"]


def _url_do_banco() -> str | None:
    if os.environ.get("SUPABASE_DB_URL"):
        return os.environ["SUPABASE_DB_URL"]
    env = RAIZ / "backend" / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.startswith("SUPABASE_DB_URL="):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return None


@pytest.fixture(scope="module")
def linhas_do_catalogo() -> list[dict]:
    url = _url_do_banco()
    if not url:
        pytest.skip("sem SUPABASE_DB_URL: o fio do banco não roda (e não fica verde por omissão)")
    psycopg = pytest.importorskip("psycopg")
    colunas, filtros = consulta_do_catalogo()
    where = " and ".join(f"{c} = {v.replace(chr(39), chr(39))}" for c, v in filtros)
    sql = f"select {', '.join(colunas)} from public.auxiliary_templates where {where} order by slug"
    with psycopg.connect(url, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")  # nunca SET SESSION (pooler)
            cur.execute(sql)
            nomes = [d.name for d in cur.description]
            linhas = [dict(zip(nomes, r)) for r in cur.fetchall()]
        conn.rollback()
    return linhas


def test_o_que_a_migration_gravou_e_o_que_o_catalogo_le(linhas_do_catalogo):
    linhas = linhas_do_catalogo
    print(f"\n  📊 o catálogo lê {len(linhas)} aplicativos ativos")
    assert len(linhas) == 18, [l["slug"] for l in linhas]
    ruins = duvidas_ruins(linhas, slugs_da_migration())
    assert ruins == [], ruins
    sem_duvida = sorted(l["slug"] for l in linhas if not (l.get("faq") or []))
    assert sem_duvida == ["quem-cobra-menos"], sem_duvida  # a SPEC só muda a capa do QCM


def test_nenhuma_frase_de_maquina_na_loja(linhas_do_catalogo):
    achados = frases_de_maquina(linhas_do_catalogo)
    assert achados == [], achados


def test_todo_aplicativo_da_loja_tem_capa_com_o_mesmo_icone(linhas_do_catalogo):
    paleta = paleta_das_capas()
    sem_capa = [l["slug"] for l in linhas_do_catalogo if l["slug"] not in paleta]
    outro_icone = [f"{l['slug']}: banco {l['icon']} · capa {paleta[l['slug']]}" for l in linhas_do_catalogo
                   if l["slug"] in paleta and l.get("icon") != paleta[l["slug"]]]
    assert sem_capa == [] and outro_icone == [], (sem_capa, outro_icone)
    assert all(not l.get("cover_url") or str(l["cover_url"]).startswith("https://") for l in linhas_do_catalogo)


def test_o_em_breve_e_decisao_nao_conteudo(linhas_do_catalogo):
    estados = [l["catalog_state"] for l in linhas_do_catalogo]
    assert (estados.count("available"), estados.count("coming_soon")) == (9, 9), estados
