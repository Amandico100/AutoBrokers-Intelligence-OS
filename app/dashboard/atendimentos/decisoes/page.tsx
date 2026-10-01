import DiarioClient from './DiarioClient';

export const metadata = { title: 'Decisões do agente · Atendimentos' };

// A tela lê filtros do estado do cliente e busca no servidor a cada troca — não há o
// que pré-renderizar (o precedente é `casos/page.tsx`).
export const dynamic = 'force-dynamic';

// SPEC-123 F4 — o diário de decisões: o que o agente decidiu sozinho, para a corretora
// dizer "certo" ou "errado" e ensinar.
export default function DecisoesPage() {
  return <DiarioClient />;
}
