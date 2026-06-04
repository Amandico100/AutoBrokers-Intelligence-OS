-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: check_and_increment_rate_limit(text, uuid, integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_and_increment_rate_limit(p_identifier text, p_agent_id uuid, p_max_requests integer DEFAULT 50, p_window_minutes integer DEFAULT 60) RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_record RECORD;
    v_new_count INTEGER;
    v_window_seconds INTEGER;
BEGIN
    v_window_seconds := p_window_minutes * 60;

    SELECT id, request_count, window_start
    INTO v_record
    FROM widget_rate_limits
    WHERE identifier = p_identifier AND agent_id = p_agent_id
    FOR UPDATE;

    IF FOUND THEN
        IF EXTRACT(EPOCH FROM (NOW() - v_record.window_start)) > v_window_seconds THEN
            UPDATE widget_rate_limits
            SET request_count = 1, window_start = NOW()
            WHERE id = v_record.id;
            RETURN 1;
        END IF;

        IF v_record.request_count >= p_max_requests THEN
            RETURN -1;
        END IF;

        UPDATE widget_rate_limits
        SET request_count = request_count + 1
        WHERE id = v_record.id
        RETURNING request_count INTO v_new_count;

        RETURN v_new_count;
    ELSE
        INSERT INTO widget_rate_limits (identifier, identifier_type, agent_id, request_count, window_start)
        VALUES (p_identifier, 'session', p_agent_id, 1, NOW())
        ON CONFLICT (identifier, agent_id, identifier_type) DO UPDATE
        SET request_count = widget_rate_limits.request_count + 1
        RETURNING request_count INTO v_new_count;

        RETURN COALESCE(v_new_count, 1);
    END IF;
END;
$$;


--
-- Name: create_user_account(character varying, character varying, character varying, character varying, character varying, character varying, date, uuid, character varying, character varying, boolean); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid DEFAULT NULL::uuid, p_status character varying DEFAULT 'pending'::character varying, p_role character varying DEFAULT 'member'::character varying, p_is_owner boolean DEFAULT false) RETURNS TABLE(id uuid, email character varying, first_name character varying, last_name character varying, company_id uuid, role character varying, status character varying, is_owner boolean, created_at timestamp without time zone)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM users_v2 WHERE users_v2.email = p_email) THEN
        RAISE EXCEPTION 'Email already exists';
    END IF;

    IF p_role NOT IN ('admin_company', 'member') THEN
        RAISE EXCEPTION 'Invalid role';
    END IF;

    IF p_status NOT IN ('active', 'pending', 'suspended') THEN
        RAISE EXCEPTION 'Invalid status';
    END IF;

    IF p_role = 'member' AND p_is_owner = TRUE THEN
        RAISE EXCEPTION 'Members cannot be owners';
    END IF;

    RETURN QUERY
    INSERT INTO users_v2 (
        first_name, last_name, email, password_hash, cpf, phone, birth_date,
        company_id, status, role, is_owner,
        terms_accepted_at, privacy_policy_accepted_at, created_at, updated_at
    ) VALUES (
        p_first_name, p_last_name, p_email, p_password_hash, p_cpf, p_phone, p_birth_date,
        p_company_id, p_status, p_role, p_is_owner,
        NOW(), NOW(), NOW(), NOW()
    )
    RETURNING 
        users_v2.id, users_v2.email, users_v2.first_name, users_v2.last_name,
        users_v2.company_id, users_v2.role, users_v2.status, users_v2.is_owner,
        users_v2.created_at;
END;
$$;


--
-- Name: create_user_account(character varying, character varying, character varying, character varying, character varying, character varying, date, uuid, character varying, character varying, boolean, uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid DEFAULT NULL::uuid, p_status character varying DEFAULT 'pending'::character varying, p_role character varying DEFAULT 'member'::character varying, p_is_owner boolean DEFAULT false, p_accepted_terms_version uuid DEFAULT NULL::uuid) RETURNS TABLE(id uuid, email character varying, first_name character varying, last_name character varying, company_id uuid, role character varying, status character varying, is_owner boolean, created_at timestamp without time zone)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM users_v2 WHERE users_v2.email = p_email) THEN
        RAISE EXCEPTION 'Email already exists';
    END IF;

    IF p_role NOT IN ('admin_company', 'member') THEN
        RAISE EXCEPTION 'Invalid role';
    END IF;

    IF p_status NOT IN ('active', 'pending', 'suspended') THEN
        RAISE EXCEPTION 'Invalid status';
    END IF;

    IF p_role = 'member' AND p_is_owner = TRUE THEN
        RAISE EXCEPTION 'Members cannot be owners';
    END IF;

    RETURN QUERY
    INSERT INTO users_v2 (
        first_name, last_name, email, password_hash, cpf, phone, birth_date,
        company_id, status, role, is_owner,
        terms_accepted_at, privacy_policy_accepted_at,
        accepted_terms_version,
        created_at, updated_at
    ) VALUES (
        p_first_name, p_last_name, p_email, p_password_hash, p_cpf, p_phone, p_birth_date,
        p_company_id, p_status, p_role, p_is_owner,
        NOW(), NOW(),
        p_accepted_terms_version,
        NOW(), NOW()
    )
    RETURNING 
        users_v2.id, users_v2.email, users_v2.first_name, users_v2.last_name,
        users_v2.company_id, users_v2.role, users_v2.status, users_v2.is_owner,
        users_v2.created_at;
END;
$$;


--
-- Name: debit_company_balance(uuid, numeric); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.debit_company_balance(p_company_id uuid, p_amount numeric) RETURNS numeric
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_new_balance NUMERIC;
BEGIN
    UPDATE company_credits
    SET 
        balance_brl = balance_brl - p_amount,
        updated_at = NOW()
    WHERE company_id = p_company_id
    RETURNING balance_brl INTO v_new_balance;
    
    IF NOT FOUND THEN
        INSERT INTO company_credits (company_id, balance_brl, updated_at)
        VALUES (p_company_id, -p_amount, NOW())
        RETURNING balance_brl INTO v_new_balance;
    END IF;
    
    RETURN v_new_balance;
END;
$$;


