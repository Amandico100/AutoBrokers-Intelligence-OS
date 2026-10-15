'use client';

// SPEC-139 · L2 — o botão "Liberar reenvio dos boletos de teste", MOVIDO do `PainelDeRotinas` (SPEC-078 E.4).
//
// 🔴 A dedup é PERMANENTE: 📊 chave `(company_id, recibo, send_mode)`, sem janela. É o certo em produção — o segurado
// não pode receber o mesmo boleto duas vezes — e tornava o teste um tiro só. A rota limpa APENAS `send_mode='test'`.

import { useState } from 'react';
import { Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';

export function LiberarReenvioDeTeste({ className, onAviso }: { className?: string; onAviso?: (texto: string) => void }) {
  const [liberando, setLiberando] = useState(false);
  const [aviso, setAviso] = useState('');
  const dizer = (t: string) => { setAviso(t); onAviso?.(t); };

  const liberarReenvioDeTeste = async () => {
    if (!confirm(
      'Liberar o reenvio dos boletos que já foram enviados EM TESTE?\n\n'
      + 'A próxima execução vai mandá-los de novo para o seu número de teste.\n'
      + 'Envios reais a segurados NÃO são afetados.',
    )) return;
    setLiberando(true);
    dizer('');
    try {
      const r = await fetch('/api/dashboard/auxiliaries/cobranca/liberar-reenvio', { method: 'POST' });
      const j = await r.json().catch(() => ({}));
      dizer(j?.ok ? j.mensagem : (j?.error || 'Não foi possível liberar o reenvio.'));
    } catch {
      dizer('Falha de conexão.');
    }
    setLiberando(false);
  };

  return (
    <span className={cn('inline-flex flex-col gap-1', className)}>
      <button
        type="button"
        onClick={liberarReenvioDeTeste}
        disabled={liberando}
        className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-sm text-foreground transition-colors hover:bg-surface-2 disabled:opacity-50 sm:min-h-[36px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        title="Permite que os boletos já enviados em teste sejam enviados de novo. Não afeta envios reais."
      >
        {liberando && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
        Liberar reenvio dos boletos de teste
      </button>
      {!onAviso && aviso && <span className="text-sm text-muted-foreground" role="status">{aviso}</span>}
    </span>
  );
}

export default LiberarReenvioDeTeste;
