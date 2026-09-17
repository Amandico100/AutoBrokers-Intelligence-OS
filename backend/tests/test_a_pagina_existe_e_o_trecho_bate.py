# -*- coding: utf-8 -*-
r"""🔴 M-A3 · A PÁGINA EXISTE E O TRECHO BATE — sobre um PDF REAL do acervo.

SPEC-EXTRA-001.5 · BLOCO A. O CHECK `servico_tem_fonte` (M-A2) garante que a
linha **tem** documento e página. Não garante que a página **existe** nem que o
trecho está **lá**. Uma citação com a página errada é pior que nenhuma: ela
convence o curador, e o segurado recebe "está na página 14" apontando para uma
página que fala de outra coisa.

```
✅  B.conferir_pagina(documento_real, N, trecho=<lido da página N>)  -> confere
❌  regex sobre um texto inventado
```

🔴 **O texto vem do ACERVO, não da imaginação** (CLAUDE.md §9.4): o trecho é
**lido do PDF arquivado** (`storage_ref` → MinIO → `fitz`, o mesmo extrator de
`insurance_corpus`), e o par de controle é o **MESMO trecho na página N+1**,
que tem de dar FALSO.

⚠️ E `fonte_ausente` é um resultado **explícito**, não `False`: 📊 33 das 206
versões não têm PDF arquivado (17/09/2026), e tratá-las como "trecho errado"
faria o curador apagar a linha certa.

⛔ Somente leitura. Nada é escrito no banco; o bloco do `nivel` duplicado roda
em `BEGIN … ROLLBACK`.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _dsn():
    dsn = os.environ.get("SUPABASE_DB_URL")
    if dsn:
        return dsn
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(RAIZ, ".env"))
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("SUPABASE_DB_URL")


DSN = _dsn()
if not DSN:
    print("\n\U0001F7E1 PULADO: `SUPABASE_DB_URL` ausente do ambiente e de backend/.env.")
    print("   Este guarda lê um documento REAL do acervo; sem banco não há acervo.")
    sys.exit(0)
try:
    import psycopg
except ImportError:
    print("\n\U0001F7E1 PULADO: `psycopg` (v3) não instalado.")
    sys.exit(0)

from app.services.knowledge import assistance_plans_base as B  # noqa: E402

# -------------------------------------------------------------------------
# [0] escolher, por SELECT, um documento de auto/residencial COM fonte
# -------------------------------------------------------------------------
with psycopg.connect(DSN, autocommit=True, prepare_threshold=None) as c, c.cursor() as cur:
    cur.execute(
        "select v.document_id, v.version from normative_document_versions v "
        "join normative_documents d on d.id = v.document_id "
        "where v.storage_ref is not null and d.product_line in ('auto','residencial') "
        "order by v.document_id limit 1"
    )
    escolhido = cur.fetchone()
    cur.execute(
        "select count(*) from normative_document_versions where storage_ref is null"
    )
    sem_fonte = cur.fetchone()[0]
    cur.execute(
        "select document_id, version from normative_document_versions "
        "where storage_ref is null order by document_id limit 1"
    )
    orfa = cur.fetchone()

if not escolhido:
    print("\n\U0001F7E1 PULADO: nenhum documento de auto/residencial com `storage_ref`.")
    sys.exit(0)
doc, versao = str(escolhido[0]), int(escolhido[1])
print(f"\n[0] documento real do acervo: {doc} v{versao}  ·  📊 {sem_fonte} versões sem fonte")

# -------------------------------------------------------------------------
# [1] o trecho LIDO da página N confere NAQUELA página
# -------------------------------------------------------------------------
print("\n[1] o trecho lido da página N confere na página N")

from app.services.knowledge import acervo_arquivo as AA  # noqa: E402
from app.services.minio_service import get_minio_service  # noqa: E402

corpo = get_minio_service().download_file(AA.caminho(doc, versao, AA.ORIGINAL)).read()
import fitz  # noqa: E402

pdf = fitz.open(stream=corpo, filetype="pdf")
total = pdf.page_count
print(f"     o PDF tem {total} páginas · {len(corpo)} bytes")

# uma página com texto de sobra, e a SEGUINTE também — o par precisa das duas.
alvo = None
for n in range(1, total):
    a, b = pdf[n - 1].get_text("text"), pdf[n].get_text("text")
    if len(a.strip()) > 400 and len(b.strip()) > 400:
        alvo = n
        break
if alvo is None:
    pdf.close()
    print("\n\U0001F7E1 PULADO: nenhum par de páginas consecutivas com texto suficiente.")
    sys.exit(0)

texto_n = pdf[alvo - 1].get_text("text")
texto_n1 = pdf[alvo].get_text("text")
pdf.close()

# um trecho de verdade da página N: a linha mais longa dela.
trecho = max((ln.strip() for ln in texto_n.splitlines()), key=len)
print(f"     página escolhida: {alvo} · trecho de {len(trecho)} chars")

r = B.conferir_pagina(doc, alvo, trecho=trecho, versao=versao)
checar(bool(r) and r.motivo == "confere",
       f"🔴 o trecho lido da página {alvo} CONFERE na página {alvo}",
       f"motivo={r.motivo} total={r.total_de_paginas}")

# -------------------------------------------------------------------------
# [2] 🔴 O PAR DE CONTROLE — o MESMO trecho na página N+1 dá FALSO
# -------------------------------------------------------------------------
print("\n[2] 🔴 o PAR: o MESMO trecho na página seguinte NÃO confere")
if B.normalizar_trecho(trecho) in B.normalizar_trecho(texto_n1):
    checar(False, "🔴 o trecho escolhido se repete na página seguinte — par inválido",
           "escolha outro documento; sem trechos distintos o par não prova nada")
else:
    r2 = B.conferir_pagina(doc, alvo + 1, trecho=trecho, versao=versao)
    checar((not r2) and r2.motivo == "trecho_nao_esta_na_pagina",
           f"🔴 o MESMO trecho na página {alvo + 1}: NÃO confere",
           f"ok={r2.ok} motivo={r2.motivo}")

# -------------------------------------------------------------------------
# [3] página que não existe, e página inválida
# -------------------------------------------------------------------------
print("\n[3] página inexistente e página inválida têm motivo PRÓPRIO")
r3 = B.conferir_pagina(doc, total + 5000, trecho=trecho, versao=versao)
checar((not r3) and r3.motivo == "pagina_inexistente",
       f"página {total + 5000} num PDF de {total}: `pagina_inexistente`",
       f"motivo={r3.motivo}")
for ruim in (0, -1, "abc", None):
    rr = B.conferir_pagina(doc, ruim, trecho=trecho, versao=versao)
    checar((not rr) and rr.motivo == "pagina_inexistente",
           f"pagina={ruim!r}: `pagina_inexistente`", f"motivo={rr.motivo}")

# -------------------------------------------------------------------------
# [4] 🔴 fonte ausente NÃO é False — é `fonte_ausente`
# -------------------------------------------------------------------------
print("\n[4] 🔴 a versão SEM PDF arquivado devolve `fonte_ausente`, não um `não`")
if orfa:
    r4 = B.conferir_pagina(str(orfa[0]), 1, trecho="qualquer", versao=int(orfa[1]))
    checar(r4.motivo == "fonte_ausente",
           "versão sem `storage_ref`: motivo `fonte_ausente` — o curador sabe que "
           "o problema é o ARQUIVO, não o trecho",
           f"motivo={r4.motivo}")
    checar(not r4.ok,
           "e ela também não vale como confirmação (ok=False)")
else:
    print("     (nenhuma versão sem `storage_ref` — bloco sem o que medir)")

r5 = B.conferir_pagina(doc, alvo, versao=versao)
checar((not r5) and r5.motivo == "sem_trecho_para_conferir",
       "sem trecho e sem hash: `sem_trecho_para_conferir` — não inventa um verde",
       f"motivo={r5.motivo}")

# -------------------------------------------------------------------------
# [5] o hash é o MESMO dos dois lados (CLAUDE.md §9.4, dialeto)
# -------------------------------------------------------------------------
print("\n[5] o hash do trecho é o mesmo em quem grava e em quem confere")
checar(B.hash_do_trecho(trecho) == B.hash_do_trecho(trecho.replace("\n", " ") + "  "),
       "espaço e quebra de linha não mudam o hash (a normalização é uma só)")
checar(B.hash_do_trecho(trecho) != B.hash_do_trecho(trecho + " X"),
       "🔴 CONTROLE: mudar o TEXTO muda o hash — ele não é constante")
checar(len(B.hash_do_trecho(trecho)) == 64,
       "o hash tem 64 hex, que é o que `servico_tem_fonte` exige")

# -------------------------------------------------------------------------
# [6] nível duplicado no mesmo produto é recusado pelo UNIQUE
# -------------------------------------------------------------------------
print("\n[6] dois planos no mesmo nível, no mesmo produto: o UNIQUE recusa")
with psycopg.connect(DSN, prepare_threshold=None) as conn, conn.cursor() as cur:
    COLS = ("insurer_key,ramo,produto,plano,nivel,vigencia_inicio,documento_id,"
            "pagina,confianca,content_hash")
    cur.execute(
        f"insert into public.insurer_assistance_plans ({COLS}) values "
        f"('allianz','auto','GUARDA M-A3','Essencial',1,'2026-01-01','{doc}',1,'media','h')"
    )
    cur.execute("savepoint sp")
    try:
        cur.execute(
            f"insert into public.insurer_assistance_plans ({COLS}) values "
            f"('allianz','auto','GUARDA M-A3','Completo',1,'2026-01-01','{doc}',2,'media','h')"
        )
        checar(False, "🔴 dois planos no nível 1 do mesmo produto foram ACEITOS",
               "'existe plano acima?' deixaria de ter resposta única")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).strip().splitlines()[0]
        checar("uq_iap_nivel" in msg, "nível 1 repetido no produto: RECUSADO por `uq_iap_nivel`", msg)
    cur.execute("rollback to savepoint sp")

    # 🔴 CONTROLE: o nível 2 no MESMO produto entra — o UNIQUE é do nível, não do produto.
    cur.execute("savepoint sp")
    try:
        cur.execute(
            f"insert into public.insurer_assistance_plans ({COLS}) values "
            f"('allianz','auto','GUARDA M-A3','Completo',2,'2026-01-01','{doc}',2,'media','h')"
        )
        checar(True, "🔴 CONTROLE: nível 2 no MESMO produto é ACEITO")
    except Exception as exc:  # noqa: BLE001
        checar(False, "🔴 CONTROLE: o nível 2 foi recusado — o UNIQUE pega demais",
               f"{type(exc).__name__}: {str(exc).strip().splitlines()[0]}")
    cur.execute("rollback to savepoint sp")
    conn.rollback()

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
