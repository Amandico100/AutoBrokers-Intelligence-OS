'use client';

// SPEC-038 — ATLAS de Rotas v2 (admin-only). Árvore interativa fiel à sequência
// real das URAs (founder 18/07): guarda-chuva que abre da primeira pergunta,
// clique na opção → revela a próxima tela; lacunas em âmbar a partir de onde a
// rota não existe; expandir/colapsar tudo; modal lateral com a sequência escrita.

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Map as MapIcon, RefreshCw, ChevronRight, AlertTriangle, ListTree,
  ScrollText, X, Maximize2, Minimize2, MousePointerClick, PencilLine, Repeat,
} from 'lucide-react';

type Card = {
  id: string; insurer_key: string; ramo: string; status: string; source: string;
  nodes: number; coverage_pct: number; sessions: number; updated_at: string;
};
type Variant = { to: string; count: number };
type Opt = {
  label: string; leads_to: string | null; confidence?: string;
  seen_count?: number; variants?: Variant[];
};
type Node = {
  hash: string; text: string; kind: string; status?: string; options: Opt[];
  samples?: number; order?: number; answer_hint?: { placeholder: string; instrucao: string };
};
type Edge = { src: string; label: string; to: string; count: number; inferred?: boolean; order?: number; dests?: Record<string, number> };
type PathStep = { n: string; c: string | null };
type MapObj = {
  root: string | null; nodes: Record<string, Node>; edges?: Record<string, Edge>;
  coverage?: { options_total: number; options_covered: number; pct: number; nodes: number };
  paths?: { at: string | null; steps: PathStep[] }[];
  meta?: { sessions?: number };
};

const BRAND: Record<string, { bg: string; mono: string }> = {
  porto: { bg: '#00A1FC', mono: 'P' }, allianz: { bg: '#003781', mono: 'A' },
  azul: { bg: '#0072CE', mono: 'Az' }, bradesco: { bg: '#CC092F', mono: 'B' },
  hdi: { bg: '#00714B', mono: 'H' }, itau: { bg: '#EC7000', mono: 'It' },
  mapfre: { bg: '#D81E05', mono: 'M' }, tokio: { bg: '#00A650', mono: 'TM' },
  yelum: { bg: '#5B2D90', mono: 'Y' }, youse: { bg: '#F65C78', mono: 'Yo' },
  zurich: { bg: '#2167AE', mono: 'Z' }, alfa: { bg: '#004B8D', mono: 'Al' },
};
const brand = (k: string) => BRAND[k] || { bg: '#334155', mono: (k || '?')[0].toUpperCase() };

