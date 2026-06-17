import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { resolveInternalCompanyId } from '@/lib/attendance/runtime-internal-auth';

export const dynamic = 'force-dynamic';

/** GET — retorna o outbox e a trilha de auditoria persistidos (sanitizados). */
export async function GET(request: NextRequest, { params }: { params: Promise<{ caseId: string }> }) {
  try {
    const { caseId } = await params;
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    const supabaseAdmin = getAdminClient();
    let companyId: string | null = null;
    if (session.userId) companyId = await getCompanyId(supabaseAdmin, session.userId);
    else companyId = resolveInternalCompanyId(request, {});
    if (!companyId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const { data: packet } = await supabaseAdmin
      .from('dispatch_packets')
      .select('metadata')
      .eq('company_id', companyId)
      .eq('idempotency_key', `dispatch_dry_run:${caseId}`)
      .maybeSingle();
    const pmd = packet?.metadata && typeof packet.metadata === 'object' ? (packet.metadata as Record<string, any>) : {};
    return NextResponse.json({
      ok: true,
      outbox: Array.isArray(pmd.external_action_outbox) ? pmd.external_action_outbox : [],
      audit_events: Array.isArray(pmd.external_action_audit_events) ? pmd.external_action_audit_events.slice(-20) : [],
      external_action: { allowed: false, send_allowed: false, sent: false },
    });
  } catch (error: any) {
    console.error('[ACTION OUTBOX GET] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
