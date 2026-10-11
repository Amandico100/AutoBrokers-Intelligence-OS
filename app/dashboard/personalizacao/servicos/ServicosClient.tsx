'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

/**
 * SPEC-131-0 parte A · F4 — a tela "Serviços".
 *
 * Os números (padrões, faixas) e os ramos vêm do BACKEND (`config.py` é o único lugar — o guarda G8 da 130-A): esta
 * tela não escreve nenhum número comercial. Ela edita SÓ o manual de cada serviço e as seguradoras preferidas; o
 * backend recusa qualquer outra chave.
 */
type Modo = 'calcular' | 'calcular_entregar' | 'calcular_entregar_negociar';
type Excecao = { ramo?: string; valor_acima_de?: number; modo: Modo };
type Preferencias = Record<string, (string | number)[]>;
type Efetivo = {
  modo: Modo;
  excecoes_do_modo: Excecao[];
  preferencias_de_seguradoras: Preferencias;
  conta_global_se_vence_em_dias?: number;
  antecedencia_dias?: number;
  reajuste_basica_pct?: Record<string, number | null>;
};
type Servico = 'cotacao' | 'renovacao' | 'qcm';
type DadosServicos = {
  qcm_aderido: boolean;
  servicos: Servico[];
  editaveis: Servico[];
  ramos: { codigo: string; nome: string }[];
  comum: { preferencias_de_seguradoras: Preferencias };
  sobreposto: { servicos: Partial<Record<Servico, Record<string, unknown>>>; preferencias_de_seguradoras?: Preferencias | null };
  efetivo: Partial<Record<Servico, Efetivo>>;
  padrao: Partial<Record<Servico, Efetivo>>;
  faixas: { antecedencia_dias_max: number; conta_global_dias_max: number };
  /** a versão que esta tela leu — volta no salvar; se outra pessoa salvou no meio, o servidor recusa (409) */
  versao?: string | null;
};
type Passo = { chave: string; titulo: string; estado: string; detalhe: string; link: string };
type Prontidao = { passos: Passo[]; prontos: number; total: number } | null;

const NOME_DO_SERVICO: Record<Servico, string> = {
  cotacao: 'Cotação',
  renovacao: 'Renovação',
  qcm: 'Quem Cobra Menos',
};

const MODOS: { valor: Modo; titulo: string; explica: string; curto: string }[] = [
  {
    valor: 'calcular', titulo: 'Só calcular e deixar pronto no Agger', curto: 'só calcular',
    explica: 'O AutoBrokers calcula e a cotação fica pronta no Agger para a sua equipe revisar e mandar.',
  },
  {
    valor: 'calcular_entregar', titulo: 'Calcular e entregar ao cliente', curto: 'calcular e entregar',
    explica: 'Calcula e manda a proposta ao cliente. A negociação fica com a sua equipe.',
  },
  {
    valor: 'calcular_entregar_negociar', titulo: 'Calcular, entregar e negociar', curto: 'calcular, entregar e negociar',
    explica: 'Calcula, manda ao cliente e negocia dentro das regras da sua corretora.',
  },
];

const ESTADO: Record<string, { rotulo: string; ponto: string; texto: string }> = {
  pronto: { rotulo: 'Pronto', ponto: 'bg-emerald-500', texto: 'text-emerald-600' },
  em_parte: { rotulo: 'Em parte', ponto: 'bg-amber-500', texto: 'text-amber-600' },
  atencao: { rotulo: 'Precisa de atenção', ponto: 'bg-red-500', texto: 'text-red-600' },
  falta: { rotulo: 'Falta fazer', ponto: 'bg-border', texto: 'text-muted-foreground' },
  nao_sei: { rotulo: 'Não consegui conferir', ponto: 'bg-border', texto: 'text-muted-foreground' },
};

const reais = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

function textoDaExcecao(e: Excecao, ramos: DadosServicos['ramos']): string {
  const partes: string[] = [];
  if (e.ramo) partes.push(ramos.find((r) => r.codigo === e.ramo)?.nome ?? `Ramo ${e.ramo}`);
  if (typeof e.valor_acima_de === 'number') partes.push(`acima de ${reais(e.valor_acima_de)}`);
  const modo = MODOS.find((m) => m.valor === e.modo)?.curto ?? e.modo;
  return `${partes.join(', ')}: ${modo}`;
}

