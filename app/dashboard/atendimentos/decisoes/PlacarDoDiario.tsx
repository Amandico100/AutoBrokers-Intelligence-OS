'use client';

// ─────────────────────────────────────────────────────────────────────────────
// O PLACAR do diário (SPEC-125 S6) — poucos números que ajudam a DECIDIR.
// ─────────────────────────────────────────────────────────────────────────────
// Os números vêm prontos da rota (`lib/diario/placar.ts`, função pura, testada à mão).
// Aqui só se mostra, em português de gente, e — na tela da corretora — o botão
// "Pausar esta seguradora" (só quem administra; confirmação antes; a rota registra).
// 📱 Mobile-first: 2 colunas no celular, 4 no computador; o detalhe por seguradora
// e por tipo de decisão fica recolhido.

import { useState } from 'react';
import { ChevronDown, PauseCircle, TrendingDown, TrendingUp } from 'lucide-react';

import { cn } from '@/lib/utils';

import type { Placar, Semana } from '@/lib/diario/placar';

export type { Placar };

const ROTULO_DA_CLASSE: Record<string, string> = {
  conduzir: 'Conduziu',
  responder_com_dado: 'Respondeu com dado do caso',
  deduzir: 'Deduziu',
  perguntar_ao_segurado: 'Perguntou ao segurado',
  nunca_sozinho: 'Chamou uma pessoa',
};

export function nomeDaSeguradora(chave: string): string {
  const s = String(chave || '').trim();
  if (!s) return 'Seguradora';
  return s.length <= 3 ? s.toUpperCase() : s.charAt(0).toUpperCase() + s.slice(1);
}

const ou = (n: number | null, sufixo = '%') => (n == null ? '—' : `${n}${sufixo}`);

function Numero({ titulo, valor, detalhe, alerta = false }: {
  titulo: string; valor: string; detalhe: string; alerta?: boolean;
}) {
  return (
    <div className={cn('rounded-xl border bg-surface p-3', alerta ? 'border-danger/50' : 'border-border')}>
      <p className="text-[11px] leading-tight text-muted-foreground">{titulo}</p>
      <p className={cn('mt-1 text-2xl font-semibold tabular-nums', alerta ? 'text-danger' : 'text-foreground')}>{valor}</p>
      <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">{detalhe}</p>
    </div>
  );
}

function Tendencia({ agora, antes }: { agora: Semana; antes: Semana }) {
  const delta = agora.pct_certo != null && antes.pct_certo != null ? agora.pct_certo - antes.pct_certo : null;
  return (
    <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
      {delta != null && delta < 0
        ? <TrendingDown className="h-3.5 w-3.5 text-warning" />
        : <TrendingUp className="h-3.5 w-3.5 text-success" />}
      Esta semana: <strong className="font-semibold text-foreground">{agora.decisoes}</strong> decisões
      ({ou(agora.pct_sem_atendente)} sem atendente, acerto {ou(agora.pct_certo)}) · semana passada: {antes.decisoes}
      ({ou(antes.pct_sem_atendente)} sem atendente, acerto {ou(antes.pct_certo)})
    </p>
  );
}