--
-- Name: get_agent_ucp_capabilities(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_agent_ucp_capabilities(p_agent_id uuid) RETURNS TABLE(store_url text, capability text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        uc.store_url,
        unnest(uc.capabilities_enabled) as capability
    FROM public.ucp_connections uc
    WHERE uc.agent_id = p_agent_id
    AND uc.is_active = true;
END;
$$;


--
-- Name: get_token_usage_by_company(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_token_usage_by_company(start_date timestamp with time zone, end_date timestamp with time zone) RETURNS TABLE(company_id uuid, company_name text, total_calls bigint, total_input bigint, total_output bigint, total_cost numeric)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.company_id,
    COALESCE(c.company_name::TEXT, 'Sistema Interno') as company_name,
    COUNT(*) as total_calls,
    COALESCE(SUM(t.input_tokens), 0)::BIGINT as total_input,
    COALESCE(SUM(t.output_tokens), 0)::BIGINT as total_output,
    COALESCE(SUM(t.total_cost_usd), 0) as total_cost
  FROM token_usage_logs t
  LEFT JOIN companies c ON t.company_id = c.id
  WHERE t.created_at >= start_date AND t.created_at <= end_date
  GROUP BY t.company_id, c.company_name
  ORDER BY total_cost DESC;
END;
$$;


--
-- Name: get_token_usage_report(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_token_usage_report(start_date timestamp with time zone, end_date timestamp with time zone) RETURNS TABLE(company_name text, service_type text, model_name text, total_calls bigint, total_input bigint, total_output bigint, total_cost numeric)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    COALESCE(c.company_name::TEXT, 'Sistema Interno') as company_name,
    t.service_type::TEXT,
    t.model_name::TEXT,
    COUNT(*) as total_calls,
    COALESCE(SUM(t.input_tokens), 0)::BIGINT as total_input,
    COALESCE(SUM(t.output_tokens), 0)::BIGINT as total_output,
    COALESCE(SUM(t.total_cost_usd), 0) as total_cost
  FROM token_usage_logs t
  LEFT JOIN companies c ON t.company_id = c.id
  WHERE t.created_at >= start_date AND t.created_at <= end_date
  GROUP BY c.company_name, t.service_type, t.model_name
  ORDER BY total_cost DESC;
END;
$$;


--
-- Name: get_user_for_login(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_user_for_login(p_email character varying) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
  v_result jsonb;
BEGIN
  SELECT jsonb_build_object(
    'id', u.id,
    'email', u.email,
    'password_hash', u.password_hash,
    'first_name', u.first_name,
    'last_name', u.last_name,
    'status', u.status,
    'plan_id', u.plan_id,
    'company_id', u.company_id,
    'failed_login_attempts', u.failed_login_attempts,
    'account_locked_until', u.account_locked_until,
    'company_status', c.status,
    'webhook_url', c.webhook_url
  )
  INTO v_result
  FROM users_v2 u
  LEFT JOIN companies c ON u.company_id = c.id
  WHERE u.email = p_email AND u.deleted_at IS NULL;

  RETURN v_result;
END;
$$;


--
-- Name: update_agent_delegations_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_agent_delegations_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


--
-- Name: update_documents_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_documents_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_ucp_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_ucp_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    name character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    reset_token text,
    reset_token_expires_at timestamp with time zone,
    password_migrated_at timestamp with time zone,
    reset_attempts integer DEFAULT 0
);


--
-- Name: agent_delegations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_delegations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    orchestrator_id uuid NOT NULL,
    subagent_id uuid NOT NULL,
    task_description text NOT NULL,
    is_active boolean DEFAULT true,
    max_context_chars integer DEFAULT 2000,
    timeout_seconds integer DEFAULT 30,
    max_iterations integer DEFAULT 5,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT no_self_delegation CHECK ((orchestrator_id <> subagent_id))
);


--
-- Name: agent_http_tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_http_tools (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_id uuid NOT NULL,
    name character varying(64) NOT NULL,
    description text NOT NULL,
    method character varying(10) DEFAULT 'GET'::character varying,
    url text NOT NULL,
    headers jsonb DEFAULT '{}'::jsonb,
    parameters jsonb DEFAULT '[]'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    body_template jsonb
);


--
-- Name: agent_mcp_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_mcp_connections (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_id uuid NOT NULL,
    mcp_server_id uuid NOT NULL,
    access_token text,
    refresh_token text,
    token_expires_at timestamp with time zone,
    scopes_granted jsonb,
    is_active boolean DEFAULT true,
    connected_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: agent_mcp_tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_mcp_tools (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_id uuid NOT NULL,
    mcp_server_id uuid NOT NULL,
    mcp_server_name character varying(100) NOT NULL,
    tool_name character varying(100) NOT NULL,
    variable_name character varying(150) NOT NULL,
    description text,
    input_schema jsonb,
    is_enabled boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    is_active boolean DEFAULT true,
    llm_provider character varying(50),
    llm_model character varying(100),
    llm_api_key text,
    llm_temperature numeric(3,2) DEFAULT 0.7,
    llm_max_tokens integer DEFAULT 2000,
    llm_top_p numeric(3,2) DEFAULT 1.0,
    llm_top_k integer DEFAULT 40,
    llm_frequency_penalty numeric(3,2) DEFAULT 0.0,
    llm_presence_penalty numeric(3,2) DEFAULT 0.0,
    agent_system_prompt text,
    agent_enabled boolean DEFAULT true,
    use_langchain boolean DEFAULT false,
    allow_web_search boolean DEFAULT true,
    allow_vision boolean DEFAULT false,
    vision_model text,
    vision_api_key text,
    tools_config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    avatar_url text,
    reasoning_effort character varying(10) DEFAULT 'medium'::character varying,
    verbosity character varying(10) DEFAULT 'medium'::character varying,
    is_hyde_enabled boolean DEFAULT false,
    widget_config jsonb DEFAULT '{}'::jsonb,
    security_settings jsonb DEFAULT '{"enabled": false, "check_nsfw": true, "check_urls": false, "pii_action": "mask", "custom_regex": [], "error_message": "Sua mensagem viola as políticas de segurança.", "url_whitelist": [], "allowed_topics": [], "check_jailbreak": true, "check_secret_keys": true}'::jsonb,
    is_subagent boolean DEFAULT false,
    allow_direct_chat boolean DEFAULT false,
    retrieval_mode text DEFAULT 'semantic'::text NOT NULL,
    CONSTRAINT check_retrieval_mode CHECK ((retrieval_mode = ANY (ARRAY['semantic'::text, 'filesystem'::text]))),
    CONSTRAINT chk_reasoning_effort CHECK (((reasoning_effort IS NULL) OR ((reasoning_effort)::text = ANY (ARRAY[('none'::character varying)::text, ('low'::character varying)::text, ('medium'::character varying)::text, ('high'::character varying)::text])))),
    CONSTRAINT chk_verbosity CHECK (((verbosity IS NULL) OR ((verbosity)::text = ANY (ARRAY[('low'::character varying)::text, ('medium'::character varying)::text, ('high'::character varying)::text]))))
);


--
-- Name: COLUMN agents.is_subagent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.is_subagent IS 'Se true, esconde widget/WhatsApp/canais públicos no frontend';


--
-- Name: COLUMN agents.allow_direct_chat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents.allow_direct_chat IS 'Se true, subagent aparece no chat test para o admin treinar/debugar';


--
-- Name: checkpoint_blobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checkpoint_blobs (
    thread_id text NOT NULL,
    checkpoint_ns text DEFAULT ''::text NOT NULL,
    channel text NOT NULL,
    version text NOT NULL,
    type text NOT NULL,
    blob bytea
);


--
-- Name: checkpoint_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checkpoint_migrations (
    v integer NOT NULL
);


--
-- Name: checkpoint_writes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checkpoint_writes (
    thread_id text NOT NULL,
    checkpoint_ns text DEFAULT ''::text NOT NULL,
    checkpoint_id text NOT NULL,
    task_id text NOT NULL,
    idx integer NOT NULL,
    channel text NOT NULL,
    type text,
    blob bytea NOT NULL,
    task_path text DEFAULT ''::text NOT NULL
);


--
-- Name: checkpoints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checkpoints (
    thread_id text NOT NULL,
    checkpoint_ns text DEFAULT ''::text NOT NULL,
    checkpoint_id text NOT NULL,
    parent_checkpoint_id text,
    type text,
    checkpoint jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: companies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.companies (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_name character varying(255) NOT NULL,
    legal_name character varying(255),
    cnpj character varying(18),
    webhook_url text,
    n8n_instance_url text,
    plan_type character varying(50) DEFAULT 'starter'::character varying,
    monthly_fee numeric(10,2) DEFAULT 0,
    setup_fee numeric(10,2) DEFAULT 0,
    max_users integer DEFAULT 5,
    status character varying(20) DEFAULT 'active'::character varying,
    primary_contact_name character varying(255),
    primary_contact_email character varying(255),
    primary_contact_phone character varying(20),
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    use_langchain boolean DEFAULT false,
    agent_enabled boolean DEFAULT false,
    llm_provider character varying(50),
    llm_model character varying(100),
    llm_api_key text,
    llm_temperature numeric(3,2) DEFAULT 0.7,
    llm_max_tokens integer DEFAULT 2000,
    llm_top_p numeric(3,2) DEFAULT 1.0,
    llm_top_k integer,
    llm_frequency_penalty numeric(3,2),
    llm_presence_penalty numeric(3,2),
    agent_system_prompt text,
    agent_user_prompt_template text,
    agent_config_updated_at timestamp with time zone,
    agent_config_updated_by uuid,
    allow_web_search boolean DEFAULT true,
    allow_vision boolean DEFAULT false,
    vision_api_key text,
    vision_model text,
    cep character varying(9),
    street character varying(255),
    number character varying(50),
    complement character varying(255),
    neighborhood character varying(100),
    city character varying(100),
    state character varying(2),
    CONSTRAINT companies_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('trial'::character varying)::text, ('suspended'::character varying)::text, ('cancelled'::character varying)::text])))
);


--
-- Name: company_credits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.company_credits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid,
    balance_brl numeric(10,4) DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    alert_80_sent boolean DEFAULT false,
    alert_100_sent boolean DEFAULT false
);


--
-- Name: conversation_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_logs (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    company_id uuid NOT NULL,
    user_id uuid NOT NULL,
    session_id text NOT NULL,
    user_question text NOT NULL,
    assistant_response text NOT NULL,
    llm_provider text NOT NULL,
    llm_model text NOT NULL,
    llm_temperature double precision NOT NULL,
    tokens_input integer,
    tokens_output integer,
    tokens_total integer,
    rag_chunks jsonb,
    rag_chunks_count integer DEFAULT 0,
    response_time_ms integer,
    rag_search_time_ms integer,
    status text DEFAULT 'success'::text,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    search_strategy text,
    retrieval_score double precision,
    agent_id uuid,
    internal_steps jsonb
);


--
-- Name: COLUMN conversation_logs.internal_steps; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.conversation_logs.internal_steps IS 'Traces de execução de SubAgents (ReAct loop steps, tokens, latência)';


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    session_id text NOT NULL,
    title text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    company_id uuid,
    status character varying(20) DEFAULT 'open'::character varying,
    channel character varying(20) DEFAULT 'web'::character varying,
    last_message_preview text,
    unread_count integer DEFAULT 0,
    agent_name text DEFAULT 'Smith Agent'::text,
    status_color character varying(20) DEFAULT 'green'::character varying,
    user_name text,
    user_avatar text,
    user_phone text,
    last_message_at timestamp with time zone DEFAULT now(),
    agent_id uuid,
    human_handoff_reason text
);


--
-- Name: credit_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_transactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid,
    agent_id uuid,
    type character varying(20) NOT NULL,
    amount_brl numeric(10,4) NOT NULL,
    balance_after numeric(10,4),
    model_name character varying(100),
    tokens_input integer,
    tokens_output integer,
    description text,
    stripe_payment_id character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT credit_transactions_type_check CHECK (((type)::text = ANY (ARRAY[('subscription'::character varying)::text, ('topup'::character varying)::text, ('consumption'::character varying)::text, ('refund'::character varying)::text, ('bonus'::character varying)::text])))
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid NOT NULL,
    file_name text NOT NULL,
    file_type text NOT NULL,
    file_size integer NOT NULL,
    minio_path text NOT NULL,
    qdrant_collection text,
    status text DEFAULT 'pending'::text NOT NULL,
    error_message text,
    chunks_count integer DEFAULT 0,
    processed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    ingestion_strategy character varying(50),
    quality_score double precision,
    quality_audited_at timestamp with time zone,
    agent_id uuid,
    ingestion_mode text DEFAULT 'semantic'::text NOT NULL,
    fs_storage_path text,
    fs_token_count integer,
    fs_section_count integer,
    fs_outline jsonb,
    CONSTRAINT check_ingestion_mode CHECK ((ingestion_mode = ANY (ARRAY['semantic'::text, 'filesystem'::text]))),
    CONSTRAINT check_ingestion_strategy CHECK (((ingestion_strategy IS NULL) OR ((ingestion_strategy)::text = ANY (ARRAY['recursive'::text, 'semantic'::text, 'page'::text, 'agentic'::text, 'csv'::text])))),
    CONSTRAINT documents_chunks_count_check CHECK ((chunks_count >= 0)),
    CONSTRAINT documents_file_size_check CHECK ((file_size > 0)),
    CONSTRAINT documents_file_type_check CHECK ((file_type = ANY (ARRAY['pdf'::text, 'docx'::text, 'txt'::text, 'md'::text, 'csv'::text]))),
    CONSTRAINT documents_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text])))
);


