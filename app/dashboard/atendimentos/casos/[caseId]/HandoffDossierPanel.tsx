'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';

import { StatusPill, type StatusTone } from '@/components/patterns';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { destinationTypeLabel } from '@/lib/attendance/support-destination-labels';

type DossierState = any;

function badgeFor(dossier: DossierState, error: boolean): { tone: StatusTone; label: string } {
  if (error) return { tone: 'danger', label: 'Erro' };
  if (!dossier) return { tone: 'neutral', label: 'Não gerado' };
  if (!dossier.support_destination?.configured) return { tone: 'warning', label: 'Sem destino humano' };
  return { tone: 'success', label: 'Pronto para copiar' };
}

export default function HandoffDossierPanel({ caseId, autoLoad }: { caseId: string; autoLoad?: boolean }) {
  const [dossier, setDossier] = useState<DossierState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetch(`/api/attendance/cases/${caseId}/handoff-dossier`);
      if (!res.ok) throw new Error('failed');
      const data = await res.json();
      setDossier(data.dossier || null);
    } catch {
      setError(true);
      setDossier(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (autoLoad) load();
  }, [autoLoad, load]);

  const copy = async () => {
    if (!dossier?.markdown) return;
    const text = dossier.markdown as string;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      } catch {
        setCopied(false);
      }
    }
  };

  const badge = badgeFor(dossier, error);
  const primary = dossier?.support_destination?.primary || null;
  const configured = Boolean(dossier?.support_destination?.configured);
  const filledCount = dossier ? Object.keys(dossier.slots?.filled || {}).length : 0;
  const missingCount = dossier ? (Array.isArray(dossier.slots?.missing) ? dossier.slots.missing.length : 0) : 0;

  return (
    <section className="rounded-xl border border-border bg-card p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-faint">Dossiê / Handoff humano</p>
          <StatusPill tone={badge.tone} label={badge.label} />
        </div>
        <div className="flex items-center gap-1.5">
          {!dossier ? (
            <button
              onClick={load}
              disabled={loading}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {loading ? 'Gerando…' : 'Gerar dossiê'}
            </button>
          ) : (
            <>
              <button
                onClick={load}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-2/70 disabled:opacity-60"
              >
                <Icon icon={icons.renovacao} size={14} /> {loading ? 'Atualizando…' : 'Atualizar dossiê'}
              </button>
              <button
                onClick={copy}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
              >
                {copied ? 'Dossiê copiado' : 'Copiar dossiê'}
              </button>
            </>
          )}
        </div>
      </div>

      <p className="mb-3 text-xs text-muted-foreground">
        Use este dossiê quando o agente precisar transferir o atendimento para um humano. Neste MVP, nenhuma mensagem é
        enviada automaticamente.
      </p>

      {error ? (
        <p className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
          Não foi possível gerar o dossiê.{' '}
          <button onClick={load} className="underline">
            Tentar novamente
          </button>
          .
        </p>
      ) : loading && !dossier ? (
        <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Icon icon={icons.renovacao} size={16} className="animate-spin" /> Gerando dossiê…
        </div>
      ) : !dossier ? (
        <p className="text-xs text-muted-foreground">Clique em “Gerar dossiê” para montar o pacote de transferência.</p>
      ) : (
        <div className="space-y-3">
          {/* Resumo visual */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <Mini label="Status" value={dossier.status?.case_status} />
            <Mini label="Prioridade" value={dossier.status?.priority} />
            <Mini label="Risco" value={dossier.status?.risk_level} />
            <Mini label="Coletados" value={String(filledCount)} />
            <Mini label="Faltantes" value={String(missingCount)} />
            <Mini label="Mensagens" value={String(dossier.messages?.message_count ?? 0)} />
          </div>

          {/* Destino humano */}
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs">
            {configured && primary ? (
              <p className="text-foreground">
                Destino configurado: <span className="font-medium">{primary.name}</span> —{' '}
                {destinationTypeLabel(primary.destination_type)} —{' '}
                <span className="font-mono">{primary.display_ref || 'destino configurado'}</span>
              </p>
            ) : (
              <p className="text-warning">
                Destino humano ainda não configurado. Configure em{' '}
                <Link href="/dashboard/personalizacao/corretora/suporte-humano" className="underline">
                  Personalização → Corretora → Suporte humano
                </Link>
                .
              </p>
            )}
          </div>

          {/* Markdown copiável */}
          <pre className="max-h-[360px] overflow-auto rounded-lg border border-border bg-background p-3 font-mono text-[11px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
            {dossier.markdown}
          </pre>

          {/* Aviso fixo */}
          <p className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-[11px] text-warning">
            Nenhuma ação externa foi executada. Copiar este dossiê não envia mensagem para o segurado, seguradora ou
            suporte humano.
          </p>
        </div>
      )}
    </section>
  );
}

function Mini({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 px-2.5 py-1.5">
      <p className="text-[10px] uppercase tracking-wide text-faint">{label}</p>
      <p className="text-xs font-medium text-foreground">{value ?? '—'}</p>
    </div>
  );
}
