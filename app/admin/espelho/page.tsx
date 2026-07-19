'use client';

// SPEC-041 — Espelho de Atendimento (centro de comando).
// Fila de aprovação de knowledge cards, playbooks de conduta com gate
// nunca-regredir, replay mascarado das sessões e contribuição por corretora.

import { useCallback, useEffect, useState } from 'react';

type Resumo = {
  sessions_closed: number;
  sessions_distilled: number;
  baseline_humano: { media_global: number | null; por_corretora: Record<string, number>; amostras: number };
  cards: Record<string, number>;
};
type Card = {
  id: string; card_text: string; category: string | null; ramo: string | null;
  insurer_key: string | null; status: string; created_at: string;
};
type Playbook = {
  id: string; ramo: string; servico: string; version: number; status: string;
  model_used: string | null; created_at: string;
  content: Record<string, unknown> | null;
};
type Sessao = {
  id: string; company_id: string; started_at: string; status: string;
  servico: string | null; ramo: string | null; tipo: string | null;
  score: number | null; destilada: boolean;
};
type ReplayItem = { at: string | null; quem: string; tipo?: string; texto: string };
type Contrib = Record<string, { total: number; destiladas?: number; primeiro: string; ultimo: string }>;

const mono: React.CSSProperties = { fontFamily: 'Geist Mono, monospace' };
const card: React.CSSProperties = { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 12 };
const btn: React.CSSProperties = {
  ...mono, fontSize: 10.5, letterSpacing: '0.05em', padding: '6px 13px', borderRadius: 8,
  border: '1px solid #2C3A4E', background: '#0E141C', color: '#B9C2CF', cursor: 'pointer',
};

function badge(color: string): React.CSSProperties {
  return { ...mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 9px', borderRadius: 999, border: `1px solid ${color}55`, color, whiteSpace: 'nowrap' };
}

function when(iso: string | null | undefined): string {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch { return '—'; }
}

const SectionTitle = ({ children, hint }: { children: React.ReactNode; hint?: string }) => (
  <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 26, marginBottom: 10 }}>
    <div style={{ fontSize: 15, fontWeight: 650 }}>{children}</div>
    {hint && <div style={{ fontSize: 11.5, color: '#6B7688' }}>{hint}</div>}
  </div>
);

