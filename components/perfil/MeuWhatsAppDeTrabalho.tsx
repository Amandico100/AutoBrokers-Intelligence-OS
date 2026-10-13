'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, Info } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';

import { fraseDoErro, type MeuPerfil } from './useMeuPerfil';

/**
 * SPEC-131-B G3 (D-131-41) — "Meu WhatsApp de trabalho": SÓ o número em que a pessoa atende os clientes, confirmado por
 * ela. A página de renovação usa este número no "Quero renovar" (o cliente responde ao dono da carteira).
 * Nenhum pareamento, nada em `integrations`: o número de atendimento da corretora e o do Quem Cobra Menos são outros e
 * não mudam. O envio continua saindo do aparelho de quem clica.
 */
function exibir(e164: string): string {
  const d = e164.replace(/\D/g, '');
  if (d.startsWith('55') && (d.length === 12 || d.length === 13)) {
    const ddd = d.slice(2, 4);
    const n = d.slice(4);
    return `(${ddd}) ${n.length === 9 ? `${n.slice(0, 1)} ${n.slice(1, 5)}-${n.slice(5)}` : `${n.slice(0, 4)}-${n.slice(4)}`}`;
  }
  return e164;
}

export function MeuWhatsAppDeTrabalho({ perfil, onMudou }: { perfil: MeuPerfil | null; onMudou: () => void }) {
  const atual = perfil?.whatsapp_trabalho;
  const [editando, setEditando] = useState(false);
  const [numero, setNumero] = useState('');
  const [confirmo, setConfirmo] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  useEffect(() => {
    if (atual) { setEditando(!atual.confirmado); setNumero(atual.numero ? exibir(atual.numero) : ''); setConfirmo(false); }
  }, [atual]);

  if (!perfil) return <Skeleton className="h-40 w-full rounded-xl" />;

  const gravar = async (corpo: Record<string, unknown>, ok: string) => {
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch('/api/dashboard/meu-perfil', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo),
      });
      if (!res.ok) { setErro(await fraseDoErro(res, 'Não conseguimos salvar agora.')); return; }
      setAviso(ok);
      onMudou();
    } catch {
      setErro('Não conseguimos salvar agora.');
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-base font-semibold text-foreground">Meu WhatsApp de trabalho</h3>
        <p className="text-sm text-muted-foreground">
          O número em que você atende os clientes. Quando um cliente abre a renovação que você mandou e toca em
          {' '}&quot;Quero renovar&quot;, a conversa vem para este número — direto para você.
        </p>
      </div>

      {atual?.disponivel === false ? (
        <p className="rounded-lg border border-border-soft bg-surface p-3 text-sm text-muted-foreground">
          Este campo ainda não está disponível na sua corretora. Tente de novo mais tarde.
        </p>
      ) : !editando && atual?.confirmado && atual.numero ? (
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2 text-sm text-foreground">
            <CheckCircle2 size={16} strokeWidth={1.6} className="text-success" aria-hidden />
            <span className="tabular-nums">{exibir(atual.numero)}</span>
            <span className="text-muted-foreground">· confirmado</span>
          </p>
          <div className="flex gap-2">
            <button type="button" onClick={() => { setEditando(true); setAviso(''); }}
              className="h-11 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2">
              Mudar
            </button>
            <button type="button" disabled={ocupado}
              onClick={() => { if (confirm('Tirar o seu WhatsApp de trabalho? O "Quero renovar" passa a ir para o número da corretora.')) gravar({ numero: null }, 'Número tirado.'); }}
              className="h-11 rounded-lg border border-border px-4 text-sm font-medium text-danger hover:bg-surface-2 disabled:opacity-60">
              Tirar
            </button>
          </div>
        </div>
      ) : (
        <form className="space-y-3 rounded-xl border border-border bg-surface p-4"
          onSubmit={(e) => { e.preventDefault(); gravar({ numero, confirmo }, 'WhatsApp de trabalho confirmado.'); }}>
          <div className="space-y-1">
            <label htmlFor="zap-trabalho" className="text-sm font-medium text-foreground">Número com DDD</label>
            <input id="zap-trabalho" type="tel" inputMode="tel" autoComplete="tel" placeholder="(11) 9 1234-5678"
              value={numero} onChange={(e) => setNumero(e.target.value)}
              className="h-11 w-full max-w-xs rounded-lg border border-border bg-background px-3 text-sm tabular-nums text-foreground" />
          </div>
          <label className="flex items-start gap-3 text-sm text-foreground">
            <input type="checkbox" checked={confirmo} onChange={(e) => setConfirmo(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-[hsl(var(--primary))]" />
            Confirmo que este é o WhatsApp em que eu atendo os clientes.
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={ocupado || !numero.trim() || !confirmo}
              className="h-11 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60">
              {ocupado ? 'Salvando…' : 'Salvar'}
            </button>
            {atual?.confirmado && (
              <button type="button" onClick={() => { setEditando(false); setErro(''); }}
                className="h-11 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2">
                Cancelar
              </button>
            )}
          </div>
        </form>
      )}

      <p className="flex items-start gap-2 rounded-lg border border-border-soft p-3 text-sm text-muted-foreground">
        <Info size={16} strokeWidth={1.6} className="mt-0.5 shrink-0" aria-hidden />
        <span>
          Isto é só o número: o AutoBrokers não se conecta a ele e não envia nada por ele. O número de atendimento da
          corretora e o do Quem Cobra Menos são outros e não mudam.
        </span>
      </p>
      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}
      {aviso && <p className="text-sm text-success" role="status">{aviso}</p>}
    </div>
  );
}

export default MeuWhatsAppDeTrabalho;
