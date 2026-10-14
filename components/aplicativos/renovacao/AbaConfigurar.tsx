'use client';

import type { PropsDaAba } from '@/lib/auxiliaries/catalog';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { AlertCircle, CheckCircle2, ChevronDown, Clock, MessageCircle } from 'lucide-react';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';

import { BarraSalvar, Grupo, Linha, NumeroComBotoes, Segmentado } from '@/components/aplicativos/configurar/pecas';
import { Excecoes, Preferidas, type OpcaoDeModo } from '@/components/aplicativos/configurar/campos';
import {
  copia, type ContaDaRenovacao, type DadosServicos, type Efetivo, type Excecao, type Modo, type Preferencias,
  useServicos,
} from '@/components/aplicativos/configurar/servicos';

/**
 * SPEC-131-B G3 — a aba CONFIGURAR da Renovação (laudo de design §4; D-131-06: no lugar do modal e de Personalização →
 * Serviços). Quatro grupos: O que fazer · Quando · Com qual conta · Avançado (recolhido).
 *
 * Grava pela config que JÁ existe (`/api/dashboard/servicos` → `servicos.renovacao.*` em `multicalculo_config`, lida pela
 * madrugada da 131-A pelo único leitor `config.py`). Salvar é explícito: a barra só aparece com alteração.
 * O produto não envia nada sozinho: "preparar o envio" deixa a apresentação e a mensagem prontas; quem envia é o
 * comercial, pelo WhatsApp do aparelho dele. Nenhum número comercial nesta tela: padrões e faixas vêm do backend.
 */
// SPEC-131-B G5 (D-131-24): o ENVIO é sempre ação do comercial nesta SPEC — a tela não oferece "calcular_entregar"
// (envio automático). O backend aceita o valor (outra SPEC o liga); aqui ele é lido como "Só calcular", que é o que o
// produto faz com ele hoje (nenhum leitor de `pode_entregar` na renovação).
const MODOS_DA_RENOVACAO: OpcaoDeModo[] = [
  {
    valor: 'calcular', titulo: 'Só calcular', curto: 'só calcular',
    explica: 'De madrugada, calcula as renovações que vão vencer e deixa tudo pronto no Agger e na aba Renovações. Quem envia ao cliente é o comercial, pelo WhatsApp dele.',
  },
  {
    valor: 'calcular_entregar_negociar', titulo: 'Enviar e negociar', curto: 'enviar e negociar', emBreve: true,
    explica: 'O AutoBrokers conversa com o cliente e negocia dentro das regras da corretora.',
  },
];

/** Só para LER exceções antigas que pediam o envio automático (nenhuma se escolhe por aqui). */
const MODOS_PARA_LER: OpcaoDeModo[] = [
  ...MODOS_DA_RENOVACAO,
  { valor: 'calcular_entregar', titulo: 'Preparar o envio', curto: 'preparar o envio', explica: '', emBreve: true },
];

/** O nome de gente de cada opção da renovação (a chave é a do produto, `presets.OPCOES_DA_RENOVACAO`). */
const NOME_DA_OPCAO: Record<string, string> = {
  anterior: 'a renovação igual ao ano passado',
  franquia_reduzida: 'com franquia reduzida',
  completa_mais: 'mais completa',
};

type Rascunho = {
  modo: Modo;
  excecoes: Excecao[];
  igualParaTodos: boolean;
  preferencias: Preferencias;
  antecedencia: number;
  reajuste: Record<string, string>;
  quantasOpcoes: number;
  teto: number;
  antecipar: number;
  usarCorretoraSeFalhar: boolean;
  contaGlobalDias: number;
  conta: ContaDaRenovacao;
};

/** O modo como a TELA o mostra: o que ela não oferece (o envio automático) é o que o produto faz — só calcular. */
const modoNaTela = (m: Modo): Modo => (MODOS_DA_RENOVACAO.some((x) => x.valor === m) ? m : 'calcular');

