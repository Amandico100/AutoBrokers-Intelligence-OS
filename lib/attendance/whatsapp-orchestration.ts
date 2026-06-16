// Orquestração autônoma do atendimento WhatsApp (42W1 / 42W1.1).
//
// Aciona as MESMAS rotas de runtime do dashboard IN-PROCESS (ver runtime-invoke).
// NÃO é runtime paralelo; NUNCA envia externo; nunca decide cobertura por LLM.

const DISPATCH_MESSAGES: Record<string, string> = {
  hitl_required:
    'Já organizei o pacote do atendimento. Antes de acionar, nossa equipe precisa validar a cobertura para evitar qualquer erro.',
  ready_for_human_approval:
    'Já organizei o pacote do atendimento. Ele está pronto para aprovação de envio pela nossa equipe.',
  blocked:
    'Organizei o pacote, mas preciso que nossa equipe revise um detalhe da apólice antes de seguir.',
};

export interface DispatchDraftOutcome {
  prepared: boolean;
  packet_state: string | null;
  message: string | null;
}

/**
 * Hook idempotente: prepara o dispatch dry-run quando a evidência está pronta.
 * `runDispatch` é injetado (in-process) para manter este helper testável/desacoplado.
 */
export async function maybePrepareDispatchDraft(input: {
  verificationStatus?: string | null;
  runDispatch: () => Promise<{ ok: boolean; json: any }>;
}): Promise<DispatchDraftOutcome> {
  const verified = typeof input.verificationStatus === 'string' && input.verificationStatus.startsWith('verified');
  if (!verified) return { prepared: false, packet_state: null, message: null };

  const res = await input.runDispatch();
  if (!res.ok || !res.json?.ok) return { prepared: false, packet_state: null, message: null };
  const state = res.json?.dispatch_readiness?.packet_state ?? null;
  const message = state && state !== 'incomplete' ? DISPATCH_MESSAGES[state] ?? null : null;
  return { prepared: state != null && state !== 'incomplete', packet_state: state, message };
}