const C = {
  ok: '#43C08C', gap: '#E2A94F', drift: '#E0574B', app: '#B48EAD',
  dim: '#5B6472', blue: '#7FB7E8', border: '#161D28', card: '#0B0F15', bg2: '#0E141C',
};
const S = {
  page: { background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' } as React.CSSProperties,
  card: { background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, padding: 16 } as React.CSSProperties,
  btn: { display: 'flex', alignItems: 'center', gap: 6, background: '#12202E', border: '1px solid #22384C', color: '#CFE0F0', borderRadius: 10, padding: '8px 12px', cursor: 'pointer', fontSize: 12.5 } as React.CSSProperties,
};
const pct = (n: number) => `${Math.round(n || 0)}%`;

// ------------------------------------------------------------------ //
// Árvore: um nó (tela) + opções; clique na opção expande o destino.
// ------------------------------------------------------------------ //
function kindLabel(kind: string): { label: string; icon: React.ReactNode } {
  if (kind === 'menu') return { label: 'menu — clique numa opção', icon: <MousePointerClick size={11} /> };
  if (kind === 'pergunta') return { label: 'pergunta — resposta digitada', icon: <PencilLine size={11} /> };
  if (kind === 'app_form') return { label: 'APP NATIVO — formulário', icon: <AlertTriangle size={11} /> };
  return { label: kind, icon: null };
}

function NodeCard({
  nid, mapObj, depth, pathKey, visited, expanded, toggle,
}: {
  nid: string; mapObj: MapObj; depth: number; pathKey: string;
  visited: Set<string>; expanded: Set<string>; toggle: (k: string) => void;
}) {
  const node = mapObj.nodes[nid];
  if (!node) return null;
  const col = node.status === 'complete' ? C.ok : node.status === 'app_form' ? C.app
    : node.status === 'partial' ? C.gap : C.dim;
  const kl = kindLabel(node.kind);

  // continuação sequencial (a URA emenda telas sem esperar clique)
  const seqEdge = Object.values(mapObj.edges || {}).find(
    (e) => e.src === nid && e.label === '→');
  const nextVisited = new Set(visited); nextVisited.add(nid);

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ background: C.bg2, border: `1px solid ${C.border}`, borderLeft: `3px solid ${col}`, borderRadius: 10, padding: '11px 13px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, color: col, display: 'flex', alignItems: 'center', gap: 4, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>
            {kl.icon} {kl.label}
          </span>
          {node.samples ? <span style={{ fontSize: 10, color: C.dim }}>visto {node.samples}x</span> : null}
        </div>
        <p style={{ fontSize: 12.5, margin: 0, color: '#D6DEE9', lineHeight: 1.45, whiteSpace: 'pre-line' }}>{node.text}</p>

        {node.answer_hint && (
          <div style={{ marginTop: 8, background: '#101C2A', border: '1px solid #1D3450', borderRadius: 8, padding: '7px 10px', fontSize: 11.5, color: '#9FC2E4', display: 'flex', gap: 7, alignItems: 'center' }}>
            <PencilLine size={12} />
            <span><b style={{ color: '#CFE4F8' }}>Responder com {node.answer_hint.placeholder}</b> — {node.answer_hint.instrucao}</span>
          </div>
        )}

        {(node.options || []).length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
            {node.options.map((o, i) => {
              const key = `${pathKey}/${o.label}`;
              const gap = o.confidence === 'gap';
              const open = expanded.has(key);
              const loops = o.leads_to ? visited.has(o.leads_to) : false;
              const variants = o.variants && o.variants.length > 1 ? o.variants : null;
              return (
                <div key={i}>
                  <button
                    onClick={() => toggle(key)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 7, width: '100%', textAlign: 'left',
                      background: gap ? '#221A0E' : '#10201A',
                      border: `1px solid ${gap ? '#3A2E1A' : '#1E3326'}`,
                      color: gap ? C.gap : '#8FCFAB', borderRadius: 8, padding: '6px 10px',
                      fontSize: 12, cursor: 'pointer',
                    }}
                  >
                    <ChevronRight size={13} style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s', flexShrink: 0 }} />
                    <span style={{ flex: 1 }}>{o.label}</span>
                    {variants && <span title="Nem sempre leva à mesma tela" style={{ fontSize: 10, color: C.gap, display: 'flex', alignItems: 'center', gap: 3 }}><Repeat size={10} /> varia</span>}
                    {o.seen_count ? <span style={{ fontSize: 10, color: C.dim }}>{o.seen_count}x</span> : null}
                    {gap && <span style={{ fontSize: 10, fontWeight: 700 }}>NÃO MAPEADO</span>}
                    {!gap && !variants && <span style={{ fontSize: 11 }}>✓</span>}
                  </button>

                  {open && (
                    <div style={{ marginLeft: 14, paddingLeft: 14, borderLeft: `2px solid ${gap ? '#3A2E1A' : '#22384C'}`, marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {gap ? (
                        <div style={{ border: `1px dashed ${C.gap}`, borderRadius: 8, padding: '9px 11px', fontSize: 11.5, color: C.gap, background: '#1A150C' }}>
                          🔍 Rota ainda não observada. Quando uma atendente escolher &quot;{o.label}&quot; num atendimento real, o Observador desenha o que vem depois.
                        </div>
                      ) : loops ? (
                        <div style={{ fontSize: 11.5, color: C.dim, padding: '4px 2px', display: 'flex', gap: 5, alignItems: 'center' }}>
                          <Repeat size={11} /> retorna a uma tela anterior do fluxo
                        </div>
                      ) : variants ? (
                        variants.map((v, vi) => {
                          const total = variants.reduce((s, x) => s + x.count, 0) || 1;
                          return (
                            <div key={vi}>
                              <p style={{ fontSize: 10.5, color: C.gap, margin: '2px 0 4px', fontWeight: 600 }}>
                                Variante {vi + 1} — aconteceu em {Math.round((100 * v.count) / total)}% das vezes
                                {vi === 0 ? '' : ' (ex.: seguradora já tinha o dado salvo)'}
                              </p>
                              <NodeCard nid={v.to} mapObj={mapObj} depth={depth + 1} pathKey={`${key}#${vi}`} visited={nextVisited} expanded={expanded} toggle={toggle} />
                            </div>
                          );
                        })
                      ) : o.leads_to ? (
                        <NodeCard nid={o.leads_to} mapObj={mapObj} depth={depth + 1} pathKey={key} visited={nextVisited} expanded={expanded} toggle={toggle} />
                      ) : null}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {seqEdge && !visited.has(seqEdge.to) && depth < 40 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '4px 0 4px 18px', color: C.dim, fontSize: 10.5 }}>
            <span style={{ width: 2, height: 14, background: '#22384C', display: 'inline-block' }} />
            continua ↓
          </div>
          <NodeCard nid={seqEdge.to} mapObj={mapObj} depth={depth + 1} pathKey={`${pathKey}/->`} visited={nextVisited} expanded={expanded} toggle={toggle} />
        </div>
      )}
    </div>
  );
}

// coleta todas as chaves expansíveis (p/ Expandir tudo), com guarda de ciclo
function collectKeys(mapObj: MapObj, nid: string | null, pathKey: string, visited: Set<string>, acc: Set<string>, depth = 0) {
  if (!nid || depth > 40) return;
  const node = mapObj.nodes[nid];
  if (!node) return;
  const nv = new Set(visited); nv.add(nid);
  for (const o of node.options || []) {
    const key = `${pathKey}/${o.label}`;
    acc.add(key);
    if (o.variants && o.variants.length > 1) {
      o.variants.forEach((v, vi) => { if (!nv.has(v.to)) collectKeys(mapObj, v.to, `${key}#${vi}`, nv, acc, depth + 1); });
    } else if (o.leads_to && !nv.has(o.leads_to)) {
      collectKeys(mapObj, o.leads_to, key, nv, acc, depth + 1);
    }
  }
  const seq = Object.values(mapObj.edges || {}).find((e) => e.src === nid && e.label === '→');
  if (seq && !nv.has(seq.to)) collectKeys(mapObj, seq.to, `${pathKey}/->`, nv, acc, depth + 1);
}

export default function AtlasPage() {
  const [cards, setCards] = useState<Card[] | null>(null);
  const [sel, setSel] = useState<{ insurer: string; ramo: string } | null>(null);
  const [map, setMap] = useState<MapObj | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showTranscript, setShowTranscript] = useState(false);

  const load = useCallback(() => {
    fetch('/api/admin/atlas/maps').then((r) => r.json()).then((j) => setCards(j.cards || [])).catch(() => setCards([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const openMap = (insurer: string, ramo: string) => {
    setSel({ insurer, ramo }); setMap(null); setExpanded(new Set()); setShowTranscript(false);
    fetch(`/api/admin/atlas/map/${insurer}/${ramo}`).then((r) => r.json())
      .then((j) => setMap(j.map || null)).catch(() => setMap(null));
  };

  const runWeave = async () => {
    setBusy(true); setNotice('Tecendo os mapas a partir das observações…');
    try {
      const r = await fetch('/api/admin/atlas/weave', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const j = await r.json();
      setNotice(j.ok ? `Tecido: ${(j.woven || []).length || 1} seguradora(s).` : 'Falha ao tecer.');
      if (sel) openMap(sel.insurer, sel.ramo); else load();
    } catch { setNotice('Falha ao tecer.'); } finally { setBusy(false); }
  };

  const toggle = (k: string) => setExpanded((prev) => {
    const n = new Set(prev);
    if (n.has(k)) n.delete(k); else n.add(k);
    return n;
  });
  const expandAll = () => {
    if (!map) return;
    const acc = new Set<string>();
    collectKeys(map, map.root, 'r', new Set(), acc);
    setExpanded(acc);
  };
  const collapseAll = () => setExpanded(new Set());

  const gaps = useMemo(() => {
    if (!map) return [];
    const out: { screen: string; missing: string[] }[] = [];
    const ordered = Object.values(map.nodes || {}).sort((a, b) => (a.order || 0) - (b.order || 0));
    for (const n of ordered) {
      const missing = (n.options || []).filter((o) => o.confidence === 'gap').map((o) => o.label);
      if (missing.length) out.push({ screen: n.text.slice(0, 60), missing });
    }
    return out;
  }, [map]);

  const orphans = useMemo(() => {
    if (!map || !map.root) return [];
    const reach = new Set<string>();
    const stack = [map.root];
    while (stack.length) {
      const nid = stack.pop()!;
      if (reach.has(nid)) continue;
      reach.add(nid);
      const node = map.nodes[nid];
      for (const o of node?.options || []) {
        if (o.leads_to) stack.push(o.leads_to);
        (o.variants || []).forEach((v) => stack.push(v.to));
      }
      Object.values(map.edges || {}).forEach((e) => { if (e.src === nid) stack.push(e.to); });
    }
    return Object.keys(map.nodes).filter((nid) => !reach.has(nid))
      .sort((a, b) => (map.nodes[a].order || 0) - (map.nodes[b].order || 0));
  }, [map]);

  return (
    <div style={S.page}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <MapIcon size={22} color={C.blue} />
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Atlas de Rotas</h1>
            <p style={{ fontSize: 12.5, color: '#8A93A3', margin: '2px 0 0' }}>
              Mapa vivo dos WhatsApps das seguradoras — na sequência real. Inteligência AutoBrokers (admin-only).
            </p>
          </div>
        </div>
        <button onClick={runWeave} disabled={busy} style={S.btn}>
          <RefreshCw size={14} className={busy ? 'spin' : ''} /> {busy ? 'Tecendo…' : 'Tecer mapas'}
        </button>
      </div>
      {notice && <p style={{ fontSize: 12.5, color: C.blue, margin: '4px 0 14px' }}>{notice}</p>}

      {!sel && (
        cards === null ? <p style={{ color: '#8A93A3', marginTop: 20 }}>Carregando…</p> :
          cards.length === 0 ? (
            <div style={{ ...S.card, marginTop: 16, textAlign: 'center', padding: 30 }}>
              <p style={{ fontSize: 14, fontWeight: 600 }}>Nenhum mapa ainda.</p>
              <p style={{ fontSize: 12.5, color: '#8A93A3', maxWidth: 460, margin: '6px auto 0' }}>
                Assim que o Observador capturar atendimentos com seguradoras, clique em &quot;Tecer mapas&quot; para desenhar as rotas aqui.
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12, marginTop: 16 }}>
              {cards.map((c) => {
                const b = brand(c.insurer_key);
                const cov = c.coverage_pct || 0;
                const covColor = cov >= 80 ? C.ok : cov >= 40 ? C.gap : C.drift;
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
                      <div style={{ height: 6, background: C.border, borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ width: pct(cov), height: '100%', background: covColor }} />
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                        <span style={{ fontSize: 11.5, color: covColor, fontWeight: 600 }}>{pct(cov)} percorrido</span>
                        <span style={{ fontSize: 11.5, color: '#8A93A3', display: 'flex', alignItems: 'center', gap: 3 }}>Abrir árvore <ChevronRight size={13} /></span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )
      )}

      {sel && (
        <div style={{ marginTop: 8 }}>
          <button onClick={() => { setSel(null); setMap(null); }} style={{ background: 'none', border: 'none', color: '#8A93A3', cursor: 'pointer', fontSize: 12.5, marginBottom: 10 }}>← Todas as seguradoras</button>

          {map === null ? <p style={{ color: '#8A93A3' }}>Carregando mapa…</p> : (
            <>
              {/* Cabeçalho da seguradora */}
              <div style={{ ...S.card, marginBottom: 12, background: `linear-gradient(135deg, ${brand(sel.insurer).bg}22, ${C.card} 55%)` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: brand(sel.insurer).bg, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 16 }}>{brand(sel.insurer).mono}</div>
                  <div style={{ flex: 1, minWidth: 180 }}>
                    <p style={{ fontSize: 16, fontWeight: 700, margin: 0, textTransform: 'capitalize' }}>{sel.insurer} · {sel.ramo}</p>
                    <p style={{ fontSize: 11.5, color: '#8A93A3', margin: '2px 0 0' }}>
                      {map.coverage?.nodes || 0} telas · {map.meta?.sessions || 0} sessões · {map.coverage?.options_covered || 0}/{map.coverage?.options_total || 0} opções percorridas
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button onClick={expandAll} style={S.btn}><Maximize2 size={13} /> Expandir tudo</button>
                    <button onClick={collapseAll} style={S.btn}><Minimize2 size={13} /> Colapsar</button>
                    <button onClick={() => setShowTranscript(true)} style={S.btn}><ScrollText size={13} /> Sequência escrita</button>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 14, marginTop: 12, flexWrap: 'wrap', fontSize: 11 }}>
                  {[[C.ok, 'percorrida ✓'], [C.gap, 'oferecida, não percorrida (lacuna)'], [C.app, 'app nativo'], [C.drift, 'mudou (em breve)'], [C.dim, 'informativa']].map(([col, lab], i) => (
                    <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#9AA5B3' }}>
                      <span style={{ width: 9, height: 9, borderRadius: 3, background: col as string }} /> {lab}
                    </span>
                  ))}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 290px', gap: 14, alignItems: 'start' }}>
                {/* A ÁRVORE (sequência fiel, do início) */}
                <div style={{ ...S.card, padding: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10, color: C.blue, fontSize: 12, fontWeight: 700 }}>
                    <ListTree size={14} /> INÍCIO DO ATENDIMENTO — clique nas opções para abrir a rota
                  </div>
                  {map.root && map.nodes[map.root] ? (
                    <NodeCard nid={map.root} mapObj={map} depth={0} pathKey="r" visited={new Set()} expanded={expanded} toggle={toggle} />
                  ) : (
                    <p style={{ fontSize: 12.5, color: '#8A93A3' }}>Sem raiz identificada ainda — precisa de uma sessão completa desde a saudação.</p>
                  )}

                  {orphans.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <p style={{ fontSize: 11, color: C.dim, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 8 }}>
                        Telas observadas fora do fluxo principal ({orphans.length}) — conectam quando os cliques forem capturados
                      </p>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 300, overflowY: 'auto' }}>
                        {orphans.map((nid) => {
                          const n = map.nodes[nid];
                          return (
                            <div key={nid} style={{ borderLeft: `3px solid ${C.dim}`, background: C.bg2, borderRadius: 8, padding: '7px 10px' }}>
                              <p style={{ fontSize: 11.5, margin: 0, color: '#9AA5B3' }}>{n.text.slice(0, 110)}</p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* O QUE FALTA */}
                <div style={{ ...S.card, position: 'sticky', top: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
                    <AlertTriangle size={15} color={C.gap} />
                    <p style={{ fontSize: 13.5, fontWeight: 700, margin: 0 }}>O que falta mapear</p>
                  </div>
                  {gaps.length === 0 ? (
                    <p style={{ fontSize: 12, color: C.ok }}>Tudo que apareceu já foi percorrido. 🎉</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: '62vh', overflowY: 'auto' }}>
                      <p style={{ fontSize: 11.5, color: '#8A93A3', margin: 0 }}>
                        Opções que a URA oferece mas ninguém percorreu. Peça às atendentes para, se aparecer, escolher estas:
                      </p>
                      {gaps.map((g, i) => (
                        <div key={i} style={{ background: C.bg2, borderRadius: 8, padding: '8px 10px' }}>
                          <p style={{ fontSize: 11.5, color: '#B9C2CE', margin: 0 }}>{g.screen}…</p>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 5 }}>
                            {g.missing.map((mm, j) => (
                              <span key={j} style={{ fontSize: 11, padding: '2px 7px', borderRadius: 20, background: '#221A0E', color: C.gap, border: '1px solid #3A2E1A' }}>{mm}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* MODAL LATERAL — sequência escrita (transcript fiel, sem PII) */}
              {showTranscript && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', zIndex: 50 }} onClick={() => setShowTranscript(false)}>
                  <div onClick={(e) => e.stopPropagation()} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 'min(480px, 92vw)', background: C.card, borderLeft: `1px solid ${C.border}`, padding: 18, overflowY: 'auto' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                      <p style={{ fontSize: 14, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 7 }}><ScrollText size={15} /> Sequência escrita (como aconteceu)</p>
                      <button onClick={() => setShowTranscript(false)} style={{ background: 'none', border: 'none', color: '#8A93A3', cursor: 'pointer' }}><X size={17} /></button>
                    </div>
                    {(map.paths || []).length === 0 ? (
                      <p style={{ fontSize: 12.5, color: '#8A93A3' }}>Sem transcripts ainda.</p>
                    ) : (
                      (map.paths || []).slice().reverse().map((p, pi) => (
                        <div key={pi} style={{ marginBottom: 18 }}>
                          <p style={{ fontSize: 11, color: C.blue, fontWeight: 700, marginBottom: 8 }}>
                            Sessão {String(p.at || '').slice(0, 16).replace('T', ' ') || `#${pi + 1}`}
                          </p>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            {p.steps.map((st, si) => (
                              <div key={si}>
                                <div style={{ background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 8, padding: '7px 10px', fontSize: 11.5, color: '#C7D0DC', whiteSpace: 'pre-line' }}>
                                  {(map.nodes[st.n]?.text || '').slice(0, 220)}
                                </div>
                                {st.c && (
                                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                                    <span style={{ background: '#10201A', border: '1px solid #1E3326', color: '#8FCFAB', borderRadius: 14, padding: '3px 10px', fontSize: 11.5 }}>
                                      👤 {st.c}
                                    </span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
      <style>{`.spin{animation:sp 1s linear infinite}@keyframes sp{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
