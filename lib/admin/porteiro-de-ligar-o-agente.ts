// SPEC-EXTRA-001.3 — BLOCO F · o painel pergunta ANTES de ligar o agente.
//
// ⛔ Este arquivo NÃO decide nada (CLAUDE.md §5). Ele PERGUNTA ao backend, que
// responde pelo mesmo `resolver_destino_de_suporte` por onde o handoff sai —
// um resolvedor "parecido" aqui decidiria uma coisa e o handoff faria outra
// (CLAUDE.md §9.4: um padrão medido com um motor e aplicado com outro é um
// padrão sobre outra coisa).
//
// 🔴 E A FALHA DE COMUNICAÇÃO DEIXA LIGAR. ⚠️ Isto é deliberado e é o oposto da
// regra de runtime: se o backend não responde, a corretora fica sem agente por
// uma indisponibilidade de rede — e o portão de execução
// (`attendance_agent_active`) continua fail-closed do outro lado. O que este
// porteiro evita é a configuração incompleta, não o backend fora do ar.
import { getBackendUrl } from '@/lib/backend-url';

export type VeredictoDeLigar = { pode: boolean; motivo: string; falta: string };

const PODE: VeredictoDeLigar = { pode: true, motivo: '', falta: '' };

export async function porteiroDeLigarOAgente(companyId: string): Promise<VeredictoDeLigar> {
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!key) {
    console.warn('[PORTEIRO LIGAR] sem chave interna — deixo ligar');
    return PODE;
  }
  try {
    const base = getBackendUrl();
    const res = await fetch(
      `${base}/api/atendimento/pode-ligar?company_id=${encodeURIComponent(companyId)}`,
      { headers: { 'X-AutoBrokers-Internal-Key': key }, cache: 'no-store' },
    );
    if (!res.ok) {
      console.warn(`[PORTEIRO LIGAR] backend respondeu ${res.status} — deixo ligar`);
      return PODE;
    }
    const body = (await res.json().catch(() => ({}))) as Partial<VeredictoDeLigar>;
    // ⚠️ Resposta sem o campo `pode` é resposta que não entendi: deixa ligar.
    if (typeof body.pode !== 'boolean') return PODE;
    return {
      pode: body.pode,
      motivo: String(body.motivo || ''),
      falta: String(body.falta || ''),
    };
  } catch (e) {
    console.warn('[PORTEIRO LIGAR] backend indisponível — deixo ligar', e);
    return PODE;
  }
}