export default function PlacarDoDiario({ placar, modos = {}, podePausar = false, onPausada }: {
  placar: Placar;
  modos?: Record<string, string>;
  podePausar?: boolean;
  onPausada?: () => void;
}) {
  const [aberto, setAberto] = useState(false);
  const [pausando, setPausando] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const av = placar.avaliadas;
  const seguradoras = Array.from(new Set([...Object.keys(placar.por_seguradora), ...Object.keys(modos)]))
    .filter((s) => s !== 'sem seguradora').sort();

  const pausar = async (seguradora: string) => {
    const ok = window.confirm(
      `Pausar ${nomeDaSeguradora(seguradora)}?\n\nO agente deixa de decidir sozinho nos atendimentos desta seguradora ` +
      'na sua corretora: quando travar, chama uma pessoa, como antes. Fica registrado quem pausou e quando.',
    );
    if (!ok) return;
    setPausando(seguradora);
    setAviso(null);
    try {
      const res = await fetch('/api/dashboard/decisoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acao: 'pausar_seguradora', seguradora, confirmar: true }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setAviso(j?.error || 'Não conseguimos pausar agora. Tente de novo em instantes.'); return; }
      setAviso(`${nomeDaSeguradora(seguradora)} pausada. O agente não decide mais sozinho nela.`);
      onPausada?.();
    } catch {
      setAviso('Não conseguimos pausar agora. Tente de novo em instantes.');
    } finally {
      setPausando(null);
    }
  };

  return (
    <section aria-label="Placar do agente" className="mt-4 space-y-2">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Numero
          titulo="Resolvidos sem atendente"
          valor={ou(placar.pct_sem_atendente)}
          detalhe={`de ${placar.atendimentos} atendimentos com decisão do agente`}
        />
        <Numero
          titulo="Viraram pergunta ao segurado"
          valor={ou(placar.pct_pergunta_ao_segurado)}
          detalhe="das decisões em que o agente agiu"
        />
        <Numero
          titulo="Avaliadas pela corretora"
          valor={`${av.certo} ✓ · ${av.errado} ✗`}
          detalhe={`${av.sem} ainda sem avaliação`}
        />
        <Numero
          titulo="Erros graves (meta: 0)"
          valor={String(placar.erros_graves)}
          detalhe={`${placar.erros_leves} deslizes leves corrigidos na hora`}
          alerta={placar.erros_graves > 0}
        />
      </div>
      <Tendencia agora={placar.semana} antes={placar.semana_anterior} />

      <button
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
      >
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', aberto && 'rotate-180')} />
        {aberto ? 'Esconder' : 'Ver'} por seguradora e por tipo de decisão
      </button>

      {aberto && (
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-surface p-3">
            <p className="text-xs font-medium text-foreground">Por seguradora</p>
            <ul className="mt-2 space-y-2">
              {seguradoras.length === 0 && <li className="text-xs text-muted-foreground">Nenhuma decisão ainda.</li>}
              {seguradoras.map((s) => {
                const c = placar.por_seguradora[s] || { certo: 0, errado: 0, sem: 0, total: 0 };
                const pausada = modos[s] === 'pausado';
                return (
                  <li key={s} className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className="text-foreground">
                      {nomeDaSeguradora(s)}
                      <span className="ml-1.5 text-muted-foreground">{c.certo} certas · {c.errado} erradas · {c.sem} sem avaliação</span>
                    </span>
                    {pausada ? (
                      <span className="rounded-full border border-border px-2 py-0.5 text-muted-foreground">Pausada</span>
                    ) : podePausar && modos[s] ? (
                      <button
                        onClick={() => pausar(s)}
                        disabled={pausando !== null}
                        className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-muted-foreground hover:text-foreground disabled:opacity-60"
                      >
                        <PauseCircle className="h-3.5 w-3.5" />
                        {pausando === s ? 'Pausando…' : 'Pausar esta seguradora'}
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="rounded-xl border border-border bg-surface p-3">
            <p className="text-xs font-medium text-foreground">Por tipo de decisão</p>
            <ul className="mt-2 space-y-2">
              {Object.keys(placar.por_classe).length === 0 && <li className="text-xs text-muted-foreground">Nenhuma decisão ainda.</li>}
              {Object.entries(placar.por_classe).map(([k, c]) => (
                <li key={k} className="text-xs text-foreground">
                  {ROTULO_DA_CLASSE[k] || k}
                  <span className="ml-1.5 text-muted-foreground">{c.certo} certas · {c.errado} erradas · {c.sem} sem avaliação</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      {aviso && <p className="text-xs text-warning">{aviso}</p>}
    </section>
  );
}
