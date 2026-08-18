# -*- coding: utf-8 -*-
"""Dá à corretora a marca que ela já tem no arquivo, e que o banco nunca teve.

    python backend/scripts/instalar_marca_resulta.py --company <UUID> --dry-run
    python backend/scripts/instalar_marca_resulta.py --company <UUID>
    python backend/scripts/instalar_marca_resulta.py --company <UUID> --undo

    # sem credencial na máquina (ver §"os dois caminhos", no fim):
    python backend/scripts/instalar_marca_resulta.py --company <UUID> --emit-sql
    python backend/scripts/instalar_marca_resulta.py --company <UUID> --emit-sql --undo

SPEC-081 §Bloco E. Duas escritas de DML, nenhuma migration, nenhum arquivo
congelado tocado — este script só CONSOME `app.services.brand`.

📊 O ESTADO QUE ISTO CONSERTA, medido em 18/08/2026 pelo MCP do Supabase:

    select company_id, palette->>'primary', logo_asset_id from brand_profiles;
        -> 3 linhas, primary NULL nas tres, logo_asset_id NULL nas tres
    select count(*) from brand_assets;
        -> 0

    select count(*) filter (where v.brand_snapshot->>'is_fallback'='true')
      from artifacts a join artifact_versions v on v.artifact_id=a.id;
        -> 40 de 40

Quarenta peças entregues em produção saíram com o azul-petróleo da casa e sem
logo nenhuma, porque `snapshot_para_artefato` (capture.py:554-558) cai no ramo
de fallback quando `palette.primary` é nulo. A marca real sempre existiu —
mora em `backend/tools/_resulta_logo.png`, e um script offline de aceite já a
usava. Nunca chegou ao banco.


TRÊS DECISÕES QUE ESTE ARQUIVO TOMA, E POR QUÊ
----------------------------------------------

1. **`ON CONFLICT` está proibido aqui.** 📊 Medido contra o banco de produção
   em 18/08/2026, com a transação abortada de propósito:

       insert into brand_assets (...) on conflict (company_id, kind) do nothing
       -> 42P10 :: there is no unique or exclusion constraint matching the
                   ON CONFLICT specification

   O índice `brand_assets_one_current_per_kind` é PARCIAL (`WHERE is_current`,
   migration 20260725_05:79-80) e o Postgres não o infere a partir de um
   `ON CONFLICT` sem o `WHERE` correspondente. O caminho de `capture.py:297`
   usa exatamente esse upsert — e é por isso que `brand_assets` está vazia:
   **aquele código nunca gravou uma linha na vida.** Aqui vão dois statements:
   desliga todos os `is_current`, depois insere.

2. 🔴 **`visual_style` é `'aurora'`, e isso é invariante, não preferência.**
   📊 `artifacts/service.py:187` resolve o tema como
   `pedido || MARCA.visual_style || TEMPLATE.visual_style` — a marca **vence**
   o template. O template do Auxiliar de Cobrança
   (`financial.billing_collection`) declara `aurora`. Gravar `'meridian'` ou
   `'obsidian'` aqui trocaria, em silêncio e sem deploy, o tema de TODAS as
   peças da Cobrança. Por isso a constante abaixo tem nome, comentário e teste
   (`backend/tests/test_a_resulta_tem_marca.py`).

3. 🔴 **A paleta gravada tem de ser o sistema de design COMPLETO — com
   `typography` dentro.** Isto não estava na SPEC e é o defeito mais grave que
   este bloco encontrou. 📊 Medido:

       render.py:41-42    if paleta.get("themes"): return paleta
       system.py:298      for chave, valor in sistema["typography"].items():
       capture.py:508-513 editar() grava a paleta com SEIS chaves:
                          primary, accent, scales, themes, audit, origin

   `_sistema_da_marca` devolve a paleta do banco **verbatim** quando ela tem
   `themes`, e `to_css_variables` então procura `typography` lá dentro. Como
   `editar()` não põe, o resultado é `KeyError: 'typography'` — e o render
   **inteiro** morre. Reproduzido nesta máquina antes de qualquer escrita:

       RENDER EXPLODIU: KeyError 'typography'

   Por que ninguém viu: 📊 os 40 artifacts em produção são `is_fallback=true`,
   e o ramo de fallback (`capture.py:556`) devolve `"palette": sistema` — a
   saída INTEIRA de `build_design_system`, com `typography`. O defeito só é
   alcançável por uma corretora que **tem** marca. Nunca houve uma.

   🔴 Consequência direta para a apresentação: instalar a marca sem esta
   correção teria feito **todas** as peças do Auxiliar de Cobrança pararem de
   renderizar, com exceção, na véspera.

   A correção é de DADO, não de código: o docstring de `_sistema_da_marca` diz
   *"o snapshot já traz o sistema pronto"*. Quem descumpre o contrato é quem
   grava seis chaves. Este script grava as sete.

4. **A cor vem do pixel, não do documento.** A SPEC supunha `#1D5579`; este
   script mede o arquivo e usa o que mediu. 📊 A medição confirmou a suposição
   (`#1D5579` / `#EE7501`, 94,3% / 5,6% da área de tinta), mas a ordem importa:
   se um dia a logo mudar, quem manda continua sendo o arquivo.


O QUE ESTE SCRIPT NÃO ESCREVE, DE PROPÓSITO
--------------------------------------------

`susep_code`, `legal_name` e `tagline` existem no script de aceite
(`backend/tools/gerar_visual_acceptance_pack.py:62-96`) e **não entram aqui**.
📊 `blocks.py:382` imprime o SUSEP no rodapé de toda peça: um número de
registro não conferido, impresso num documento que vai ao cliente, é pior que
rodapé sem SUSEP. Aquilo era 💭 ilustrativo num pack de aceite visual; virar
📊 fato exige o Founder confirmar. Ficou em PENDENCIAS.

`typography` também fica de fora. 📊 O renderizador não emite `<link>` de
Google Fonts (varredura em `render.py` e `styles.py`: zero ocorrência de
`googleapis` ou `@font-face`), então declarar `'Montserrat'` produziria uma
`font-family` que nenhum navegador consegue carregar — degradação silenciosa
para a fonte de sistema. Melhor a fonte padrão honesta.

`contact` fica de fora porque nenhum bloco o renderiza (varredura em
`blocks.py`: zero ocorrência de `contact`) e porque o telefone e o e-mail já
moram em `companies`. Copiar dado verificado para um segundo lugar é como se
cria a segunda verdade.


OS DOIS CAMINHOS DE ESCRITA, E POR QUE EXISTEM DOIS
----------------------------------------------------

**Caminho normal** (`--company X`): fala PostgREST com a service role e usa
`BrandCaptureService.editar()`, que é o caminho de produção. Exige
`SUPABASE_URL` + `SUPABASE_KEY` reais no ambiente.

**Caminho `--emit-sql`**: imprime o SQL equivalente, para ser executado por
quem TEM acesso ao banco. 📊 Existe porque a máquina onde este bloco foi
executado não tem credencial nenhuma — o `.env.local` do repositório aponta
para `https://build-local.invalid` com a chave `build-local-service`, que são
marcadores de build, não segredo.

O SQL não é uma segunda implementação: cada statement diz, em comentário, qual
linha de `capture.py` ele espelha, e o VERIFY do fim compara a paleta gravada
com `build_design_system(primaria, acento)` recalculada em Python. Se os dois
caminhos divergirem, o VERIFY fica vermelho — é assim que se impede a cópia de
envelhecer em silêncio.

⚠️ A ÚNICA divergência conhecida e aceita: `completeness`. `editar()` a
recalcula lendo o perfil (`capture.py:_completude`); o SQL grava o valor
aritmético equivalente, comentado. É coluna de cache para barra de progresso —
a próxima captura ou edição a recalcula sozinha.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

# O console do Windows abre em cp1252 e derruba o processo no primeiro 📊 que
# aparece num comentário do SQL. Perder uma execução de banco por causa da
# codificação do terminal seria o tipo de falha que não ensina nada.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
LOGO_PADRAO = BACKEND / "tools" / "_resulta_logo.png"

# 🔴 O tema das peças. Ver decisão 2 no cabeçalho. Não troque sem ler
# `service.py:187` e sem avisar quem cuida do Auxiliar de Cobrança.
VISUAL_STYLE = "aurora"

# A assinatura que este script deixa em `brand_field_provenance.source_detail`,
# e o único critério pelo qual o UNDO reconhece o que É dele.
#
# ⚠️ Isto não é enfeite. 📊 Em 18/08/2026, ANTES desta instalação, a Resulta já
# tinha ONZE linhas de procedência `human_edited=true` gravadas em 17/08 pelo
# painel da corretora ("editado no painel da corretora") — entre elas
# `display_name`, `tagline`, `susep_code` e `legal_name`. Um UNDO que apagasse
# por `field_path` apagaria decisões de uma pessoa que este script nunca viu.
# Desfazer o próprio trabalho é obrigação; desfazer o dos outros é estrago.
ASSINATURA = "instalar_marca_resulta.py -- cor medida na area de tinta do arquivo"

# Campos que o `--undo` restaura. 📊 Lidos do banco de produção em 18/08/2026,
# antes da primeira execução deste script:
#   select capture_status, captured_at, completeness, is_published
#     from brand_profiles where company_id='04b5cdbc-...';
#   -> capturing | null | 0.13 | false
ESTADO_DE_18_08 = {
    "palette": {},
    "logo_asset_id": None,
    "capture_status": "capturing",
    "captured_at": None,
    "completeness": 0.13,
    # ⚠️ Sem esta linha o UNDO é recusado pelo banco: o CHECK
    # `brand_profiles_published_needs_primary` (migration 20260725_05:148-150)
    # proíbe perfil publicado sem `palette.primary`. Apagar a paleta e deixar
    # `is_published` ligado é uma combinação que o Postgres não aceita — e
    # descobrir isso durante um rollback é o pior momento possível.
    "is_published": False,
}


# --------------------------------------------------------------------------
# Carregamento dos módulos de marca
# --------------------------------------------------------------------------

def _carregar_env() -> tuple[str, str]:
    """Resolve as credenciais ANTES de qualquer import de `app.`.

    A ordem não é detalhe: `brand/web.py` importa `app.core`, cujo
    `__init__.py` instancia `Settings()` no momento do import. Carregar o
    `.env` depois disso é carregar tarde — o processo já morreu.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # noqa: BLE001
        print("[x] dependencia ausente: python-dotenv")
        sys.exit(2)

    for arquivo in (RAIZ / ".env.local", BACKEND / ".env", RAIZ / ".env"):
        if arquivo.exists():
            load_dotenv(arquivo, override=False)

    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    chave = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not chave:
        print("[x] faltam SUPABASE_URL e SUPABASE_KEY (ou "
              "NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)")
        sys.exit(2)
    os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"] = url, chave
    return url, chave


