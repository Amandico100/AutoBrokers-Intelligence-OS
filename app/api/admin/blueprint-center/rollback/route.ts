// SPEC-013 Fase B P4 — rollback da release de uma corretora (master-only, manual).
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { rollbackRollout } from '@/lib/admin/release-rollout-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const companyId = typeof body.company_id === 'string' ? body.company_id : '';
  const blueprintKey = typeof body.blueprint_key === 'string' ? body.blueprint_key : '';
  if (!companyId || !blueprintKey) return NextResponse.json({ ok: false, error: 'parametros_obrigatorios' }, { status: 400 });
  const out = await rollbackRollout(auth.supabase, companyId, blueprintKey, auth.ctx.adminId);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
