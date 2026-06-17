'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';

import { DetailHeader, StatusPill, type StatusTone } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import {
  fmtDate,
  priorityPill,
  riskTone,
  statusTone,
  subcorridorLabel,
  verificationPill,
} from '@/lib/attendance/labels';
import HandoffDossierPanel from './HandoffDossierPanel';
import AttendanceConversationSimulator from './AttendanceConversationSimulator';

type Detail = {
  case?: any;
  conversation?: any;
  messages?: any[];
  corridor_run?: any;
  corridor_template?: any;
  dispatch_packets?: any[];
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-card p-4">
      <p className="mb-3 text-[11px] font-medium uppercase tracking-wide text-faint">{title}</p>
      {children}
    </section>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="max-w-[60%] text-right text-xs font-medium text-foreground">{value ?? '—'}</span>
    </div>
  );
}

export default function CaseDetailClient({ caseId }: { caseId: string }) {
  const [data, setData] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [acting, setActing] = useState(false);
  const [notice, setNotice] = useState('');
  const [insurerReply, setInsurerReply] = useState('');
  const [actionInterp, setActionInterp] = useState<any>(null);
  const [execSession, setExecSession] = useState<any>(null);
  const [outbox, setOutbox] = useState<any>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    setNotFound(false);
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}`);
      if (res.status === 404) {
        setNotFound(true);
        setData(null);
        return;
      }
      if (!res.ok) throw new Error('fetch failed');
      setData(await res.json());
    } catch {
      setError(true);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load]);

  const patchCase = async (patch: Record<string, unknown>, msg: string) => {
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error('patch failed');
      setNotice(msg);
      await load();
    } catch {
      setNotice('Não foi possível atualizar o caso.');
    } finally {
      setActing(false);
    }
  };

  const runDispatchDryRun = async () => {
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/dispatch-dry-run`, { method: 'POST' });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) {
        setNotice(`Pacote de acionamento (dry-run) preparado: ${json.dispatch_packet?.status || 'rascunho'}. Nenhuma ação externa foi executada.`);
      } else {
        setNotice(`Não foi possível preparar o pacote: ${json?.error || 'erro'}.`);
      }
      await load();
    } catch {
      setNotice('Falha ao preparar o pacote de acionamento.');
    } finally {
      setActing(false);
    }
  };

  const coverageDecision = async (decision: 'approved' | 'rejected' | 'needs_more_info') => {
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/coverage-validation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, source: 'human' }),
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) {
        setNotice(`Decisão de cobertura registrada: ${json.coverage_validation?.state || decision}. Sem ação externa.`);
      } else {
        setNotice(`Não foi possível registrar a decisão: ${json?.error || 'erro'}.`);
      }
      await load();
    } catch {
      setNotice('Falha ao registrar a decisão de cobertura.');
    } finally {
      setActing(false);
    }
  };

  const generateActionPlan = async () => {
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/action-plan`, { method: 'POST' });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) setNotice(`Plano de acionamento (dry-run): ${json.action_plan?.status || '—'}. Nada foi enviado.`);
      else setNotice(`Não foi possível gerar o plano: ${json?.error || 'erro'}.`);
      await load();
    } catch {
      setNotice('Falha ao gerar o plano de acionamento.');
    } finally {
      setActing(false);
    }
  };

  const simulateInsurerReply = async () => {
    if (!insurerReply.trim()) return;
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/action-simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simulated_insurer_reply: insurerReply }),
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) setActionInterp(json.interpretation);
      else setNotice(`Não foi possível interpretar: ${json?.error || 'erro'}.`);
    } catch {
      setNotice('Falha ao interpretar a resposta simulada.');
    } finally {
      setActing(false);
    }
  };

  const startExecution = async () => {
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/action-execution/start`, { method: 'POST' });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) { setExecSession(json.execution); setNotice('Execução sandbox iniciada. Nada foi enviado.'); }
      else setNotice(`Não foi possível iniciar a execução: ${json?.error || 'erro'}.`);
    } catch {
      setNotice('Falha ao iniciar a execução sandbox.');
    } finally {
      setActing(false);
    }
  };

  const sendExecutionReply = async () => {
    if (!insurerReply.trim()) return;
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/action-execution/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: 'simulated_insurer_reply', text: insurerReply }),
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) setExecSession(json.execution);
      else setNotice(`Não foi possível processar o evento: ${json?.error || 'erro'}.`);
    } catch {
      setNotice('Falha ao processar o evento de execução.');
    } finally {
      setActing(false);
    }
  };

  const prepareOutbox = async () => {
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/action-outbox/prepare`, { method: 'POST' });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) { setOutbox(json); setNotice('Outbox preparado. Envio real bloqueado (sem flag/aprovação/canal homologado).'); }
      else setNotice(`Não foi possível preparar o outbox: ${json?.error || 'erro'}.`);
    } catch {
      setNotice('Falha ao preparar o outbox.');
    } finally {
      setActing(false);
    }
  };

  const approveOutbox = async () => {
    if (!outbox?.outbox_entry?.outbox_id) return;
    setActing(true);
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/action-outbox/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outbox_id: outbox.outbox_entry.outbox_id }),
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) { setOutbox((p: any) => ({ ...p, outbox_entry: json.outbox_entry, audit_events: json.audit_events })); setNotice('Aprovado (dry-run). Continua sem envio real.'); }
      else setNotice(`Não foi possível aprovar: ${json?.error || 'erro'}.`);
    } catch {
      setNotice('Falha ao aprovar o outbox.');
    } finally {
      setActing(false);
    }
  };

  // ---- Estados ----
  if (loading && !data) {
    return (
      <div className="mx-auto flex max-w-5xl items-center justify-center gap-2 px-4 py-20 text-sm text-muted-foreground">
        <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando caso…
      </div>
    );
  }
  if (notFound) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-20 text-center">
        <p className="text-sm font-medium text-foreground">Caso não encontrado.</p>
        <Link href="/dashboard/atendimentos/fila" className="mt-3 inline-block text-sm text-primary hover:underline">
          Voltar para a fila
        </Link>
      </div>
    );
  }
  if (error || !data?.case) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-20 text-center text-sm text-muted-foreground">
        Não foi possível carregar o caso.{' '}
        <button onClick={load} className="text-primary hover:underline">
          Tentar novamente
        </button>
      </div>
    );
  }

  const c = data.case;
  const run = data.corridor_run || null;
  const tpl = data.corridor_template || null;
  const messages = Array.isArray(data.messages) ? data.messages : [];
  const packets = Array.isArray(data.dispatch_packets) ? data.dispatch_packets : [];
  const diag = (run?.diagnostics || {}) as Record<string, any>;
  const slots = (run?.slots || {}) as { filled?: Record<string, unknown>; missing?: string[]; conflicts?: unknown[] };
  const filledKeys = Object.keys(slots.filled || {});
  const missing = Array.isArray(slots.missing) ? slots.missing : [];
  const conflicts = Array.isArray(slots.conflicts) ? slots.conflicts : [];

  const vp = verificationPill(c.verification_status);
  const pri = priorityPill(c.priority);
  const hasCoverageEvidence = c.coverage_evidence && typeof c.coverage_evidence === 'object' && Object.keys(c.coverage_evidence).length > 0;
  const externalAllowed = diag.external_action_allowed === true;
  // 42B6: dispatch readiness + coverage readiness (do metadata).
  const coverageReadiness: any = c.metadata?.coverage_readiness || null;
  const dispatchReadiness: any = c.metadata?.dispatch_readiness || null;
  const actionPlan: any = c.metadata?.external_action_plan || null;
  const dispatchStateLabel: Record<string, string> = {
    incomplete: 'Incompleto — coletar dados',
    blocked: 'Bloqueado — revisão humana',
    hitl_required: 'Validação humana necessária',
    ready_for_human_approval: 'Pronto para aprovação humana',
  };
  const dispatchStateTone: Record<string, StatusTone> = {
    incomplete: 'warning',
    blocked: 'danger',
    hitl_required: 'warning',
    ready_for_human_approval: 'success',
  };
  const canValidateCoverage = Boolean(coverageReadiness) && !['handoff', 'closed', 'cancelled'].includes(c.status);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 sm:px-6">
        <DetailHeader
          icon={icons.casos}
          title={c.customer_name || 'Segurado não informado'}
          subtitle={`${c.case_number} · sandbox / dry-run`}
          breadcrumb={[
            { label: 'Atendimentos', href: '/dashboard/atendimentos' },
            { label: 'Fila', href: '/dashboard/atendimentos/fila' },
            { label: 'Caso' },
          ]}
          status={{ tone: statusTone(c.status), label: c.status }}
          actions={
            <>
              <Link
                href="/dashboard/atendimentos/fila"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70"
              >
                <Icon icon={icons.voltar} size={14} /> Voltar para fila
              </Link>
              <button
                onClick={load}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70"
              >
                <Icon icon={icons.renovacao} size={14} /> Atualizar
              </button>
            </>
          }
        />

        <div className="flex flex-wrap items-center gap-1.5">
          <StatusPill tone="info" label="Sandbox / dry-run" />
          {vp && <StatusPill tone={vp.tone} label={vp.label} />}
          <StatusPill tone={pri.tone} label={pri.label} />
          {c.risk_level && c.risk_level !== 'low' && (
            <StatusPill tone={riskTone(c.risk_level)} label={`Risco ${c.risk_level}`} />
          )}
          {subcorridorLabel(c.selected_subcorridor_key) && (
            <StatusPill tone="neutral" label={subcorridorLabel(c.selected_subcorridor_key) as string} />
          )}
        </div>

        {notice && (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
            <span>{notice}</span>
            <button onClick={() => setNotice('')} className="text-muted-foreground hover:text-foreground">
              <Icon icon={icons.negado} size={14} />
            </button>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-3">
          {/* ===== Coluna principal ===== */}
          <div className="space-y-4 lg:col-span-2">
            {/* Simulador de conversa (42B5J) */}
            <AttendanceConversationSimulator caseId={caseId} onChanged={load} />

            {/* Resumo */}
            <Section title="Resumo do caso">
              {c.summary && <p className="mb-2 text-sm text-foreground">{c.summary}</p>}
              {c.next_step && (
                <p className="mb-3 rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">Próximo passo: </span>
                  {c.next_step}
                </p>
              )}
              <Field label="Intenção" value={c.intent} />
              <Field label="Canal" value={c.channel} />
              <Field label="Seguradora" value={c.insurer_key} />
              <Field label="Macroserviço" value={c.macro_service} />
              <Field label="Apólice" value={c.verification_status} />
              <Field label="Risco" value={c.risk_level} />
            </Section>

            {/* Conversa */}
            <Section title="Conversa">
              {messages.length === 0 ? (
                <p className="text-xs text-muted-foreground">Ainda não há mensagens espelhadas neste caso.</p>
              ) : (
                <ul className="space-y-2">
                  {messages.map((m: any) => (
                    <li key={m.id} className="rounded-lg border border-border bg-surface-2 px-3 py-2">
                      <div className="mb-0.5 flex items-center justify-between">
                        <span className="font-mono text-[10px] uppercase text-muted-foreground">
                          {m.role === 'user' ? 'cliente' : 'agente'}
                        </span>
                        <span className="font-mono text-[10px] text-faint">{fmtDate(m.created_at)}</span>
                      </div>
                      <p className="text-xs text-foreground">{m.content}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            {/* Slots */}
            <Section title="Dados do corredor (slots)">
              <p className="mb-1.5 text-[11px] text-muted-foreground">Coletados ({filledKeys.length})</p>
              <div className="mb-3 flex flex-wrap gap-1.5">
                {filledKeys.length === 0 ? (
                  <span className="text-xs text-faint">Nenhum dado coletado ainda.</span>
                ) : (
                  filledKeys.map((k) => (
                    <span key={k} className="rounded-full border border-success/40 px-2 py-0.5 text-[10px] text-success">
                      {k}
                    </span>
                  ))
                )}
              </div>
              <p className="mb-1.5 text-[11px] text-muted-foreground">Faltantes ({missing.length}) — pendência</p>
              <div className="flex flex-wrap gap-1.5">
                {missing.length === 0 ? (
                  <span className="text-xs text-faint">Sem pendências.</span>
                ) : (
                  missing.map((k: string) => (
                    <span key={k} className="rounded-full border border-warning/40 px-2 py-0.5 text-[10px] text-warning">
                      {k}
                    </span>
                  ))
                )}
              </div>
              {conflicts.length > 0 && (
                <p className="mt-3 text-[11px] text-danger">Conflitos: {conflicts.length}</p>
              )}
            </Section>

            {/* Apólice e evidência */}
            <Section title="Apólice e evidência">
              <Field label="Origem" value={c.policy_source} />
              {c.policy_number && <Field label="Número" value={c.policy_number} />}
              <Field label="Verificação" value={c.verification_status} />
              <Field label="Evidência" value={hasCoverageEvidence ? 'Evidência registrada' : 'Sem evidência'} />
              {c.verification_status === 'unverified' && (
                <p className="mt-2 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-[11px] text-warning">
                  Sem evidência de apólice verificada ainda. Não confirmar cobertura sem fonte.
                </p>
              )}
            </Section>

            {/* Dispatch packets */}
            <Section title="Pacotes de acionamento (dispatch)">
              {packets.length === 0 ? (
                <p className="text-xs text-muted-foreground">Nenhum pacote de acionamento criado ainda.</p>
              ) : (
                <ul className="space-y-1.5">
                  {packets.map((p: any) => (
                    <li key={p.id} className="flex items-center justify-between rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs">
                      <span className="text-foreground">{p.channel || p.provider || 'pacote'}</span>
                      <StatusPill tone="neutral" label={p.status} />
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-[10px] text-faint">Nenhuma ação externa foi executada neste caso.</p>
            </Section>

            {/* Readiness de acionamento (42B6) */}
            <Section title="Readiness de acionamento (dry-run / HITL)">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <button
                  onClick={runDispatchDryRun}
                  disabled={acting}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
                >
                  <Icon icon={icons.avancar} size={14} /> Preparar dispatch dry-run
                </button>
                {dispatchReadiness?.packet_state && (
                  <StatusPill
                    tone={dispatchStateTone[dispatchReadiness.packet_state] || 'neutral'}
                    label={dispatchStateLabel[dispatchReadiness.packet_state] || dispatchReadiness.packet_state}
                  />
                )}
              </div>

              {dispatchReadiness ? (
                <>
                  <Field label="Dispatch liberado" value={dispatchReadiness.dispatch_allowed ? 'sim (ainda HITL)' : 'não'} />
                  <Field label="Validação humana" value={dispatchReadiness.hitl_required ? 'necessária' : 'não'} />
                  {Array.isArray(dispatchReadiness.blockers) && dispatchReadiness.blockers.length > 0 && (
                    <div className="mt-2">
                      <p className="mb-1 text-[11px] text-danger">Bloqueios</p>
                      <div className="flex flex-wrap gap-1.5">
                        {dispatchReadiness.blockers.map((b: string) => (
                          <span key={b} className="rounded-full border border-danger/40 px-2 py-0.5 text-[10px] text-danger">{b}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(dispatchReadiness.warnings) && dispatchReadiness.warnings.length > 0 && (
                    <div className="mt-2">
                      <p className="mb-1 text-[11px] text-warning">Avisos</p>
                      <div className="flex flex-wrap gap-1.5">
                        {dispatchReadiness.warnings.map((w: string) => (
                          <span key={w} className="rounded-full border border-warning/40 px-2 py-0.5 text-[10px] text-warning">{w}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-xs text-muted-foreground">Nenhum pacote dry-run preparado ainda.</p>
              )}

              {/* HITL de cobertura */}
              {canValidateCoverage && (
                <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3">
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">Validação humana de cobertura</p>
                  {coverageReadiness?.message && (
                    <p className="mb-2 text-[11px] text-muted-foreground">{coverageReadiness.message}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => coverageDecision('approved')}
                      disabled={acting}
                      className="rounded-lg border border-success/40 bg-success/5 px-3 py-1.5 text-xs font-medium text-success hover:bg-success/10 disabled:opacity-60"
                    >
                      Aprovar cobertura
                    </button>
                    <button
                      onClick={() => coverageDecision('rejected')}
                      disabled={acting}
                      className="rounded-lg border border-danger/40 bg-danger/5 px-3 py-1.5 text-xs font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                    >
                      Reprovar
                    </button>
                    <button
                      onClick={() => coverageDecision('needs_more_info')}
                      disabled={acting}
                      className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
                    >
                      Solicitar mais informação
                    </button>
                  </div>
                </div>
              )}
              <p className="mt-3 text-[10px] text-faint">
                Modo dry-run/HITL: nenhum envio para seguradora/prestador. Acionamento real exige homologação futura.
              </p>
            </Section>

            {/* Action Engine — plano de acionamento externo (dry-run, 42X0) */}
            <Section title="Plano de acionamento externo (dry-run)">
              <button
                onClick={generateActionPlan}
                disabled={acting}
                className="mb-3 inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
              >
                <Icon icon={icons.avancar} size={14} /> Gerar plano de acionamento
              </button>
              {actionPlan ? (
                <>
                  <Field label="Status" value={actionPlan.status} />
                  <Field label="Canal recomendado" value={actionPlan.selected_channel} />
                  {actionPlan.selected_provider_key && (
                    <Field label="Provider (config)" value={`${actionPlan.selected_provider_label || actionPlan.selected_provider_key} · ${actionPlan.selected_destination_ref_masked || '—'} · ${actionPlan.selected_homologation_status || '—'}`} />
                  )}
                  <Field label="Origem do canal" value={actionPlan.channel_config_source || 'none'} />
                  <Field label="Validação humana" value={actionPlan.human_review_required ? 'necessária' : 'não'} />
                  <Field label="Envio externo" value="bloqueado (dry-run, sent=false)" />
                  {Array.isArray(actionPlan.missing_data) && actionPlan.missing_data.length > 0 && (
                    <div className="mt-2">
                      <p className="mb-1 text-[11px] text-warning">Dados faltantes</p>
                      <div className="flex flex-wrap gap-1.5">
                        {actionPlan.missing_data.map((m: string) => (
                          <span key={m} className="rounded-full border border-warning/40 px-2 py-0.5 text-[10px] text-warning">{m}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(actionPlan.message_drafts) && actionPlan.message_drafts.length > 0 && (
                    <div className="mt-2">
                      <p className="mb-1 text-[11px] text-muted-foreground">Mensagem (draft) para a seguradora — não enviada</p>
                      <p className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-[11px] text-foreground">{actionPlan.message_drafts[0].text}</p>
                    </div>
                  )}
                  <div className="mt-3">
                    <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">Simular resposta da seguradora</p>
                    <textarea
                      value={insurerReply}
                      onChange={(e) => setInsurerReply(e.target.value)}
                      rows={2}
                      placeholder="Cole aqui uma resposta simulada da seguradora…"
                      className="min-h-[40px] w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-faint focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      onClick={simulateInsurerReply}
                      disabled={acting || !insurerReply.trim()}
                      className="mt-1.5 inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
                    >
                      Interpretar resposta (dry-run)
                    </button>
                    {actionInterp && (
                      <div className="mt-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-[11px]">
                        <p className="text-foreground"><span className="text-muted-foreground">Classificação:</span> {actionInterp.classification}</p>
                        <p className="text-foreground"><span className="text-muted-foreground">Próximo passo:</span> {actionInterp.next_step}</p>
                        {actionInterp.customer_message && <p className="mt-1 text-muted-foreground">{actionInterp.customer_message}</p>}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-xs text-muted-foreground">Nenhum plano gerado ainda.</p>
              )}
              {/* Execução sandbox (42X1) */}
              {actionPlan?.status === 'ready_for_human_approval' && (
                <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-faint">Execução (sandbox)</p>
                    <button
                      onClick={startExecution}
                      disabled={acting}
                      className="rounded-lg border border-primary/40 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
                    >
                      Iniciar execução sandbox
                    </button>
                    {execSession?.status && <StatusPill tone="info" label={execSession.status} />}
                  </div>
                  {execSession ? (
                    <>
                      <p className="text-[11px] text-muted-foreground">Canal: <span className="text-foreground">{execSession.channel}</span> · adapter: {execSession.adapter} · envio: <span className="text-foreground">bloqueado (sandbox)</span></p>
                      {execSession.prepared_message && (
                        <p className="mt-1 rounded-lg border border-border bg-card px-3 py-2 text-[11px] text-foreground">{execSession.prepared_message}</p>
                      )}
                      {execSession.customer_update && (
                        <p className="mt-1 text-[11px] text-muted-foreground">Cliente: {execSession.customer_update}</p>
                      )}
                      <div className="mt-2 flex items-end gap-2">
                        <textarea
                          value={insurerReply}
                          onChange={(e) => setInsurerReply(e.target.value)}
                          rows={2}
                          placeholder="Resposta simulada da seguradora (alimenta a execução)…"
                          className="min-h-[36px] flex-1 resize-y rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-faint focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                        <button
                          onClick={sendExecutionReply}
                          disabled={acting || !insurerReply.trim() || ['completed_sandbox', 'cancelled', 'failed_sandbox'].includes(execSession.status)}
                          className="shrink-0 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
                        >
                          Enviar à execução
                        </button>
                      </div>
                      {Array.isArray(execSession.events) && execSession.events.length > 0 && (
                        <div className="mt-2">
                          <p className="mb-1 text-[10px] uppercase tracking-wide text-faint">Timeline</p>
                          <ul className="space-y-1">
                            {execSession.events.slice(-8).map((ev: any, i: number) => (
                              <li key={i} className="text-[10px] text-muted-foreground">
                                {ev.type}{ev.classification ? ` · ${ev.classification}` : ''}{ev.note ? ` — ${ev.note}` : ''}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">Sessão de execução não iniciada.</p>
                  )}
                </div>
              )}
              {/* Outbox & gates de permissão (42X2) */}
              {actionPlan?.status === 'ready_for_human_approval' && (
                <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-faint">Outbox & permissão (envio real bloqueado)</p>
                    <button
                      onClick={prepareOutbox}
                      disabled={acting}
                      className="rounded-lg border border-primary/40 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
                    >
                      Preparar outbox
                    </button>
                    <button
                      onClick={approveOutbox}
                      disabled={acting || !outbox?.outbox_entry || outbox?.outbox_entry?.status !== 'awaiting_approval'}
                      className="rounded-lg border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
                    >
                      Aprovar (dry-run)
                    </button>
                    {outbox?.outbox_entry?.status && <StatusPill tone="warning" label={outbox.outbox_entry.status} />}
                  </div>
                  {outbox?.outbox_entry ? (
                    <>
                      <p className="text-[11px] text-muted-foreground">
                        Canal: <span className="text-foreground">{outbox.outbox_entry.channel}</span> · provider: {outbox.outbox_entry.provider ?? '—'} · destino: {outbox.outbox_entry.destination_ref_masked ?? '—'} · envio real: <span className="font-medium text-amber-600">bloqueado</span>
                      </p>
                      {Array.isArray(outbox.outbox_entry.blockers) && outbox.outbox_entry.blockers.length > 0 && (
                        <p className="mt-1 text-[10px] text-muted-foreground">Blockers: {outbox.outbox_entry.blockers.join(', ')}</p>
                      )}
                      {Array.isArray(outbox.permission?.blockers) && outbox.permission.blockers.length > 0 && (
                        <p className="mt-1 text-[10px] text-muted-foreground">Gates pendentes: {outbox.permission.blockers.join(', ')}</p>
                      )}
                      {Array.isArray(outbox.warnings) && outbox.warnings.includes('channel_plan_outbox_mismatch') && (
                        <p className="mt-1 text-[10px] font-medium text-warning">⚠ Divergência plano↔outbox de canal (channel_plan_outbox_mismatch)</p>
                      )}
                      {Array.isArray(outbox.audit_events) && outbox.audit_events.length > 0 && (
                        <div className="mt-2">
                          <p className="mb-1 text-[10px] uppercase tracking-wide text-faint">Auditoria</p>
                          <ul className="space-y-1">
                            {outbox.audit_events.slice(-6).map((ev: any, i: number) => (
                              <li key={i} className="text-[10px] text-muted-foreground">{ev.type}{ev.note ? ` — ${ev.note}` : ''}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">Outbox não preparado.</p>
                  )}
                </div>
              )}
              <p className="mt-3 text-[10px] text-faint">Modo dry-run/HITL/sandbox/outbox: nada é enviado à seguradora/prestador. O envio real exige flag global, tenant_connection homologada, aprovação humana e adapter homologado (42X3+).</p>
            </Section>

            {/* Dossiê / Handoff humano */}
            <HandoffDossierPanel
              caseId={caseId}
              autoLoad={Boolean(c.handoff_required) || c.status === 'handoff'}
            />
          </div>

          {/* ===== Coluna lateral ===== */}
          <div className="space-y-4">
            {/* Corredor */}
            <Section title="Corredor">
              <Field label="Template" value={tpl?.display_name} />
              <Field label="Readiness" value={tpl?.readiness} />
              <Field label="Fases" value={Array.isArray(tpl?.phases) ? tpl.phases.length : '—'} />
              <Field label="Guardrails" value={Array.isArray(tpl?.guardrails) ? tpl.guardrails.length : '—'} />
              <Field label="Golden tests" value={Array.isArray(tpl?.golden_tests) ? tpl.golden_tests.length : '—'} />
            </Section>

            {/* Diagnóstico */}
            <Section title="Diagnóstico">
              <Field label="Fase" value={run?.phase} />
              <Field label="Status do run" value={run?.status} />
              <Field label="Modo" value={diag.mvp_mode || '—'} />
              <Field label="HITL necessário" value={diag.hitl_required ? 'sim' : 'não'} />
              <Field label="Ação externa" value={externalAllowed ? 'permitida' : 'bloqueada'} />
            </Section>

            {/* Autonomia */}
            <Section title="Autonomia do atendimento">
              {diag.autonomy_level ? (
                <Field label="Nível" value={diag.autonomy_level} />
              ) : (
                <>
                  <p className="text-xs text-foreground">Modo atual: <span className="font-medium">Sandbox / dry-run</span></p>
                  <p className="mt-1 text-xs text-muted-foreground">Ação externa automática: <span className="text-warning">bloqueada neste MVP</span>.</p>
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    Visão final: autonomia permitida quando corredor, fonte, canal e readiness estiverem homologados.
                  </p>
                </>
              )}
            </Section>

            {/* Handoff humano */}
            <Section title="Handoff humano">
              <Field label="Necessário" value={c.handoff_required ? 'sim' : 'não'} />
              {c.handoff_reason && <Field label="Motivo" value={c.handoff_reason} />}
              <p className="mt-2 text-[11px] text-muted-foreground">
                Configuração de suporte humano será conectada em batch futuro. Quando o agente não conseguir resolver,
                ele deve montar dossiê e transferir para o humano configurado.
              </p>
            </Section>

            {/* Ações seguras MVP */}
            <Section title="Ações seguras (MVP)">
              <div className="space-y-2">
                <button
                  onClick={() =>
                    patchCase(
                      {
                        status: 'handoff',
                        handoff_required: true,
                        handoff_reason: 'manual_review',
                        next_step: 'Caso marcado para revisão humana. Preparar dossiê para transferência.',
                      },
                      'Caso marcado para handoff humano.',
                    )
                  }
                  disabled={acting}
                  className="w-full rounded-lg border border-warning/40 bg-warning/5 px-3 py-2 text-left text-xs font-medium text-warning hover:bg-warning/10 disabled:opacity-60"
                >
                  Marcar como handoff
                </button>
                <button
                  onClick={() => patchCase({ priority: 'high' }, 'Prioridade definida como alta.')}
                  disabled={acting}
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-left text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
                >
                  Marcar prioridade alta
                </button>
                <button
                  onClick={() =>
                    patchCase(
                      { status: 'closed', next_step: 'Caso encerrado manualmente em modo sandbox.' },
                      'Caso encerrado (sandbox).',
                    )
                  }
                  disabled={acting}
                  className="w-full rounded-lg border border-success/40 bg-success/5 px-3 py-2 text-left text-xs font-medium text-success hover:bg-success/10 disabled:opacity-60"
                >
                  Encerrar caso
                </button>
                <button
                  onClick={() =>
                    patchCase(
                      {
                        status: 'collecting_slots',
                        handoff_required: false,
                        handoff_reason: null,
                        next_step:
                          'Coletar dados mínimos e validar apólice antes de qualquer acionamento externo.',
                      },
                      'Caso reaberto para coleta de dados.',
                    )
                  }
                  disabled={acting}
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-left text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
                >
                  Reabrir / coletar dados
                </button>
              </div>
              <p className="mt-2 text-[10px] text-faint">
                Ações alteram apenas o estado do caso. Nenhuma mensagem ou acionamento externo é enviado.
              </p>
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}
