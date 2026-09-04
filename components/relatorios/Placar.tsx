'use client';

// SPEC-095 BLOCO C — o placar do trabalho feito.
//
// 🔴 O QUE ELE NÃO É. Não é um dashboard, não tem gráfico, não tem cor forte e
// não diz "trabalhamos muito para você". 📊 A prova é o número, e o número vem
// do banco do próprio dono: 79 relatórios, 266 conversas, 45 execuções, 14
// trabalhos pedidos. Uma frase de marketing ao lado disso só daria motivo para
// duvidar do resto (DS-001 §5: calma, poucos elementos competindo).
//
// 🔴 E o que ele NÃO CONTA: o relógio da plataforma. 📊 1.214 dos 1.229
// `work_runs` da Resulta são o tick do sistema — o placar ingênuo diria "1.229
// trabalhos" e estaria errado por 87×. A regra mora na rota, escrita, com o
// porquê (`app/api/dashboard/relatorios/placar/route.ts`).
//
// A tela não calcula nada: ela lê. Somar aqui criaria um segundo lugar onde a
// conta pode divergir da resposta — e seria o lugar sem teste.

import { useCallback, useEffect, useState } from 'react';

const JANELAS: { chave: string; rotulo: string }[] = [
  { chave: 'hoje', rotulo: 'Hoje' },
  { chave: '7d', rotulo: '7 dias' },
  { chave: '30d', rotulo: '30 dias' },
  { chave: '365d', rotulo: '1 ano' },
  { chave: 'tudo', rotulo: 'Desde o início' },
];

/** A ordem em que os números aparecem, e o nome de cada um em português. */
const CONTAGENS: { chave: string; rotulo: string }[] = [
  { chave: 'relatorios', rotulo: 'relatórios' },
  { chave: 'conversas', rotulo: 'conversas' },
  { chave: 'execucoes', rotulo: 'execuções' },
  { chave: 'sinais', rotulo: 'sinais' },
  { chave: 'pesquisas', rotulo: 'pesquisas' },
  { chave: 'atividades', rotulo: 'atividades' },
  { chave: 'trabalhos', rotulo: 'trabalhos pedidos' },
];

type Contagens = Record<string, number>;

/**
 * 30 dias é o padrão porque é a janela em que o dono da corretora reconhece o
 * próprio mês. "Desde o início" impressiona e não ajuda a decidir nada.
 */
const JANELA_PADRAO = '30d';
const PREFERENCIA = 'autobrokers.relatorios.placar.janela';

/** Zero é "—", nunca uma linha vazia: espaço em branco parece defeito de carga. */
function numero(n: number | undefined): string {
  if (!n) return '—';
  return n.toLocaleString('pt-BR');
}

export function Placar() {
  const [janelas, setJanelas] = useState<Record<string, Contagens> | null>(null);
  const [janela, setJanela] = useState(JANELA_PADRAO);
  const [falhou, setFalhou] = useState(false);

  // A janela escolhida sobrevive ao refresh. Em `try/catch` porque navegador com
  // armazenamento bloqueado LANÇA ao ler `localStorage` — e um placar não é
  // motivo para uma tela inteira não abrir.
  useEffect(() => {
    try {
      const salva = window.localStorage.getItem(PREFERENCIA);
      if (salva && JANELAS.some((j) => j.chave === salva)) setJanela(salva);
    } catch {
      /* sem preferência — 30 dias */
    }
  }, []);

  const escolher = useCallback((chave: string) => {
    setJanela(chave);
    try {
      window.localStorage.setItem(PREFERENCIA, chave);
    } catch {
      /* a escolha vale para esta visita */
    }
  }, []);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const r = await fetch('/api/dashboard/relatorios/placar', { cache: 'no-store' });
        const j = await r.json();
        if (!vivo) return;
        if (!r.ok || !j?.ok) {
          setFalhou(true);
          return;
        }
        setJanelas(j.janelas || {});
      } catch {
        if (vivo) setFalhou(true);
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  // O placar é um acréscimo: se ele não carregar, a lista de relatórios continua
  // sendo a tela. Nada de caixa de erro no topo do que o corretor veio ver.
  if (falhou) return null;

  const atual = janelas?.[janela];

  return (
    <section className="rounded-xl border border-border bg-surface-2 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {atual ? (
            <>
              <span className="font-medium text-foreground">{numero(atual.soma)}</span> coisas feitas
              por você
            </>
          ) : (
            'Somando o que foi feito…'
          )}
        </p>

        {/* Controle segmentado: cinco janelas, uma escolhida. Sem dropdown —
            cinco opções cabem na linha e um menu esconderia todas menos uma. */}
        <div className="flex flex-wrap items-center gap-1">
          {JANELAS.map((j) => (
            <button
              key={j.chave}
              onClick={() => escolher(j.chave)}
              className={`rounded px-2 py-0.5 text-[11px] transition-colors ${
                janela === j.chave
                  ? 'bg-surface font-medium text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {j.rotulo}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-2">
        {CONTAGENS.map((c) => (
          <div key={c.chave} className="min-w-[64px]">
            <p className="text-sm tabular-nums text-foreground">{numero(atual?.[c.chave])}</p>
            <p className="text-[11px] text-faint">{c.rotulo}</p>
          </div>
        ))}
      </div>

      {/* 📊 Amandus 0 · AutoFleet 0 em "trabalhos pedidos": as duas corretoras
          ainda não pediram nada ao AutoBrokers. Um "—" sozinho pareceria coluna
          quebrada; a frase diz que o número está certo e que a conta é dela. */}
      {atual && !atual.trabalhos && (
        <p className="mt-2 text-[11px] text-faint">
          Ainda não houve trabalho pedido neste período — o relógio da plataforma não conta.
        </p>
      )}
    </section>
  );
}

export default Placar;