--
-- Name: integrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integrations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid,
    provider character varying(50) DEFAULT 'z-api'::character varying,
    identifier character varying(100) NOT NULL,
    token text NOT NULL,
    instance_id text NOT NULL,
    base_url text DEFAULT 'https://api.z-api.io/instances'::text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    client_token text,
    buffer_enabled boolean DEFAULT true,
    buffer_debounce_seconds integer DEFAULT 3,
    buffer_max_wait_seconds integer DEFAULT 10,
    agent_id uuid,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: invites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invites (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid NOT NULL,
    token text NOT NULL,
    created_by uuid,
    email_restriction text,
    max_uses integer DEFAULT 1000,
    current_uses integer DEFAULT 0,
    expires_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    role character varying(50) DEFAULT 'member'::character varying,
    email character varying(255),
    name character varying(255),
    is_owner_invite boolean DEFAULT false
);


--
-- Name: leads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid NOT NULL,
    email text NOT NULL,
    name text,
    phone text,
    custom_fields jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    last_seen_at timestamp with time zone DEFAULT now()
);


--
-- Name: legal_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.legal_documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    version character varying(20) NOT NULL,
    is_active boolean DEFAULT false,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT legal_documents_type_check CHECK (((type)::text = ANY ((ARRAY['terms_of_use'::character varying, 'privacy_policy'::character varying])::text[])))
);


--
-- Name: llm_pricing; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_pricing (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    model_name character varying(100) NOT NULL,
    input_price_per_million numeric(10,4) NOT NULL,
    output_price_per_million numeric(10,4) NOT NULL,
    unit character varying(20) DEFAULT 'token'::character varying,
    is_active boolean DEFAULT true,
    provider character varying(50),
    display_name character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    sell_multiplier numeric(4,2) DEFAULT 2.68,
    cache_write_multiplier numeric(5,2) DEFAULT 1.25,
    cache_read_multiplier numeric(5,2) DEFAULT 0.10,
    cached_input_multiplier numeric(5,2) DEFAULT 0.50
);


--
-- Name: mcp_servers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcp_servers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    package_name character varying(255) NOT NULL,
    command jsonb NOT NULL,
    oauth_provider character varying(50),
    oauth_scopes jsonb,
    env_vars jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: memory_processing_locks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.memory_processing_locks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id text NOT NULL,
    company_id uuid NOT NULL,
    is_processing boolean DEFAULT false,
    last_trigger_at timestamp with time zone,
    last_completed_at timestamp with time zone,
    last_message_count integer DEFAULT 0,
    scheduled_for timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    agent_id uuid
);


--
-- Name: memory_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.memory_settings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid,
    web_summarization_mode text DEFAULT 'session_end'::text,
    web_message_threshold integer DEFAULT 20,
    web_inactivity_timeout_min integer DEFAULT 30,
    whatsapp_summarization_mode text DEFAULT 'message_count'::text,
    whatsapp_sliding_window_size integer DEFAULT 50,
    whatsapp_time_interval_hours integer DEFAULT 24,
    whatsapp_message_threshold integer DEFAULT 50,
    extract_user_profile boolean DEFAULT true,
    extract_session_summary boolean DEFAULT true,
    memory_llm_model text DEFAULT 'gpt-4o-mini'::text,
    debounce_seconds integer DEFAULT 10,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    agent_id uuid
);


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id uuid NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    type text DEFAULT 'text'::text,
    audio_url text,
    image_url text,
    sender_user_id uuid,
    CONSTRAINT messages_role_check CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text]))),
    CONSTRAINT messages_type_check CHECK ((type = ANY (ARRAY['text'::text, 'voice'::text])))
);


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: payment_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    amount numeric(10,2) NOT NULL,
    currency character varying(3) DEFAULT 'BRL'::character varying,
    status character varying(20) NOT NULL,
    payment_method character varying(50),
    stripe_payment_intent_id character varying(255),
    stripe_invoice_id character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT payment_history_payment_method_check CHECK (((payment_method)::text = ANY (ARRAY[('credit_card'::character varying)::text, ('pix'::character varying)::text, ('boleto'::character varying)::text]))),
    CONSTRAINT payment_history_status_check CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text, ('refunded'::character varying)::text])))
);


--
-- Name: plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    slug character varying(50) NOT NULL,
    description text,
    monthly_price numeric(10,2) NOT NULL,
    yearly_price numeric(10,2),
    credits_limit integer NOT NULL,
    storage_limit_mb integer NOT NULL,
    max_users integer DEFAULT 1,
    features jsonb,
    is_active boolean DEFAULT true,
    sort_order integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    price_brl numeric(10,2),
    display_credits integer,
    max_agents integer DEFAULT 3,
    max_knowledge_bases integer DEFAULT 5,
    stripe_product_id character varying(100),
    stripe_price_id character varying(100),
    display_order integer DEFAULT 0
);


--
-- Name: sanitization_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sanitization_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid NOT NULL,
    original_filename text NOT NULL,
    original_file_path text NOT NULL,
    original_file_size bigint NOT NULL,
    original_mime_type text NOT NULL,
    sanitized_file_path text,
    sanitized_file_size bigint,
    status text DEFAULT 'pending'::text NOT NULL,
    progress integer DEFAULT 0 NOT NULL,
    error_message text,
    pages_count integer,
    images_count integer,
    tables_count integer,
    processing_time_seconds real,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '7 days'::interval) NOT NULL,
    extract_images boolean DEFAULT false NOT NULL
);


--
-- Name: COLUMN sanitization_jobs.extract_images; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sanitization_jobs.extract_images IS 'Se true, ativa Vision API para descrever imagens durante a sanitização';


--
-- Name: session_summaries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_summaries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id text NOT NULL,
    user_id uuid NOT NULL,
    company_id uuid NOT NULL,
    summary text NOT NULL,
    channel text DEFAULT 'web'::text,
    messages_count integer DEFAULT 0,
    started_at timestamp with time zone,
    ended_at timestamp with time zone,
    topics text[] DEFAULT '{}'::text[],
    decisions text[] DEFAULT '{}'::text[],
    pending_items text[] DEFAULT '{}'::text[],
    created_at timestamp with time zone DEFAULT now(),
    agent_id uuid
);


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscriptions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_id uuid,
    plan_id uuid,
    status character varying(20) DEFAULT 'active'::character varying,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    stripe_subscription_id character varying(100),
    stripe_customer_id character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    cancel_at timestamp with time zone,
    CONSTRAINT subscriptions_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('cancelled'::character varying)::text, ('past_due'::character varying)::text, ('trialing'::character varying)::text])))
);


--
-- Name: system_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    user_id uuid,
    admin_id uuid,
    company_id uuid,
    action_type character varying(100) NOT NULL,
    resource_type character varying(50),
    resource_id uuid,
    details jsonb,
    ip_address inet,
    user_agent text,
    session_id text,
    status character varying(20),
    error_message text,
    CONSTRAINT system_logs_status_check CHECK (((status)::text = ANY (ARRAY[('success'::character varying)::text, ('error'::character varying)::text, ('warning'::character varying)::text])))
);


--
-- Name: token_usage_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.token_usage_logs (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    company_id uuid,
    agent_id uuid,
    service_type text NOT NULL,
    model_name text NOT NULL,
    input_tokens integer DEFAULT 0,
    output_tokens integer DEFAULT 0,
    total_cost_usd numeric(10,6) DEFAULT 0,
    details jsonb,
    created_at timestamp with time zone DEFAULT now(),
    billed boolean DEFAULT false,
    billed_at timestamp with time zone,
    cache_creation_tokens integer DEFAULT 0,
    cache_read_tokens integer DEFAULT 0,
    cached_tokens integer DEFAULT 0
);


--
-- Name: ucp_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ucp_connections (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_id uuid NOT NULL,
    company_id uuid NOT NULL,
    store_url text NOT NULL,
    manifest_cached jsonb,
    manifest_version text,
    preferred_transport character varying(10) DEFAULT 'rest'::character varying,
    capabilities_enabled text[] DEFAULT '{}'::text[],
    is_active boolean DEFAULT true,
    last_used_at timestamp with time zone,
    last_error text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE ucp_connections; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ucp_connections IS 'Conexões UCP entre agentes e lojas. Usa discovery-based approach via /.well-known/ucp';


--
-- Name: COLUMN ucp_connections.store_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ucp_connections.store_url IS 'URL completa da loja (ex: https://minhaloja.com.br)';


--
-- Name: COLUMN ucp_connections.manifest_cached; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ucp_connections.manifest_cached IS 'Manifest UCP completo em formato JSON, cacheado do discovery';


--
-- Name: COLUMN ucp_connections.preferred_transport; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ucp_connections.preferred_transport IS 'Transport preferido: rest, mcp ou a2a';


--
-- Name: COLUMN ucp_connections.capabilities_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ucp_connections.capabilities_enabled IS 'Lista de capabilities UCP habilitadas (ex: dev.ucp.shopping.checkout)';


--
-- Name: ucp_connection_summary; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.ucp_connection_summary AS
 SELECT uc.id,
    uc.agent_id,
    uc.company_id,
    uc.store_url,
    uc.manifest_version,
    uc.preferred_transport,
    array_length(uc.capabilities_enabled, 1) AS capabilities_count,
    uc.is_active,
    uc.last_used_at,
    uc.created_at,
    a.name AS agent_name
   FROM (public.ucp_connections uc
     LEFT JOIN public.agents a ON ((uc.agent_id = a.id)))
  WHERE (uc.is_active = true);


--
-- Name: user_memories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    company_id uuid NOT NULL,
    profile jsonb DEFAULT '{}'::jsonb,
    facts text[] DEFAULT '{}'::text[],
    facts_metadata jsonb DEFAULT '[]'::jsonb,
    facts_count integer DEFAULT 0,
    last_extraction_at timestamp with time zone,
    last_consolidation_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    agent_id uuid
);


