-- =====================================================================
-- SPEC-057 · Bloco A2 — Artifact Hub
-- =====================================================================
-- Até aqui o sistema produzia texto. Texto some no scroll. Um Artefato é
-- resultado com identidade: tem dono, versão, marca, procedência, validade,
-- e pode ser aberto por alguém que nunca entrou no produto.
--
-- Três decisões que sustentam o resto:
--
-- 1) brand_snapshot congelado DENTRO da versão. Se a corretora trocar de
--    marca amanhã, o relatório de hoje não pode se reescrever sozinho — ele
--    é registro de um momento, e um registro que muda depois não vale nada
--    numa reunião com o cliente.
--
-- 2) render separado de version. O mesmo conteúdo vira página, PDF e resumo
--    de WhatsApp. Misturar conteúdo com apresentação obrigaria regerar o
--    relatório inteiro para trocar o formato.
--
-- 3) compartilhamento tem validade obrigatória. Link público eterno criado
--    sem querer é vazamento de dado de segurado com prazo infinito.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Catálogo de templates — versionado como Skill (SPEC-056)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.report_templates (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key   text NOT NULL UNIQUE,
  name           text NOT NULL,
  description    text NOT NULL,
  category       text NOT NULL CHECK (category IN
                   ('executive','financial','commercial','research','portfolio',
                    'renewals','claims','briefing','client_facing')),

  -- Forma narrativa, não assunto. É o que decide a ESTRUTURA da peça:
  -- um relatório liderado por veredito não se monta como um dossiê de pesquisa.
  narrative_shape text NOT NULL CHECK (narrative_shape IN
                   ('verdict_led','precision_led','narrative_led','action_led',
                    'comparative','chronological')),

  -- Público. Muda o tom, o nível de detalhe e o que pode aparecer.
  audience       text NOT NULL DEFAULT 'internal'
                   CHECK (audience IN ('internal','client','insurer','partner')),

  is_active      boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.report_template_releases (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id        uuid NOT NULL REFERENCES public.report_templates(id) ON DELETE CASCADE,
  version            text NOT NULL,

  -- Composição em blocos. O agente recompõe por relatório; o que ele NÃO faz
  -- é inventar CSS — a qualidade visual não pode depender do humor do modelo.
  composition        jsonb NOT NULL DEFAULT '[]'::jsonb,   -- [{block, props, slot}]
  data_contract      jsonb NOT NULL DEFAULT '{}'::jsonb,   -- JSON Schema do payload
  visual_style       text NOT NULL DEFAULT 'aurora'
                       CHECK (visual_style IN ('aurora','obsidian','meridian')),
  page_format        text NOT NULL DEFAULT 'web'
                       CHECK (page_format IN ('web','a4','letter','slide')),
  instruction_md     text NOT NULL DEFAULT '',
  content_hash       text NOT NULL,

  status             text NOT NULL DEFAULT 'draft'
                       CHECK (status IN ('draft','published','deprecated')),
  is_default         boolean NOT NULL DEFAULT false,
  published_at       timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT report_template_releases_uk UNIQUE (template_id, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS report_template_one_default
  ON public.report_template_releases (template_id) WHERE is_default;

-- Publicar é compromisso. Editar o que já saiu como peça é reescrever a régua
-- depois da medida.
CREATE OR REPLACE FUNCTION public.report_template_release_immutable()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.status = 'published' AND (
       NEW.composition   IS DISTINCT FROM OLD.composition   OR
       NEW.data_contract IS DISTINCT FROM OLD.data_contract OR
       NEW.instruction_md IS DISTINCT FROM OLD.instruction_md OR
       NEW.content_hash  IS DISTINCT FROM OLD.content_hash  OR
       NEW.visual_style  IS DISTINCT FROM OLD.visual_style) THEN
    RAISE EXCEPTION 'release publicada e imutavel: crie nova versao';
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_report_template_release_immutable ON public.report_template_releases;
CREATE TRIGGER trg_report_template_release_immutable
  BEFORE UPDATE ON public.report_template_releases
  FOR EACH ROW EXECUTE FUNCTION public.report_template_release_immutable();


-- ---------------------------------------------------------------------
-- 2. artifacts — o resultado como objeto de primeira classe
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.artifacts (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id     uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,

  kind           text NOT NULL DEFAULT 'report' CHECK (kind IN
                   ('report','dossier','proposal','briefing','letter','deck','dataset')),
  title          text NOT NULL,
  subtitle       text,
  summary        text,

  template_key   text REFERENCES public.report_templates(template_key) ON DELETE SET NULL,

  -- Quem pediu e por onde. Sem isto, o artefato aparece no catálogo sem
  -- história e ninguém sabe se pode confiar nele.
  work_run_id    uuid,
  requested_by   uuid,
  origin         text NOT NULL DEFAULT 'chat' CHECK (origin IN
                   ('chat','routine','api','manual','system')),

  status         text NOT NULL DEFAULT 'draft' CHECK (status IN
                   ('draft','generating','ready','failed','archived')),

  current_version integer NOT NULL DEFAULT 0,
  subject_ref    jsonb NOT NULL DEFAULT '{}'::jsonb,   -- {kind:'client', id, label}
  tags           text[] NOT NULL DEFAULT '{}',

  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  archived_at    timestamptz,

  CONSTRAINT artifacts_id_company_uk UNIQUE (id, company_id)
);

CREATE INDEX IF NOT EXISTS artifacts_company_recent_idx
  ON public.artifacts (company_id, created_at DESC) WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS artifacts_work_run_idx
  ON public.artifacts (work_run_id) WHERE work_run_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS artifacts_template_idx ON public.artifacts (template_key);


-- ---------------------------------------------------------------------
-- 3. artifact_versions — imutáveis, com a marca congelada
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.artifact_versions (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id       uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  artifact_id      uuid NOT NULL,
  version          integer NOT NULL,

  -- Conteúdo estruturado, separado da apresentação.
  payload          jsonb NOT NULL DEFAULT '{}'::jsonb,
  composition      jsonb NOT NULL DEFAULT '[]'::jsonb,

  -- A marca no instante da geração. Congelada de propósito.
  brand_snapshot   jsonb NOT NULL DEFAULT '{}'::jsonb,
  template_release_id uuid REFERENCES public.report_template_releases(id) ON DELETE SET NULL,

  -- Procedência dos números. Um relatório bonito com número sem fonte é
  -- pior do que nenhum relatório: ele convence sem poder ser conferido.
  data_sources     jsonb NOT NULL DEFAULT '[]'::jsonb,   -- [{label, kind, ref, as_of}]
  data_as_of       timestamptz,
  confidence_note  text,

  status           text NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft','published','superseded')),
  published_at     timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  created_by       uuid,

  CONSTRAINT artifact_versions_uk UNIQUE (artifact_id, version),
  CONSTRAINT artifact_versions_id_company_uk UNIQUE (id, company_id),
  CONSTRAINT artifact_versions_artifact_same_company_fk
    FOREIGN KEY (artifact_id, company_id)
    REFERENCES public.artifacts (id, company_id) ON DELETE CASCADE,

  -- Versão publicada sem marca sai com a identidade da AutoBrokers no lugar da
  -- corretora. É exatamente a falha que este bloco existe para impedir.
  CONSTRAINT artifact_versions_published_needs_brand CHECK (
    status <> 'published' OR (brand_snapshot ? 'palette' AND brand_snapshot ? 'name')
  )
);

CREATE INDEX IF NOT EXISTS artifact_versions_artifact_idx
  ON public.artifact_versions (artifact_id, version DESC);

CREATE OR REPLACE FUNCTION public.artifact_version_immutable()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.status = 'published' AND (
       NEW.payload        IS DISTINCT FROM OLD.payload OR
       NEW.composition    IS DISTINCT FROM OLD.composition OR
       NEW.brand_snapshot IS DISTINCT FROM OLD.brand_snapshot OR
       NEW.data_sources   IS DISTINCT FROM OLD.data_sources) THEN
    RAISE EXCEPTION 'versao publicada e imutavel: gere nova versao do artefato';
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_artifact_version_immutable ON public.artifact_versions;
CREATE TRIGGER trg_artifact_version_immutable
  BEFORE UPDATE ON public.artifact_versions
  FOR EACH ROW EXECUTE FUNCTION public.artifact_version_immutable();


-- ---------------------------------------------------------------------
-- 4. artifact_renders — o mesmo conteúdo em vários formatos
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.artifact_renders (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id          uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  artifact_version_id uuid NOT NULL,

  format              text NOT NULL CHECK (format IN
                        ('html','pdf','png','markdown','whatsapp_text','email_html','csv')),
  storage_ref         text,
  inline_content      text,          -- formatos curtos não merecem ida ao storage
  byte_size           integer,
  page_count          integer,
  checksum            text,

  status              text NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','rendering','ready','failed')),
  error               text,
  duration_ms         integer,
  created_at          timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT artifact_renders_uk UNIQUE (artifact_version_id, format),
  CONSTRAINT artifact_renders_version_same_company_fk
    FOREIGN KEY (artifact_version_id, company_id)
    REFERENCES public.artifact_versions (id, company_id) ON DELETE CASCADE,

  -- Render pronto que não aponta para lugar nenhum é estado mentiroso: a UI
  -- mostra "pronto" e o download falha.
  CONSTRAINT artifact_renders_ready_has_content CHECK (
    status <> 'ready' OR storage_ref IS NOT NULL OR inline_content IS NOT NULL
  )
);


-- ---------------------------------------------------------------------
-- 5. artifact_shares — link público, com prazo
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.artifact_shares (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id          uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  artifact_id         uuid NOT NULL,
  artifact_version_id uuid NOT NULL,

  token               text NOT NULL UNIQUE,
  -- 32 chars é o piso de entropia. Token curto em URL pública é adivinhável,
  -- e do outro lado do link tem dado de segurado.
  CONSTRAINT artifact_shares_token_entropy CHECK (length(token) >= 32),

  audience_label      text,           -- "Cliente X", "Diretoria" — para o log
  password_hash       text,
  expires_at          timestamptz NOT NULL,
  max_views           integer CHECK (max_views IS NULL OR max_views > 0),
  view_count          integer NOT NULL DEFAULT 0,

  -- Marca de quem compartilha, não de quem hospeda. O corretor manda o link e
  -- o cliente vê a corretora — não a AutoBrokers.
  white_label         boolean NOT NULL DEFAULT true,

  revoked_at          timestamptz,
  revoked_by          uuid,
  created_at          timestamptz NOT NULL DEFAULT now(),
  created_by          uuid,
  last_viewed_at      timestamptz,

  CONSTRAINT artifact_shares_artifact_same_company_fk
    FOREIGN KEY (artifact_id, company_id)
    REFERENCES public.artifacts (id, company_id) ON DELETE CASCADE,
  CONSTRAINT artifact_shares_version_same_company_fk
    FOREIGN KEY (artifact_version_id, company_id)
    REFERENCES public.artifact_versions (id, company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS artifact_shares_live_idx
  ON public.artifact_shares (company_id, created_at DESC) WHERE revoked_at IS NULL;

-- Compartilhar rascunho é vazar número que ainda vai mudar.
CREATE OR REPLACE FUNCTION public.artifact_share_requires_published()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE v_status text;
BEGIN
  SELECT status INTO v_status FROM public.artifact_versions WHERE id = NEW.artifact_version_id;
  IF v_status IS DISTINCT FROM 'published' THEN
    RAISE EXCEPTION 'so versao publicada pode ser compartilhada (status atual: %)', coalesce(v_status,'inexistente');
  END IF;
  IF NEW.expires_at <= now() THEN
    RAISE EXCEPTION 'validade do compartilhamento precisa estar no futuro';
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_artifact_share_requires_published ON public.artifact_shares;
CREATE TRIGGER trg_artifact_share_requires_published
  BEFORE INSERT ON public.artifact_shares
  FOR EACH ROW EXECUTE FUNCTION public.artifact_share_requires_published();


-- ---------------------------------------------------------------------
-- 6. artifact_events — trilha append-only
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.artifact_events (
  id             bigserial PRIMARY KEY,
  company_id     uuid NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  artifact_id    uuid NOT NULL,
  event_type     text NOT NULL,       -- artifact.created, version.published, share.viewed...
  actor_kind     text NOT NULL DEFAULT 'system'
                   CHECK (actor_kind IN ('user','agent','system','public')),
  actor_id       uuid,
  detail         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at     timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT artifact_events_artifact_same_company_fk
    FOREIGN KEY (artifact_id, company_id)
    REFERENCES public.artifacts (id, company_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS artifact_events_artifact_idx
  ON public.artifact_events (artifact_id, created_at DESC);

CREATE OR REPLACE FUNCTION public.artifact_events_append_only()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'artifact_events e append-only: UPDATE proibido';
  END IF;
  IF TG_OP = 'DELETE'
     AND coalesce(current_setting('app.artifact_events_purge', true), 'off') <> 'on' THEN
    RAISE EXCEPTION 'DELETE em artifact_events exige app.artifact_events_purge=on';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

DROP TRIGGER IF EXISTS trg_artifact_events_append_only ON public.artifact_events;
CREATE TRIGGER trg_artifact_events_append_only
  BEFORE UPDATE OR DELETE ON public.artifact_events
  FOR EACH ROW EXECUTE FUNCTION public.artifact_events_append_only();


-- ---------------------------------------------------------------------
-- 7. RLS — fail-closed
-- ---------------------------------------------------------------------
ALTER TABLE public.report_templates          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_template_releases  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifacts                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifact_versions         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifact_renders          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifact_shares           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.artifact_events           ENABLE ROW LEVEL SECURITY;


-- ---------------------------------------------------------------------
-- VERIFY
-- ---------------------------------------------------------------------
-- select count(*) from information_schema.tables where table_schema='public'
--  and table_name in ('report_templates','report_template_releases','artifacts',
--    'artifact_versions','artifact_renders','artifact_shares','artifact_events');  -- 7
--
-- ROLLBACK
-- drop table if exists public.artifact_events, public.artifact_shares, public.artifact_renders,
--   public.artifact_versions, public.artifacts, public.report_template_releases,
--   public.report_templates cascade;
