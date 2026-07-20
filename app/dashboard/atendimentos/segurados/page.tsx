import SeguradosClient from './SeguradosClient';

export const metadata = { title: 'Segurados · Atendimentos' };

// SPEC-043: lista REAL derivada dos atendimentos (cresce sozinha).
export default function SeguradosPage() {
  return <SeguradosClient />;
}
