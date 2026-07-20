import HistoricoClient from './HistoricoClient';

export const metadata = { title: 'Histórico · Atendimentos' };

// SPEC-043: a rota "casos" agora é o HISTÓRICO real de atendimentos
// (o sandbox antigo de casos de teste saiu das superfícies do corretor).
export default function CasosPage() {
  return <HistoricoClient />;
}