--
-- Name: users_v2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users_v2 (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    cpf character varying(14) NOT NULL,
    phone character varying(20) NOT NULL,
    birth_date date NOT NULL,
    company_id uuid,
    status character varying(20) DEFAULT 'pending'::character varying,
    plan_id uuid,
    plan_status character varying(20) DEFAULT 'active'::character varying,
    subscription_amount numeric(10,2),
    billing_cycle character varying(20),
    subscription_started_at timestamp without time zone,
    subscription_renews_at timestamp without time zone,
    subscription_canceled_at timestamp without time zone,
    stripe_customer_id character varying(255),
    stripe_subscription_id character varying(255),
    credits_used_this_month integer DEFAULT 0,
    credits_limit integer,
    storage_used_mb numeric(10,2) DEFAULT 0,
    storage_limit_mb integer,
    usage_reset_date date,
    last_login_at timestamp without time zone,
    last_login_ip inet,
    failed_login_attempts integer DEFAULT 0,
    account_locked_until timestamp without time zone,
    terms_accepted_at timestamp without time zone NOT NULL,
    privacy_policy_accepted_at timestamp without time zone NOT NULL,
    marketing_consent boolean DEFAULT false,
    data_deletion_requested_at timestamp without time zone,
    google_id character varying(255),
    github_id character varying(255),
    oauth_provider character varying(20) DEFAULT 'email'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    deleted_at timestamp without time zone,
    role character varying(20) DEFAULT 'member'::character varying,
    is_owner boolean DEFAULT false,
    avatar_url text,
    reset_token text,
    reset_token_expires_at timestamp with time zone,
    password_migrated_at timestamp with time zone,
    reset_attempts integer DEFAULT 0,
    accepted_terms_version uuid,
    CONSTRAINT users_v2_billing_cycle_check CHECK (((billing_cycle)::text = ANY (ARRAY[('monthly'::character varying)::text, ('yearly'::character varying)::text]))),
    CONSTRAINT users_v2_oauth_provider_check CHECK (((oauth_provider)::text = ANY (ARRAY[('email'::character varying)::text, ('google'::character varying)::text, ('github'::character varying)::text]))),
    CONSTRAINT users_v2_plan_status_check CHECK (((plan_status)::text = ANY (ARRAY[('active'::character varying)::text, ('past_due'::character varying)::text, ('canceled'::character varying)::text, ('suspended'::character varying)::text]))),
    CONSTRAINT users_v2_role_check CHECK (((role)::text = ANY (ARRAY[('admin_company'::character varying)::text, ('member'::character varying)::text]))),
    CONSTRAINT users_v2_status_check CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('active'::character varying)::text, ('suspended'::character varying)::text, ('lead'::character varying)::text])))
);


--
-- Name: widget_rate_limits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.widget_rate_limits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    identifier character varying(255) NOT NULL,
    identifier_type character varying(20) DEFAULT 'session'::character varying,
    request_count integer DEFAULT 1,
    window_start timestamp with time zone DEFAULT now(),
    agent_id uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: admin_users admin_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_email_key UNIQUE (email);


--
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- Name: agent_delegations agent_delegations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_delegations
    ADD CONSTRAINT agent_delegations_pkey PRIMARY KEY (id);


--
-- Name: agent_http_tools agent_http_tools_agent_id_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_http_tools
    ADD CONSTRAINT agent_http_tools_agent_id_name_key UNIQUE (agent_id, name);


--
-- Name: agent_http_tools agent_http_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_http_tools
    ADD CONSTRAINT agent_http_tools_pkey PRIMARY KEY (id);


--
-- Name: agent_mcp_connections agent_mcp_connections_agent_id_mcp_server_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_connections
    ADD CONSTRAINT agent_mcp_connections_agent_id_mcp_server_id_key UNIQUE (agent_id, mcp_server_id);


--
-- Name: agent_mcp_connections agent_mcp_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_connections
    ADD CONSTRAINT agent_mcp_connections_pkey PRIMARY KEY (id);


--
-- Name: agent_mcp_tools agent_mcp_tools_agent_id_mcp_server_id_tool_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_tools
    ADD CONSTRAINT agent_mcp_tools_agent_id_mcp_server_id_tool_name_key UNIQUE (agent_id, mcp_server_id, tool_name);


--
-- Name: agent_mcp_tools agent_mcp_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_tools
    ADD CONSTRAINT agent_mcp_tools_pkey PRIMARY KEY (id);


--
-- Name: agents agents_company_id_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_company_id_slug_key UNIQUE (company_id, slug);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: checkpoint_blobs checkpoint_blobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checkpoint_blobs
    ADD CONSTRAINT checkpoint_blobs_pkey PRIMARY KEY (thread_id, checkpoint_ns, channel, version);


--
-- Name: checkpoint_migrations checkpoint_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checkpoint_migrations
    ADD CONSTRAINT checkpoint_migrations_pkey PRIMARY KEY (v);


--
-- Name: checkpoint_writes checkpoint_writes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checkpoint_writes
    ADD CONSTRAINT checkpoint_writes_pkey PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx);


--
-- Name: checkpoints checkpoints_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checkpoints
    ADD CONSTRAINT checkpoints_pkey PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: conversation_logs conversation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_logs
    ADD CONSTRAINT conversation_logs_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_session_id_key UNIQUE (session_id);


--
-- Name: credit_transactions credit_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: integrations integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_pkey PRIMARY KEY (id);


--
-- Name: integrations integrations_provider_identifier_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_provider_identifier_key UNIQUE (provider, identifier);


--
-- Name: invites invites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invites
    ADD CONSTRAINT invites_pkey PRIMARY KEY (id);


--
-- Name: invites invites_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invites
    ADD CONSTRAINT invites_token_key UNIQUE (token);


--
-- Name: leads leads_company_id_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_company_id_email_key UNIQUE (company_id, email);


--
-- Name: leads leads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pkey PRIMARY KEY (id);


--
-- Name: legal_documents legal_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_documents
    ADD CONSTRAINT legal_documents_pkey PRIMARY KEY (id);


--
-- Name: llm_pricing llm_pricing_model_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_pricing
    ADD CONSTRAINT llm_pricing_model_name_key UNIQUE (model_name);


--
-- Name: llm_pricing llm_pricing_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_pricing
    ADD CONSTRAINT llm_pricing_pkey PRIMARY KEY (id);


--
-- Name: mcp_servers mcp_servers_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_servers
    ADD CONSTRAINT mcp_servers_name_key UNIQUE (name);


--
-- Name: mcp_servers mcp_servers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_servers
    ADD CONSTRAINT mcp_servers_pkey PRIMARY KEY (id);


--
-- Name: memory_processing_locks memory_processing_locks_session_id_company_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_processing_locks
    ADD CONSTRAINT memory_processing_locks_session_id_company_id_key UNIQUE (session_id, company_id);


--
-- Name: memory_settings memory_settings_agent_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_settings
    ADD CONSTRAINT memory_settings_agent_id_key UNIQUE (agent_id);


--
-- Name: memory_settings memory_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_settings
    ADD CONSTRAINT memory_settings_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_key UNIQUE (token);


--
-- Name: payment_history payment_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_history
    ADD CONSTRAINT payment_history_pkey PRIMARY KEY (id);


--
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


--
-- Name: plans plans_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_slug_key UNIQUE (slug);


--
-- Name: sanitization_jobs sanitization_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sanitization_jobs
    ADD CONSTRAINT sanitization_jobs_pkey PRIMARY KEY (id);


