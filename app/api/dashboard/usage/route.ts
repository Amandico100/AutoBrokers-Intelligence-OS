// TA2-C — custos e uso reais da corretora (últimos 30 dias).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { gatherUsage } from '@/lib/admin/tenant-usage-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await gatherUsage(auth.supabase, auth.ctx.companyId);
  return NextResponse.json({ ok: true, ...out });
}
