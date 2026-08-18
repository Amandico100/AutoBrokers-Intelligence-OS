# -*- coding: utf-8 -*-
"""A Resulta tem marca de verdade -- e dar marca a ela NAO quebra a Cobranca.

    npm run test:resulta-tem-marca
    python backend/tests/test_a_resulta_tem_marca.py

SPEC-081 §Bloco E (E.7) e §Bloco G.4.

POR QUE ESTE ARQUIVO EXISTE

Ha apresentacao amanha com o Auxiliar de Cobranca. O Bloco E da marca a
Resulta, e a Cobranca gera as pecas dela pelo MESMO `ArtifactService`. O efeito
colateral e real e conhecido: as pecas da Cobranca passam a sair com a logo e
as cores da Resulta. Isso e melhoria -- desde que continuem saindo INTEIRAS.

📊 E quase nao continuaram. Medido nesta maquina em 18/08/2026, antes de
qualquer escrita:

    render_html(brand=<marca nova, paleta como editar() a grava>)
        -> KeyError: 'typography'

`render.py:41-42` devolve a paleta do banco verbatim quando ela tem `themes`,
e `system.py:298` procura `typography` dentro dela. `editar()`
(`capture.py:508-513`) grava SEIS chaves e nenhuma delas e `typography`. O
defeito so e alcancavel por uma corretora que TEM marca -- e ate 18/08 nao
havia nenhuma: 📊 os 40 artifacts em producao sao `is_fallback=true`, e o ramo
de fallback devolve a saida INTEIRA de `build_design_system`.

Instalar a marca sem a setima chave teria feito TODAS as pecas da Cobranca
pararem de renderizar, com excecao, na vespera da apresentacao.

O QUE ESTE ARQUIVO GUARDA

    1  a cor sai do pixel, e o data URI e um data URI
    2  a logo aparece no HTML                    (+ CONTROLE sem logo)
    3  a paleta que o script grava renderiza     (+ CONTROLE sem typography)
    4  a peca REAL da Cobranca sai inteira       (+ CONTROLE com marca antiga)
    5  visual_style e 'aurora' -- senao a Cobranca troca de tema em silencio
    6  o --dry-run nao escreve
    7  o UNDO desliga `is_published` e so apaga o que e dele

As asseroes de banco (8) so rodam onde houver credencial; sem ela sao contadas
como PULADAS e aparecem no resumo. Guarda que se declara verde sem ter medido
nada e pior que guarda nenhum.
"""
from __future__ import annotations

import base64
import importlib.util
import os
import sys
import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # backend/
sys.path.insert(0, RAIZ)

PASS = FAIL = PULADO = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))


def pular(nome, porque):
    global PULADO
    PULADO += 1
    print("  [PULADO] " + nome + "  -- " + porque)


# --------------------------------------------------------------------------
# Carregamento -- mesma arvore sintetica do script e do pack de aceite:
# `app/services/__init__.py` importa `openai`, que nao esta em toda maquina.
# --------------------------------------------------------------------------