function rascunhoDe(d: DadosServicos): Rascunho {
  const e = d.efetivo.renovacao as Efetivo;
  const p = d.padrao.renovacao as Efetivo;
  const bruto = (d.sobreposto.servicos.renovacao || {}) as Record<string, unknown>;
  const conta = e.conta_global_se_vence_em_dias ?? p.conta_global_se_vence_em_dias ?? 0;
  return {
    modo: modoNaTela(e.modo),
    excecoes: copia(e.excecoes_do_modo || []),
    igualParaTodos: !bruto.preferencias_de_seguradoras,
    preferencias: copia(e.preferencias_de_seguradoras || {}),
    antecedencia: Number(e.antecedencia_dias ?? p.antecedencia_dias),
    reajuste: Object.fromEntries(Object.entries(e.reajuste_basica_pct || {}).map(([k, v]) => [k, v == null ? '' : String(v)])),
    quantasOpcoes: (e.opcoes || p.opcoes || []).length,
    teto: Number(e.teto_por_conta_noite ?? p.teto_por_conta_noite),
    antecipar: Number(e.antecipar_ate_dias ?? p.antecipar_ate_dias),
    usarCorretoraSeFalhar: conta > 0,
    // desligado (0) → ao religar, volta o padrão do produto
    contaGlobalDias: conta > 0 ? conta : Number(p.conta_global_se_vence_em_dias ?? 0),
    conta: e.conta ?? p.conta ?? 'responsavel',
  };
}

type Pessoa = { user_id: string; nome: string; funcoes?: string[]; agger: { conectado: boolean; situacao: string } };
type Contas = {
  corretora: { conectado: boolean; situacao?: string } | null;
  pessoas: Pessoa[];
  eu: string;
  podeGerir: boolean;
};

function useContas(): Contas | null {
  const [contas, setContas] = useState<Contas | null>(null);
  useEffect(() => {
    let vivo = true;
    Promise.all([
      fetch('/api/dashboard/agger-da-corretora', { cache: 'no-store' }).then((r) => r.json().catch(() => ({}))).catch(() => ({})),
      fetch('/api/dashboard/aggers-da-equipe', { cache: 'no-store' }).then((r) => r.json().catch(() => ({}))).catch(() => ({})),
    ]).then(([ag, eq]) => {
      if (!vivo) return;
      const c = ag?.conta;
      setContas({
        corretora: c ? { conectado: Boolean(c.tem_senha) && c.situacao !== 'senha_recusada', situacao: c.situacao } : null,
        pessoas: Array.isArray(eq?.pessoas) ? eq.pessoas : [],
        eu: String(eq?.eu || ''),
        podeGerir: Boolean(eq?.pode_gerir_todos),
      });
    });
    return () => { vivo = false; };
  }, []);
  return contas;
}

function Estado({ ok, texto, href, acao }: { ok: boolean; texto: string; href: string; acao: string }) {
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      {ok
        ? <CheckCircle2 size={16} strokeWidth={1.6} className="text-success" aria-hidden />
        : <AlertCircle size={16} strokeWidth={1.6} className="text-warning" aria-hidden />}
      <span className="text-foreground">{texto}</span>
      <span aria-hidden className="text-muted-foreground">·</span>
      <Link href={href}
        className="inline-flex min-h-11 items-center font-medium text-foreground underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-primary sm:min-h-0">
        {acao}
      </Link>
    </p>
  );
}

/**
 * "Com qual conta" — juiz de design, conserto 8: só aparece o que PEDE AÇÃO. Com tudo certo, uma linha só
 * ("Tudo conectado · ver"), em vez de três linhas de estado empilhadas.
 */
