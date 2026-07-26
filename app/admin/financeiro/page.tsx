'use client';

// SPEC-036 Etapa 2B — hub Financeiro: FinOps (nativo, intocado na lógica) na
// frente + Cobrança + Custos, em abas. Rotas antigas seguem vivas.

import { useState } from 'react';
import dynamic from 'next/dynamic';

const FinopsUsage = dynamic(() => import('../finops/usage/page'), { ssr: false });
const FinopsPricing = dynamic(() => import('../finops/pricing/page'), { ssr: false });
const FinopsPlans = dynamic(() => import('../finops/plans/page'), { ssr: false });
// SPEC-061 §6 — a aba "Cobrança" saiu.
//
// Ela embutia `/admin/billing`, que é "Meu Plano" — o plano DA CORRETORA, o
// que ela paga. Não é a receita da plataforma; é a fatura de um cliente
// específico, e dentro do Admin ela nem sabia de qual cliente falava.
//
// Mudou de casa para `/dashboard/plano`. O que fica aqui é o financeiro da
// PLATAFORMA: consumo, tabela de custos, planos e custo por corretora.
const Costs = dynamic(() => import('../costs/page'), { ssr: false });

const TABS = [
  { id: 'usage', label: 'Consumo LLM' },
  { id: 'pricing', label: 'Tabela de custos' },
  { id: 'plans', label: 'Planos' },
  { id: 'costs', label: 'Custos (legado)' },
] as const;

export default function FinanceiroHub() {
  const [tab, setTab] = useState<string>('usage');
  return (
    <div>
      <div style={{ display: 'flex', gap: 6, padding: '14px 24px 0 24px', borderBottom: '1px solid #161D28', background: '#06080C', flexWrap: 'wrap' }}>
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              fontFamily: 'Geist Mono, monospace', fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase',
              padding: '9px 16px', cursor: 'pointer', background: 'transparent',
              color: tab === t.id ? '#43C08C' : '#7C8798',
              border: 'none', borderBottom: `2px solid ${tab === t.id ? '#43C08C' : 'transparent'}`,
            }}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'usage' && <FinopsUsage />}
      {tab === 'pricing' && <FinopsPricing />}
      {tab === 'plans' && <FinopsPlans />}
      {tab === 'costs' && <Costs />}
    </div>
  );
}
