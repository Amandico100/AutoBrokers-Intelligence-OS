// Server-only helpers para as rotas de Auxiliares (auth + company + Supabase admin).
// NÃO importar em componentes client — usa cookies(), iron-session e service role.
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

import { sessionOptions, type SessionData } from '@/lib/iron-session';

/** Supabase com SERVICE ROLE (somente server). Nunca expor no client. */
export function getSupabaseAdmin(): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

export interface SessionCompany {
  userId: string;
  companyId: string;
}

/**
 * Resolve o usuário autenticado + company_id. O company_id NUNCA vem do client.
 *
 * SPEC-047 (multi-empresa): se a sessão tem uma empresa ATIVA escolhida no
 * seletor, ela vale — desde que exista o vínculo em company_members (validado
 * a cada request; revogou o vínculo, o acesso cai na hora). Sem escolha,
 * vale a empresa primária (users_v2.company_id), como sempre.
 */
export async function resolveSessionCompany(): Promise<SessionCompany | null> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (!session.userId) return null;

  const supabase = getSupabaseAdmin();

  const active = session.activeCompanyId || null;
  if (active) {
    const { data: member } = await supabase
      .from('company_members')
      .select('company_id')
      .eq('user_id', session.userId)
      .eq('company_id', active)
      .eq('status', 'active')
      .maybeSingle();
    if (member?.company_id) return { userId: session.userId, companyId: member.company_id };
  }

  const { data, error } = await supabase
    .from('users_v2')
    .select('company_id')
    .eq('id', session.userId)
    .single();

  if (error || !data?.company_id) return null;
  return { userId: session.userId, companyId: data.company_id };
}
