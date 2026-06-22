'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { Icon } from '@/components/ui/Icon';

type Item = {
  template_id: string; slug: string; name: string; description: string | null; category: string | null;
  runtime_kind: string; installed: boolean; status: string; last_run_at: string | null;
};

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  available: { label: 'Disponível', cls: 'border-border bg-surface-2 text-muted-foreground' },
  active: { label: 'Pronto', cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' },
  paused: { label: 'Pausado', cls: 'border-amber-500/30 bg-amber-500/10 text-amber-600' },
  awaiting_runtime: { label: 'Aguardando configuração', cls: 'border-amber-500/30 bg-amber-500/10 text-amber-600' },
  uninstalled: { label: 'Removido', cls: 'border-border bg-surface-2 text-faint' },
  error: { label: 'Erro', cls: 'border-red-500/30 bg-red-500/10 text-red-600' },
};
const DEEP_LINK: Record<string, string> = {
  'resumo-atendimentos': '/dashboard/auxiliares/galeria/resumo-atendimentos',
  'follow-up-whatsapp': '/dashboard/auxiliares/galeria/follow-up-whatsapp',
};

export default function MeusAuxiliaresPage() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    const j = await fetch('/api/dashboard/auxiliaries').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) setItems(j.items); else setNotice(j?.error || 'Falha ao carregar.');
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (templateId: string, action: 'install' | 'pause' | 'resume' | 'uninstall') => {
    setBusy(templateId + action); setNotice('');
    const r = await fetch(`/api/dashboard/auxiliaries/${templateId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) await load(); else setNotice(`Falha: ${j?.error || r.status}`);
    setBusy('');
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="Auxiliares"
          subtitle="Modelos prontos para a sua corretora. Instalar cria um motor isolado seu — nada é executado nem conectado automaticamente."
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Meus Auxiliares' }]}
        />
        {notice && <p className="text-[12px] text-amber-600">{notice}</p>}
        {items === null ? (
          <div className="flex items-center gap-2 py-10 text-sm text-muted-foreground"><Icon icon={icons.renovacao} size={16} className="animate-spin" /> Carregando…</div>
        ) : items.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">Nenhum Auxiliar disponível ainda.</p>
        ) : (
          <div className="space-y-3">
            {items.map((it) => {
              const meta = STATUS_LABEL[it.status] ?? STATUS_LABEL.available;
              const deep = DEEP_LINK[it.slug];
              return (
                <div key={it.template_id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">{it.name}</p>
                      {it.description && <p className="mt-0.5 text-[12px] text-muted-foreground">{it.description}</p>}
                      {it.category && <p className="mt-0.5 text-[11px] text-faint">{it.category}</p>}
                    </div>
                    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${meta.cls}`}>{meta.label}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {!it.installed && (
                      <button onClick={() => act(it.template_id, 'install')} disabled={!!busy} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Instalar</button>
                    )}
                    {it.installed && it.status === 'active' && (
                      <button onClick={() => act(it.template_id, 'pause')} disabled={!!busy} className="rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Pausar</button>
                    )}
                    {it.installed && it.status === 'paused' && (
                      <button onClick={() => act(it.template_id, 'resume')} disabled={!!busy} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Retomar</button>
                    )}
                    {it.installed && (
                      <button onClick={() => act(it.template_id, 'uninstall')} disabled={!!busy} className="rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Desinstalar</button>
                    )}
                    {deep && <Link href={deep} className="rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2">Abrir</Link>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <p className="text-[10px] text-faint">Instalar cria um motor (agente) isolado da sua corretora a partir do modelo. Não conecta provedores, não envia mensagens e não abre portais.</p>
      </div>
    </div>
  );
}