/** O rascunho editável de UM serviço. */
type Rascunho = {
  modo: Modo;
  excecoes: Excecao[];
  igualParaTodos: boolean;
  preferencias: Preferencias;
  contaGlobal?: string;
  antecedencia?: string;
  reajuste?: Record<string, string>;
};

function rascunhoDe(dados: DadosServicos, s: Servico): Rascunho {
  const efe = dados.efetivo[s] as Efetivo;
  const bruto = (dados.sobreposto.servicos[s] || {}) as Record<string, unknown>;
  const temPropria = Boolean(bruto.preferencias_de_seguradoras);
  const r: Rascunho = {
    modo: efe.modo,
    excecoes: [...(efe.excecoes_do_modo || [])],
    igualParaTodos: !temPropria,
    preferencias: JSON.parse(JSON.stringify(efe.preferencias_de_seguradoras || {})),
  };
  if (s === 'renovacao') {
    r.contaGlobal = String(efe.conta_global_se_vence_em_dias ?? '');
    r.antecedencia = String(efe.antecedencia_dias ?? '');
    r.reajuste = Object.fromEntries(
      Object.entries(efe.reajuste_basica_pct || {}).map(([k, v]) => [k, v == null ? '' : String(v)]),
    );
  }
  return r;
}

function inteiro(t: string | undefined): number | undefined {
  if (t == null || t.trim() === '') return undefined;
  const n = Number(t.replace(',', '.'));
  return Number.isFinite(n) ? n : NaN;
}

