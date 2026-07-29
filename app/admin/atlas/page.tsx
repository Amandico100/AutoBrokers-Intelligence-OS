'use client';

// SPEC-038 — ATLAS de Rotas v2 (admin-only). Árvore interativa fiel à sequência
// real das URAs (founder 18/07): guarda-chuva que abre da primeira pergunta,
// clique na opção → revela a próxima tela; lacunas em âmbar a partir de onde a
// rota não existe; expandir/colapsar tudo; modal lateral com a sequência escrita.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Map as MapIcon, RefreshCw, ChevronRight, AlertTriangle, ListTree,
  ScrollText, X, Maximize2, Minimize2, MousePointerClick, PencilLine, Repeat,
  Workflow, ZoomIn, ZoomOut, Crosshair,
} from 'lucide-react';

type Card = {
  id: string; insurer_key: string; ramo: string; status: string; source: string;
  nodes: number; coverage_pct: number; sessions: number; updated_at: string;
};
type Variant = { to: string; count: number };
type Opt = {
  label: string; leads_to: string | null; confidence?: string; acao?: string;
  seen_count?: number; variants?: Variant[];
};
type Node = {
  hash: string; text: string; kind: string; status?: string; options: Opt[];
  samples?: number; order?: number; stale?: boolean; last_seen?: string;
  answer_hint?: { placeholder: string; instrucao: string };
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
        {node.stale && (
          <span style={{ display: 'inline-block', marginTop: 5, fontSize: 10, color: C.gap, border: `1px solid ${C.gap}`, borderRadius: 12, padding: '1px 7px' }}>⏳ tela antiga (menu pode ter mudado)</span>
        )}

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
              const echo = o.confidence === 'echo';
              // Comportamento já conhecido: Voltar volta, Sair encerra, e um
              // horário de agendamento leva à mesma confirmação que qualquer
              // outro. Não é lacuna e não adianta pedir atendimento para isso.
              const conhecida = o.confidence === 'navegacao';
              const ROTULO_ACAO: Record<string, string> = {
                voltar: 'volta à tela anterior', sair: 'encerra o atendimento',
                menu: 'volta ao menu principal', horario: 'escolhe um horário',
              };
              const open = expanded.has(key);
              const loops = o.leads_to ? visited.has(o.leads_to) : false;
              const variants = o.variants && o.variants.length > 1 ? o.variants : null;
              return (
                <div key={i}>
                  <button
                    onClick={() => toggle(key)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 7, width: '100%', textAlign: 'left',
                      background: gap ? '#221A0E' : echo ? '#0E1B2A' : '#10201A',
                      border: `1px solid ${gap ? '#3A2E1A' : echo ? '#1D3450' : '#1E3326'}`,
                      color: gap ? C.gap : echo ? C.blue : '#8FCFAB', borderRadius: 8, padding: '6px 10px',
                      fontSize: 12, cursor: 'pointer',
                    }}
                  >
                    <ChevronRight size={13} style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s', flexShrink: 0 }} />
                    <span style={{ flex: 1 }}>{o.label}</span>
                    {variants && <span title="Nem sempre leva à mesma tela" style={{ fontSize: 10, color: C.gap, display: 'flex', alignItems: 'center', gap: 3 }}><Repeat size={10} /> varia</span>}
                    {o.seen_count ? <span style={{ fontSize: 10, color: C.dim }}>{o.seen_count}x</span> : null}
                    {gap && <span style={{ fontSize: 10, fontWeight: 700 }}>NÃO MAPEADO</span>}
                    {conhecida && <span style={{ fontSize: 10, color: '#7FB79A' }}>{ROTULO_ACAO[String(o.acao || '')] || 'comportamento conhecido'}</span>}
                    {echo && <span style={{ fontSize: 10, fontWeight: 700 }} title="Deduzida pelo eco da tela seguinte (menu digitado)">~✓ deduzida</span>}
                    {!gap && !echo && !variants && <span style={{ fontSize: 11 }}>✓</span>}
                  </button>

                  {open && (
                    <div style={{ marginLeft: 14, paddingLeft: 14, borderLeft: `2px solid ${gap ? '#3A2E1A' : '#22384C'}`, marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {conhecida ? (
                        <div style={{ border: '1px solid #1E3326', borderRadius: 8, padding: '9px 11px', fontSize: 11.5, color: '#8FCFAB', background: '#10201A' }}>
                          ✓ {ROTULO_ACAO[String(o.acao || '')] || 'comportamento conhecido'} — não precisa de atendimento para mapear.
                        </div>
                      ) : gap ? (
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

// ------------------------------------------------------------------ //
// CANVAS (estilo n8n): fundo livre com pan/zoom; organograma que abre
// sob clique — card da pergunta → cards das opções → próxima pergunta.
// ------------------------------------------------------------------ //
type LNode = {
  key: string; type: 'screen' | 'option' | 'stub' | 'loop';
  screenId?: string; opt?: Opt; label?: string; badge?: string;
  x: number; y: number; w: number; h: number; color: string;
  children: LNode[];
};
const CDIM = { screen: [280, 132], option: [200, 48], stub: [220, 84], loop: [180, 42] } as const;
const GX = 28, GY = 66;

function optColor(conf?: string) {
  if (conf === 'gap') return C.gap;
  if (conf === 'echo') return C.blue;
  // `navegacao` = comportamento ja conhecido (Voltar / Sair / escolher horario).
  // Verde porque nao falta nada ali, e com rotulo proprio na legenda porque
  // dizer "percorrida" seria mentira: ninguem percorreu, nos e que sabemos.
  return C.ok;
}

function buildCanvasTree(
  mapObj: MapObj, nid: string, key: string, visited: Set<string>, exp: Set<string>, depth: number,
): LNode {
  const node = mapObj.nodes[nid];
  const [w, h] = CDIM.screen;
  const col = node?.status === 'complete' ? C.ok : node?.status === 'app_form' ? C.app
    : node?.status === 'partial' ? C.gap : C.dim;
  const ln: LNode = { key, type: 'screen', screenId: nid, x: 0, y: 0, w, h, color: col, children: [] };
  if (!node || depth > 30 || !exp.has(key)) return ln;
  const nv = new Set(visited); nv.add(nid);

  if ((node.options || []).length > 0) {
    // TODAS as opções aparecem sempre (pedido do founder) — cada uma é um card
    for (const o of node.options) {
      const okey = `${key}/${o.label}`;
      const [ow, oh] = CDIM.option;
      const oc: LNode = { key: okey, type: 'option', opt: o, label: o.label, x: 0, y: 0, w: ow, h: oh, color: optColor(o.confidence), children: [] };
      if (exp.has(okey)) {
        if (o.confidence === 'navegacao') {
          // Nada a desenhar: "Voltar" volta, "Sair" encerra, e qualquer
          // horario leva a mesma confirmacao. Abrir um "rota nao observada"
          // aqui pediria um atendimento que nao ensina nada.
        } else if (o.confidence === 'gap' || !o.leads_to) {
          const [sw, sh] = CDIM.stub;
          oc.children.push({ key: `${okey}/stub`, type: 'stub', x: 0, y: 0, w: sw, h: sh, color: C.gap, children: [] });
        } else if (o.variants && o.variants.length > 1) {
          const total = o.variants.reduce((s, v) => s + v.count, 0) || 1;
          o.variants.forEach((v, vi) => {
            if (nv.has(v.to)) {
              const [lw, lh] = CDIM.loop;
              oc.children.push({ key: `${okey}#${vi}/loop`, type: 'loop', x: 0, y: 0, w: lw, h: lh, color: C.dim, children: [] });
            } else {
              const child = buildCanvasTree(mapObj, v.to, `${okey}#${vi}`, nv, exp, depth + 1);
              child.badge = `${Math.round((100 * v.count) / total)}%`;
              oc.children.push(child);
            }
          });
        } else if (nv.has(o.leads_to)) {
          const [lw, lh] = CDIM.loop;
          oc.children.push({ key: `${okey}/loop`, type: 'loop', x: 0, y: 0, w: lw, h: lh, color: C.dim, children: [] });
        } else {
          oc.children.push(buildCanvasTree(mapObj, o.leads_to, okey, nv, exp, depth + 1));
        }
      }
      ln.children.push(oc);
    }
  } else {
    // tela sem opções: continua para a próxima (aresta sequencial/eco)
    const seq = Object.values(mapObj.edges || {}).find((e) => e.src === nid && e.label === '→');
    if (seq && !nv.has(seq.to)) {
      ln.children.push(buildCanvasTree(mapObj, seq.to, `${key}/->`, nv, exp, depth + 1));
    }
  }
  return ln;
}

function layoutTree(n: LNode): number {
  // devolve a LARGURA da subárvore e posiciona os filhos relativos (x acumulado depois)
  if (!n.children.length) return n.w;
  const widths = n.children.map((c) => layoutTree(c));
  const total = widths.reduce((s, x) => s + x, 0) + GX * (n.children.length - 1);
  return Math.max(n.w, total);
}

function placeTree(n: LNode, cx: number, y: number, acc: LNode[]) {
  n.x = cx - n.w / 2; n.y = y;
  acc.push(n);
  if (!n.children.length) return;
  const widths = n.children.map((c) => layoutTree(c));
  const total = widths.reduce((s, x) => s + x, 0) + GX * (n.children.length - 1);
  let x = cx - total / 2;
  n.children.forEach((c, i) => {
    const w = widths[i];
    placeTree(c, x + w / 2, y + n.h + GY, acc);
    x += w + GX;
  });
}

function CanvasView({ mapObj, exp, toggle, expandAllKeys }: {
  mapObj: MapObj; exp: Set<string>; toggle: (k: string) => void; expandAllKeys: () => void;
}) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [view, setView] = useState({ x: 80, y: 40, k: 0.85 });
  const drag = useRef<{ on: boolean; sx: number; sy: number; ox: number; oy: number; moved: boolean }>({ on: false, sx: 0, sy: 0, ox: 0, oy: 0, moved: false });

  const flat: LNode[] = useMemo(() => {
    if (!mapObj.root || !mapObj.nodes[mapObj.root]) return [];
    const rootLn = buildCanvasTree(mapObj, mapObj.root, 'r', new Set(), exp, 0);
    const acc: LNode[] = [];
    placeTree(rootLn, 0, 0, acc);
    return acc;
  }, [mapObj, exp]);

  const center = useCallback(() => {
    const bw = boxRef.current?.clientWidth || 900;
    setView({ x: bw / 2, y: 40, k: 0.85 });
  }, []);
  useEffect(() => { center(); }, [center]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = boxRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    setView((v) => {
      const k2 = Math.min(1.8, Math.max(0.2, v.k * (e.deltaY < 0 ? 1.12 : 0.89)));
      return { k: k2, x: mx - ((mx - v.x) * k2) / v.k, y: my - ((my - v.y) * k2) / v.k };
    });
  };
  const onDown = (e: React.MouseEvent) => {
    drag.current = { on: true, sx: e.clientX, sy: e.clientY, ox: view.x, oy: view.y, moved: false };
  };
  const onMove = (e: React.MouseEvent) => {
    if (!drag.current.on) return;
    const dx = e.clientX - drag.current.sx, dy = e.clientY - drag.current.sy;
    if (Math.abs(dx) + Math.abs(dy) > 4) drag.current.moved = true;
    setView((v) => ({ ...v, x: drag.current.ox + dx, y: drag.current.oy + dy }));
  };
  const onUp = () => { drag.current.on = false; };
  const clickNode = (key: string) => { if (!drag.current.moved) toggle(key); };

  return (
    <div
      ref={boxRef}
      onWheel={onWheel} onMouseDown={onDown} onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
      style={{ position: 'relative', height: '72vh', overflow: 'hidden', borderRadius: 12, border: `1px solid ${C.border}`, background: 'radial-gradient(circle, #10151D 1px, #07090D 1px)', backgroundSize: '22px 22px', cursor: drag.current.on ? 'grabbing' : 'grab', userSelect: 'none' }}
    >
      {/* controles */}
      <div style={{ position: 'absolute', top: 10, right: 10, zIndex: 5, display: 'flex', gap: 6 }}>
        <button onClick={() => setView((v) => ({ ...v, k: Math.min(1.8, v.k * 1.15) }))} style={S.btn} title="Zoom +"><ZoomIn size={14} /></button>
        <button onClick={() => setView((v) => ({ ...v, k: Math.max(0.2, v.k * 0.87) }))} style={S.btn} title="Zoom -"><ZoomOut size={14} /></button>
        <button onClick={center} style={S.btn} title="Centralizar"><Crosshair size={14} /></button>
        <button onClick={expandAllKeys} style={S.btn} title="Expandir tudo"><Maximize2 size={13} /></button>
      </div>
      <p style={{ position: 'absolute', bottom: 8, left: 12, zIndex: 5, fontSize: 10.5, color: C.dim, margin: 0 }}>
        Arraste o fundo para mover · role para zoom · clique num card para abrir/fechar a rota
      </p>

      <div style={{ position: 'absolute', transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`, transformOrigin: '0 0' }}>
        {/* conexões */}
        <svg style={{ position: 'absolute', overflow: 'visible', pointerEvents: 'none' }} width={1} height={1}>
          {flat.map((n) => n.children.filter((c) => flat.includes(c)).map((c) => {
            const x1 = n.x + n.w / 2, y1 = n.y + n.h, x2 = c.x + c.w / 2, y2 = c.y;
            const my = (y1 + y2) / 2;
            return <path key={`${n.key}->${c.key}`} d={`M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`} stroke={c.color} strokeWidth={1.6} fill="none" opacity={0.55} />;
          }))}
        </svg>

        {/* cards */}
        {flat.map((n) => {
          if (n.type === 'screen') {
            const node = mapObj.nodes[n.screenId!];
            const hasKids = (node?.options || []).length > 0 || Object.values(mapObj.edges || {}).some((e) => e.src === n.screenId && e.label === '→');
            const open = exp.has(n.key);
            return (
              <div key={n.key} onMouseDown={(e) => e.stopPropagation()} onClick={() => clickNode(n.key)}
                style={{ position: 'absolute', left: n.x, top: n.y, width: n.w, height: n.h, background: C.bg2, border: `1px solid ${C.border}`, borderTop: `3px solid ${n.color}`, borderRadius: 10, padding: '9px 11px', cursor: 'pointer', overflow: 'hidden', boxShadow: '0 3px 14px rgba(0,0,0,.35)' }}>
                {n.badge && <span style={{ position: 'absolute', top: 6, right: 8, fontSize: 9.5, color: C.gap, fontWeight: 700 }}>{n.badge}</span>}
                <p style={{ fontSize: 11.5, color: '#D6DEE9', margin: 0, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 5, WebkitBoxOrient: 'vertical', overflow: 'hidden', whiteSpace: 'pre-line' }}>{node?.text}</p>
                {hasKids && (
                  <span style={{ position: 'absolute', bottom: 5, left: '50%', transform: 'translateX(-50%)', fontSize: 9.5, color: n.color, fontWeight: 700 }}>
                    {open ? '▲ fechar' : `▼ abrir${(node?.options || []).length ? ` (${node!.options.length} opções)` : ''}`}
                  </span>
                )}
              </div>
            );
          }
          if (n.type === 'option') {
            const gap = n.opt?.confidence === 'gap';
            const echo = n.opt?.confidence === 'echo';
            return (
              <div key={n.key} onMouseDown={(e) => e.stopPropagation()} onClick={() => clickNode(n.key)}
                style={{ position: 'absolute', left: n.x, top: n.y, width: n.w, height: n.h, background: gap ? '#221A0E' : echo ? '#0E1B2A' : '#10201A', border: `1.5px solid ${n.color}`, borderRadius: 22, padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7 }}>
                <span style={{ flex: 1, fontSize: 11.5, color: n.color, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n.label}</span>
                <span style={{ fontSize: 9, color: n.color, fontWeight: 700 }}>{gap ? '?' : echo ? '~✓' : '✓'}</span>
              </div>
            );
          }
          if (n.type === 'stub') {
            return (
              <div key={n.key} style={{ position: 'absolute', left: n.x, top: n.y, width: n.w, height: n.h, border: `1.5px dashed ${C.gap}`, borderRadius: 10, padding: '8px 10px', background: '#1A150C' }}>
                <p style={{ fontSize: 10.5, color: C.gap, margin: 0, lineHeight: 1.35 }}>🔍 Rota ainda não observada — será desenhada quando alguém percorrer esta opção num atendimento real.</p>
              </div>
            );
          }
          return (
            <div key={n.key} style={{ position: 'absolute', left: n.x, top: n.y, width: n.w, height: n.h, border: `1px solid ${C.border}`, borderRadius: 20, padding: '6px 10px', background: C.bg2, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Repeat size={11} color={C.dim} />
              <span style={{ fontSize: 10.5, color: C.dim }}>retorna a uma tela anterior</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AtlasPage() {
  const [cards, setCards] = useState<Card[] | null>(null);
  const [sel, setSel] = useState<{ insurer: string; ramo: string } | null>(null);
  const [map, setMap] = useState<MapObj | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showTranscript, setShowTranscript] = useState(false);
  const [viewMode, setViewMode] = useState<'tree' | 'canvas'>('tree');
  const [canvasExp, setCanvasExp] = useState<Set<string>>(new Set(['r']));
  const [drifts, setDrifts] = useState<any[]>([]);
  const [observers, setObservers] = useState<any[]>([]);
  const [nativeForms, setNativeForms] = useState<any[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [sentinelaBusy, setSentinelaBusy] = useState(false);
  const [learningBusy, setLearningBusy] = useState(false);
  const [showCost, setShowCost] = useState(false);
  const [cost, setCost] = useState<any | null>(null);

  useEffect(() => {
    if (showCost && !cost) {
      fetch('/api/admin/atlas/cost-estimate').then((r) => r.json()).then((j) => setCost(j)).catch(() => setCost({ error: true }));
    }
  }, [showCost, cost]);

  useEffect(() => {
    fetch('/api/admin/atlas/drifts').then((r) => r.json()).then((j) => setDrifts(j.drifts || [])).catch(() => {});
    fetch('/api/admin/atlas/onboarding/status').then((r) => r.json()).then((j) => setObservers(j.observers || [])).catch(() => {});
  }, []);

  const runSentinela = async () => {
    setSentinelaBusy(true);
    try {
      await fetch('/api/admin/atlas/sentinela/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const j = await fetch('/api/admin/atlas/drifts').then((r) => r.json());
      setDrifts(j.drifts || []);
      load();
    } finally { setSentinelaBusy(false); }
  };

  const runLearning = async () => {
    setLearningBusy(true);
    setNotice('Enviando para processamento…');
    try {
      const response = await fetch('/api/admin/atlas/espelho/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      const result = await response.json().catch(() => ({}));
      // A MENSAGEM VEM DO SERVIDOR, não é montada aqui.
      //
      // Isto lia `result.processed || result.distilled` — dois campos que a
      // rota nunca devolveu — e caía no texto de erro. Em 29/07/2026 o Founder
      // clicou, a rodada publicou 278 cartas no RAG com sucesso, e a tela
      // disse "não foi possível processar o aprendizado agora".
      //
      // Tela que diz que falhou quando deu certo leva a clicar de novo, e
      // clicar de novo dobra o gasto.
      setNotice(response.ok && result.ok
        ? String(result.mensagem || 'Aprendizado em processamento.')
        : 'Não foi possível iniciar o processamento agora.');
      load();
    } catch {
      setNotice('Não foi possível iniciar o processamento agora.');
    } finally {
      setLearningBusy(false);
    }
  };

  const load = useCallback(() => {
    fetch('/api/admin/atlas/maps').then((r) => r.json()).then((j) => setCards(j.cards || [])).catch(() => setCards([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const openMap = (insurer: string, ramo: string) => {
    setSel({ insurer, ramo }); setMap(null); setExpanded(new Set()); setShowTranscript(false);
    setCanvasExp(new Set(['r'])); setNativeForms(null); setShowForm(false);
    fetch(`/api/admin/atlas/map/${insurer}/${ramo}`).then((r) => r.json())
      .then((j) => setMap(j.map || null)).catch(() => setMap(null));
    fetch(`/api/admin/atlas/native-form/${insurer}`).then((r) => r.json())
      .then((j) => setNativeForms(j.forms || [])).catch(() => setNativeForms([]));
  };

  const toggleCanvas = (k: string) => setCanvasExp((prev) => {
    const n = new Set(prev);
    if (n.has(k)) n.delete(k); else n.add(k);
    return n;
  });
  const canvasExpandAll = () => {
    if (!map || !map.root) return;
    const acc = new Set<string>();
    const walk = (nid: string, key: string, visited: Set<string>, depth: number) => {
      acc.add(key);
      const node = map.nodes[nid];
      if (!node || depth > 30) return;
      const nv = new Set(visited); nv.add(nid);
      if ((node.options || []).length) {
        for (const o of node.options) {
          const okey = `${key}/${o.label}`;
          acc.add(okey);
          if (o.variants && o.variants.length > 1) {
            o.variants.forEach((v, vi) => { if (!nv.has(v.to)) walk(v.to, `${okey}#${vi}`, nv, depth + 1); });
          } else if (o.leads_to && !nv.has(o.leads_to)) {
            walk(o.leads_to, okey, nv, depth + 1);
          }
        }
      } else {
        const seq = Object.values(map.edges || {}).find((e) => e.src === nid && e.label === '→');
        if (seq && !nv.has(seq.to)) walk(seq.to, `${key}/->`, nv, depth + 1);
      }
    };
    walk(map.root, 'r', new Set(), 0);
    setCanvasExp(acc);
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
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={runLearning} disabled={learningBusy} style={S.btn} title="Processa somente os dados novos observados">
            <Workflow size={14} /> {learningBusy ? 'Processando…' : 'Processar aprendizado agora'}
          </button>
          <button onClick={runSentinela} disabled={sentinelaBusy} style={S.btn} title="Tece tudo e checa se alguma seguradora mudou o menu">
            <AlertTriangle size={14} /> {sentinelaBusy ? 'Verificando…' : 'Sentinela'}
          </button>
          <button onClick={runWeave} disabled={busy} style={S.btn}>
            <RefreshCw size={14} className={busy ? 'spin' : ''} /> {busy ? 'Tecendo…' : 'Tecer mapas'}
          </button>
        </div>
      </div>
      {notice && <p style={{ fontSize: 12.5, color: C.blue, margin: '4px 0 14px' }}>{notice}</p>}

      {/* Barra: Observadores ativos + mudanças recentes (Sentinela) */}
      {!sel && (drifts.length > 0 || observers.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: observers.length ? '1fr 1fr' : '1fr', gap: 12, marginBottom: 14 }}>
          {observers.length > 0 && (
            <div style={S.card}>
              <p style={{ fontSize: 12.5, fontWeight: 700, margin: '0 0 8px', display: 'flex', alignItems: 'center', gap: 6 }}>📡 Modo Observação — números pareados</p>
              {observers.map((o, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, padding: '4px 0', color: '#B9C2CE' }}>
                  <span>{o.label || o.instance}</span>
                  <span style={{ color: o.state === 'conectado' ? C.ok : C.gap }}>{o.state}</span>
                </div>
              ))}
            </div>
          )}
          {drifts.length > 0 && (
            <div style={S.card}>
              <p style={{ fontSize: 12.5, fontWeight: 700, margin: '0 0 8px', display: 'flex', alignItems: 'center', gap: 6 }}>🔔 Mudanças de menu detectadas</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 160, overflowY: 'auto' }}>
                {drifts.slice(0, 8).map((d, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: d.severity === 'structural' ? C.drift : C.gap, textTransform: 'uppercase' }}>{d.severity === 'structural' ? 'estrutural' : 'cosmético'}</span>
                    <span style={{ color: '#B9C2CE', textTransform: 'capitalize' }}>{d.insurer_key}</span>
                    <span style={{ color: C.dim, flex: 1 }}>{d.summary}</span>
                    <span style={{ color: d.auto_applied ? C.ok : d.needs_founder ? C.drift : C.dim, fontSize: 10 }}>
                      {d.auto_applied ? '✓ auto-aplicado' : d.needs_founder ? '⚠ revisar' : d.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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
                        <p style={{ fontSize: 11.5, color: '#8A93A3', margin: '2px 0 0' }}>{c.nodes} telas da URA{(c as any).nodes_humano ? ` · ${(c as any).nodes_humano} de conversa com o especialista` : ''} · {c.sessions} sessões observadas</p>
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
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <div style={{ display: 'flex', borderRadius: 10, overflow: 'hidden', border: '1px solid #22384C' }}>
                      <button onClick={() => setViewMode('tree')} style={{ ...S.btn, border: 'none', borderRadius: 0, background: viewMode === 'tree' ? '#1C324A' : '#12202E' }}><ListTree size={13} /> Árvore</button>
                      <button onClick={() => setViewMode('canvas')} style={{ ...S.btn, border: 'none', borderRadius: 0, background: viewMode === 'canvas' ? '#1C324A' : '#12202E' }}><Workflow size={13} /> Canvas</button>
                    </div>
                    {viewMode === 'tree' && <button onClick={expandAll} style={S.btn}><Maximize2 size={13} /> Expandir tudo</button>}
                    {viewMode === 'tree' && <button onClick={collapseAll} style={S.btn}><Minimize2 size={13} /> Colapsar</button>}
                    <button onClick={() => { setViewMode(viewMode === 'canvas' ? 'canvas' : viewMode); setShowCost(true); }} style={S.btn}><span style={{ fontSize: 12 }}>💰 Custo IA</span></button>
                    <button onClick={() => setShowTranscript(true)} style={S.btn}><ScrollText size={13} /> Sequência escrita</button>
                    {nativeForms && nativeForms.length > 0 && (
                      <button onClick={() => setShowForm(true)} style={{ ...S.btn, background: '#241832', border: '1px solid #4A2E6B', color: '#D4B8F0' }} title="Formulário nativo capturado — a chave do app HDI/Yelum">
                        🔓 App nativo capturado
                      </button>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 14, marginTop: 12, flexWrap: 'wrap', fontSize: 11 }}>
                  {[[C.ok, 'percorrida ✓'], [C.blue, 'deduzida pelo eco ~✓'], [C.ok, 'comportamento conhecido (Voltar/Sair/horário)'], [C.gap, 'oferecida, não percorrida (lacuna)'], [C.app, 'app nativo'], [C.drift, 'mudou (em breve)'], [C.dim, 'informativa']].map(([col, lab], i) => (
                    <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#9AA5B3' }}>
                      <span style={{ width: 9, height: 9, borderRadius: 3, background: col as string }} /> {lab}
                    </span>
                  ))}
                </div>
              </div>

              {viewMode === 'canvas' && (
                <CanvasView mapObj={map} exp={canvasExp} toggle={toggleCanvas} expandAllKeys={canvasExpandAll} />
              )}

              <div style={{ display: viewMode === 'tree' ? 'grid' : 'none', gridTemplateColumns: '1fr 290px', gap: 14, alignItems: 'start' }}>
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

              {/* MODAL — estimativa de custo do resolvedor de IA */}
              {showCost && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', zIndex: 50 }} onClick={() => setShowCost(false)}>
                  <div onClick={(e) => e.stopPropagation()} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 'min(460px, 92vw)', background: C.card, borderLeft: `1px solid ${C.border}`, padding: 18, overflowY: 'auto' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>💰 Custo do resolvedor de IA</p>
                      <button onClick={() => setShowCost(false)} style={{ background: 'none', border: 'none', color: '#8A93A3', cursor: 'pointer' }}><X size={17} /></button>
                    </div>
                    <p style={{ fontSize: 11.5, color: '#8A93A3', marginBottom: 12 }}>
                      O modelo forte só resolve o resíduo ambíguo (menus digitados sem eco), uma vez por seguradora. A ingestão do histórico é gratuita (determinística). Custo independe do nº de conversas.
                    </p>
                    {!cost ? <p style={{ fontSize: 12, color: '#8A93A3' }}>Calculando…</p> : cost.error ? <p style={{ fontSize: 12, color: C.drift }}>Falha ao calcular.</p> : (
                      <>
                        <div style={{ background: C.bg2, borderRadius: 8, padding: 12, marginBottom: 12 }}>
                          <p style={{ fontSize: 12.5, margin: 0 }}>Custo total de 1 passada: <b style={{ color: C.ok }}>R$ {cost.total_brl_one_pass}</b></p>
                        </div>
                        {(cost.per_insurer || []).map((p: any, i: number) => (
                          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, padding: '5px 0', borderBottom: `1px solid ${C.border}`, color: '#B9C2CE' }}>
                            <span style={{ textTransform: 'capitalize' }}>{p.insurer_key}</span>
                            <span style={{ color: C.dim }}>{p.ambiguous_edges} ambíguas</span>
                            <span style={{ color: C.ok }}>R$ {p.brl_per_insurer}</span>
                          </div>
                        ))}
                        <p style={{ fontSize: 10.5, color: C.dim, marginTop: 10 }}>Modelo: {(cost.per_insurer || [{}])[0]?.model || 'sonnet'} · dólar R$6</p>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* MODAL — formulário nativo capturado (a Pedra de Roseta) */}
              {showForm && nativeForms && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', zIndex: 50 }} onClick={() => setShowForm(false)}>
                  <div onClick={(e) => e.stopPropagation()} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 'min(540px, 94vw)', background: C.card, borderLeft: `1px solid ${C.border}`, padding: 18, overflowY: 'auto' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                      <p style={{ fontSize: 14, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 7, color: '#D4B8F0' }}>🔓 App nativo — como o humano preencheu</p>
                      <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', color: '#8A93A3', cursor: 'pointer' }}><X size={17} /></button>
                    </div>
                    <p style={{ fontSize: 11.5, color: '#8A93A3', marginBottom: 14 }}>
                      Este é o formulário dentro do WhatsApp (HDI/Yelum). Capturamos o schema e as respostas reais — a referência para a Even atravessar a tela sozinha, sem humano.
                    </p>
                    {nativeForms.map((f, fi) => (
                      <div key={fi} style={{ marginBottom: 16, background: C.bg2, border: `1px solid ${C.border}`, borderRadius: 10, padding: 12 }}>
                        <p style={{ fontSize: 12.5, fontWeight: 700, color: C.app, margin: '0 0 4px' }}>{f.flow_name || 'Formulário'}</p>
                        <p style={{ fontSize: 10.5, color: C.dim, margin: '0 0 10px' }}>flow_id {f.flow_id}</p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {(f.fields || []).map((c: any, ci: number) => (
                            <div key={ci} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                              <span style={{ fontSize: 11.5, color: '#B9C2CE' }}>{c.label || c.name}</span>
                              <span style={{ fontSize: 12, color: C.ok, fontFamily: 'Geist Mono, monospace', background: '#0C1610', border: '1px solid #1E3326', borderRadius: 6, padding: '3px 8px', width: 'fit-content' }}>
                                → {Array.isArray(c.answer) ? c.answer.join(', ') : String(c.answer ?? '—')}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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
