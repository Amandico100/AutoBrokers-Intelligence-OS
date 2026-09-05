'use client';

/**
 * SPEC-096 · C.3 — UMA LINHA DE ATIVIDADE. UMA.
 *
 * 📊 §3 nº 1: o chat do Claude mostra *"an indicator that Claude is searching
 * the web"* — no singular. Não uma árvore de execução, não uma lista de passos
 * abertos. O corretor quer saber que o trabalho está acontecendo, não como o
 * motor está montado.
 *
 * 🔴 R6 — o rótulo nasce do EVENTO (`stage.started`), nunca de `setTimeout`.
 * Uma linha que aparece por relógio mente duas vezes: aparece quando não há
 * trabalho, e continua quando o trabalho já acabou.
 *
 * ⛔ E o rótulo é a frase da corretora, não o nome da ferramenta (UX-001).
 */
export function LinhaDeAtividade({ label }: { label: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2 px-1 py-2 text-sm text-muted-foreground"
    >
      <span
        aria-hidden="true"
        className="inline-block h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-primary"
      />
      <span>{label}…</span>
    </div>
  );
}

export default LinhaDeAtividade;
