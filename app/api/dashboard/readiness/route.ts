// TA2-B — checklist de prontidão da corretora (estado real derivado).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { gatherReadiness } from '@/lib/admin/tenant-readiness-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await gatherReadiness(auth.supabase, auth.ctx.companyId);
  return NextResponse.json({ ok: true, ...out });
}
