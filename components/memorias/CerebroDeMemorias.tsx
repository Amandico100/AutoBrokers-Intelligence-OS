'use client';

// SPEC-036 Etapa 3 (refinada 14/07) — MEMÓRIAS (Segundo Cérebro).
// Fidelidade ao design do Claude Design: núcleo pulsante com o nome da
// corretora, brilho por sprite de gradiente radial, PULSOS elétricos viajando
// pelas conexões ("terminações nervosas"), arrasto ELÁSTICO de nós (o
// organismo inteiro reage), labels dos vizinhos no foco. Dados 100% reais.

import { useEffect, useRef, useState } from 'react';

type Item = { id: string; name: string; tema: string; at?: string; locked?: boolean };
type Node = {
  id: string; name: string; layer: 'global' | 'corretora' | 'pessoal'; tema: string;
  hub?: boolean; core?: boolean; locked?: boolean; col: string; r: number; x: number; y: number;
  vx: number; vy: number; ax: number; ay: number; ag: number; q: number;
};

const LAYER = {
  global: { col: '#E2A94F', label: 'Global AutoBrokers' },
  corretora: { col: '#5D9BE0', label: 'Corretora' },
  pessoal: { col: '#43C08C', label: 'Pessoal' },
} as const;

const mono = 'Geist Mono, monospace';

