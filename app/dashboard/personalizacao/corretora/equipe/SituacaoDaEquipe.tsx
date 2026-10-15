'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CalendarClock, CheckCircle2, Copy, MinusCircle } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';

/**
 * SPEC-131-B G3 (D-131-07, revê D-131-0-06) — a SITUAÇÃO de cada pessoa: o Agger dela, o WhatsApp de trabalho
 * confirmado e a ausência de hoje. Cada pessoa conecta o PRÓPRIO Agger em Meu perfil; aqui o admin vê quem falta e
 * "pede para conectar" — o produto só monta o texto para ele COPIAR e mandar como quiser. Nada é enviado; nenhum
 * login de outra pessoa é digitado aqui. Só o admin da corretora vê esta lista (a rota confere).
 */
type Pessoa = {
  user_id: string;
  nome: string;
  primeiro_nome: string;
  funcoes: string[];
  agger: { situacao: string | null; rotulo: string | null; conectado: boolean };
  whatsapp_trabalho_confirmado: boolean | null;
  ausencia: { ate: string; substituto: string } | null;
};

const dataBR = (iso: string) => {
  const [a, m, d] = iso.slice(0, 10).split('-');
  return a && m && d ? `${d}/${m}` : iso;
};

function Sinal({ tom, texto }: { tom: 'ok' | 'falta' | 'neutro'; texto: string }) {
  const Icone = tom === 'ok' ? CheckCircle2 : tom === 'falta' ? AlertCircle : MinusCircle;
  const cor = tom === 'ok' ? 'text-success' : tom === 'falta' ? 'text-warning' : 'text-muted-foreground';
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-foreground">
      <Icone size={15} strokeWidth={1.6} className={cor} aria-hidden />
      {texto}
    </span>
  );
}

function sinalDoAgger(p: Pessoa): { tom: 'ok' | 'falta' | 'neutro'; texto: string } {
  const s = p.agger.situacao;
  if (s === 'senha_recusada') return { tom: 'falta', texto: 'Agger: senha recusada' };
  if (s === 'pausado') return { tom: 'neutro', texto: 'Agger pausado' };
  if (p.agger.conectado) return { tom: 'ok', texto: 'Agger conectado' };
  return { tom: 'falta', texto: 'Sem Agger' };
}

function textoDoPedido(p: Pessoa, origem: string): string {
  return `Oi, ${p.primeiro_nome}! Para as renovações e cotações da sua carteira serem calculadas no seu Agger, `
    + `conecte-o no AutoBrokers em Meu perfil → Minhas conexões: ${origem}/dashboard/configuracoes?aba=conexoes`;
}

export function SituacaoDaEquipe() {
  const [pessoas, setPessoas] = useState<Pessoa[] | null>(null);
  const [semAcesso, setSemAcesso] = useState(false);
  const [erro, setErro] = useState('');
  const [copiado, setCopiado] = useState('');

  const carregar = useCallback(async () => {
    setErro('');
    try {
      const r = await fetch('/api/dashboard/equipe/situacao', { cache: 'no-store' });
      if (r.status === 403) { setSemAcesso(true); return; }
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro('Não conseguimos ler a situação da equipe agora.'); return; }
      setPessoas(Array.isArray(j.pessoas) ? j.pessoas : []);
    } catch {
      setErro('Não conseguimos ler a situação da equipe agora.');
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  if (semAcesso) return null;   // só o admin vê; para o membro, a seção não existe

  const pedir = async (p: Pessoa) => {
    try {
      await navigator.clipboard.writeText(textoDoPedido(p, window.location.origin));
      setCopiado(p.user_id);
    } catch {
      setCopiado('');
      setErro('Não conseguimos copiar. Peça para a pessoa abrir Meu perfil → Minhas conexões.');
    }
  };

  return (
    <section className="space-y-3" aria-labelledby="situacao-da-equipe">
      <div className="space-y-1">
        <h2 id="situacao-da-equipe" className="text-base font-semibold text-foreground">Situação de cada pessoa</h2>
        <p className="text-sm text-muted-foreground">
          Cada pessoa conecta o próprio Agger e confirma o WhatsApp de trabalho em Meu perfil. Aqui você vê quem falta.
        </p>
      </div>

      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}

      {!pessoas ? (
        !erro && <Skeleton className="h-32 w-full rounded-xl" />
      ) : pessoas.length === 0 ? (
        <p className="text-sm text-muted-foreground">Ninguém ativo na equipe ainda.</p>
      ) : (
        <ul className="divide-y divide-border-soft rounded-xl border border-border bg-surface">
          {pessoas.map((p) => {
            const ag = sinalDoAgger(p);
            const falta = !p.agger.conectado || p.agger.situacao === 'senha_recusada';
            return (
              <li key={p.user_id} className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between" data-situacao-da-pessoa>
                <div className="min-w-0 space-y-2">
                  <p className="truncate text-sm font-medium text-foreground">
                    {p.nome}
                    {p.funcoes.includes('comercial') && <span className="ml-2 text-xs font-normal text-muted-foreground">Comercial</span>}
                  </p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    <Sinal {...ag} />
                    {p.whatsapp_trabalho_confirmado === null ? null : (
                      <Sinal tom={p.whatsapp_trabalho_confirmado ? 'ok' : 'neutro'}
                        texto={p.whatsapp_trabalho_confirmado ? 'WhatsApp de trabalho confirmado' : 'WhatsApp de trabalho não informado'} />
                    )}
                    {p.ausencia && (
                      <span className="inline-flex items-center gap-1.5 text-sm text-foreground">
                        <CalendarClock size={15} strokeWidth={1.6} className="text-muted-foreground" aria-hidden />
                        Fora até {dataBR(p.ausencia.ate)} · {p.ausencia.substituto} cobre
                      </span>
                    )}
                  </div>
                </div>
                {falta && (
                  <button type="button" onClick={() => pedir(p)}
                    className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2"
                    aria-label={`Pedir para ${p.primeiro_nome} conectar o Agger: copiar a mensagem`}>
                    <Copy size={15} strokeWidth={1.6} aria-hidden />
                    {copiado === p.user_id ? 'Mensagem copiada' : 'Pedir para conectar'}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {copiado && (
        <p className="text-sm text-muted-foreground" role="status">
          A mensagem foi copiada. Cole no canal que vocês usam — o AutoBrokers não envia nada.
        </p>
      )}
    </section>
  );
}

export default SituacaoDaEquipe;
