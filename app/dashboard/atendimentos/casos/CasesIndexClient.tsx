'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

import { DetailHeader, StatusPill } from '@/components/patterns';
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

type CaseRow = {
  id: string;
  case_number: string;
  status: string;
  priority: string;
  channel: string;
  customer_name: string | null;
  customer_phone: string | null;
  insurer_key: string | null;
  selected_subcorridor_key: string | null;
  verification_status: string | null;
  risk_level: string | null;
  summary: string | null;
  updated_at: string | null;
};

const TEST_PAYLOAD = {
  customer_name: 'Cliente Teste UI',
  customer_phone: '5547999999999',
  problem_description: 'Estou sem luz só na cozinha',
  channel: 'dashboard',
  priority: 'normal',
  selected_subcorridor_key: 'electrician',
  create_conversation: true,
};

export default function CasesIndexClient() {
  const [cases, setCases] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [subFilter, setSubFilter] = useState('all');
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState('');

  const load = async () => {
    setError(false);
    try {
      const res = await fetch('/api/attendance/cases?limit=100');
      if (!res.ok) throw new Error('fetch failed');
      const data = await res.json();
      setCases(data.cases || []);
    } catch {
      setError(true);
      setCases(null);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createTestCase = async () => {
    setCreating(true);
    setNotice('');
    try {
      const res = await fetch('/api/attendance/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(TEST_PAYLOAD),
      });
      if (!res.ok) throw new Error('create failed');
      setNotice('Caso de teste (sandbox) criado.');
      await load();
    } catch {
      setNotice('Não foi possível criar o caso de teste.');
    } finally {
      setCreating(false);
    }
  };

  const statusOptions = useMemo(() => {
    const set = new Set<string>();
    (cases || []).forEach((c) => c.status && set.add(c.status));
    return Array.from(set).sort();
  }, [cases]);

  const subOptions = useMemo(() => {
    const set = new Set<string>();
    (cases || []).forEach((c) => c.selected_subcorridor_key && set.add(c.selected_subcorridor_key));
    return Array.from(set).sort();
  }, [cases]);

  const q = query.trim().toLowerCase();
  const filtered = (cases || []).filter((c) => {
    if (statusFilter !== 'all' && c.status !== statusFilter) return false;
    if (subFilter !== 'all' && c.selected_subcorridor_key !== subFilter) return false;
    if (!q) return true;
    return [c.customer_name, c.customer_phone, c.case_number, c.summary, c.selected_subcorridor_key, c.status]
      .filter(Boolean)
      .some((v) => String(v).toLowerCase().includes(q));
  });

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-[1200px] space-y-5 px-4 py-8 sm:px-6">
        <DetailHeader
          icon={icons.casos}
          title="Casos"
          subtitle="Lista de atendimentos estruturados, auditoria e acesso rápido aos detalhes."
          breadcrumb={[{ label: 'Atendimentos', href: '/dashboard/atendimentos' }, { label: 'Casos' }]}
          status={{ tone: 'info', label: 'MVP ativo · sandbox' }}
          actions={
            <>
              <Link
                href="/dashboard/atendimentos/fila"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70"
              >
                <Icon icon={icons.fila} size={14} /> Ver fila
              </Link>
              <button
                onClick={createTestCase}
                disabled={creating}
                className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-primary/50 bg-brand-soft px-3 py-1.5 text-xs font-medium text-primary hover:bg-brand-soft/70 disabled:opacity-60"
              >
                <Icon icon={icons.novaConversa} size={14} /> {creating ? 'Criando…' : 'Criar caso teste'}
              </button>
              <button
                onClick={load}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70"
              >
                <Icon icon={icons.renovacao} size={14} /> Atualizar
              </button>
            </>
          }
        />

        {/* Toolbar: busca + filtros */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
              <Icon icon={icons.buscar} size={16} />
            </span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por cliente, telefone, protocolo, resumo, status ou subcorredor"
              className="w-full rounded-lg border border-border bg-background py-2.5 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground focus:border-primary/50 focus:outline-none"
          >
            <option value="all">Todos os status</option>
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {subOptions.length > 0 && (
            <select
              value={subFilter}
              onChange={(e) => setSubFilter(e.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground focus:border-primary/50 focus:outline-none"
            >
              <option value="all">Todos os subcorredores</option>
              {subOptions.map((s) => (
                <option key={s} value={s}>
                  {subcorridorLabel(s)}
                </option>
              ))}
            </select>
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

        {/* Estados */}
        {error ? (
          <div className="rounded-xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">
            Não foi possível carregar os casos.{' '}
            <button onClick={load} className="text-primary hover:underline">
              Tentar novamente
            </button>
            .
          </div>
        ) : cases === null ? (
          <div className="flex items-center justify-center gap-2 rounded-xl border border-border bg-card p-10 text-sm text-muted-foreground">
            <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando casos…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card p-12 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
              <Icon icon={icons.casos} size={18} />
            </span>
            <p className="text-sm font-medium text-foreground">
              {cases.length === 0
                ? 'Nenhum caso criado ainda. Crie um caso teste ou inicie um atendimento pela fila.'
                : 'Nenhum caso corresponde aos filtros.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full min-w-[820px] text-sm">
              <thead className="bg-surface-2/60 text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Segurado</th>
                  <th className="px-4 py-3 text-left font-medium">Protocolo</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-left font-medium">Prioridade</th>
                  <th className="px-4 py-3 text-left font-medium">Seguradora</th>
                  <th className="px-4 py-3 text-left font-medium">Apólice</th>
                  <th className="px-4 py-3 text-left font-medium">Atualizado</th>
                  <th className="px-4 py-3 text-right font-medium">Ação</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => {
                  const vp = verificationPill(c.verification_status);
                  const pri = priorityPill(c.priority);
                  const sub = subcorridorLabel(c.selected_subcorridor_key);
                  return (
                    <tr key={c.id} className="border-t border-border align-top">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{c.customer_name || 'Segurado não informado'}</p>
                        {c.summary && <p className="mt-0.5 line-clamp-1 max-w-[260px] text-xs text-muted-foreground">{c.summary}</p>}
                        <div className="mt-1 flex flex-wrap gap-1">
                          <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">Assistência</span>
                          {sub && <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">{sub}</span>}
                          {c.risk_level && c.risk_level !== 'low' && (
                            <StatusPill tone={riskTone(c.risk_level)} label={`Risco ${c.risk_level}`} />
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">{c.case_number}</td>
                      <td className="px-4 py-3">
                        <StatusPill tone={statusTone(c.status)} label={c.status} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill tone={pri.tone} label={pri.label} />
                      </td>
                      <td className="px-4 py-3 capitalize text-muted-foreground">{c.insurer_key || '—'}</td>
                      <td className="px-4 py-3">{vp ? <StatusPill tone={vp.tone} label={vp.label} /> : <span className="text-muted-foreground">—</span>}</td>
                      <td className="px-4 py-3 font-mono text-[11px] text-faint">{fmtDate(c.updated_at)}</td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/dashboard/atendimentos/casos/${c.id}`}
                          className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface-2 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-surface-2/70"
                        >
                          Abrir <Icon icon={icons.avancar} size={14} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
