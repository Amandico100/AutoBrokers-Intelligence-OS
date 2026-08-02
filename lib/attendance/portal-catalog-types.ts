// SPEC-064 Bloco H — os tipos do CATÁLOGO de portais, sem o simulador.
//
// Estes tipos moravam em `portal-admin-sanitizers.ts`, junto com a máquina do
// Portal Browser — que era 100% simulação e foi removida.
//
// O catálogo NÃO foi removido, e a distinção é a que importa:
//
//     o Portal Browser         era um simulador que nunca acessou nada
//     o catálogo de portais    é PESQUISA — 189 portais de seguradora
//                              mapeados a partir de levantamento oficial
//
// O Founder foi explícito sobre querer, depois destas SPECs, repetir na Porto,
// HDI, Tokio e Yelum o que já funciona na Allianz. **Este catálogo é o mapa
// desse trabalho.** Apagá-lo junto com o simulador seria jogar fora a pesquisa
// por causa do código que a acompanhava.
//
// Ver PENDENCIAS.md P-26.

// Os quatro tipos abaixo vieram VERBATIM de `portal-admin-sanitizers.ts`,
// recuperados do histórico do git. Reescrevê-los de memória produziu um
// enum incompleto que rejeitou 111 linhas do catálogo — o tipo tem de
// descrever o dado que existe, não o dado que eu imaginei.
export type PortalOwnerKind = 'insurer' | 'provider' | 'regulator' | 'broker' | 'other';

export type PortalAuthMethod = 'password' | 'mfa' | 'captcha' | 'sso' | 'certificate' | 'otp';

export type PortalDefinitionStatus = 'draft' | 'sandbox_ready' | 'needs_review' | 'inactive';

export type BrowserStrategyKind =
  | 'browserbase_playwright_stagehand' | 'browserbase'
  | 'local_playwright' | 'skyvern_lab' | 'unknown';

export interface BrowserStrategySpec {
  primary: BrowserStrategyKind;
  fallback: BrowserStrategyKind | null;
}

export interface ChallengeProfile {
  captcha: boolean;
  mfa: boolean;
  certificate: boolean;
  otp: boolean;
  /** SEMPRE true quando há qualquer challenge — é o que obriga humano no loop. */
  requires_hitl: boolean;
}

export interface PortalDefinitionRecord {
  portal_id: string;
  label: string;
  owner_kind: PortalOwnerKind;
  owner_key: string;
  base_url: string;
  login_url?: string | null;
  supported_journeys: string[];
  auth_methods: PortalAuthMethod[];
  challenge_profile: ChallengeProfile;
  browser_strategy: BrowserStrategySpec;
  status: PortalDefinitionStatus;
  scope?: 'global' | 'tenant_draft' | 'tenant_override';
  notes?: string | null;
  /** Evidência, fonte e confiança do levantamento. Sem credencial, sem PII. */
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
