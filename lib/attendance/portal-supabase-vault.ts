// 43P-FINAL-2 — PortalSessionVaultAdapter real via Supabase Vault (extensão
// supabase_vault). Server-only (usa service role). Grava storageState cifrado;
// retorna SÓ uma referência opaca (uuid do secret). FALHA FECHADA se a RPC não
// existir (migration não aplicada) — nunca grava segredo em tabela comum.
//
// Migration necessária (NÃO aplicada automaticamente): ver
// docs/canon/design/2026-06-claude-design/43P-FINAL-2-portal-mvp-go-live-report.md
// (funções public.portal_vault_store_session / portal_vault_probe, SECURITY DEFINER,
//  search_path fixo, execução só por service_role).
import type { SupabaseClient } from '@supabase/supabase-js';
import type { PortalSessionVaultAdapter } from '@/lib/attendance/portal-session-vault';

export function createSupabaseVaultAdapter(supabase: SupabaseClient): PortalSessionVaultAdapter {
  return {
    available: async () => {
      try {
        const { error } = await supabase.rpc('portal_vault_probe');
        return !error;
      } catch {
        return false;
      }
    },
    write: async (input) => {
      try {
        const name = `portal_session__${input.company_id}__${input.portal_account_id}__${Date.now()}`;
        const { data, error } = await supabase.rpc('portal_vault_store_session', {
          p_company_id: input.company_id,
          p_portal_account_id: input.portal_account_id,
          p_provider: input.provider,
          p_secret: JSON.stringify(input.secret_payload ?? null),
          p_name: name,
        });
        if (error) return { ok: false, storage_ref: null, reason: `vault_rpc_error:${error.code ?? 'unknown'}` };
        if (!data) return { ok: false, storage_ref: null, reason: 'vault_no_ref' };
        const ref = String(data);
        // A referência precisa ser opaca (uuid). Nunca pode parecer segredo.
        if (/cookie|storagestate|connecturl|signingkey|token|authorization/i.test(ref)) {
          return { ok: false, storage_ref: null, reason: 'vault_ref_unsafe' };
        }
        return { ok: true, storage_ref: ref, reason: 'stored' };
      } catch {
        return { ok: false, storage_ref: null, reason: 'vault_exception' };
      }
    },
  };
}