--
-- Name: session_summaries session_summaries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_summaries
    ADD CONSTRAINT session_summaries_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_company_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_company_id_unique UNIQUE (company_id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: system_logs system_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_logs
    ADD CONSTRAINT system_logs_pkey PRIMARY KEY (id);


--
-- Name: company_credits tenant_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.company_credits
    ADD CONSTRAINT tenant_credits_pkey PRIMARY KEY (id);


--
-- Name: company_credits tenant_credits_tenant_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.company_credits
    ADD CONSTRAINT tenant_credits_tenant_id_key UNIQUE (company_id);


--
-- Name: token_usage_logs token_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_usage_logs
    ADD CONSTRAINT token_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: ucp_connections ucp_connections_agent_id_store_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ucp_connections
    ADD CONSTRAINT ucp_connections_agent_id_store_url_key UNIQUE (agent_id, store_url);


--
-- Name: ucp_connections ucp_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ucp_connections
    ADD CONSTRAINT ucp_connections_pkey PRIMARY KEY (id);


--
-- Name: agent_delegations unique_delegation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_delegations
    ADD CONSTRAINT unique_delegation UNIQUE (orchestrator_id, subagent_id);


--
-- Name: widget_rate_limits uq_rate_limit_identifier_agent; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.widget_rate_limits
    ADD CONSTRAINT uq_rate_limit_identifier_agent UNIQUE (identifier, agent_id, identifier_type);


--
-- Name: user_memories user_memories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_memories
    ADD CONSTRAINT user_memories_pkey PRIMARY KEY (id);


--
-- Name: users_v2 users_v2_cpf_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_cpf_key UNIQUE (cpf);


--
-- Name: users_v2 users_v2_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_email_key UNIQUE (email);


--
-- Name: users_v2 users_v2_github_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_github_id_key UNIQUE (github_id);


--
-- Name: users_v2 users_v2_google_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_google_id_key UNIQUE (google_id);


--
-- Name: users_v2 users_v2_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_pkey PRIMARY KEY (id);


--
-- Name: widget_rate_limits widget_rate_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.widget_rate_limits
    ADD CONSTRAINT widget_rate_limits_pkey PRIMARY KEY (id);


--
-- Name: checkpoint_blobs_thread_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX checkpoint_blobs_thread_id_idx ON public.checkpoint_blobs USING btree (thread_id);


--
-- Name: checkpoint_writes_thread_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX checkpoint_writes_thread_id_idx ON public.checkpoint_writes USING btree (thread_id);


--
-- Name: checkpoints_thread_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX checkpoints_thread_id_idx ON public.checkpoints USING btree (thread_id);


--
-- Name: idx_admin_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_users_email ON public.admin_users USING btree (email);


--
-- Name: idx_admin_users_reset_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_users_reset_token ON public.admin_users USING btree (reset_token) WHERE (reset_token IS NOT NULL);


--
-- Name: idx_agent_http_tools_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_http_tools_agent_id ON public.agent_http_tools USING btree (agent_id);


--
-- Name: idx_agent_mcp_connections_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_mcp_connections_agent ON public.agent_mcp_connections USING btree (agent_id);


--
-- Name: idx_agent_mcp_tools_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_mcp_tools_agent ON public.agent_mcp_tools USING btree (agent_id);


--
-- Name: idx_agent_mcp_tools_variable; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_mcp_tools_variable ON public.agent_mcp_tools USING btree (variable_name);


--
-- Name: idx_agents_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agents_company_id ON public.agents USING btree (company_id);


--
-- Name: idx_agents_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agents_is_active ON public.agents USING btree (is_active);


--
-- Name: idx_companies_agent_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_agent_enabled ON public.companies USING btree (agent_enabled) WHERE (agent_enabled = true);


--
-- Name: idx_companies_allow_vision; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_allow_vision ON public.companies USING btree (allow_vision) WHERE (allow_vision = true);


--
-- Name: idx_companies_llm_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_llm_provider ON public.companies USING btree (llm_provider) WHERE (llm_provider IS NOT NULL);


--
-- Name: idx_companies_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_status ON public.companies USING btree (status);


--
-- Name: idx_companies_use_langchain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_use_langchain ON public.companies USING btree (use_langchain);


--
-- Name: idx_companies_webhook; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_companies_webhook ON public.companies USING btree (webhook_url);


--
-- Name: idx_company_credits_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_company_credits_company ON public.company_credits USING btree (company_id);


--
-- Name: idx_conversation_logs_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_agent_id ON public.conversation_logs USING btree (agent_id);


--
-- Name: idx_conversation_logs_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_company ON public.conversation_logs USING btree (company_id);


--
-- Name: idx_conversation_logs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_created ON public.conversation_logs USING btree (created_at DESC);


--
-- Name: idx_conversation_logs_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_model ON public.conversation_logs USING btree (llm_provider, llm_model);


--
-- Name: idx_conversation_logs_search_strategy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_search_strategy ON public.conversation_logs USING btree (search_strategy) WHERE (search_strategy IS NOT NULL);


--
-- Name: idx_conversation_logs_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_session ON public.conversation_logs USING btree (session_id);


--
-- Name: idx_conversation_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_timestamp ON public.conversation_logs USING btree ("timestamp" DESC);


--
-- Name: idx_conversation_logs_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversation_logs_user ON public.conversation_logs USING btree (user_id);


--
-- Name: idx_conversations_admin_list; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_admin_list ON public.conversations USING btree (company_id, status);


--
-- Name: idx_conversations_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_agent_id ON public.conversations USING btree (agent_id);


--
-- Name: idx_conversations_company_admin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_company_admin ON public.conversations USING btree (company_id, last_message_at DESC);


--
-- Name: idx_conversations_company_user_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_company_user_channel ON public.conversations USING btree (company_id, user_id, channel);


--
-- Name: idx_conversations_session_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_session_company ON public.conversations USING btree (session_id, company_id);


--
-- Name: idx_conversations_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_session_id ON public.conversations USING btree (session_id);


--
-- Name: idx_conversations_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_user_id ON public.conversations USING btree (user_id);


--
-- Name: idx_credit_transactions_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_transactions_company ON public.credit_transactions USING btree (company_id);


--
-- Name: idx_credit_transactions_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_transactions_created ON public.credit_transactions USING btree (created_at DESC);


--
-- Name: idx_credit_transactions_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_transactions_tenant ON public.credit_transactions USING btree (company_id);


--
-- Name: idx_credit_transactions_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_transactions_type ON public.credit_transactions USING btree (type);


--
-- Name: idx_delegations_orchestrator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_delegations_orchestrator ON public.agent_delegations USING btree (orchestrator_id) WHERE (is_active = true);


--
-- Name: idx_documents_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_agent_id ON public.documents USING btree (agent_id);


--
-- Name: idx_documents_agent_ingestion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_agent_ingestion ON public.documents USING btree (agent_id, ingestion_mode);


--
-- Name: idx_documents_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_company_id ON public.documents USING btree (company_id);


--
-- Name: idx_documents_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_created_at ON public.documents USING btree (created_at DESC);


--
-- Name: idx_documents_ingestion_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_ingestion_mode ON public.documents USING btree (ingestion_mode);


--
-- Name: idx_documents_ingestion_strategy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_ingestion_strategy ON public.documents USING btree (ingestion_strategy);


--
-- Name: idx_documents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_status ON public.documents USING btree (status);


--
-- Name: idx_documents_strategy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_strategy ON public.documents USING btree (ingestion_strategy);


--
-- Name: idx_integrations_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_integrations_agent_id ON public.integrations USING btree (agent_id);


--
-- Name: idx_integrations_identifier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_integrations_identifier ON public.integrations USING btree (identifier);


--
-- Name: idx_invites_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invites_role ON public.invites USING btree (role);


--
-- Name: idx_invites_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invites_token ON public.invites USING btree (token);


--
-- Name: idx_leads_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_leads_lookup ON public.leads USING btree (company_id, email);


--
-- Name: idx_legal_docs_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_docs_active ON public.legal_documents USING btree (type, is_active) WHERE (is_active = true);


--
-- Name: idx_llm_pricing_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_pricing_model ON public.llm_pricing USING btree (model_name);


--
-- Name: idx_memory_locks_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_locks_agent_id ON public.memory_processing_locks USING btree (agent_id);


--
-- Name: idx_memory_locks_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_locks_company ON public.memory_processing_locks USING btree (company_id);


--
-- Name: idx_memory_locks_processing; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_locks_processing ON public.memory_processing_locks USING btree (is_processing) WHERE (is_processing = true);


--
-- Name: idx_memory_locks_scheduled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_locks_scheduled ON public.memory_processing_locks USING btree (scheduled_for) WHERE (scheduled_for IS NOT NULL);


--
-- Name: idx_memory_locks_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_locks_session ON public.memory_processing_locks USING btree (session_id);


--
-- Name: idx_memory_locks_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_memory_locks_unique ON public.memory_processing_locks USING btree (session_id, company_id);


--
-- Name: idx_memory_settings_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_settings_agent ON public.memory_settings USING btree (agent_id);


--
-- Name: idx_memory_settings_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_memory_settings_company ON public.memory_settings USING btree (company_id);


--
-- Name: idx_messages_by_conversation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_by_conversation ON public.messages USING btree (conversation_id, created_at);


--
-- Name: idx_messages_conversation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_conversation_id ON public.messages USING btree (conversation_id);


--
-- Name: idx_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_created_at ON public.messages USING btree (created_at);


--
-- Name: idx_messages_sender_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_sender_user_id ON public.messages USING btree (sender_user_id);


--
-- Name: idx_password_reset_tokens_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_password_reset_tokens_token ON public.password_reset_tokens USING btree (token);


--
-- Name: idx_password_reset_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_password_reset_tokens_user_id ON public.password_reset_tokens USING btree (user_id);


--
-- Name: idx_payment_history_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_history_status ON public.payment_history USING btree (status);


--
-- Name: idx_payment_history_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_history_user_id ON public.payment_history USING btree (user_id);


--
-- Name: idx_plans_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_plans_is_active ON public.plans USING btree (is_active);


--
-- Name: idx_plans_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_plans_slug ON public.plans USING btree (slug);


--
-- Name: idx_sanitization_jobs_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sanitization_jobs_company ON public.sanitization_jobs USING btree (company_id);


--
-- Name: idx_sanitization_jobs_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sanitization_jobs_expires ON public.sanitization_jobs USING btree (expires_at);


--
-- Name: idx_sanitization_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sanitization_jobs_status ON public.sanitization_jobs USING btree (status);


--
-- Name: idx_session_summaries_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_summaries_agent_id ON public.session_summaries USING btree (agent_id);


--
-- Name: idx_session_summaries_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_summaries_company ON public.session_summaries USING btree (company_id);


--
-- Name: idx_session_summaries_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_summaries_created ON public.session_summaries USING btree (created_at DESC);


--
-- Name: idx_session_summaries_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_summaries_session ON public.session_summaries USING btree (session_id);


--
-- Name: idx_session_summaries_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_summaries_user ON public.session_summaries USING btree (user_id);


--
-- Name: idx_subscriptions_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_company ON public.subscriptions USING btree (company_id);


--
-- Name: idx_subscriptions_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_company_id ON public.subscriptions USING btree (company_id);


--
-- Name: idx_subscriptions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_status ON public.subscriptions USING btree (status);


--
-- Name: idx_subscriptions_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_tenant ON public.subscriptions USING btree (company_id);


--
-- Name: idx_system_logs_action_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_logs_action_type ON public.system_logs USING btree (action_type);


--
-- Name: idx_system_logs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_logs_status ON public.system_logs USING btree (status);


--
-- Name: idx_system_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_logs_timestamp ON public.system_logs USING btree ("timestamp");


--
-- Name: idx_system_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_logs_user_id ON public.system_logs USING btree (user_id);


--
-- Name: idx_tenant_credits_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tenant_credits_tenant ON public.company_credits USING btree (company_id);


--
-- Name: idx_token_usage_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_company ON public.token_usage_logs USING btree (company_id);


--
-- Name: idx_token_usage_company_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_company_date ON public.token_usage_logs USING btree (company_id, created_at DESC);


--
-- Name: idx_token_usage_company_unbilled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_company_unbilled ON public.token_usage_logs USING btree (company_id, created_at) WHERE (billed = false);


--
-- Name: idx_token_usage_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_created ON public.token_usage_logs USING btree (created_at);


--
-- Name: idx_token_usage_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_model ON public.token_usage_logs USING btree (model_name);


--
-- Name: idx_token_usage_service; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_service ON public.token_usage_logs USING btree (service_type);


--
-- Name: idx_token_usage_unbilled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_usage_unbilled ON public.token_usage_logs USING btree (billed, created_at) WHERE (billed = false);


--
-- Name: idx_ucp_connections_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ucp_connections_active ON public.ucp_connections USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_ucp_connections_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ucp_connections_agent ON public.ucp_connections USING btree (agent_id);


--
-- Name: idx_ucp_connections_capabilities; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ucp_connections_capabilities ON public.ucp_connections USING gin (capabilities_enabled);


--
-- Name: idx_ucp_connections_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ucp_connections_company ON public.ucp_connections USING btree (company_id);


--
-- Name: idx_ucp_connections_store; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ucp_connections_store ON public.ucp_connections USING btree (store_url);


--
-- Name: idx_user_memories_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_memories_agent_id ON public.user_memories USING btree (agent_id);


--
-- Name: idx_user_memories_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_memories_company ON public.user_memories USING btree (company_id);


--
-- Name: idx_user_memories_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_memories_user ON public.user_memories USING btree (user_id);


--
-- Name: idx_user_memories_user_company_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_user_memories_user_company_agent ON public.user_memories USING btree (user_id, company_id, COALESCE(agent_id, '00000000-0000-0000-0000-000000000000'::uuid));


--
-- Name: idx_users_v2_company_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_company_id ON public.users_v2 USING btree (company_id);


--
-- Name: idx_users_v2_cpf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_cpf ON public.users_v2 USING btree (cpf);


--
-- Name: idx_users_v2_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_deleted_at ON public.users_v2 USING btree (deleted_at);


--
-- Name: idx_users_v2_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_email ON public.users_v2 USING btree (email);


--
-- Name: idx_users_v2_github_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_github_id ON public.users_v2 USING btree (github_id);


--
-- Name: idx_users_v2_google_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_google_id ON public.users_v2 USING btree (google_id);


--
-- Name: idx_users_v2_not_migrated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_not_migrated ON public.users_v2 USING btree (id) WHERE (password_migrated_at IS NULL);


--
-- Name: idx_users_v2_plan_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_plan_id ON public.users_v2 USING btree (plan_id);


--
-- Name: idx_users_v2_reset_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_v2_reset_token ON public.users_v2 USING btree (reset_token) WHERE (reset_token IS NOT NULL);


--
-- Name: agent_delegations trigger_delegations_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_delegations_updated_at BEFORE UPDATE ON public.agent_delegations FOR EACH ROW EXECUTE FUNCTION public.update_agent_delegations_updated_at();


--
-- Name: documents trigger_documents_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_documents_updated_at BEFORE UPDATE ON public.documents FOR EACH ROW EXECUTE FUNCTION public.update_documents_updated_at();


--
-- Name: ucp_connections ucp_connections_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ucp_connections_updated_at BEFORE UPDATE ON public.ucp_connections FOR EACH ROW EXECUTE FUNCTION public.update_ucp_updated_at();


--
-- Name: companies update_companies_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON public.companies FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: legal_documents update_legal_documents_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_legal_documents_updated_at BEFORE UPDATE ON public.legal_documents FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: plans update_plans_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_plans_updated_at BEFORE UPDATE ON public.plans FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users_v2 update_users_v2_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_v2_updated_at BEFORE UPDATE ON public.users_v2 FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: agent_delegations agent_delegations_orchestrator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_delegations
    ADD CONSTRAINT agent_delegations_orchestrator_id_fkey FOREIGN KEY (orchestrator_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_delegations agent_delegations_subagent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_delegations
    ADD CONSTRAINT agent_delegations_subagent_id_fkey FOREIGN KEY (subagent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_http_tools agent_http_tools_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_http_tools
    ADD CONSTRAINT agent_http_tools_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_mcp_connections agent_mcp_connections_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_connections
    ADD CONSTRAINT agent_mcp_connections_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_mcp_connections agent_mcp_connections_mcp_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_connections
    ADD CONSTRAINT agent_mcp_connections_mcp_server_id_fkey FOREIGN KEY (mcp_server_id) REFERENCES public.mcp_servers(id) ON DELETE CASCADE;


--
-- Name: agent_mcp_tools agent_mcp_tools_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_tools
    ADD CONSTRAINT agent_mcp_tools_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_mcp_tools agent_mcp_tools_mcp_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_mcp_tools
    ADD CONSTRAINT agent_mcp_tools_mcp_server_id_fkey FOREIGN KEY (mcp_server_id) REFERENCES public.mcp_servers(id) ON DELETE CASCADE;


--
-- Name: agents agents_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: conversation_logs conversation_logs_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_logs
    ADD CONSTRAINT conversation_logs_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: conversation_logs conversation_logs_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_logs
    ADD CONSTRAINT conversation_logs_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: conversations conversations_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: conversations conversations_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: credit_transactions credit_transactions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: credit_transactions credit_transactions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_tenant_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: documents documents_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: documents documents_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: integrations integrations_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: integrations integrations_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: invites invites_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invites
    ADD CONSTRAINT invites_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: invites invites_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invites
    ADD CONSTRAINT invites_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users_v2(id);


--
-- Name: leads leads_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: legal_documents legal_documents_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_documents
    ADD CONSTRAINT legal_documents_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.admin_users(id);


--
-- Name: memory_processing_locks memory_processing_locks_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_processing_locks
    ADD CONSTRAINT memory_processing_locks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: memory_processing_locks memory_processing_locks_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_processing_locks
    ADD CONSTRAINT memory_processing_locks_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: memory_settings memory_settings_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_settings
    ADD CONSTRAINT memory_settings_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: memory_settings memory_settings_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.memory_settings
    ADD CONSTRAINT memory_settings_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: messages messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: messages messages_sender_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_user_id_fkey FOREIGN KEY (sender_user_id) REFERENCES public.users_v2(id) ON DELETE SET NULL;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users_v2(id) ON DELETE CASCADE;


--
-- Name: payment_history payment_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_history
    ADD CONSTRAINT payment_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users_v2(id) ON DELETE CASCADE;


--
-- Name: sanitization_jobs sanitization_jobs_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sanitization_jobs
    ADD CONSTRAINT sanitization_jobs_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: session_summaries session_summaries_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_summaries
    ADD CONSTRAINT session_summaries_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: session_summaries session_summaries_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_summaries
    ADD CONSTRAINT session_summaries_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: subscriptions subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id) ON DELETE SET NULL;


--
-- Name: subscriptions subscriptions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_tenant_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: system_logs system_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_logs
    ADD CONSTRAINT system_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.admin_users(id);


--
-- Name: system_logs system_logs_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_logs
    ADD CONSTRAINT system_logs_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: system_logs system_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_logs
    ADD CONSTRAINT system_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users_v2(id);


--
-- Name: company_credits tenant_credits_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.company_credits
    ADD CONSTRAINT tenant_credits_tenant_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: token_usage_logs token_usage_logs_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_usage_logs
    ADD CONSTRAINT token_usage_logs_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: token_usage_logs token_usage_logs_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_usage_logs
    ADD CONSTRAINT token_usage_logs_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE SET NULL;


--
-- Name: ucp_connections ucp_connections_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ucp_connections
    ADD CONSTRAINT ucp_connections_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: ucp_connections ucp_connections_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ucp_connections
    ADD CONSTRAINT ucp_connections_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: user_memories user_memories_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_memories
    ADD CONSTRAINT user_memories_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE SET NULL;


--
-- Name: user_memories user_memories_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_memories
    ADD CONSTRAINT user_memories_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: users_v2 users_v2_accepted_terms_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_accepted_terms_version_fkey FOREIGN KEY (accepted_terms_version) REFERENCES public.legal_documents(id);


--
-- Name: users_v2 users_v2_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: users_v2 users_v2_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users_v2
    ADD CONSTRAINT users_v2_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


--
-- Name: widget_rate_limits widget_rate_limits_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.widget_rate_limits
    ADD CONSTRAINT widget_rate_limits_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: messages Allow realtime subscriptions on messages; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Allow realtime subscriptions on messages" ON public.messages FOR SELECT TO anon USING (true);


--
-- Name: mcp_servers Anyone can read MCP servers; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Anyone can read MCP servers" ON public.mcp_servers FOR SELECT USING (true);


--
-- Name: llm_pricing Anyone can read pricing; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Anyone can read pricing" ON public.llm_pricing FOR SELECT USING (true);


--
-- Name: legal_documents Public read active legal_documents; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Public read active legal_documents" ON public.legal_documents FOR SELECT TO authenticated, anon USING ((is_active = true));


--
-- Name: token_usage_logs Service Role Full Access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service Role Full Access" ON public.token_usage_logs TO service_role USING (true) WITH CHECK (true);


--
-- Name: agent_mcp_connections Service role full access agent_mcp_connections; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access agent_mcp_connections" ON public.agent_mcp_connections TO service_role USING (true) WITH CHECK (true);


--
-- Name: agent_mcp_tools Service role full access agent_mcp_tools; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access agent_mcp_tools" ON public.agent_mcp_tools TO service_role USING (true) WITH CHECK (true);


--
-- Name: checkpoint_blobs Service role full access checkpoint_blobs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access checkpoint_blobs" ON public.checkpoint_blobs TO service_role USING (true) WITH CHECK (true);


--
-- Name: checkpoint_migrations Service role full access checkpoint_migrations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access checkpoint_migrations" ON public.checkpoint_migrations TO service_role USING (true) WITH CHECK (true);


--
-- Name: checkpoint_writes Service role full access checkpoint_writes; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access checkpoint_writes" ON public.checkpoint_writes TO service_role USING (true) WITH CHECK (true);


--
-- Name: checkpoints Service role full access checkpoints; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access checkpoints" ON public.checkpoints TO service_role USING (true) WITH CHECK (true);


--
-- Name: legal_documents Service role full access legal_documents; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access legal_documents" ON public.legal_documents TO service_role USING (true) WITH CHECK (true);


--
-- Name: mcp_servers Service role full access mcp_servers; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access mcp_servers" ON public.mcp_servers TO service_role USING (true) WITH CHECK (true);


--
-- Name: admin_users Service role full access to admin_users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to admin_users" ON public.admin_users TO service_role USING (true) WITH CHECK (true);


--
-- Name: agent_http_tools Service role full access to agent_http_tools; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to agent_http_tools" ON public.agent_http_tools TO service_role USING (true) WITH CHECK (true);


--
-- Name: agents Service role full access to agents; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to agents" ON public.agents TO service_role USING (true) WITH CHECK (true);


--
-- Name: companies Service role full access to companies; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to companies" ON public.companies TO service_role USING (true) WITH CHECK (true);


--
-- Name: conversation_logs Service role full access to conversation_logs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to conversation_logs" ON public.conversation_logs TO service_role USING (true) WITH CHECK (true);


--
-- Name: conversations Service role full access to conversations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to conversations" ON public.conversations TO service_role USING (true) WITH CHECK (true);


--
-- Name: memory_processing_locks Service role full access to memory_processing_locks; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to memory_processing_locks" ON public.memory_processing_locks TO service_role USING (true) WITH CHECK (true);


--
-- Name: messages Service role full access to messages; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to messages" ON public.messages TO service_role USING (true) WITH CHECK (true);


--
-- Name: system_logs Service role full access to system_logs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to system_logs" ON public.system_logs TO service_role USING (true) WITH CHECK (true);


--
-- Name: users_v2 Service role full access to users_v2; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access to users_v2" ON public.users_v2 TO service_role USING (true) WITH CHECK (true);


--
-- Name: ucp_connections Service role full access ucp_connections; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Service role full access ucp_connections" ON public.ucp_connections TO service_role USING (true) WITH CHECK (true);


--
-- Name: conversations Users can create own conversations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can create own conversations" ON public.conversations FOR INSERT WITH CHECK ((user_id = auth.uid()));


--
-- Name: messages Users can insert messages to own conversations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can insert messages to own conversations" ON public.messages FOR INSERT WITH CHECK ((conversation_id IN ( SELECT conversations.id
   FROM public.conversations
  WHERE ((conversations.user_id = auth.uid()) OR (conversations.company_id = ( SELECT users_v2.company_id
           FROM public.users_v2
          WHERE (users_v2.id = auth.uid())))))));