def _carregar_modulos():
    """Monta a árvore de pacotes à mão, sem executar os `__init__.py`.

    Mesmo motivo (e mesmo padrão) de `backend/tools/gerar_visual_acceptance_pack.py`:
    `app/services/__init__.py` importa `AudioService`, que importa `openai`.
    Um script de operação que precisa do SDK da OpenAI instalado para gravar
    uma cor num banco é um script que ninguém consegue rodar quando precisa.

    Os quatro `setdefault` são o mesmo problema pela outra ponta: `app.core.
    config` exige seis variáveis obrigatórias, e `brand/web.py` o importa em
    cadeia. Este script não fala com OpenAI, não cifra nada e não sobe arquivo
    ao MinIO — as quatro que ele não usa recebem marcador. As duas do Supabase
    NÃO recebem: se faltarem, o script tem de parar, e para.
    """
    _carregar_env()
    for chave in ("OPENAI_API_KEY", "ENCRYPTION_KEY",
                  "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"):
        os.environ.setdefault(chave, "nao-usado-por-este-script")

    sys.path.insert(0, str(BACKEND))
    for nome in ("app", "app.services", "app.services.brand"):
        if nome not in sys.modules:
            pkg = types.ModuleType(nome)
            pkg.__path__ = [str(BACKEND.joinpath(*nome.split(".")))]
            sys.modules[nome] = pkg

    def _mod(caminho: str):
        arquivo = str(BACKEND.joinpath(*caminho.split("."))) + ".py"
        spec = importlib.util.spec_from_file_location(caminho, arquivo)
        m = importlib.util.module_from_spec(spec)
        m.__package__ = caminho.rsplit(".", 1)[0]
        sys.modules[caminho] = m
        spec.loader.exec_module(m)
        return m

    _mod("app.services.brand.color")
    extract = _mod("app.services.brand.extract")
    system = _mod("app.services.brand.system")
    _mod("app.services.brand.web")
    capture = _mod("app.services.brand.capture")
    return extract, system, capture


