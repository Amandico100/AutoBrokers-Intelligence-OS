'use client';

// SPEC-061 §12 — a Home executiva.
//
// A Home antiga era uma grade de quatro caixas do mesmo tamanho: MRR, total de
// empresas, total de usuários, aprovações pendentes. Todas com o mesmo peso
// visual — então nenhuma com peso nenhum. A pessoa lia as quatro e decidia
// sozinha qual importava, que é o trabalho que a tela deveria ter feito.
//
// A hierarquia aqui é deliberada e segue §12.1:
//
//   1. uma frase          — o que está acontecendo
//   2. precisa de decisão — o que só anda se alguém agir
//   3. corretoras em risco
//   4. operação
//   5. números            — pequenos, no rodapé, subordinados
//
// Tamanho de fonte, cor e ordem carregam a hierarquia. Se tudo é destaque,
// nada é.
import { useCallback, useEffect, useState } from 'react';

type Estado = { tom: 'estavel' | 'atencao' | 'incerto'; texto: string };
type Decisao = {
  tipo: string;
  o_que: string;
  por_que: string;
  company_id: string | null;
  desde: string | null;
  acao: string;
  href: string;
  risco: 'alto' | 'medio' | 'baixo';
};
type Risco = {
  company_id: string;
  nome: string;
  motivos: string[];
  dias_sem_atividade: number | null;
  href: string;
};
type Dados = {
  estado_geral: Estado;
  fontes_indisponiveis: string[];
  precisa_de_decisao: Decisao[];
  corretoras_em_risco: Risco[];
  operacao: { mensagem?: string; travados?: number; com_problema?: number; total?: number };
  numeros: { rotulo: string; valor: number }[];
};

const TOM: Record<Estado['tom'], string> = {
  estavel: 'border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30',
  atencao: 'border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30',
  incerto: 'border-neutral-300 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900',
};

const RISCO: Record<Decisao['risco'], { borda: string; rotulo: string }> = {
  alto: { borda: 'border-l-red-500', rotulo: 'alto risco' },
  medio: { borda: 'border-l-amber-500', rotulo: 'atenção' },
  baixo: { borda: 'border-l-neutral-300 dark:border-l-neutral-700', rotulo: 'quando der' },
};

function haQuanto(v: string | null): string {
  if (!v) return '';
  try {
    const min = Math.floor((Date.now() - new Date(v).getTime()) / 60000);
    if (min < 60) return `há ${Math.max(1, min)} min`;
    if (min < 1440) return `há ${Math.floor(min / 60)} h`;
    return `há ${Math.floor(min / 1440)} dias`;
  } catch {
    return '';
  }
}

export default function HomeExecutiva() {
  const [d, setD] = useState<Dados | null>(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const r = await fetch('/api/admin/control-plane/home', { cache: 'no-store' });
      setD(await r.json());
    } catch {
      setD(null);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  if (carregando) return <p className="text-sm text-neutral-500">Carregando…</p>;
  if (!d) return null;

  return (
    <div className="space-y-8">
      {/* 1. Uma frase. É o que a pessoa lê primeiro e, muitas vezes, só. */}
      <section className={`rounded-xl border p-5 ${TOM[d.estado_geral?.tom ?? 'incerto']}`}>
        <p className="text-lg leading-relaxed">{d.estado_geral?.texto}</p>
        {d.fontes_indisponiveis?.length > 0 && (
          <p className="text-xs mt-2 text-neutral-600 dark:text-neutral-400">
            Fontes que não responderam: {d.fontes_indisponiveis.join(', ')}.
          </p>
        )}
      </section>

      {/* 2. O que só anda se alguém agir. */}
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500 mb-3">
          Precisa de decisão
        </h2>
        {d.precisa_de_decisao?.length === 0 ? (
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Nada esperando você agora.
          </p>
        ) : (
          <ul className="space-y-2">
            {d.precisa_de_decisao.map((i, n) => (
              <li
                key={`${i.tipo}-${n}`}
                className={`rounded-lg border border-neutral-200 dark:border-neutral-800 border-l-4 ${
                  RISCO[i.risco].borda
                } p-4`}
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="min-w-0">
                    <p className="font-medium">{i.o_que}</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-0.5">
                      {i.por_que}
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">
                      {RISCO[i.risco].rotulo}
                      {i.desde ? ` · ${haQuanto(i.desde)}` : ''}
                    </p>
                  </div>
                  <a
                    href={i.href}
                    className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900 whitespace-nowrap"
                  >
                    {i.acao}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 3. Onde dói. */}
      {d.corretoras_em_risco?.length > 0 && (
        <section>
          <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500 mb-3">
            Corretoras que merecem um olhar
          </h2>
          <ul className="space-y-2">
            {d.corretoras_em_risco.map((c) => (
              <li
                key={c.company_id}
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4 flex items-start justify-between gap-4 flex-wrap"
              >
                <div>
                  <p className="font-medium">{c.nome}</p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    {c.motivos.join(' · ')}
                  </p>
                </div>
                <a
                  href={c.href}
                  className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900"
                >
                  Ver a corretora
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 4. O que está rodando. */}
      {d.operacao?.mensagem && (
        <section>
          <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500 mb-3">
            Operação
          </h2>
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4 flex items-center justify-between gap-4 flex-wrap">
            <p className="text-sm">{d.operacao.mensagem}</p>
            <a
              href="/admin/trabalhos"
              className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900"
            >
              Ver trabalhos
            </a>
          </div>
        </section>
      )}

      {/* 5. Números — pequenos, no fim. §12.4: "sempre subordinadas às decisões". */}
      {d.numeros?.length > 0 && (
        <section className="pt-2 border-t border-neutral-200 dark:border-neutral-800">
          <div className="flex gap-6 flex-wrap">
            {d.numeros.map((n) => (
              <div key={n.rotulo}>
                <span className="text-xs text-neutral-500">{n.rotulo}: </span>
                <span className="text-sm font-medium">{n.valor}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
