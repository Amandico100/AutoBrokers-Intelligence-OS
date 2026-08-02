// SPEC-064 Bloco C — Auxiliares numa tela só.
//
// Esta página mostrava dois cards intermediários ("Rotinas prontas" e "Minhas
// rotinas") e o subtítulo "Rotinas inteligentes que rodam sozinhas" — ou seja,
// chamava de Auxiliar aquilo que é Rotina, e escondia o Auxiliar de verdade em
// /dashboard/auxiliares/meus, que não tinha link no menu.
//
// A ontologia está em docs/canon/ONTOLOGIA-DO-TRABALHO.md:
// **Auxiliar TEM Rotina. Auxiliar NÃO É Rotina.**
//
// O catálogo é GLOBAL — Resulta, AutoFleet, Amandus e as próximas veem os
// mesmos Auxiliares. O que muda por corretora é o que ela ligou, o que ela
// conectou e como personalizou.

import AuxiliaresClient from './AuxiliaresClient';

export const dynamic = 'force-dynamic';

export default function AuxiliaresPage() {
  return <AuxiliaresClient />;
}