function PendenciasDaConta({
  conta, contas, eu, comerciais, semAgger,
}: { conta: ContaDaRenovacao; contas: Contas; eu?: Pessoa; comerciais: Pessoa[]; semAgger: Pessoa[] }) {
  const faltas: { texto: string; href: string; acao: string }[] = [];
  if (conta === 'responsavel' && eu && !eu.agger?.conectado) {
    faltas.push({ texto: 'Seu Agger não está conectado', href: '/dashboard/configuracoes?aba=conexoes', acao: 'conectar' });
  }
  if (conta === 'responsavel') {
    if (comerciais.length === 0) {
      faltas.push({ texto: 'Ninguém marcado como comercial na equipe', href: '/dashboard/personalizacao/equipe', acao: 'ver equipe' });
    } else if (semAgger.length > 0) {
      faltas.push({
        texto: `${semAgger.length} ${semAgger.length === 1 ? 'comercial' : 'comerciais'} sem Agger próprio`,
        href: '/dashboard/personalizacao/equipe', acao: 'ver equipe',
      });
    }
  }
  if (!contas.corretora?.conectado) {
    faltas.push({ texto: 'Agger da corretora não conectado', href: '/dashboard/personalizacao/conectores', acao: 'conectar' });
  }
  if (faltas.length === 0) {
    return <Estado ok texto="Tudo conectado" href="/dashboard/personalizacao/conectores" acao="ver" />;
  }
  return <>{faltas.map((f) => <Estado key={f.texto} ok={false} texto={f.texto} href={f.href} acao={f.acao} />)}</>;
}

