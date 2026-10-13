'use client';

import Link from 'next/link';

import { AggersDaEquipe } from '@/components/vault/AggersDaEquipe';

/**
 * SPEC-131-B G3 (D-131-07) — "Minhas conexões": as contas da PESSOA (laudo I2 §5). Hoje, o MEU Agger (o fluxo de conta
 * da pessoa da 131-0 A: a senha vai para o cofre e nunca volta, só "senha guardada"). As conexões da CORRETORA (InfoCap,
 * Agger da corretora, WhatsApp de atendimento) continuam em Personalização → Conectores, com o admin.
 */
export function MinhasConexoes() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface p-4">
        <AggersDaEquipe apenasEu />
      </div>
      <p className="text-sm text-muted-foreground">
        As conexões da corretora (sistema de gestão, Agger da corretora, WhatsApp de atendimento) ficam em{' '}
        <Link href="/dashboard/personalizacao/conectores" className="font-medium text-primary underline-offset-4 hover:underline">
          Personalização → Conectores
        </Link>
        , com quem administra a corretora.
      </p>
    </div>
  );
}

export default MinhasConexoes;
