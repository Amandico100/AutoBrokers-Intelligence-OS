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
    const { data: member, error: erroVinculo } = await supabase
      .from('company_members')
      .select('company_id')
      .eq('user_id', session.userId)
      .eq('company_id', active)
      .eq('status', 'active')
      .maybeSingle();
    if (member?.company_id) return { userId: session.userId, companyId: member.company_id };

    // 🔴 SPEC-098 · CONSERTO 1 (red team B3) — VÍNCULO REVOGADO NÃO CAI NA
    //    PRIMÁRIA. Devolve `null` (o chamador responde 401/403).
    //
    // ⚠️ Até aqui, o `if` sem `else` deixava a execução escorregar para a
    // consulta de baixo e devolver a empresa PRIMÁRIA — com 200. O backend
    // desta mesma SPEC escreve a regra oposta em letras grandes
    // (`backend/app/core/auth.py:343-348`): *"vínculo não vigente → 403, nunca
    // o silêncio de cair na primária: cair na primária devolveria dado da
    // corretora ERRADA com status 200, que é o defeito mais caro que existe
    // aqui"*. E `requireCompanyMember` (`lib/admin/admin-auth.ts:74-82`) já
    // fazia 403. O BFF fazia o contrário dos dois.
    //
    // 📊 O raio disto: esta SPEC passou 11 rotas a depender deste resolvedor —
    // as 7 de `billing/*`, `n8n`, `user/company-data`, `chat/session` e a proxy
    // `mcp/[...caminho]`. `billing/change-plan` e `billing/portal` ESCREVEM. O
    // sócio com o acesso à corretora B revogado continua com `activeCompanyId=B`
    // no cookie e com "B" no seletor da tela — e a escrita ia para a A.
    //
    // ⛔ Erro de banco também cai aqui: não conseguir confirmar o vínculo não é
    // o mesmo que ter o vínculo (fail-closed, como `vinculo_vigente`).
    if (erroVinculo) {
      console.error('[SESSÃO] não deu para conferir o vínculo da empresa ativa:', erroVinculo.message);
    }
    return null;
  }

  // Sem empresa escolhida no seletor: vale a primária. Este é o CONTROLE — o
  // caminho de quem nunca trocou de corretora, que não pode mudar de
  // comportamento por causa do conserto acima.

  const { data, error } = await supabase
    .from('users_v2')
    .select('company_id')
    .eq('id', session.userId)
    .single();

  if (error || !data?.company_id) return null;
  return { userId: session.userId, companyId: data.company_id };
}
