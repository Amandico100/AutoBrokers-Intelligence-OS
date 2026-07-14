'use client';

// SPEC-036 Etapa 2 — índice da Base de Conhecimento (corrige o 404: a rota só
// tinha a subpágina /sanitize). Escolha a empresa e gerencie o RAG dela; a
// "AutoBrokers Global Knowledge" é a biblioteca GLOBAL (todas as corretoras leem).

import { useEffect, useState } from 'react';
import { DocumentManagementModal } from '@/components/admin/DocumentManagementModal';

type Company = { id: string; company_name: string; is_technical?: boolean };

export default function KnowledgeBasePage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [sel, setSel] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/admin/companies')
      .then((r) => r.json())
      .then((d) => {
        const list: Company[] = d.companies || d || [];
        setCompanies(Array.isArray(list) ? list : []);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const globals = companies.filter((c) => c.company_name === 'AutoBrokers Global Knowledge');
  const normals = companies.filter((c) => c.company_name !== 'AutoBrokers Global Knowledge');

  return (
    <div style={{ padding: '26px 30px', minHeight: '100vh', background: '#06080C', color: '#E7EBF1', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 21, fontWeight: 650, letterSpacing: '-0.02em' }}>Conhecimento (RAG)</div>
        <div style={{ fontSize: 12.5, color: '#7C8798' }}>
          Escolha de quem é o conhecimento: a biblioteca GLOBAL alimenta todas as corretoras; cada corretora tem o cofre dela.
        </div>
      </div>

      {loading && <div style={{ marginTop: 18, fontSize: 13, color: '#7C8798' }}>carregando empresas…</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12, marginTop: 16 }}>
        {globals.map((c) => (
          <div key={c.id} onClick={() => setSel(c)}
            style={{ background: 'rgba(226,169,79,0.05)', border: `1px solid ${sel?.id === c.id ? '#E2A94F' : '#3A2E17'}`, borderRadius: 14, padding: '16px 18px', cursor: 'pointer' }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#F2D9A6' }}>📚 Biblioteca Global AutoBrokers</div>
            <div style={{ fontSize: 12, color: '#C7A868', marginTop: 6, lineHeight: 1.5 }}>
              Conhecimento curado (jurídico, marketing, vendas, seguradoras). Todas as corretoras usam nas respostas — nunca exportável.
            </div>
          </div>
        ))}
        {normals.map((c) => (
          <div key={c.id} onClick={() => setSel(c)}
            style={{ background: '#0B0F15', border: `1px solid ${sel?.id === c.id ? '#2C3A4E' : '#161D28'}`, borderRadius: 14, padding: '16px 18px', cursor: 'pointer' }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{c.company_name}</div>
            <div style={{ fontSize: 12, color: '#7C8798', marginTop: 6 }}>
              {c.is_technical ? 'Empresa técnica da plataforma' : 'Cofre privado da corretora (a corretora também sobe pelo dashboard dela)'}
            </div>
          </div>
        ))}
      </div>

      {sel && (
        <div style={{ marginTop: 20 }}>
          <DocumentManagementModal companyId={sel.id} companyName={sel.company_name} />
        </div>
      )}
    </div>
  );
}
