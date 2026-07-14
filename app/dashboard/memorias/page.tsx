'use client';

// SPEC-036 Etapa 3 — MEMÓRIAS (Segundo Cérebro): grafo vivo do conhecimento,
// implementado a partir do design do Claude Design (Memórias.dc.html) com
// DADOS REAIS (/api/dashboard/memorias). Dourado=Global · Azul=Corretora ·
// Verde=Pessoal. Hover acende as conexões; clique abre o painel; busca filtra.

import { useEffect, useRef, useState } from 'react';

type Item = { id: string; name: string; tema: string; at?: string };
type Node = {
  id: string; name: string; layer: 'global' | 'corretora' | 'pessoal'; tema: string;
  hub?: boolean; col: string; r: number; x: number; y: number; vx: number; vy: number;
  ax: number; ay: number; ag: number; q: number;
};

const LAYER = {
  global: { col: '#E2A94F', label: 'Global AutoBrokers' },
  corretora: { col: '#5D9BE0', label: 'Corretora' },
  pessoal: { col: '#43C08C', label: 'Pessoal' },
} as const;

const mono = 'Geist Mono, monospace';

export default function MemoriasPage() {
  const cvRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<any>({ nodes: [], edges: [], adj: new Map(), cam: { x: 0, y: 0, k: 0.85 }, alpha: 1 });
  const [counts, setCounts] = useState({ mem: 0, con: 0 });
  const [sel, setSel] = useState<Node | null>(null);
  const [query, setQuery] = useState('');
  const [layerFilter, setLayerFilter] = useState<'all' | 'global' | 'corretora' | 'pessoal'>('all');
  const [empty, setEmpty] = useState(false);
  const queryRef = useRef(''); const layerRef = useRef('all'); const hovRef = useRef<Node | null>(null); const selRef = useRef<Node | null>(null);
  queryRef.current = query.toLowerCase(); layerRef.current = layerFilter; selRef.current = sel;

  useEffect(() => {
    let raf = 0;
    const st = stateRef.current;

    const build = (data: any) => {
      const nodes: Node[] = []; const edges: { a: Node; b: Node }[] = [];
      let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
      const clusters: { key: 'global' | 'corretora' | 'pessoal'; items: Item[]; byTema: Map<string, Item[]> }[] = [
        { key: 'global', items: data.global || [], byTema: new Map() },
        { key: 'corretora', items: [...(data.corretora || []), ...(data.clientes || [])], byTema: new Map() },
        { key: 'pessoal', items: data.pessoal || [], byTema: new Map() },
      ];
      let totalLeaves = 0;
      clusters.forEach((c) => c.items.forEach((it) => {
        const t = it.tema || 'Geral';
        if (!c.byTema.has(t)) c.byTema.set(t, []);
        c.byTema.get(t)!.push(it); totalLeaves++;
      }));
      setEmpty(totalLeaves === 0);
      let angle = -Math.PI / 2;
      const hubCount = clusters.reduce((a, c) => a + c.byTema.size, 0) || 1;
      clusters.forEach((c) => {
        c.byTema.forEach((items, tema) => {
          const rad = 300 + rnd() * 120;
          const ax = Math.cos(angle) * rad, ay = Math.sin(angle) * rad * 0.72;
          angle += (2 * Math.PI) / hubCount;
          const hub: Node = { id: `hub-${c.key}-${tema}`, name: tema, layer: c.key, tema, hub: true, col: LAYER[c.key].col, r: 12, x: ax * 0.2, y: ay * 0.2, vx: 0, vy: 0, ax, ay, ag: 0.05, q: 46 };
          nodes.push(hub);
          items.slice(0, 60).forEach((it) => {
            const n: Node = { id: it.id, name: it.name, layer: c.key, tema, col: LAYER[c.key].col, r: 3.5 + rnd() * 3.5, x: ax + (rnd() - 0.5) * 80, y: ay + (rnd() - 0.5) * 80, vx: 0, vy: 0, ax, ay, ag: 0.004, q: 14 };
            nodes.push(n); edges.push({ a: hub, b: n });
          });
        });
      });
      const adj = new Map<Node, Node[]>();
      nodes.forEach((n) => adj.set(n, []));
      edges.forEach((e) => { adj.get(e.a)!.push(e.b); adj.get(e.b)!.push(e.a); });
      st.nodes = nodes; st.edges = edges; st.adj = adj; st.alpha = 1;
      setCounts({ mem: totalLeaves, con: edges.length });
    };

    fetch('/api/dashboard/memorias').then((r) => r.json()).then((d) => { if (d?.ok) build(d); }).catch(() => {});

    const cv = cvRef.current!; const ctx = cv.getContext('2d')!;
    let W = 0, H = 0;
    const resize = () => {
      const p = cv.parentElement!; W = p.clientWidth; H = p.clientHeight;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = W * dpr; cv.height = H * dpr; cv.style.width = `${W}px`; cv.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize(); window.addEventListener('resize', resize);

    const sx = (n: Node) => (n.x - st.cam.x) * st.cam.k + W / 2;
    const sy = (n: Node) => (n.y - st.cam.y) * st.cam.k + H / 2;

    const pick = (mx: number, my: number): Node | null => {
      let best: Node | null = null; let bd = 1e9;
      for (const n of st.nodes as Node[]) {
        const d = Math.hypot(sx(n) - mx, sy(n) - my);
        if (d < n.r * st.cam.k + 8 && d < bd) { best = n; bd = d; }
      }
      return best;
    };
    let drag: { mx: number; my: number; cx: number; cy: number; moved: boolean } | null = null;
    const local = (e: PointerEvent | WheelEvent) => { const rc = cv.getBoundingClientRect(); return [e.clientX - rc.left, e.clientY - rc.top]; };
    cv.onpointerdown = (e) => { const [mx, my] = local(e); drag = { mx, my, cx: st.cam.x, cy: st.cam.y, moved: false }; };
    window.onpointermove = (e) => {
      const [mx, my] = local(e);
      if (drag) {
        if (Math.abs(mx - drag.mx) + Math.abs(my - drag.my) > 4) drag.moved = true;
        st.cam.x = drag.cx - (mx - drag.mx) / st.cam.k; st.cam.y = drag.cy - (my - drag.my) / st.cam.k;
        return;
      }
      hovRef.current = pick(mx, my);
      cv.style.cursor = hovRef.current ? 'pointer' : 'grab';
    };
    window.onpointerup = (e) => {
      if (drag && !drag.moved) { const [mx, my] = local(e as PointerEvent); setSel(pick(mx, my)); }
      drag = null;
    };
    cv.onwheel = (e) => {
      e.preventDefault();
      st.cam.k = Math.max(0.35, Math.min(3, st.cam.k * Math.exp(-e.deltaY * 0.0011)));
    };

    const loop = (t: number) => {
      raf = requestAnimationFrame(loop);
      const N = st.nodes as Node[]; const A = (st.alpha = Math.max(0.03, st.alpha * 0.995));
      for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {
        const n = N[i], m = N[j];
        let dx = n.x - m.x, dy = n.y - m.y; let d2 = dx * dx + dy * dy;
        if (d2 > 36000) continue; if (d2 < 4) { dx = 1; dy = 1; d2 = 2; }
        const f = ((n.q * m.q) / d2) * 0.06 * A;
        n.vx += dx * f; n.vy += dy * f; m.vx -= dx * f; m.vy -= dy * f;
      }
      for (const e of st.edges) {
        const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y; const d = Math.hypot(dx, dy) || 1;
        const f = (d - 70) * 0.012 * A;
        e.a.vx += (dx / d) * f; e.a.vy += (dy / d) * f; e.b.vx -= (dx / d) * f; e.b.vy -= (dy / d) * f;
      }
      for (const n of N) {
        n.vx += (n.ax - n.x) * n.ag * A; n.vy += (n.ay - n.y) * n.ag * A;
        n.vx *= 0.85; n.vy *= 0.85; n.x += n.vx * 2; n.y += n.vy * 2;
      }
      ctx.clearRect(0, 0, W, H); ctx.fillStyle = '#06080C'; ctx.fillRect(0, 0, W, H);
      const focus = hovRef.current || selRef.current;
      const nb = focus ? new Set(st.adj.get(focus) || []) : null;
      const q = queryRef.current; const lf = layerRef.current;
      for (const n of N) {
        let a = 1;
        if (lf !== 'all' && n.layer !== lf) a *= 0.07;
        if (q) a *= n.name.toLowerCase().includes(q) ? 1 : (n.hub ? 0.2 : 0.05);
        if (nb) a *= n === focus || nb.has(n) ? 1 : 0.08;
        (n as any)._a = a;
      }
      for (const e of st.edges) {
        const ea = Math.min((e.a as any)._a, (e.b as any)._a); if (ea < 0.03) continue;
        const hot = nb && (e.a === focus || e.b === focus);
        ctx.globalAlpha = hot ? 0.9 : 0.22 * ea;
        ctx.strokeStyle = hot ? e.b.col : '#33445C'; ctx.lineWidth = hot ? 1.4 : 0.7;
        ctx.beginPath(); ctx.moveTo(sx(e.a), sy(e.a)); ctx.lineTo(sx(e.b), sy(e.b)); ctx.stroke();
      }
      for (const n of N) {
        const a = (n as any)._a; if (a < 0.02) continue;
        const x = sx(n), y = sy(n), r = Math.max(1.6, n.r * st.cam.k);
        ctx.globalAlpha = a * 0.45;
        ctx.fillStyle = n.col; ctx.beginPath(); ctx.arc(x, y, r * 2.2, 0, 6.283); ctx.fill();
        ctx.globalAlpha = a; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.283); ctx.fill();
        if (n.hub) {
          ctx.font = `600 11px ${mono}`; ctx.textAlign = 'center';
          ctx.fillStyle = `rgba(231,235,241,${0.9 * a})`;
          ctx.fillText(n.name.toUpperCase().slice(0, 22), x, y + r + 16);
        } else if ((st.cam.k > 1.4 || n === focus) && a > 0.4) {
          ctx.font = '500 10px Geist, sans-serif'; ctx.textAlign = 'center';
          ctx.fillStyle = `rgba(185,194,207,${0.85 * a})`;
          ctx.fillText(n.name.length > 32 ? `${n.name.slice(0, 31)}…` : n.name, x, y + r + 12);
        }
      }
      const hov = hovRef.current;
      if (hov && !hov.hub) {
        const x = sx(hov), y = sy(hov);
        ctx.font = '600 12px Geist, sans-serif';
        const w = ctx.measureText(hov.name).width + 26;
        let tx = x + 14; if (tx + w > W - 10) tx = x - w - 14;
        ctx.globalAlpha = 1; ctx.fillStyle = 'rgba(10,13,19,0.94)'; ctx.strokeStyle = '#243044';
        ctx.beginPath(); (ctx as any).roundRect(tx, y - 34, w, 26, 8); ctx.fill(); ctx.stroke();
        ctx.fillStyle = hov.col; ctx.fillRect(tx, y - 34, 3, 26);
        ctx.textAlign = 'left'; ctx.fillStyle = '#E7EBF1'; ctx.fillText(hov.name, tx + 12, y - 16);
      }
      ctx.globalAlpha = 1;
    };
    raf = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); window.onpointermove = null; window.onpointerup = null; };
  }, []);

  const chip = (active: boolean, col: string): React.CSSProperties => ({
    fontFamily: mono, fontSize: 10.5, letterSpacing: '0.08em', textTransform: 'uppercase',
    padding: '5px 11px', borderRadius: 999, cursor: 'pointer', userSelect: 'none',
    background: active ? 'rgba(20,28,40,0.9)' : 'rgba(13,17,24,0.7)',
    border: `1px solid ${active ? col : '#1E2634'}`, color: active ? col : '#7C8798',
  });

  const conns = sel ? (stateRef.current.adj.get(sel) || []).slice(0, 8) : [];

  return (
    <div style={{ position: 'relative', height: 'calc(100vh - 0px)', background: '#06080C', overflow: 'hidden', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <canvas ref={cvRef} style={{ position: 'absolute', inset: 0, cursor: 'grab' }} />
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, padding: '18px 22px 0', pointerEvents: 'none' }}>
        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 21, fontWeight: 650, display: 'flex', gap: 10, alignItems: 'center' }}>
              Memórias
              <span style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.12em', color: '#7FB7E8', border: '1px solid #24405C', borderRadius: 999, padding: '3px 9px', textTransform: 'uppercase' }}>segundo cérebro</span>
            </div>
            <div style={{ fontFamily: mono, fontSize: 12, color: '#7C8798', marginTop: 4 }}>{counts.mem} memórias · {counts.con} conexões · vivo</div>
          </div>
          <div style={{ flex: 1 }} />
          <input
            value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Pesquise em tudo que eu sei sobre o seu negócio…"
            style={{ pointerEvents: 'auto', width: 340, maxWidth: '42vw', background: 'rgba(13,17,24,0.85)', border: '1px solid #1E2634', borderRadius: 12, padding: '10px 14px', color: '#E7EBF1', fontSize: 13 }}
          />
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 12, pointerEvents: 'auto', flexWrap: 'wrap' }}>
          {([['all', 'Tudo', '#C6CEDA'], ['global', 'Global', '#E2A94F'], ['corretora', 'Corretora', '#5D9BE0'], ['pessoal', 'Pessoal', '#43C08C']] as const).map(([id, label, col]) => (
            <span key={id} style={chip(layerFilter === id, col)} onClick={() => setLayerFilter(id as any)}>{label}</span>
          ))}
        </div>
      </div>

      <div style={{ position: 'absolute', left: 22, bottom: 18, background: 'rgba(10,13,19,0.78)', border: '1px solid #161D28', borderRadius: 12, padding: '12px 14px', fontSize: 11.5, color: '#A9B2C0', pointerEvents: 'none' }}>
        <div style={{ display: 'flex', gap: 9, alignItems: 'center' }}><span style={{ width: 9, height: 9, background: '#E2A94F', transform: 'rotate(45deg)', borderRadius: 1.5 }} /> Global AutoBrokers</div>
        <div style={{ display: 'flex', gap: 9, alignItems: 'center', marginTop: 6 }}><span style={{ width: 9, height: 9, background: '#5D9BE0', borderRadius: '50%' }} /> Corretora e clientes</div>
        <div style={{ display: 'flex', gap: 9, alignItems: 'center', marginTop: 6 }}><span style={{ width: 9, height: 9, background: '#43C08C', borderRadius: '50%' }} /> Pessoal — o que a IA aprendeu de você</div>
      </div>
      <div style={{ position: 'absolute', right: 22, bottom: 18, fontFamily: mono, fontSize: 11, color: '#485364', pointerEvents: 'none' }}>arraste · role para aproximar</div>

      {empty && (
        <div style={{ position: 'absolute', left: '50%', bottom: 90, transform: 'translateX(-50%)', width: 420, background: 'rgba(11,14,20,0.9)', border: '1px solid #1D2532', borderRadius: 16, padding: '20px 22px', textAlign: 'center' }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>Seu segundo cérebro acabou de nascer</div>
          <div style={{ fontSize: 12.5, color: '#8A93A3', marginTop: 6, lineHeight: 1.55 }}>Cada documento e conversa vira uma nova estrela. Suba conhecimento em Personalização → Conhecimento e veja ele crescer.</div>
        </div>
      )}

      {sel && (
        <div style={{ position: 'absolute', top: 118, right: 16, bottom: 16, width: 330, background: 'rgba(11,14,20,0.92)', border: '1px solid #1D2532', borderRadius: 16, padding: 18, overflowY: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: sel.col }} />
            <span style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#8A93A3' }}>{LAYER[sel.layer].label} · {sel.tema}</span>
            <span style={{ flex: 1 }} />
            <span onClick={() => setSel(null)} style={{ color: '#5A6577', cursor: 'pointer', fontSize: 16 }}>✕</span>
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 10, lineHeight: 1.35 }}>{sel.name}</div>
          <a href={`/dashboard/chat?q=${encodeURIComponent(`O que você sabe sobre "${sel.name}"?`)}`}
            style={{ display: 'block', textAlign: 'center', marginTop: 16, background: 'linear-gradient(180deg,#16344E,#112A40)', border: '1px solid #2C577E', borderRadius: 11, padding: '11px 14px', fontSize: 13, color: '#CBE4F8', textDecoration: 'none' }}>
            Perguntar ao AutoBrokers sobre isso
          </a>
          <div style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#5A6577', margin: '18px 0 8px' }}>Conexões</div>
          {conns.map((c: Node) => (
            <div key={c.id} onClick={() => setSel(c)} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '8px 6px', borderRadius: 8, fontSize: 12.5, color: '#B9C2CF', cursor: 'pointer' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.col }} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
