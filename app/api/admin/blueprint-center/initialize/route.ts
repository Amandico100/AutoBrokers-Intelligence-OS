// SPEC-013 Fase B P2 — inicializa os Source Agents do Studio (master-only, idempotente).
// Disparo manual (sem escrita automática no carregamento). Não toca empresas-cliente.
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { initializeStudio } from '@/lib/admin/blueprint-studio-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await initializeStudio(auth.supabase);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
