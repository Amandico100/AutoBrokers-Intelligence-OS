'use client';

import { useState } from 'react';
import { CalendarClock, X } from 'lucide-react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { Confirmar } from '@/components/aplicativos/casca/Confirmar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { dataBR, fraseDoErro, type MeuPerfil } from './useMeuPerfil';

/**
 * SPEC-131-B G3 (D-131-08) — "Ausência": o período em que a pessoa está fora e QUEM cobre — OUTRA pessoa da mesma
 * corretora, escolhida de uma LISTA. As renovações da carteira dela continuam calculadas no Agger dela; o aviso de cada
 * uma vai para quem cobre. O servidor confere tudo de novo (outra pessoa, ativa, da mesma corretora, período válido).
 */
export function MinhaAusencia({ perfil, onMudou }: { perfil: MeuPerfil | null; onMudou: () => void }) {
  const [de, setDe] = useState('');
  const [ate, setAte] = useState('');
  const [quem, setQuem] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  if (!perfil) return <Skeleton className="h-48 w-full rounded-xl" />;
  if (perfil.ausencia_disponivel === false) {
    return (
      <p className="rounded-lg border border-border-soft bg-surface p-3 text-sm text-muted-foreground">
        A ausência ainda não está disponível na sua corretora. Tente de novo mais tarde.
      </p>
    );
  }

  const marcar = async () => {
    setErro(''); setAviso('');
    if (!de || !ate || !quem) { setErro('Escolha as datas e quem vai cobrir.'); return; }
    if (ate < de) { setErro('O último dia fora é antes do dia de saída.'); return; }
    setOcupado(true);
    try {
      const res = await fetch('/api/dashboard/meu-perfil', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ substituto_user_id: quem, de, ate }),
      });
      if (!res.ok) { setErro(await fraseDoErro(res, 'Não conseguimos marcar agora.')); return; }
      setDe(''); setAte(''); setQuem('');
      setAviso('Ausência marcada.');
      onMudou();
    } catch {
      setErro('Não conseguimos marcar agora.');
    } finally {
      setOcupado(false);
    }
  };

  const apagar = async (id: string) => {
    // a confirmação é a da casa (`Confirmar`, no botão) — nunca o confirm() do navegador
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch(`/api/dashboard/meu-perfil?id=${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (!res.ok) { setErro(await fraseDoErro(res, 'Não conseguimos apagar agora.')); return; }
      setAviso('Ausência apagada.');
      onMudou();
    } catch {
      setErro('Não conseguimos apagar agora.');
    } finally {
      setOcupado(false);
    }
  };

  const campo = 'h-11 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground';
  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h3 className="text-base font-semibold text-foreground">Ausência</h3>
        <p className="text-sm text-muted-foreground">
          Vai sair de férias? Escolha quem cobre você. Suas renovações seguem no seu Agger; os avisos vão para quem cobre.
        </p>
      </div>

      {perfil.ausencias.length > 0 && (
        <ul className="divide-y divide-border-soft rounded-xl border border-border bg-surface">
          {perfil.ausencias.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-3 p-4">
              <p className="flex min-w-0 items-start gap-2 text-sm text-foreground">
                <CalendarClock size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden />
                <span>
                  De {dataBR(a.de)} a {dataBR(a.ate)} · {a.nome} cobre você
                  {a.ativa && <span className="ml-2 font-medium text-foreground dark:text-success">· agora</span>}
                </span>
              </p>
              <Confirmar titulo="Apagar esta ausência?" descricao={`De ${dataBR(a.de)} a ${dataBR(a.ate)}. Os avisos voltam a ir para você.`}
                acao="Apagar" perigo onConfirmar={() => apagar(a.id)}>
                <button type="button" disabled={ocupado} aria-label={`Apagar a ausência de ${dataBR(a.de)} a ${dataBR(a.ate)}`}
                  className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:text-danger disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <X size={16} strokeWidth={1.6} aria-hidden />
                </button>
              </Confirmar>
            </li>
          ))}
        </ul>
      )}

      {perfil.pessoas.length === 0 ? (
        <p className="rounded-lg border border-border-soft p-3 text-sm text-muted-foreground">
          Não há outra pessoa ativa na sua corretora para cobrir você.
        </p>
      ) : (
        <form className="space-y-3 rounded-xl border border-border bg-surface p-4" onSubmit={(e) => { e.preventDefault(); marcar(); }}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label htmlFor="aus-de" className="text-sm font-medium text-foreground">Saio em</label>
              <input id="aus-de" type="date" value={de} onChange={(e) => setDe(e.target.value)} className={campo} />
            </div>
            <div className="space-y-1">
              <label htmlFor="aus-ate" className="text-sm font-medium text-foreground">Último dia fora</label>
              <input id="aus-ate" type="date" value={ate} min={de || undefined} onChange={(e) => setAte(e.target.value)} className={campo} />
            </div>
          </div>
          <div className="space-y-1">
            <label htmlFor="aus-quem" className="text-sm font-medium text-foreground">Quem cobre você</label>
            <select id="aus-quem" value={quem} onChange={(e) => setQuem(e.target.value)} className={campo}>
              <option value="">Escolha uma pessoa da equipe</option>
              {perfil.pessoas.map((p) => <option key={p.user_id} value={p.user_id}>{p.nome}</option>)}
            </select>
          </div>
          <button type="submit" disabled={ocupado}
            className={cn('h-11 rounded-lg px-5 text-sm font-medium disabled:opacity-60', BOTAO_PRIMARIO, 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring')}>
            {ocupado ? 'Salvando…' : 'Marcar ausência'}
          </button>
        </form>
      )}

      {perfil.cubro.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-foreground">Você cobre</h4>
          <ul className="space-y-1">
            {perfil.cubro.map((a) => (
              <li key={a.id} className="text-sm text-foreground-2">
                {a.nome}, de {dataBR(a.de)} a {dataBR(a.ate)}{a.ativa ? ' · agora' : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}
      {aviso && <p className="text-sm text-foreground dark:text-success" role="status">{aviso}</p>}
    </div>
  );
}

export default MinhaAusencia;
