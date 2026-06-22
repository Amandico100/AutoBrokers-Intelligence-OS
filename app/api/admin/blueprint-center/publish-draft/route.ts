// SPEC-013 Fase B P3 — publica uma draft (draft → published, imutável). Master-only.
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { publishReleaseDraft } from '@/lib/admin/blueprint-studio-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const releaseId = typeof body.release_id === 'string' ? body.release_id : '';
  if (!releaseId) return NextResponse.json({ ok: false, error: 'release_id_required' }, { status: 400 });
  const out = await publishReleaseDraft(auth.supabase, releaseId);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
