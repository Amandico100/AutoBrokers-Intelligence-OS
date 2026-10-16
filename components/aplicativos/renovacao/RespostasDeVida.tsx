'use client';

// SPEC-129-D · conserto K2 (red team B3) — "As respostas do cliente": o formulário curto no detalhe de uma renovação de
// VIDA pendente. 3–4 campos, português, cabe em 390 px (alvos de 44 px). Envia para a rota da sessão
// (`/api/renovacoes/<id>/respostas-de-vida`) e a próxima madrugada calcula.
// ⛔ Nada vem marcado: o rascunho nasce vazio (`rascunhoVazio`). ⛔ Nada vai para o navegador guardar nem para log.

import { useState } from 'react';
import { Loader2, ShieldAlert } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { cn } from '@/lib/utils';

import {
  ROTULO_DO_CAMPO,
  corpoDoRascunho,
  rascunhoVazio,
  type CampoDaResposta,
  type Rascunho,
  type RespostasDeVidaDoDetalhe,
} from './regrasDasRespostas';

export function RespostasDeVida({
  id,
  pedido,
  onRespondido,
}: {
  id: string;
  pedido: RespostasDeVidaDoDetalhe;
  onRespondido: (frase: string) => void;
}) {
  const [r, setR] = useState<Rascunho>(rascunhoVazio);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (enviando) return;
    const pronto = corpoDoRascunho(r, pedido.campos);
    if (!pronto.ok) {
      setErro(pronto.erro);
      return;
    }
    setErro(null);
    setEnviando(true);
    try {
      const res = await fetch(`/api/renovacoes/${encodeURIComponent(id)}/respostas-de-vida`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pronto.corpo),
        cache: 'no-store',
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof j?.error === 'string' ? j.error : 'Não deu certo agora. Tente de novo.');
      setR(rascunhoVazio());
      onRespondido(typeof j?.frase === 'string' ? j.frase : 'Respostas registradas.');
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} aria-labelledby="respostas-do-cliente" className="rounded-lg border border-border bg-surface p-3">
      <h3 id="respostas-do-cliente" className="text-base font-semibold text-foreground">
        As respostas do cliente
      </h3>
      <p className="mt-1 flex items-start gap-1.5 text-sm text-foreground-2">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        {pedido.aviso}
      </p>
      <div className="mt-3 space-y-4">
        {pedido.campos.map((c) => (
          <Campo key={c} campo={c} r={r} setR={setR} />
        ))}
      </div>
      {erro && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {erro}
        </p>
      )}
      <button
        type="submit"
        disabled={enviando}
        className={cn(
          'mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold',
          BOTAO_PRIMARIO,
          'transition-opacity disabled:opacity-60',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        )}
      >
        {enviando && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        Registrar as respostas
      </button>
    </form>
  );
}

function Campo({
  campo,
  r,
  setR,
}: {
  campo: CampoDaResposta;
  r: Rascunho;
  setR: (f: (x: Rascunho) => Rascunho) => void;
}) {
  const rotulo = ROTULO_DO_CAMPO[campo];
  if (campo === 'fumante' || campo === 'esporte_radical') {
    const valor = r[campo];
    return (
      <fieldset>
        <legend className="text-sm font-medium text-foreground">{rotulo}</legend>
        <div className="mt-1.5 grid grid-cols-2 gap-2" role="radiogroup" aria-label={rotulo}>
          {([true, false] as const).map((opcao) => (
            <button
              key={String(opcao)}
              type="button"
              role="radio"
              aria-checked={valor === opcao}
              onClick={() => setR((x) => ({ ...x, [campo]: opcao }))}
              className={cn(
                'inline-flex h-11 items-center justify-center rounded-lg border px-3 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                valor === opcao
                  ? 'border-primary bg-brand-soft text-foreground'
                  : 'border-border bg-background text-foreground hover:bg-surface-2',
              )}
            >
              {opcao ? 'Sim' : 'Não'}
            </button>
          ))}
        </div>
        {campo === 'esporte_radical' && valor === true && (
          <p className="mt-1.5 text-xs text-muted-foreground">
            O Agger pede qual esporte: com esporte radical, cote esta vida direto no Agger.
          </p>
        )}
      </fieldset>
    );
  }
  const idDoCampo = `resposta-${campo}`;
  return (
    <div>
      <label htmlFor={idDoCampo} className="text-sm font-medium text-foreground">
        {rotulo}
      </label>
      <Input
        id={idDoCampo}
        className="mt-1.5 h-11 text-base sm:text-sm"
        inputMode={campo === 'renda_mensal' ? 'decimal' : 'text'}
        autoComplete="off"
        placeholder={campo === 'renda_mensal' ? 'ex.: 8.500,00' : 'ex.: advogada'}
        value={campo === 'renda_mensal' ? r.renda_mensal : r.profissao_texto}
        onChange={(e) => {
          const v = e.currentTarget.value;
          setR((x) => ({ ...x, [campo]: v }));
        }}
      />
    </div>
  );
}
