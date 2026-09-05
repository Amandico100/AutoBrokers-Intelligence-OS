'use client';

import Link from 'next/link';
import type { RefDeArtifact } from '@/lib/chat/protocolo';

/**
 * SPEC-096 · C.3 — A PEÇA PRONTA VIRA UM CARTÃO, NÃO UM PARÁGRAFO
 *
 * 📊 §3 nº 1: o Claude entrega o Artifact como peça clicável ao lado da
 * conversa, não como um bloco de texto no meio dela. Aqui a peça é entidade de
 * primeira classe do Hub (SPEC-057) — tem dono, corretora e versão — e o
 * cartão é só o jeito de a conversa apontar para ela.
 *
 * Os dois caminhos que o corretor quer, e mais nenhum:
 *   · **Abrir** — a peça, na tela dela.
 *   · **Perguntar sobre isso** — volta ao chat com a pergunta já escrita
 *     (o `?pergunta=` da SPEC-095, o mesmo gancho da tela de entregas).
 */
export function CardDeRelatorio({ artifact }: { artifact: RefDeArtifact }) {
  const pergunta = `Sobre ${artifact.title}: `;

  return (
    <div className="mt-3 w-full rounded-xl border border-border bg-surface p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {artifact.kind_human}
      </div>
      <div className="mt-1 text-sm font-medium text-foreground">{artifact.title}</div>

      {/* Largura total no celular: a ação principal tem de ser alcançável com
          o polegar, sem mira. */}
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <Link
          href={artifact.href}
          className="rounded-md border border-primary bg-primary px-3 py-2 text-center text-xs font-medium text-primary-foreground transition-colors hover:opacity-90 sm:py-1.5"
        >
          Abrir
        </Link>
        <Link
          href={`/dashboard/chat?pergunta=${encodeURIComponent(pergunta)}`}
          className="rounded-md border border-border bg-surface px-3 py-2 text-center text-xs font-medium text-primary transition-colors hover:border-primary/40 sm:py-1.5"
        >
          Perguntar sobre isso
        </Link>
      </div>
    </div>
  );
}

export default CardDeRelatorio;