def _cliente():
    """Cliente Supabase com service role. Sem chave, o script para."""
    try:
        from supabase import create_client
    except ImportError as exc:  # noqa: BLE001
        print(f"[x] dependencia ausente: {exc}")
        print("    pip install supabase python-dotenv")
        sys.exit(2)

    url, chave = _carregar_env()
    print(f"    banco: {url}")
    return create_client(url, chave)


# --------------------------------------------------------------------------
# Medição
# --------------------------------------------------------------------------

def medir_logo(caminho: Path, extract) -> dict:
    """Lê o arquivo e devolve o que a marca É — não o que se supõe que ela seja."""
    import hashlib

    dados = caminho.read_bytes()
    a = extract.analisar_logo(dados, "image/png")
    if not a or not a.ink_colors:
        print(f"[x] {caminho.name}: nenhuma cor de tinta legível")
        sys.exit(3)
    if not a.primary:
        print(f"[x] {caminho.name}: sem cor primária cromática")
        sys.exit(3)

    uri = "data:image/png;base64," + base64.b64encode(dados).decode()
    return {
        "bytes": len(dados),
        "data_uri": uri,
        # Só para o SQL comparar o conteúdo sem repetir 6 KB de base64.
        # md5 aqui é chave de igualdade, não de segurança.
        "md5": hashlib.md5(uri.encode()).hexdigest(),
        "width": a.width,
        "height": a.height,
        "has_transparency": a.has_transparency,
        "ink_colors": [c.as_dict() for c in a.ink_colors],
        "primary": a.primary,
        "accent": a.accent,
        "confidence": round(float(a.confidence), 2),
    }


