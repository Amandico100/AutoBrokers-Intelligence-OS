// SPEC-013 Fase B P2 — publica/persiste as releases reais v1.0.0 (master-only, idempotente).
// Secret-scan obrigatório antes de publicar; hash SHA-256; sem duplicar chave/versão.
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { publishSeedReleases } from '@/lib/admin/blueprint-studio-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await publishSeedReleases(auth.supabase);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
