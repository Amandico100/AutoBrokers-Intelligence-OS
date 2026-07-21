import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';

import { sessionOptions, type SessionData } from '@/lib/iron-session';
import { getSupabaseAdmin, resolveSessionCompany } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * SPEC-047 — Multi-empresa (o mesmo e-mail acessa mais de uma corretora).
 *
 * GET  → { companies: [{id, name, role, is_owner, active}] }
 * POST → { company_id } — troca a empresa ATIVA da sessão (valida o vínculo
 *        em company_members; o company_id nunca é aceito sem vínculo).
 */

export async function GET() {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  const { data: members } = await supabase
    .from('company_members')
    .select('company_id, role, is_owner')
    .eq('user_id', ctx.userId)
    .eq('status', 'active');

  const ids = (members || []).map((m) => m.company_id);
  if (!ids.length) return NextResponse.json({ companies: [] });

  const { data: companies } = await supabase
    .from('companies')
    .select('id, company_name, status')
    .in('id', ids)
    .eq('status', 'active');

  const byId = new Map((companies || []).map((c) => [c.id, c]));
  const out = (members || [])
    .filter((m) => byId.has(m.company_id))
    .map((m) => ({
      id: m.company_id,
      name: byId.get(m.company_id)!.company_name,
      role: m.role,
      is_owner: m.is_owner,
      active: m.company_id === ctx.companyId,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));

  return NextResponse.json({ companies: out });
}

export async function POST(req: NextRequest) {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
  if (!session.userId) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const companyId = String(body.company_id || '').trim();
  if (!companyId) return NextResponse.json({ error: 'company_id obrigatório' }, { status: 400 });

  const supabase = getSupabaseAdmin();
  const { data: member } = await supabase
    .from('company_members')
    .select('company_id')
    .eq('user_id', session.userId)
    .eq('company_id', companyId)
    .eq('status', 'active')
    .maybeSingle();
  if (!member) {
    return NextResponse.json({ error: 'Você não tem acesso a esta empresa.' }, { status: 403 });
  }

  session.activeCompanyId = companyId;
  await session.save();
  return NextResponse.json({ ok: true, company_id: companyId });
}
