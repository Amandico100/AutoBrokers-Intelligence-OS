'use client';

// SPEC-038 — ATLAS de Rotas (admin-only). O mapa vivo dos WhatsApps das
// seguradoras, construído pelo Observador. Inteligência 100% AutoBrokers.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Map as MapIcon, RefreshCw, ChevronRight, AlertTriangle } from 'lucide-react';

type Card = {
  id: string; insurer_key: string; ramo: string; status: string; source: string;
  nodes: number; coverage_pct: number; sessions: number; updated_at: string;
};
type Opt = { label: string; leads_to: string | null; confidence?: string };
type Node = { hash: string; text: string; kind: string; status?: string; options: Opt[]; samples?: number };
type MapObj = { root: string | null; nodes: Record<string, Node>; edges?: Record<string, any>; coverage?: any; meta?: any };

const BRAND: Record<string, { bg: string; mono: string }> = {
  porto: { bg: '#00A1FC', mono: 'P' }, allianz: { bg: '#003781', mono: 'A' },
  azul: { bg: '#0072CE', mono: 'Az' }, bradesco: { bg: '#CC092F', mono: 'B' },
  hdi: { bg: '#00714B', mono: 'H' }, itau: { bg: '#EC7000', mono: 'It' },
  mapfre: { bg: '#D81E05', mono: 'M' }, tokio: { bg: '#00A650', mono: 'TM' },
  yelum: { bg: '#5B2D90', mono: 'Y' }, youse: { bg: '#F65C78', mono: 'Yo' },
  zurich: { bg: '#2167AE', mono: 'Z' }, alfa: { bg: '#004B8D', mono: 'Al' },
};
const brand = (k: string) => BRAND[k] || { bg: '#334155', mono: (k || '?')[0].toUpperCase() };