--
-- Name: integrations Users can manage own company integrations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can manage own company integrations" ON public.integrations USING ((company_id = ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid()))));


--
-- Name: leads Users can manage own company leads; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can manage own company leads" ON public.leads USING ((company_id = ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid()))));


--
-- Name: widget_rate_limits Users can manage rate limits for own company agents; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can manage rate limits for own company agents" ON public.widget_rate_limits USING ((agent_id IN ( SELECT agents.id
   FROM public.agents
  WHERE (agents.company_id = ( SELECT users_v2.company_id
           FROM public.users_v2
          WHERE (users_v2.id = auth.uid()))))));


--
-- Name: conversations Users can update own conversations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can update own conversations" ON public.conversations FOR UPDATE USING ((user_id = auth.uid()));


--
-- Name: messages Users can view messages from accessible conversations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can view messages from accessible conversations" ON public.messages FOR SELECT USING ((conversation_id IN ( SELECT conversations.id
   FROM public.conversations
  WHERE ((conversations.user_id = auth.uid()) OR (conversations.company_id = ( SELECT users_v2.company_id
           FROM public.users_v2
          WHERE (users_v2.id = auth.uid())))))));


--
-- Name: ucp_connections Users can view own company connections; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can view own company connections" ON public.ucp_connections FOR SELECT TO authenticated USING ((company_id IN ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid()))));


