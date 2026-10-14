'use client';

// SPEC-132-B · B3 (D-132B-06) — "As regras do cálculo" da Cotação Rápida, na aba Configurar.
//
// O Founder: "antes tinha um card em Serviços com as especificações e regras para calcular as cotações". Aqui elas
// aparecem TODAS, em linguagem de gente, cada uma marcada "Padrão do AutoBrokers" ou "Mudada pela corretora" (o
// efetivo comparado com o padrão — os dois vêm do backend, lidos pelos MESMOS leitores do cálculo). Três se editam:
// quais versões calcular, a comissão de entrada e a validade — e só quando o backend diz que já aceita gravar
// (`editaveis_da_cotacao`). ⛔ Nenhum número comercial escrito aqui: valores, padrões e faixas chegam do backend.

import type { ReactNode } from 'react';

import { Selo } from '@/components/aplicativos/casca/Selo';
import { Grupo, Linha, NumeroComBotoes } from '@/components/aplicativos/configurar/pecas';
import type { DadosServicos, RegrasDaCotacao } from '@/components/aplicativos/configurar/servicos';
import { cn } from '@/lib/utils';

/** O nome de cada versão como o corretor fala (a SPEC: "Calculamos 3 versões: Completa, Econômica e Completa+"). */
export const VERSOES: Record<string, { titulo: string; explica: string }> = {
  padrao: { titulo: 'Completa', explica: 'A proteção completa. É dela que sai a opção Recomendada.' },
  economica: {
    titulo: 'Econômica',
    explica: 'A mesma base com coberturas mais enxutas. Vira a opção Mais em conta quando sai mais barata.',
  },
  completa_mais: { titulo: 'Completa+', explica: 'A Completa com coberturas a mais. Vira a opção Mais completa.' },
  minima: { titulo: 'Mínima', explica: 'O mínimo do mínimo, só para mostrar a maior economia possível.' },
};

const PAPEL: Record<string, string> = {
  completa: 'Recomendada',
  economica: 'Mais em conta',
  completa_mais: 'Mais completa',
  minima: 'Mínima',
};

const PASSO_DO_MAIS_BARATO: Record<string, string> = {
  desconto: 'desconto',
  comissao: 'comissão',
  franquia: 'franquia',
  carro_reserva: 'carro reserva',
  vidros: 'vidros',
  assistencia: 'assistência',
};

const RAMO: Record<string, string> = { '31': 'Automóvel', '16': 'Condomínio', '2': 'Residencial', '18': 'Empresarial' };

export type ValorDasRegras = { opcoes: string[]; entrada: number; validade: number };

const num = (n: number | null | undefined) =>
  typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : '—';
const pct = (n: number | null | undefined) => (num(n) === '—' ? '—' : `${num(n)}%`);
const dias = (n: number | null | undefined) =>
  typeof n === 'number' && Number.isFinite(n) ? (n === 1 ? '1 dia' : `${n} dias`) : '—';
