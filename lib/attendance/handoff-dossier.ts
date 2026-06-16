// Gerador de dossiê de handoff (read-only do caso). NÃO envia mensagem,
// NÃO cria approval_request, NÃO cria dispatch. Sem token/secret/destination_ref cru.
import { destinationTypeLabel } from './support-destination-labels';
import { subcorridorLabel } from './labels';

export function maskPhone(value?: string | null): string {
  const r = (value || '').trim();
  if (!r) return '';
  const digits = r.replace(/\D/g, '');
  if (digits.length < 6) return r;
  return `${r.slice(0, 4)}****${r.slice(-4)}`;
}

export function normalizeSlots(slots: unknown): {
  filled: Record<string, unknown>;
  missing: string[];
  conflicts: unknown[];
} {
  const s = slots && typeof slots === 'object' && !Array.isArray(slots) ? (slots as Record<string, any>) : {};
  const filled =
    s.filled && typeof s.filled === 'object' && !Array.isArray(s.filled) ? (s.filled as Record<string, unknown>) : {};
  const missing = Array.isArray(s.missing) ? s.missing.filter((x: unknown): x is string => typeof x === 'string') : [];
  const conflicts = Array.isArray(s.conflicts) ? s.conflicts : [];
  return { filled, missing, conflicts };
}

type SlimDestination = {
  id: string;
  name: string;
  destination_type: string;
  channel_provider: string;
  display_ref: string | null;
  is_primary: boolean;
  fallback_enabled: boolean;
  silence_minutes: number;
} | null;

function slimDestination(d: any): SlimDestination {
  if (!d) return null;
  return {
    id: d.id,
    name: d.name,
    destination_type: d.destination_type,
    channel_provider: d.channel_provider,
    display_ref: d.display_ref ?? null,
    is_primary: Boolean(d.is_primary),
    fallback_enabled: Boolean(d.fallback_enabled),
    silence_minutes: d.silence_minutes ?? 0,
  };
}

function lineKindLabel(k?: string | null): string {
  if (!k) return '—';
  if (k === 'residential' || k === 'residencial') return 'Residencial';
  if (k === 'auto') return 'Auto';
  return k;
}

function verificationLabel(v?: string | null): string {
  if (!v) return '—';
  if (v.startsWith('verified')) return 'verificada';
  if (v === 'pending_human') return 'pendente';
  if (v === 'unverified') return 'não verificada';
  return v;
}