# --------------------------------------------------------------------------
# Leitura do estado
# --------------------------------------------------------------------------

def estado(db, company_id: str) -> dict:
    p = (db.table("brand_profiles").select(
        "id, display_name, palette, logo_asset_id, visual_style, "
        "capture_status, captured_at, completeness, is_published")
        .eq("company_id", company_id).limit(1).execute()).data
    perfil = p[0] if p else {}
    ativos = (db.table("brand_assets")
              .select("id, kind, is_current, byte_size, storage_ref")
              .eq("company_id", company_id).eq("kind", "logo_primary")
              .execute()).data or []
    return {
        "profile_id": perfil.get("id"),
        "display_name": perfil.get("display_name"),
        "palette_primary": (perfil.get("palette") or {}).get("primary"),
        "palette_accent": (perfil.get("palette") or {}).get("accent"),
        # 🔴 A chave sem a qual o render morre. Ver decisão 3.
        "palette_tem_typography": "typography" in (perfil.get("palette") or {}),
        "logo_asset_id": perfil.get("logo_asset_id"),
        "visual_style": perfil.get("visual_style"),
        "capture_status": perfil.get("capture_status"),
        "captured_at": perfil.get("captured_at"),
        "completeness": perfil.get("completeness"),
        "is_published": perfil.get("is_published"),
        "assets_logo_primary": len(ativos),
        "assets_is_current": sum(1 for a in ativos if a.get("is_current")),
        "asset_e_data_uri": any(
            str(a.get("storage_ref") or "").startswith("data:image/")
            for a in ativos if a.get("is_current")),
    }


def _mostrar(rotulo: str, e: dict) -> None:
    print(f"\n  {rotulo}")
    for k, v in e.items():
        print(f"    {k:22} = {v}")


# --------------------------------------------------------------------------
# Instalação
# --------------------------------------------------------------------------

def _paleta_completa(sistema: dict) -> dict:
    """O sistema de design inteiro, do jeito que `render.py` espera achá-lo.

    🔴 As seis primeiras chaves são as que `editar()` grava (capture.py:508-513).
    A sétima, `typography`, é a que ele esquece e sem a qual
    `to_css_variables` (system.py:298) levanta `KeyError` e derruba o render
    da peça inteira. Ver decisão 3 no cabeçalho do arquivo.

    `origin: 'human'` também vem de `editar()`: a cor não foi inferida de site
    nenhum, foi medida no arquivo que a corretora usa como logo.
    """
    return {
        "primary": sistema["primary"],
        "accent": sistema["accent"],
        "scales": sistema["scales"],
        "themes": sistema["themes"],
        "audit": sistema["audit"],
        "typography": sistema["typography"],
        "origin": "human",
    }

def _gravar_asset(db, company_id: str, medida: dict) -> str:
    """Grava (ou reaproveita) a logo em `brand_assets`. Devolve o id.

    DOIS statements, nunca `upsert` — ver decisão 1 no cabeçalho.

    A idempotência é por conteúdo: se já existe um asset desta corretora com
    exatamente este data URI, ele é reaproveitado. Rodar o script duas vezes
    não pode deixar duas logos idênticas no banco disputando o `is_current`,
    porque a segunda seria indistinguível da primeira na hora de investigar
    qualquer coisa.
    """
    existentes = (db.table("brand_assets")
                  .select("id, storage_ref, is_current")
                  .eq("company_id", company_id).eq("kind", "logo_primary")
                  .execute()).data or []
    igual = next((a for a in existentes
                  if a.get("storage_ref") == medida["data_uri"]), None)

    # 1º statement: nenhum `is_current` de pé. O índice parcial
    # `brand_assets_one_current_per_kind` só permite UM por (company, kind), e
    # ele é verificado linha a linha — desligar todos antes é o que torna o
    # passo seguinte sempre válido, inclusive na segunda execução.
    if any(a.get("is_current") for a in existentes):
        (db.table("brand_assets").update({"is_current": False})
         .eq("company_id", company_id).eq("kind", "logo_primary").execute())

    if igual:
        (db.table("brand_assets").update({"is_current": True})
         .eq("id", igual["id"]).execute())
        print(f"    asset reaproveitado (mesmo conteudo): {igual['id']}")
        return igual["id"]

    # 2º statement: insert puro.
    # `storage_ref` recebe o data URI e não um caminho `bucket/path`. 📊 A
    # coluna é `text NOT NULL` sem CHECK de formato, e `render.py:70` procura a
    # logo em `data_uri -> public_url -> storage_ref`, aceitando qualquer um
    # dos três. O nome da coluna promete um caminho de storage que NENHUM
    # código deste repositório escreve — `capture.py:300` já grava ali a URL
    # externa do site. Desvio declarado, registrado em PENDENCIAS (P-223).
    linha = (db.table("brand_assets").insert({
        "company_id": company_id,
        "kind": "logo_primary",
        "storage_ref": medida["data_uri"],
        "mime_type": "image/png",
        "byte_size": medida["bytes"],
        "width": medida["width"],
        "height": medida["height"],
        "has_transparency": medida["has_transparency"],
        "ink_colors": medida["ink_colors"],
        "source_url": None,
        "source_kind": "upload",
        "confidence": 1.00,   # o arquivo é a marca; não há inferência aqui
        "is_current": True,
    }).execute()).data
    if not linha:
        print("[x] insert em brand_assets nao devolveu linha")
        sys.exit(4)
    print(f"    asset novo: {linha[0]['id']}")
    return linha[0]["id"]


