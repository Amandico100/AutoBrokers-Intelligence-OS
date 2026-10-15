'use client';

// SPEC-131-0-B3 F4 — Custos e Uso em português. Dinheiro só do razão; uso medido, nunca estimado.
import { useEffect, useState } from 'react';

type Grupo = { chave: string; rotulo: string; chamadas: number; palavras: string };
type Dados = {
  saldo: { balance_brl: number; alert_80: boolean; alert_100: boolean } | null;
  cobranca: { comecou: boolean; total_brl: number; lancamentos: number };
  uso: { chamadas: number; palavras: string };
  por_assistente: Grupo[];
  por_pessoa: Grupo[];
  por_modelo: Grupo[];
  has_data: boolean;
};

const brl = (n: number) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const int = (n: number) => n.toLocaleString('pt-BR');
const vezes = (n: number) => `${int(n)} ${n === 1 ? 'resposta ou leitura' : 'respostas e leituras'}`;

function Cartao({ titulo, children, tom = 'normal' }: { titulo: string; children: React.ReactNode; tom?: 'normal' | 'aviso' | 'perigo' }) {
  const borda = tom === 'perigo' ? 'border-danger/30 bg-danger/5' : tom === 'aviso' ? 'border-warning/30 bg-warning/5' : 'border-border bg-card';
  return (
    <div className={`min-w-0 rounded-lg border p-4 ${borda}`}>
      <p className="text-[11px] uppercase tracking-wide text-faint">{titulo}</p>
      {children}
    </div>
  );
}

function Quebra({ titulo, grupos }: { titulo: string; grupos: Grupo[] }) {
  if (grupos.length === 0) return null;
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="mb-2 text-sm font-medium text-foreground">{titulo}</h2>
      <ul>
        {grupos.map((g) => (
          <li key={g.chave} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-t border-border py-2 text-[13px] first:border-0">
            <span className="min-w-0 break-words text-foreground">{g.rotulo}</span>
            <span className="text-muted-foreground">{vezes(g.chamadas)} · {g.palavras}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function UsageClient() {
  const [d, setD] = useState<Dados | null>(null);
  const [falhou, setFalhou] = useState(false);
  useEffect(() => {
    fetch('/api/dashboard/usage')
      .then((r) => r.json())
      .then((j) => { if (j?.ok && j.uso) setD(j as Dados); else setFalhou(true); })
      .catch(() => setFalhou(true));
  }, []);
  if (falhou) return <p className="text-sm text-muted-foreground">Não foi possível carregar o uso agora. Tente de novo em instantes.</p>;
  if (!d) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  const tomSaldo = d.saldo?.alert_100 ? 'perigo' : d.saldo?.alert_80 ? 'aviso' : 'normal';

  return (
    <div className="space-y-4">
      <div className={`grid grid-cols-1 gap-3 ${d.saldo ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
        {d.saldo && (
          <Cartao titulo="Saldo" tom={tomSaldo}>
            <p className="mt-1 text-lg font-semibold text-foreground">{brl(d.saldo.balance_brl)}</p>
            {d.saldo.alert_100 ? <p className="text-[12px] text-danger">Saldo esgotado</p> : d.saldo.alert_80 ? <p className="text-[12px] text-warning">Saldo baixo</p> : null}
          </Cartao>
        )}
        <Cartao titulo="Cobrado pelo uso (30 dias)">
          {d.cobranca.comecou ? (
            <>
              <p className="mt-1 text-lg font-semibold text-foreground">{brl(d.cobranca.total_brl)}</p>
              <p className="text-[12px] text-muted-foreground">{int(d.cobranca.lancamentos)} {d.cobranca.lancamentos === 1 ? 'lançamento' : 'lançamentos'} no extrato</p>
            </>
          ) : (
            <p className="mt-1 text-sm text-foreground">A cobrança por uso ainda não começou na sua conta.</p>
          )}
        </Cartao>
        <Cartao titulo="Respostas e leituras da IA (30 dias)">
          <p className="mt-1 text-lg font-semibold text-foreground">{int(d.uso.chamadas)}</p>
          <p className="text-[12px] text-muted-foreground">cada vez que a IA respondeu, leu um documento ou buscou no conhecimento</p>
        </Cartao>
      </div>

      {d.has_data ? (
        <Cartao titulo="Volume de texto processado (30 dias)">
          <p className="mt-1 text-lg font-semibold text-foreground">{d.uso.palavras}</p>
          <p className="text-[12px] text-muted-foreground">A IA lê e escreve em pedaços de texto; 1.000 desses ≈ 750 palavras.</p>
        </Cartao>
      ) : (
        <p className="text-sm text-muted-foreground">Nenhum uso da IA registrado com a sua corretora nos últimos 30 dias.</p>
      )}

      <Quebra titulo="Por assistente" grupos={d.por_assistente} />
      <Quebra titulo="Por pessoa" grupos={d.por_pessoa} />
      <Quebra titulo="Por modelo de IA" grupos={d.por_modelo} />

      <p className="text-[11px] text-faint">Mostramos o uso já registrado com a sua corretora.</p>
    </div>
  );
}