function capitalize(s?: string | null): string {
  if (!s) return '—';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function buildHandoffDossier(input: {
  caseRow: any;
  messages: any[];
  run: any;
  template: any;
  dispatchPackets: any[];
  destinations: any[];
  generatedAt: string;
  dispatchPacketDraft?: any;
}) {
  const { caseRow: c, messages, run, template: tpl, dispatchPackets, destinations, generatedAt, dispatchPacketDraft } = input;
  const slots = normalizeSlots(run?.slots);

  const msgs = Array.isArray(messages) ? messages : [];
  const userMsgs = msgs.filter((m: any) => m?.role === 'user');
  const lastUser = userMsgs.length ? userMsgs[userMsgs.length - 1] : null;
  const lastCustomerMessage =
    lastUser && typeof lastUser.content === 'string' ? lastUser.content.slice(0, 200) : null;

  const active = (destinations || []).filter((d: any) => d.is_active);
  const primary = active.find((d: any) => d.is_primary) || null;
  const fallbacks = active.filter((d: any) => !primary || d.id !== primary.id);

  const coverage =
    c.coverage_evidence && typeof c.coverage_evidence === 'object' && Object.keys(c.coverage_evidence).length > 0
      ? 'registered'
      : 'not_verified';

  return {
    case_id: c.id,
    case_number: c.case_number,
    generated_at: generatedAt,
    title: `Dossiê de handoff — ${c.customer_name || 'Segurado não informado'}`,
    summary: c.summary || null,
    customer: { name: c.customer_name || null, phone: c.customer_phone || null },
    status: {
      case_status: c.status,
      priority: c.priority,
      risk_level: c.risk_level,
      verification_status: c.verification_status,
      handoff_required: Boolean(c.handoff_required),
      handoff_reason: c.handoff_reason || null,
    },
    corridor: {
      display_name: tpl?.display_name || null,
      corridor_key: c.selected_corridor_key || tpl?.corridor_key || null,
      subcorridor_key: c.selected_subcorridor_key || tpl?.subcorridor_key || null,
      insurer_key: c.insurer_key || null,
      line_kind: c.line_kind || null,
      run_phase: run?.phase || null,
      run_status: run?.status || null,
    },
    policy: {
      source: c.policy_source || null,
      number: c.policy_number || null,
      verification_status: c.verification_status || null,
      coverage_evidence_status: coverage,
      snapshot: c.policy_snapshot && typeof c.policy_snapshot === 'object' ? c.policy_snapshot : null,
    },
    coverage_readiness:
      c.metadata?.coverage_readiness && typeof c.metadata.coverage_readiness === 'object'
        ? {
            state: c.metadata.coverage_readiness.state ?? null,
            dispatch_allowed: c.metadata.coverage_readiness.dispatch_allowed === true,
            human_required: c.metadata.coverage_readiness.human_required === true,
            message: typeof c.metadata.coverage_readiness.message === 'string' ? c.metadata.coverage_readiness.message : null,
          }
        : null,
    dispatch: {
      readiness:
        c.metadata?.dispatch_readiness && typeof c.metadata.dispatch_readiness === 'object'
          ? c.metadata.dispatch_readiness
          : null,
      packet_draft: dispatchPacketDraft && typeof dispatchPacketDraft === 'object' ? dispatchPacketDraft : null,
      hitl_reason:
        c.metadata?.dispatch_readiness?.packet_state === 'hitl_required'
          ? 'coverage_not_confirmed'
          : c.metadata?.dispatch_readiness?.packet_state === 'blocked'
            ? 'blocked_policy_or_risk'
            : null,
      human_next_steps:
        c.metadata?.dispatch_readiness?.packet_state === 'ready_for_human_approval'
          ? ['Revisar pacote', 'Aprovar envio (futuro)']
          : c.metadata?.dispatch_readiness?.packet_state === 'hitl_required'
            ? ['Validar cobertura manualmente', 'Aprovar/Reprovar cobertura']
            : c.metadata?.dispatch_readiness?.packet_state === 'incomplete'
              ? ['Coletar dados faltantes']
              : c.metadata?.dispatch_readiness?.packet_state === 'blocked'
                ? ['Revisão humana do caso', 'Tratar apólice/risco']
                : [],
    },
    slots: { filled: slots.filled, missing: slots.missing, conflicts: slots.conflicts },
    messages: { last_customer_message: lastCustomerMessage, message_count: msgs.length },
    support_destination: {
      configured: active.length > 0,
      primary: slimDestination(primary),
      fallbacks: fallbacks.map(slimDestination),
    },
    dispatch_packets: {
      count: (dispatchPackets || []).length,
      statuses: (dispatchPackets || []).map((p: any) => p.status).filter(Boolean),
    },
    recommended_next_step: c.next_step || null,
    external_action: {
      sent: false,
      allowed: Boolean(run?.diagnostics?.external_action_allowed),
      note: 'Nenhuma mensagem foi enviada neste endpoint.',
    },
  };
}

export function formatHandoffMarkdown(d: any): string {
  const L: string[] = [];
  L.push(`# Dossiê de atendimento — ${d.customer?.name || 'Segurado não informado'}`);
  L.push('');
  L.push(`Caso: ${d.case_number}`);
  L.push(`Status: ${d.status?.case_status ?? '—'}`);
  L.push(`Prioridade: ${d.status?.priority ?? '—'}`);
  L.push(`Risco: ${d.status?.risk_level ?? '—'}`);
  if (d.status?.handoff_reason) L.push(`Motivo do handoff: ${d.status.handoff_reason}`);

  L.push('', '## Cliente');
  L.push(`Nome: ${d.customer?.name || 'não informado'}`);
  if (d.customer?.phone) L.push(`Telefone: ${d.customer.phone}`);

  L.push('', '## Solicitação');
  L.push(`Resumo: ${d.summary || '—'}`);
  L.push(`Próximo passo: ${d.recommended_next_step || '—'}`);

  L.push('', '## Corredor');
  L.push(`Seguradora: ${capitalize(d.corridor?.insurer_key)}`);
  L.push(`Ramo: ${lineKindLabel(d.corridor?.line_kind)}`);
  L.push(`Subcorredor: ${subcorridorLabel(d.corridor?.subcorridor_key) || '—'}`);
  L.push(`Fase: ${d.corridor?.run_phase || '—'}`);

  L.push('', '## Apólice');
  L.push(`Status: ${verificationLabel(d.policy?.verification_status)}`);
  L.push(`Origem: ${d.policy?.source || '—'}`);
  if (d.policy?.snapshot) {
    const s = d.policy.snapshot;
    L.push(`Seguradora/Produto: ${s.insurer_key || '—'} / ${s.product || '—'}`);
    if (s.masked_policy_number) L.push(`Nº (mascarado): ${s.masked_policy_number}`);
  }
  L.push('Atenção: não confirmar cobertura sem fonte.');

  if (d.coverage_readiness) {
    L.push('', '## Cobertura (readiness)');
    L.push(`Estado: ${d.coverage_readiness.state || '—'}`);
    L.push(`Validação humana necessária: ${d.coverage_readiness.human_required ? 'sim' : 'não'}`);
    if (d.coverage_readiness.message) L.push(`Resumo: ${d.coverage_readiness.message}`);
  }

  if (d.dispatch?.readiness) {
    const r = d.dispatch.readiness;
    L.push('', '## Acionamento (dispatch dry-run)');
    L.push(`Estado do pacote: ${r.packet_state || '—'}`);
    L.push(`Dispatch liberado: ${r.dispatch_allowed ? 'sim' : 'não'} (sempre dry-run/HITL neste MVP)`);
    if (Array.isArray(r.blockers) && r.blockers.length) L.push(`Bloqueios: ${r.blockers.join(', ')}`);
    if (Array.isArray(r.warnings) && r.warnings.length) L.push(`Avisos: ${r.warnings.join(', ')}`);
    if (d.dispatch.hitl_reason) L.push(`Motivo HITL: ${d.dispatch.hitl_reason}`);
    const hns: string[] = Array.isArray(d.dispatch.human_next_steps) ? d.dispatch.human_next_steps : [];
    if (hns.length) L.push(`Próximos passos humanos: ${hns.join('; ')}`);
    L.push('Nenhuma ação externa foi executada (external_action_sent=false).');
  }

  L.push('', '## Dados coletados');
  const filledKeys = Object.keys(d.slots?.filled || {});
  if (filledKeys.length === 0) {
    L.push('- (nenhum)');
  } else {
    for (const k of filledKeys) {
      const v = d.slots.filled[k];
      const val = typeof v === 'string' ? v : JSON.stringify(v);
      L.push(`- ${k}: ${String(val).slice(0, 160)}`);
    }
  }

  L.push('', '## Dados faltantes');
  const missing: string[] = Array.isArray(d.slots?.missing) ? d.slots.missing : [];
  if (missing.length === 0) L.push('- (nenhum)');
  else for (const k of missing) L.push(`- ${k}`);

  L.push('', '## Destino humano');
  const p = d.support_destination?.primary;
  if (p) {
    L.push(`${p.name} — ${destinationTypeLabel(p.destination_type)} — ${p.display_ref || 'destino configurado'}`);
  } else {
    L.push('Destino humano ainda não configurado.');
  }

  L.push('', '## Observação');
  L.push('Nenhuma ação externa foi executada automaticamente.');

  return L.join('\n');
}
