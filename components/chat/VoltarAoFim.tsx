'use client';

/**
 * SPEC-096 · C.2 — QUEM ROLOU PARA CIMA NÃO É PUXADO DE VOLTA
 *
 * 🔴 📊 O efeito de `page.tsx:147-149` rolava a tela a CADA mensagem: o
 * corretor que voltava para reler algo era arrancado de lá no pedaço seguinte
 * de resposta. O autoscroll passa a valer só perto do fim (≤120px),
 * e quem está longe ganha este botão — a volta é dele, quando ele quiser.
 */
export function VoltarAoFim({ onClick, rotulo }: { onClick: () => void; rotulo: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-border bg-surface px-4 py-2 text-xs font-medium text-foreground shadow-lg transition-colors hover:border-primary/40"
    >
      {rotulo}
    </button>
  );
}

export default VoltarAoFim;
