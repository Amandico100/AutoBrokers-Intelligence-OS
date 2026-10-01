'use client';

// SPEC-123 F4 — o diário de decisões, visto pelo master (todas as corretoras).
// O que o agente decidiu sozinho; o que cada corretora disse (certo/errado + "o certo era…").
// "Errado" vira caso pendente de bancada (`backend/scripts/diario_para_bancada.py`) e, pelo
// botão abaixo, rascunho de carta com status `proposta_diario` — que só é publicado pela mão
// do master na aba "Propostas do diário de decisões" do /admin/espelho.

import { useCallback, useEffect, useState } from 'react';

type Linha = {
  id: string; company_id: string; corretora: string; created_at: string; seguradora: string; ramo: string;
  classe: string; acao: string; nota: number | null; modo: string; explicacao_para_gente: string;
  resultado: string; veredito: 'certo' | 'errado' | null; o_certo_era: string | null; sugere_regra: boolean;
  veredito_em: string | null; virou_caso_em: string | null; caso_chave: string | null; carta_rascunho_id: string | null;
};

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

const VEREDITOS = [
  { id: 'errado', label: 'Errados' }, { id: 'sem', label: 'Sem avaliação' },
  { id: 'certo', label: 'Certos' }, { id: 'todas', label: 'Todas' },
];
const ROTULO_DA_CLASSE: Record<string, string> = {
  conduzir: 'Conduziu', responder_com_dado: 'Respondeu com dado do caso', deduzir: 'Deduziu',
  perguntar_ao_segurado: 'Perguntou ao segurado', nunca_sozinho: 'Chamou uma pessoa',
};

export default function AdminDecisoesPage() {
  const [linhas, setLinhas] = useState<Linha[] | null>(null);
  const [veredito, setVeredito] = useState('errado');
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setLinhas(null);
    setErro(null);
    try {
      const r = await fetch(`/api/admin/decisoes?veredito=${veredito}`, { cache: 'no-store' });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { setErro(d?.error || 'Não conseguimos carregar o diário agora.'); setLinhas([]); return; }
      setLinhas(d.items || []);
    } catch {
      setErro('Não conseguimos carregar o diário agora. Tente novamente em instantes.');
      setLinhas([]);
    }
  }, [veredito]);

  useEffect(() => { carregar(); }, [carregar]);

  const virarCarta = async (l: Linha) => {
    setOcupado(l.id);
    setAviso(null);
    try {
      const r = await fetch(`/api/admin/decisoes?id=${l.id}`, { method: 'POST' });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        setAviso(`Não virou carta: ${d?.detail || d?.error || r.status}`);
      } else {
        setAviso('Rascunho de carta criado. Ele está em /admin/espelho → "Propostas do diário de decisões", esperando a sua aprovação.');
        carregar();
      }
    } catch {
      setAviso('Falha na chamada — tente de novo.');
    } finally {
      setOcupado(null);
    }
  };

  return (
    <div style={{ background: '#06080C', minHeight: '100vh', padding: '26px 30px', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Diário de decisões do agente</div>
      <div style={{ fontSize: 12.5, color: '#7C8798', marginTop: 4 }}>
        O que o agente decidiu sozinho para destravar atendimentos, em todas as corretoras — e o que cada corretora disse.
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
        {VEREDITOS.map((v) => (
          <button key={v.id} aria-pressed={veredito === v.id}
            style={{ ...btn, ...(veredito === v.id ? { borderColor: '#E2A94F88', color: '#E2A94F' } : {}) }}
            onClick={() => setVeredito(v.id)}>{v.label}</button>
        ))}
      </div>

      {aviso && (
        <div style={{ ...card, marginTop: 10, padding: '9px 14px', fontSize: 12, color: '#B9C2CF' }}>
          {aviso}
          <span style={{ cursor: 'pointer', color: '#E2A94F', marginLeft: 10 }} onClick={() => setAviso(null)}>fechar</span>
        </div>
      )}
      {erro && <div style={{ ...card, marginTop: 10, padding: '12px 16px', fontSize: 12.5, color: '#E06B6B' }}>{erro}</div>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 14 }}>
        {linhas === null ? (
          <div style={{ ...card, padding: '18px 20px', color: '#7C8798', fontSize: 12.5 }}>Carregando…</div>
        ) : linhas.length === 0 && !erro ? (
          <div style={{ ...card, padding: '18px 20px', color: '#7C8798', fontSize: 12.5 }}>
            Nada aqui com este filtro. As decisões aparecem quando o agente destrava um atendimento sozinho.
          </div>
        ) : linhas.map((l) => (
          <div key={l.id} style={{ ...card, padding: '13px 16px' }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={badge('#7FB7E8')}>{l.corretora || l.company_id.slice(0, 8)}</span>
              {l.seguradora && <span style={badge('#8A93A3')}>{l.seguradora}</span>}
              <span style={badge('#8A93A3')}>{ROTULO_DA_CLASSE[l.classe] || l.classe}</span>
              {l.nota != null && <span style={badge('#8A93A3')}>certeza {l.nota}%</span>}
              {l.modo === 'sombra' && <span style={badge('#E2A94F')}>só observando</span>}
              <span style={{ ...mono, fontSize: 10, color: '#5A6577' }}>{when(l.created_at)}</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.5, marginTop: 8 }}>{l.explicacao_para_gente}</div>
            {l.veredito && (
              <div style={{ fontSize: 12.5, marginTop: 6, color: l.veredito === 'certo' ? '#43C08C' : '#E06B6B' }}>
                {l.veredito === 'certo' ? 'A corretora disse: certo.' : `A corretora disse: errado. O certo era: ${l.o_certo_era || '—'}`}
                {l.sugere_regra ? ' · parece regra' : ''}
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 8, flexWrap: 'wrap', ...mono, fontSize: 10.5, color: '#7C8798' }}>
              {l.virou_caso_em ? <span>virou caso de bancada: {l.caso_chave}</span> : l.veredito === 'errado' ? <span>ainda não virou caso de bancada</span> : null}
              {l.carta_rascunho_id ? (
                <span>rascunho de carta criado · revise em /admin/espelho</span>
              ) : l.veredito === 'errado' ? (
                <button style={btn} disabled={ocupado !== null} onClick={() => virarCarta(l)}>
                  {ocupado === l.id ? 'criando…' : 'Virar rascunho de carta'}
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
