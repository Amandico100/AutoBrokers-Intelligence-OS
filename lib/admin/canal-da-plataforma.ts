// SPEC-133-A F4 — QUAL é a empresa do canal da plataforma (o Quem Cobra Menos).
//
// 🔴 CLAUDE.md §13.9: nenhum id de empresa escrito no código. A empresa do canal
// é descoberta no banco pelo TIPO (`companies.company_kind = 'platform_canal'`,
// SPEC-130-A) — no ambiente de teste, no de produção e no de uma corretora que
// um dia rode o próprio canal, a mesma linha de código acha a empresa certa.
//
// ⛔ Fail-closed: nenhuma empresa desse tipo → 404; MAIS de uma → 409. Escolher
// "a primeira" entre duas seria parear o WhatsApp na empresa errada em silêncio.
import type { SupabaseClient } from '@supabase/supabase-js';

export const KIND_DO_CANAL = 'platform_canal';

export type EmpresaDoCanal =
  | { ok: true; companyId: string; nome: string | null }
  | { ok: false; status: 404 | 409 | 503; detail: 'canal_nao_cadastrado' | 'canal_ambiguo' | 'canal_indisponivel' };

/** Pura: decide sobre as linhas lidas (o teste executa esta função). */
export function escolherEmpresaDoCanal(
  linhas: Array<{ id?: string | null; company_name?: string | null }> | null | undefined,
): EmpresaDoCanal {
  const validas = (linhas || []).filter((l) => typeof l?.id === 'string' && l.id.length > 0);
  if (validas.length === 0) return { ok: false, status: 404, detail: 'canal_nao_cadastrado' };
  if (validas.length > 1) return { ok: false, status: 409, detail: 'canal_ambiguo' };
  return { ok: true, companyId: validas[0].id as string, nome: validas[0].company_name ?? null };
}

/** Lê no banco (service role; o filtro é o tipo, nunca um id). */
export async function resolverEmpresaDoCanal(supabase: SupabaseClient): Promise<EmpresaDoCanal> {
  try {
    const { data, error } = await supabase
      .from('companies')
      .select('id, company_name')
      .eq('company_kind', KIND_DO_CANAL)
      .limit(2);
    if (error) return { ok: false, status: 503, detail: 'canal_indisponivel' };
    return escolherEmpresaDoCanal(data as Array<{ id?: string | null; company_name?: string | null }>);
  } catch {
    return { ok: false, status: 503, detail: 'canal_indisponivel' };
  }
}
