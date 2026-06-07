import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

/* =========================================================================
   /sandbox — Showcase técnico da fundação visual (B0).
   Rota interna só para inspeção dos tokens Névoa, Geist e primitivos.
   Sem dados reais, sem lógica. Não é linkada na navegação.
   ========================================================================= */

export const metadata = { title: 'Sandbox · AutoBrokers' };

function BrandMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 22 22" fill="none" aria-hidden="true" className="text-primary">
      <rect x="1.2" y="1.2" width="19.6" height="19.6" rx="6" stroke="currentColor" strokeWidth="1.4" />
      <rect x="7.2" y="7.2" width="7.6" height="7.6" rx="2" transform="rotate(45 11 11)" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function Swatch({ name, className }: { name: string; className: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className={`h-14 w-full rounded-lg border border-border-soft ${className}`} />
      <span className="font-mono text-[11px] text-faint">{name}</span>
    </div>
  );
}

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'approval';

function StatusChip({ tone, label }: { tone: Tone; label: string }) {
  const styles: Record<Tone, string> = {
    neutral: 'text-muted-foreground border-border',
    info: 'text-primary border-primary/40 bg-brand-soft',
    success: 'text-success border-success/40',
    warning: 'text-warning border-warning/40',
    danger: 'text-danger border-danger/40',
    approval: 'text-primary border-dashed border-primary/60 bg-brand-soft',
  };
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] ${styles[tone]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full bg-current ${tone === 'approval' ? 'animate-pulse' : ''}`} />
      {label}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.12em] text-faint">{title}</h2>
      {children}
    </section>
  );
}

const pillars = [
  { key: 'autobrokers' as const, label: 'AutoBrokers', active: true },
  { key: 'atendimentos' as const, label: 'Atendimentos', active: false },
  { key: 'auxiliares' as const, label: 'Auxiliares', active: false },
  { key: 'personalizacao' as const, label: 'Personalização', active: false },
];

export default function SandboxPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto w-full max-w-5xl px-6 py-12 space-y-14">
        {/* Header */}
        <header className="flex items-center gap-3 border-b border-border-soft pb-8">
          <BrandMark size={34} />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">AutoBrokers · Sandbox visual</h1>
            <p className="text-sm text-muted-foreground">
              Fundação <span className="text-foreground-2">Névoa</span> + <span className="text-foreground-2">Geist</span> — inspeção técnica de tokens e primitivos (B0).
            </p>
          </div>
        </header>

        {/* Nav line (pilares) */}
        <Section title="Navegação · 4 pilares">
          <div className="flex flex-wrap gap-2">
            {pillars.map((p) => (
              <span
                key={p.key}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                  p.active
                    ? 'border-border bg-surface-2 text-foreground'
                    : 'border-border-soft text-muted-foreground'
                }`}
              >
                <Icon icon={icons[p.key]} size={17} className={p.active ? 'text-primary' : ''} />
                {p.label}
              </span>
            ))}
          </div>
        </Section>

        {/* Tokens */}
        <Section title="Tokens de cor · Névoa">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 md:grid-cols-6">
            <Swatch name="background" className="bg-background" />
            <Swatch name="surface" className="bg-surface" />
            <Swatch name="surface-2" className="bg-surface-2" />
            <Swatch name="card" className="bg-card" />
            <Swatch name="border" className="bg-border" />
            <Swatch name="primary/accent" className="bg-primary" />
            <Swatch name="success" className="bg-success" />
            <Swatch name="warning" className="bg-warning" />
            <Swatch name="danger" className="bg-danger" />
            <Swatch name="muted-fg" className="bg-muted-foreground" />
            <Swatch name="foreground-2" className="bg-foreground-2" />
            <Swatch name="foreground" className="bg-foreground" />
          </div>
        </Section>

        {/* Tipografia */}
        <Section title="Tipografia · Geist / Geist Mono">
          <div className="space-y-2 rounded-xl border border-border bg-surface p-6 shadow-card">
            <p className="text-3xl font-semibold tracking-tight text-foreground">
              Como posso ajudar sua corretora hoje?
            </p>
            <p className="text-base text-foreground-2">
              Texto secundário em foreground-2 — leituras e descrições de apoio.
            </p>
            <p className="text-sm text-muted-foreground">
              Texto muted — descrições discretas e legendas.
            </p>
            <p className="font-mono text-xs uppercase tracking-[0.1em] text-faint">
              meta · mono · faint · 11—12px
            </p>
          </div>
        </Section>

        {/* Botões */}
        <Section title="Botões · components/ui/button.tsx">
          <div className="flex flex-wrap items-center gap-3">
            <Button>Primário</Button>
            <Button variant="secondary">Secundário</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="destructive">Destrutivo</Button>
            <Button disabled>Desabilitado</Button>
            <Button size="sm" className="gap-2">
              <Icon icon={icons.enviar} size={15} />
              Enviar
            </Button>
          </div>
        </Section>

        {/* Status */}
        <Section title="Sistema de status · 6 tons">
          <div className="flex flex-wrap gap-2">
            <StatusChip tone="neutral" label="Disponível" />
            <StatusChip tone="info" label="Em andamento" />
            <StatusChip tone="success" label="Conectado" />
            <StatusChip tone="warning" label="Precisa configurar" />
            <StatusChip tone="danger" label="Com erro" />
            <StatusChip tone="approval" label="Aguardando aprovação" />
          </div>
        </Section>

        {/* Ícones */}
        <Section title="Ícones · wrapper Icon + lib/icons (Lucide)">
          <div className="flex flex-wrap gap-5 rounded-xl border border-border bg-surface p-6">
            {(
              ['autobrokers', 'atendimentos', 'auxiliares', 'personalizacao', 'conectores', 'seguradoras', 'conhecimento', 'equipe', 'success', 'warning', 'danger', 'aprovacao'] as const
            ).map((name) => (
              <div key={name} className="flex w-16 flex-col items-center gap-2 text-muted-foreground">
                <Icon icon={icons[name]} size={20} />
                <span className="font-mono text-[10px] text-faint">{name}</span>
              </div>
            ))}
          </div>
        </Section>

        {/* Mini chat card + mini gallery card */}
        <Section title="Prévia (sem lógica)">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Mini chat */}
            <Card className="border-border bg-surface p-5 shadow-card">
              <div className="mb-4 flex items-center gap-2">
                <BrandMark size={20} />
                <span className="text-sm font-medium text-foreground">AutoBrokers</span>
              </div>
              <p className="mb-4 text-lg font-medium text-foreground">
                Como posso ajudar sua corretora hoje?
              </p>
              <div className="flex items-center gap-2 rounded-xl border border-border bg-surface-2 px-4 py-3">
                <span className="flex-1 text-sm text-muted-foreground">Pergunte ao AutoBrokers…</span>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Icon icon={icons.enviar} size={16} />
                </span>
              </div>
            </Card>

            {/* Mini gallery/auxiliar card */}
            <Card className="border-border bg-surface p-5 shadow-card">
              <div className="mb-3 flex items-start justify-between">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                  <Icon icon={icons.auxiliares} size={18} />
                </span>
                <StatusChip tone="success" label="Ativo" />
              </div>
              <h3 className="text-base font-semibold text-foreground">Auxiliar de Resumo de Atendimentos</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Resume conversas e destaca pendências e próxima ação sugerida.
              </p>
              <div className="mt-4 flex items-center gap-2">
                <Button size="sm">Ver detalhes</Button>
                <span className="font-mono text-[11px] text-faint">categoria · operação</span>
              </div>
            </Card>
          </div>
        </Section>

        <footer className="border-t border-border-soft pt-8 font-mono text-[11px] text-faint">
          AutoBrokers.ai · /sandbox · fundação Névoa · Geist · B0 — rota interna de inspeção
        </footer>
      </div>
    </div>
  );
}
