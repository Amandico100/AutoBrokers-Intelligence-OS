import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getIronSession } from 'iron-session';
import { getAdminClient, getCompanyId } from '@/lib/attendance/support-destinations';
import { sessionOptions, SessionData } from '@/lib/iron-session';
import { diagnoseInfocapConnection } from '@/lib/attendance/connectors/infocap-policy-lookup';

export const dynamic = 'force-dynamic';

const VALID_PROVIDERS = new Set(['z-api', 'evolution', 'evolution-api', 'wppconnect', 'whatsapp', 'whatsapp-cloud', 'meta']);

type Check = { name: string; ok: boolean; level: 'info' | 'warning' | 'blocker'; detail?: string };

/**
 * GET /api/attendance/whatsapp/preflight
 *
 * Preflight SANITIZADO do atendimento WhatsApp (sem segredo/token/telefone cru).
 * Verifica o que é visível ao app Next (chave interna, flag de envio real,
 * integração ativa, agente attendance, conexão InfoCap). Envs do backend
 * (ATTENDANCE_WHATSAPP_ENABLED, WHATSAPP_WEBHOOK_AUTH_MODE, ATTENDANCE_BRIDGE_URL)
 * são verificadas no backend e indicadas como "checar no backend".
 */
export async function GET(_request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const session = await getIronSession<SessionData>(cookieStore, sessionOptions);
    if (!session.userId) return NextResponse.json({ ok: false, error: 'Não autorizado' }, { status: 401 });

    const supabaseAdmin = getAdminClient();
    const companyId = await getCompanyId(supabaseAdmin, session.userId);
    if (!companyId) return NextResponse.json({ ok: false, error: 'Empresa não encontrada' }, { status: 404 });

    const checks: Check[] = [];
    const blockers: string[] = [];
    const warnings: string[] = [];
    const nextRequiredEnv: string[] = [];

    // 1. Chave interna Next↔Backend (necessária para o bridge).
    const hasInternalKey = Boolean(process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY);
    checks.push({ name: 'internal_key_present', ok: hasInternalKey, level: hasInternalKey ? 'info' : 'blocker' });
    if (!hasInternalKey) { blockers.push('internal_key_missing'); nextRequiredEnv.push('BACKEND_INTERNAL_API_KEY'); }

    // 2. Envio real (deve estar OFF por padrão).
    const outboundReal = process.env.WHATSAPP_ATTENDANCE_OUTBOUND_REAL_ENABLED === 'true';
    checks.push({ name: 'outbound_real_blocked', ok: !outboundReal, level: outboundReal ? 'warning' : 'info', detail: outboundReal ? 'envio real HABILITADO' : 'dry-run (seguro)' });
    if (outboundReal) warnings.push('outbound_real_enabled');

    // 3. Integração WhatsApp ativa para a empresa (sem expor token).
    const { data: integrations } = await supabaseAdmin
      .from('integrations')
      .select('provider, is_active, agent_id')
      .eq('company_id', companyId)
      .eq('is_active', true);
    const waActive = (integrations || []).some((i: any) => VALID_PROVIDERS.has(String(i.provider || '').toLowerCase()));
    checks.push({ name: 'whatsapp_integration_active', ok: waActive, level: waActive ? 'info' : 'blocker' });
    if (!waActive) blockers.push('no_active_whatsapp_integration');

    // 4. Agente de atendimento (insured_external).
    const { data: agents } = await supabaseAdmin
      .from('agents')
      .select('id')
      .eq('company_id', companyId)
      .eq('is_active', true)
      .eq('agent_role', 'attendance')
      .limit(1);
    const hasAttendanceAgent = Boolean(agents && agents.length > 0);
    checks.push({ name: 'attendance_agent_present', ok: hasAttendanceAgent, level: hasAttendanceAgent ? 'info' : 'blocker' });
    if (!hasAttendanceAgent) blockers.push('no_attendance_agent');

    // 5. Conexão InfoCap pronta (não obrigatória para iniciar, mas avisa).
    let infocapReady = false;
    try {
      const infocap = await diagnoseInfocapConnection(companyId);
      infocapReady = infocap.ready_for_real_lookup === true;
      checks.push({ name: 'infocap_connection_ready', ok: infocapReady, level: infocapReady ? 'info' : 'warning', detail: infocapReady ? 'pronta' : `blockers: ${infocap.blockers.join(',') || 'n/a'}` });
      if (!infocapReady) warnings.push('infocap_not_ready');
    } catch {
      checks.push({ name: 'infocap_connection_ready', ok: false, level: 'warning', detail: 'diag_failed' });
      warnings.push('infocap_diag_failed');
    }

    // 6. Corredores ativos (global + tenant) — WhatsApp é canal global (42W1.1).
    const { data: templates } = await supabaseAdmin
      .from('corridor_templates')
      .select('corridor_key, subcorridor_key, scope, company_id')
      .eq('is_active', true)
      .or(`company_id.is.null,company_id.eq.${companyId}`);
    const activeCorridors = (templates || []).length;
    checks.push({ name: 'active_corridor_templates', ok: activeCorridors > 0, level: activeCorridors > 0 ? 'info' : 'warning', detail: `${activeCorridors} corredor(es) ativo(s)` });
    if (activeCorridors === 0) warnings.push('no_active_corridor_templates');

    // 7. Default MVP por env (opcional). Sem default → desconhecidos vão para triagem.
    const defaultCorridor = process.env.ATTENDANCE_DEFAULT_CORRIDOR_KEY || null;
    checks.push({
      name: 'default_corridor_fallback',
      ok: true,
      level: 'info',
      detail: defaultCorridor ? `fallback MVP: ${defaultCorridor}` : 'sem default — intenção desconhecida vai para triagem (canal global)',
    });
    checks.push({ name: 'whatsapp_routing_mode', ok: true, level: 'info', detail: defaultCorridor ? 'global + fallback MVP' : 'global/triage' });

    // 8. Envs do backend (não visíveis aqui) — checar no backend.
    checks.push({ name: 'backend_envs', ok: true, level: 'info', detail: 'ATTENDANCE_WHATSAPP_ENABLED / WHATSAPP_WEBHOOK_AUTH_MODE / ATTENDANCE_BRIDGE_URL: verificar no backend' });

    const readiness = blockers.length > 0 ? 'blocked' : warnings.length > 0 ? 'warning' : 'ready';

    return NextResponse.json({
      ok: blockers.length === 0,
      readiness,
      checks,
      blockers,
      warnings,
      next_required_env: nextRequiredEnv,
      note: 'Envio externo bloqueado por padrão (dry-run). Nenhum segredo/telefone exposto.',
    });
  } catch (error: any) {
    console.error('[WA PREFLIGHT] error:', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
