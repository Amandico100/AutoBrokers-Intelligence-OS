'use client';

// SPEC-036 — ATIVIDADES: tudo que os agentes fizeram pela corretora, em tempo
// real (layout aprovado pelo founder: categorias como filtros + timeline).

import { useEffect, useMemo, useState } from 'react';

type Activity = { category: string; title: string; detail: string; created_at: string };

const CATS: { id: string; label: string; color: string }[] = [
  { id: 'todas', label: 'Todas', color: '#C6CEDA' },
  { id: 'atendimentos', label: 'Atendimentos', color: '#7FB7E8' },
  { id: 'acionamentos', label: 'Acionamentos', color: '#E2A94F' },
  { id: 'qualidade', label: 'Qualidade', color: '#43C08C' },
  { id: 'conhecimento', label: 'Conhecimento', color: '#B48EAD' },
  { id: 'inteligencia', label: 'Inteligência', color: '#74ACE8' },
];

const mono: React.CSSProperties = { fontFamily: 'Geist Mono, monospace' };

function when(iso: string): string {
  try {
    const d = new Date(iso);
    const today = new Date().toDateString() === d.toDateString();
    const hm = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    return today ? hm : `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} ${hm}`;
  } catch { return ''; }
}

export default function AtividadesPage() {
  const [acts, setActs] = useState<Activity[]>([]);
  const [cat, setCat] = useState('todas');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () =>
      fetch('/api/dashboard/atividades')
        .then((r) => r.json())
        .then((d) => { if (d?.ok) setActs(d.activities || []); })
        .catch(() => undefined)
        .finally(() => setLoading(false));
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { todas: acts.length };
    for (const a of acts) c[a.category] = (c[a.category] || 0) + 1;
    return c;
  }, [acts]);

  const list = cat === 'todas' ? acts : acts.filter((a) => a.category === cat);

  return (
    <div style={{ background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Atividades</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>Tudo que a sua equipe de IA executou — em tempo real.</div>
      </div>

      <div style={{ display: 'flex', gap: 14, marginTop: 16, alignItems: 'flex-start' }}>
        <div style={{ width: 250, minWidth: 210, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {CATS.map((c) => (
            <div key={c.id} onClick={() => setCat(c.id)}
              style={{ background: cat === c.id ? '#0E141C' : '#0B0F15', border: `1px solid ${cat === c.id ? '#2C3A4E' : '#161D28'}`, borderRadius: 12, padding: '12px 15px', cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: c.color }} />
                <span style={{ fontSize: 13.5, fontWeight: 600 }}>{c.label}</span>
                <span style={{ flex: 1 }} />
                <span style={{ ...mono, fontSize: 11, color: '#7C8798' }}>{counts[c.id] || 0}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14, padding: '18px 22px', minWidth: 0 }}>
          {loading && <div style={{ fontSize: 13, color: '#7C8798' }}>carregando…</div>}
          {!loading && list.length === 0 && (
            <div style={{ padding: '24px 12px', textAlign: 'center', color: '#7C8798', fontSize: 13, lineHeight: 1.6 }}>
              As atividades aparecem aqui conforme os agentes trabalham — atendimentos,
              acionamentos de assistência, verificações de qualidade e inteligência do seu negócio.
              Todo sábado você recebe o resumo da semana no WhatsApp. 📊
            </div>
          )}
          {list.map((a, i) => {
            const meta = CATS.find((c) => c.id === a.category) || CATS[0];
            return (
              <div key={i} style={{ display: 'flex', gap: 14, padding: '10px 0 10px 16px', borderLeft: '2px solid #161D28', marginLeft: 4, position: 'relative' }}>
                <span style={{ position: 'absolute', left: -5, top: 16, width: 8, height: 8, borderRadius: '50%', background: meta.color, boxShadow: `0 0 8px ${meta.color}` }} />
                <span style={{ ...mono, fontSize: 10.5, color: '#5A6577', minWidth: 76, paddingTop: 2 }}>{when(a.created_at)}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: '#E7EBF1' }}>{a.title}</div>
                  {a.detail && <div style={{ fontSize: 12, color: '#8A93A3', marginTop: 3, lineHeight: 1.5 }}>{a.detail}</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
