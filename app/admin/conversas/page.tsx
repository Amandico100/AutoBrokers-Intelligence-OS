'use client';

// SPEC-036 Etapa 2B — hub Conversas: funde conversations + conversation-logs +
// logs em UMA página com abas (as rotas antigas continuam vivas p/ bookmarks).

import { useState } from 'react';
import dynamic from 'next/dynamic';

const ConversationsPage = dynamic(() => import('../conversations/page'), { ssr: false });
const ConversationLogsPage = dynamic(() => import('../conversation-logs/page'), { ssr: false });
const SystemLogsPage = dynamic(() => import('../logs/page'), { ssr: false });

const TABS = [
  { id: 'aovivo', label: 'Ao vivo' },
  { id: 'logs', label: 'Logs de conversação' },
  { id: 'sistema', label: 'Sistema' },
] as const;

export default function ConversasHub() {
  const [tab, setTab] = useState<string>('aovivo');
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
      {tab === 'aovivo' && <ConversationsPage />}
      {tab === 'logs' && <ConversationLogsPage />}
      {tab === 'sistema' && <SystemLogsPage />}
    </div>
  );
}
