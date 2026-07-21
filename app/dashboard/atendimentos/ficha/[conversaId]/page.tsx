import FichaClient from './FichaClient';

export const metadata = { title: 'Ficha do Atendimento · AutoBrokers' };

// SPEC-046: Fila, Histórico e Segurados abrem esta FICHA — o dossiê vivo do
// atendimento. A conversa completa vira um botão dentro dela.
export default async function FichaPage({ params }: { params: Promise<{ conversaId: string }> }) {
  const { conversaId } = await params;
  return <FichaClient conversaId={conversaId} />;
}
