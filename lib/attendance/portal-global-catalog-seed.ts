// AUTO-GERADO por scripts/generate-portal-global-catalog.mjs (43P1.2). NÃO editar à mão.
// Fonte: docs/intake/portal-registry/portal_registry_unificado_linha_a_linha.csv (official_research).
// Sem credencial/PII. Catálogo GLOBAL (scope:'global'). real_action_allowed sempre false.
import type { PortalDefinitionRecord } from '@/lib/attendance/portal-admin-sanitizers';

export const PORTAL_GLOBAL_CATALOG_GENERATED_AT = '2026-06-18T00:00:00.000Z';
export const PORTAL_GLOBAL_CATALOG_STATS = {
  "source_rows": 189,
  "mapped": 189,
  "seed_active": 111,
  "needs_review": 78,
  "ignored": 0,
  "insurers": [
    "alfa",
    "allianz",
    "azul",
    "bradesco",
    "chubb",
    "hdi",
    "junto",
    "liberty_legacy",
    "mapfre",
    "open_insurance",
    "porto",
    "sompo",
    "sulamerica",
    "sura",
    "susep",
    "tokio_marine",
    "yelum",
    "zurich"
  ],
  "deduped": 189
} as const;

export const PORTAL_GLOBAL_CATALOG_SEED: PortalDefinitionRecord[] = [
  {
    "portal_id": "allianz__allianznet_corretor_portal_do_corretor",
    "label": "AllianzNet Corretor (Portal do Corretor)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianznet.com.br/ngx-epac/public/home",
    "login_url": "https://www.allianznet.com.br/ngx-epac/public/home",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal do corretor com login por usuário e senha; página indica senha sensível a maiúsculas/minúsculas e oferece recuperação de senha.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianznet.com.br/ngx-epac/public/home",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__allianznet_sso_idp_seaservlet",
    "label": "AllianzNet SSO/IDP (SEAServlet)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianznet.com.br/idp/SEAServlet?action=home",
    "login_url": "https://www.allianznet.com.br/idp/SEAServlet?action=home",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de identificação do SSO/IDP; exibe mensagem de sessão expirada e campos User/Password.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "sessionized",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianznet.com.br/idp/SEAServlet?action=home",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__allianz_cliente_portal_do_cliente",
    "label": "Allianz Cliente (Portal do Cliente)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://seguros.allianz.com.br/ngx-ecliente/public/register",
    "login_url": "https://seguros.allianz.com.br/ngx-ecliente/public/register",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal do segurado/cliente com serviços como emissão de 2ª via de boleto, visão de apólices, abertura e status de sinistros (conforme página institucional); cadastro/ativação utiliza código enviado por e-mail.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/sobre-allianz/allianz-cliente.html; https://seguros.allianz.com.br/ngx-ecliente/public/register; https://seguros.allianz.com.br/ngx-ecliente/public/activation-code",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__allianz_cliente_tela_de_codigo_de_ativacao",
    "label": "Allianz Cliente (tela de código de ativação)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://seguros.allianz.com.br/ngx-ecliente/public/activation-code",
    "login_url": "https://seguros.allianz.com.br/ngx-ecliente/public/activation-code",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password",
      "mfa"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": true,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Fluxo de registro/ativação do portal solicita CPF/CNPJ, usuário e código de ativação.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://seguros.allianz.com.br/ngx-ecliente/public/activation-code",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__pagamentos_allianz_extrato_boleto_2_via",
    "label": "Pagamentos Allianz (extrato/boleto/2ª via)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianz.com.br/pagamentos.html",
    "login_url": "https://www.allianz.com.br/pagamentos.html",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página institucional para acessar extrato e boleto/2ª via e apoiar gestão de pagamentos.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "cobrança",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/pagamentos.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__servicos_digitais_allianz_hub",
    "label": "Serviços Digitais Allianz (hub)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianz.com.br/servicos.html",
    "login_url": "https://www.allianz.com.br/servicos.html",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub institucional com atalhos para portais (corretor/cliente/prestador), chat e outras jornadas.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/servicos.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__contato_allianz_central_de_canais_digitais",
    "label": "Contato Allianz (central de canais digitais)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianz.com.br/contato.html",
    "login_url": "https://www.allianz.com.br/contato.html",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página institucional consolida canais digitais para assistência, sinistro digital, chat e app.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/contato.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__sinistro_digital_allianz_aviso_e_acompanhamento",
    "label": "Sinistro Digital Allianz (aviso e acompanhamento)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://sec-br.controlexpert.com",
    "login_url": "https://sec-br.controlexpert.com/apps/allianz.ect360/acm/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Plataforma externa linkada do site da Allianz para aviso e acompanhamento de sinistro; evidência institucional também afirma acesso por múltiplos canais.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/contato.html; https://sec-br.controlexpert.com/apps/allianz.ect360/acm/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__assistencia_24h_online_allianz_auto",
    "label": "Assistência 24h online Allianz Auto",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://allianzauto.assistencia24h.com.br/",
    "login_url": "https://allianzauto.assistencia24h.com.br/",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Canal web para solicitação de assistência auto (linkado do portal institucional).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "assistência",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/contato.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__chat_allianz_atendimento_digital",
    "label": "Chat Allianz (atendimento digital)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://chatcc.allianz.com.br",
    "login_url": "https://chatcc.allianz.com.br",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Canal de chat para atendimento (linkado em páginas institucionais de serviços/contato).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/contato.html; https://www.allianz.com.br/servicos.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__allianznet_prestador_portal_parceiro_prestador",
    "label": "AllianzNet Prestador (portal parceiro/prestador)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianznet.com.br/",
    "login_url": "https://www.allianznet.com.br/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página institucional de prestadores informa existir canal dedicado via 'Allianznet Prestador' para gerir documentações e pagamentos.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.allianz.com.br/sobre-allianz/prestadores.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__portal_transportes_allianz",
    "label": "Portal Transportes (Allianz)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://transportes.allianznet.com.br/Login",
    "login_url": "https://transportes.allianznet.com.br/Login",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal específico de transportes com tela de login e seleção de filial; função exata (interno x parceiro) não é explicitada na tela.",
    "metadata": {
      "audience": "interno",
      "line_of_business": "transporte",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://transportes.allianznet.com.br/Login; https://www.allianz.com.br/sobre-allianz/prestadores.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__app_allianz_cliente_android",
    "label": "App Allianz Cliente (Android)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://play.google.com/store/apps/details?hl=pt_BR&id=br.com.allianz.mobile.auto",
    "login_url": "https://play.google.com/store/apps/details?hl=pt_BR&id=br.com.allianz.mobile.auto",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App oficial para Auto/Residência/Vida/AP; permite consultar apólice, pagamentos, aviso/acompanhamento de sinistro e assistência (conforme descrição).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?hl=pt_BR&id=br.com.allianz.mobile.auto; https://www.allianz.com.br/servicos/app-allianz-cliente.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__app_allianz_cliente_ios",
    "label": "App Allianz Cliente (iOS)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://apps.apple.com/br/app/allianz-cliente/id1554862261",
    "login_url": "https://apps.apple.com/br/app/allianz-cliente/id1554862261",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Versão iOS do app oficial Allianz Cliente.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/allianz-cliente/id1554862261; https://www.allianz.com.br/servicos/app-allianz-cliente.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__cotacao_online_hub",
    "label": "Cotação online (hub)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://cote.allianz.com.br/",
    "login_url": "https://cote.allianz.com.br/",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Hub de cotação on-line referenciado no site institucional para Seguro Auto, Residencial e Vida (pode ser SPA).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.allianz.com.br/; https://cote.allianz.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__corretor_online_col_login",
    "label": "Corretor Online (COL) - login",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://corretor.portoseguro.com.br/corretoronline/",
    "login_url": "https://corretor.portoseguro.com.br/corretoronline/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password",
      "captcha"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal do corretor solicita CPF, senha e SUSEP e menciona reCAPTCHA para segurança. Há mensagens de sessão expirada e restrições por SUSEP/parceiro.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://corretor.portoseguro.com.br/corretoronline/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__portal_do_cliente_porto_id_login",
    "label": "Portal do Cliente (Porto ID) - login",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://cliente.portoseguro.com.br/auth/login",
    "login_url": "https://cliente.portoseguro.com.br/auth/login",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Entrada do portal do cliente via Porto ID (conteúdo carregado por JS; URL de login obtida em base de ajuda e links institucionais).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/consulta-de-clientes/portal-cliente-porto-seguro; https://www.portoseguro.com.br/consulta-de-clientes/login-no-portal-do-cliente",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__area_do_cliente_hub_institucional",
    "label": "Área do Cliente (hub institucional)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/area-do-cliente",
    "login_url": "https://www.portoseguro.com.br/area-do-cliente",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página-hub para acesso à Área do Cliente (conteúdo/CTA de entrada observável via resultado oficial; página pode carregar via JS na coleta).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/area-do-cliente; https://www.portoseguro.com.br/consulta-de-clientes/portal-cliente-porto-seguro",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__quero_pagar_2_via_de_boletos_pagamentos",
    "label": "Quero Pagar (2ª via de boletos / pagamentos)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/quero-pagar",
    "login_url": "https://www.portoseguro.com.br/quero-pagar",
    "supported_journeys": [
      "document_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal para emissão de 2ª via de boletos por produto; página informa que alguns produtos só podem ser visualizados na Área do Cliente.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "segunda_via",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/quero-pagar",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__faq_2_via_de_boleto_da_apolice_instrucoes",
    "label": "FAQ: 2ª via de boleto da apólice (instruções)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/faqs/como-solicito-segunda-via-de-boleto-da-minha-apolice",
    "login_url": "https://www.portoseguro.com.br/faqs/como-solicito-segunda-via-de-boleto-da-minha-apolice",
    "supported_journeys": [
      "document_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "FAQ oficial orienta emissão via app (menu financeiro) e alternativa via 'Quero Pagar' ou WhatsApp.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "segunda_via",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.portoseguro.com.br/faqs/como-solicito-segunda-via-de-boleto-da-minha-apolice; https://www.portoseguro.com.br/quero-pagar",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__avisos_de_sinistros_hub",
    "label": "Avisos de Sinistros (hub)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/atendimento/sinistros",
    "login_url": "https://www.portoseguro.com.br/atendimento/sinistros",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página institucional promete facilidade para aviso de sinistros (veículos, imóveis, empresas, celular). Pode requerer navegação JS.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/atendimento/sinistros",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__sinistro_de_veiculos_aviso_digital",
    "label": "Sinistro de Veículos (aviso digital)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/sinistros/veiculos",
    "login_url": "https://www.portoseguro.com.br/sinistros/veiculos",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página institucional de sinistro de veículos indica abertura de sinistro 100% digital.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/sinistros/veiculos",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__sinistro_seguro_celular",
    "label": "Sinistro Seguro Celular",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/sinistros/celular",
    "login_url": "https://www.portoseguro.com.br/sinistros/celular",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página institucional indica canais digitais para abertura/acompanhamento de sinistro de celular (pode carregar via JS).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "unknown",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/sinistros/celular.html",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__sinistro_vida_e_familia_seguro_de_vida",
    "label": "Sinistro Vida e Família (Seguro de Vida)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/sinistros/vida-e-familia/sinistro-seguro-vida",
    "login_url": "https://www.portoseguro.com.br/sinistros/vida-e-familia/sinistro-seguro-vida",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página institucional com orientações para sinistro de seguro de vida.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "vida",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.portoseguro.com.br/sinistros/vida-e-familia/sinistro-seguro-vida",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__assistencia_24h_para_o_seu_carro_sos_canais_digi",
    "label": "Assistência 24h para o seu carro (SOS / canais digitais)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/beneficios/assistencia-24h-para-o-seu-carro",
    "login_url": "https://www.portoseguro.com.br/beneficios/assistencia-24h-para-o-seu-carro",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página institucional orienta solicitação de assistência por SOS Porto Seguro e WhatsApp.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "assistência",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/beneficios/assistencia-24h-para-o-seu-carro",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__seguro_auto_landing_de_cotacao",
    "label": "Seguro Auto (landing de cotação)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/seguro-auto",
    "login_url": "https://www.portoseguro.com.br/seguro-auto",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Landing institucional do Seguro Auto com CTA de 'Faça uma cotação'.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.portoseguro.com.br/seguro-auto; https://www.portoseguro.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__cotacao_digital_seguro_auto_loja_placa_do_veicul",
    "label": "Cotação digital Seguro Auto (loja) - placa do veículo",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://www.portoseguro.com.br/loja/seguro-auto/placa-do-veiculo",
    "login_url": "https://www.portoseguro.com.br/loja/seguro-auto/placa-do-veiculo",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Fluxo de cotação digital solicita placa do veículo e preenche dados automaticamente.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "cotação",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.portoseguro.com.br/loja/seguro-auto/placa-do-veiculo",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__app_porto_android",
    "label": "App Porto (Android)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://play.google.com/store/apps/details?hl=pt_BR&id=br.com.portoseguro.experienciacliente.mundoporto",
    "login_url": "https://play.google.com/store/apps/details?hl=pt_BR&id=br.com.portoseguro.experienciacliente.mundoporto",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App oficial agrega serviços de seguros e conta/cartão; descrição cita 2ª via de boleto, aviso de sinistro e assistência 24h, inclusive para Azul Seguros.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?hl=pt_BR&id=br.com.portoseguro.experienciacliente.mundoporto; https://www.portoseguro.com.br/app-porto-download",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__app_porto_ios",
    "label": "App Porto (iOS)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://apps.apple.com/br/app/porto-conta-digital-e-seguros/id1511026277",
    "login_url": "https://apps.apple.com/br/app/porto-conta-digital-e-seguros/id1511026277",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Versão iOS do app Porto (Conta Digital e Seguros).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/porto-conta-digital-e-seguros/id1511026277; https://www.portoseguro.com.br/app-porto-download",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__sinistro_agil_rota_legada",
    "label": "Sinistro Ágil (rota legada)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://wwws.portoseguro.com.br/avisointernet/iniciarAviso.do",
    "login_url": "https://wwws.portoseguro.com.br/avisointernet/iniciarAviso.do",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota legada relacionada a aviso online; a própria página informa que o site mudou e direciona para novo fluxo (coleta apresentou erro de decodificação).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "legacy_route",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "partial_evidence",
      "official_sources": "https://wwws.portoseguro.com.br/avisointernet/iniciarAviso.do",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__acompanhamento_de_sinistro_auto_rota_legada",
    "label": "Acompanhamento de Sinistro Auto (rota legada)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://wwws.portoseguro.com.br/acompanhamentosinistro/login.doss",
    "login_url": "https://wwws.portoseguro.com.br/acompanhamentosinistro/login.doss",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota legada para acompanhamento de sinistro; indica migração para timeline (na coleta houve erro de decodificação).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "legacy_route",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "partial_evidence",
      "official_sources": "https://wwws.portoseguro.com.br/acompanhamentosinistro/login.doss",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__acessos_hub_de_portais",
    "label": "Acessos (hub de portais)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdiseguros.com.br/acessos",
    "login_url": "https://www.hdiseguros.com.br/acessos",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub oficial lista portais para corretor, colaborador, segurado, prestador (portal de serviços), desenvolvedor e CitNet.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.hdiseguros.com.br/acessos",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__canais_digitais_hub_de_jornadas_e_portais",
    "label": "Canais Digitais (hub de jornadas e portais)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdiseguros.com.br/servicos/canais-digitais",
    "login_url": "https://www.hdiseguros.com.br/servicos/canais-digitais",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página descreve canais digitais para segurado, corretor, terceiro e prestador, incluindo app e assistência 24h.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__hdi_digital_portal_do_corretor_login",
    "label": "HDI Digital (Portal do Corretor) - login",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdi.com.br/hdidigital/",
    "login_url": "https://www.hdi.com.br/hdidigital/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal do corretor com campos Usuário/Senha e fluxo de 'esqueci minha senha'; página orienta cadastro de corretores via link institucional.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.hdi.com.br/hdidigital/; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__portal_do_segurado_hdi_login",
    "label": "Portal do Segurado HDI - login",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdi.com.br/segurado/v2/portalDoSegurado/login",
    "login_url": "https://www.hdi.com.br/segurado/v2/portalDoSegurado/login",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página de login do Portal do Segurado indica ações disponíveis: abrir assistência 24h, avisar sinistro, emitir 2ª via de boleto, acompanhar sinistro e conferir apólice (conteúdo pode carregar via JS na coleta).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.hdi.com.br/segurado/v2/portalDoSegurado/login; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__aviso_de_sinistro_segurado_sofia",
    "label": "Aviso de Sinistro (Segurado) - Sofia",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://avisodesinistro.hdi.com.br/",
    "login_url": "https://avisodesinistro.hdi.com.br/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Canal dedicado para aviso de sinistro do segurado (URL referenciada no site oficial; conteúdo não foi renderizado na coleta).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.hdiseguros.com.br/; https://avisodesinistro.hdi.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__portal_do_terceiro_sinistro_pagina_de_instrucoes",
    "label": "Portal do Terceiro (sinistro) - página de instruções",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdiseguros.com.br/servicos/portal-do-terceiro",
    "login_url": "https://www.hdiseguros.com.br/servicos/portal-do-terceiro",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página orienta terceiros a se cadastrarem com placa do veículo segurado ou número do sinistro + data de ocorrência, e lista funcionalidades (aviso, agendamento de vistoria, envio de fotos, status, etc.).",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.hdiseguros.com.br/servicos/portal-do-terceiro",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__portal_do_terceiro_acesso_app",
    "label": "Portal do Terceiro (acesso/app)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdi.com.br/terceiro/",
    "login_url": "https://www.hdi.com.br/terceiro/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal de acesso do terceiro (cadastro e abertura do sinistro) apontado na página de instruções; renderização pública via JS dificultou captura textual.",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.hdiseguros.com.br/servicos/portal-do-terceiro; https://www.hdi.com.br/terceiro/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__portal_de_servicos_prestadores_oficinas_login",
    "label": "Portal de Serviços (prestadores/oficinas) - login",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://www.hdi.com.br/hdiprestador/",
    "login_url": "https://www.hdi.com.br/hdiprestador/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Login para prestadores/oficinas; seleção de perfil (Oficinas/Prestador de Serviços).",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.hdi.com.br/hdiprestador/; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__assistencia_24h_autoatendimento_facil24h",
    "label": "Assistência 24h (autoatendimento Facil24h)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://autoatendimento.facil24h.com.br/",
    "login_url": "https://autoatendimento.facil24h.com.br/",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Canal externo linkado do site oficial para solicitação de assistência (auto e residência).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "assistência",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.hdiseguros.com.br/; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__app_hdi_segurado_android",
    "label": "App HDI Segurado (Android)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://play.google.com/store/apps/details?hl=pt_BR&id=com.hdi.segurado",
    "login_url": "https://play.google.com/store/apps/details?hl=pt_BR&id=com.hdi.segurado",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App do segurado com carteirinha, apólice, pagamentos, oficinas, assistência 24h e aviso/acompanhamento de sinistro.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?hl=pt_BR&id=com.hdi.segurado; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__app_hdi_segurado_ios",
    "label": "App HDI Segurado (iOS)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://apps.apple.com/br/app/hdi-segurado/id1170248571",
    "login_url": "https://apps.apple.com/br/app/hdi-segurado/id1170248571",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Versão iOS do app HDI Segurado.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/hdi-segurado/id1170248571; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__app_hdi_corretor_android",
    "label": "App HDI Corretor (Android)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://play.google.com/store/apps/details?hl=pt&id=hdi.com.hdicorretor",
    "login_url": "https://play.google.com/store/apps/details?hl=pt&id=hdi.com.hdicorretor",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App para corretores com foco em gestão de carteira, tarefas, criação de proposta e atalhos de contato.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?hl=pt&id=hdi.com.hdicorretor; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__app_hdi_corretor_ios",
    "label": "App HDI Corretor (iOS)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://apps.apple.com/br/app/hdi-corretor/id1133425770",
    "login_url": "https://apps.apple.com/br/app/hdi-corretor/id1133425770",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Versão iOS do app HDI Corretor.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/hdi-corretor/id1133425770; https://www.hdiseguros.com.br/servicos/canais-digitais",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__portal_do_corretor_portal_parceiros_acesso",
    "label": "Portal do Corretor (Portal Parceiros) - acesso",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://portalparceiros.tokiomarine.com.br/",
    "login_url": "https://portalparceiros.tokiomarine.com.br/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página institucional de corretores direciona para Portal do Corretor; portal é restrito a corretores/colaboradores/parceiros e autentica via SSO.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.tokiomarine.com.br/corretores/; https://portalparceiros.tokiomarine.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__sso_da_area_do_corretor_openam",
    "label": "SSO da Área do Corretor (OpenAM)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://ssoportais3.tokiomarine.com.br/openam/",
    "login_url": "https://ssoportais3.tokiomarine.com.br/openam/XUI/?realm=TOKIOLFR&goto=http://portalparceiros.tokiomarine.com.br/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Fluxo SSO (OpenAM) usado para autenticação do Portal Parceiros/Corretor; página pode renderizar em JS ('Carregando...').",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "sessionized",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "partial_evidence",
      "official_sources": "https://portalparceiros.tokiomarine.com.br/; https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__cadastro_de_corretores_parceiros_de_negocios",
    "label": "Cadastro de Corretores (Parceiros de Negócios)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://portal.tokiomarine.com.br/parceiroNegocio/cadastro/corretor",
    "login_url": "https://portal.tokiomarine.com.br/parceiroNegocio/cadastro/corretor",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Formulário institucional para cadastro de corretores, com análise prévia de informações e documentos.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://portal.tokiomarine.com.br/parceiroNegocio/cadastro/corretor; https://www.tokiomarine.com.br/corretores/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__canais_digitais_tokio_marine_hub_do_cliente",
    "label": "Canais Digitais Tokio Marine (hub do cliente)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://www.tokiomarine.com.br/canais-digitais/",
    "login_url": "https://www.tokiomarine.com.br/canais-digitais/",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página institucional consolida Área do Cliente, assistências, pagamentos, 2ª via de apólice e links para apps; contém link explícito para Área do Corretor (SSO).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__nova_area_do_cliente_autoatendimento_portal",
    "label": "Nova Área do Cliente / Autoatendimento (portal)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://autoatendimento.tokiomarine.com.br/",
    "login_url": "https://autoatendimento.tokiomarine.com.br/superapp/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal de autoatendimento do cliente indicado no hub de Canais Digitais; rotas internas e conteúdo podem ser carregados via JS.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "strong_evidence",
      "official_sources": "https://www.tokiomarine.com.br/canais-digitais/; https://autoatendimento.tokiomarine.com.br/superapp/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__pagamentos_area_do_cliente_autoatendimento",
    "label": "Pagamentos (Área do Cliente / Autoatendimento)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://autoatendimento.tokiomarine.com.br/portais/ui/smart-web/",
    "login_url": "https://autoatendimento.tokiomarine.com.br/portais/ui/smart-web/",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Deep link de 'Pagamentos' a partir do hub institucional; renderização pública não foi capturada na coleta (JS).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "cobrança",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "partial_evidence",
      "official_sources": "https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__2_via_apolice_area_do_cliente_autoatendimento",
    "label": "2ª via Apólice (Área do Cliente / Autoatendimento)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://autoatendimento.tokiomarine.com.br/portais/ui/smart-web/",
    "login_url": "https://autoatendimento.tokiomarine.com.br/portais/ui/smart-web/",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Deep link para 2ª via de apólice a partir do hub institucional; aparentemente usa a mesma rota base de smart-web.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "apólice/documentos",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "partial_evidence",
      "official_sources": "https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__assistencia_24h_guincho_area_do_cliente_autoaten",
    "label": "Assistência 24h - guincho (Área do Cliente / Autoatendimento)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://autoatendimento.tokiomarine.com.br/portais/ui/assistencia24h/",
    "login_url": "https://autoatendimento.tokiomarine.com.br/portais/ui/assistencia24h/",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Deep link de assistência 24h automóvel (guincho) indicado no hub institucional; conteúdo pode ser gerenciado via SPA.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "assistência",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "partial_evidence",
      "official_sources": "https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__cotar_seguro_auto_e_moto_digital",
    "label": "Cotar Seguro Auto e Moto (digital)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://cotacoes.tokiomarine.com.br/massificados/auto/digital/front/",
    "login_url": "https://cotacoes.tokiomarine.com.br/massificados/auto/digital/front/",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página dedicada de cotação online de seguro auto/moto (digital).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://cotacoes.tokiomarine.com.br/massificados/auto/digital/front/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__cotacoes_hub",
    "label": "Cotações (hub)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://www.tokiomarine.com.br/cotacoes/",
    "login_url": "https://www.tokiomarine.com.br/cotacoes/",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub institucional para simulações/cotações on-line por categoria (auto, moto, etc.).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.tokiomarine.com.br/cotacoes/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__app_tokio_marine_seguro_auto_android",
    "label": "App Tokio Marine: seguro auto (Android)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://play.google.com/store/apps/details?hl=pt&id=br.com.tokiomarine.seguradora.mobile.superapp",
    "login_url": "https://play.google.com/store/apps/details?hl=pt&id=br.com.tokiomarine.seguradora.mobile.superapp",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Super App do segurado com gestão de seguros, documentos, assistência 24h, sinistro e pagamentos; inclui cotação/contratação conforme descrição.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?hl=pt&id=br.com.tokiomarine.seguradora.mobile.superapp; https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__app_tokio_marine_seguro_auto_ios",
    "label": "App Tokio Marine: seguro auto (iOS)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://apps.apple.com/br/app/tokio-marine-seguro-auto/id1582879602",
    "login_url": "https://apps.apple.com/br/app/tokio-marine-seguro-auto/id1582879602",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Versão iOS do app do segurado com pagamentos, documentos, assistência 24h e sinistro.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/tokio-marine-seguro-auto/id1582879602; https://www.tokiomarine.com.br/canais-digitais/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__tokio_corretor_android",
    "label": "Tokio Corretor (Android)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://play.google.com/store/apps/details?hl=pt&id=br.com.tokiomarine.seguradora.mobile.superapp.corretor",
    "login_url": "https://play.google.com/store/apps/details?hl=pt&id=br.com.tokiomarine.seguradora.mobile.superapp.corretor",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App para corretores com consulta de apólices/pagamentos dos segurados, 2ª via de boletos/documentos, pendências de emissão e extratos/comissão, aviso/acompanhamento de sinistro.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?hl=pt&id=br.com.tokiomarine.seguradora.mobile.superapp.corretor; https://www.tokiomarine.com.br/lp/mobile/corretor/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__tokio_corretor_ios",
    "label": "Tokio Corretor (iOS)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://apps.apple.com/br/app/tokio-corretor/id6450320793",
    "login_url": "https://apps.apple.com/br/app/tokio-corretor/id6450320793",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Versão iOS do app Tokio Corretor.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/tokio-corretor/id6450320793; https://www.tokiomarine.com.br/lp/mobile/corretor/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__super_app_corretor_landing_institucional",
    "label": "Super App Corretor (landing institucional)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://www.tokiomarine.com.br/lp/mobile/corretor/",
    "login_url": "https://www.tokiomarine.com.br/lp/mobile/corretor/",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Landing do app para corretores informa que o acesso usa as mesmas credenciais já existentes no portal do corretor e que o uso requer corretor cadastrado e liberado.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.tokiomarine.com.br/lp/mobile/corretor/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__super_app_cliente_landing_institucional",
    "label": "Super App Cliente (landing institucional)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://www.tokiomarine.com.br/lp/mobile/cliente/",
    "login_url": "https://www.tokiomarine.com.br/lp/mobile/cliente/",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Landing do Super App do cliente descreve funcionalidades como 2ª via de apólices, documentos, assistências e pagamentos (Pix).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.tokiomarine.com.br/lp/mobile/cliente/",
      "checked_at": "2026-04-06",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 1.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__alfanet_workflow_sinistro_login",
    "label": "AlfaNet Workflow (sinistro) - login",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://workflow.alfaseguradora.com.br/",
    "login_url": "https://workflow.alfaseguradora.com.br/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Sistema 'Workflow Sinistro AlfaNet' acessível pela internet, mas aparenta ser para operação interna/backoffice (não há evidência pública de acesso por corretor).",
    "metadata": {
      "audience": "interno",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "no",
      "confidence": "partial_evidence",
      "official_sources": "https://workflow.alfaseguradora.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__area_do_corretor_login",
    "label": "Área do Corretor (login)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/portal/Corretor/Login",
    "login_url": "https://wwws.alfaseguradora.com.br/portal/Corretor/Login",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal direcionado a corretores (Alfa Seguradora / Alfa Vida).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/portal/Corretor/Login",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__calculo_portal_de_calculo_cotacao",
    "label": "Cálculo (portal de cálculo/cotação)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://calculo.alfaseguradora.com.br/",
    "login_url": "https://calculo.alfaseguradora.com.br/",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal específico para cálculo/cotação; tipicamente usado para operações do corretor.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://calculo.alfaseguradora.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__site_institucional_home_com_atalhos_para_area_do",
    "label": "Site institucional (home com atalhos para área do cliente e do corretor)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/",
    "login_url": "https://wwws.alfaseguradora.com.br/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Home expõe atalhos 'Área do cliente' e 'Área do corretor', além de conteúdos de produtos e assistência 24h.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__area_do_segurado_login",
    "label": "Área do Segurado (login)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Segurado/",
    "login_url": "https://wwws.alfaseguradora.com.br/Segurado/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Área restrita do segurado (cliente).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Segurado/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__assistencia_24h_e_aviso_de_sinistro_contatos_por",
    "label": "Assistência 24h e aviso de sinistro (contatos por produto)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Auto/Assistencia",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Auto/Assistencia",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página lista contatos de assistência e aviso de sinistro para linhas (Vida; Auto/Resid/Empresa/Condomínio etc).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "assistência",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Auto/Assistencia",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__oficinas_referenciadas_sinistro_auto",
    "label": "Oficinas Referenciadas (sinistro auto)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Sinistro/OficinasReferenciadas",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Sinistro/OficinasReferenciadas",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Consulta de oficinas referenciadas dentro do menu de sinistro.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "assistência",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Sinistro/OficinasReferenciadas",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__formularios_uteis_sinistro",
    "label": "Formulários Úteis (sinistro)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Sinistro/Formularios",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Sinistro/Formularios",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página agrega formulários e menu de 'Em caso de sinistro'.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "apólice/documentos",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Sinistro/Formularios",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__formulario_de_aviso_de_sinistro_pdf",
    "label": "Formulário de Aviso de Sinistro (PDF)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/2/Aviso%20de%20sinistro.pdf",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/2/Aviso%20de%20sinistro.pdf",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "PDF de aviso de sinistro menciona campos para corretor; útil para processos e coleta de dados.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/2/Aviso%20de%20sinistro.pdf",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__formulario_de_indenizacao_integral_pdf",
    "label": "Formulário de Indenização Integral (PDF)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/1/Formulario%20Indenizacao%20Integral%20Alfa.pdf",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/1/Formulario%20Indenizacao%20Integral%20Alfa.pdf",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Documento de sinistro (indenização integral) com orientações e prazos.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/1/Formulario%20Indenizacao%20Integral%20Alfa.pdf",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__procedimentos_de_sinistro_vida_pdf",
    "label": "Procedimentos de Sinistro Vida (PDF)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/2/Procedimentos%20-%20Sinistro%20Vida-dez-18.pdf",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/2/Procedimentos%20-%20Sinistro%20Vida-dez-18.pdf",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "PDF descreve canais e procedimentos para comunicar sinistro vida.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "vida",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Arquivos/244/2/Procedimentos%20-%20Sinistro%20Vida-dez-18.pdf",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__condicoes_gerais_e_manuais_de_assistencia_hub",
    "label": "Condições Gerais e manuais de assistência (hub)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/Portal/Alfa/CondicoesGerais",
    "login_url": "https://wwws.alfaseguradora.com.br/Portal/Alfa/CondicoesGerais",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página lista condições gerais e manuais (inclui manuais de assistência 24h).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "apólice/documentos",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/Portal/Alfa/CondicoesGerais",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__corretor_online_grupo_porto_acesso_para_corretor",
    "label": "Corretor Online (Grupo Porto) - acesso para corretores (inclui Azul no ecossistema)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://corretor.portoseguro.com.br/corretoronline/",
    "login_url": "https://corretor.portoseguro.com.br/corretoronline/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password",
      "captcha"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de login do Corretor Online exibe 'Ecossistema' com Azul; usada como base para ferramentas de cálculo/renovação citadas pela Azul.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://corretor.portoseguro.com.br/corretoronline/; https://www.azulseguros.com.br/perguntas-frequentes/como-fazer-o-calculo-de-seguros-na-azul-seguros/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__ppweb_multicalculo_renovacao_congenere_via_corre",
    "label": "PPWeb (multicálculo/renovação congênere) - via Corretor Online",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://corretor.portoseguro.com.br/corretoronline/",
    "login_url": "https://www.azulseguros.com.br/perguntas-frequentes/como-fazer-o-calculo-de-seguros-na-azul-seguros/",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [
      "password",
      "captcha"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "FAQ da Azul orienta corretores a usar o PPWeb disponível no Corretor Online (plataforma do grupo). Não há URL pública dedicada do PPWeb; acesso presumido pós-login.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "auto",
      "journey_type": "multicálculo",
      "url_kind": "deep_link",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.azulseguros.com.br/perguntas-frequentes/como-fazer-o-calculo-de-seguros-na-azul-seguros/; https://corretor.portoseguro.com.br/corretoronline/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__area_restrita_hub_multi_perfil_corretor_cliente_",
    "label": "Área Restrita (hub multi-perfil: corretor/cliente/terceiro/produção/prestador)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Seletor de perfil com login e fluxos de recuperação de senha; usa reCAPTCHA no fluxo de recuperação.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__portal_do_segurado_base_logada",
    "label": "Portal do Segurado (base logada)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Base da área logada do segurado; usada também como referência em FAQ de parcelas.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.azulseguros.com.br/perguntas-frequentes/como-o-segurado-pode-consultar-situacao-das-parcelas-da-apolice/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__cadastro_no_portal_do_segurado_criacao_de_login_",
    "label": "Cadastro no Portal do Segurado (criação de login/senha)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/cadastro/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/cadastro/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Fluxo de cadastro com confirmação por e-mail ou celular (chave de validação); orienta contato com corretor quando dados não são reconhecidos.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/cadastro/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__2_via_de_apolice_portal_do_segurado",
    "label": "2ª via de apólice (Portal do Segurado)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/2a-via-de-apolice/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/2a-via-de-apolice/",
    "supported_journeys": [
      "document_query"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página existe e informa que é necessário login para acessar.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "segunda_via",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/2a-via-de-apolice/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__2_via_de_apolice_deep_link_apolice_parcelas",
    "label": "2ª via de apólice (deep link: apólice / parcelas)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/2a-via-de-apolice/apolice-parcelas/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/2a-via-de-apolice/apolice-parcelas/",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Rota interna da jornada de 2ª via/apólice; requer login.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "apólice/documentos",
      "url_kind": "deep_link",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/2a-via-de-apolice/apolice-parcelas/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__relacao_de_parcelas_status_de_pagamento_boletos",
    "label": "Relação de parcelas (status de pagamento / boletos)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/relacao-de-parcelas/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/relacao-de-parcelas/",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página da área restrita para consulta de parcelas; associada a gestão de boletos/pagamento (inclui fluxo de boleto de endosso conforme notícia).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "cobrança",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/relacao-de-parcelas/; https://www.azulseguros.com.br/fique-por-dentro/como-fazer-a-gestao-financeira-do-pagamento-do-seguro/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__envio_de_documentos_online_sinistro_area_logada",
    "label": "Envio de documentos online (sinistro) - área logada",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/envio-de-documentos-online/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/envio-de-documentos-online/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Autosserviço de envio de documentos do sinistro; requer login.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/envio-de-documentos-online/; https://www.azulseguros.com.br/perguntas-frequentes/por-onde-eu-envio-os-documentos-pedidos-pela-analise-de-sinistro/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__envio_de_documentos_fisicos_codigo_de_postagem_a",
    "label": "Envio de documentos físicos (código de postagem) - área logada",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/envio-de-documentos-fisicos/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/envio-de-documentos-fisicos/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Autosserviço para geração de código de postagem e envio por correio; requer login e usa reCAPTCHA em fluxos relacionados.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/envio-de-documentos-fisicos/; https://www.azulseguros.com.br/fique-por-dentro/como-enviar-documentos-originais-pelo-correio-e-sem-custo/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__acompanhe_o_sinistro_autosservico_logado",
    "label": "Acompanhe o sinistro (autosserviço logado)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/segurado/acompanhe-o-sinistro/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/segurado/acompanhe-o-sinistro/",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Autosserviço de acompanhamento; a página pode retornar erro intermitente, mas mantém seção de contatos de sinistro/assistência.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "partial_evidence",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/segurado/acompanhe-o-sinistro/; https://www.azulseguros.com.br/perguntas-frequentes/como-posso-saber-a-situacao-atual-e-os-proximos-passos-do-meu-processo-de-sinistro/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__pague_facil_2_via_de_boleto_pagamento",
    "label": "Pague Fácil (2ª via de boleto / pagamento)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/pague-facil",
    "login_url": "https://www.azulseguros.com.br/pague-facil",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página pública de entrada do 'Pague Fácil' (citado como solução para boletos/pagamento; pode exigir login em etapas posteriores).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "cobrança",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.azulseguros.com.br/resolva-aqui/; https://www.azulseguros.com.br/fique-por-dentro/como-fazer-a-gestao-financeira-do-pagamento-do-seguro/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__sos_acionar_assistencia_24h_via_redirecionamento",
    "label": "SOS (acionar assistência 24h via redirecionamento)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/sos",
    "login_url": "https://api.whatsapp.com/send?phone=552139062985&text=&source=&data=",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Link de SOS na página 'Resolva Aqui' redireciona para chat externo (api.whatsapp.com) com número (21) 3906-2985.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "assistência",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/resolva-aqui/; https://www.azulseguros.com.br/perguntas-frequentes/a-azul-tem-um-canal-de-atendimento-no-whatsapp/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__rede_de_servicos_busca_por_cidade_cep_e_categori",
    "label": "Rede de Serviços (busca por cidade/CEP e categoria)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/rede-de-servicos/",
    "login_url": "https://www.azulseguros.com.br/rede-de-servicos/",
    "supported_journeys": [
      "assistance"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Ferramenta de consulta da rede; página inclui filtros e pode embutir reCAPTCHA na camada de login do site.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "assistência",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/rede-de-servicos/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__condicoes_gerais_hub_de_documentos",
    "label": "Condições Gerais (hub de documentos)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/condicoes-gerais/",
    "login_url": "https://www.azulseguros.com.br/condicoes-gerais/",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub para consulta de condições gerais e documentos de produtos.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "apólice/documentos",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/condicoes-gerais/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__resolva_aqui_hub_de_autosservicos_operacionais",
    "label": "Resolva Aqui (hub de autosserviços operacionais)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/resolva-aqui/",
    "login_url": "https://www.azulseguros.com.br/resolva-aqui/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página lista atalhos: Pague Fácil, SOS, sinistro, rede de serviços, documentação, etc.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/resolva-aqui/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__atendimento_via_chat_pagina_de_acesso",
    "label": "Atendimento via chat (página de acesso)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/fale-com-a-azul/chat/",
    "login_url": "https://www.azulseguros.com.br/fale-com-a-azul/chat/",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página oficial de atendimento via chat; pode exigir interação dinâmica.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/fale-com-a-azul/chat/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__portal_para_terceiros_conteudo_acesso_via_area_r",
    "label": "Portal para Terceiros (conteúdo + acesso via área restrita)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/fique-por-dentro/acesso-ao-portal-para-terceiros/",
    "login_url": "https://www.azulseguros.com.br/fique-por-dentro/acesso-ao-portal-para-terceiros/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Artigo descreve área exclusiva para terceiros (envio de documentos e acompanhamento).",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/fique-por-dentro/acesso-ao-portal-para-terceiros/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__portal_do_terceiro_cadastro_recuperacao_e_abertu",
    "label": "Portal do Terceiro (cadastro/recuperação e abertura de aviso)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/terceiro/cadastro/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/terceiro/cadastro/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": true,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": true
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página do terceiro exibe 'Abrir Aviso de Sinistro' e fluxos de recuperação; protegida por reCAPTCHA.",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/terceiro/cadastro/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__abertura_de_aviso_de_sinistro_para_terceiro_subd",
    "label": "Abertura de aviso de sinistro para terceiro (subdomínio area-restrita)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://area-restrita.azulseguros.com.br/novoAviso/novoAvisoTerceiro_java.cfm?terceirosite=1",
    "login_url": "https://area-restrita.azulseguros.com.br/novoAviso/novoAvisoTerceiro_java.cfm?terceirosite=1",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página específica para abertura de aviso (terceiro) sem depender do front-end principal do portal; solicita CPF/CNPJ e mostra contatos.",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://area-restrita.azulseguros.com.br/novoAviso/novoAvisoTerceiro_java.cfm?terceirosite=1",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__roteiro_operacional_prestadores_oficinas_pdf",
    "label": "Roteiro Operacional (Prestadores / oficinas) - PDF",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/wp-content/uploads/prestador/roteiro_operacional.pdf",
    "login_url": "https://www.azulseguros.com.br/wp-content/uploads/prestador/roteiro_operacional.pdf",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Documento operacional para prestadores/oficinas com instruções de regulação e canais (pode haver versões diferentes no site).",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "auto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/wp-content/uploads/prestador/roteiro_operacional.pdf",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__app_porto_android_usado_por_clientes_azul",
    "label": "App Porto (Android) usado por clientes Azul",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://play.google.com/store/apps/details?id=br.com.portoseguro.experienciacliente.mundoporto",
    "login_url": "https://play.google.com/store/apps/details?id=br.com.portoseguro.experienciacliente.mundoporto",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Azul indica que o aplicativo para clientes é o App Porto, com assistência, consulta de apólice, dados do corretor e status de pagamento.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "likely_persistent",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.azulseguros.com.br/perguntas-frequentes/a-azul-seguros-tem-aplicativo/; https://play.google.com/store/apps/details?id=br.com.portoseguro.experienciacliente.mundoporto",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__app_porto_ios_usado_por_clientes_azul",
    "label": "App Porto (iOS) usado por clientes Azul",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://apps.apple.com/us/app/porto-conta-digital-e-seguros/id1511026277",
    "login_url": "https://apps.apple.com/us/app/porto-conta-digital-e-seguros/id1511026277",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Listagem do App Porto na App Store; Azul aponta este app como app de clientes.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "likely_persistent",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://www.azulseguros.com.br/perguntas-frequentes/a-azul-seguros-tem-aplicativo/; https://apps.apple.com/us/app/porto-conta-digital-e-seguros/id1511026277",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__portal_chubb_seguros_pre_cadastro_onboarding_de_",
    "label": "Portal Chubb Seguros (pré-cadastro / onboarding de corretor)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.portalaceseguros.com.br/",
    "login_url": "https://www.portalaceseguros.com.br/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal se apresenta como porta de entrada/cadastro para corretores que ainda não trabalham com a Chubb.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.portalaceseguros.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__portal_chubb_seguros_corretor_ja_cadastrado_inst",
    "label": "Portal Chubb Seguros (corretor já cadastrado - instruções de acesso)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.portalaceseguros.com.br/preportal",
    "login_url": "https://www.portalaceseguros.com.br/preportal",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página orienta corretores cadastrados/ativos a completar cadastro no portal sem envio adicional de documentação.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.portalaceseguros.com.br/preportal",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__chubbnet_portal_do_corretor_pagina_descritiva",
    "label": "ChubbNet (portal do corretor) - página descritiva",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/business-partners/insurance-broker-applications.html",
    "login_url": "https://www.chubb.com/br-pt/business-partners/insurance-broker-applications.html",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página oficial descreve o ChubbNet e lista funcionalidades para corretores parceiros (cotações, comissões, histórico de apólices, 2ª via de documentos, regularizar parcelas etc).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/business-partners/insurance-broker-applications.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__chubbnet_sso_login",
    "label": "ChubbNet (SSO login)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://sso.chubbnet.com/",
    "login_url": "https://sso.chubbnet.com/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de login do portal ChubbNet com opções de idioma e telefones (inclui Brasil).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://sso.chubbnet.com/; https://www.chubb.com/br-pt/business-partners/insurance-broker-applications.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__ibroker_br_login_sso_oauth2",
    "label": "iBroker-BR (login SSO/OAuth2)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://brportal.chubb.com/iBroker-BR/login-logoff.action",
    "login_url": "https://brportal.chubb.com/iBroker-BR/login-logoff.action",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página de login com encaminhamento para domínio de autenticação (auth.chubb.com) via fluxo OAuth2/OpenID (indicado pelo redirect).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://brportal.chubb.com/iBroker-BR/login-logoff.action",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__parceiros_de_negocios_hub_de_portais_ferramentas",
    "label": "Parceiros de Negócios (hub de portais/ferramentas)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/business-partners.html",
    "login_url": "https://www.chubb.com/br-pt/business-partners.html",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub que referencia portais e recursos para parceiros (inclui ChubbNet e Worldview).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/business-partners.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__chubb_worldview_login_para_programas_multinacion",
    "label": "Chubb Worldview (login para programas multinacionais)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/business-partners/worldview.html",
    "login_url": "https://www.chubb.com/br-pt/business-partners/worldview.html",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal voltado a gerentes de risco e programas multinacionais; relevante para corretoras corporativas específicas.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "empresarial",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "no",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/business-partners/worldview.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__apolice_digital_consulta_baixar_por_codigo_de_ac",
    "label": "Apólice Digital (consulta/baixar por código de acesso)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://brportal.chubb.com/portal/apolicedigital.aspx/",
    "login_url": "https://brportal.chubb.com/portal/apolicedigital.aspx/",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página solicita 'código de acesso' (e, em alguns fluxos, CPF/CNPJ do titular) para baixar apólice digital.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "apólice/documentos",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://brportal.chubb.com/portal/apolicedigital.aspx/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__apolice_digital_envio_de_link_por_e_mail",
    "label": "Apólice Digital (envio de link por e-mail)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://brportal.chubb.com/portal/CorporateNotification.aspx",
    "login_url": "https://brportal.chubb.com/portal/CorporateNotification.aspx",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página permite solicitar envio por e-mail de arquivos relacionados à apólice digital.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "apólice/documentos",
      "url_kind": "deep_link",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://brportal.chubb.com/portal/CorporateNotification.aspx",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__epayment_boleto_endpoint_service",
    "label": "ePayment (boleto) - endpoint service",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://brportal.chubb.com/ePayment/ePaymentService341.aspx",
    "login_url": "https://brportal.chubb.com/ePayment/ePaymentService341.aspx?IDA4=",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de boleto (Itaú 341) aparenta ser gerada por parâmetros (ex.: IDA4). Útil para receber/validar boletos emitidos via portal/fluxos de cobrança.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "cobrança",
      "url_kind": "sessionized",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://brportal.chubb.com/ePayment/ePaymentService341.aspx?IDA4=",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__portal_de_sinistros_hub",
    "label": "Portal de Sinistros (hub)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/claims.html",
    "login_url": "https://www.chubb.com/br-pt/claims.html",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub de sinistros com links para aviso, centro de catástrofes e orientações.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/claims.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__aviso_de_sinistro_pagina_de_entrada_lista_por_pr",
    "label": "Aviso de Sinistro (página de entrada/lista por produto)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/claims/abra-um-sinistro.html",
    "login_url": "https://www.chubb.com/br-pt/claims/abra-um-sinistro.html",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de aviso de sinistro com seleção/canais por linhas (viagem, smartphone, residencial, empresarial, transportes etc).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/claims/abra-um-sinistro.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__sinistro_transportes_canais_e_requisitos",
    "label": "Sinistro Transportes (canais e requisitos)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/claims/transportes.html",
    "login_url": "https://www.chubb.com/br-pt/claims/transportes.html",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página lista canais para abertura de sinistro de transportes (nacional/internacional) e informações necessárias.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "transporte",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/claims/transportes.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__contato_brasil_ouvidoria_e_canais",
    "label": "Contato Brasil (ouvidoria e canais)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/contact/contact.html",
    "login_url": "https://www.chubb.com/br-pt/contact/contact.html",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de contato com ouvidoria e telefones (incluindo atendimento PCD).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/contact/contact.html",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_do_corretor_login",
    "label": "Portal do Corretor (login)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://corretor.sulamericaseguros.com.br/",
    "login_url": "https://corretor.sulamericaseguros.com.br/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal explícito para corretores; portal principal de entrada (login).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://corretor.sulamericaseguros.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_do_corretor_rota_legada_esqueci_minha_sen",
    "label": "Portal do Corretor (rota legada: esqueci minha senha / 'Portal do Corretor old')",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/main.jsp?lumPageId=8A488A8E19DF2F300119DF82ED626AF9",
    "login_url": "https://portal.sulamericaseguros.com.br/main.jsp?lumPageId=8A488A8E19DF2F300119DF82ED626AF9",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página legada de recuperação/solicitação de senha do 'Portal do Corretor old'. Útil para troubleshooting e onboarding de kit de cálculo (legado).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "legacy_route",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/main.jsp?lumPageId=8A488A8E19DF2F300119DF82ED626AF9",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_do_corretor_funcionalidades_cotacao_consu",
    "label": "Portal do Corretor (funcionalidades: cotação/consulta/comissões/documentos)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://corretor.sulamericaseguros.com.br/",
    "login_url": "https://portal.sulamericaseguros.com.br/institucional/noticias-sulamerica/melhorias-no-portal-do-corretor.htm",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Notícia corporativa descreve melhorias e capacidades no portal do corretor (ex.: obter PDFs de proposta/pedido de endosso para Auto, além de fluxos operacionais).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "deep_link",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/institucional/noticias-sulamerica/melhorias-no-portal-do-corretor.htm; https://corretor.sulamericaseguros.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_sulamerica_home_hub_de_servicos_e_conteud",
    "label": "Portal SulAmérica (home / hub de serviços e conteúdo)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/",
    "login_url": "https://portal.sulamericaseguros.com.br/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal institucional que agrega produtos, acessos rápidos, notícias e links para apps/atendimento.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__canais_de_atendimento_hub_filtravel_por_perfil_p",
    "label": "Canais de Atendimento (hub filtrável por perfil/produto)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/canais-de-atendimento",
    "login_url": "https://portal.sulamericaseguros.com.br/canais-de-atendimento",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página central de atendimento; inclui indicação de chat (segurado saúde/odonto) e outros canais por perfil/produto.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/canais-de-atendimento",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__ouvidoria_formulario_e_canais",
    "label": "Ouvidoria (formulário e canais)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/ouvidoria",
    "login_url": "https://portal.sulamericaseguros.com.br/ouvidoria",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Canal de ouvidoria com possibilidade de encaminhar reclamação via formulário.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/ouvidoria",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__pagamentos_hub_validacao_de_boleto",
    "label": "Pagamentos (hub + validação de boleto)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/pagamentos",
    "login_url": "https://portal.sulamericaseguros.com.br/pagamentos",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página agrega acessos de pagamentos (Saúde/Vida/Previdência/Odonto) e verificação de autenticidade de boleto.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "cobrança",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/pagamentos",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__espaco_do_cliente_auto_residencial_condominio_em",
    "label": "Espaço do Cliente Auto/Residencial/Condomínio/Empresarial (login por CPF/CNPJ)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/main.jsp?lumPageId=402881823D9DF8EE013D9E0F894208B0",
    "login_url": "https://portal.sulamericaseguros.com.br/main.jsp?lumPageId=402881823D9DF8EE013D9E0F894208B0",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Login do Espaço do Cliente para linhas patrimoniais/auto; inclui recuperação de senha.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/main.jsp?lumPageId=402881823D9DF8EE013D9E0F894208B0",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__tutorial_do_espaco_do_cliente_mapa_de_jornadas_a",
    "label": "Tutorial do Espaço do Cliente (mapa de jornadas: apólice PDF, 2ª via, sinistro, oficinas, vistoria, etc.)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://www.sulamerica.com.br/espacodocliente/tutorial/",
    "login_url": "https://www.sulamerica.com.br/espacodocliente/tutorial/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Material oficial descrevendo jornadas disponíveis no Espaço do Cliente (kit do segurado, histórico de pagamento, 2ª via, aviso/acompanhamento de sinistro, oficinas e postos de vistoria) e menciona app Auto.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.sulamerica.com.br/espacodocliente/tutorial/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__aplicativos_sulamerica_hub_saude_e_odonto",
    "label": "Aplicativos SulAmérica (hub: Saúde e Odonto)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/aplicativos/",
    "login_url": "https://portal.sulamericaseguros.com.br/aplicativos/",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Hub oficial de apps (foco em Saúde e Odonto).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/aplicativos/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__app_sulamerica_saude_android",
    "label": "App SulAmérica Saúde (Android)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://play.google.com/store/apps/details?id=br.com.sulamerica.sam.saude",
    "login_url": "https://play.google.com/store/apps/details?id=br.com.sulamerica.sam.saude",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App oficial do seguro saúde; inclui funções como 2ª via de boleto, carteirinha digital e reembolso/teleatendimento (conforme descrição da loja).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "likely_persistent",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?id=br.com.sulamerica.sam.saude; https://portal.sulamericaseguros.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__app_sulamerica_saude_ios",
    "label": "App SulAmérica Saúde (iOS)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://apps.apple.com/br/app/sulam%C3%A9rica-sa%C3%BAde/id492556516",
    "login_url": "https://apps.apple.com/br/app/sulam%C3%A9rica-sa%C3%BAde/id492556516",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Listagem oficial na App Store do app SulAmérica Saúde.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "likely_persistent",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/sulam%C3%A9rica-sa%C3%BAde/id492556516",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__app_sulamerica_odonto_android",
    "label": "App SulAmérica Odonto (Android)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://play.google.com/store/apps/details?id=br.com.sulamerica.odonto",
    "login_url": "https://play.google.com/store/apps/details?id=br.com.sulamerica.odonto",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App oficial Odonto (Android).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "likely_persistent",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://play.google.com/store/apps/details?id=br.com.sulamerica.odonto",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__app_sulamerica_odonto_ios",
    "label": "App SulAmérica Odonto (iOS)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://apps.apple.com/br/app/sulam%C3%A9rica-odonto/id1044444954",
    "login_url": "https://apps.apple.com/br/app/sulam%C3%A9rica-odonto/id1044444954",
    "supported_journeys": [
      "mobile_app"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "App oficial Odonto (iOS).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "mobile_app",
      "url_kind": "canonical",
      "session_profile": "likely_persistent",
      "integration_type": "app_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://apps.apple.com/br/app/sulam%C3%A9rica-odonto/id1044444954",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__saude_online_hub_de_acesso_segurado_empresa_refe",
    "label": "Saúde Online (hub de acesso Segurado/Empresa/Referenciado)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/main.jsp?lumChannelId=8A619BA64ED07F8C014ED19C6E2C6463",
    "login_url": "https://portal.sulamericaseguros.com.br/main.jsp?lumChannelId=8A619BA64ED07F8C014ED19C6E2C6463",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de entrada do Saúde Online com links para perfis de acesso.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/main.jsp?lumChannelId=8A619BA64ED07F8C014ED19C6E2C6463",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__saude_online_segurado_login_cadastro_de_senha",
    "label": "Saúde Online Segurado (login + cadastro de senha)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://saude.sulamericaseguros.com.br/segurado/login/",
    "login_url": "https://saude.sulamericaseguros.com.br/segurado/login/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "A própria página de cadastro de senha informa que a mesma senha dá acesso ao Saúde Online Segurado, Portal do Reembolso e app Saúde.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "mixed",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://saude.sulamericaseguros.com.br/segurado/login/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__saude_online_empresa_login",
    "label": "Saúde Online Empresa (login)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://saude.sulamericaseguros.com.br/empresa/login/",
    "login_url": "https://saude.sulamericaseguros.com.br/empresa/login/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Login de empresa; exibe atalhos como 2ª via do boleto, além de links informativos.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://saude.sulamericaseguros.com.br/empresa/login/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_do_reembolso_saude_login",
    "label": "Portal do Reembolso Saúde (login)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://saude.sulamericaseguros.com.br/reembolsosaude/login/",
    "login_url": "https://saude.sulamericaseguros.com.br/reembolsosaude/login/",
    "supported_journeys": [
      "policy_query"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal web dedicado ao reembolso (saúde). A senha do segurado Saúde dá acesso a este portal (conforme comunicação no login do segurado Saúde).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "apólice/documentos",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "strong_evidence",
      "official_sources": "https://saude.sulamericaseguros.com.br/reembolsosaude/login/; https://saude.sulamericaseguros.com.br/segurado/login/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_odonto_segurado_login_por_cpf_carteirinha",
    "label": "Portal Odonto Segurado (login por CPF/carteirinha)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/odonto/login/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/odonto/login/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Login do Odonto no portal (seleção de carteirinha).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/odonto/login/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__avisar_um_sinistro_auto_web_para_empresa",
    "label": "Avisar um sinistro Auto (web) - Para Empresa",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-empresa/auto/servicos-online/avisar-um-sinistro/avise-seu-sinistro-pela-internet.htm",
    "login_url": "https://portal.sulamericaseguros.com.br/para-empresa/auto/servicos-online/avisar-um-sinistro/avise-seu-sinistro-pela-internet.htm",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Abertura de aviso de sinistro online (auto) com formulário e instruções.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-empresa/auto/servicos-online/avisar-um-sinistro/avise-seu-sinistro-pela-internet.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__aviso_de_sinistro_de_vidros_lanternas_retrovisor",
    "label": "Aviso de sinistro de vidros/lanternas/retrovisores (Auto)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/aviso-de-sinistro-vidros-lanternas-e-retrovisores/aviso-de-sinistro-vidros-lanternas-e-retrovisores.htm",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/aviso-de-sinistro-vidros-lanternas-e-retrovisores/aviso-de-sinistro-vidros-lanternas-e-retrovisores.htm",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de serviço online (auto) com navegação para várias jornadas (2ª via, oficinas, vistoria, etc).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/aviso-de-sinistro-vidros-lanternas-e-retrovisores/aviso-de-sinistro-vidros-lanternas-e-retrovisores.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__2_via_do_boleto_auto_individual_servicos_online",
    "label": "2ª via do boleto (Auto - individual) - serviços online",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/2a-via-do-boleto-individual/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/2a-via-do-boleto-individual/",
    "supported_journeys": [
      "document_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "URL canônica existe, porém o acesso pode redirecionar para tela com 'accessError' (indício de necessidade de sessão/login).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "segunda_via",
      "url_kind": "canonical",
      "session_profile": "likely_high_friction",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "partial_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/2a-via-do-boleto-individual/; https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/aviso-de-sinistro-vidros-lanternas-e-retrovisores/aviso-de-sinistro-vidros-lanternas-e-retrovisores.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__boleto_em_atraso_auto_individual_servicos_online",
    "label": "Boleto em atraso (Auto - individual) - serviços online",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/boleto-em-atraso-individual/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/boleto-em-atraso-individual/",
    "supported_journeys": [
      "billing_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota canônica identificada no menu de serviços; acesso observado com redirecionamento para 'accessError'.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "cobrança",
      "url_kind": "canonical",
      "session_profile": "likely_high_friction",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "partial_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/boleto-em-atraso-individual/; https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/aviso-de-sinistro-vidros-lanternas-e-retrovisores/aviso-de-sinistro-vidros-lanternas-e-retrovisores.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__acompanhamento_de_devolucoes_de_credito_auto_ser",
    "label": "Acompanhamento de devoluções de crédito (Auto) - serviços online",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/acompanhamento-de-devolucoes-de-credito/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/acompanhamento-de-devolucoes-de-credito/",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota de acompanhamento de devolução de crédito; pode requerer sessão.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "canonical",
      "session_profile": "likely_high_friction",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "yes",
      "confidence": "partial_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/acompanhamento-de-devolucoes-de-credito/; https://www.sulamerica.com.br/espacodocliente/tutorial/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__informacoes_para_credito_em_conta_corrente_auto_",
    "label": "Informações para crédito em conta corrente (Auto) - serviços online",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/informacoes-para-credito-em-conta-corrente/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/informacoes-para-credito-em-conta-corrente/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota do menu de serviços online; possivelmente depende de contexto cadastral.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "likely_high_friction",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "yes",
      "confidence": "partial_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/informacoes-para-credito-em-conta-corrente/; https://www.sulamerica.com.br/espacodocliente/tutorial/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__postos_de_vistoria_auto_consulta",
    "label": "Postos de vistoria (Auto) - consulta",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/seguro-auto/postos-de-vistoria/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/seguro-auto/postos-de-vistoria/",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota de consulta de postos de vistoria; observada no menu do seguro Auto (pode redirecionar para 'accessError').",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "canonical",
      "session_profile": "likely_high_friction",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "partial_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/seguro-auto/postos-de-vistoria/; https://www.sulamerica.com.br/espacodocliente/tutorial/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__acompanhamento_de_sinistro_segurado_rota_santand",
    "label": "Acompanhamento de Sinistro (segurado) - rota 'santander'",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-para-segurado.htm",
    "login_url": "https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-para-segurado.htm",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página pública de acompanhamento (entrada por CPF/CNPJ) com rota 'santander' (indica uso também por canal específico/parceiro).",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-para-segurado.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__aviso_de_sinistro_vida_acionamento_com_envio_de_",
    "label": "Aviso de Sinistro Vida (acionamento com envio de documentos)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/acionamento-segurodevida/",
    "login_url": "https://portal.sulamericaseguros.com.br/acionamento-segurodevida/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de aviso/acionamento de sinistro com necessidade de envio de imagens de documentos e formulários.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "vida",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/acionamento-segurodevida/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__servicos_online_vida_formulario_de_aviso_de_sini",
    "label": "Serviços Online Vida (formulário de aviso de sinistro / solicite cálculo)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/vida/servicos-online/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/vida/servicos-online/",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página de serviços online de Vida inclui campos de Aviso de Sinistro (form web) e outros serviços.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "vida",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/vida/servicos-online/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__acompanhamento_de_sinistro_terceiro_rota_santand",
    "label": "Acompanhamento de Sinistro (terceiro) - rota 'santander'",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-de-terceiros.htm",
    "login_url": "https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-de-terceiros.htm",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página pública de acompanhamento para terceiros (entrada por CPF/CNPJ).",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-de-terceiros.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__acompanhamento_de_sinistro_de_terceiros_auto_ser",
    "label": "Acompanhamento de sinistro de terceiros (Auto) - serviços online",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/acompanhamento-de-sinistro-de-terceiros/",
    "login_url": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/acompanhamento-de-sinistro-de-terceiros/",
    "supported_journeys": [
      "status_query"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Rota equivalente dentro do menu de serviços online; acesso observado com redirecionamento para 'accessError'. Existe também rota pública alternativa em /santander/.",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "auto",
      "journey_type": "status",
      "url_kind": "canonical",
      "session_profile": "likely_high_friction",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "partial_evidence",
      "official_sources": "https://portal.sulamericaseguros.com.br/para-voce/auto/servicos-online/acompanhamento-de-sinistro-de-terceiros/; https://portal.sulamericaseguros.com.br/santander/acompanhamento-de-sinistro-de-terceiros.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__fale_conosco_sobre_sinistro_segurado_ou_terceiro",
    "label": "Fale Conosco sobre Sinistro (segurado ou terceiro)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/santander/fale-conosco-sobre-sinistro.htm",
    "login_url": "https://portal.sulamericaseguros.com.br/santander/fale-conosco-sobre-sinistro.htm",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Formulário seleciona perfil (Segurado/Terceiro) e solicita CPF/CNPJ.",
    "metadata": {
      "audience": "terceiro",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/santander/fale-conosco-sobre-sinistro.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_referenciado_saude_prestador_login",
    "label": "Portal Referenciado Saúde (prestador) - login",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://saude.sulamericaseguros.com.br/prestador/login/login.htm",
    "login_url": "https://saude.sulamericaseguros.com.br/prestador/login/login.htm",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Login de prestadores/referenciados da rede (saúde).",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://saude.sulamericaseguros.com.br/prestador/login/login.htm",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_prestador_odonto_sad_net_acesso_logado",
    "label": "Portal Prestador Odonto (Sad.Net) - acesso logado",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://prestadorodontop.sulamerica.com.br/SadNet/SadAcesso.aspx",
    "login_url": "https://prestadorodontop.sulamerica.com.br/SadNet/SadAcesso.aspx",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Portal de conectividade para dentistas/clínicas (prestadores ativos) com código + senha; usado para fluxos de guias/autorizações e rotina de faturamento (conforme páginas e manual).",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://prestadorodontop.sulamerica.com.br/SadNet/SadAcesso.aspx; https://odonto.sulamerica.com.br/assets/manual_resumido_de_atendimento_sulamerica_odonto_04052020.pdf",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__prestador_odonto_pwa_paas_login",
    "label": "Prestador Odonto PWA (paas) - login",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://prestador-odonto-pwa.paas.sulamerica.com.br/",
    "login_url": "https://prestador-odonto-pwa.paas.sulamerica.com.br/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "PWA de prestador odonto (código do prestador + senha). Pode coexistir com Sad.Net.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "saúde",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://prestador-odonto-pwa.paas.sulamerica.com.br/",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__portal_prestadores_auto_oficinas_manual_pdf_evid",
    "label": "Portal Prestadores Auto (oficinas) - manual PDF (evidência pública de portal)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://portal.sulamericaseguros.com.br/lumis/portal/file/fileDownload.jsp?fileId=FF80808129DD41450129DD961A95466C",
    "login_url": "https://portal.sulamericaseguros.com.br/lumis/portal/file/fileDownload.jsp?fileId=FF80808129DD41450129DD961A95466C",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Manual (2010) descreve portal de prestadores/oficinas integrado ao ClaimCenter (Guidewire), com funções de acompanhamento de reparos e faturamento. Pode ser legado.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "auto",
      "journey_type": "other",
      "url_kind": "legacy_route",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "no",
      "confidence": "confirmed",
      "official_sources": "https://portal.sulamericaseguros.com.br/lumis/portal/file/fileDownload.jsp?fileId=FF80808129DD41450129DD961A95466C",
      "checked_at": "2026-04-07",
      "registry_block": "operational",
      "source_document": "PORTAL REGISTRY 3.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__portal_da_pessoa_desenvolvedora_catalogo_de_apis",
    "label": "Portal da Pessoa Desenvolvedora (catálogo de APIs)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://dev.portoseguro.com.br/api-portal/node/1",
    "login_url": "https://dev.portoseguro.com.br/api-portal/node/1",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal de desenvolvedores indica acesso ao catálogo de APIs; cadastro aceito apenas para parceiros com acordo estabelecido.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://dev.portoseguro.com.br/api-portal/node/1",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__documentacao_de_autorizacao_e_token_oauth_2_0",
    "label": "Documentação de autorização e token (OAuth 2.0)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://dev.portoseguro.com.br/api-portal/content/autorizacao",
    "login_url": "https://dev.portoseguro.com.br/api-portal/content/autorizacao",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página descreve concessão de token OAuth 2.0 e necessidade de Client ID/Client Secret obtidos via criação de APP no portal.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://dev.portoseguro.com.br/api-portal/content/autorizacao",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__introducao_e_ambiente_de_sandbox_orientacoes",
    "label": "Introdução e ambiente de Sandbox (orientações)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://dev.portoseguro.com.br/api-portal/content/introducao",
    "login_url": "https://dev.portoseguro.com.br/api-portal/content/introducao",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Texto menciona testes em sandbox com dados mock; consumo exige token e APP cadastrada/aprovada pela companhia.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://dev.portoseguro.com.br/api-portal/content/introducao",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "porto__faq_e_base_de_suporte_do_portal_de_apis_zendesk",
    "label": "FAQ e base de suporte do portal de APIs (Zendesk)",
    "owner_kind": "insurer",
    "owner_key": "porto",
    "base_url": "https://devportoseg.zendesk.com/hc/pt-br/categories/24577718731149-D%C3%BAvidas-Frequentes-APIs-Porto-Seguro",
    "login_url": "https://devportoseg.zendesk.com/hc/pt-br/categories/24577718731149-D%C3%BAvidas-Frequentes-APIs-Porto-Seguro",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Base de ajuda específica para APIs Porto Seguro.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://devportoseg.zendesk.com/hc/pt-br/categories/24577718731149-D%C3%BAvidas-Frequentes-APIs-Porto-Seguro",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "zurich__portal_de_desenvolvedores_zurich_developers",
    "label": "Portal de Desenvolvedores (Zurich Developers)",
    "owner_kind": "insurer",
    "owner_key": "zurich",
    "base_url": "https://api-portal.zurich.com.br/api-portal/en",
    "login_url": "https://api-portal.zurich.com.br/api-portal/en",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal informa que acesso é solicitado via ponto de contato na companhia; documentação funcional e técnica fica disponível após autenticação.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://api-portal.zurich.com.br/api-portal/en",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "zurich__api_guide_e_autenticacao_tokens_client_id",
    "label": "API Guide e autenticação (tokens, client_id)",
    "owner_kind": "insurer",
    "owner_key": "zurich",
    "base_url": "https://api-portal.zurich.com.br/api-portal/content/api-guide",
    "login_url": "https://api-portal.zurich.com.br/api-portal/content/api-guide",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Documentação descreve autenticação via tokens em header; client_id é gerado na criação de uma APP no portal do desenvolvedor.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://api-portal.zurich.com.br/api-portal/content/api-guide",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "zurich__documentacao_oauth_2_conceitos_e_fluxo",
    "label": "Documentação OAuth 2 (conceitos e fluxo)",
    "owner_kind": "insurer",
    "owner_key": "zurich",
    "base_url": "https://api-portal.zurich.com.br/api-portal/content/oauth-2",
    "login_url": "https://api-portal.zurich.com.br/api-portal/content/oauth-2",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página resume OAuth 2 como padrão de autenticação para acesso a recursos por terceiros.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://api-portal.zurich.com.br/api-portal/content/oauth-2",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__hdi_developers_portal_de_parcerias_e_apis",
    "label": "HDI Developers (portal de parcerias e APIs)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://developers.hdi.com.br/page/home",
    "login_url": "https://developers.hdi.com.br/page/home",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal menciona solicitação de acesso e biblioteca de APIs para projetos de parceiros.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.hdi.com.br/page/home",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__fluxo_de_autenticacao_autorizacao_gerar_renovar_",
    "label": "Fluxo de autenticação (autorização, gerar/renovar token)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://developers.hdi.com.br/reference/nossas-apis",
    "login_url": "https://developers.hdi.com.br/reference/nossas-apis",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Documentação descreve fluxo de autorização e geração/renovação de token para uso das APIs.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.hdi.com.br/reference/nossas-apis",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__api_de_gerar_token_endpoint_e_swagger_postman",
    "label": "API de Gerar Token (endpoint e Swagger/Postman)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://developers.hdi.com.br/reference/autenticacao-post-token",
    "login_url": "https://developers.hdi.com.br/reference/autenticacao-post-token",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página expõe endpoint de token em openapi-int.hdi.com.br e openapi.hdi.com.br e disponibiliza Swagger e Postman.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.hdi.com.br/reference/autenticacao-post-token",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "hdi__apis_auto_cotacao_recalculo_efetivacao_e_dominio",
    "label": "APIs Auto (cotação, recálculo, efetivação e domínios)",
    "owner_kind": "insurer",
    "owner_key": "hdi",
    "base_url": "https://developers.hdi.com.br/reference/nossas-apis-auto",
    "login_url": "https://developers.hdi.com.br/reference/nossas-apis-auto",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Visão geral lista APIs principais (cotação/recálculo/efetivação) e APIs de apoio (portfólio, coberturas, questionário).",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "auto",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.hdi.com.br/reference/nossas-apis-auto",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__tokio_marine_api_portal_sensedia",
    "label": "Tokio Marine API Portal (Sensedia)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://portal-tokiomarine.sensedia.com/api-portal/pt-br/node/1",
    "login_url": "https://portal-tokiomarine.sensedia.com/api-portal/pt-br/node/1",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal descreve criação de conta e acesso à documentação, fluxo de autenticação, SDKs e API Browser.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://portal-tokiomarine.sensedia.com/api-portal/pt-br/node/1",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__documentacao_e_guias_api_docs_autenticacao_codig",
    "label": "Documentação e guias (API Docs/Autenticação/Códigos de Erro)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://portal-tokiomarine.sensedia.com/api-portal/pt-br/documentation",
    "login_url": "https://portal-tokiomarine.sensedia.com/api-portal/pt-br/documentation",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página de documentação lista seções de FAQ, autenticação e códigos de erro para APIs.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "strong_evidence",
      "official_sources": "https://portal-tokiomarine.sensedia.com/api-portal/pt-br/documentation",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__portal_de_integracoes_api_landing",
    "label": "Portal de Integrações & API (landing)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://integracao.tokiomarine.com.br/",
    "login_url": "https://integracao.tokiomarine.com.br/",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Landing do portal de integrações & API (conteúdo pode ser carregado via JS; validar em navegação real).",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "partial_evidence",
      "official_sources": "https://integracao.tokiomarine.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "tokio_marine__swagger_ui_api_integracao_ambiente",
    "label": "Swagger UI (API Integração - ambiente)",
    "owner_kind": "insurer",
    "owner_key": "tokio_marine",
    "base_url": "https://aceitetma-api-integracao.tokiomarine.com.br/",
    "login_url": "https://aceitetma-api-integracao.tokiomarine.com.br/",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Swagger UI expõe documentação interativa; conteúdo aponta endpoints de apólices/endossos (detalhar requer navegação).",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "partial_evidence",
      "official_sources": "https://aceitetma-api-integracao.tokiomarine.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__sulamerica_developers_sensedia_portal",
    "label": "SulAmérica Developers (Sensedia) - portal",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://devsulamerica.sensedia.com/api-portal/node/1",
    "login_url": "https://devsulamerica.sensedia.com/api-portal/node/1",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal de APIs da SulAmérica hospedado em Sensedia; exige login Sensedia.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://devsulamerica.sensedia.com/api-portal/node/1",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__primeiros_passos_autenticacao_por_app_client_id_",
    "label": "Primeiros passos: autenticação por APP (client_id/client_secret) e access token",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://devsulamerica.sensedia.com/api-portal/node/2?language=pt-br",
    "login_url": "https://devsulamerica.sensedia.com/api-portal/node/2?language=pt-br",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Documentação explica geração de token via app registrada com client_id e client_secret.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://devsulamerica.sensedia.com/api-portal/node/2?language=pt-br",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sulamerica__documentacao_geral_faq_autenticacao_codigos_de_e",
    "label": "Documentação geral (FAQ, autenticação, códigos de erro, exemplos, SDKs)",
    "owner_kind": "insurer",
    "owner_key": "sulamerica",
    "base_url": "https://devsulamerica.sensedia.com/api-portal/content/documentation?language=en",
    "login_url": "https://devsulamerica.sensedia.com/api-portal/content/documentation?language=en",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página de documentação apresenta seções de autenticação, códigos de erro, exemplos e download de SDKs.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "strong_evidence",
      "official_sources": "https://devsulamerica.sensedia.com/api-portal/content/documentation?language=en",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "bradesco__portal_de_desenvolvedores_api_developer_portal",
    "label": "Portal de Desenvolvedores / API Developer Portal",
    "owner_kind": "insurer",
    "owner_key": "bradesco",
    "base_url": "https://apiportal.bradescoseguros.com.br/",
    "login_url": "https://apiportal.bradescoseguros.com.br/",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal descreve catálogo de APIs, documentação REST; menciona segurança com OAuth e mecanismos como certificados (SSL/mTLS) e tokens JWT; uso das APIs requer parceria e liberação.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://apiportal.bradescoseguros.com.br/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "bradesco__pagina_institucional_portal_apis_bradesco_seguro",
    "label": "Página institucional: Portal APIs Bradesco Seguros (sobre)",
    "owner_kind": "insurer",
    "owner_key": "bradesco",
    "base_url": "https://www.bradescoseguros.com.br/clientes/portal-apis",
    "login_url": "https://www.bradescoseguros.com.br/clientes/portal-apis",
    "supported_journeys": [
      "support"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página pública descreve objetivo do portal para parcerias com clientes/parceiros/desenvolvedores e navegação por jornadas.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "suporte",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.bradescoseguros.com.br/clientes/portal-apis",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "bradesco__seguro_empresarial_catalogo_de_apis_cotacao_efet",
    "label": "Seguro Empresarial: catálogo de APIs (cotação, efetivação, pagamento, consulta, endosso) + Swagger",
    "owner_kind": "insurer",
    "owner_key": "bradesco",
    "base_url": "https://apiportal.bradescoseguros.com.br/pages/Portal_UI_Bundle/empresarial.html",
    "login_url": "https://apiportal.bradescoseguros.com.br/pages/Portal_UI_Bundle/empresarial.html",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página lista APIs por jornada e indica navegação por 'Saiba mais' para cada API; portal fornece Swagger/contratos.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "empresarial",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://apiportal.bradescoseguros.com.br/pages/Portal_UI_Bundle/empresarial.html",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "bradesco__seguro_empresarial_swagger_full_todas_as_apis_e_",
    "label": "Seguro Empresarial: Swagger Full (todas as APIs) e coleções de teste",
    "owner_kind": "insurer",
    "owner_key": "bradesco",
    "base_url": "https://www.bradescoseguros.com.br/portalapis/Portal/api/empresarial/apiscompletas.html",
    "login_url": "https://www.bradescoseguros.com.br/portalapis/Portal/api/empresarial/apiscompletas.html",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página oferece 'Download Swagger' e recursos como onboarding/credenciais/certificados/coleções para testes.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "empresarial",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "strong_evidence",
      "official_sources": "https://www.bradescoseguros.com.br/portalapis/Portal/api/empresarial/apiscompletas.html",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sompo__sompo_developers_portal_portal_de_apis_e_sandbox",
    "label": "Sompo Developers Portal (portal de APIs e sandbox)",
    "owner_kind": "insurer",
    "owner_key": "sompo",
    "base_url": "https://developers.sompo.com.br/api-portal/node/1",
    "login_url": "https://developers.sompo.com.br/api-portal/node/1",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal descreve cadastro gratuito, catálogo de APIs e ambiente de sandbox para testes.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.sompo.com.br/api-portal/node/1",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sompo__introducao_nossas_apis_swagger_sandbox",
    "label": "Introdução: Nossas APIs (swagger + sandbox)",
    "owner_kind": "insurer",
    "owner_key": "sompo",
    "base_url": "https://developers.sompo.com.br/api-portal/content/nossas-apis-0",
    "login_url": "https://developers.sompo.com.br/api-portal/content/nossas-apis-0",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página informa que portal permite conexão em sandbox e documentação via swagger.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.sompo.com.br/api-portal/content/nossas-apis-0",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sompo__autenticacao_na_plataforma_access_token_bearer",
    "label": "Autenticação na plataforma (Access-Token + Bearer)",
    "owner_kind": "insurer",
    "owner_key": "sompo",
    "base_url": "https://developers.sompo.com.br/api-portal/content/autentica%C3%A7%C3%A3o",
    "login_url": "https://developers.sompo.com.br/api-portal/content/autentica%C3%A7%C3%A3o",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Guia descreve chamada HTTPS/POST para obter access-token e uso de Bearer Authentication para consumir APIs.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.sompo.com.br/api-portal/content/autentica%C3%A7%C3%A3o",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sompo__api_do_corretor_index_swagger",
    "label": "API do Corretor (index + swagger)",
    "owner_kind": "insurer",
    "owner_key": "sompo",
    "base_url": "https://developers.sompo.com.br/api-portal/broker",
    "login_url": "https://developers.sompo.com.br/api-portal/broker",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página lista operações (login corretor, consulta de perfil, redefinir senha) com acesso via swagger.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://developers.sompo.com.br/api-portal/broker",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sompo__api_de_sinistro_claims_orientacoes_iniciais",
    "label": "API de Sinistro (claims) - orientações iniciais",
    "owner_kind": "insurer",
    "owner_key": "sompo",
    "base_url": "https://developers.sompo.com.br/api-portal/claims",
    "login_url": "https://developers.sompo.com.br/api-portal/claims",
    "supported_journeys": [
      "claim"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Página menciona autenticação na plataforma e obtenção de access-token antes de consumir APIs de sinistro.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "sinistro",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "strong_evidence",
      "official_sources": "https://developers.sompo.com.br/api-portal/claims",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "allianz__allianz_hotsite_vida_individual_guia_de_implemen",
    "label": "Allianz HotSite Vida Individual (guia de implementação para integração de corretor)",
    "owner_kind": "insurer",
    "owner_key": "allianz",
    "base_url": "https://www.allianz.com.br/content/dam/onemarketing/iberolatam/allianz-br/p%C3%A1gina-documentos/GuiaDeImplementa%C3%A7%C3%A3o_V2.pdf",
    "login_url": "https://www.allianz.com.br/content/dam/onemarketing/iberolatam/allianz-br/p%C3%A1gina-documentos/GuiaDeImplementa%C3%A7%C3%A3o_V2.pdf",
    "supported_journeys": [
      "quote"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Documento descreve concessão de link de acesso para canal HotSite via chamadas servidor-a-servidor; usa BasicAuthentication + HTTPS e grant_type=client_credentials; inclui exemplos com base URI em apis.allianz.com (UAT).",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "vida",
      "journey_type": "cotação",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.allianz.com.br/content/dam/onemarketing/iberolatam/allianz-br/p%C3%A1gina-documentos/GuiaDeImplementa%C3%A7%C3%A3o_V2.pdf",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "mapfre__open_insurance_mapfre_informativo_institucional",
    "label": "Open Insurance MAPFRE (informativo institucional)",
    "owner_kind": "insurer",
    "owner_key": "mapfre",
    "base_url": "https://www.mapfre.com.br/quem-somos/mapfre/open-insurance-mapfre/",
    "login_url": "https://www.mapfre.com.br/quem-somos/mapfre/open-insurance-mapfre/",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página explica conceito de Open Insurance e aponta que compartilhamento de dados ocorre via consentimento; não é um catálogo técnico de APIs.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "unknown",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.mapfre.com.br/quem-somos/mapfre/open-insurance-mapfre/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "azul__area_restrita_multi_perfil_corretor_cliente_terc",
    "label": "Área Restrita (multi-perfil: corretor/cliente/terceiro etc.)",
    "owner_kind": "insurer",
    "owner_key": "azul",
    "base_url": "https://www.azulseguros.com.br/area-restrita/",
    "login_url": "https://www.azulseguros.com.br/area-restrita/",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Área restrita apresenta seleção de perfil e login; não há evidência pública de portal dev/API nesta coleta.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "auto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "no",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.azulseguros.com.br/area-restrita/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__mrservices_soap_web_services_multi_risco",
    "label": "MRServices SOAP (Web Services Multi-Risco)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/servicos/ws/MRServices.asmx",
    "login_url": "https://wwws.alfaseguradora.com.br/servicos/ws/MRServices.asmx",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Endpoint expõe WSDL/serviços SOAP para operações Multi-Risco; página menciona necessidade de cadastramento junto à seguradora para liberação.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/servicos/ws/MRServices.asmx",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "alfa__mrservices_soap_enviararquivomr2_upload_de_arqui",
    "label": "MRServices SOAP: EnviarArquivoMR2 (upload de arquivo de propostas MR)",
    "owner_kind": "insurer",
    "owner_key": "alfa",
    "base_url": "https://wwws.alfaseguradora.com.br/servicos/ws/MRServices.asmx?op=EnviarArquivoMR2",
    "login_url": "https://wwws.alfaseguradora.com.br/servicos/ws/MRServices.asmx?op=EnviarArquivoMR2",
    "supported_journeys": [
      "issue"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página do método indica envio de arquivo TXT (limite 3MB) e descreve chamada SOAP; formulário de teste disponível apenas localmente (padrão IIS).",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "emissão",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://wwws.alfaseguradora.com.br/servicos/ws/MRServices.asmx?op=EnviarArquivoMR2",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__chubb_studio_pagina_de_parceria_e_tecnologia",
    "label": "Chubb Studio (página de parceria e tecnologia)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://www.chubb.com/br-pt/partnership/technology.html",
    "login_url": "https://www.chubb.com/br-pt/partnership/technology.html",
    "supported_journeys": [
      "other"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página descreve Chubb Studio e menciona configuração de API para parceiros de distribuição; não é documentação técnica completa.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "other",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.chubb.com/br-pt/partnership/technology.html",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "chubb__api_connect_chubb_studio_portal_catalogo_e_teste",
    "label": "API Connect / Chubb Studio portal (catálogo e testes)",
    "owner_kind": "insurer",
    "owner_key": "chubb",
    "base_url": "https://apistudio.chubb.com/",
    "login_url": "https://apistudio.chubb.com/",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal indica criação de conta e possibilidade de encontrar/testar APIs; escopo pode ser global (validar oferta específica Brasil em onboarding).",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "strong_evidence",
      "official_sources": "https://apistudio.chubb.com/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "yelum__guia_de_integracao_de_apis_parcerias_pdf_massifi",
    "label": "Guia de Integração de APIs Parcerias (PDF - Massificado)",
    "owner_kind": "insurer",
    "owner_key": "yelum",
    "base_url": "https://www.yelumseguros.com.br/Shared%20Documents/Documentacao-Tecnica/Integracao-YELUM-MASSIFICADO.pdf",
    "login_url": "https://www.yelumseguros.com.br/Shared%20Documents/Documentacao-Tecnica/Integracao-YELUM-MASSIFICADO.pdf",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Guia (PDF) descreve necessidade de chaves, autenticação e token; menciona validação de autenticação LDAP e autorização no controle de acesso; links internos para portal do desenvolvedor e coleções Postman não aparecem na extração textual.",
    "metadata": {
      "audience": "parceiro",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.yelumseguros.com.br/Shared%20Documents/Documentacao-Tecnica/Integracao-YELUM-MASSIFICADO.pdf",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "yelum__faq_auto_pdf_token_de_autenticacao_client_creden",
    "label": "FAQ Auto (PDF) - token de autenticação (client_credentials) e portal Developers",
    "owner_kind": "insurer",
    "owner_key": "yelum",
    "base_url": "https://www.yelumseguros.com.br/Shared%20Documents/Digital/FAQ/FAQ-AUTO.pdf",
    "login_url": "https://www.yelumseguros.com.br/Shared%20Documents/Digital/FAQ/FAQ-AUTO.pdf",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "FAQ menciona URL de token em produção (integracao.grupohdiseguros.com.br/.../Token?grant_type=client_credentials) e referência ao portal de desenvolvedores developer.grupohdiseguros.com.br.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "auto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.yelumseguros.com.br/Shared%20Documents/Digital/FAQ/FAQ-AUTO.pdf",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "liberty_legacy__portal_do_desenvolvedor_producao_e_homologacao_l",
    "label": "Portal do Desenvolvedor (produção e homologação) - legado Liberty",
    "owner_kind": "insurer",
    "owner_key": "liberty_legacy",
    "base_url": "https://developer.libertyseguros.com.br/",
    "login_url": "https://test-developer.libertyseguros.com.br/",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "PDF oficial descreve modernização das APIs e orienta cadastro de chaves (client_id/client_secret) no novo portal; cita portais de homologação e produção.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.yelumseguros.com.br/Shared%20Documents/Digital/Comunicado/Moderniza%C3%A7%C3%A3o%20das%20APIS%20Liberty%20-%20Procedimento.pdf",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "liberty_legacy__base_de_apis_producao_e_homologacao_legado_liber",
    "label": "Base de APIs (produção e homologação) - legado Liberty",
    "owner_kind": "insurer",
    "owner_key": "liberty_legacy",
    "base_url": "https://api.libertyseguros.com.br",
    "login_url": "https://api-tst.libertyseguros.com.br",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "PDF descreve mudança das URLs base das APIs para ambientes de homologação e produção.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.yelumseguros.com.br/Shared%20Documents/Digital/Comunicado/Moderniza%C3%A7%C3%A3o%20das%20APIS%20Liberty%20-%20Procedimento.pdf",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "liberty_legacy__token_de_autenticacao_client_credentials_e_token",
    "label": "Token de autenticação (client_credentials) e tokenCorretor (E-Retorno V1) - legado Liberty",
    "owner_kind": "insurer",
    "owner_key": "liberty_legacy",
    "base_url": "https://api.libertyseguros.com.br/controledeacesso/token?grant_type=client_credentials",
    "login_url": "https://api.libertyseguros.com.br/controledeacesso/tokenCorretor?grant_type=client_credentials",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Documento menciona endpoints de autenticação para APIs (token) e para E-Retorno V1 (tokenCorretor) e necessidade de recadastrar token_corretor no portal do corretor.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "partial",
      "confidence": "confirmed",
      "official_sources": "https://www.yelumseguros.com.br/Shared%20Documents/Digital/Comunicado/Moderniza%C3%A7%C3%A3o%20das%20APIS%20Liberty%20-%20Procedimento.pdf",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "sura__portal_do_corretor_canal_do_corretor_acesso_web",
    "label": "Portal do Corretor (Canal do Corretor) - acesso web",
    "owner_kind": "insurer",
    "owner_key": "sura",
    "base_url": "https://www.segurossura.com.br/acesso-portal/corretor.html",
    "login_url": "https://www.segurossura.com.br/acesso-portal/corretor.html",
    "supported_journeys": [
      "login"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Página descreve funções (2ª via, sinistro, cotações, comissão) e recomenda Edge com compatibilidade IE; não há evidência pública de portal de desenvolvedor/APIs nesta coleta.",
    "metadata": {
      "audience": "corretor",
      "line_of_business": "multiproduto",
      "journey_type": "login_base",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "portal_only",
      "public_api_evidence": "unclear",
      "broker_standardization_likelihood": "low",
      "same_for_all_brokers": "unknown",
      "confidence": "confirmed",
      "official_sources": "https://www.segurossura.com.br/acesso-portal/corretor.html",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "open_insurance__area_do_desenvolvedor_especificacoes_e_guias",
    "label": "Área do Desenvolvedor (especificações e guias)",
    "owner_kind": "regulator",
    "owner_key": "open_insurance",
    "base_url": "https://br-openinsurance.github.io/areadesenvolvedor/",
    "login_url": "https://br-openinsurance.github.io/areadesenvolvedor/",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Área pública com orientações para implementação e testes automatizados de conformidade das APIs do ecossistema Open Insurance.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_public",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://br-openinsurance.github.io/areadesenvolvedor/; https://opinbrasil.com.br/participante/como-participar/certificado-de-conformidade",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "susep__manual_de_apis_do_open_insurance_susep_versao_1_",
    "label": "Manual de APIs do Open Insurance (SUSEP) - versão 1.2",
    "owner_kind": "regulator",
    "owner_key": "susep",
    "base_url": "https://www.gov.br/susep/pt-br/assuntos/open-insurance/arquivos/manual-de-apis-do-open-insurance-v1-2.pdf/%40%40display-file/file",
    "login_url": "https://www.gov.br/susep/pt-br/assuntos/open-insurance/arquivos/manual-de-apis-do-open-insurance-v1-2.pdf/%40%40display-file/file",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Manual oficial define especificações das APIs do Open Insurance e referencia a Área do Desenvolvedor; descreve princípios e APIs do ecossistema.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "unknown",
      "integration_type": "api_public",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.gov.br/susep/pt-br/assuntos/open-insurance/arquivos/manual-de-apis-do-open-insurance-v1-2.pdf/%40%40display-file/file",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "susep__api_corretores_consulta_de_corretor_e_download_d",
    "label": "API Corretores (consulta de corretor e download da base) - instruções",
    "owner_kind": "regulator",
    "owner_key": "susep",
    "base_url": "https://www.gov.br/susep/pt-br/arquivos/arquivos-licenciamento/corretor-de-seguros/empresa-consulta-api-corretores-instrucoes.pdf/%40%40display-file/file",
    "login_url": "https://www.gov.br/susep/pt-br/arquivos/arquivos-licenciamento/corretor-de-seguros/empresa-consulta-api-corretores-instrucoes.pdf/%40%40display-file/file",
    "supported_journeys": [
      "api_catalog"
    ],
    "auth_methods": [
      "sso"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "sandbox_ready",
    "scope": "global",
    "notes": "Documento descreve autenticação via JWT e endpoints para consulta por CPF e para baixar arquivo zip com base de corretores; acesso requer cliente válido.",
    "metadata": {
      "audience": "segurado",
      "line_of_business": "unknown",
      "journey_type": "api_catalog",
      "url_kind": "canonical",
      "session_profile": "api_token_based",
      "integration_type": "api_partner",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "high",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://www.gov.br/susep/pt-br/arquivos/arquivos-licenciamento/corretor-de-seguros/empresa-consulta-api-corretores-instrucoes.pdf/%40%40display-file/file",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  },
  {
    "portal_id": "junto__portal_do_desenvolvedor_apis_para_emissao",
    "label": "Portal do Desenvolvedor (APIs para emissão)",
    "owner_kind": "insurer",
    "owner_key": "junto",
    "base_url": "https://desenvolvedor.juntoseguros.com/",
    "login_url": "https://desenvolvedor.juntoseguros.com/",
    "supported_journeys": [
      "developer_portal"
    ],
    "auth_methods": [
      "password"
    ],
    "challenge_profile": {
      "captcha": false,
      "mfa": false,
      "certificate": false,
      "otp": false,
      "requires_hitl": false
    },
    "browser_strategy": {
      "primary": "browserbase_playwright_stagehand",
      "fallback": "skyvern_lab"
    },
    "status": "needs_review",
    "scope": "global",
    "notes": "Portal de desenvolvedor aberto com criação de conta; voltado a integração de APIs para emissão.",
    "metadata": {
      "audience": "desenvolvedor",
      "line_of_business": "multiproduto",
      "journey_type": "developer_portal",
      "url_kind": "canonical",
      "session_profile": "likely_expires",
      "integration_type": "api_public",
      "public_api_evidence": "yes",
      "broker_standardization_likelihood": "medium",
      "same_for_all_brokers": "yes",
      "confidence": "confirmed",
      "official_sources": "https://desenvolvedor.juntoseguros.com/",
      "checked_at": "2026-04-06",
      "registry_block": "technical",
      "source_document": "deep-research-report PROMPT 2.md",
      "source_type": "official_research"
    },
    "created_at": "2026-06-18T00:00:00.000Z",
    "updated_at": "2026-06-18T00:00:00.000Z"
  }
];
