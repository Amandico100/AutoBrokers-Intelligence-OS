// SPEC-013 Fase B P3 — cria draft de nova versão a partir do Source Agent editado (master-only).
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { createReleaseDraftFromSourceAgent } from '@/lib/admin/blueprint-studio-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const blueprintKey = typeof body.blueprint_key === 'string' ? body.blueprint_key : '';
  const bump = ['major', 'minor', 'patch'].includes(body.bump) ? body.bump : 'minor';
  if (!blueprintKey) return NextResponse.json({ ok: false, error: 'blueprint_key_required' }, { status: 400 });
  const out = await createReleaseDraftFromSourceAgent(auth.supabase, blueprintKey, bump);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
