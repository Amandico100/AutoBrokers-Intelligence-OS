// Orquestração autônoma do atendimento WhatsApp (42W1).
//
// Server-side: aciona as MESMAS rotas de runtime do dashboard (reply, policy-lookup,
// policy-select, step, dispatch-dry-run) via chave interna, para conduzir o
// atendimento sem cliques. NÃO é runtime paralelo: só orquestra os endpoints
// existentes. NUNCA envia externo; nunca decide cobertura por LLM.

/** Chama uma rota interna de runtime (server-to-server) com a chave interna. */
export async function callRuntimeInternal(
  origin: string,
  path: string,
  internalKey: string,
  body: Record<string, unknown>,
): Promise<{ ok: boolean; status: number; json: any }> {
  try {
    const res = await fetch(new URL(path, origin).toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify(body),
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, json };
  } catch {
    return { ok: false, status: 0, json: {} };
  }
}

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
 * Só dispara se a apólice já estiver verificada (evidence ready). Nunca envia externo.
 */
export async function maybePrepareDispatchDraft(input: {
  origin: string;
  internalKey: string;
  companyId: string;
  caseId: string;
  verificationStatus?: string | null;
}): Promise<DispatchDraftOutcome> {
  const verified = typeof input.verificationStatus === 'string' && input.verificationStatus.startsWith('verified');
  if (!verified) return { prepared: false, packet_state: null, message: null };

  const res = await callRuntimeInternal(
    input.origin,
    `/api/attendance/cases/${input.caseId}/runtime/dispatch-dry-run`,
    input.internalKey,
    { company_id: input.companyId },
  );
  if (!res.ok || !res.json?.ok) return { prepared: false, packet_state: null, message: null };
  const state = res.json?.dispatch_readiness?.packet_state ?? null;
  // 'incomplete' → ainda coletando; não anuncia dispatch (mantém a pergunta de slot).
  const message = state && state !== 'incomplete' ? DISPATCH_MESSAGES[state] ?? null : null;
  return { prepared: state != null && state !== 'incomplete', packet_state: state, message };
}