for _chave in ("SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY",
               "ENCRYPTION_KEY", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"):
    os.environ.setdefault(_chave, "nao-usado-por-este-teste")

for _nome in ("app", "app.services", "app.services.brand",
              "app.services.artifacts"):
    if _nome not in sys.modules:
        _pkg = types.ModuleType(_nome)
        _pkg.__path__ = [os.path.join(RAIZ, *_nome.split("."))]
        sys.modules[_nome] = _pkg


def carregar(rotulo, caminho):
    spec = importlib.util.spec_from_file_location(
        rotulo, os.path.join(RAIZ, caminho))
    m = importlib.util.module_from_spec(spec)
    m.__package__ = rotulo.rsplit(".", 1)[0] if "." in rotulo else ""
    sys.modules[rotulo] = m
    spec.loader.exec_module(m)
    return m


carregar("app.services.brand.color", "app/services/brand/color.py")
carregar("app.services.brand.extract", "app/services/brand/extract.py")
sistema_mod = carregar("app.services.brand.system", "app/services/brand/system.py")
carregar("app.services.artifacts.charts", "app/services/artifacts/charts.py")
carregar("app.services.artifacts.blocks", "app/services/artifacts/blocks.py")
carregar("app.services.artifacts.styles", "app/services/artifacts/styles.py")
render = carregar("app.services.artifacts.render", "app/services/artifacts/render.py")
cobranca = carregar("app.services.billing_collection",
                    "app/services/billing_collection.py")

# 🔴 O script e importado, nao reimplementado. E o que faz uma mutacao NELE
# aparecer aqui em vermelho -- teste que copia a logica do alvo nao guarda o
# alvo, guarda a copia.
marca_script = carregar("instalar_marca_resulta",
                        "scripts/instalar_marca_resulta.py")

LOGO = os.path.join(RAIZ, "tools", "_resulta_logo.png")


# ==========================================================================
# 1. A cor sai do pixel
# ==========================================================================
print("\n1. A COR SAI DO PIXEL, E O DATA URI E UM DATA URI")

extract = sys.modules["app.services.brand.extract"]
medida = marca_script.medir_logo(
    __import__("pathlib").Path(LOGO), extract)

check("analisar_logo devolve cores de tinta",
      len(medida["ink_colors"]) >= 1, medida["ink_colors"])

# 🔴 Nao se afirma #1D5579. A SPEC supunha essa cor; quem manda e o arquivo.
# Se a logo mudar, este teste continua correto -- ele mede que HA cor de
# marca, nao qual e. (Mutacao M-controle da SPEC E.7: trocar a cor -> VERDE.)
primaria = str(medida["primary"] or "")
check("primary e um hex valido",
      primaria.startswith("#") and len(primaria) == 7, primaria)
check("primary nao e cinza (tem cor)",
      len(set(primaria[1:].lower())) > 2, primaria)

check("data URI comeca com o prefixo de PNG em base64",
      medida["data_uri"].startswith("data:image/png;base64,"),
      medida["data_uri"][:40])
def _volta_nos_bytes(uri: str) -> bool:
    """Defensivo de proposito: um data URI quebrado tem de virar FALHOU, nao
    excecao. Teste que morre na terceira linha nao chega a medir a quarta --
    e uma mutacao ficaria 'vermelha' escondendo tudo o que vinha depois."""
    try:
        return base64.b64decode(uri.split(",", 1)[1]) == open(LOGO, "rb").read()
    except Exception:  # noqa: BLE001
        return False


check("o data URI decodifica de volta nos bytes do arquivo",
      _volta_nos_bytes(medida["data_uri"]))
check("byte_size bate com o arquivo",
      medida["bytes"] == os.path.getsize(LOGO), medida["bytes"])


# ==========================================================================
# 2. A logo aparece no HTML -- com linha de controle
# ==========================================================================
print("\n2. A LOGO APARECE NO HTML")

sistema = sistema_mod.build_design_system(medida["primary"], medida["accent"])
paleta = marca_script._paleta_completa(sistema)

MARCA_NOVA = {
    "name": "Resulta Seguros",
    "palette": paleta,
    "typography": paleta.get("typography") or {},
    "logo": {"storage_ref": medida["data_uri"]},
    "visual_style": marca_script.VISUAL_STYLE,
    "is_fallback": False,
}
MARCA_ANTIGA = {   # o fallback: exatamente o que os 40 artifacts trazem
    "name": "Corretora",
    "palette": sistema_mod.build_design_system(
        sistema_mod.FALLBACK_PRIMARIA, sistema_mod.FALLBACK_ACENTO),
    "logo": None,
    "visual_style": "aurora",
    "is_fallback": True,
}
CAPA = [{"block": "cover", "props": {"title": "Peca de teste",
                                     "eyebrow": "Bloco E",
                                     "verdict": "so para medir a capa"}}]


def desenhar(marca, composicao, titulo="t"):
    """Renderiza e devolve `(html, diagnostico)` -- ou `("", {erro})`.

    O render PODE explodir: foi assim que o defeito da `typography` apareceu.
    Deixar a excecao subir mataria o arquivo na primeira asseracao e esconderia
    todas as outras, e um guarda que so consegue relatar um problema por vez
    faz o segundo problema parecer inexistente.
    """
    try:
        return render.render_html(brand=marca, composition=composicao,
                                  visual_style="aurora", title=titulo)
    except Exception as exc:  # noqa: BLE001
        return "", {"blocos": -1, "falhas": [type(exc).__name__ + ": " + str(exc)],
                    "desconhecidos": [], "marca_padrao": None}


html_com, diag_com = desenhar(MARCA_NOVA, CAPA)
check('<img src="data:image/png;base64, esta no HTML',
      '<img src="data:image/png;base64,' in html_com)
check("o render nao reporta falha", diag_com["falhas"] == [], diag_com)
check("marca_padrao = False", diag_com["marca_padrao"] is False)

# 🔴 CONTROLE. Sem esta linha, a asseracao acima poderia estar medindo
# qualquer coisa que sempre aparece no HTML.
html_sem, diag_sem = desenhar(MARCA_ANTIGA, CAPA)
check("CONTROLE: sem logo, nao ha <img de capa",
      '<img src="data:image/png;base64,' not in html_sem)
check("CONTROLE: sem logo, a capa usa ab-cover-wordmark",
      "ab-cover-wordmark" in html_sem)
check("CONTROLE: sem marca, marca_padrao = True",
      diag_sem["marca_padrao"] is True)


# ==========================================================================
# 3. 🔴 A paleta que o script grava renderiza -- e a de seis chaves NAO
# ==========================================================================
print("\n3. A PALETA GRAVADA TEM AS SETE CHAVES (o defeito que matava tudo)")

check("_paleta_completa inclui 'typography'", "typography" in paleta,
      sorted(paleta.keys()))
check("_paleta_completa inclui 'primary' (sem ele o publicar() recusa)",
      bool(paleta.get("primary")), sorted(paleta.keys()))
check("_paleta_completa inclui 'themes' e 'scales'",
      "themes" in paleta and "scales" in paleta, sorted(paleta.keys()))

# 🔴 CONTROLE. Prova que a asseracao acima mede algo que CONSEGUE quebrar:
# a paleta de seis chaves -- a que `editar()` grava sozinho -- explode.
seis = {k: v for k, v in paleta.items() if k != "typography"}
explodiu = ""
try:
    render.render_html(brand={**MARCA_NOVA, "palette": seis},
                       composition=CAPA, visual_style="aurora", title="t")
except Exception as exc:  # noqa: BLE001
    explodiu = type(exc).__name__ + ": " + str(exc)
check("CONTROLE: a paleta SEM typography levanta KeyError",
      explodiu.startswith("KeyError"), explodiu or "nao levantou nada")


# ==========================================================================
# 4. 🔴 A peca REAL da Cobranca sai inteira com a marca nova
# ==========================================================================
print("\n4. A COBRANCA CONTINUA INTEIRA (SPEC-081 §G.4)")

# A composicao vem de `compor_peca_da_cobranca`, a funcao de producao
# (`billing_collection.py`, arquivo CONGELADO -- aqui so consumido). Os dados
# sao sinteticos de proposito: a composicao real de producao traz nome de
# segurado, e fixture com nome de cliente nao entra no repositorio.
BLOCOS = cobranca.compor_peca_da_cobranca(
    routine={"id": "r-1", "name": "Cobranca de boletos atrasados"},
    cfg={"portal_keys": ["allianz"], "send_mode": "test",
         "management_provider": "infocap"},
    items=[{"cliente": "CLIENTE DE TESTE LTDA", "documento": "...0001",
            "seguradora": "ALLIANZ", "vencimento": "08/08/2026",
            "valor": 1972.40}],
    boletos=[{"ok": True}],
    fila=[{"telefone": "...7463"}],
    retidos=[],
    tarefas=[],
    blockers=[],
    test_sends=[{"ok": True}],
)
check("compor_peca_da_cobranca devolve composicao nao vazia",
      isinstance(BLOCOS, list) and len(BLOCOS) >= 5, len(BLOCOS or []))

html_cob_novo, diag_cob_novo = desenhar(MARCA_NOVA, BLOCOS,
                                        "Cobranca - Resulta Seguros")
check("a peca da Cobranca renderiza sem falha",
      diag_cob_novo["falhas"] == [], diag_cob_novo["falhas"])
check("a peca da Cobranca nao tem bloco desconhecido",
      diag_cob_novo["desconhecidos"] == [], diag_cob_novo["desconhecidos"])
check("a peca da Cobranca sai com a logo",
      '<img src="data:image/png;base64,' in html_cob_novo)
check("a peca da Cobranca fecha o documento",
      html_cob_novo.rstrip().endswith("</html>"))
check("a peca da Cobranca leva a cor da marca",
      primaria.upper().lstrip("#") in html_cob_novo.upper())

# 🔴 CONTROLE. A mesma composicao com a marca ANTIGA tambem sai inteira --
# prova que a asseracao acima mede a PECA, e nao a marca.
html_cob_velho, diag_cob_velho = desenhar(MARCA_ANTIGA, BLOCOS, "Cobranca")
check("CONTROLE: com a marca antiga a peca tambem sai inteira",
      diag_cob_velho["falhas"] == [] and diag_cob_velho["desconhecidos"] == [],
      diag_cob_velho)
check("os dois HTML tem o MESMO numero de blocos -- muda cor e logo, "
      "nao estrutura",
      diag_cob_novo["blocos"] == diag_cob_velho["blocos"],
      (diag_cob_novo["blocos"], diag_cob_velho["blocos"]))
check("os dois HTML tem o mesmo numero de <section",
      html_cob_novo.count("<section") == html_cob_velho.count("<section"),
      (html_cob_novo.count("<section"), html_cob_velho.count("<section")))


# ==========================================================================
# 5. 🔴 visual_style = 'aurora'
# ==========================================================================
print("\n5. O TEMA DA COBRANCA NAO MUDA")

# 📊 `service.py:187`: estilo = pedido || MARCA.visual_style || TEMPLATE.
# A marca VENCE o template. Gravar 'meridian' aqui trocaria o tema de todas as
# pecas do Auxiliar de Cobranca sem deploy e sem aviso.
check("o script grava visual_style='aurora'",
      marca_script.VISUAL_STYLE == "aurora", marca_script.VISUAL_STYLE)

sql = marca_script.sql_instalar("00000000-0000-0000-0000-000000000000",
                                medida, sistema)
check("o SQL emitido grava visual_style = 'aurora'",
      "visual_style = 'aurora'" in sql)
check("o SQL emitido nunca escreve outro tema",
      "'meridian'" not in sql and "'obsidian'" not in sql)
# Só as linhas executáveis: o comentário do script CITA o `on conflict` que
# não pode ser usado, e um teste que casasse com o comentário estaria medindo
# a documentação em vez do SQL.
sql_executavel = "\n".join(l for l in sql.splitlines()
                           if not l.lstrip().startswith("--")).lower()
check("o SQL emitido nao usa ON CONFLICT em brand_assets (42P10)",
      "on conflict (company_id, kind)" not in sql_executavel)
# CONTROLE: o `on conflict` da procedencia CONTINUA la -- aquele indice e
# UNIQUE total e funciona. Se esta linha ficasse vermelha, a de cima estaria
# passando por varrer o arquivo errado.
check("CONTROLE: o ON CONFLICT da procedencia continua no SQL",
      "on conflict (brand_profile_id, field_path)" in sql_executavel)
check("o SQL emitido grava a paleta com typography",
      '"typography"' in sql)


# ==========================================================================
# 6. O --dry-run nao escreve
# ==========================================================================
print("\n6. O --dry-run NAO ESCREVE")


class _BancoQueRecusaEscrita:
    """Qualquer escrita aqui e um defeito, entao qualquer escrita levanta."""

    def __init__(self):
        self.escritas = []

    def table(self, nome):
        self.escritas.append(nome)
        raise AssertionError("o dry-run tocou na tabela " + nome)


_argv = sys.argv[:]
_stdout = sys.stdout
banco = _BancoQueRecusaEscrita()
try:
    sys.argv = ["x", "--company", "00000000-0000-0000-0000-000000000000",
                "--emit-sql"]
    # O SQL inteiro no meio do relatorio do teste esconde o resultado do
    # teste. Engolir a saida aqui e o unico jeito de o resumo continuar
    # legivel -- e o conteudo do SQL ja e conferido na secao 5.
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    marca_script.main()
    tocou = banco.escritas
except SystemExit:
    tocou = banco.escritas
except AssertionError as exc:  # noqa: BLE001
    tocou = [str(exc)]
finally:
    if sys.stdout is not _stdout:
        sys.stdout.close()
    sys.stdout = _stdout
    sys.argv = _argv
check("--emit-sql nao abre conexao nem escreve", tocou == [], tocou)


# ==========================================================================
# 6b. A gravacao do asset: DOIS statements, nunca upsert
# ==========================================================================
print("\n6b. O ASSET E GRAVADO EM DOIS STATEMENTS, E SO UM FICA is_current")


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Tabela:
    """PostgREST de mentira que anota o que foi pedido.

    Existe porque a alternativa -- conferir o texto do arquivo com `in` -- nao
    guarda comportamento nenhum: um `is_current` dentro de um comentario
    passaria no teste e nao gravaria nada no banco.
    """

    def __init__(self, diario, nome, linhas):
        self.diario, self.nome, self.linhas = diario, nome, linhas
        self.acao = ("select", None)

    def select(self, *a, **k):
        self.acao = ("select", None)
        return self

    def insert(self, row):
        self.acao = ("insert", row)
        return self

    def update(self, patch):
        self.acao = ("update", patch)
        return self

    def upsert(self, row, **k):
        self.acao = ("upsert", row)
        return self

    def delete(self):
        self.acao = ("delete", None)
        return self

    def eq(self, *a):
        return self

    def in_(self, *a):
        return self

    def limit(self, n):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        verbo, carga = self.acao
        self.diario.append((self.nome, verbo, carga))
        if verbo == "select":
            return _Resposta(list(self.linhas))
        if verbo in ("insert", "upsert"):
            # `upsert` responde como `insert` de proposito. Se respondesse
            # vazio, o script chamaria `sys.exit(4)` e a mutacao "voltou a
            # usar upsert" derrubaria o processo sem uma linha vermelha
            # explicando o que houve -- ruido em vez de diagnostico.
            nova = dict(carga)
            nova["id"] = "asset-de-mentira"
            self.linhas.append(nova)
            return _Resposta([nova])
        return _Resposta([])


class _Banco:
    def __init__(self, linhas=None):
        self.diario = []
        self.linhas = list(linhas or [])

    def table(self, nome):
        return _Tabela(self.diario, nome, self.linhas)


banco_vazio = _Banco()
asset_id = marca_script._gravar_asset(
    banco_vazio, "00000000-0000-0000-0000-000000000000", medida)
verbos = [(n, v) for n, v, _ in banco_vazio.diario]
inseridos = [c for _, v, c in banco_vazio.diario if v == "insert"]

check("nenhum upsert em brand_assets (era o 42P10)",
      not any(v == "upsert" for _, v in verbos), verbos)
check("houve exatamente UM insert", len(inseridos) == 1, verbos)
check("o insert marca is_current=True",
      bool(inseridos and inseridos[0].get("is_current")),
      inseridos[0] if inseridos else None)
check("o insert grava o data URI em storage_ref",
      bool(inseridos and str(inseridos[0].get("storage_ref", ""))
           .startswith("data:image/png;base64,")))
check("o insert leva as cores medidas",
      bool(inseridos and inseridos[0].get("ink_colors")))
check("devolveu um id de asset", bool(asset_id), asset_id)

# Idempotencia: rodando de novo sobre a linha que ja existe, nada e inserido.
banco_cheio = _Banco([{"id": "ja-existe", "is_current": True,
                       "storage_ref": medida["data_uri"]}])
segundo_id = marca_script._gravar_asset(
    banco_cheio, "00000000-0000-0000-0000-000000000000", medida)
check("2a execucao NAO insere logo duplicada",
      not any(v == "insert" for _, v, _ in banco_cheio.diario),
      [(n, v) for n, v, _ in banco_cheio.diario])
check("2a execucao reaproveita o asset existente",
      segundo_id == "ja-existe", segundo_id)
# E o desliga-tudo tem de vir ANTES do religa, senao o indice parcial unico
# `brand_assets_one_current_per_kind` recusaria dois `is_current` ao mesmo
# tempo.
_updates = [i for i, (_, v, _c) in enumerate(banco_cheio.diario)
            if v == "update"]
_desliga = [i for i, (_, v, c) in enumerate(banco_cheio.diario)
            if v == "update" and c == {"is_current": False}]
check("o desliga-todos vem antes de qualquer religa",
      bool(_desliga) and _desliga[0] == _updates[0],
      [(v, c) for _, v, c in banco_cheio.diario])


# ==========================================================================
# 7. O UNDO
# ==========================================================================
print("\n7. O UNDO DESFAZ O QUE E DELE, E SO ISSO")

undo = marca_script.sql_undo("00000000-0000-0000-0000-000000000000")

# ⚠️ Sem esta linha o UNDO e recusado pelo CHECK
# `brand_profiles_published_needs_primary` (migration 20260725_05:148-150).
check("o UNDO desliga is_published", "is_published = false" in undo)
check("o UNDO zera a paleta", "palette = '{}'::jsonb" in undo)
check("o UNDO solta o logo_asset_id", "logo_asset_id = null" in undo)
check("o UNDO desliga o is_current do asset",
      "set is_current = false" in undo)
check("o UNDO NAO apaga linha de brand_assets",
      "delete from public.brand_assets" not in undo)

# 📊 A Resulta ja tinha 11 linhas `human_edited` gravadas pelo painel em
# 17/08. Um UNDO que apagasse por `field_path` levaria junto o trabalho dela.
check("o UNDO apaga procedencia pela ASSINATURA do script",
      marca_script.ASSINATURA in undo)
check("o UNDO NAO apaga procedencia por field_path",
      "field_path in (" not in undo.lower())


# ==========================================================================
# 8. O banco -- so onde houver credencial
# ==========================================================================
print("\n8. O ESTADO NO BANCO")

_url = os.getenv("SUPABASE_URL") or ""
_chave = os.getenv("SUPABASE_KEY") or ""
_tem_credencial = (_url.startswith("http") and "invalid" not in _url
                   and _chave and not _chave.startswith("build-local")
                   and _chave != "nao-usado-por-este-teste")
_empresa = os.getenv("RESULTA_COMPANY_ID",
                     "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab")

if not _tem_credencial:
    for _nome in ("a marca da Resulta nao e fallback",
                  "visual_style da Resulta e 'aurora'",
                  "a paleta da Resulta tem primary e typography",
                  "a logo da Resulta e um data URI",
                  "ha exatamente UM logo_primary is_current"):
        pular(_nome, "sem SUPABASE_URL/SUPABASE_KEY reais no ambiente")
else:
    from supabase import create_client  # noqa: E402

    db = create_client(_url, _chave)
    capture = carregar("app.services.brand.capture",
                       "app/services/brand/capture.py")
    snap = capture.BrandCaptureService(db).snapshot_para_artefato(_empresa)

    check("a marca da Resulta nao e fallback",
          snap.get("is_fallback") is False, snap.get("is_fallback"))
    check("visual_style da Resulta e 'aurora'",
          snap.get("visual_style") == "aurora", snap.get("visual_style"))
    # 📊 `service.py:228-233` levanta ValueError ao publicar sem `palette` e
    # `name`: paleta sem primary faz a Cobranca PARAR DE PUBLICAR.
    check("a paleta da Resulta tem primary e typography",
          bool((snap.get("palette") or {}).get("primary"))
          and "typography" in (snap.get("palette") or {}),
          sorted((snap.get("palette") or {}).keys()))
    check("a logo da Resulta e um data URI",
          str(((snap.get("logo") or {}).get("storage_ref") or ""))
          .startswith("data:image/png;base64,"))

    atuais = (db.table("brand_assets").select("id")
              .eq("company_id", _empresa).eq("kind", "logo_primary")
              .eq("is_current", True).execute()).data or []
    check("ha exatamente UM logo_primary is_current", len(atuais) == 1,
          len(atuais))

    # A prova final: a peca da Cobranca com a marca que esta NO BANCO.
    _h, _d = render.render_html(brand=snap, composition=BLOCOS,
                                visual_style=snap.get("visual_style"),
                                title="Cobranca - marca do banco")
    check("a Cobranca renderiza com a marca que esta no banco",
          _d["falhas"] == [] and _d["desconhecidos"] == []
          and '<img src="data:image/png;base64,' in _h, _d)


# ==========================================================================
print("\n" + "=" * 66)
print(f"  {PASS} ok · {FAIL} falha(s) · {PULADO} pulada(s)")
if PULADO:
    print("  As puladas exigem credencial real. Sem ela, este arquivo NAO")
    print("  afirma nada sobre o banco -- so sobre o codigo e o SQL.")
print("=" * 66)
sys.exit(1 if FAIL else 0)
