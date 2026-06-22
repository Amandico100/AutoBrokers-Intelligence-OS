// SPEC-013 Fase B — leitura defensiva da classificação de empresa. Server-only.
// DEFENSIVO: enquanto a coluna company_kind não existir no banco (pré-migration),
// retorna 'client' — comportamento idêntico ao de hoje. Pós-migration, ativa os guardas.
import type { SupabaseClient } from '@supabase/supabase-js';
import { normalizeCompanyKind, type CompanyKind } from '@/lib/admin/company-kind';

export async function getCompanyKind(supabase: SupabaseClient, companyId: string): Promise<CompanyKind> {
  try {
    const { data, error } = await supabase.from('companies').select('company_kind').eq('id', companyId).maybeSingle();
    if (error) return 'client'; // coluna ainda não existe → trata como cliente
    return normalizeCompanyKind((data as any)?.company_kind);
  } catch {
    return 'client';
  }
}
