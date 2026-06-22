// SPEC-013 B1 — cria um Source Agent de Auxiliar no Studio (master-only) e lista os existentes.
import { NextRequest, NextResponse } from 'next/server';
import { requireMasterAdmin, assertSameOrigin } from '@/lib/admin/admin-auth';
import { createSourceAuxiliary, listStudioAuxiliarySources } from '@/lib/admin/blueprint-studio-store';

export const dynamic = 'force-dynamic';

export async function GET() {
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await listStudioAuxiliarySources(auth.supabase);
  return NextResponse.json(out);
}

export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireMasterAdmin();
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const out = await createSourceAuxiliary(auth.supabase, {
    name: typeof body.name === 'string' ? body.name : '',
    slug: typeof body.slug === 'string' ? body.slug : '',
    description: typeof body.description === 'string' ? body.description : undefined,
  });
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
