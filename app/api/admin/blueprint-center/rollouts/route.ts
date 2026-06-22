// SPEC-013 Fase B P4 — lista rollouts (master-only).
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin } from '@/lib/admin/admin-auth';
import { listRollouts } from '@/lib/admin/release-rollout-store';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const companyId = req.nextUrl.searchParams.get('company_id') || undefined;
  const out = await listRollouts(auth.supabase, companyId);
  return NextResponse.json(out);
}
