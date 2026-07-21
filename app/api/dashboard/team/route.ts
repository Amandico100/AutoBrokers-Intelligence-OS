// TA2-C / SPEC-048 — equipe da corretora ATIVA, gerida pelo próprio dono/admin
// no dashboard (sem portal admin, sem confirmação de e-mail).
// GET: membros (via company_members). POST: adicionar. PATCH: editar.
// DELETE: remover o vínculo. Escritas exigem papel administrativo DA empresa
// ativa; um membro comum só enxerga a lista.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { canWriteTenantConfig } from '@/lib/admin/admin-auth-policy';
import { getTeam } from '@/lib/admin/tenant-overview-store';
import { hashPassword } from '@/lib/auth';

export const dynamic = 'force-dynamic';

const ALLOWED_ROLES = new Set(['admin_company', 'member']);

const digits = (v: unknown) => String(v || '').replace(/\D/g, '');

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getTeam(auth.supabase, auth.ctx.companyId);
  return NextResponse.json({
    ...out,
    can_manage: canWriteTenantConfig({ role: auth.ctx.role, isOwner: auth.ctx.isOwner }),
    me: auth.ctx.userId,
  });
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));

  const email = String(body.email || '').trim().toLowerCase();
  const firstName = String(body.first_name || '').trim();
  const lastName = String(body.last_name || '').trim();
  const phone = digits(body.phone);
  const role = ALLOWED_ROLES.has(String(body.role)) ? String(body.role) : 'member';
  const password = String(body.password || 'mudar123');
  if (!email || !email.includes('@')) return NextResponse.json({ ok: false, error: 'E-mail inválido.' }, { status: 400 });
  if (!firstName) return NextResponse.json({ ok: false, error: 'Informe o nome.' }, { status: 400 });
  if (password.length < 6) return NextResponse.json({ ok: false, error: 'Senha provisória muito curta (mínimo 6).' }, { status: 400 });

  const supabase = auth.supabase;
  const { data: existing } = await supabase.from('users_v2')
    .select('id, company_id').eq('email', email).is('deleted_at', null).maybeSingle();

  let userId = existing?.id as string | undefined;
  if (!userId) {
    // Usuário novo: nasce com esta empresa como primária. CPF placeholder único
    // (o membro completa depois em Configurações); sem confirmação de e-mail.
    const cpfPlaceholder = `p${Date.now().toString().slice(-12)}`;
    const { data: created, error } = await supabase.from('users_v2').insert({
      email,
      password_hash: await hashPassword(password),
      first_name: firstName,
      last_name: lastName || '',
      cpf: cpfPlaceholder,
      phone: phone || '0',
      birth_date: '1990-01-01',
      company_id: auth.ctx.companyId,
      status: 'active',
      role,
      is_owner: false,
      terms_accepted_at: new Date().toISOString(),
      privacy_policy_accepted_at: new Date().toISOString(),
    }).select('id').single();
    if (error || !created?.id) {
      console.error('[TEAM] create user error:', error?.message);
      return NextResponse.json({ ok: false, error: 'Não foi possível criar o usuário.' }, { status: 500 });
    }
    userId = created.id;
  }

  const { error: memberErr } = await supabase.from('company_members').upsert(
    { user_id: userId, company_id: auth.ctx.companyId, role, is_owner: false, status: 'active' },
    { onConflict: 'user_id,company_id' },
  );
  if (memberErr) {
    console.error('[TEAM] membership error:', memberErr.message);
    return NextResponse.json({ ok: false, error: 'Não foi possível vincular à empresa.' }, { status: 500 });
  }
  return NextResponse.json({ ok: true, user_id: userId, existed: Boolean(existing) });
}

export async function PATCH(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const userId = String(body.user_id || '').trim();
  if (!userId) return NextResponse.json({ ok: false, error: 'user_id obrigatório' }, { status: 400 });
  const supabase = auth.supabase;

  const { data: member } = await supabase.from('company_members')
    .select('id, role, is_owner').eq('user_id', userId)
    .eq('company_id', auth.ctx.companyId).eq('status', 'active').maybeSingle();
  if (!member) return NextResponse.json({ ok: false, error: 'Membro não encontrado nesta empresa.' }, { status: 404 });
  // Dono só é editado por outro dono (nunca rebaixado por um gestor).
  if (member.is_owner && !auth.ctx.isOwner) {
    return NextResponse.json({ ok: false, error: 'Só o dono pode editar outro dono.' }, { status: 403 });
  }

  const userUpd: Record<string, unknown> = {};
  if (typeof body.first_name === 'string' && body.first_name.trim()) userUpd.first_name = body.first_name.trim();
  if (typeof body.last_name === 'string') userUpd.last_name = body.last_name.trim();
  if (body.phone != null) userUpd.phone = digits(body.phone) || '0';
  if (typeof body.password === 'string' && body.password) {
    if (body.password.length < 6) return NextResponse.json({ ok: false, error: 'Senha muito curta (mínimo 6).' }, { status: 400 });
    userUpd.password_hash = await hashPassword(body.password);
  }
  if (Object.keys(userUpd).length) {
    userUpd.updated_at = new Date().toISOString();
    const { error } = await supabase.from('users_v2').update(userUpd).eq('id', userId);
    if (error) return NextResponse.json({ ok: false, error: 'Não foi possível atualizar os dados.' }, { status: 500 });
  }

  if (typeof body.role === 'string' && ALLOWED_ROLES.has(body.role) && body.role !== member.role && !member.is_owner) {
    const { error } = await supabase.from('company_members').update({ role: body.role }).eq('id', member.id);
    if (error) return NextResponse.json({ ok: false, error: 'Não foi possível mudar o papel.' }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}

export async function DELETE(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const userId = String(body.user_id || '').trim();
  if (!userId) return NextResponse.json({ ok: false, error: 'user_id obrigatório' }, { status: 400 });
  if (userId === auth.ctx.userId) {
    return NextResponse.json({ ok: false, error: 'Você não pode remover a si mesmo.' }, { status: 400 });
  }
  const supabase = auth.supabase;
  const { data: member } = await supabase.from('company_members')
    .select('id, is_owner').eq('user_id', userId)
    .eq('company_id', auth.ctx.companyId).eq('status', 'active').maybeSingle();
  if (!member) return NextResponse.json({ ok: false, error: 'Membro não encontrado nesta empresa.' }, { status: 404 });
  if (member.is_owner) {
    return NextResponse.json({ ok: false, error: 'Donos não podem ser removidos por aqui.' }, { status: 403 });
  }
  // Remove o VÍNCULO com esta empresa — a conta continua existindo (a pessoa
  // pode pertencer a outra corretora).
  const { error } = await supabase.from('company_members').delete().eq('id', member.id);
  if (error) return NextResponse.json({ ok: false, error: 'Não foi possível remover.' }, { status: 500 });
  return NextResponse.json({ ok: true });
}