def instalar(db, company_id: str, medida: dict, capture, system) -> None:
    servico = capture.BrandCaptureService(db)
    perfil = servico.obter_ou_criar(company_id)

    asset_id = _gravar_asset(db, company_id, medida)

    # `editar()` e não um UPDATE cru: é ele que re-deriva o sistema de design
    # inteiro a partir das duas cores (capture.py:505-512) — escalas, temas,
    # séries de gráfico, contraste conferido — e é ele que marca a procedência
    # como `human_edited`. Sem essa marca, a próxima captura automática do site
    # sobrescreveria a cor medida do arquivo pela cor do tema WordPress, que é
    # exatamente o erro que o cabeçalho de `capture.py` descreve.
    campos = {
        "palette": {"primary": medida["primary"], "accent": medida["accent"]},
        "logo_asset_id": asset_id,
        "visual_style": VISUAL_STYLE,
    }
    if not (perfil.get("display_name") or "").strip():
        c = (db.table("companies").select("company_name")
             .eq("id", company_id).maybe_single().execute()).data or {}
        if c.get("company_name"):
            campos["display_name"] = c["company_name"]

    servico.editar(company_id, campos, user_id=None)

    # 🔴 A sétima chave. `editar()` acabou de gravar uma paleta de seis, e uma
    # paleta de seis derruba `to_css_variables` (system.py:298) — decisão 3 no
    # cabeçalho. Não se reconstrói a paleta aqui: lê-se a que `editar()`
    # gravou e acrescenta-se só o que falta, para que a fonte da verdade
    # continue sendo o caminho de produção.
    atual = (db.table("brand_profiles").select("palette")
             .eq("company_id", company_id).limit(1).execute()).data
    paleta = (atual[0].get("palette") if atual else None) or {}
    if paleta.get("themes") and "typography" not in paleta:
        sistema = system.build_design_system(medida["primary"], medida["accent"])
        paleta["typography"] = sistema["typography"]
        (db.table("brand_profiles").update({"palette": paleta})
         .eq("company_id", company_id).execute())
        print("    paleta completada com 'typography' "
              "(sem ela o render levanta KeyError)")

    # `editar()` carimba `source_detail = 'editado no painel da corretora'`,
    # que é verdade quando a edição vem da tela e mentira quando vem daqui.
    # Reescrever com a ASSINATURA faz duas coisas: conta a origem certa a quem
    # for auditar, e é o que permite ao UNDO reconhecer as SUAS linhas sem
    # encostar nas onze que a corretora gravou pelo painel em 17/08.
    (db.table("brand_field_provenance")
     .update({"source_detail": ASSINATURA})
     .eq("brand_profile_id", perfil["id"])
     # Só os três que são desta instalação. `display_name`, quando entra, é
     # cópia do cadastro da empresa e o UNDO não o desfaz — carimbá-lo daria
     # ao UNDO permissão para apagar uma linha que ele não deve apagar.
     .in_("field_path", ["palette", "logo_asset_id", "visual_style"])
     .execute())

    # Estes três não são campos de marca, são estado da captura — por isso não
    # passam pelo `editar()`, que criaria linha de procedência para eles.
    # 📊 `capture_status` estava em `'capturing'` desde uma captura que nunca
    # terminou: a tela mostraria um spinner eterno. `'manual'` é o que o
    # próprio `capture.py:517` usa para identidade posta à mão, e é a verdade.
    (db.table("brand_profiles").update({
        "capture_status": "manual",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "is_published": True,
    }).eq("company_id", company_id).execute())