export default function EspelhoPage() {
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [contrib, setContrib] = useState<{ observacao_ura: Contrib; atendimentos_parte1: Contrib } | null>(null);
  const [openPb, setOpenPb] = useState<string | null>(null);
  const [replay, setReplay] = useState<{ id: string; timeline: ReplayItem[]; distilled: Record<string, unknown> | null } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadAll = useCallback(() => {
    fetch('/api/admin/atlas/espelho/resumo').then((r) => r.json()).then((d) => d.ok && setResumo(d)).catch(() => undefined);
    fetch('/api/admin/atlas/espelho/cards?status=pending_review').then((r) => r.json()).then((d) => setCards(d.cards || [])).catch(() => undefined);
    fetch('/api/admin/atlas/espelho/playbooks').then((r) => r.json()).then((d) => setPlaybooks(d.playbooks || [])).catch(() => undefined);
    fetch('/api/admin/atlas/espelho/sessoes').then((r) => r.json()).then((d) => setSessoes(d.sessoes || [])).catch(() => undefined);
    fetch('/api/admin/atlas/onboarding/contribuicao').then((r) => r.json()).then((d) => d.ok && setContrib(d)).catch(() => undefined);
  }, []);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30000);
    return () => clearInterval(t);
  }, [loadAll]);

  const post = async (path: string, body?: Record<string, unknown>) => {
    setBusy(path);
    try {
      const r = await fetch(`/api/admin/atlas${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
      });
      const d = await r.json();
      setNotice(JSON.stringify(d).slice(0, 400));
      loadAll();
      return d;
    } catch {
      setNotice('falha na chamada — tente de novo');
      return null;
    } finally {
      setBusy(null);
    }
  };

  const openReplay = async (id: string) => {
    try {
      const r = await fetch(`/api/admin/atlas/replay/atendimento/${id}`);
      const d = await r.json();
      if (d.ok) setReplay({ id, timeline: d.timeline || [], distilled: d.session?.distilled || null });
    } catch { /* silencioso */ }
  };

  const baseline = resumo?.baseline_humano;
  const cardCounts = resumo?.cards || {};

  return (
    <div style={{ background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Espelho de Atendimento</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>
          As conversas de trabalho viram conduta e conhecimento — com PII no cofre e gate nunca-regredir.
        </div>
        <span style={{ flex: 1 }} />
        <button style={btn} disabled={busy !== null} onClick={() => post('/espelho/run')}>
          {busy === '/espelho/run' ? 'destilando…' : '▶ Rodar destilação agora'}
        </button>
      </div>

      <div style={{ ...card, marginTop: 14, padding: '12px 16px', display: 'flex', gap: 22, alignItems: 'center', flexWrap: 'wrap', ...mono, fontSize: 11, color: '#7C8798' }}>
        <span>sessões capturadas <span style={{ color: '#A9B2C0' }}>{resumo?.sessions_closed ?? '—'}</span></span>
        <span>destiladas <span style={{ color: '#A9B2C0' }}>{resumo?.sessions_distilled ?? '—'}</span></span>
        <span>baseline humano (interno) <span style={{ color: '#E2A94F' }}>{baseline?.media_global ?? '—'}</span>{baseline?.amostras ? ` · ${baseline.amostras} amostras` : ''}</span>
        <span>cards: {Object.entries(cardCounts).map(([k, v]) => `${k} ${v}`).join(' · ') || 'nenhum ainda'}</span>
      </div>

      {notice && (
        <div style={{ ...card, marginTop: 10, padding: '9px 14px', ...mono, fontSize: 10.5, color: '#8A93A3', wordBreak: 'break-all' }}>
          resultado: {notice}
          <span style={{ cursor: 'pointer', color: '#E2A94F', marginLeft: 10 }} onClick={() => setNotice(null)}>fechar</span>
        </div>
      )}

      <SectionTitle hint="cada card aprovado é publicado no conhecimento global na hora — dupla checagem de PII já feita">
        Fila de aprovação — knowledge cards
      </SectionTitle>
      {cards.length === 0 ? (
        <div style={{ ...card, padding: '18px 20px', color: '#7C8798', fontSize: 12.5 }}>
          Nenhum card aguardando. Eles nascem da destilação das conversas — após o pareamento das atendentes, a fila enche sozinha.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {cards.map((c) => (
            <div key={c.id} style={{ ...card, padding: '13px 16px', display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ fontSize: 13, lineHeight: 1.5 }}>{c.card_text}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 7 }}>
                  {c.insurer_key && <span style={badge('#7FB7E8')}>{c.insurer_key}</span>}
                  {c.ramo && <span style={badge('#8A93A3')}>{c.ramo}</span>}
                  {c.category && <span style={badge('#8A93A3')}>{c.category}</span>}
                  <span style={{ ...mono, fontSize: 10, color: '#5A6577', alignSelf: 'center' }}>{when(c.created_at)}</span>
                </div>
              </div>
              <button style={{ ...btn, borderColor: '#43C08C66', color: '#43C08C' }} disabled={busy !== null}
                onClick={() => post(`/espelho/cards/${c.id}/decide`, { action: 'approve' })}>APROVAR → RAG</button>
              <button style={{ ...btn, borderColor: '#E06B6B66', color: '#E06B6B' }} disabled={busy !== null}
                onClick={() => post(`/espelho/cards/${c.id}/decide`, { action: 'reject' })}>rejeitar</button>
            </div>
          ))}
        </div>
      )}

      <SectionTitle hint="draft só assume se passar no gate (juiz + nunca-regredir); rollback devolve a versão anterior">
        Playbooks de conduta
      </SectionTitle>
      {playbooks.length === 0 ? (
        <div style={{ ...card, padding: '18px 20px', color: '#7C8798', fontSize: 12.5 }}>
          Nenhum playbook ainda. O Destilador cria os primeiros (com o modelo forte) quando houver atendimentos suficientes por serviço.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {playbooks.map((p) => {
            const stColor = p.status === 'active' ? '#43C08C' : p.status === 'draft' ? '#E2A94F' : '#8A93A3';
            const open = openPb === p.id;
            return (
              <div key={p.id} style={{ ...card, padding: '13px 16px' }}>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600 }}>{p.ramo} / {p.servico}</span>
                  <span style={{ ...mono, fontSize: 10.5, color: '#6B7688' }}>v{p.version}</span>
                  <span style={badge(stColor)}>{p.status}</span>
                  {p.model_used && <span style={{ ...mono, fontSize: 10, color: '#5A6577' }}>{p.model_used}</span>}
                  <span style={{ flex: 1 }} />
                  <button style={btn} onClick={() => setOpenPb(open ? null : p.id)}>{open ? 'fechar' : 'ver conteúdo'}</button>
                  {p.status === 'draft' && (
                    <button style={{ ...btn, borderColor: '#43C08C66', color: '#43C08C' }} disabled={busy !== null}
                      onClick={() => post(`/espelho/playbooks/${p.id}/activate`)}>ATIVAR (gate)</button>
                  )}
                  {p.status === 'active' && (
                    <>
                      <button style={{ ...btn, borderColor: '#E2A94F66', color: '#E2A94F' }} disabled={busy !== null}
                        onClick={() => post('/espelho/optimize', { ramo: p.ramo, servico: p.servico })}>lapidar (GEPA)</button>
                      <button style={btn} disabled={busy !== null}
                        onClick={() => post('/espelho/playbooks/rollback', { ramo: p.ramo, servico: p.servico })}>rollback</button>
                    </>
                  )}
                </div>
                {open && p.content && (
                  <pre style={{ ...mono, fontSize: 11, color: '#A9B2C0', background: '#080B10', border: '1px solid #131A23', borderRadius: 8, padding: 14, marginTop: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 420, overflow: 'auto' }}>
                    {JSON.stringify(p.content, null, 2)}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 340 }}>
          <SectionTitle hint="clique para o replay — transcript MASCARADO (dado pessoal fica no cofre)">
            Sessões capturadas
          </SectionTitle>
          {sessoes.length === 0 ? (
            <div style={{ ...card, padding: '18px 20px', color: '#7C8798', fontSize: 12.5 }}>
              Nenhuma sessão ainda — aparecem aqui assim que os WhatsApps das atendentes forem pareados.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {sessoes.map((s) => (
                <div key={s.id} onClick={() => openReplay(s.id)}
                  style={{ ...card, padding: '10px 14px', cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'center', border: `1px solid ${replay?.id === s.id ? '#2C3A4E' : '#161D28'}` }}>
                  <span style={{ ...mono, fontSize: 10.5, color: '#5A6577' }}>{when(s.started_at)}</span>
                  <span style={{ fontSize: 12.5 }}>{s.servico || s.tipo || 'atendimento'}</span>
                  {s.score != null && <span style={badge(s.score >= 75 ? '#43C08C' : '#E2A94F')}>nota {s.score}</span>}
                  <span style={{ flex: 1 }} />
                  <span style={badge(s.destilada ? '#43C08C' : '#8A93A3')}>{s.destilada ? 'destilada' : s.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {replay && (
          <div style={{ ...card, flex: 1.4, minWidth: 380, padding: '18px 20px', marginTop: 44 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Replay (mascarado)</span>
              <span style={{ flex: 1 }} />
              <span style={{ ...btn, padding: '3px 10px' }} onClick={() => setReplay(null)}>fechar</span>
            </div>
            {replay.distilled && (
              <div style={{ ...mono, fontSize: 10.5, color: '#8A93A3', marginTop: 8 }}>
                destilado: {JSON.stringify(replay.distilled).slice(0, 220)}
              </div>
            )}
            <div style={{ marginTop: 12, maxHeight: 460, overflow: 'auto' }}>
              {replay.timeline.map((ev, i) => {
                const isCliente = ev.quem === 'cliente';
                return (
                  <div key={i} style={{ display: 'flex', gap: 12, padding: '7px 0' }}>
                    <span style={{ ...mono, fontSize: 10, color: '#5A6577', minWidth: 76 }}>{when(ev.at)}</span>
                    <span style={{ ...badge(isCliente ? '#8A93A3' : '#7FB7E8'), minWidth: 78, textAlign: 'center', height: 'fit-content' }}>{ev.quem}</span>
                    <span style={{ fontSize: 12, color: '#B9C2CF', lineHeight: 1.5, flex: 1, wordBreak: 'break-word' }}>{ev.texto || `[${ev.tipo}]`}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <SectionTitle hint="o efeito rede: o que cada corretora trouxe para a inteligência global">
        Contribuição por corretora
      </SectionTitle>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {(['observacao_ura', 'atendimentos_parte1'] as const).map((k) => {
          const data = contrib?.[k] || {};
          const label = k === 'observacao_ura' ? 'Observação de URAs (Atlas)' : 'Atendimentos Parte 1 (Espelho)';
          const entries = Object.entries(data);
          return (
            <div key={k} style={{ ...card, flex: 1, minWidth: 320, padding: '14px 18px' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{label}</div>
              {entries.length === 0 ? (
                <div style={{ fontSize: 12, color: '#7C8798' }}>Sem capturas ainda.</div>
              ) : entries.map(([cid, v]) => (
                <div key={cid} style={{ display: 'flex', gap: 10, ...mono, fontSize: 11, color: '#8A93A3', padding: '5px 0', borderTop: '1px solid #131A23' }}>
                  <span style={{ color: '#A9B2C0' }}>{cid.slice(0, 8)}…</span>
                  <span>{v.total} sessões</span>
                  {v.destiladas != null && <span>· {v.destiladas} destiladas</span>}
                  <span style={{ flex: 1 }} />
                  <span>{when(v.ultimo)}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
