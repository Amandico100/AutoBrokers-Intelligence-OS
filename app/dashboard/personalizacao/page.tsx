import Link from 'next/link';

import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import type { IconName } from '@/lib/icons';

export const metadata = { title: 'Personalização · AutoBrokers' };

const areas: { label: string; hint: string; icon: IconName }[] = [
  { label: 'Conectores', hint: 'Integrações reutilizáveis', icon: 'conectores' },
  { label: 'Seguradoras', hint: 'Canais, portais e corredores', icon: 'seguradoras' },
  { label: 'Conhecimento', hint: 'Documentos e fontes da corretora', icon: 'conhecimento' },
  { label: 'Corretora', hint: 'Dados e identidade', icon: 'personalizacao' },
  { label: 'Equipe', hint: 'Usuários e permissões', icon: 'equipe' },
];

export default function PersonalizacaoPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-12">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface-2 text-primary">
            <Icon icon={icons.personalizacao} size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Personalização</h1>
            <p className="text-sm text-muted-foreground">Conectores, seguradoras, conhecimento e equipe.</p>
          </div>
        </div>

        <p className="mt-6 max-w-xl text-sm leading-relaxed text-foreground-2">
          Aqui a corretora configura o sistema. Estamos preparando a navegação — as áreas abaixo serão
          habilitadas por fases. Nenhuma conexão real é feita ainda.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {areas.map((a) => (
            <div key={a.label} className="flex items-start gap-3 rounded-xl border border-border bg-surface p-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                <Icon icon={icons[a.icon]} size={18} />
              </span>
              <div>
                <p className="text-sm font-medium text-foreground">{a.label}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{a.hint}</p>
                <span className="mt-2 inline-block rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
                  em breve
                </span>
              </div>
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
