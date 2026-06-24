// C2-P2 frente 2 — config dos provedores OAuth (Google Drive, Notion). Tenant-scoped.
// As credenciais ficam no ENV do serviço WEB (configuradas pelo Founder). Nada de segredo no client.

export interface OAuthProviderCfg {
  slug: string; // connector_template slug
  label: string;
  authUrl: string;
  tokenUrl: string;
  scopes: string[];
  clientIdEnv: string;
  clientSecretEnv: string;
  redirectEnv: string;
  authParams?: Record<string, string>;
  tokenAuth: 'body' | 'basic'; // google=body (form), notion=basic
}

export const OAUTH_PROVIDERS: Record<string, OAuthProviderCfg> = {
  'google-drive': {
    slug: 'google_drive',
    label: 'Google Drive',
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'https://oauth2.googleapis.com/token',
    scopes: ['https://www.googleapis.com/auth/drive.readonly'],
    clientIdEnv: 'GOOGLE_OAUTH_CLIENT_ID',
    clientSecretEnv: 'GOOGLE_OAUTH_CLIENT_SECRET',
    redirectEnv: 'GOOGLE_OAUTH_REDIRECT_URI',
    authParams: { access_type: 'offline', prompt: 'consent', include_granted_scopes: 'true' },
    tokenAuth: 'body',
  },
  notion: {
    slug: 'notion',
    label: 'Notion',
    authUrl: 'https://api.notion.com/v1/oauth/authorize',
    tokenUrl: 'https://api.notion.com/v1/oauth/token',
    scopes: [],
    clientIdEnv: 'NOTION_OAUTH_CLIENT_ID',
    clientSecretEnv: 'NOTION_OAUTH_CLIENT_SECRET',
    redirectEnv: 'NOTION_OAUTH_REDIRECT_URI',
    authParams: { owner: 'user' },
    tokenAuth: 'basic',
  },
};

// connector_template slug -> chave de provider OAuth (para o catálogo decidir o fluxo)
export const SLUG_TO_OAUTH_PROVIDER: Record<string, string> = {
  google_drive: 'google-drive',
  notion: 'notion',
};

export function providerCfg(key: string): OAuthProviderCfg | undefined {
  return OAUTH_PROVIDERS[key];
}

export function providerConfigured(key: string): boolean {
  const c = OAUTH_PROVIDERS[key];
  return Boolean(c && process.env[c.clientIdEnv] && process.env[c.clientSecretEnv]);
}
