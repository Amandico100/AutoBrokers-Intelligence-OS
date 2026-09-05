import HistoricoClient from './HistoricoClient';

export const metadata = { title: 'Casos · Atendimentos' };

// ⚠️ A tela lê `?busca=` (o atalho vindo de Segurados) com `useSearchParams`.
// Sem isto o `next build` tenta pré-renderizar a página e para com
// "useSearchParams() should be wrapped in a suspense boundary" — o mesmo tipo
// de erro que só aparece DEPOIS do build (CLAUDE.md §9.1). O precedente é
// `app/dashboard/entregas/page.tsx:8`.
export const dynamic = 'force-dynamic';

// SPEC-097 · R10: a rota "casos" É a lista de casos — por EPISÓDIO, com busca
// no banco. "Histórico" saiu do nome: um caso parado há três dias está aberto.
export default function CasosPage() {
  return <HistoricoClient />;
}
