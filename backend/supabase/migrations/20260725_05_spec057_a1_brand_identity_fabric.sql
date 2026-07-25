-- =====================================================================
-- SPEC-057 · Bloco A1 — Brand Identity Fabric
-- =====================================================================
-- Toda peça que a AutoBrokers entrega em nome de uma corretora precisa
-- parecer propriedade DELA. Para isso a marca precisa existir como dado
-- governado — não como campo solto de configuração.
--
-- Cinco objetos, cada um com uma razão:
--   brand_profiles          identidade efetiva (a que vale agora)
--   brand_assets            logos e imagens, com variantes derivadas
--   brand_sources           onde olhamos e o que voltou
--   brand_field_provenance  de onde veio CADA campo, e com que confiança
--   brand_profile_versions  histórico append-only para reverter
--
-- O quarto é o que separa isto de "scraping bonitinho": captura automática
-- sem procedência é mágica não-verificável, e mágica não-verificável em
-- material que vai ao cliente final é passivo, não ativo. O corretor precisa
-- poder ver de onde veio a cor, conferir e discordar.
--
-- APPLY: idempotente. VERIFY e ROLLBACK ao final do arquivo, em comentário.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. brand_assets — logos e imagens
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.brand_assets (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id        uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,

  -- Papel do arquivo. Uma marca precisa de mais de um: o logo colorido não
  -- funciona sobre fundo escuro, e o favicon não funciona numa capa A4.
  kind              text NOT NULL CHECK (kind IN (
                      'logo_primary',     -- lockup principal, como está no site
                      'logo_light_bg',    -- variante para fundo claro
                      'logo_dark_bg',     -- variante para fundo escuro
                      'logo_mono',        -- monocromático (carimbo, marca d'água)
                      'symbol',           -- só o símbolo, sem tipografia
                      'favicon',
                      'og_image',
                      'photo',            -- foto de equipe/fachada
                      'pattern')),        -- textura/grafismo de apoio

  storage_ref       text NOT NULL,        -- caminho canônico bucket/path (SPEC-054)
  mime_type         text,
  byte_size         integer,
  width             integer,
  height            integer,
  has_transparency  boolean,

  -- Cores medidas DENTRO do arquivo, ponderadas por área de tinta opaca.
  -- Fundo transparente não vota. É o sinal mais confiável de cor de marca
  -- que existe — muito acima do CSS, que em tema pronto é cor do tema.
  ink_colors        jsonb NOT NULL DEFAULT '[]'::jsonb,  -- [{hex, ink_share, saturation, luminance}]

  source_url        text,
  source_kind       text NOT NULL DEFAULT 'derived' CHECK (source_kind IN
                      ('website','instagram','linkedin','google_business','upload','derived')),
  derived_from_id   uuid REFERENCES public.brand_assets(id) ON DELETE SET NULL,

  confidence        numeric(3,2) NOT NULL DEFAULT 0.50 CHECK (confidence BETWEEN 0 AND 1),
  is_current        boolean NOT NULL DEFAULT true,

  created_at        timestamptz NOT NULL DEFAULT now(),
  created_by        uuid,

  -- Permite FK composta a partir de artefatos: referenciar um asset SEM
  -- carregar junto o company_id torna o vazamento entre tenants sintaticamente
  -- possível. Com a composta, é impossível escrever a linha errada.
  CONSTRAINT brand_assets_id_company_uk UNIQUE (id, company_id)
);

CREATE INDEX IF NOT EXISTS brand_assets_company_kind_idx
  ON public.brand_assets (company_id, kind) WHERE is_current;
CREATE INDEX IF NOT EXISTS brand_assets_derived_from_idx
  ON public.brand_assets (derived_from_id) WHERE derived_from_id IS NOT NULL;

-- Um "atual" por papel. Duas logos primárias ativas é ambiguidade que só
-- aparece na hora de gerar o PDF, quando já é tarde.
CREATE UNIQUE INDEX IF NOT EXISTS brand_assets_one_current_per_kind
  ON public.brand_assets (company_id, kind) WHERE is_current;


-- ---------------------------------------------------------------------
-- 2. brand_profiles — a identidade efetiva
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.brand_profiles (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id          uuid NOT NULL UNIQUE REFERENCES public.companies(id) ON DELETE CASCADE,

  -- Fontes declaradas pelo corretor. Nada é capturado sem ele apontar onde.
  website_url         text,
  instagram_url       text,
  linkedin_url        text,
  google_business_url text,
  facebook_url        text,

  -- Identidade textual
  display_name        text,
  legal_name          text,
  tagline             text,
  mission             text,
  about_md            text,
  services            jsonb NOT NULL DEFAULT '[]'::jsonb,  -- [{name, description, audience}]
  differentiators     jsonb NOT NULL DEFAULT '[]'::jsonb,
  service_area        text,
  founded_year        integer CHECK (founded_year IS NULL OR founded_year BETWEEN 1800 AND 2200),
  susep_code          text,

  contact             jsonb NOT NULL DEFAULT '{}'::jsonb,  -- {phones[], emails[], whatsapp, address{}}
  insurers            jsonb NOT NULL DEFAULT '[]'::jsonb,  -- seguradoras parceiras citadas

  -- Identidade visual. Guardado como objeto de valor porque é sempre lido e
  -- escrito inteiro, e porque é ele que é congelado dentro do artefato.
  palette             jsonb NOT NULL DEFAULT '{}'::jsonb,
  typography          jsonb NOT NULL DEFAULT '{}'::jsonb,
  logo_asset_id       uuid,
  visual_style        text NOT NULL DEFAULT 'aurora'
                        CHECK (visual_style IN ('aurora','obsidian','meridian')),

  -- Voz. O agente escreve o relatório; sem isto ele escreve como AutoBrokers,
  -- não como a corretora.
  tone                jsonb NOT NULL DEFAULT '{}'::jsonb,  -- {formality, warmth, person, avoid[]}

  capture_status      text NOT NULL DEFAULT 'empty' CHECK (capture_status IN
                        ('empty','capturing','captured','partial','failed','manual')),
  captured_at         timestamptz,
  capture_run_id      uuid,
  capture_error       text,

  -- 0..1 — quanto da identidade está preenchida. Vira a barra de progresso da
  -- tela e o gate de "pronto para gerar peça".
  completeness        numeric(3,2) NOT NULL DEFAULT 0 CHECK (completeness BETWEEN 0 AND 1),
  is_published        boolean NOT NULL DEFAULT false,

  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  updated_by          uuid,

  CONSTRAINT brand_profiles_id_company_uk UNIQUE (id, company_id),

  -- Composta: o logo do perfil TEM de ser um asset da mesma corretora.
  CONSTRAINT brand_profiles_logo_same_company_fk
    FOREIGN KEY (logo_asset_id, company_id)
    REFERENCES public.brand_assets (id, company_id) ON DELETE SET NULL,

  -- Publicar é declarar "pode ir ao cliente". Sem cor primária, toda peça sai
  -- com a cor da AutoBrokers e a promessa de personalização é falsa.
  CONSTRAINT brand_profiles_published_needs_primary CHECK (
    NOT is_published OR (palette ? 'primary' AND palette->>'primary' IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS brand_profiles_status_idx
  ON public.brand_profiles (capture_status) WHERE capture_status IN ('capturing','failed');


-- ---------------------------------------------------------------------
-- 3. brand_sources — onde olhamos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.brand_sources (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id     uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  brand_profile_id uuid NOT NULL,

  kind           text NOT NULL CHECK (kind IN
                   ('website','instagram','linkedin','google_business','facebook','manual','logo_pixels')),
  url            text,
  status         text NOT NULL DEFAULT 'pending' CHECK (status IN
                   ('pending','fetched','failed','skipped','blocked')),

  http_status    integer,
  fetched_at     timestamptz,
  duration_ms    integer,
  error          text,

  -- Só o resumo estruturado, nunca a página inteira: o corpo bruto é grande,
  -- envelhece rápido e pode conter dado pessoal que não pedimos.
  extract        jsonb NOT NULL DEFAULT '{}'::jsonb,
  content_hash   text,

  created_at     timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT brand_sources_profile_same_company_fk
    FOREIGN KEY (brand_profile_id, company_id)
    REFERENCES public.brand_profiles (id, company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS brand_sources_profile_idx
  ON public.brand_sources (brand_profile_id, kind);


-- ---------------------------------------------------------------------
-- 4. brand_field_provenance — de onde veio cada campo
-- ---------------------------------------------------------------------
-- Sem isto, o corretor abre a tela e vê uma cor que ele não escolheu, um texto
-- que ele não escreveu, e não tem como saber se aquilo é o site dele ou uma
-- invenção. Procedência transforma automação em algo auditável.
CREATE TABLE IF NOT EXISTS public.brand_field_provenance (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id       uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  brand_profile_id uuid NOT NULL,

  field_path       text NOT NULL,        -- 'palette.primary', 'tagline', 'services'
  source_id        uuid REFERENCES public.brand_sources(id) ON DELETE SET NULL,
  source_kind      text NOT NULL CHECK (source_kind IN
                     ('website','instagram','linkedin','google_business','facebook',
                      'logo_pixels','inferred','default','human')),
  source_detail    text,                 -- URL exata, seletor, "PLTE do logo"
  confidence       numeric(3,2) NOT NULL DEFAULT 0.50 CHECK (confidence BETWEEN 0 AND 1),

  -- Depois que o humano edita, nenhuma recaptura sobrescreve. Autonomia que
  -- desfaz decisão humana não é autonomia, é perda de controle.
  human_edited     boolean NOT NULL DEFAULT false,
  human_edited_at  timestamptz,
  human_edited_by  uuid,

  captured_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT brand_field_provenance_profile_same_company_fk
    FOREIGN KEY (brand_profile_id, company_id)
    REFERENCES public.brand_profiles (id, company_id) ON DELETE CASCADE,
  CONSTRAINT brand_field_provenance_uk UNIQUE (brand_profile_id, field_path),

  -- Marcar como editado por humano sem dizer quando é registro que não prova nada.
  CONSTRAINT brand_field_provenance_human_needs_stamp CHECK (
    NOT human_edited OR human_edited_at IS NOT NULL
  )
);

CREATE INDEX IF NOT EXISTS brand_field_provenance_human_idx
  ON public.brand_field_provenance (brand_profile_id) WHERE human_edited;


-- ---------------------------------------------------------------------
-- 5. brand_profile_versions — histórico append-only
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.brand_profile_versions (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id       uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  brand_profile_id uuid NOT NULL,

  version          integer NOT NULL,
  snapshot         jsonb NOT NULL,       -- perfil inteiro no momento
  reason           text NOT NULL CHECK (reason IN
                     ('capture','human_edit','recapture','revert','seed')),
  changed_fields   text[] NOT NULL DEFAULT '{}',

  created_at       timestamptz NOT NULL DEFAULT now(),
  created_by       uuid,

  CONSTRAINT brand_profile_versions_profile_same_company_fk
    FOREIGN KEY (brand_profile_id, company_id)
    REFERENCES public.brand_profiles (id, company_id) ON DELETE CASCADE,
  CONSTRAINT brand_profile_versions_uk UNIQUE (brand_profile_id, version)
);

-- Histórico que pode ser editado não é histórico.
CREATE OR REPLACE FUNCTION public.brand_versions_append_only()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'brand_profile_versions e append-only: UPDATE proibido';
  END IF;
  -- DELETE só na intenção declarada (offboarding, LGPD). CASCADE legítimo
  -- precisa passar por aqui, então não se bloqueia DELETE de forma absoluta.
  IF TG_OP = 'DELETE'
     AND coalesce(current_setting('app.brand_versions_purge', true), 'off') <> 'on' THEN
    RAISE EXCEPTION 'DELETE em brand_profile_versions exige app.brand_versions_purge=on';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

DROP TRIGGER IF EXISTS trg_brand_versions_append_only ON public.brand_profile_versions;
CREATE TRIGGER trg_brand_versions_append_only
  BEFORE UPDATE OR DELETE ON public.brand_profile_versions
  FOR EACH ROW EXECUTE FUNCTION public.brand_versions_append_only();


-- ---------------------------------------------------------------------
-- 6. RLS — fail-closed, igual ao resto da casa
-- ---------------------------------------------------------------------
ALTER TABLE public.brand_assets            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_sources           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_field_provenance  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_profile_versions  ENABLE ROW LEVEL SECURITY;
-- Sem policy: nada passa a não ser service_role, que faz bypass. A API é quem
-- filtra por tenant. Mesma disciplina de work_runs e skills.


-- ---------------------------------------------------------------------
-- VERIFY
-- ---------------------------------------------------------------------
-- select count(*) from information_schema.tables where table_schema='public'
--   and table_name in ('brand_profiles','brand_assets','brand_sources',
--                      'brand_field_provenance','brand_profile_versions');  -- 5
--
-- ROLLBACK
-- drop table if exists public.brand_profile_versions, public.brand_field_provenance,
--   public.brand_sources, public.brand_profiles, public.brand_assets cascade;
-- drop function if exists public.brand_versions_append_only();
