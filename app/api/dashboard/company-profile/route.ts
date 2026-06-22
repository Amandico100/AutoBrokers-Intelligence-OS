// TA2-C — dados da corretora (perfil). GET membro; PATCH admin da própria + same-origin.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember, assertSameOrigin } from '@/lib/admin/admin-auth';
import { getCompanyProfile, patchCompanyProfile } from '@/lib/admin/company-profile-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getCompanyProfile(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out);
}

export async function PATCH(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const out = await patchCompanyProfile(auth.supabase, auth.ctx.companyId, body?.values && typeof body.values === 'object' ? body.values : body);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
