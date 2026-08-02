// SPEC-064 Bloco H — autenticação pelo caminho canônico.
// Esta rota resolvia sessão de admin por um helper que morava dentro do
// módulo do Portal Browser (removido). Auth pertence a `admin-auth.ts`.
import { NextResponse } from 'next/server';
import { getAdminContext } from '@/lib/admin/admin-auth';
import {
  getProductionFlags,
  evaluateGlobalKillSwitch,
  evaluatePortalRealActionGate,
  evaluateExternalActionRealSendGate,
  evaluateRagKnowledgePublishGate,
  evaluateMemoryAccessGate,
} from '@/lib/security/production-gates';

export const dynamic = 'force-dynamic';

/** GET — health-check dos gates de produção. Tudo bloqueado por padrão; sem segredos. */
export async function GET() {
  try {
    const ctx = await getAdminContext();
    if (!ctx?.adminId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });

    const flags = getProductionFlags();
    const kill = evaluateGlobalKillSwitch(flags);
    const portal = evaluatePortalRealActionGate({ flags });
    const external = evaluateExternalActionRealSendGate({ flags });
    const rag = evaluateRagKnowledgePublishGate({ flags, target: 'attendance' });
    const memory = evaluateMemoryAccessGate({ flags, actor: 'attendance' });

    return NextResponse.json({
      ok: true,
      flags, // só booleans — sem segredos
      global_kill_switch: kill.active,
      portal_real_action_allowed: false,
      external_action_real_send_allowed: false,
      rag_attendance_publish_allowed: false,
      memory_long_term_allowed: flags.memory_long_term_enabled === true ? false : false,
      gates: {
        portal_real_action: { allowed: portal.allowed, blockers: portal.blockers },
        external_action_real_send: { allowed: external.allowed, blockers: external.blockers },
        rag_knowledge_publish: { allowed: rag.allowed, blockers: rag.blockers },
        memory_access: { allowed: memory.allowed, blockers: memory.blockers },
      },
      warnings: kill.active ? [] : ['global_kill_switch_off_review_before_real'],
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[SECURITY PRODUCTION GATES]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
