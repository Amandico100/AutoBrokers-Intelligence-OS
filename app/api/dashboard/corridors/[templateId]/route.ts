// TA2-B — ativar/pausar/retomar um corredor para a corretora logada.
// Apenas estado de configuração (não liga canal, não abre portal, não envia nada).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { setTenantCorridorStatus } from '@/lib/admin/tenant-corridor-store';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  const { templateId } = await params;
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const body = await req.json().catch(() => ({}));
  const action = typeof body.action === 'string' ? body.action : '';
  const out = await setTenantCorridorStatus(auth.supabase, auth.ctx.companyId, templateId, action, auth.ctx.userId);
  return NextResponse.json(out, { status: out.ok ? 200 : 400 });
}
