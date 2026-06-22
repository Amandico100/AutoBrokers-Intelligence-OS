// SPEC-013 Fase B P4 — aplica uma release a uma corretora (master-only, manual, canário).
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { applyRollout } from '@/lib/admin/release-rollout-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const releaseId = typeof body.release_id === 'string' ? body.release_id : '';
  const companyId = typeof body.company_id === 'string' ? body.company_id : '';
  if (!releaseId || !companyId) return NextResponse.json({ ok: false, error: 'parametros_obrigatorios' }, { status: 400 });
  const out = await applyRollout(auth.supabase, releaseId, companyId, auth.ctx.adminId);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
