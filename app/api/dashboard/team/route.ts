// TA2-C — equipe da corretora (read-only, sanitizado).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { getTeam } from '@/lib/admin/tenant-overview-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getTeam(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out);
}