def desinstalar(db, company_id: str) -> None:
    """Volta ao estado de 18/08/2026. Nada é apagado de `brand_assets`."""
    perfil = (db.table("brand_profiles").select("id")
              .eq("company_id", company_id).limit(1).execute()).data
    pid = perfil[0]["id"] if perfil else None

    # UM update só: `is_published=False` e `palette={}` têm de chegar juntos ao
    # banco, senão o CHECK recusa o estado intermediário.
    (db.table("brand_profiles").update(dict(ESTADO_DE_18_08))
     .eq("company_id", company_id).execute())

    # Desligar basta, e preserva a auditoria: o asset continua lá, com as cores
    # medidas e a data. Apagar linha para "limpar" é como se perde o histórico
    # que explica por que a peça de ontem está diferente da de hoje.
    (db.table("brand_assets").update({"is_current": False})
     .eq("company_id", company_id).eq("kind", "logo_primary").execute())

    # 🔴 A parte que o UNDO da SPEC esquecia. A instalação marcou `palette`,
    # `logo_asset_id` e `visual_style` como `human_edited=True`, e
    # `capture.py:_protegidos` faz a recaptura PULAR todo campo assim marcado.
    # Sem apagar estas linhas, o UNDO deixaria a corretora num estado pior que
    # o original: sem marca E impedida de capturar uma.
    #
    # O filtro é por `source_detail = ASSINATURA`, nunca por `field_path`: só
    # sai o que ESTE script escreveu. Ver o comentário de ASSINATURA.
    if pid:
        (db.table("brand_field_provenance").delete()
         .eq("brand_profile_id", pid)
         .eq("source_detail", ASSINATURA).execute())


# --------------------------------------------------------------------------
# O mesmo trabalho, em SQL, para quem tem o banco mas não tem o Python
# --------------------------------------------------------------------------

def _lit(v) -> str:
    """Literal SQL. `'` vira `''` — o único escape que o Postgres pede aqui."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (dict, list)):
        return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    return "'" + str(v).replace("'", "''") + "'"


def sql_instalar(company_id: str, medida: dict, sistema: dict) -> str:
    c = _lit(company_id)
    uri = _lit(medida["data_uri"])
    paleta = _paleta_completa(sistema)
    # 📊 `capture.py:_completude` — pesos: logo .26 + palette .24 +
    # display_name .10 + website_url .03 = 0.63. As demais chaves do perfil
    # (about_md, services, contact, tagline, typography) seguem vazias.
    completude = 0.63

    return f"""-- ==========================================================
-- SPEC-081 Bloco E · instalar_marca_resulta.py --emit-sql
-- corretora: {company_id}
-- logo: {medida['width']}x{medida['height']}, {medida['bytes']} bytes
-- primaria medida no pixel: {medida['primary']}  (acento {medida['accent']})
-- ==========================================================

-- 1) Nenhum `is_current` de pe. O indice parcial
--    `brand_assets_one_current_per_kind` so permite UM por (company, kind).
update public.brand_assets set is_current = false
 where company_id = {c} and kind = 'logo_primary';

-- 2) A logo. INSERT PURO -- 📊 `on conflict (company_id, kind)` devolve 42P10
--    aqui, porque o indice unico e PARCIAL. O `where not exists` e a
--    idempotencia: rodar duas vezes nao cria a segunda logo identica.
--    A comparacao e por `md5(storage_ref)` e nao pelo data URI inteiro para o
--    URI de {len(medida['data_uri'])} caracteres aparecer UMA vez neste
--    arquivo. SQL que ninguem consegue ler e SQL que ninguem confere.
insert into public.brand_assets
  (company_id, kind, storage_ref, mime_type, byte_size, width, height,
   has_transparency, ink_colors, source_url, source_kind, confidence, is_current)
select {c}, 'logo_primary', {uri}, 'image/png', {medida['bytes']},
       {medida['width']}, {medida['height']}, {_lit(medida['has_transparency'])},
       {_lit(medida['ink_colors'])}, null, 'upload', 1.00, true
 where not exists (
   select 1 from public.brand_assets
    where company_id = {c} and kind = 'logo_primary'
      and md5(storage_ref) = {_lit(medida['md5'])})
   -- 🔴 Trava de integridade. Este SQL existe para ser COLADO num console, e
   --    6 KB de base64 colados a mao truncam com facilidade. Se o literal
   --    acima nao for byte a byte o arquivo medido, esta linha faz o insert
   --    afetar ZERO linhas -- em vez de gravar uma logo corrompida que so
   --    apareceria quebrada na peca do cliente.
   and md5({uri}) = {_lit(medida['md5'])};