const lista = (itens: string[]) =>
  itens.length <= 1 ? itens.join('') : `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
const igual = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

/** "Padrão do AutoBrokers" × "Mudada pela corretora" — nunca só cor: a palavra vai junto. */
function Origem({ mudada }: { mudada: boolean }) {
  return mudada ? <Selo tom="info" rotulo="Mudada pela corretora" /> : <Selo tom="neutral" rotulo="Padrão do AutoBrokers" />;
}

function Valor({ children, mudada }: { children: ReactNode; mudada: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
      <span className="text-sm text-foreground">{children}</span>
      <Origem mudada={mudada} />
    </div>
  );
}

/** As frases das regras que só se MOSTRAM (puras — o teste as chama). */
export function frasesDasRegras(r: RegrasDaCotacao) {
  const c = r.comissao || {};
  const porRamo = Object.entries(r.comissao_por_ramo || {})
    .filter(([ramo]) => ramo !== '31')
    .map(([ramo, v]) => `${RAMO[ramo] || ramo} ${pct(v)}`);
  const papeis = Object.entries(r.calculo_por_papel || {})
    .filter(([papel]) => papel !== 'minima')
    .map(([papel, calc]) => `a ${PAPEL[papel] || papel} sai da ${VERSOES[calc]?.titulo || calc}`);
  const passos = (r.ordem_do_mais_barato || []).map((p) => PASSO_DO_MAIS_BARATO[p] || p.replace(/_/g, ' '));
  const essenciais = Object.entries(r.coberturas_essenciais || {}).map(
    ([ramo, l]) => `${RAMO[ramo] || ramo}: ${l.length === 1 ? '1 cobertura' : `${l.length} coberturas`}`,
  );
  return {
    opcoesMostradas: `${r.opcoes_no_whatsapp ?? '—'} na mensagem do WhatsApp e ${r.opcoes_na_pagina ?? '—'} na apresentação`,
    negociacao: `Desce ${num(c.passo_pp)} ${c.passo_pp === 1 ? 'ponto' : 'pontos'} por vez até ${pct(c.autonomo_minimo)}; até ${pct(c.piso)} só para fechar negócio`,
    comissaoPorRamo: porRamo.length ? porRamo.join(' · ') : 'A mesma comissão de entrada',
    papeis: papeis.length ? `${papeis.join('; ')}.` : '—',
    alvo: `Mira entre ${pct(r.alvo_abaixo_da_atual_pct?.minimo)} e ${pct(r.alvo_abaixo_da_atual_pct?.maximo)} abaixo do seguro atual`,
    maisBarato: passos.length ? `Primeiro ${lista(passos)}, nesta ordem` : '—',
    essenciais: essenciais.length ? essenciais.join(' · ') : '—',
    validadePorSeguradora: Object.keys(r.validade_por_seguradora || {}).length,
  };
}

export function RegrasDoCalculo({
  dados,
  valor,
  onChange,
  pode,
}: {
  dados: DadosServicos;
  valor: ValorDasRegras;
  onChange: (v: ValorDasRegras) => void;
  pode: boolean;
}) {
  const r = dados.efetivo.cotacao?.regras;
  const p = dados.padrao.cotacao?.regras;
  const padraoOpcoes = dados.padrao.cotacao?.opcoes || [];
  const editaveis = new Set(dados.editaveis_da_cotacao || []);
  if (!r || !p) {
    return (
      <Grupo id="cfg-cot-regras" titulo="As regras do cálculo">
        <p className="p-4 text-sm text-muted-foreground">Não deu para ler as regras agora. Recarregue a página.</p>
      </Grupo>
    );
  }
  const f = frasesDasRegras(r);
  const fp = frasesDasRegras(p);
  const aceitas = dados.faixas.opcoes_da_cotacao || padraoOpcoes;
  const [entMin, entMax] = dados.faixas.comissao_entrada_da_cotacao || [valor.entrada, valor.entrada];
  const [valMin, valMax] = dados.faixas.validade_dias_da_cotacao || [valor.validade, valor.validade];
  const podeOpcoes = pode && editaveis.has('opcoes');
  const podeComissao = pode && editaveis.has('comissao');
  const podeValidade = pode && editaveis.has('validade');
  const algumaTravada = pode && (!podeOpcoes || !podeComissao || !podeValidade);

  const alternar = (o: string) => {
    const tem = valor.opcoes.includes(o);
    if (tem && valor.opcoes.length === 1) return; // ao menos uma versão
    const novas = tem ? valor.opcoes.filter((x) => x !== o) : [...valor.opcoes, o];
    onChange({ ...valor, opcoes: aceitas.filter((x) => novas.includes(x)) });
  };

  return (
    <Grupo
      id="cfg-cot-regras"
      titulo="As regras do cálculo"
      descricao="Como o AutoBrokers calcula cada cotação. Valem só para a Cotação Rápida."
    >
      <Linha
        rotulo="Versões calculadas"
        info={
          <>
            Cada versão é um cálculo no Agger, em todas as seguradoras da conta.
            {aceitas.map((o) => (
              <span key={o} className="mt-2 block">
                <strong className="font-semibold text-foreground">{VERSOES[o]?.titulo || o}:</strong> {VERSOES[o]?.explica}
              </span>
            ))}
          </>
        }
      >
        {podeOpcoes ? (
          <div className="space-y-2">
            <div role="group" aria-label="Versões calculadas" className="flex flex-wrap gap-2">
              {aceitas.map((o) => {
                const marcada = valor.opcoes.includes(o);
                return (
                  <button
                    key={o}
                    type="button"
                    role="checkbox"
                    aria-checked={marcada}
                    onClick={() => alternar(o)}
                    disabled={marcada && valor.opcoes.length === 1}
                    className={cn(
                      'min-h-11 rounded-lg border px-3 text-sm transition-colors sm:min-h-10',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed',
                      marcada
                        ? 'border-primary/60 bg-brand-soft font-medium text-foreground'
                        : 'border-border text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {VERSOES[o]?.titulo || o}
                  </button>
                );
              })}
            </div>
            <p className="text-sm text-muted-foreground">
              {valor.opcoes.length === 1
                ? 'Calculamos 1 versão'
                : `Calculamos ${valor.opcoes.length} versões`}
              : {lista(valor.opcoes.map((o) => VERSOES[o]?.titulo || o))}.
            </p>
            <Origem mudada={!igual(valor.opcoes, padraoOpcoes)} />
          </div>
        ) : (
          <Valor mudada={!igual(dados.efetivo.cotacao?.opcoes, padraoOpcoes)}>
            {(dados.efetivo.cotacao?.opcoes || []).length === 1 ? 'Calculamos 1 versão' : `Calculamos ${(dados.efetivo.cotacao?.opcoes || []).length} versões`}:{' '}
            {lista((dados.efetivo.cotacao?.opcoes || []).map((o) => VERSOES[o]?.titulo || o))}
          </Valor>
        )}
      </Linha>

      <Linha
        rotulo="Comissão de entrada"
        htmlFor={podeComissao ? 'cfg-cot-comissao' : undefined}
        info="Vale para Residencial, Condomínio e Empresarial: é a comissão com que esses cálculos começam num cliente novo (quando o ramo não tem uma comissão própria) e, na negociação, ela desce aos poucos, nunca abaixo do piso. No carro, o cálculo sai com a comissão que está na conta do Agger."
      >
        {podeComissao ? (
          <div className="space-y-2">
            <NumeroComBotoes id="cfg-cot-comissao" rotulo="Comissão de entrada" valor={valor.entrada} min={Math.ceil(entMin)}
              max={Math.floor(entMax)} sufixo="%" onChange={(entrada) => onChange({ ...valor, entrada })} />
            <Origem mudada={valor.entrada !== p.comissao.entrada} />
          </div>
        ) : (
          <Valor mudada={r.comissao.entrada !== p.comissao.entrada}>{pct(r.comissao.entrada)}</Valor>
        )}
      </Linha>

      <Linha
        rotulo="Validade da cotação"
        htmlFor={podeValidade ? 'cfg-cot-validade' : undefined}
        info="Por quantos dias os preços valem. A apresentação mostra a data até quando vale, nunca um cronômetro. Se uma seguradora do quadro tem validade menor, vale a menor."
      >
        {podeValidade ? (
          <div className="space-y-2">
            <NumeroComBotoes id="cfg-cot-validade" rotulo="Validade da cotação" valor={valor.validade} min={valMin}
              max={valMax} sufixo={valor.validade === 1 ? 'dia' : 'dias'} onChange={(validade) => onChange({ ...valor, validade })} />
            <Origem mudada={valor.validade !== p.validade_dias} />
          </div>
        ) : (
          <Valor mudada={r.validade_dias !== p.validade_dias}>{dias(r.validade_dias)}</Valor>
        )}
      </Linha>

      <Linha rotulo="Opções mostradas" info="Quantas opções vão na mensagem que você manda e quantas a apresentação mostra lado a lado.">
        <Valor mudada={f.opcoesMostradas !== fp.opcoesMostradas}>{f.opcoesMostradas}</Valor>
      </Linha>
      <Linha rotulo="De onde sai cada opção" info="Cada opção da apresentação vem de uma das versões calculadas.">
        <Valor mudada={f.papeis !== fp.papeis}>{f.papeis}</Valor>
      </Linha>
      <Linha rotulo="Negociação da comissão" info="Até onde a comissão pode descer para o cliente fechar, e de quanto em quanto.">
        <Valor mudada={f.negociacao !== fp.negociacao}>{f.negociacao}</Valor>
      </Linha>
      <Linha rotulo="Comissão em residencial, condomínio e empresarial">
        <Valor mudada={f.comissaoPorRamo !== fp.comissaoPorRamo}>{f.comissaoPorRamo}</Valor>
      </Linha>
      <Linha rotulo="Cliente novo com apólice" info="Quando o cliente manda a apólice de hoje, a cotação procura um preço abaixo do que ele paga, guardando margem.">
        <Valor mudada={f.alvo !== fp.alvo}>{f.alvo}</Valor>
      </Linha>
      <Linha rotulo="Para chegar mais barato" info="A ordem em que o preço é baixado: primeiro a margem, só depois a cobertura.">
        <Valor mudada={f.maisBarato !== fp.maisBarato}>{f.maisBarato}</Valor>
      </Linha>
      <Linha rotulo="Coberturas que todo seguro de imóvel precisa ter" info="Para nenhuma seguradora parecer mais barata por cobrir menos, a comparação de residencial, condomínio e empresarial exige estas coberturas.">
        <Valor mudada={f.essenciais !== fp.essenciais}>{f.essenciais}</Valor>
      </Linha>
      <Linha rotulo="Preço igual entre seguradoras">
        <Valor mudada={false}>A seguradora preferida da corretora aparece primeiro</Valor>
      </Linha>

      {algumaTravada && (
        <p className="p-4 text-sm text-muted-foreground" role="note">
          Algumas destas regras ainda não se mudam por aqui. Elas seguem o padrão do AutoBrokers.
        </p>
      )}
    </Grupo>
  );
}
