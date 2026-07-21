'use client';

// SPEC-036 Etapa 2B — Cockpit da corretora: visão 360º (conversas, qualidade
// do Auditor, insights do Garimpo, conhecimento, acionamentos) num lugar só.

import { useEffect, useState } from 'react';

type Company = { id: string; company_name: string; is_technical?: boolean };
type Overview = {
  company?: { company_name?: string; status?: string; plan_type?: string };
  conversas?: { total: number; acionamentos: number; recentes: any[]; acionamentos_recentes: any[] };
  qualidade?: { nota_media: number | null; auditadas: number; flags: [string, number][] };
  insights?: { kind: string; summary: string; source: string; created_at: string }[];
  conhecimento?: { documentos: number };
};

const mono: React.CSSProperties = { fontFamily: 'Geist Mono, monospace' };
const card: React.CSSProperties = { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14, padding: '16px 18px' };

const KIND_COLOR: Record<string, string> = {
  dor: '#E06B6B', desejo: '#7FB7E8', pedido_feature: '#E2A94F', risco_churn: '#E06B6B',
  elogio: '#43C08C', sugestao_enviada: '#8A93A3',
};

export default function CorretorasCockpit() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [sel, setSel] = useState<string>('');
  const [ov, setOv] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/admin/companies')
      .then((r) => r.json())
      .then((d) => {
        const list: Company[] = (d.companies || d || []).filter((c: Company) => !c.is_technical);
        setCompanies(list);
        if (list.length) setSel(list[0].id);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!sel) return;
    setLoading(true);
    fetch(`/api/admin/spec034/company-overview/${sel}`)
      .then((r) => r.json())
      .then(setOv)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [sel]);

  const nota = ov?.qualidade?.nota_media;
  const notaColor = nota == null ? '#8A93A3' : nota >= 80 ? '#43C08C' : nota >= 60 ? '#E2A94F' : '#E06B6B';

  return (
    <div style={{ background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Cockpit da corretora</div>
        <select value={sel} onChange={(e) => setSel(e.target.value)}
          style={{ background: '#0B0F15', border: '1px solid #2C3A4E', color: '#E7EBF1', borderRadius: 9, padding: '7px 12px', fontSize: 13 }}>
          {companies.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
        </select>
        {loading && <span style={{ fontSize: 12, color: '#7C8798' }}>carregando…</span>}
        <span style={{ flex: 1 }} />
        {/* SPEC-046: caminho de volta para a tela REAL de configuração da
            empresa (Identidade, HTTP Tools, MCP, WhatsApp, Agentes, Subagentes). */}
        {sel && (
          <a
            href={`/admin/companies/${sel}/agents`}
            style={{
              background: '#12233A', border: '1px solid #2C4A72', color: '#7FB7E8',
              borderRadius: 9, padding: '7px 14px', fontSize: 13, fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            ⚙ Configuração completa
          </a>
        )}
      </div>

      {ov && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12, marginTop: 16 }}>
            <div style={card}>
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577' }}>Nota do Auditor</div>
              <div style={{ fontSize: 28, fontWeight: 650, color: notaColor, marginTop: 8 }}>
                {nota == null ? '—' : `${nota}/100`}
              </div>
              <div style={{ fontSize: 11, color: '#6B7688' }}>{ov.qualidade?.auditadas || 0} conversas auditadas</div>
            </div>
            <div style={card}>
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577' }}>Conversas</div>
              <div style={{ fontSize: 28, fontWeight: 650, marginTop: 8 }}>{ov.conversas?.total ?? 0}</div>
              <div style={{ fontSize: 11, color: '#6B7688' }}>{ov.conversas?.acionamentos ?? 0} acionamentos de seguradora</div>
            </div>
            <div style={card}>
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577' }}>Conhecimento</div>
              <div style={{ fontSize: 28, fontWeight: 650, marginTop: 8 }}>{ov.conhecimento?.documentos ?? 0}</div>
              <div style={{ fontSize: 11, color: '#6B7688' }}>documentos no cofre da corretora</div>
            </div>
            <div style={card}>
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577' }}>Plano</div>
              <div style={{ fontSize: 20, fontWeight: 650, marginTop: 10 }}>{ov.company?.plan_type || '—'}</div>
              <div style={{ fontSize: 11, color: '#6B7688' }}>{ov.company?.status || ''}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ ...card, flex: 1, minWidth: 320 }}>
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577', marginBottom: 10 }}>
                Voz do corretor (Garimpo)
              </div>
              {(ov.insights || []).length === 0 && (
                <div style={{ fontSize: 12.5, color: '#7C8798' }}>Sem insights ainda — o Garimpo minera diariamente.</div>
              )}
              {(ov.insights || []).map((i, k) => (
                <div key={k} style={{ display: 'flex', gap: 10, padding: '7px 0', alignItems: 'baseline' }}>
                  <span style={{ ...mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: KIND_COLOR[i.kind] || '#8A93A3', minWidth: 64 }}>{i.kind.replace('_', ' ')}</span>
                  <span style={{ fontSize: 12.5, color: '#B9C2CF', flex: 1 }}>{i.summary}</span>
                </div>
              ))}
            </div>
            <div style={{ ...card, flex: 1, minWidth: 320 }}>
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577', marginBottom: 10 }}>
                Qualidade — flags mais comuns
              </div>
              {(ov.qualidade?.flags || []).length === 0 && (
                <div style={{ fontSize: 12.5, color: '#7C8798' }}>Nenhuma flag — ou nada auditado ainda.</div>
              )}
              {(ov.qualidade?.flags || []).map(([flag, n], k) => (
                <div key={k} style={{ display: 'flex', gap: 10, padding: '7px 0' }}>
                  <span style={{ fontSize: 12.5, color: '#B9C2CF', flex: 1 }}>{flag.replace(/_/g, ' ')}</span>
                  <span style={{ ...mono, fontSize: 12, color: '#E2A94F' }}>{n}×</span>
                </div>
              ))}
              <div style={{ ...mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577', margin: '14px 0 8px' }}>
                Acionamentos recentes
              </div>
              {(ov.conversas?.acionamentos_recentes || []).map((c: any, k: number) => (
                <div key={k} style={{ fontSize: 12.5, color: '#B9C2CF', padding: '4px 0' }}>{c.user_name}</div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
