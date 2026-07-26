'use client';

// SPEC-036 Etapa 2B — hub Conversas: funde conversations + conversation-logs +
// logs em UMA página com abas (as rotas antigas continuam vivas p/ bookmarks).

import { useState } from 'react';
import dynamic from 'next/dynamic';

// SPEC-061 §6 — a aba "Ao vivo" saiu.
//
// Ela embutia `/admin/conversations`, que é a visão de conversas DA CORRETORA
// — o inbox dela, com o conteúdo dos atendimentos dela. Renderizar isso dentro
// do Admin da plataforma era a mistura de superfícies que a §6 manda desfazer:
// o operador da plataforma abria um hub de "conversas" e via o atendimento de
// um segurado.
//
// A tela não sumiu: mudou de casa, para `/dashboard/conversas`, onde a
// corretora a usa. O que fica aqui é o que é DE PLATAFORMA — o log técnico de
// conversação e o log de sistema, que respondem "o motor está funcionando?" e
// não "o que o cliente disse?".
const ConversationLogsPage = dynamic(() => import('../conversation-logs/page'), { ssr: false });
const SystemLogsPage = dynamic(() => import('../logs/page'), { ssr: false });

const TABS = [
  { id: 'logs', label: 'Logs de conversação' },
  { id: 'sistema', label: 'Sistema' },
] as const;

export default function ConversasHub() {
  const [tab, setTab] = useState<string>('logs');
  return (
    <div>
      <div style={{ display: 'flex', gap: 6, padding: '14px 24px 0 24px', borderBottom: '1px solid #161D28', background: '#06080C' }}>
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              fontFamily: 'Geist Mono, monospace', fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase',
              padding: '9px 16px', cursor: 'pointer', background: 'transparent',
              color: tab === t.id ? '#7FB7E8' : '#7C8798',
              border: 'none', borderBottom: `2px solid ${tab === t.id ? '#7FB7E8' : 'transparent'}`,
            }}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'logs' && <ConversationLogsPage />}
      {tab === 'sistema' && <SystemLogsPage />}
    </div>
  );
}
