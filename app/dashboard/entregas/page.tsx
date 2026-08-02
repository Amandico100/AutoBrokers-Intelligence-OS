// SPEC-064 Bloco B/E — Entregas: o pilar que responde "o que já aconteceu aqui?".
//
// Substitui três itens de menu que respondiam a mesma pergunta — Atividades,
// Histórico e Pesquisas — e dá tela a dois produtores que não tinham nenhuma:
// os artifacts e as execuções de Auxiliar.
import EntregasClient from './EntregasClient';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Entregas · AutoBrokers' };

export default function EntregasPage() {
  return <EntregasClient />;
}