-- 2b) Se a linha ja existia (segunda execucao), religa exatamente uma.
update public.brand_assets set is_current = true
 where id = (select id from public.brand_assets
              where company_id = {c} and kind = 'logo_primary'
                and md5(storage_ref) = {_lit(medida['md5'])}
              order by created_at limit 1);

-- 3) O perfil. Espelha o UPDATE de `editar()` (capture.py:514-519); a paleta
--    e a saida de `build_design_system`, calculada em Python e colada aqui.
update public.brand_profiles
   set palette = {_lit(paleta)},
       logo_asset_id = (select id from public.brand_assets
                         where company_id = {c} and kind = 'logo_primary'
                           and is_current limit 1),
       visual_style = {_lit(VISUAL_STYLE)},
       display_name = coalesce(nullif(trim(coalesce(display_name, '')), ''),
                               (select company_name from public.companies
                                 where id = {c})),
       updated_at = now(), updated_by = null
 where company_id = {c};

-- 4) Procedencia. Espelha o upsert de `editar()` (capture.py:521-533).
--    🔴 ESTE `on conflict` FUNCIONA: `brand_field_provenance_uk` e UNIQUE
--    TOTAL (migration 20260725_05:222), nao parcial. E o contraste que
--    explica por que o do passo 2 nao podia ser usado.
--    Marcar `human_edited` aqui e o que impede a proxima captura automatica
--    de trocar a cor medida no arquivo pela cor do tema WordPress do site.
insert into public.brand_field_provenance
  (company_id, brand_profile_id, field_path, source_kind, source_detail,
   confidence, human_edited, human_edited_at, human_edited_by, captured_at)
select {c}, bp.id, f.campo, 'human',
       {_lit(ASSINATURA)},
       1.0, true, now(), null, now()
  from public.brand_profiles bp,
       (values ('palette'), ('logo_asset_id'), ('visual_style')) as f(campo)
 where bp.company_id = {c}
    on conflict (brand_profile_id, field_path) do update
   set source_kind = excluded.source_kind,
       source_detail = excluded.source_detail,
       confidence = excluded.confidence,
       human_edited = true,
       human_edited_at = excluded.human_edited_at,
       captured_at = excluded.captured_at;

-- 5) Estado da captura. 📊 `capture_status` estava travado em 'capturing'
--    desde uma captura que nunca terminou -- spinner eterno na tela.
--    `is_published` so pode ir a true DEPOIS do passo 3: o CHECK
--    `brand_profiles_published_needs_primary` exige `palette.primary`.
update public.brand_profiles
   set capture_status = 'manual', captured_at = now(),
       is_published = true, completeness = {completude}
 where company_id = {c};

-- 6) A versao, DEPOIS do update -- como `_versionar` (capture.py:466-478),
--    que le o perfil ja atualizado.
insert into public.brand_profile_versions
  (company_id, brand_profile_id, version, snapshot, reason, changed_fields)
select bp.company_id, bp.id,
       coalesce((select max(version) from public.brand_profile_versions v
                  where v.brand_profile_id = bp.id), 0) + 1,
       to_jsonb(bp), 'human_edit',
       array['logo_asset_id', 'palette', 'visual_style']
  from public.brand_profiles bp
 where bp.company_id = {c};
"""


def sql_undo(company_id: str) -> str:
    c = _lit(company_id)
    e = ESTADO_DE_18_08
    return f"""-- ==========================================================
-- SPEC-081 Bloco E · UNDO -- volta ao estado de 18/08/2026
-- ==========================================================

-- 1) UM update so: `is_published=false` e `palette='{{}}'` TEM de chegar
--    juntos, senao o CHECK recusa o estado intermediario.
update public.brand_profiles
   set palette = '{{}}'::jsonb,
       logo_asset_id = null,
       capture_status = {_lit(e['capture_status'])},
       captured_at = null,
       completeness = {e['completeness']},
       is_published = false,
       updated_at = now()
 where company_id = {c};

-- 2) Desligar basta: o asset fica, com as cores medidas e a data. Apagar
--    linha para "limpar" e como se perde o historico que explica por que a
--    peca de ontem esta diferente da de hoje.
update public.brand_assets set is_current = false
 where company_id = {c} and kind = 'logo_primary'
   and storage_ref like 'data:image/png;base64,%';

-- 3) 🔴 A parte que o UNDO da SPEC esquecia. `human_edited=true` faz
--    `capture.py:_protegidos` PULAR o campo na recaptura. Sem isto o UNDO
--    deixaria a corretora pior que no comeco: sem marca E impedida de
--    capturar uma.
--    O filtro e pela ASSINATURA e nao por `field_path`: 📊 a Resulta ja tinha
--    11 linhas `human_edited` gravadas pelo painel em 17/08, e apagar por
--    nome de campo levaria junto decisoes que nao sao deste script.
delete from public.brand_field_provenance
 where source_detail = {_lit(ASSINATURA)}
   and brand_profile_id in (select id from public.brand_profiles
                             where company_id = {c});
