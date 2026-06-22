// TA2-C — conhecimento privado da corretora (read-only, escopo company).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { getKnowledge } from '@/lib/admin/tenant-overview-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getKnowledge(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out);
}
