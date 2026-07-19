'use client';

// SPEC-036 Etapa 1 — Acionamentos ao vivo (design Claude Design 14/07).
// Sessões com seguradoras em tempo real: Even executa, Vigia observa, Sentinela intervém.

import { useEffect, useState } from 'react';

type TimelineItem = { at: string | null; direction: string; via: string; text: string };
type Session = {
  company_id: string; insurer_phone: string; insurer_label: string; case_id: string;
  state: string; subservice: string; created_at: string; sentinela_attempts: number;
  reason: string | null; timeline: TimelineItem[];
};

const STATE_META: Record<string, { label: string; color: string }> = {
  ura: { label: 'EM ANDAMENTO', color: '#7FB7E8' },
  human_phase: { label: 'FASE HUMANA', color: '#7FB7E8' },
  preparing: { label: 'PREPARANDO', color: '#8A93A3' },
  ready_to_send: { label: 'PRONTO', color: '#8A93A3' },
  monitoring: { label: 'MONITORANDO', color: '#43C08C' },
  captured: { label: 'PROTOCOLO OK', color: '#43C08C' },
  test_aborted: { label: 'TESTE CONCLUÍDO', color: '#43C08C' },
  needs_human: { label: 'TRAVADO → HUMANO', color: '#E06B6B' },
};

// "atendente" é papel, não nome próprio — cada corretora batiza o seu (Even é só o da Resulta).
const ACTOR_META: Record<string, string> = {
  sentinela: '#E2A94F', vigia: '#E06B6B', atendente: '#7FB7E8', seguradora: '#8A93A3',
};

const mono: React.CSSProperties = { fontFamily: 'Geist Mono, monospace' };
const card: React.CSSProperties = { background: '#0B0F15', border: '1px solid #161D28', borderRadius: 12 };

function badge(color: string): React.CSSProperties {
  return { ...mono, fontSize: 9.5, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 9px', borderRadius: 999, border: `1px solid ${color}55`, color, whiteSpace: 'nowrap' };
}

function hhmm(iso: string | null): string {
  if (!iso) return '--:--';
  try { return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }); } catch { return '--:--'; }
}

type HistItem = {
  id: string; company_id: string; title: string; last_message_at: string | null;
  last_message_preview: string | null;
};
type HistTimeline = { at: string | null; quem: string; texto: string };

