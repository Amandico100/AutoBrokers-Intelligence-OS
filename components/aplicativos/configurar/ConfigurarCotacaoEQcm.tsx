'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown } from 'lucide-react';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { BarraSalvar, Grupo } from './pecas';
import { CartoesDeModo, Excecoes, Preferidas, type OpcaoDeModo } from './campos';
import { copia, type DadosServicos, type Excecao, type Modo, type Preferencias, usePodeGerir, useServicos } from './servicos';
import { RegrasDoCalculo, type ValorDasRegras } from '@/components/aplicativos/cotacao/RegrasDoCalculo';

/**
 * SPEC-131-B G3 — a aba Configurar da COTAÇÃO e a do QUEM COBRA MENOS: o conteúdo que a antiga tela "Serviços" tinha
 * para elas, no padrão da aba Configurar (D-131-06, D-131-21). A Cotação Rápida edita o manual dela (o que fazer, exceções,
 * seguradoras preferidas) e — SPEC-132-B · B3 (D-132B-06) — mostra TODAS as regras do cálculo, editando as versões, a
 * comissão de entrada e a validade; o Quem Cobra Menos não se edita — é a natureza do canal.
 */
const MODOS_DA_COTACAO: OpcaoDeModo[] = [
  {
    valor: 'calcular', titulo: 'Só calcular e deixar pronto no Agger', curto: 'só calcular',
    explica: 'O AutoBrokers calcula e a cotação fica pronta no Agger para a sua equipe revisar e mandar.',
  },
  {
    valor: 'calcular_entregar', titulo: 'Calcular e entregar ao cliente', curto: 'calcular e entregar',
    explica: 'Calcula e prepara a proposta para o cliente. A negociação fica com a sua equipe.',
  },
  {
    valor: 'calcular_entregar_negociar', titulo: 'Calcular, entregar e negociar', curto: 'calcular, entregar e negociar',
    explica: 'Calcula, entrega e negocia dentro das regras da sua corretora.',
  },
];

type Rascunho = { modo: Modo; excecoes: Excecao[]; igualParaTodos: boolean; preferencias: Preferencias; regras: ValorDasRegras };

function rascunhoDe(d: DadosServicos): Rascunho | null {
  const e = d.efetivo.cotacao;
  if (!e) return null;
  const bruto = (d.sobreposto.servicos.cotacao || {}) as Record<string, unknown>;
  return {
    modo: e.modo, excecoes: copia(e.excecoes_do_modo || []), igualParaTodos: !bruto.preferencias_de_seguradoras,
    preferencias: copia(e.preferencias_de_seguradoras || {}),
    regras: {
      opcoes: [...(e.opcoes || [])],
      entrada: Number(e.regras?.comissao?.entrada ?? 0),
      validade: Number(e.regras?.validade_dias ?? 0),
    },
  };
}

function Carregando() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 py-6" aria-busy="true">
      {[0, 1].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
    </div>
  );
}

function Falhou({ onTentar }: { onTentar: () => void }) {
  return (
    <div className="mx-auto max-w-3xl space-y-3 py-6">
      <p className="text-sm text-foreground">Não conseguimos carregar a configuração agora.</p>
      <button type="button" onClick={onTentar} className="h-11 rounded-lg border border-border px-4 text-sm font-medium hover:bg-surface-2">
        Tentar de novo
      </button>
    </div>
  );
}