export function AbaConfigurar(_props: Partial<PropsDaAba> = {}) {
  const { dados, erro, carregar, salvar, salvando, aviso, setAviso, conflito } = useServicos();
  const contas = useContas();
  const [base, setBase] = useState<Rascunho | null>(null);
  const [r, setR] = useState<Rascunho | null>(null);
  const [avancado, setAvancado] = useState(false);

  useEffect(() => {
    if (dados?.efetivo.renovacao) { const x = rascunhoDe(dados); setBase(x); setR(copia(x)); }
  }, [dados]);

  const mudar = useCallback((patch: Partial<Rascunho>) => { setAviso(''); setR((x) => (x ? { ...x, ...patch } : x)); }, [setAviso]);
  const alterado = useMemo(() => Boolean(r && base && JSON.stringify(r) !== JSON.stringify(base)), [r, base]);
  const pode = contas?.podeGerir ?? false;

  if (erro) {
    return (
      <div className="mx-auto max-w-3xl space-y-3 py-6">
        <p className="text-sm text-foreground">Não conseguimos carregar a configuração agora.</p>
        <button type="button" onClick={carregar} className="h-11 rounded-lg border border-border px-4 text-sm font-medium hover:bg-surface-2">
          Tentar de novo
        </button>
      </div>
    );
  }
  if (!dados || !r || !base) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 py-6" aria-busy="true">
        {[0, 1, 2].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
      </div>
    );
  }

  const padrao = dados.padrao.renovacao as Efetivo;
  const ordem = dados.faixas.opcoes_da_renovacao || padrao.opcoes || [];
  const faixaTeto = dados.faixas.teto_por_conta_noite || [1, Math.max(r.teto, 1)];
  const faixaAntecipar = dados.faixas.antecipar_ate_dias || [0, Math.max(r.antecipar, 0)];
  const ramos = dados.ramos;

  const comerciais = (contas?.pessoas || []).filter((p) => (p.funcoes || []).includes('comercial'));
  const semAgger = comerciais.filter((p) => !p.agger?.conectado);
  const eu = (contas?.pessoas || []).find((p) => p.user_id === contas?.eu);

  const enviar = async () => {
    const bloco: Record<string, unknown> = { modo: r.modo, excecoes_do_modo: r.excecoes };
    if (!r.igualParaTodos) bloco.preferencias_de_seguradoras = r.preferencias;
    const conta = r.usarCorretoraSeFalhar ? r.contaGlobalDias : 0;
    if (conta !== padrao.conta_global_se_vence_em_dias) bloco.conta_global_se_vence_em_dias = conta;
    const ren: Record<string, unknown> = {};
    if (r.antecedencia !== padrao.antecedencia_dias) ren.antecedencia_dias = r.antecedencia;
    const reaj: Record<string, number> = {};
    for (const [ramo, t] of Object.entries(r.reajuste)) {
      if (t.trim() === '') continue;
      const n = Number(t.replace(',', '.'));
      if (!Number.isFinite(n) || n < 0 || n > 100) { setAviso('O reajuste é um percentual de 0 a 100.'); return; }
      if (n !== (padrao.reajuste_basica_pct || {})[ramo]) reaj[ramo] = n;
    }
    if (Object.keys(reaj).length) ren.reajuste_basica_pct = reaj;
    if (Object.keys(ren).length) bloco.renovacao = ren;
    const opcoes = ordem.slice(0, r.quantasOpcoes);
    if (JSON.stringify(opcoes) !== JSON.stringify(padrao.opcoes || [])) bloco.opcoes = opcoes;
    if (r.teto !== padrao.teto_por_conta_noite) bloco.teto_por_conta_noite = r.teto;
    if (r.antecipar !== padrao.antecipar_ate_dias) bloco.antecipar_ate_dias = r.antecipar;
    if (r.conta !== (padrao.conta ?? 'responsavel')) bloco.conta = r.conta;
    const corpo: Record<string, unknown> = { servicos: { renovacao: bloco } };
    if (r.igualParaTodos) corpo.preferencias_de_seguradoras = r.preferencias;
    await salvar(corpo, 'Configuração da Renovação Automática salva.');
  };

  return (
    <div className="mx-auto max-w-3xl space-y-10 pb-6 pt-2">
      {!pode && contas && (
        <p className="rounded-lg border border-border-soft bg-surface p-3 text-sm text-muted-foreground" role="note">
          Você pode ver estas regras. Só um administrador da corretora muda.
        </p>
      )}

      <Grupo id="cfg-o-que-fazer" titulo="O que fazer" descricao="O que o AutoBrokers faz com cada renovação que vai vencer.">
        {/* juiz de design, conserto 8: uma linha SÓ DE LEITURA — havia dois cartões e só um se escolhia (escolha falsa) */}
        <div className="p-4" data-o-que-fazer="leitura">
          <p className="flex items-start gap-2 text-sm text-foreground">
            <CheckCircle2 size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-success" aria-hidden />
            <span><span className="font-medium">Calcula e deixa pronto.</span> Quem envia ao cliente é o comercial, pelo WhatsApp dele.</span>
          </p>
          <p className="mt-2 pl-6 text-sm text-muted-foreground">Enviar e negociar · em breve</p>
        </div>
        <Linha rotulo="Quantas opções para o cliente"
          info={<>Cada renovação ganha até 3 cálculos, nesta ordem: {ordem.map((o) => NOME_DA_OPCAO[o] || o).join(', ')}. Com menos opções, a madrugada termina mais cedo.</>}>
          <Segmentado rotulo="Quantas opções" valor={String(r.quantasOpcoes)} desabilitado={!pode}
            opcoes={ordem.map((_, i) => ({ valor: String(i + 1), titulo: String(i + 1) }))}
            onChange={(v) => mudar({ quantasOpcoes: Number(v) })} />
          <p className="mt-2 text-sm text-muted-foreground">
            {ordem.slice(0, r.quantasOpcoes).map((o) => NOME_DA_OPCAO[o] || o).join(' · ')}
          </p>
        </Linha>
      </Grupo>

      <Grupo id="cfg-quando" titulo="Quando" descricao="Quanto tempo antes do vencimento a renovação fica pronta.">
        <Linha rotulo="Preparar antes do vencimento" htmlFor="cfg-antecedencia"
          info="A madrugada calcula as apólices que vencem dentro deste prazo. Mais dias dão mais tempo para o comercial conversar com o cliente.">
          <NumeroComBotoes id="cfg-antecedencia" rotulo="dias antes do vencimento" valor={r.antecedencia} min={1}
            max={dados.faixas.antecedencia_dias_max} sufixo="dias antes" desabilitado={!pode}
            onChange={(antecedencia) => mudar({ antecedencia })} />
        </Linha>
        <Linha rotulo="Horário">
          <p className="flex items-center gap-2 text-sm text-foreground-2">
            <Clock size={16} strokeWidth={1.6} className="text-muted-foreground" aria-hidden />
            Fica pronto antes das 7h, todos os dias.
          </p>
        </Linha>
      </Grupo>

      <Grupo id="cfg-conta" titulo="Com qual conta" descricao="Em qual Agger o cálculo é feito e de onde sai a mensagem.">
        <Linha rotulo="Agger"
          info="Do responsável: a renovação é calculada no Agger de quem cuida da apólice, para o negócio ficar na carteira dele; o da corretora entra quando o responsável não tem Agger conectado, ou quando o dele falha perto do vencimento (veja em Avançado). Da corretora: todas as renovações são calculadas no Agger da corretora.">
          <Segmentado<ContaDaRenovacao> rotulo="Agger usado no cálculo" valor={r.conta} desabilitado={!pode}
            opcoes={[
              { valor: 'responsavel', titulo: 'Do responsável (recomendado)' },
              { valor: 'corretora', titulo: 'Da corretora' },
            ]}
            onChange={(conta) => mudar({ conta })} />
          <p className="mt-2 text-sm text-muted-foreground">
            {r.conta === 'corretora'
              ? 'Todas as renovações são calculadas no Agger da corretora. O negócio fica na conta da corretora, não na do comercial.'
              : 'Cada renovação é calculada no Agger de quem cuida da apólice.'}
          </p>
          <div className="mt-3 space-y-2">
            {contas ? (
              <PendenciasDaConta conta={r.conta} contas={contas} eu={eu} comerciais={comerciais} semAgger={semAgger} />
            ) : (
              <Skeleton className="h-11 w-full" />
            )}
          </div>
        </Linha>
        <Linha rotulo="WhatsApp"
          info="O AutoBrokers não envia nada sozinho. Na aba Renovações, o botão Enviar abre o WhatsApp do aparelho de quem clicou, com a mensagem pronta. O número de atendimento da corretora e o do Quem Cobra Menos não são usados.">
          <p className="flex items-center gap-2 text-sm text-foreground-2">
            <MessageCircle size={16} strokeWidth={1.6} className="text-muted-foreground" aria-hidden />
            Sai do celular de quem clica em Enviar.
          </p>
        </Linha>
      </Grupo>

      <Collapsible open={avancado} onOpenChange={setAvancado} className="space-y-3">
        <CollapsibleTrigger
          className="flex min-h-[44px] w-full items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span>
            <span className="block text-base font-semibold text-foreground">Avançado</span>
            <span className="block text-sm text-muted-foreground">Reajuste, limite por noite e seguradoras preferidas.</span>
          </span>
          <ChevronDown size={18} strokeWidth={1.6} aria-hidden className={cn('shrink-0 text-muted-foreground transition-transform', avancado && 'rotate-180')} />
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-8">
          {/* Com um modo só para escolher (o envio é sempre do comercial), uma exceção nova não mudaria nada: o grupo
              aparece só para ver e tirar as que já existem. */}
          {r.excecoes.length > 0 && (
            <Grupo id="cfg-excecoes" titulo="Exceções" descricao="Exceções antigas, por ramo ou por valor. O envio é sempre do comercial.">
              <div className="p-4">
                <Excecoes excecoes={r.excecoes} ramos={ramos} modos={MODOS_PARA_LER} desabilitado={!pode}
                  onChange={(excecoes) => mudar({ excecoes })} />
              </div>
            </Grupo>
          )}

          <Grupo id="cfg-limites" titulo="Limites da madrugada">
            {Object.keys(r.reajuste).length > 0 && (
              <Linha rotulo="Reajuste da cobertura básica"
                info="Em condomínio, residencial e empresarial, a cobertura básica da renovação sobe este percentual sobre a do ano anterior.">
                <div className="grid gap-2">
                  {Object.keys(r.reajuste).map((ramo) => (
                    <label key={ramo} className="flex items-center justify-between gap-2 rounded-lg border border-border-soft px-3 py-2">
                      <span className="text-sm text-foreground">{ramos.find((x) => x.codigo === ramo)?.nome ?? `Ramo ${ramo}`}</span>
                      <span className="flex items-center gap-1">
                        <input inputMode="decimal" disabled={!pode} aria-label={`Reajuste em ${ramos.find((x) => x.codigo === ramo)?.nome ?? ramo}, em %`}
                          className="h-10 w-20 rounded-lg border border-border bg-background px-2 text-right text-sm tabular-nums"
                          value={r.reajuste[ramo] ?? ''}
                          placeholder={String((padrao.reajuste_basica_pct || {})[ramo] ?? '')}
                          onChange={(e) => mudar({ reajuste: { ...r.reajuste, [ramo]: e.target.value } })} />
                        <span className="text-sm text-muted-foreground">%</span>
                      </span>
                    </label>
                  ))}
                </div>
              </Linha>
            )}
            <Linha rotulo="Máximo por Agger por noite" htmlFor="cfg-teto"
              info="Quantas renovações cada Agger calcula numa noite. O que passar disso é adiantado para as noites anteriores.">
              <NumeroComBotoes id="cfg-teto" rotulo="renovações por noite" valor={r.teto} min={faixaTeto[0]} max={faixaTeto[1]}
                sufixo="por noite" desabilitado={!pode} onChange={(teto) => mudar({ teto })} />
            </Linha>
            <Linha rotulo="Adiantar até" htmlFor="cfg-antecipar"
              info="Quando uma noite passa do máximo, as renovações que sobram podem ser calculadas até este número de dias antes do previsto. Nunca depois do vencimento.">
              <NumeroComBotoes id="cfg-antecipar" rotulo="dias de antecipação" valor={r.antecipar} min={faixaAntecipar[0]}
                max={faixaAntecipar[1]} sufixo="dias antes" desabilitado={!pode} onChange={(antecipar) => mudar({ antecipar })} />
            </Linha>
            {r.conta === 'responsavel' && (
            <Linha rotulo="Se o Agger do responsável falhar, usar o da corretora"
              info="Se o Agger de quem cuida da apólice recusar a senha, a renovação espera por ele. Ligado, ela passa para o Agger da corretora quando faltar pouco para vencer.">
              <div className="space-y-3">
                <Switch checked={r.usarCorretoraSeFalhar} disabled={!pode} aria-label="Usar o Agger da corretora se o do responsável falhar"
                  onCheckedChange={(v) => mudar({ usarCorretoraSeFalhar: Boolean(v) })} />
                {r.usarCorretoraSeFalhar && (
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Quando faltar menos de</p>
                    <NumeroComBotoes id="cfg-conta-global" rotulo="dias para vencer" valor={r.contaGlobalDias} min={1}
                      max={dados.faixas.conta_global_dias_max} sufixo="dias para vencer" desabilitado={!pode}
                      onChange={(contaGlobalDias) => mudar({ contaGlobalDias })} />
                  </div>
                )}
              </div>
            </Linha>
            )}
          </Grupo>

          <Grupo id="cfg-seguradoras" titulo="Seguradoras preferidas" descricao="Por ramo, em ordem de preferência.">
            <div className="p-4">
              <Preferidas ramos={ramos} lista={r.preferencias} igualParaTodos={r.igualParaTodos} desabilitado={!pode}
                comum={dados.comum.preferencias_de_seguradoras} nomeDoServico="Renovação Automática"
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

export default AbaConfigurar;