export default function AcionamentosPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sel, setSel] = useState(0);
  const [loading, setLoading] = useState(true);
  const [hist, setHist] = useState<HistItem[]>([]);
  const [histSel, setHistSel] = useState<string | null>(null);
  const [histTimeline, setHistTimeline] = useState<HistTimeline[]>([]);
  const [histScore, setHistScore] = useState<{ score: number; flags: string[] } | null>(null);

  useEffect(() => {
    const load = () =>
      fetch('/api/admin/spec034/sessions')
        .then((r) => r.json())
        .then((d) => setSessions(d.sessions || []))
        .catch(() => undefined)
        .finally(() => setLoading(false));
    // SPEC-041: histórico persistente (replay) — sobrevive ao Redis.
    const loadHist = () =>
      fetch('/api/admin/atlas/replay/acionamentos')
        .then((r) => r.json())
        .then((d) => d.ok && setHist(d.acionamentos || []))
        .catch(() => undefined);
    load();
    loadHist();
    const t = setInterval(load, 10000);
    const th = setInterval(loadHist, 60000);
    return () => { clearInterval(t); clearInterval(th); };
  }, []);

  const openHist = (id: string) => {
    setHistSel(id);
    fetch(`/api/admin/atlas/replay/acionamento/${id}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          setHistTimeline(d.timeline || []);
          setHistScore(d.scorecard || null);
        }
      })
      .catch(() => undefined);
  };

  const cur = sessions[sel];

  return (
    <div style={{ background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Acionamentos ao vivo</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>O atendente executa, o Vigia observa, a Sentinela intervém.</div>
      </div>

      {loading && <div style={{ marginTop: 20, color: '#7C8798', fontSize: 13 }}>carregando sessões…</div>}
      {!loading && sessions.length === 0 && (
        <div style={{ ...card, marginTop: 16, padding: '28px 24px', textAlign: 'center', color: '#7C8798', fontSize: 13 }}>
          Nenhum acionamento ativo agora. Quando a Even acionar uma seguradora, a sessão aparece aqui em tempo real
          — e a conversa completa fica espelhada em Conversas.
        </div>
      )}

      {sessions.length > 0 && (
        <div style={{ display: 'flex', gap: 14, marginTop: 16, alignItems: 'flex-start' }}>
          <div style={{ width: 330, minWidth: 280, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sessions.map((s, i) => {
              const m = STATE_META[s.state] || { label: s.state?.toUpperCase(), color: '#8A93A3' };
              return (
                <div key={`${s.company_id}-${s.insurer_phone}-${s.case_id}`} onClick={() => setSel(i)}
                  style={{ ...card, padding: '13px 15px', cursor: 'pointer', border: `1px solid ${i === sel ? '#2C3A4E' : '#161D28'}`, background: i === sel ? '#0E141C' : '#0B0F15' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{s.insurer_label}</span>
                    <span style={{ flex: 1 }} />
                    <span style={badge(m.color)}>{m.label}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 10, marginTop: 6, fontSize: 11.5, color: '#6B7688' }}>
                    <span>caso {s.case_id}</span>
                    <span style={{ flex: 1 }} />
                    <span style={mono}>{s.subservice || ''}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {cur && (
            <div style={{ ...card, flex: 1, padding: '20px 22px', minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ fontSize: 16, fontWeight: 600 }}>{cur.insurer_label}</div>
                <span style={badge((STATE_META[cur.state] || { color: '#8A93A3' }).color)}>
                  {(STATE_META[cur.state] || { label: cur.state }).label}
                </span>
                {cur.sentinela_attempts > 0 && (
                  <span style={badge('#E2A94F')}>SENTINELA {cur.sentinela_attempts}x</span>
                )}
                <span style={{ flex: 1 }} />
                <span style={{ ...mono, fontSize: 11, color: '#6B7688' }}>caso {cur.case_id}{cur.reason ? ` · ${cur.reason}` : ''}</span>
              </div>
              <div style={{ marginTop: 18 }}>
                {cur.timeline.map((ev, i) => {
                  const actor = (ev.via || '').toLowerCase();
                  const color = ACTOR_META[actor] || (ev.direction === 'in' ? '#8A93A3' : '#7FB7E8');
                  const label = actor === 'seguradora' ? 'SEGURADORA' : actor.toUpperCase();
                  return (
                    <div key={i} style={{ display: 'flex', gap: 14, padding: '9px 0 9px 16px', borderLeft: `2px solid ${actor === 'sentinela' || actor === 'vigia' ? color + '66' : '#161D28'}`, marginLeft: 4, position: 'relative' }}>
                      <span style={{ position: 'absolute', left: -5, top: 14, width: 8, height: 8, borderRadius: '50%', background: color }} />
                      <span style={{ ...mono, fontSize: 10.5, color: '#5A6577', minWidth: 38, paddingTop: 2 }}>{hhmm(ev.at)}</span>
                      <span style={{ ...badge(color), minWidth: 84, textAlign: 'center', height: 'fit-content' }}>{label}</span>
                      <span style={{ fontSize: 12.5, color: '#B9C2CF', lineHeight: 1.5, flex: 1, wordBreak: 'break-word' }}>{ev.text}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SPEC-041 — Histórico (replay persistente: sobrevive ao Redis) */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 30, marginBottom: 10 }}>
        <div style={{ fontSize: 15, fontWeight: 650 }}>Histórico (replay)</div>
        <div style={{ fontSize: 11.5, color: '#6B7688' }}>
          acionamentos espelhados no banco — reproduza qualquer um, para sempre
        </div>
      </div>
      {hist.length === 0 ? (
        <div style={{ ...card, padding: '18px 20px', color: '#7C8798', fontSize: 12.5 }}>
          Nenhum acionamento espelhado ainda — o histórico aparece aqui a partir do primeiro acionamento real.
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
          <div style={{ width: 330, minWidth: 280, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {hist.map((h) => (
              <div key={h.id} onClick={() => openHist(h.id)}
                style={{ ...card, padding: '11px 14px', cursor: 'pointer', border: `1px solid ${histSel === h.id ? '#2C3A4E' : '#161D28'}` }}>
                <div style={{ fontSize: 12.5, fontWeight: 600 }}>{h.title}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 5, fontSize: 11, color: '#6B7688' }}>
                  <span style={mono}>{hhmm(h.last_message_at)}</span>
                  <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {h.last_message_preview || ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
          {histSel && (
            <div style={{ ...card, flex: 1, padding: '18px 20px', minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 14, fontWeight: 600 }}>Replay do acionamento</span>
                {histScore && <span style={badge(histScore.score >= 75 ? '#43C08C' : '#E2A94F')}>nota {histScore.score}</span>}
              </div>
              <div style={{ marginTop: 12, maxHeight: 480, overflow: 'auto' }}>
                {histTimeline.map((ev, i) => (
                  <div key={i} style={{ display: 'flex', gap: 12, padding: '7px 0' }}>
                    <span style={{ ...mono, fontSize: 10.5, color: '#5A6577', minWidth: 40 }}>{hhmm(ev.at)}</span>
                    <span style={{ ...badge(ev.quem === 'seguradora' ? '#8A93A3' : '#7FB7E8'), minWidth: 88, textAlign: 'center', height: 'fit-content' }}>
                      {ev.quem.toUpperCase()}
                    </span>
                    <span style={{ fontSize: 12.5, color: '#B9C2CF', lineHeight: 1.5, flex: 1, wordBreak: 'break-word' }}>{ev.texto}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