export function ConfigurarCotacao() {
  const { dados, erro, carregar, salvar, salvando, aviso, setAviso, conflito } = useServicos();
  const pode = usePodeGerir() ?? false;
  const [base, setBase] = useState<Rascunho | null>(null);
  const [r, setR] = useState<Rascunho | null>(null);
  const [avancado, setAvancado] = useState(false);

  useEffect(() => {
    if (dados) { const x = rascunhoDe(dados); setBase(x); setR(x ? copia(x) : null); }
  }, [dados]);
  const mudar = useCallback((patch: Partial<Rascunho>) => { setAviso(''); setR((x) => (x ? { ...x, ...patch } : x)); }, [setAviso]);
  const alterado = useMemo(() => Boolean(r && base && JSON.stringify(r) !== JSON.stringify(base)), [r, base]);

  if (erro) return <Falhou onTentar={carregar} />;
  if (!dados || !r || !base) return <Carregando />;

  const enviar = async () => {
    const bloco: Record<string, unknown> = { modo: r.modo, excecoes_do_modo: r.excecoes };
    if (!r.igualParaTodos) bloco.preferencias_de_seguradoras = r.preferencias;
    // SPEC-132-B · B3: só vai o que DIFERE do padrão (chave ausente = volta ao padrão do AutoBrokers) e só o que o
    // backend já aceita gravar — o resto ele recusaria com 422
    const editaveis = new Set(dados.editaveis_da_cotacao || []);
    const padrao = dados.padrao.cotacao;
    if (editaveis.has('opcoes') && JSON.stringify(r.regras.opcoes) !== JSON.stringify(padrao?.opcoes || [])) {
      bloco.opcoes = r.regras.opcoes;
    }
    if (editaveis.has('comissao') && r.regras.entrada !== padrao?.regras?.comissao?.entrada) {
      bloco.comissao = { entrada: r.regras.entrada };
    }
    if (editaveis.has('validade') && r.regras.validade !== padrao?.regras?.validade_dias) {
      bloco.validade = { padrao_dias: r.regras.validade };
    }
    const corpo: Record<string, unknown> = { servicos: { cotacao: bloco } };
    if (r.igualParaTodos) corpo.preferencias_de_seguradoras = r.preferencias;
    await salvar(corpo, 'Configuração da Cotação Rápida salva.');
  };

  return (
    <div className="mx-auto max-w-3xl space-y-10 pb-6 pt-2">
      {!pode && (
        <p className="rounded-lg border border-border-soft bg-surface p-3 text-sm text-muted-foreground" role="note">
          Você pode ver estas regras. Só um administrador da corretora muda.
        </p>
      )}
      <Grupo id="cfg-cot-o-que-fazer" titulo="O que fazer" descricao="O que o AutoBrokers faz com cada pedido de cotação.">
        <CartoesDeModo opcoes={MODOS_DA_COTACAO} valor={r.modo} nome="O que fazer" desabilitado={!pode}
          onChange={(modo) => mudar({ modo })} />
      </Grupo>
      <RegrasDoCalculo dados={dados} valor={r.regras} pode={pode} onChange={(regras) => mudar({ regras })} />
      <p className="text-sm text-muted-foreground">
        As regras da Cotação Rápida são só dela: mudar aqui não muda a Renovação Automática nem o Quem Cobra Menos.
      </p>

      <Collapsible open={avancado} onOpenChange={setAvancado} className="space-y-3">
        <CollapsibleTrigger className="flex min-h-[44px] w-full items-center justify-between rounded-xl border border-border bg-surface px-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span>
            <span className="block text-base font-semibold text-foreground">Avançado</span>
            <span className="block text-sm text-muted-foreground">Exceções e seguradoras preferidas.</span>
          </span>
          <ChevronDown size={18} strokeWidth={1.6} aria-hidden className={cn('shrink-0 text-muted-foreground transition-transform', avancado && 'rotate-180')} />
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-8">
          <Grupo id="cfg-cot-excecoes" titulo="Exceções" descricao="Por ramo ou por valor. Se duas valerem para o mesmo cálculo, vale a que faz menos.">
            <div className="p-4">
              <Excecoes excecoes={r.excecoes} ramos={dados.ramos} modos={MODOS_DA_COTACAO} desabilitado={!pode}
                onChange={(excecoes) => mudar({ excecoes })} />
            </div>
          </Grupo>
          <Grupo id="cfg-cot-seguradoras" titulo="Seguradoras preferidas" descricao="Por ramo, em ordem de preferência.">
            <div className="p-4">
              <Preferidas ramos={dados.ramos} lista={r.preferencias} igualParaTodos={r.igualParaTodos} desabilitado={!pode}
                comum={dados.comum.preferencias_de_seguradoras} nomeDoServico="Cotação Rápida"
                onChange={({ preferencias, igualParaTodos }) => mudar({ preferencias, igualParaTodos })} />
            </div>
          </Grupo>
        </CollapsibleContent>
      </Collapsible>

      <BarraSalvar visivel={pode && alterado} salvando={salvando} aviso={aviso} conflito={conflito}
        onDescartar={() => { setR(copia(base)); setAviso(''); }} onSalvar={enviar} onRecarregar={carregar} />
    </div>
  );
}

export function ConfigurarQcm() {
  const { dados, erro, carregar } = useServicos();
  if (erro) return <Falhou onTentar={carregar} />;
  if (!dados) return <Carregando />;
  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-6 pt-2">
      <Grupo id="cfg-qcm-o-que-fazer" titulo="O que fazer"
        descricao={dados.qcm_aderido ? 'A sua corretora participa do Quem Cobra Menos.' : 'A sua corretora ainda não participa do Quem Cobra Menos.'}>
        <div className="space-y-2 p-4">
          <p className="text-sm font-medium text-foreground">Calcular, entregar e negociar.</p>
          <p className="text-sm text-muted-foreground">
            No Quem Cobra Menos é sempre assim: é como o canal funciona, e a comparação entre as corretoras segue a mesma
            regra para todas. As regras da Cotação Rápida e da Renovação Automática da sua corretora não mudam o Quem Cobra Menos.
          </p>
        </div>
      </Grupo>
    </div>
  );
}
