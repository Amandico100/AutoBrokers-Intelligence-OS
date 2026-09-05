'use client';

import type { AvisoDoTurnoDados } from '@/lib/chat/protocolo';

/**
 * SPEC-096 · C.3 / R5 — AVISO TEM CARA DE AVISO, NÃO DE RESPOSTA
 *
 * 🔴 📊 §1.4: hoje uma recusa da porteira e um erro do modelo chegam pelo
 * mesmo cano do texto, viram mensagem do assistente e são GRAVADOS. Ou seja:
 * "não posso responder isso" entra na memória da corretora como se o agente
 * tivesse dito, e volta a assombrar conversas seguintes.
 *
 * Aqui o aviso é outra coisa na tela e outra coisa no banco — ele não é
 * conteúdo, então não vira conteúdo.
 *
 * E "Tentar de novo" só aparece onde tentar de novo faz sentido: erro e parada.
 * Repetir um pedido que a política recusou é convidar a mesma recusa.
 */
export function AvisoDoTurno({
  aviso,
  onRetry,
}: {
  aviso: AvisoDoTurnoDados;
  onRetry?: () => void;
}) {
  const tom =
    aviso.kind === 'error'
      ? 'border-destructive/40 bg-destructive/10 text-foreground'
      : aviso.kind === 'policy'
        ? 'border-amber-500/40 bg-amber-500/10 text-foreground'
        : 'border-border bg-surface text-muted-foreground';

  const podeTentarDeNovo = Boolean(onRetry) && aviso.kind !== 'policy';

  return (
    <div role="status" className={`mt-2 w-full rounded-xl border px-4 py-3 text-sm ${tom}`}>
      <div>{aviso.message_human}</div>
      {podeTentarDeNovo && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:border-primary/40"
        >
          Tentar de novo
        </button>
      )}
    </div>
  );
}

export default AvisoDoTurno;
