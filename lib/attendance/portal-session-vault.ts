// 43P-FINAL-1 — Vault adapter para SessionRef de portal. SELF-CONTAINED.
// O storageState/cookies REAIS só podem ser persistidos cifrados num Vault real.
// Sem Vault disponível → FALHA FECHADA (vault_unavailable); NUNCA grava cookie em
// tenant_connections/Supabase comum, NUNCA finge sucesso, NUNCA loga segredo.

export interface PortalSessionVaultWriteInput {
  company_id: string;
  portal_account_id: string;
  provider: string;
  // Conteúdo sensível (storageState/cookies) — fica SÓ aqui dentro do adapter,
  // nunca sai. O retorno é apenas uma referência opaca.
  secret_payload: unknown;
  metadata?: Record<string, unknown>;
}

export interface PortalSessionVaultWriteResult {
  ok: boolean;
  storage_ref: string | null; // referência opaca (nunca o segredo)
  reason: string;
}

export interface PortalSessionVaultReadInput {
  company_id: string;
  portal_account_id: string;
  storage_ref: string; // referência opaca (uuid do secret no Vault)
}
export interface PortalSessionVaultReadResult {
  ok: boolean;
  secret_payload: unknown | null; // SÓ server-side, em memória; nunca exposto/logado
  reason: string;
}

export interface PortalSessionVaultAdapter {
  available: () => Promise<boolean>;
  write: (input: PortalSessionVaultWriteInput) => Promise<PortalSessionVaultWriteResult>;
  read: (input: PortalSessionVaultReadInput) => Promise<PortalSessionVaultReadResult>;
}

// Detecta vazamento de segredo num objeto de referência que será exposto.
const REF_FORBIDDEN = ['storagestate', 'storage_state', 'cookie', 'cookies', 'connecturl', 'connect_url', 'signingkey', 'signing_key', 'token', 'authorization', 'apikey', 'api_key', 'seleniumremoteurl', 'password', 'otp'];
export function findVaultRefSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (REF_FORBIDDEN.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findVaultRefSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

/** Adapter que FALHA FECHADO: usado quando não há Vault real configurado. */
export const failClosedVaultAdapter: PortalSessionVaultAdapter = {
  available: async () => false,
  write: async () => ({ ok: false, storage_ref: null, reason: 'vault_unavailable' }),
  read: async () => ({ ok: false, secret_payload: null, reason: 'vault_unavailable' }),
};

/**
 * Lê o storageState cifrado via Vault (server-side). FALHA FECHADA sem Vault.
 * O payload retornado é SÓ para uso em memória no closure de restore — nunca
 * deve ser logado/persistido/retornado ao frontend.
 */
export async function readSessionRefViaVault(
  input: PortalSessionVaultReadInput,
  adapter: PortalSessionVaultAdapter = failClosedVaultAdapter,
): Promise<PortalSessionVaultReadResult> {
  if (!input.storage_ref) return { ok: false, secret_payload: null, reason: 'missing_storage_ref' };
  const ok = await adapter.available();
  if (!ok) return { ok: false, secret_payload: null, reason: 'vault_unavailable' };
  return adapter.read(input);
}

/**
 * Persiste a SessionRef via Vault. Se o Vault não estiver disponível, FALHA
 * FECHADA. Garante que o resultado NÃO contém segredo (storage_ref é opaca).
 */
export async function persistSessionRefViaVault(
  input: PortalSessionVaultWriteInput,
  adapter: PortalSessionVaultAdapter = failClosedVaultAdapter,
): Promise<PortalSessionVaultWriteResult> {
  const ok = await adapter.available();
  if (!ok) return { ok: false, storage_ref: null, reason: 'vault_unavailable' };
  const res = await adapter.write(input);
  if (res.ok && res.storage_ref) {
    // Defesa em profundidade: storage_ref nunca pode parecer um segredo.
    const leak = findVaultRefSecrets({ storage_ref: res.storage_ref });
    if (leak.length > 0) return { ok: false, storage_ref: null, reason: 'vault_ref_unsafe' };
  }
  return res;
}
