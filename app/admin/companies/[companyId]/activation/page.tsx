'use client';

// TA2-C Parte 9 — visão master de ativação de uma corretora (rollup canônico).
// Mesma fonte do Dashboard (read-only). Não expõe segredo/prompt/Vault/SessionRef.
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { ArrowLeft, Bot, Loader2, Headphones } from 'lucide-react';

type AgentCfg = { ok: boolean; provisioned?: boolean; config?: { display_name: string; blueprint_version: string } };
type Corridor = { template_id: string; title: string; status: string };
type ReadinessItem = { key: string; label: string; status: string; reason: string; critical: boolean };
type Rollup = {
  ok: boolean;
  agents: { core: AgentCfg; attendance: AgentCfg };
  corridors: { active: number; items: Corridor[] };
  auxiliaries: { installed: number };
  readiness: { production_ready: boolean; ready_count: number; total: number; items: ReadinessItem[] };
};

const STATUS_CLS: Record<string, string> = {
  active: 'text-emerald-600', ready: 'text-emerald-600',
  paused: 'text-amber-600', pending: 'text-amber-600',
  blocked: 'text-red-600', available: 'text-muted-foreground', not_applicable: 'text-muted-foreground',
};

export default function AdminCompanyActivationPage() {
  const params = useParams();
  const router = useRouter();
  const companyId = params.companyId as string;
  const [data, setData] = useState<Rollup | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`/api/admin/companies/${companyId}/activation`)
      .then((r) => r.json())
      .then((j) => { if (j?.ok) setData(j); else setError(j?.error || 'Falha ao carregar'); })
      .catch(() => setError('Falha ao carregar'));
  }, [companyId]);

  if (error) return <div className="p-6 text-sm text-red-600">Erro: {error}</div>;
  if (!data) return <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Carregando…</div>;

  const core = data.agents.core;
  const even = data.agents.attendance;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
      <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Voltar</button>
      <h1 className="text-xl font-semibold">Ativação da corretora</h1>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-2"><Bot className="h-4 w-4" /><p className="font-medium">AutoBrokers</p></div>
          <p className="mt-1 text-sm text-muted-foreground">{core?.provisioned ? `${core.config?.display_name} · ${core.config?.blueprint_version}` : 'Aguardando provisionamento'}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-2"><Headphones className="h-4 w-4" /><p className="font-medium">Atendimento{even?.config?.display_name ? ` · ${even.config.display_name}` : ''}</p></div>
          <p className="mt-1 text-sm text-muted-foreground">{even?.provisioned ? `${even.config?.display_name} · ${even.config?.blueprint_version}` : 'Aguardando provisionamento'}</p>
        </CardContent></Card>
      </div>

      <Card><CardContent className="p-4">
        <p className="font-medium">Corredores ({data.corridors.active} ativos) · Auxiliares ({data.auxiliaries.installed} instalados)</p>
        <div className="mt-2 space-y-1">
          {data.corridors.items.map((c) => (
            <div key={c.template_id} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{c.title}</span>
              <span className={STATUS_CLS[c.status] ?? ''}>{c.status}</span>
            </div>
          ))}
        </div>
      </CardContent></Card>

      <Card><CardContent className="p-4">
        <p className="font-medium">Prontidão — {data.readiness.ready_count}/{data.readiness.total} {data.readiness.production_ready ? '· pronta para produção' : '· pendente'}</p>
        <div className="mt-2 space-y-1">
          {data.readiness.items.map((it) => (
            <div key={it.key} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{it.label}{it.critical ? ' *' : ''}</span>
              <span className={STATUS_CLS[it.status] ?? ''}>{it.status}</span>
            </div>
          ))}
        </div>
      </CardContent></Card>

      <p className="text-xs text-muted-foreground">Mesma fonte canônica do Dashboard da corretora. Somente leitura — sem segredos, prompts protegidos, Vault ou SessionRef.</p>
    </div>
  );
}
