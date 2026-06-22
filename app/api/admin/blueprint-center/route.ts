// SPEC-013 Fase B P2 — estado do Blueprint Center (master-only). Read-only.
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin } from '@/lib/admin/admin-auth';
import { getStudioStatus } from '@/lib/admin/blueprint-studio-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await getStudioStatus(auth.supabase);
  return NextResponse.json(out);
}
