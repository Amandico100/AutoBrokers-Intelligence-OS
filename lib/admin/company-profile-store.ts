// TA2-C — store do perfil da corretora (reusa `companies`). Server-only.
import type { SupabaseClient } from '@supabase/supabase-js';
import { COMPANY_PROFILE_FIELDS, validateCompanyProfile } from '@/lib/admin/company-profile';

const COLS = ['id', ...COMPANY_PROFILE_FIELDS.map((f) => f.key)].join(', ');

export async function getCompanyProfile(supabase: SupabaseClient, companyId: string) {
  const { data } = await supabase.from('companies').select(COLS).eq('id', companyId).maybeSingle();
  const values: Record<string, string> = {};
  for (const f of COMPANY_PROFILE_FIELDS) values[f.key] = (data as any)?.[f.key] ?? '';
  return { ok: true as const, fields: COMPANY_PROFILE_FIELDS, values };
}

export async function patchCompanyProfile(supabase: SupabaseClient, companyId: string, input: Record<string, unknown>) {
  const v = validateCompanyProfile(input);
  if (!v.ok) return { ok: false as const, error: 'validation_failed', errors: v.errors };
  if (Object.keys(v.clean).length === 0) return { ok: false as const, error: 'nada_para_salvar' };
  const { error } = await supabase.from('companies').update({ ...v.clean, updated_at: new Date().toISOString() }).eq('id', companyId);
  if (error) return { ok: false as const, error: 'update_failed' };
  return getCompanyProfile(supabase, companyId);
}