const STATUS_COLOR: Record<string, string> = {
  complete: '#43C08C', partial: '#E2A94F', drift: '#E0574B',
  app_form: '#B48EAD', unknown: '#5B6472',
};
const S = {
  page: { background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' } as React.CSSProperties,
  card: { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 14, padding: 16 } as React.CSSProperties,
};

function pct(n: number) { return `${Math.round(n || 0)}%`; }

export default function AtlasPage() {
  const [cards, setCards] = useState<Card[] | null>(null);
  const [sel, setSel] = useState<{ insurer: string; ramo: string } | null>(null);
  const [map, setMap] = useState<MapObj | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const load = useCallback(() => {
    fetch('/api/admin/atlas/maps').then((r) => r.json()).then((j) => setCards(j.cards || [])).catch(() => setCards([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const openMap = (insurer: string, ramo: string) => {
    setSel({ insurer, ramo }); setMap(null);
    fetch(`/api/admin/atlas/map/${insurer}/${ramo}`).then((r) => r.json())
      .then((j) => setMap(j.map || null)).catch(() => setMap(null));
  };

  const runWeave = async () => {
    setBusy(true); setNotice('Tecendo os mapas a partir das observações…');
    try {
      const r = await fetch('/api/admin/atlas/weave', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const j = await r.json();
      setNotice(j.ok ? `Tecido: ${(j.woven || []).length || 1} seguradora(s).` : 'Falha ao tecer.');
      load();
    } catch { setNotice('Falha ao tecer.'); } finally { setBusy(false); }
  };

  // "O que falta": nós com opções em lacuna (gap)
  const gaps = useMemo(() => {
    if (!map) return [];
    const out: { screen: string; missing: string[] }[] = [];
    for (const n of Object.values(map.nodes || {})) {
      const missing = (n.options || []).filter((o) => o.confidence === 'gap').map((o) => o.label);
      if (missing.length) out.push({ screen: n.text.slice(0, 60), missing });
    }
    return out;
  }, [map]);

  return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <MapIcon size={22} color="#7FB7E8" />
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Atlas de Rotas</h1>
            <p style={{ fontSize: 12.5, color: '#8A93A3', margin: '2px 0 0' }}>
              Mapa vivo dos WhatsApps das seguradoras — construído pelo Observador. Inteligência AutoBrokers (admin-only).
            </p>
          </div>
        </div>
        <button onClick={runWeave} disabled={busy} style={{ display: 'flex', alignItems: 'center', gap: 7, background: '#12202E', border: '1px solid #22384C', color: '#CFE0F0', borderRadius: 10, padding: '9px 14px', cursor: busy ? 'default' : 'pointer', fontSize: 13 }}>
          <RefreshCw size={15} className={busy ? 'spin' : ''} /> {busy ? 'Tecendo…' : 'Tecer mapas'}
        </button>
      </div>
      {notice && <p style={{ fontSize: 12.5, color: '#7FB7E8', margin: '4px 0 14px' }}>{notice}</p>}

      {!sel && (
        <>
          {cards === null ? <p style={{ color: '#8A93A3', marginTop: 20 }}>Carregando…</p> :
            cards.length === 0 ? (
              <div style={{ ...S.card, marginTop: 16, textAlign: 'center', padding: 30 }}>
                <p style={{ fontSize: 14, fontWeight: 600 }}>Nenhum mapa ainda.</p>
                <p style={{ fontSize: 12.5, color: '#8A93A3', maxWidth: 460, margin: '6px auto 0' }}>
                  Assim que o Observador capturar atendimentos com seguradoras, clique em "Tecer mapas" para desenhar as rotas aqui.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12, marginTop: 16 }}>
                {cards.map((c) => {
                  const b = brand(c.insurer_key);
                  const cov = c.coverage_pct || 0;
                  const covColor = cov >= 80 ? '#43C08C' : cov >= 40 ? '#E2A94F' : '#E0574B';
                  return (
                    <button key={c.id} onClick={() => openMap(c.insurer_key, c.ramo)} style={{ ...S.card, textAlign: 'left', cursor: 'pointer' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                        <div style={{ width: 42, height: 42, borderRadius: 11, background: b.bg, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 15 }}>{b.mono}</div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontSize: 14, fontWeight: 700, margin: 0, textTransform: 'capitalize' }}>{c.insurer_key} · {c.ramo}</p>
                          <p style={{ fontSize: 11.5, color: '#8A93A3', margin: '2px 0 0' }}>{c.nodes} telas · {c.sessions} sessões observadas</p>
                        </div>
                      </div>
                      <div style={{ marginTop: 12 }}>
                        <div style={{ height: 6, background: '#161D28', borderRadius: 4, overflow: 'hidden' }}>
                          <div style={{ width: pct(cov), height: '100%', background: covColor }} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                          <span style={{ fontSize: 11.5, color: covColor, fontWeight: 600 }}>{pct(cov)} mapeado</span>
                          <span style={{ fontSize: 11.5, color: '#8A93A3', display: 'flex', alignItems: 'center', gap: 3 }}>Abrir <ChevronRight size={13} /></span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
        </>
      )}

      {sel && (
        <div style={{ marginTop: 14 }}>
          <button onClick={() => { setSel(null); setMap(null); }} style={{ background: 'none', border: 'none', color: '#8A93A3', cursor: 'pointer', fontSize: 12.5, marginBottom: 12 }}>← Todas as seguradoras</button>
          {map === null ? <p style={{ color: '#8A93A3' }}>Carregando mapa…</p> : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16, alignItems: 'start' }}>
              {/* Árvore de telas */}
              <div style={S.card}>
                <div style={{ display: 'flex', gap: 14, marginBottom: 14, flexWrap: 'wrap', fontSize: 11.5 }}>
                  {Object.entries(STATUS_COLOR).map(([k, col]) => (
                    <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#9AA5B3' }}>
                      <span style={{ width: 9, height: 9, borderRadius: 3, background: col }} />
                      {k === 'complete' ? 'completa' : k === 'partial' ? 'parcial' : k === 'drift' ? 'mudou' : k === 'app_form' ? 'app nativo' : 'não visto'}
                    </span>
                  ))}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '68vh', overflowY: 'auto' }}>
                  {Object.values(map.nodes || {}).map((n) => {
                    const col = STATUS_COLOR[n.status || 'unknown'] || '#5B6472';
                    return (
                      <div key={n.hash} style={{ borderLeft: `3px solid ${col}`, background: '#0E141C', borderRadius: 8, padding: '10px 12px' }}>
                        <p style={{ fontSize: 12.5, margin: 0, color: '#D6DEE9', lineHeight: 1.4 }}>{n.text}</p>
                        {(n.options || []).length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                            {n.options.map((o, i) => {
                              const gap = o.confidence === 'gap';
                              return (
                                <span key={i} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, border: `1px solid ${gap ? '#3A2E1A' : '#1E3326'}`, background: gap ? '#221A0E' : '#10201A', color: gap ? '#E2A94F' : '#8FCFAB' }}>
                                  {o.label}{gap ? ' ·?' : ' ✓'}
                                </span>
                              );
                            })}
                          </div>
                        )}
                        <span style={{ fontSize: 10.5, color: '#5B6472' }}>{n.kind}{n.samples ? ` · visto ${n.samples}x` : ''}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              {/* Feed "O que falta" */}
              <div style={{ ...S.card }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
                  <AlertTriangle size={15} color="#E2A94F" />
                  <p style={{ fontSize: 13.5, fontWeight: 700, margin: 0 }}>O que falta mapear</p>
                </div>
                {gaps.length === 0 ? (
                  <p style={{ fontSize: 12, color: '#43C08C' }}>Tudo que apareceu já foi percorrido. 🎉</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <p style={{ fontSize: 11.5, color: '#8A93A3', margin: 0 }}>
                      Opções que a URA oferece mas que ninguém percorreu ainda. Peça às atendentes para, se aparecer, escolher estas:
                    </p>
                    {gaps.map((g, i) => (
                      <div key={i} style={{ background: '#0E141C', borderRadius: 8, padding: '8px 10px' }}>
                        <p style={{ fontSize: 11.5, color: '#B9C2CE', margin: 0 }}>{g.screen}…</p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 5 }}>
                          {g.missing.map((m, j) => (
                            <span key={j} style={{ fontSize: 11, padding: '2px 7px', borderRadius: 20, background: '#221A0E', color: '#E2A94F', border: '1px solid #3A2E1A' }}>{m}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {map.coverage && (
                  <p style={{ fontSize: 11, color: '#5B6472', marginTop: 14 }}>
                    {map.coverage.options_covered}/{map.coverage.options_total} opções percorridas · {map.coverage.nodes} telas
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      <style>{`.spin{animation:sp 1s linear infinite}@keyframes sp{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
