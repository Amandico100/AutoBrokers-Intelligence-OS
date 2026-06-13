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

            {/* Dossiê / Handoff humano */}
            <Section title="Dossiê / Handoff humano">
              <Field label="Handoff necessário" value={c.handoff_required ? 'sim' : 'não'} />
              {c.handoff_reason && <Field label="Motivo" value={c.handoff_reason} />}
              <div className="mt-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
                <p className="mb-1 font-medium text-foreground">Resumo para o humano</p>
                <p>{c.summary || '—'}</p>
                <p className="mt-2"><span className="font-medium text-foreground">Coletados:</span> {filledKeys.length} · <span className="font-medium text-foreground">Faltantes:</span> {missing.length}</p>
                <p className="mt-1"><span className="font-medium text-foreground">Próximo passo:</span> {c.next_step || '—'}</p>
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Destino humano: <span className="text-foreground">ainda não conectado neste MVP</span>. Quando o agente
                não conseguir resolver, ele deve montar este dossiê e transferir para o humano configurado.
              </p>
            </Section>
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
