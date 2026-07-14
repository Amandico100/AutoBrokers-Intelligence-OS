'use client';

// SPEC-036 Etapa 1 — Insights · Garimpo (design Claude Design 14/07).
// Dores, desejos e pedidos extraídos das conversas + histórico da IA de Sugestões.

import { useEffect, useState } from 'react';

type RankItem = { kind: string; summary: string; count: number };
type Sugestao = { company_id: string; summary: string; status: string; created_at: string };

const KIND_META: Record<string, { label: string; color: string }> = {
  dor: { label: 'DOR', color: '#E06B6B' },
  desejo: { label: 'DESEJO', color: '#7FB7E8' },
  pedido_feature: { label: 'PEDIDO', color: '#E2A94F' },
  risco_churn: { label: 'CHURN', color: '#E06B6B' },
  elogio: { label: 'ELOGIO', color: '#43C08C' },
};

const mono: React.CSSProperties = { fontFamily: 'Geist Mono, monospace' };
const card: React.CSSProperties = { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14 };

function badge(color: string): React.CSSProperties {
  return { ...mono, fontSize: 9.5, letterSpacing: '0.08em', padding: '3px 9px', borderRadius: 999, border: `1px solid ${color}55`, color, whiteSpace: 'nowrap' };
}

export default function InsightsPage() {
  const [ranking, setRanking] = useState<RankItem[]>([]);
  const [sugestoes, setSugestoes] = useState<Sugestao[]>([]);
  const [companies, setCompanies] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/admin/spec034/insights')
      .then((r) => r.json())
      .then((d) => {
        setRanking(d.ranking || []);
        setSugestoes(d.sugestoes || []);
        setCompanies(d.companies || {});
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const max = Math.max(1, ...ranking.map((r) => r.count));
  const respondidas = sugestoes.filter((s) => s.status !== 'novo').length;

  return (
    <div style={{ background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Insights · Garimpo</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>Dores, desejos e pedidos extraídos das conversas dos corretores.</div>
      </div>

      {loading && <div style={{ marginTop: 20, color: '#7C8798', fontSize: 13 }}>garimpando…</div>}

      <div style={{ display: 'flex', gap: 14, marginTop: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ ...card, flex: 1.5, minWidth: 380, padding: 8 }}>
          {ranking.length === 0 && !loading && (
            <div style={{ padding: '26px 20px', textAlign: 'center', color: '#7C8798', fontSize: 13 }}>
              O Garimpo roda diariamente sobre as conversas dos corretores. Conforme dores e desejos aparecerem,
              o ranking nasce aqui — com a citação original de cada um.
            </div>
          )}
          {ranking.map((ins, i) => {
            const m = KIND_META[ins.kind] || { label: ins.kind, color: '#8A93A3' };
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '11px 14px', borderRadius: 10 }}>
                <span style={{ ...mono, fontSize: 11, color: '#5A6577', minWidth: 20 }}>{String(i + 1).padStart(2, '0')}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                    <span style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ins.summary}</span>
                    <span style={badge(m.color)}>{m.label}</span>
                  </div>
                  <div style={{ height: 4, background: '#131A23', borderRadius: 2, marginTop: 7, overflow: 'hidden' }}>
                    <div style={{ height: '100%', borderRadius: 2, background: `${m.color}99`, width: `${Math.round((ins.count / max) * 100)}%` }} />
                  </div>
                </div>
                <span style={{ ...mono, fontSize: 12, color: '#A9B2C0', minWidth: 30, textAlign: 'right' }}>{ins.count}</span>
              </div>
            );
          })}
        </div>

        <div style={{ flex: 1, minWidth: 300, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ ...card, padding: '18px 20px' }}>
            <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577' }}>IA de Sugestões</div>
            <div style={{ display: 'flex', gap: 26, marginTop: 12 }}>
              <div>
                <div style={{ fontSize: 24, fontWeight: 650 }}>{sugestoes.length}</div>
                <div style={{ fontSize: 11, color: '#6B7688' }}>enviadas</div>
              </div>
              <div>
                <div style={{ fontSize: 24, fontWeight: 650, color: '#43C08C' }}>{respondidas}</div>
                <div style={{ fontSize: 11, color: '#6B7688' }}>com retorno</div>
              </div>
            </div>
          </div>
          <div style={{ ...card, padding: '10px 8px' }}>
            <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577', padding: '8px 12px' }}>Histórico recente</div>
            {sugestoes.length === 0 && !loading && (
              <div style={{ padding: '14px 12px', color: '#7C8798', fontSize: 12.5 }}>
                Toda segunda a IA envia a mensagem semanal (oportunidade + alerta + pergunta) para cada corretora
                — e o registro aparece aqui.
              </div>
            )}
            {sugestoes.map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 9 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, color: '#D6DDE7', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.summary}</div>
                  <div style={{ ...mono, fontSize: 10.5, color: '#5A6577', marginTop: 2 }}>
                    {companies[s.company_id] || 'corretora'} · {s.created_at ? new Date(s.created_at).toLocaleDateString('pt-BR') : ''}
                  </div>
                </div>
                <span style={badge(s.status !== 'novo' ? '#43C08C' : '#8A93A3')}>{s.status !== 'novo' ? 'VISTA' : 'ENVIADA'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
