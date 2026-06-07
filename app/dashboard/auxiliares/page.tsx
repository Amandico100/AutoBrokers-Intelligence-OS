import Link from 'next/link';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Auxiliares · AutoBrokers' };

const areas = [
  { label: 'Meus Auxiliares', hint: 'Auxiliares ativados pela corretora' },
  { label: 'Galeria', hint: 'Modelos prontos para ativar' },
  { label: 'Execuções', hint: 'Histórico do que foi feito' },
];

export default function AuxiliaresPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-12">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icons.auxiliares} size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Auxiliares</h1>
            <p className="text-sm text-muted-foreground">Automações e rotinas da corretora.</p>
          </div>
        </div>

        <p className="mt-6 max-w-xl text-sm leading-relaxed text-foreground-2">
          Auxiliares são assistentes especializados em tarefas. O primeiro a entrar será o
          <span className="text-foreground"> Auxiliar de Resumo de Atendimentos</span>. Estamos preparando
          a navegação — sem agendamento e sem criação por prompt nesta fase.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          {areas.map((a) => (
            <div key={a.label} className="rounded-xl border border-border bg-surface p-4">
              <p className="text-sm font-medium text-foreground">{a.label}</p>
              <p className="mt-1 text-xs text-muted-foreground">{a.hint}</p>
              <span className="mt-3 inline-block rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
                em breve
              </span>
            </div>
          ))}
        </div>

        <div className="mt-8">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:border-primary/40"
          >
            <Icon icon={icons.autobrokers} size={16} className="text-primary" />
            Abrir o AutoBrokers
          </Link>
        </div>
      </div>
    </div>
  );
}