"""


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--company", required=True, help="UUID da corretora")
    ap.add_argument("--logo", default=str(LOGO_PADRAO), help="PNG da logo")
    ap.add_argument("--dry-run", action="store_true",
                    help="mede, imprime e NAO escreve nada")
    ap.add_argument("--undo", action="store_true",
                    help="volta ao estado de 18/08/2026")
    ap.add_argument("--emit-sql", action="store_true",
                    help="imprime o SQL equivalente e NAO toca no banco")
    args = ap.parse_args()

    extract, sistema_mod, capture = _carregar_modulos()

    print("\n== MARCA ==")
    caminho = Path(args.logo)
    if not caminho.exists():
        print(f"[x] logo nao encontrada: {caminho}")
        return 3

    medida = medir_logo(caminho, extract)
    print(f"    arquivo   : {caminho.name}  {medida['bytes']} bytes  "
          f"{medida['width']}x{medida['height']}  "
          f"transparencia={medida['has_transparency']}")
    print(f"    primaria  : {medida['primary']}   "
          f"({medida['ink_colors'][0]['ink_share']:.1%} da area de tinta)")
    print(f"    acento    : {medida['accent']}"
          + (f"   ({medida['ink_colors'][1]['ink_share']:.1%})"
             if len(medida["ink_colors"]) > 1 else ""))
    print(f"    confianca : {medida['confidence']}")
    print(f"    data URI  : {len(medida['data_uri'])} caracteres  "
          f"({medida['data_uri'][:30]}...)")
    print(f"    visual_style que sera gravado: {VISUAL_STYLE!r}")

    if args.emit_sql:
        # Não abre conexão nenhuma: este modo existe justamente para a máquina
        # que não tem credencial. O SQL sai no stdout, para colar onde houver.
        sistema = sistema_mod.build_design_system(medida["primary"],
                                                  medida["accent"])
        print("\n== SQL ==")
        print(sql_undo(args.company) if args.undo
              else sql_instalar(args.company, medida, sistema))
        return 0

    db = _cliente()
    antes = estado(db, args.company)
    _mostrar("ANTES", antes)

    if args.dry_run:
        print("\n  --dry-run: NENHUMA escrita foi feita.")
        print("  O que seria gravado:")
        print("    brand_assets  : 1 linha logo_primary, is_current=true, "
              f"storage_ref = <data URI de {len(medida['data_uri'])} chars>")
        print("    brand_profiles: palette(primary/accent + sistema derivado), "
              f"logo_asset_id, visual_style={VISUAL_STYLE!r}, "
              "capture_status='manual', is_published=true")
        return 0

    if args.undo:
        print("\n  UNDO...")
        desinstalar(db, args.company)
    else:
        print("\n  instalando...")
        instalar(db, args.company, medida, capture, sistema_mod)

    depois = estado(db, args.company)
    _mostrar("DEPOIS", depois)

    # VERIFY já executado, para ninguém ter de lembrar de rodar.
    print("\n== VERIFY ==")
    if args.undo:
        ok = (depois["palette_primary"] is None
              and depois["logo_asset_id"] is None
              and depois["is_published"] is False
              and depois["assets_is_current"] == 0)
        print("  voltou ao fallback:", "SIM" if ok else "NAO")
    else:
        ok = (depois["palette_primary"] is not None
              and depois["palette_tem_typography"] is True
              and depois["logo_asset_id"] is not None
              and depois["visual_style"] == VISUAL_STYLE
              and depois["assets_is_current"] == 1
              and depois["asset_e_data_uri"] is True)
        print(f"  palette.primary        : {depois['palette_primary']}")
        print(f"  palette.typography     : {depois['palette_tem_typography']}"
              + ("  [ok]" if depois["palette_tem_typography"]
                 else "  [FALHOU — o render vai levantar KeyError]"))
        print(f"  logo_asset_id          : {depois['logo_asset_id']}")
        print(f"  visual_style           : {depois['visual_style']}"
              + ("  [ok]" if depois["visual_style"] == VISUAL_STYLE
                 else "  [FALHOU — a Cobranca muda de tema]"))
        print(f"  logos is_current       : {depois['assets_is_current']} "
              "(tem de ser 1)")
        print(f"  storage_ref e data URI : {depois['asset_e_data_uri']}")
    print("\n  " + ("VERDE" if ok else "VERMELHO"))
    print(json.dumps({"antes": antes, "depois": depois},
                     ensure_ascii=False, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
