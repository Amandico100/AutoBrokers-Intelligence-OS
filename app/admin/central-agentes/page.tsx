'use client';

// SPEC-036 Etapa 1 — Central de Agentes (design Claude Design 14/07).
// O organismo que opera o AutoBrokers: quem faz o quê, último pulso, ações do dia.

import { useEffect, useState } from 'react';

type AgentStatus = {
  id: string;
  name: string;
  desc: string;
  last_run: string | null;
  actions_today: number;
};

const COLORS: Record<string, string> = {
  espelho: '#7FB7E8', vigia_sentinela: '#E2A94F', followup: '#43C08C',
  garimpo: '#43C08C', auditor: '#E2A94F', alfaiate: '#B48EAD',
  sugestoes: '#7FB7E8', cartografo: '#74ACE8', cerebro: '#43C08C',
};

const S = {
  page: { background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' } as React.CSSProperties,
  card: { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14, padding: '16px 18px' } as React.CSSProperties,
  mono: { fontFamily: 'Geist Mono, monospace' } as React.CSSProperties,
};

function ago(iso: string | null): string {
  if (!iso) return 'nunca rodou';
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return `há ${Math.round(s)}s`;
  if (s < 5400) return `há ${Math.round(s / 60)} min`;
  return `há ${Math.round(s / 3600)} h`;
}

function health(iso: string | null): { label: string; color: string } {
  if (!iso) return { label: 'AGUARDANDO', color: '#8A93A3' };
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 900) return { label: 'SAUDÁVEL', color: '#43C08C' };
  if (s < 7200) return { label: 'ATENÇÃO', color: '#E2A94F' };
  return { label: 'PARADO', color: '#E06B6B' };
}

export default function CentralAgentesPage() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () =>
      fetch('/api/admin/spec034/agents-status')
        .then((r) => r.json())
        .then((d) => setAgents(d.agents || []))
        .catch(() => undefined)
        .finally(() => setLoading(false));
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  const totalActions = agents.reduce((a, b) => a + (b.actions_today || 0), 0);
  const alive = agents.filter((a) => a.last_run && Date.now() - new Date(a.last_run).getTime() < 900e3).length;

  return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Central de Agentes</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>
          O organismo que opera o AutoBrokers — entenda em 1 minuto quem faz o quê.
        </div>
      </div>

      <div style={{ ...S.card, marginTop: 14, padding: '11px 16px', display: 'flex', gap: 18, alignItems: 'center', ...S.mono, fontSize: 11, color: '#7C8798' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 7, color: '#43C08C' }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#43C08C' }} />
          AO VIVO
        </span>
        <span>{alive}/{agents.length} agentes pulsando</span>
        <span><span style={{ color: '#A9B2C0' }}>{totalActions}</span> ações hoje</span>
        {loading && <span>carregando…</span>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12, marginTop: 14 }}>
        {agents.map((a) => {
          const h = health(a.last_run);
          const color = COLORS[a.id] || '#7FB7E8';
          return (
            <div key={a.id} style={{ ...S.card, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                <span style={{ width: 11, height: 11, borderRadius: 3, background: color, transform: 'rotate(45deg)', boxShadow: `0 0 6px ${color}` }} />
                <span style={{ fontSize: 14.5, fontWeight: 600 }}>{a.name}</span>
                <span style={{ flex: 1 }} />
                <span style={{ ...S.mono, fontSize: 9.5, letterSpacing: '0.08em', padding: '3px 9px', borderRadius: 999, border: `1px solid ${h.color}55`, color: h.color }}>
                  {h.label}
                </span>
              </div>
              <div style={{ fontSize: 12.5, color: '#8A93A3', lineHeight: 1.5, minHeight: 36 }}>{a.desc}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, ...S.mono, fontSize: 10.5, color: '#5A6577', borderTop: '1px solid #131A23', paddingTop: 10 }}>
                <span>último run <span style={{ color: '#A9B2C0' }}>{ago(a.last_run)}</span></span>
                <span style={{ flex: 1 }} />
                <span><span style={{ color: '#A9B2C0' }}>{a.actions_today}</span> ações · hoje</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