--
-- Name: company_credits Users can view own company credits; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can view own company credits" ON public.company_credits FOR SELECT USING ((company_id = ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid()))));


--
-- Name: subscriptions Users can view own company subscription; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can view own company subscription" ON public.subscriptions FOR SELECT USING ((company_id = ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid()))));


--
-- Name: credit_transactions Users can view own company transactions; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can view own company transactions" ON public.credit_transactions FOR SELECT USING ((company_id = ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid()))));


--
-- Name: conversations Users can view own or company conversations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Users can view own or company conversations" ON public.conversations FOR SELECT USING (((user_id = auth.uid()) OR (company_id = ( SELECT users_v2.company_id
   FROM public.users_v2
  WHERE (users_v2.id = auth.uid())))));


--
-- Name: admin_users; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_delegations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_delegations ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_http_tools; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_http_tools ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_mcp_connections; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_mcp_connections ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_mcp_tools; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_mcp_tools ENABLE ROW LEVEL SECURITY;

--
-- Name: agents; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

--
-- Name: checkpoint_blobs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.checkpoint_blobs ENABLE ROW LEVEL SECURITY;

--
-- Name: checkpoint_migrations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.checkpoint_migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: checkpoint_writes; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.checkpoint_writes ENABLE ROW LEVEL SECURITY;

--
-- Name: checkpoints; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.checkpoints ENABLE ROW LEVEL SECURITY;

--
-- Name: companies; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

--
-- Name: company_credits; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.company_credits ENABLE ROW LEVEL SECURITY;

--
-- Name: sanitization_jobs company_isolation_delete; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY company_isolation_delete ON public.sanitization_jobs FOR DELETE USING ((company_id = ((auth.jwt() ->> 'company_id'::text))::uuid));


--
-- Name: sanitization_jobs company_isolation_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY company_isolation_insert ON public.sanitization_jobs FOR INSERT WITH CHECK ((company_id = ((auth.jwt() ->> 'company_id'::text))::uuid));


--
-- Name: sanitization_jobs company_isolation_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY company_isolation_select ON public.sanitization_jobs FOR SELECT USING ((company_id = ((auth.jwt() ->> 'company_id'::text))::uuid));


--
-- Name: conversation_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.conversation_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: conversations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

--
-- Name: credit_transactions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_delegations delegations_same_company; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY delegations_same_company ON public.agent_delegations USING ((( SELECT agents.company_id
   FROM public.agents
  WHERE (agents.id = agent_delegations.orchestrator_id)) = ( SELECT agents.company_id
   FROM public.agents
  WHERE (agents.id = agent_delegations.subagent_id))));


--
-- Name: documents; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

--
-- Name: integrations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.integrations ENABLE ROW LEVEL SECURITY;

--
-- Name: invites; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.invites ENABLE ROW LEVEL SECURITY;

--
-- Name: leads; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

--
-- Name: legal_documents; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.legal_documents ENABLE ROW LEVEL SECURITY;

--
-- Name: llm_pricing; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.llm_pricing ENABLE ROW LEVEL SECURITY;

--
-- Name: mcp_servers; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.mcp_servers ENABLE ROW LEVEL SECURITY;

--
-- Name: memory_processing_locks; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.memory_processing_locks ENABLE ROW LEVEL SECURITY;

--
-- Name: memory_settings; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.memory_settings ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

--
-- Name: password_reset_tokens; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: payment_history; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.payment_history ENABLE ROW LEVEL SECURITY;

--
-- Name: plans; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;

--
-- Name: sanitization_jobs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.sanitization_jobs ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_http_tools service_role_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_all ON public.agent_http_tools TO service_role USING (true) WITH CHECK (true);


--
-- Name: session_summaries; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.session_summaries ENABLE ROW LEVEL SECURITY;

--
-- Name: subscriptions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

--
-- Name: system_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.system_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: token_usage_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.token_usage_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: ucp_connections; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.ucp_connections ENABLE ROW LEVEL SECURITY;

--
-- Name: user_memories; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;

--
-- Name: users_v2; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.users_v2 ENABLE ROW LEVEL SECURITY;

--
-- Name: widget_rate_limits; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.widget_rate_limits ENABLE ROW LEVEL SECURITY;

--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;


--
-- Name: FUNCTION check_and_increment_rate_limit(p_identifier text, p_agent_id uuid, p_max_requests integer, p_window_minutes integer); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.check_and_increment_rate_limit(p_identifier text, p_agent_id uuid, p_max_requests integer, p_window_minutes integer) TO anon;
GRANT ALL ON FUNCTION public.check_and_increment_rate_limit(p_identifier text, p_agent_id uuid, p_max_requests integer, p_window_minutes integer) TO authenticated;
GRANT ALL ON FUNCTION public.check_and_increment_rate_limit(p_identifier text, p_agent_id uuid, p_max_requests integer, p_window_minutes integer) TO service_role;


--
-- Name: FUNCTION create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean) TO anon;
GRANT ALL ON FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean) TO authenticated;
GRANT ALL ON FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean) TO service_role;


--
-- Name: FUNCTION create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean, p_accepted_terms_version uuid); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean, p_accepted_terms_version uuid) TO anon;
GRANT ALL ON FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean, p_accepted_terms_version uuid) TO authenticated;
GRANT ALL ON FUNCTION public.create_user_account(p_first_name character varying, p_last_name character varying, p_email character varying, p_password_hash character varying, p_cpf character varying, p_phone character varying, p_birth_date date, p_company_id uuid, p_status character varying, p_role character varying, p_is_owner boolean, p_accepted_terms_version uuid) TO service_role;


--
-- Name: FUNCTION debit_company_balance(p_company_id uuid, p_amount numeric); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.debit_company_balance(p_company_id uuid, p_amount numeric) TO anon;
GRANT ALL ON FUNCTION public.debit_company_balance(p_company_id uuid, p_amount numeric) TO authenticated;
GRANT ALL ON FUNCTION public.debit_company_balance(p_company_id uuid, p_amount numeric) TO service_role;


--
-- Name: FUNCTION get_agent_ucp_capabilities(p_agent_id uuid); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.get_agent_ucp_capabilities(p_agent_id uuid) TO anon;
GRANT ALL ON FUNCTION public.get_agent_ucp_capabilities(p_agent_id uuid) TO authenticated;
GRANT ALL ON FUNCTION public.get_agent_ucp_capabilities(p_agent_id uuid) TO service_role;


--
-- Name: FUNCTION get_token_usage_by_company(start_date timestamp with time zone, end_date timestamp with time zone); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.get_token_usage_by_company(start_date timestamp with time zone, end_date timestamp with time zone) TO anon;
GRANT ALL ON FUNCTION public.get_token_usage_by_company(start_date timestamp with time zone, end_date timestamp with time zone) TO authenticated;
GRANT ALL ON FUNCTION public.get_token_usage_by_company(start_date timestamp with time zone, end_date timestamp with time zone) TO service_role;