export default function CerebroDeMemorias() {
  const cvRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<any>({ nodes: [], edges: [], adj: new Map(), cam: { x: 0, y: -10, k: 0.85 }, alpha: 1, sprites: {}, pulses: [] });
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
      const nodes: Node[] = []; const edges: { a: Node; b: Node; spine?: boolean }[] = [];
      let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
      const core: Node = { id: 'core', name: data.company_name || 'Sua corretora', layer: 'corretora', tema: 'Centro', core: true, col: '#CFEBFF', r: 22, x: 0, y: 0, vx: 0, vy: 0, ax: 0, ay: 0, ag: 0.08, q: 90 };
      nodes.push(core);
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
          const rad = 330 + rnd() * 130;
          const ax = Math.cos(angle) * rad, ay = Math.sin(angle) * rad * 0.72;
          angle += (2 * Math.PI) / hubCount;
          const hub: Node = { id: `hub-${c.key}-${tema}`, name: tema, layer: c.key, tema, hub: true, col: LAYER[c.key].col, r: 12.5, x: ax * 0.2, y: ay * 0.2, vx: 0, vy: 0, ax, ay, ag: 0.05, q: 46 };
          nodes.push(hub);
          edges.push({ a: core, b: hub, spine: true });
          items.slice(0, 60).forEach((it) => {
            const n: Node = { id: it.id, name: it.name, layer: c.key, tema, locked: it.locked, col: LAYER[c.key].col, r: 3.4 + rnd() * 3.8, x: ax + (rnd() - 0.5) * 90, y: ay + (rnd() - 0.5) * 90, vx: 0, vy: 0, ax, ay, ag: 0.004, q: 14 };
            nodes.push(n); edges.push({ a: hub, b: n });
          });
        });
      });
      const adj = new Map<Node, Node[]>();
      nodes.forEach((n) => adj.set(n, []));
      edges.forEach((e) => { adj.get(e.a)!.push(e.b); adj.get(e.b)!.push(e.a); });
      st.nodes = nodes; st.edges = edges; st.adj = adj; st.alpha = 1; st.pulses = [];
      // O grafo desenha no máximo 24 estrelas por pasta global — senão a
      // simulação de forças trava. O cabeçalho mostra o número VERDADEIRO:
      // dizer "52 memórias" quando existem 987 é vender o cérebro por menos
      // do que ele é.
      const desenhadasGlobais = (data.global || []).length;
      const reaisGlobais = Number(data.global_total || desenhadasGlobais);
      setCounts({ mem: totalLeaves - desenhadasGlobais + reaisGlobais, con: edges.length });
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
    const wx = (mx: number) => (mx - W / 2) / st.cam.k + st.cam.x;
    const wy = (my: number) => (my - H / 2) / st.cam.k + st.cam.y;

    // Sprite de brilho premium (gradiente radial cacheado por cor) — o "glow"
    // suave do design, sem o anel chapado.
    const sprite = (col: string) => {
      if (st.sprites[col]) return st.sprites[col];
      const s = document.createElement('canvas'); s.width = s.height = 96;
      const g = s.getContext('2d')!;
      const gr = g.createRadialGradient(48, 48, 2, 48, 48, 46);
      gr.addColorStop(0, `${col}B0`); gr.addColorStop(0.35, `${col}38`); gr.addColorStop(1, `${col}00`);
      g.fillStyle = gr; g.fillRect(0, 0, 96, 96);
      st.sprites[col] = s; return s;
    };

    const pick = (mx: number, my: number): Node | null => {
      let best: Node | null = null; let bd = 1e9;
      for (const n of st.nodes as Node[]) {
        const d = Math.hypot(sx(n) - mx, sy(n) - my);
        if (d < n.r * st.cam.k + 8 && d < bd) { best = n; bd = d; }
      }
      return best;
    };
    let drag: { mx: number; my: number; cx: number; cy: number; moved: boolean } | null = null;
    let dragNode: Node | null = null;
    const local = (e: PointerEvent | WheelEvent) => { const rc = cv.getBoundingClientRect(); return [e.clientX - rc.left, e.clientY - rc.top]; };
    cv.onpointerdown = (e) => {
      const [mx, my] = local(e);
      drag = { mx, my, cx: st.cam.x, cy: st.cam.y, moved: false };
      dragNode = pick(mx, my);
      cv.style.cursor = 'grabbing';
    };
    window.onpointermove = (e) => {
      const [mx, my] = local(e);
      if (drag) {
        if (Math.abs(mx - drag.mx) + Math.abs(my - drag.my) > 4) drag.moved = true;
        if (dragNode && !dragNode.core) {
          // ELÁSTICO: o nó segue o mouse; as molas puxam os vizinhos — o
          // organismo inteiro estica e reage (efeito Obsidian).
          dragNode.x = wx(mx); dragNode.y = wy(my);
          dragNode.vx = 0; dragNode.vy = 0;
          st.alpha = Math.max(st.alpha, 0.35);
        } else {
          st.cam.x = drag.cx - (mx - drag.mx) / st.cam.k;
          st.cam.y = drag.cy - (my - drag.my) / st.cam.k;
        }
        return;
      }
      hovRef.current = pick(mx, my);
      cv.style.cursor = hovRef.current ? 'pointer' : 'grab';
    };
    window.onpointerup = (e) => {
      if (drag && !drag.moved) { const [mx, my] = local(e as PointerEvent); setSel(pick(mx, my)); }
      drag = null; dragNode = null; cv.style.cursor = 'grab';
    };
    cv.onwheel = (e) => {
      e.preventDefault();
      st.cam.k = Math.max(0.35, Math.min(3, st.cam.k * Math.exp(-e.deltaY * 0.0011)));
    };

    let lastT = 0;
    const loop = (t: number) => {
      raf = requestAnimationFrame(loop);
      const dt = Math.min(40, t - (lastT || t)); lastT = t;
      const N = st.nodes as Node[]; const A = (st.alpha = Math.max(0.04, st.alpha * 0.996));
      for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {
        const n = N[i], m = N[j];
        let dx = n.x - m.x, dy = n.y - m.y; let d2 = dx * dx + dy * dy;
        if (d2 > 40000) continue; if (d2 < 4) { dx = 1; dy = 1; d2 = 2; }
        const f = ((n.q * m.q) / d2) * 0.06 * A;
        n.vx += dx * f; n.vy += dy * f; m.vx -= dx * f; m.vy -= dy * f;
      }
      for (const e of st.edges) {
        const rest = e.spine ? 300 : 70;
        const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y; const d = Math.hypot(dx, dy) || 1;
        const f = (d - rest) * (e.spine ? 0.003 : 0.012) * A;
        e.a.vx += (dx / d) * f; e.a.vy += (dy / d) * f; e.b.vx -= (dx / d) * f; e.b.vy -= (dy / d) * f;
      }
      for (const n of N) {
        if (n.core) { n.x *= 0.9; n.y *= 0.9; continue; }
        if (n === dragNode) continue;
        n.vx += (n.ax - n.x) * n.ag * A; n.vy += (n.ay - n.y) * n.ag * A;
        n.vx *= 0.85; n.vy *= 0.85; n.x += n.vx * 2; n.y += n.vy * 2;
      }

      ctx.clearRect(0, 0, W, H);
      const bg = ctx.createRadialGradient(W / 2, H / 2, 60, W / 2, H / 2, Math.max(W, H) * 0.7);
      bg.addColorStop(0, '#0A0F17'); bg.addColorStop(1, '#06080C');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

      const focus = hovRef.current || selRef.current;
      const nb = focus ? new Set(st.adj.get(focus) || []) : null;
      const q = queryRef.current; const lf = layerRef.current;
      for (const n of N) {
        let a = 1;
        if (lf !== 'all' && !n.core && n.layer !== lf) a *= 0.07;
        if (q) a *= n.name.toLowerCase().includes(q) ? 1 : (n.hub || n.core ? 0.2 : 0.05);
        if (nb) a *= n === focus || nb.has(n) ? 1 : 0.08;
        (n as any)._a = a;
      }
      // conexões
      for (const e of st.edges) {
        const ea = Math.min((e.a as any)._a, (e.b as any)._a); if (ea < 0.03) continue;
        const hot = nb && (e.a === focus || e.b === focus);
        ctx.globalAlpha = hot ? 0.9 : (e.spine ? 0.3 : 0.22) * ea;
        ctx.strokeStyle = hot ? (e.b.hub || e.b.core ? e.a.col : e.b.col) : (e.spine ? '#41546E' : '#33445C');
        ctx.lineWidth = hot ? 1.5 : e.spine ? 1.1 : 0.7;
        ctx.beginPath(); ctx.moveTo(sx(e.a), sy(e.a)); ctx.lineTo(sx(e.b), sy(e.b)); ctx.stroke();
      }
      // PULSOS elétricos (terminações nervosas): cargas viajando pelas conexões.
      if (st.pulses.length < 24 && Math.random() < 0.5 && st.edges.length) {
        const e = st.edges[Math.floor(Math.random() * st.edges.length)];
        st.pulses.push({ e, t: 0, sp: 0.35 + Math.random() * 0.8, col: (e.b.hub || e.b.core ? e.a : e.b).col });
      }
      st.pulses = st.pulses.filter((p: any) => p.t <= 1);
      for (const p of st.pulses) {
        p.t += (p.sp * dt) / 1000;
        const ea = Math.min((p.e.a as any)._a, (p.e.b as any)._a); if (ea < 0.04) continue;
        const ax = sx(p.e.a), ay = sy(p.e.a), bx = sx(p.e.b), by = sy(p.e.b);
        for (let k = 0; k < 3; k++) {
          const tt = Math.max(0, Math.min(1, p.t - k * 0.035));
          const x = ax + (bx - ax) * tt, y = ay + (by - ay) * tt;
          ctx.globalAlpha = (k === 0 ? 0.85 : k === 1 ? 0.35 : 0.15) * ea;
          ctx.fillStyle = k === 0 ? '#EAF4FF' : p.col;
          ctx.beginPath(); ctx.arc(x, y, k === 0 ? 1.5 : 1.1, 0, 6.283); ctx.fill();
        }
      }
      // nós
      for (const n of N) {
        const a = (n as any)._a; if (a < 0.02) continue;
        const x = sx(n), y = sy(n);
        if (n.core) {
          const pr = n.r * st.cam.k * (1 + 0.05 * Math.sin(t / 660));
          ctx.globalAlpha = 0.9 * a;
          ctx.drawImage(sprite('#7FB7E8'), x - pr * 3.4, y - pr * 3.4, pr * 6.8, pr * 6.8);
          ctx.globalAlpha = a;
          const cg = ctx.createRadialGradient(x, y, 1, x, y, pr);
          cg.addColorStop(0, '#FFFFFF'); cg.addColorStop(0.55, '#D9EEFF'); cg.addColorStop(1, 'rgba(127,183,232,0.15)');
          ctx.fillStyle = cg; ctx.beginPath(); ctx.arc(x, y, pr, 0, 6.283); ctx.fill();
          ctx.font = `600 12px ${mono}`; ctx.textAlign = 'center';
          ctx.fillStyle = `rgba(217,238,255,${0.85 * a})`;
          ctx.fillText(n.name.toUpperCase().slice(0, 26), x, y + pr + 22);
          ctx.font = `500 9px ${mono}`;
          ctx.fillStyle = `rgba(139,166,196,${0.7 * a})`;
          ctx.fillText('SEGUNDO CÉREBRO', x, y + pr + 36);
          continue;
        }
        const r = Math.max(1.6, n.r * st.cam.k);
        ctx.globalAlpha = (n.hub ? 0.75 : 0.5) * a;
        const gs = r * (n.hub ? 5.2 : 4.2);
        ctx.drawImage(sprite(n.col), x - gs / 2, y - gs / 2, gs, gs);
        ctx.globalAlpha = a;
        ctx.fillStyle = n.col;
        ctx.beginPath(); ctx.arc(x, y, r, 0, 6.283); ctx.fill();
        if (n.hub) {
          ctx.strokeStyle = 'rgba(255,255,255,0.19)'; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.arc(x, y, r + 3.5, 0, 6.283); ctx.stroke();
        }
        if (n === selRef.current) {
          ctx.strokeStyle = n.col; ctx.lineWidth = 1.4;
          ctx.setLineDash([4, 5]); ctx.lineDashOffset = -t / 45;
          ctx.beginPath(); ctx.arc(x, y, r + 8, 0, 6.283); ctx.stroke(); ctx.setLineDash([]);
        }
      }
      // labels: hubs sempre; folhas quando zoom alto, focadas OU vizinhas do foco.
      ctx.textAlign = 'center';
      for (const n of N) {
        const a = (n as any)._a; if (a < 0.05 || n.core) continue;
        const x = sx(n), y = sy(n), r = n.r * st.cam.k;
        if (n.hub) {
          ctx.font = `600 11px ${mono}`;
          ctx.fillStyle = `rgba(231,235,241,${0.9 * a})`;
          ctx.fillText(n.name.toUpperCase().slice(0, 22), x, y + r + 17);
        } else if ((st.cam.k > 1.4 || n === focus || (nb && nb.has(n))) && a > 0.35) {
          ctx.font = '500 10px Geist, sans-serif';
          ctx.fillStyle = `rgba(185,194,207,${0.85 * a})`;
          ctx.fillText(n.name.length > 32 ? `${n.name.slice(0, 31)}…` : n.name, x, y + r + 12);
        }
      }
      // tooltip do hover
      const hov = hovRef.current;
      if (hov && !hov.hub && !hov.core) {
        const x = sx(hov), y = sy(hov);
        ctx.font = '600 12px Geist, sans-serif';
        const w = ctx.measureText(hov.name).width + 26;
        let tx = x + 14; if (tx + w > W - 10) tx = x - w - 14;
        ctx.globalAlpha = 1; ctx.fillStyle = 'rgba(10,13,19,0.94)'; ctx.strokeStyle = '#243044';
        ctx.beginPath(); (ctx as any).roundRect(tx, y - 34, w, 26, 8); ctx.fill(); ctx.stroke();
        ctx.fillStyle = hov.col; ctx.fillRect(tx, y - 34, 3, 26);
        ctx.textAlign = 'left'; ctx.fillStyle = '#E7EBF1'; ctx.fillText(hov.name, tx + 12, y - 16);
        ctx.textAlign = 'center';
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
        <div style={{ display: 'flex', gap: 9, alignItems: 'center' }}><span style={{ width: 9, height: 9, background: '#E2A94F', transform: 'rotate(45deg)', borderRadius: 1.5, boxShadow: '0 0 8px rgba(226,169,79,0.6)' }} /> Global AutoBrokers — inteligência da plataforma <span style={{ color: '#E2A94F', marginLeft: 2 }}>· protegida</span></div>
        <div style={{ display: 'flex', gap: 9, alignItems: 'center', marginTop: 6 }}><span style={{ width: 9, height: 9, background: '#5D9BE0', borderRadius: '50%', boxShadow: '0 0 8px rgba(93,155,224,0.6)' }} /> Corretora e clientes — docs e operação</div>
        <div style={{ display: 'flex', gap: 9, alignItems: 'center', marginTop: 6 }}><span style={{ width: 9, height: 9, background: '#43C08C', borderRadius: '50%', boxShadow: '0 0 8px rgba(67,192,140,0.6)' }} /> Pessoal — o que a IA aprendeu de você</div>
      </div>
      <div style={{ position: 'absolute', right: 22, bottom: 18, fontFamily: mono, fontSize: 11, color: '#485364', pointerEvents: 'none' }}>arraste os nós · role para aproximar</div>

      {empty && (
        <div style={{ position: 'absolute', left: '50%', bottom: 90, transform: 'translateX(-50%)', width: 420, background: 'rgba(11,14,20,0.9)', border: '1px solid #1D2532', borderRadius: 16, padding: '20px 22px', textAlign: 'center' }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>Seu segundo cérebro acabou de nascer</div>
          <div style={{ fontSize: 12.5, color: '#8A93A3', marginTop: 6, lineHeight: 1.55 }}>Cada documento e conversa vira uma nova estrela. Suba conhecimento em Personalização → Conhecimento e veja ele crescer.</div>
        </div>
      )}

      {sel && !sel.core && (
        <div style={{ position: 'absolute', top: 118, right: 16, bottom: 16, width: 330, background: 'rgba(11,14,20,0.92)', border: '1px solid #1D2532', borderRadius: 16, padding: 18, overflowY: 'auto', backdropFilter: 'blur(12px)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: sel.col, boxShadow: `0 0 10px ${sel.col}` }} />
            <span style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#8A93A3' }}>{LAYER[sel.layer].label} · {sel.tema}</span>
            <span style={{ flex: 1 }} />
            <span onClick={() => setSel(null)} style={{ color: '#5A6577', cursor: 'pointer', fontSize: 16 }}>✕</span>
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 10, lineHeight: 1.35 }}>{sel.name}</div>
          {sel.locked ? (
            // A inteligência global é da AutoBrokers, não da corretora. A pasta
            // e o volume aparecem — é o que mostra o tamanho do cérebro. O
            // conteúdo não abre, e o botão que levaria ao chat sairia daqui com
            // um rótulo mascarado ("Procedimentos · Auto · 37") que não quer
            // dizer nada. Melhor dizer a verdade do que fingir um atalho.
            <div style={{ marginTop: 16, background: 'rgba(226,169,79,0.06)', border: '1px solid rgba(226,169,79,0.25)', borderRadius: 11, padding: '13px 14px' }}>
              <div style={{ fontFamily: mono, fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#E2A94F' }}>conteúdo protegido</div>
              <div style={{ fontSize: 12.5, color: '#A9B2C0', marginTop: 7, lineHeight: 1.55 }}>
                Esta é a inteligência da AutoBrokers. Os agentes usam este conhecimento
                para atender por você — ele não é exibido nem exportado.
              </div>
            </div>
          ) : (
            <a href={`/dashboard/chat?q=${encodeURIComponent(`O que você sabe sobre "${sel.name}"?`)}`}
              style={{ display: 'block', textAlign: 'center', marginTop: 16, background: 'linear-gradient(180deg,#16344E,#112A40)', border: '1px solid #2C577E', borderRadius: 11, padding: '11px 14px', fontSize: 13, color: '#CBE4F8', textDecoration: 'none' }}>
              Perguntar ao AutoBrokers sobre isso
            </a>
          )}
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
