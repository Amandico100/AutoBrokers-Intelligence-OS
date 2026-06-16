'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { StatusPill } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { fmtDate, statusTone, priorityPill, riskTone, verificationPill } from '@/lib/attendance/labels';

const MOCK_FIXTURE = 'allianz_residential_electrician_covered';

type Busy = 'reply' | 'step' | 'lookup' | 'infocap' | 'select' | 'reload' | null;

/**
 * Simulador de conversa do atendimento (42B5J).
 * Permite testar o runtime E2E pelo dashboard, sem WhatsApp real e sem ação externa.
 * Consome: GET /api/attendance/cases/[caseId], runtime/reply, runtime/step, runtime/policy-lookup.
 */
export default function AttendanceConversationSimulator({
  caseId,
  onChanged,
}: {
  caseId: string;
  onChanged?: () => void;
}) {
  const [data, setData] = useState<{ case?: any; messages?: any[]; corridor_run?: any } | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const listRef = useRef<HTMLDivElement>(null);

  const reload = useCallback(
    async (silent = false) => {
      if (!silent) setBusy('reload');
      try {
        const res = await fetch(`/api/attendance/cases/${caseId}`);
        if (!res.ok) throw new Error('fetch failed');
        const json = await res.json();
        setData({ case: json.case, messages: json.messages || [], corridor_run: json.corridor_run || null });
      } catch {
        setError('Não foi possível carregar a conversa.');
      } finally {
        if (!silent) setBusy(null);
      }
    },
    [caseId],
  );

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [data?.messages?.length]);

  const after = async () => {
    await reload(true);
    onChanged?.();
  };

  const sendReply = async () => {
    const message = input.trim();
    if (!message || busy) return;
    setBusy('reply');
    setError('');
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, source: 'dashboard' }),
      });
      if (res.status === 409) {
        setNotice('Este caso está em handoff/fechado/cancelado e não aceita novas mensagens pelo simulador.');
        return;
      }
      if (!res.ok) throw new Error('reply failed');
      setInput('');
      await after();
    } catch {
      setError('Falha ao enviar a mensagem para o runtime.');
    } finally {
      setBusy(null);
    }
  };

  const runStep = async () => {
    if (busy) return;
    setBusy('step');
    setError('');
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'dashboard' }),
      });
      if (res.status === 409) {
        setNotice('Caso em handoff/fechado/cancelado não pode ser avançado automaticamente.');
        return;
      }
      if (!res.ok) throw new Error('step failed');
      await after();
    } catch {
      setError('Falha ao rodar o próximo passo do agente.');
    } finally {
      setBusy(null);
    }
  };

  const runLookup = async () => {
    if (busy) return;
    setBusy('lookup');
    setError('');
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/policy-lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'mock', mode: 'mock', fixture: MOCK_FIXTURE }),
      });
      if (!res.ok) throw new Error('lookup failed');
      setNotice('Consulta de apólice (mock/manual) registrada. Use “Rodar próximo passo” para retomar o atendimento.');
      await after();
    } catch {
      setError('Falha ao simular a consulta de apólice.');
    } finally {
      setBusy(null);
    }
  };

  const runInfocapLookup = async () => {
    if (busy) return;
    setBusy('infocap');
    setError('');
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/policy-lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'infocap', mode: 'connector' }),
      });
      const json = await res.json().catch(() => ({}));
      const st = json?.policy_lookup_result?.status;
      if (st === 'found') setNotice('InfoCap: apólice localizada e evidência registrada.');
      else if (st === 'multiple_matches') setNotice('InfoCap: múltiplas apólices. Selecione uma abaixo.');
      else if (st === 'client_found') setNotice('InfoCap: cliente localizado, sem apólice vinculada retornada.');
      else setNotice(`InfoCap: ${st || 'sem resultado'}. Cobertura não confirmada.`);
      await after();
    } catch {
      setError('Falha ao consultar a InfoCap.');
    } finally {
      setBusy(null);
    }
  };

  const selectPolicy = async (policyRef: string) => {
    if (busy || !policyRef) return;
    setBusy('select');
    setError('');
    setNotice('');
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/runtime/policy-select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'infocap', policy_ref: policyRef }),
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json?.ok) {
        const conf = json?.policy_select_result?.confidence;
        setNotice(`Apólice selecionada e registrada (confiança: ${conf || '—'}). Use “Rodar próximo passo” para continuar.`);
      } else {
        setNotice(`Não foi possível registrar a apólice: ${json?.policy_select_result?.status || json?.error || 'erro'}.`);
      }
      await after();
    } catch {
      setError('Falha ao selecionar a apólice na InfoCap.');
    } finally {
      setBusy(null);
    }
  };

  const c = data?.case || {};
  const run = data?.corridor_run || null;
  const messages = Array.isArray(data?.messages) ? data!.messages! : [];
  const runtime = (run?.diagnostics?.runtime || {}) as Record<string, any>;
  const macroState: string | null = c.metadata?.attendance_macro_state || runtime.macro_state || null;
  const lastAgentAction: string | null = run?.last_agent_action || null;
  const selectedSlot: string | null = runtime.selected_slot || null;
  const hasEvidence =
    (c.coverage_evidence && typeof c.coverage_evidence === 'object' && Object.keys(c.coverage_evidence).length > 0) ||
    runtime.coverage_evidence_ready === true;

  const isLocked = ['handoff', 'closed', 'cancelled'].includes(c.status);
  const showLookup =
    !isLocked &&
    (macroState === 'policy_lookup_required' ||
      lastAgentAction === 'policy_lookup:pending' ||
      (c.verification_status === 'unverified' && Boolean(c.has_insured_document_ref)));
  // Apólices retornadas pela InfoCap (mascaradas) p/ seleção (42I3A).
  const infocapMatches: any[] = Array.isArray(c.metadata?.policy_lookup?.matches)
    ? c.metadata.policy_lookup.matches
    : [];
  const showPolicyOptions =
    !isLocked && macroState !== 'policy_evidence_ready' && infocapMatches.length > 0;

  const vp = verificationPill(c.verification_status);
  const pri = priorityPill(c.priority);

  return (
    <section className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon icon={icons.novaConversa} size={16} className="text-muted-foreground" />
          <p className="text-[11px] font-medium uppercase tracking-wide text-faint">Simulador de conversa</p>
          <StatusPill tone="info" label="MVP · sem WhatsApp real" />
        </div>
        <button
          onClick={() => reload()}
          disabled={Boolean(busy)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
        >
          <Icon icon={icons.renovacao} size={13} className={busy === 'reload' ? 'animate-spin' : ''} /> Atualizar
        </button>
      </div>

      {/* Resumo técnico enxuto */}
      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Mini label="Status" value={c.status} tone={statusTone(c.status)} />
        <Mini label="Macro estado" value={macroState} />
        <Mini label="Prioridade" value={pri?.label || c.priority} />
        <Mini label="Risco" value={c.risk_level} tone={c.risk_level && c.risk_level !== 'low' ? riskTone(c.risk_level) : undefined} />
        <Mini label="Verificação" value={vp?.label || c.verification_status} />
        <Mini label="Policy source" value={c.policy_source} />
        <Mini label="Slot atual" value={selectedSlot} />
        <Mini label="Última ação" value={lastAgentAction} />
        <Mini label="Evidência" value={hasEvidence ? 'pronta' : 'não'} />
      </div>

      {/* Próximo passo */}
      {c.next_step && (
        <p className="mb-3 rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Próximo passo: </span>
          {c.next_step}
        </p>
      )}

      {/* Alertas */}
      <div className="mb-3 space-y-1.5">
        {c.handoff_required && (
          <p className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-[11px] text-warning">
            Caso em handoff humano{c.handoff_reason ? ` (${c.handoff_reason})` : ''}.
          </p>
        )}
        {c.risk_level === 'high' && (
          <p className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-[11px] text-danger">
            Risco alto detectado — orientar segurança e priorizar atenção humana.
          </p>
        )}
        {c.verification_status === 'unverified' && (
          <p className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-[11px] text-muted-foreground">
            Apólice ainda não verificada. Não confirmar cobertura sem evidência.
          </p>
        )}
        {hasEvidence && (
          <p className="rounded-lg border border-success/30 bg-success/5 px-3 py-2 text-[11px] text-success">
            Evidência de apólice registrada.
          </p>
        )}
      </div>

      {/* Lista de mensagens */}
      <div
        ref={listRef}
        className="mb-3 max-h-[360px] space-y-2 overflow-y-auto rounded-lg border border-border bg-background p-3"
      >
        {messages.length === 0 ? (
          <p className="py-6 text-center text-xs text-faint">Nenhuma mensagem ainda. Envie uma mensagem como o segurado.</p>
        ) : (
          messages.map((m: any) => {
            const isUser = m.role === 'user';
            return (
              <div key={m.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-3 py-2 ${
                    isUser ? 'bg-primary text-primary-foreground' : 'border border-border bg-surface-2 text-foreground'
                  }`}
                >
                  <div className="mb-0.5 flex items-center gap-2">
                    <span className={`text-[10px] uppercase ${isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                      {isUser ? 'Cliente/Segurado' : 'Agente'}
                    </span>
                    <span className={`font-mono text-[10px] ${isUser ? 'text-primary-foreground/60' : 'text-faint'}`}>
                      {fmtDate(m.created_at)}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-xs">{m.content}</p>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Notices / erros */}
      {notice && (
        <p className="mb-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-[11px] text-muted-foreground">{notice}</p>
      )}
      {error && (
        <p className="mb-2 rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-[11px] text-danger">{error}</p>
      )}

      {/* Campo de entrada */}
      <div className="flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              sendReply();
            }
          }}
          rows={2}
          disabled={isLocked || Boolean(busy)}
          placeholder={isLocked ? 'Caso bloqueado para o simulador.' : 'Digite uma mensagem como se fosse o segurado…'}
          className="min-h-[40px] flex-1 resize-y rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-faint focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60"
        />
        <button
          onClick={sendReply}
          disabled={isLocked || !input.trim() || Boolean(busy)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
        >
          {busy === 'reply' ? <Icon icon={icons.renovacao} size={14} className="animate-spin" /> : <Icon icon={icons.novaConversa} size={14} />}
          Enviar como cliente
        </button>
      </div>

      {/* Ações do agente */}
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          onClick={runStep}
          disabled={isLocked || Boolean(busy)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
        >
          {busy === 'step' ? <Icon icon={icons.renovacao} size={14} className="animate-spin" /> : <Icon icon={icons.avancar} size={14} />}
          Rodar próximo passo do agente
        </button>
        {showLookup && (
          <button
            onClick={runLookup}
            disabled={Boolean(busy)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
          >
            {busy === 'lookup' ? <Icon icon={icons.renovacao} size={14} className="animate-spin" /> : <Icon icon={icons.buscar} size={14} />}
            Simular consulta de apólice (mock)
          </button>
        )}
        {showLookup && (
          <button
            onClick={runInfocapLookup}
            disabled={Boolean(busy)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
          >
            {busy === 'infocap' ? <Icon icon={icons.renovacao} size={14} className="animate-spin" /> : <Icon icon={icons.buscar} size={14} />}
            Consultar InfoCap (real)
          </button>
        )}
      </div>

      {/* Seleção de apólice (InfoCap multiple_matches) — MVP funcional */}
      {showPolicyOptions && (
        <div className="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-primary">
            Apólices encontradas na InfoCap — selecione uma
          </p>
          <div className="space-y-2">
            {infocapMatches.map((m: any, i: number) => (
              <div
                key={`${m.policy_ref}-${i}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2"
              >
                <div className="min-w-0 text-xs text-foreground">
                  <span className="font-medium">{m.insurer_key || 'Seguradora ?'}</span>
                  {m.product ? ` · ${m.product}` : ''}
                  {m.masked_policy_number ? ` · nº ${m.masked_policy_number}` : ''}
                  <div className="text-[10px] text-muted-foreground">
                    {m.policy_status || 'status ?'}
                    {m.valid_to ? ` · vence ${m.valid_to}` : ''}
                    {m.active_now === true ? ' · vigente' : m.active_now === false ? ' · não vigente' : ''}
                    {m.cancelled ? ' · cancelada' : ''}
                    {typeof m.coverages_count === 'number' ? ` · ${m.coverages_count} cobertura(s)` : ''}
                  </div>
                </div>
                <button
                  onClick={() => selectPolicy(String(m.policy_ref))}
                  disabled={Boolean(busy) || !m.policy_ref}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                >
                  {busy === 'select' ? <Icon icon={icons.renovacao} size={13} className="animate-spin" /> : <Icon icon={icons.check} size={13} />}
                  Selecionar
                </button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-faint">
            Selecionar carrega o detalhe da apólice (read-only) e registra a evidência. Nenhuma seguradora/prestador é acionada.
          </p>
        </div>
      )}

      <p className="mt-3 text-[10px] text-faint">
        Simulador MVP: nenhuma mensagem é enviada por WhatsApp. Nenhuma ação externa é executada automaticamente. A
        consulta de apólice é mock/manual (sem InfoCap real).
      </p>
    </section>
  );
}

function Mini({ label, value, tone }: { label: string; value?: string | null; tone?: any }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 px-2.5 py-1.5">
      <p className="text-[10px] uppercase tracking-wide text-faint">{label}</p>
      {tone ? (
        <span className="mt-0.5 inline-block">
          <StatusPill tone={tone} label={value || '—'} />
        </span>
      ) : (
        <p className="truncate text-xs font-medium text-foreground" title={value || undefined}>
          {value || '—'}
        </p>
      )}
    </div>
  );
}