--
-- Name: FUNCTION get_token_usage_report(start_date timestamp with time zone, end_date timestamp with time zone); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.get_token_usage_report(start_date timestamp with time zone, end_date timestamp with time zone) TO anon;
GRANT ALL ON FUNCTION public.get_token_usage_report(start_date timestamp with time zone, end_date timestamp with time zone) TO authenticated;
GRANT ALL ON FUNCTION public.get_token_usage_report(start_date timestamp with time zone, end_date timestamp with time zone) TO service_role;


--
-- Name: FUNCTION get_user_for_login(p_email character varying); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.get_user_for_login(p_email character varying) TO anon;
GRANT ALL ON FUNCTION public.get_user_for_login(p_email character varying) TO authenticated;
GRANT ALL ON FUNCTION public.get_user_for_login(p_email character varying) TO service_role;


--
-- Name: FUNCTION update_agent_delegations_updated_at(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.update_agent_delegations_updated_at() TO anon;
GRANT ALL ON FUNCTION public.update_agent_delegations_updated_at() TO authenticated;
GRANT ALL ON FUNCTION public.update_agent_delegations_updated_at() TO service_role;


--
-- Name: FUNCTION update_documents_updated_at(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.update_documents_updated_at() TO anon;
GRANT ALL ON FUNCTION public.update_documents_updated_at() TO authenticated;
GRANT ALL ON FUNCTION public.update_documents_updated_at() TO service_role;


--
-- Name: FUNCTION update_ucp_updated_at(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.update_ucp_updated_at() TO anon;
GRANT ALL ON FUNCTION public.update_ucp_updated_at() TO authenticated;
GRANT ALL ON FUNCTION public.update_ucp_updated_at() TO service_role;


--
-- Name: FUNCTION update_updated_at_column(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.update_updated_at_column() TO anon;
GRANT ALL ON FUNCTION public.update_updated_at_column() TO authenticated;
GRANT ALL ON FUNCTION public.update_updated_at_column() TO service_role;


--
-- Name: TABLE admin_users; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.admin_users TO anon;
GRANT ALL ON TABLE public.admin_users TO authenticated;
GRANT ALL ON TABLE public.admin_users TO service_role;


--
-- Name: TABLE agent_delegations; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.agent_delegations TO anon;
GRANT ALL ON TABLE public.agent_delegations TO authenticated;
GRANT ALL ON TABLE public.agent_delegations TO service_role;


--
-- Name: TABLE agent_http_tools; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.agent_http_tools TO anon;
GRANT ALL ON TABLE public.agent_http_tools TO authenticated;
GRANT ALL ON TABLE public.agent_http_tools TO service_role;


--
-- Name: TABLE agent_mcp_connections; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.agent_mcp_connections TO anon;
GRANT ALL ON TABLE public.agent_mcp_connections TO authenticated;
GRANT ALL ON TABLE public.agent_mcp_connections TO service_role;


--
-- Name: TABLE agent_mcp_tools; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.agent_mcp_tools TO anon;
GRANT ALL ON TABLE public.agent_mcp_tools TO authenticated;
GRANT ALL ON TABLE public.agent_mcp_tools TO service_role;


--
-- Name: TABLE agents; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.agents TO anon;
GRANT ALL ON TABLE public.agents TO authenticated;
GRANT ALL ON TABLE public.agents TO service_role;


--
-- Name: TABLE checkpoint_blobs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.checkpoint_blobs TO anon;
GRANT ALL ON TABLE public.checkpoint_blobs TO authenticated;
GRANT ALL ON TABLE public.checkpoint_blobs TO service_role;


--
-- Name: TABLE checkpoint_migrations; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.checkpoint_migrations TO anon;
GRANT ALL ON TABLE public.checkpoint_migrations TO authenticated;
GRANT ALL ON TABLE public.checkpoint_migrations TO service_role;


--
-- Name: TABLE checkpoint_writes; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.checkpoint_writes TO anon;
GRANT ALL ON TABLE public.checkpoint_writes TO authenticated;
GRANT ALL ON TABLE public.checkpoint_writes TO service_role;


--
-- Name: TABLE checkpoints; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.checkpoints TO anon;
GRANT ALL ON TABLE public.checkpoints TO authenticated;
GRANT ALL ON TABLE public.checkpoints TO service_role;


--
-- Name: TABLE companies; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.companies TO anon;
GRANT ALL ON TABLE public.companies TO authenticated;
GRANT ALL ON TABLE public.companies TO service_role;


--
-- Name: TABLE company_credits; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.company_credits TO anon;
GRANT ALL ON TABLE public.company_credits TO authenticated;
GRANT ALL ON TABLE public.company_credits TO service_role;


--
-- Name: TABLE conversation_logs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.conversation_logs TO anon;
GRANT ALL ON TABLE public.conversation_logs TO authenticated;
GRANT ALL ON TABLE public.conversation_logs TO service_role;


--
-- Name: TABLE conversations; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.conversations TO anon;
GRANT ALL ON TABLE public.conversations TO authenticated;
GRANT ALL ON TABLE public.conversations TO service_role;


--
-- Name: TABLE credit_transactions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.credit_transactions TO anon;
GRANT ALL ON TABLE public.credit_transactions TO authenticated;
GRANT ALL ON TABLE public.credit_transactions TO service_role;


--
-- Name: TABLE documents; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.documents TO anon;
GRANT ALL ON TABLE public.documents TO authenticated;
GRANT ALL ON TABLE public.documents TO service_role;


--
-- Name: TABLE integrations; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.integrations TO anon;
GRANT ALL ON TABLE public.integrations TO authenticated;
GRANT ALL ON TABLE public.integrations TO service_role;


--
-- Name: TABLE invites; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.invites TO anon;
GRANT ALL ON TABLE public.invites TO authenticated;
GRANT ALL ON TABLE public.invites TO service_role;


--
-- Name: TABLE leads; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.leads TO anon;
GRANT ALL ON TABLE public.leads TO authenticated;
GRANT ALL ON TABLE public.leads TO service_role;


--
-- Name: TABLE legal_documents; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.legal_documents TO anon;
GRANT ALL ON TABLE public.legal_documents TO authenticated;
GRANT ALL ON TABLE public.legal_documents TO service_role;


--
-- Name: TABLE llm_pricing; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.llm_pricing TO anon;
GRANT ALL ON TABLE public.llm_pricing TO authenticated;
GRANT ALL ON TABLE public.llm_pricing TO service_role;


--
-- Name: TABLE mcp_servers; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.mcp_servers TO anon;
GRANT ALL ON TABLE public.mcp_servers TO authenticated;
GRANT ALL ON TABLE public.mcp_servers TO service_role;


--
-- Name: TABLE memory_processing_locks; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.memory_processing_locks TO anon;
GRANT ALL ON TABLE public.memory_processing_locks TO authenticated;
GRANT ALL ON TABLE public.memory_processing_locks TO service_role;


--
-- Name: TABLE memory_settings; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.memory_settings TO anon;
GRANT ALL ON TABLE public.memory_settings TO authenticated;
GRANT ALL ON TABLE public.memory_settings TO service_role;


--
-- Name: TABLE messages; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.messages TO anon;
GRANT ALL ON TABLE public.messages TO authenticated;
GRANT ALL ON TABLE public.messages TO service_role;


--
-- Name: TABLE password_reset_tokens; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.password_reset_tokens TO anon;
GRANT ALL ON TABLE public.password_reset_tokens TO authenticated;
GRANT ALL ON TABLE public.password_reset_tokens TO service_role;


--
-- Name: TABLE payment_history; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.payment_history TO anon;
GRANT ALL ON TABLE public.payment_history TO authenticated;
GRANT ALL ON TABLE public.payment_history TO service_role;


--
-- Name: TABLE plans; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.plans TO anon;
GRANT ALL ON TABLE public.plans TO authenticated;
GRANT ALL ON TABLE public.plans TO service_role;


--
-- Name: TABLE sanitization_jobs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.sanitization_jobs TO anon;
GRANT ALL ON TABLE public.sanitization_jobs TO authenticated;
GRANT ALL ON TABLE public.sanitization_jobs TO service_role;


--
-- Name: TABLE session_summaries; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.session_summaries TO anon;
GRANT ALL ON TABLE public.session_summaries TO authenticated;
GRANT ALL ON TABLE public.session_summaries TO service_role;


--
-- Name: TABLE subscriptions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.subscriptions TO anon;
GRANT ALL ON TABLE public.subscriptions TO authenticated;
GRANT ALL ON TABLE public.subscriptions TO service_role;


--
-- Name: TABLE system_logs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.system_logs TO anon;
GRANT ALL ON TABLE public.system_logs TO authenticated;
GRANT ALL ON TABLE public.system_logs TO service_role;


--
-- Name: TABLE token_usage_logs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.token_usage_logs TO anon;
GRANT ALL ON TABLE public.token_usage_logs TO authenticated;
GRANT ALL ON TABLE public.token_usage_logs TO service_role;


--
-- Name: TABLE ucp_connections; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.ucp_connections TO anon;
GRANT ALL ON TABLE public.ucp_connections TO authenticated;
GRANT ALL ON TABLE public.ucp_connections TO service_role;


--
-- Name: TABLE ucp_connection_summary; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.ucp_connection_summary TO anon;
GRANT ALL ON TABLE public.ucp_connection_summary TO authenticated;
GRANT ALL ON TABLE public.ucp_connection_summary TO service_role;


--
-- Name: TABLE user_memories; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.user_memories TO anon;
GRANT ALL ON TABLE public.user_memories TO authenticated;
GRANT ALL ON TABLE public.user_memories TO service_role;


--
-- Name: TABLE users_v2; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.users_v2 TO anon;
GRANT ALL ON TABLE public.users_v2 TO authenticated;
GRANT ALL ON TABLE public.users_v2 TO service_role;


--
-- Name: TABLE widget_rate_limits; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.widget_rate_limits TO anon;
GRANT ALL ON TABLE public.widget_rate_limits TO authenticated;
GRANT ALL ON TABLE public.widget_rate_limits TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


