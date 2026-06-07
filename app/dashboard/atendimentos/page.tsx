import Link from 'next/link';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Atendimentos · AutoBrokers' };

const areas = [
  { label: 'Fila', hint: 'Casos aguardando atendimento' },
  { label: 'Casos', hint: 'Detalhe, timeline e ações' },
  { label: 'Conversas', hint: 'Histórico por canal' },
  { label: 'Segurados', hint: 'Clientes e apólices' },
];

export default function AtendimentosPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-12">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icons.atendimentos} size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Atendimentos</h1>
            <p className="text-sm text-muted-foreground">Operação de filas, casos, conversas e segurados.</p>
          </div>
        </div>

        <p className="mt-6 max-w-xl text-sm leading-relaxed text-foreground-2">
          Este módulo vai concentrar a operação da corretora. Estamos preparando a navegação — as áreas
          abaixo serão habilitadas por fases. Nada aqui executa ações ainda.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
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