export function ServicosClient() {
  const [dados, setDados] = useState<DadosServicos | null>(null);
  const [prontidao, setProntidao] = useState<Prontidao>(null);
  const [erro, setErro] = useState('');
  const [aba, setAba] = useState<Servico>('cotacao');
  const [rascunhos, setRascunhos] = useState<Partial<Record<Servico, Rascunho>>>({});
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [conflito, setConflito] = useState(false);

  const aplicar = useCallback((j: { servicos?: DadosServicos; prontidao?: Prontidao } | DadosServicos) => {
    const d = ('efetivo' in j ? j : j.servicos) as DadosServicos | undefined;
    if (!d || !d.efetivo) return;
    setDados(d);
    setConflito(false);
    setRascunhos(Object.fromEntries(d.servicos.map((s) => [s, rascunhoDe(d, s)])));
    if ('prontidao' in j && j.prontidao !== undefined) setProntidao(j.prontidao ?? null);
  }, []);

  const carregar = useCallback(() => {
    fetch('/api/dashboard/servicos', { cache: 'no-store' })
      .then(async (r) => {
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j?.error || j?.detail || 'Não consegui carregar agora.');
        aplicar(j);
      })
      .catch((e) => setErro(e instanceof Error ? e.message : 'Não consegui carregar agora.'));
  }, [aplicar]);

  useEffect(() => { carregar(); }, [carregar]);

  const r = rascunhos[aba];
  const editavel = Boolean(dados?.editaveis.includes(aba));
  const mudar = (patch: Partial<Rascunho>) => setRascunhos((x) => ({ ...x, [aba]: { ...(x[aba] as Rascunho), ...patch } }));

  const salvar = async () => {
    if (!dados || !r) return;
    setAviso('');
    const padrao = dados.padrao[aba] as Efetivo;
    const bloco: Record<string, unknown> = { modo: r.modo, excecoes_do_modo: r.excecoes };
    if (!r.igualParaTodos) bloco.preferencias_de_seguradoras = r.preferencias;
    if (aba === 'renovacao') {
      const conta = inteiro(r.contaGlobal);
      const antec = inteiro(r.antecedencia);
      if (Number.isNaN(conta) || Number.isNaN(antec)) { setAviso('Use só números nos dias.'); return; }
      if (conta !== undefined && conta !== padrao.conta_global_se_vence_em_dias) bloco.conta_global_se_vence_em_dias = conta;
      const ren: Record<string, unknown> = {};
      if (antec !== undefined && antec !== padrao.antecedencia_dias) ren.antecedencia_dias = antec;
      const reaj: Record<string, number> = {};
      for (const [ramo, t] of Object.entries(r.reajuste || {})) {
        const n = inteiro(t);
        if (Number.isNaN(n)) { setAviso('Use só números no reajuste.'); return; }
        if (n !== undefined && n !== (padrao.reajuste_basica_pct || {})[ramo]) reaj[ramo] = n;
      }
      if (Object.keys(reaj).length) ren.reajuste_basica_pct = reaj;
      if (Object.keys(ren).length) bloco.renovacao = ren;
    }
    const corpo: Record<string, unknown> = { servicos: { [aba]: bloco }, versao: dados.versao ?? null };
    if (r.igualParaTodos) corpo.preferencias_de_seguradoras = r.preferencias;
    setSalvando(true);
    try {
      const res = await fetch('/api/dashboard/servicos', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        // 409: outra pessoa salvou antes — o rascunho fica na tela; recarregar mostra o que ela gravou
        setConflito(res.status === 409);
        setAviso(typeof j?.detail === 'string' ? j.detail : j?.error || 'Não consegui salvar.');
        return;
      }
      aplicar(j);
      setAviso(`Regras da ${NOME_DO_SERVICO[aba]} salvas.`);
      carregar();
    } finally {
      setSalvando(false);
    }
  };

  if (erro) return <p className="text-sm text-red-600">{erro}</p>;
  if (!dados || !r) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-6">
      <PassosGuiados prontidao={prontidao} />

      <div className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-3 text-[13px] text-foreground">
        As regras de cada serviço são separadas: mudar a Renovação não muda a Cotação nem o Quem Cobra Menos.
      </div>

      <div role="tablist" aria-label="Serviços" className="flex gap-1 overflow-x-auto rounded-lg border border-border bg-card p-1">
        {dados.servicos.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={aba === s}
            onClick={() => { setAba(s); setAviso(''); }}
            className={`min-h-[40px] flex-1 whitespace-nowrap rounded-md px-3 text-sm ${aba === s ? 'bg-surface-2 font-semibold text-foreground' : 'text-muted-foreground hover:bg-surface-2'}`}
          >
            {NOME_DO_SERVICO[s]}
          </button>
        ))}
      </div>

      {!editavel ? (
        <section className="space-y-2 rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">O que o AutoBrokers faz</h2>
          <p className="text-sm text-foreground">Calcular, entregar e negociar.</p>
          <p className="text-[13px] text-muted-foreground">
            No Quem Cobra Menos é sempre assim: é como o canal funciona, e a comparação entre as corretoras segue a
            mesma regra para todas. As regras da Cotação e da Renovação da sua corretora não mudam o Quem Cobra Menos.
          </p>
        </section>
      ) : (
        <div className="space-y-5">
          <section className="space-y-3 rounded-lg border border-border bg-card p-4">
            <h2 className="text-sm font-semibold text-foreground">O que o AutoBrokers faz</h2>
            <div className="grid gap-2">
              {MODOS.map((m) => (
                <label
                  key={m.valor}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${r.modo === m.valor ? 'border-primary bg-primary/5' : 'border-border'}`}
                >
                  <input
                    type="radio" name={`modo-${aba}`} className="mt-1" checked={r.modo === m.valor}
                    onChange={() => mudar({ modo: m.valor })}
                  />
                  <span>
                    <span className="block text-sm font-medium text-foreground">{m.titulo}</span>
                    <span className="block text-[12px] text-muted-foreground">{m.explica}</span>
                  </span>
                </label>
              ))}
            </div>
            <Excecoes
              excecoes={r.excecoes} ramos={dados.ramos}
              onChange={(excecoes) => mudar({ excecoes })}
            />
          </section>

          <Preferidas
            ramos={dados.ramos} rascunho={r} servico={aba}
            onChange={(p) => mudar(p)}
            comum={dados.comum.preferencias_de_seguradoras}
          />

          {aba === 'renovacao' && (
            <section className="space-y-4 rounded-lg border border-border bg-card p-4">
              <h2 className="text-sm font-semibold text-foreground">Regras da renovação</h2>
              <div className="space-y-2">
                <p className="text-sm text-foreground">Reajuste da cobertura básica</p>
                <p className="text-[12px] text-muted-foreground">
                  Na renovação de condomínio, residencial e empresarial, a cobertura básica sobe este percentual sobre a do ano anterior.
                </p>
                <div className="grid gap-2 sm:grid-cols-3">
                  {Object.keys(r.reajuste || {}).map((ramo) => (
                    <label key={ramo} className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2">
                      <span className="text-sm text-foreground">{dados.ramos.find((x) => x.codigo === ramo)?.nome ?? ramo}</span>
                      <span className="flex items-center gap-1">
                        <input
                          inputMode="decimal" className="h-9 w-16 rounded-md border border-border bg-background px-2 text-right text-sm"
                          value={(r.reajuste || {})[ramo] ?? ''}
                          placeholder={String((dados.padrao.renovacao?.reajuste_basica_pct || {})[ramo] ?? '')}
                          onChange={(e) => mudar({ reajuste: { ...(r.reajuste || {}), [ramo]: e.target.value } })}
                        />
                        <span className="text-sm text-muted-foreground">%</span>
                      </span>
                    </label>
                  ))}
                </div>
                <p className="text-[11px] text-faint">
                  Padrão do AutoBrokers: {Object.values(dados.padrao.renovacao?.reajuste_basica_pct || {}).filter((v) => v != null)[0] ?? '—'} %.
                </p>
              </div>
              <CampoDeDias
                rotulo="Calcular quantos dias antes do vencimento"
                valor={r.antecedencia ?? ''} padrao={dados.padrao.renovacao?.antecedencia_dias}
                maximo={dados.faixas.antecedencia_dias_max}
                onChange={(antecedencia) => mudar({ antecedencia })}
              />
              <CampoDeDias
                rotulo="Se o Agger do comercial falhar, usar o da corretora quando faltar menos de"
                explica="Se a senha do Agger de quem cuida da apólice for recusada, o cálculo espera por ele — e só passa para o Agger da corretora quando o vencimento estiver perto."
                valor={r.contaGlobal ?? ''} padrao={dados.padrao.renovacao?.conta_global_se_vence_em_dias}
                maximo={dados.faixas.conta_global_dias_max}
                onChange={(contaGlobal) => mudar({ contaGlobal })}
              />
            </section>
          )}

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <button
              onClick={salvar} disabled={salvando}
              className="min-h-[44px] rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-60"
            >
              {salvando ? 'Salvando…' : `Salvar regras da ${NOME_DO_SERVICO[aba]}`}
            </button>
            {aviso && <p className={`text-[13px] ${conflito ? 'text-red-600' : 'text-muted-foreground'}`}>{aviso}</p>}
            {conflito && (
              <button
                onClick={() => { setAviso(''); carregar(); }}
                className="min-h-[44px] rounded-lg border border-border px-4 text-sm font-medium"
              >
                Recarregar
              </button>
            )}
          </div>
          <p className="text-[11px] text-faint">
            O AutoBrokers passa a seguir estas regras quando a {NOME_DO_SERVICO[aba]} automática estiver ligada na sua corretora.
          </p>
        </div>
      )}
    </div>
  );
}

function PassosGuiados({ prontidao }: { prontidao: Prontidao }) {
  if (!prontidao) {
    return (
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-foreground">Configuração em 4 passos</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">Não consegui conferir os passos agora.</p>
      </section>
    );
  }
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold text-foreground">Configuração em {prontidao.total} passos</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">{prontidao.prontos} de {prontidao.total} prontos. Siga nesta ordem.</p>
      </div>
      <ol className="divide-y divide-border">
        {prontidao.passos.map((p, i) => {
          const e = ESTADO[p.estado] ?? ESTADO.falta;
          return (
            <li key={p.chave} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:gap-3">
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-[12px] text-muted-foreground">{i + 1}</span>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">{p.titulo}</p>
                  <p className={`mt-0.5 flex items-center gap-1.5 text-[12px] ${e.texto}`}>
                    <span className={`h-2 w-2 rounded-full ${e.ponto}`} />{e.rotulo}
                  </p>
                  <p className="mt-0.5 text-[12px] text-muted-foreground">{p.detalhe}</p>
                </div>
              </div>
              {p.chave !== 'servicos' && (
                <Link href={p.link} className="self-start rounded-lg border border-border px-3 py-2 text-[12px] text-muted-foreground hover:bg-surface-2 sm:py-1">
                  Abrir
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function Excecoes({ excecoes, ramos, onChange }: {
  excecoes: Excecao[]; ramos: DadosServicos['ramos']; onChange: (e: Excecao[]) => void;
}) {
  const [ramo, setRamo] = useState('');
  const [valor, setValor] = useState('');
  const [modo, setModo] = useState<Modo>('calcular');
  const [erro, setErro] = useState('');
  const adicionar = () => {
    const v = valor.trim() === '' ? undefined : Number(valor.replace(/\./g, '').replace(',', '.'));
    if (!ramo && v === undefined) { setErro('Escolha um ramo ou um valor.'); return; }
    if (v !== undefined && (!Number.isFinite(v) || v < 0)) { setErro('O valor precisa ser um número.'); return; }
    const e: Excecao = { modo };
    if (ramo) e.ramo = ramo;
    if (v !== undefined) e.valor_acima_de = v;
    onChange([...excecoes, e]);
    setRamo(''); setValor(''); setErro('');
  };
  return (
    <div className="space-y-2 border-t border-border pt-3">
      <p className="text-sm text-foreground">Exceções</p>
      <p className="text-[12px] text-muted-foreground">
        Por exemplo: “Condomínio: só calcular”. Se mais de uma exceção valer para o mesmo cálculo, vale a que faz menos.
      </p>
      {excecoes.length > 0 && (
        <ul className="space-y-1">
          {excecoes.map((e, i) => (
            <li key={i} className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-sm">
              <span className="min-w-0 text-foreground">{textoDaExcecao(e, ramos)}</span>
              <button
                onClick={() => onChange(excecoes.filter((_, j) => j !== i))}
                className="shrink-0 text-[12px] text-muted-foreground hover:text-red-600"
              >
                Tirar
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_1.4fr_auto]">
        <select value={ramo} onChange={(e) => setRamo(e.target.value)} className="h-10 rounded-md border border-border bg-background px-2 text-sm">
          <option value="">Qualquer ramo</option>
          {ramos.map((x) => <option key={x.codigo} value={x.codigo}>{x.nome}</option>)}
        </select>
        <input
          inputMode="decimal" placeholder="Acima de R$ (opcional)" value={valor}
          onChange={(e) => setValor(e.target.value)}
          className="h-10 rounded-md border border-border bg-background px-2 text-sm"
        />
        <select value={modo} onChange={(e) => setModo(e.target.value as Modo)} className="h-10 rounded-md border border-border bg-background px-2 text-sm">
          {MODOS.map((m) => <option key={m.valor} value={m.valor}>{m.titulo}</option>)}
        </select>
        <button onClick={adicionar} className="h-10 rounded-md border border-border px-3 text-sm text-foreground hover:bg-surface-2">
          Adicionar
        </button>
      </div>
      {erro && <p className="text-[12px] text-red-600">{erro}</p>}
    </div>
  );
}

function Preferidas({ ramos, rascunho, servico, comum, onChange }: {
  ramos: DadosServicos['ramos']; rascunho: Rascunho; servico: Servico; comum: Preferencias;
  onChange: (p: Partial<Rascunho>) => void;
}) {
  const [novo, setNovo] = useState<Record<string, string>>({});
  const lista = useMemo(() => rascunho.preferencias, [rascunho.preferencias]);
  const trocar = (ramo: string, itens: (string | number)[]) => onChange({ preferencias: { ...lista, [ramo]: itens } });
  const mover = (ramo: string, i: number, d: number) => {
    const itens = [...(lista[ramo] || [])];
    const j = i + d;
    if (j < 0 || j >= itens.length) return;
    [itens[i], itens[j]] = [itens[j], itens[i]];
    trocar(ramo, itens);
  };
  return (
    <section className="space-y-3 rounded-lg border border-border bg-card p-4">
      <h2 className="text-sm font-semibold text-foreground">Seguradoras preferidas por ramo</h2>
      <p className="text-[12px] text-muted-foreground">
        Em ordem: a primeira é a preferida. As outras seguradoras continuam sendo cotadas e comparadas — a preferida só
        aparece marcada e ganha no empate.
      </p>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <input
          type="checkbox" checked={rascunho.igualParaTodos}
          onChange={(e) => onChange({
            igualParaTodos: e.target.checked,
            preferencias: e.target.checked ? JSON.parse(JSON.stringify(comum)) : lista,
          })}
        />
        A mesma lista para todos os serviços
      </label>
      {!rascunho.igualParaTodos && (
        <p className="text-[12px] text-muted-foreground">Esta lista vale só para a {NOME_DO_SERVICO[servico]}.</p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {ramos.map((ramo) => (
          <div key={ramo.codigo} className="space-y-2 rounded-lg border border-border p-3">
            <p className="text-sm font-medium text-foreground">{ramo.nome}</p>
            {(lista[ramo.codigo] || []).length === 0 && (
              <p className="text-[12px] text-faint">Nenhuma preferida: todas são comparadas igual.</p>
            )}
            <ol className="space-y-1">
              {(lista[ramo.codigo] || []).map((seg, i) => (
                <li key={`${seg}-${i}`} className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 truncate text-foreground">{i + 1}. {String(seg)}</span>
                  <span className="flex shrink-0 gap-1">
                    <button aria-label="Subir" onClick={() => mover(ramo.codigo, i, -1)} className="h-8 w-8 rounded border border-border text-muted-foreground">↑</button>
                    <button aria-label="Descer" onClick={() => mover(ramo.codigo, i, 1)} className="h-8 w-8 rounded border border-border text-muted-foreground">↓</button>
                    <button
                      aria-label="Tirar" onClick={() => trocar(ramo.codigo, (lista[ramo.codigo] || []).filter((_, j) => j !== i))}
                      className="h-8 w-8 rounded border border-border text-muted-foreground hover:text-red-600"
                    >
                      ×
                    </button>
                  </span>
                </li>
              ))}
            </ol>
            <div className="flex gap-2">
              <input
                placeholder="Nome da seguradora" value={novo[ramo.codigo] || ''}
                onChange={(e) => setNovo({ ...novo, [ramo.codigo]: e.target.value })}
                className="h-9 min-w-0 flex-1 rounded-md border border-border bg-background px-2 text-sm"
              />
              <button
                onClick={() => {
                  const nome = (novo[ramo.codigo] || '').trim();
                  if (!nome) return;
                  trocar(ramo.codigo, [...(lista[ramo.codigo] || []), nome]);
                  setNovo({ ...novo, [ramo.codigo]: '' });
                }}
                className="h-9 rounded-md border border-border px-3 text-sm text-foreground hover:bg-surface-2"
              >
                Pôr
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CampoDeDias({ rotulo, explica, valor, padrao, maximo, onChange }: {
  rotulo: string; explica?: string; valor: string; padrao?: number; maximo: number; onChange: (v: string) => void;
}) {
  return (
    <label className="block space-y-1">
      <span className="block text-sm text-foreground">{rotulo}</span>
      {explica && <span className="block text-[12px] text-muted-foreground">{explica}</span>}
      <span className="flex items-center gap-2">
        <input
          inputMode="numeric" value={valor} placeholder={padrao != null ? String(padrao) : ''}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-20 rounded-md border border-border bg-background px-2 text-right text-sm"
        />
        <span className="text-sm text-muted-foreground">dias</span>
        <span className="text-[11px] text-faint">(padrão: {padrao ?? '—'} · até {maximo})</span>
      </span>
    </label>
  );
}
