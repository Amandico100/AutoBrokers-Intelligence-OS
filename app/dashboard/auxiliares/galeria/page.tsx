'use client';

// SPEC-019 C — Galeria de Rotinas Prontas: modelos que a corretora liga com um
// clique. "Usar modelo" abre a Nova rotina (motor F2) já preenchida.

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Loader2, Sparkles } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

type Missing = { key: string; label: string; href?: string };
type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  instructions: string;
  schedule_default: { kind?: string; time?: string; minutes?: number };
  delivery_default: { channel?: string };
  required: Record<string, boolean>;
  missing: Missing[];
};

function scheduleLabel(s: Template['schedule_default']) {
  if (s?.kind === 'interval') return `a cada ${s.minutes} min`;
  return `diária às ${s?.time || '08:00'}`;
}

export default function GaleriaRotinasProntasPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/routine-templates', { cache: 'no-store' });
      const j = await res.json();
      if (!res.ok) {
        setNotice(j.error || 'Erro ao carregar modelos.');
        setTemplates([]);
        return;
      }
      setTemplates(j.templates || []);
    } catch {
      setNotice('Falha de conexão.');
      setTemplates([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title="Rotinas prontas"
          subtitle="Modelos que a sua corretora liga com um clique. 'Usar modelo' abre a Nova rotina já preenchida — você ajusta o horário/destino e salva."
          breadcrumb={[{ label: 'Auxiliares', href: '/dashboard/auxiliares' }, { label: 'Rotinas prontas' }]}
        />

        {notice && <p className="text-sm text-danger">{notice}</p>}

        {templates === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando modelos…
          </div>
        ) : templates.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">Nenhum modelo disponível ainda</p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              Os modelos de rotina aparecem aqui. Você também pode criar do zero em{' '}
              <Link href="/dashboard/auxiliares/rotinas" className="text-primary underline">
                Rotinas
              </Link>
              .
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {templates.map((t) => (
              <div key={t.id} className="flex flex-col rounded-xl border border-border bg-surface p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">{t.name}</p>
                  <span className="shrink-0 rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
                    {t.category}
                  </span>
                </div>
                <p className="mt-1 flex-1 text-xs text-muted-foreground">{t.description}</p>
                <p className="mt-2 text-[11px] text-faint">
                  {scheduleLabel(t.schedule_default)} · entrega {t.delivery_default?.channel || 'histórico'}
                </p>
                {t.missing.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {t.missing.map((m) =>
                      m.href ? (
                        <Link
                          key={m.key}
                          href={m.href}
                          className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-600 hover:bg-amber-500/20"
                        >
                          Falta: {m.label} →
                        </Link>
                      ) : (
                        <span
                          key={m.key}
                          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-0.5 text-[11px] text-muted-foreground"
                        >
                          Falta: {m.label}
                        </span>
                      ),
                    )}
                  </div>
                )}
                <button
                  onClick={() => router.push(`/dashboard/auxiliares/rotinas?template=${t.id}`)}
                  className="mt-3 inline-flex items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  <Sparkles className="h-4 w-4" /> Usar modelo
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
