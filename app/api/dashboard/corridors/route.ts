// SPEC-063 — catálogo de corredores da corretora.
// A lista vem do CÓDIGO que executa (backend/app/services/corridor_playbooks.py,
// servido por GET /api/corridors/catalog); o status vem de `tenant_corridors`.
// Catálogo indisponível devolve erro: melhor a tela dizer que não conseguiu ler
// do que mostrar menos corredores do que a corretora tem.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { listTenantCorridors } from '@/lib/admin/tenant-corridor-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await listTenantCorridors(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out, { status: out.ok ? 200 : 503 });
}
