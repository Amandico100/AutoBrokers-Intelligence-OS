'use client';

// SPEC-139 · L2 — os CAMPOS de uma rotina, extraídos do modal do `PainelDeRotinas` (D-139-04), no layout da aba
// Configurar (laudo de design §4: grupos, rótulo + ⓘ em Popover à esquerda, controle à direita, Avançado recolhido).
//
// O MESMO componente desenha o modal do painel e a aba Configurar da Cobrança. Ele não guarda estado e não grava:
// todo clique chama o hook (`useFormularioDaRotina`), que chama as funções puras de `formulario.ts`. Os porquês de
// cada campo (SPEC-078, SPEC-EXTRA-001, SPEC-EXTRA-001.6) vieram com ele.

import { useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { AlertTriangle, ChevronDown, Plus } from 'lucide-react';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Grupo, Linha, NumeroComBotoes, Segmentado } from '@/components/aplicativos/configurar/pecas';
import { cn } from '@/lib/utils';

import { DIAS_DA_SEMANA, MODOS_COM_MOTOR, diasMarcados, numeroDigitadoNoModal } from './formulario';
import type { FormularioDaRotinaAberto } from './useFormularioDaRotina';

/**
 * Os campos da mensagem com NOME DE GENTE (juiz de design 139, Configurar §3): o chip insere o campo no texto — o
 * VALOR gravado continua o MESMO token (`{primeiro_nome}`), igual a quem o digitasse. `{cliente_nome}` e `{apolice}`
 * são sinônimos que o motor também aceita (`CHAVES_DA_MENSAGEM`): continuam valendo se digitados, mas não ganham chip.
 */
const CAMPOS_DA_MENSAGEM: { chave: string; nome: string }[] = [
  { chave: '{primeiro_nome}', nome: 'Primeiro nome' },
  { chave: '{nome_segurado}', nome: 'Nome completo' },
  { chave: '{nome_atendente}', nome: 'Quem assina' },
  { chave: '{nome_corretora}', nome: 'Nome da corretora' },
  { chave: '{nome_seguradora}', nome: 'Seguradora' },
  { chave: '{numero_parcela}', nome: 'Número da parcela' },
  { chave: '{item_segurado}', nome: 'Bem segurado' },
  { chave: '{numero_apolice}', nome: 'Número da apólice' },
  { chave: '{vencimento}', nome: 'Vencimento' },
  { chave: '{valor}', nome: 'Valor' },
  { chave: '{recibo}', nome: 'Recibo' },
  { chave: '{portal}', nome: 'Portal' },
];

/** O texto com o campo inserido onde está o cursor (sem cursor: no fim). Puro. */
function comCampoInserido(texto: string, chave: string, inicio: number | null, fim: number | null): string {
  const a = inicio ?? texto.length;
  const b = fim ?? a;
  return `${texto.slice(0, a)}${chave}${texto.slice(b)}`;
}

const CAMPO =
  'h-11 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground sm:h-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60';
const AREA =
  'w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60';

/** O aviso amarelo do formulário: ícone + texto escuro (a cor do estado fica na borda e no ícone — AA no claro). */
function Atencao({ children }: { children: ReactNode }) {
  return (
    <p className="mt-2 flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-foreground" role="note">
      <AlertTriangle size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-warning" aria-hidden />
      <span>{children}</span>
    </p>
  );
}

function Ajudinha({ children }: { children: ReactNode }) {
  return <p className="mt-1.5 text-sm text-muted-foreground">{children}</p>;
}

export function FormularioDaRotina({
  f, auxiliarNome, desabilitado = false, avancadoExtra, prefixo = 'rotina',
}: {
  f: FormularioDaRotinaAberto;
  auxiliarNome: string;
  desabilitado?: boolean;
  /** o que mais entra no Avançado (ex.: liberar o reenvio de teste, pausar a rotina) */
  avancadoExtra?: ReactNode;
  /** prefixo dos `id` (o modal e a aba podem estar na mesma página) */
  prefixo?: string;
}) {
  const { form, derivados, portais, cobrancaDegradada } = f;
  const {
    billingConfig, billingPortalKeys, billingSendMode, billingModoLegado, billingTeamNumber, billingConfirmacaoCliente,
    textoDaMensagem, chavesDesconhecidas, previaDaMensagem, billingMaxBoletos, billingTestNumber, billingAttendantName,
    billingDiasEntreCobrancas,
  } = derivados;
  const [avancado, setAvancado] = useState(false);
  const caixaDaMensagem = useRef<HTMLTextAreaElement>(null);
  const id = (nome: string) => `${prefixo}-${nome}`;
  /** O chip do campo: insere o token onde está o cursor — a MESMA gravação de quem digita no texto. */
  const inserirCampo = (chave: string) => {
    const caixa = caixaDaMensagem.current;
    const inicio = caixa ? caixa.selectionStart : null;
    f.setBillingConfig({ message_template: comCampoInserido(textoDaMensagem, chave, inicio, caixa ? caixa.selectionEnd : null) });
    const pos = (inicio ?? textoDaMensagem.length) + chave.length;
    requestAnimationFrame(() => {
      if (!caixa) return;
      caixa.focus();
      caixa.setSelectionRange(pos, pos);
    });
  };
  const marcados = diasMarcados(form);

  return (
    <div className="space-y-10">
      {/* 🔴 SPEC-078 D.1/D.2 — o NOME é o do aplicativo (fixo), e "o que ele faz" é LEITURA quando o aplicativo tem
          motor próprio: em cobrança `instructions` é inerte (`routine_engine` desvia antes do prompt). Em rotina
          genérica (que roda por modelo de linguagem) ele funciona e continua editável. */}
      <Grupo id={id('o-que-faz')} titulo="O que ele faz" descricao={`O que ${auxiliarNome} repete em cada execução.`}>
        <Linha rotulo="Em cada execução" htmlFor={billingConfig ? undefined : id('instrucoes')}
          info={billingConfig
            ? 'Isto é o que o aplicativo faz, e não muda. O que você personaliza abaixo é quando ele roda e como ele fala.'
            : 'Descreva a tarefa completa, como se instruísse um assistente. É o texto que ele segue em toda execução.'}>
          {billingConfig ? (
            <p className="whitespace-pre-wrap text-sm leading-6 text-foreground-2">
              {form.instructions || 'Varre os portais das seguradoras selecionadas, encontra os inadimplentes, baixa os boletos disponíveis e monta o relatório.'}
            </p>
          ) : (
            <textarea id={id('instrucoes')} value={form.instructions} disabled={desabilitado}
              onChange={(e) => f.mudar({ instructions: e.target.value })} rows={4}
              placeholder="Descreva a tarefa completa, como se instruísse um assistente…" className={AREA} />
          )}
        </Linha>
        {/* 🔴 SPEC-078 D.3 — "Conhecimento" SOME da cobrança: ele só é lido em `render_task_prompt`, que rotina de
            cobrança nunca alcança. Em rotina genérica ele tem função real. */}
        {!billingConfig && (
          <Linha rotulo="Conhecimento (opcional)" htmlFor={id('conhecimento')}
            info="Usado em toda execução: argumentos, perguntas frequentes, tom de voz.">
            <textarea id={id('conhecimento')} value={form.knowledge} disabled={desabilitado}
              onChange={(e) => f.mudar({ knowledge: e.target.value })} rows={3}
              placeholder="Ex.: argumentos de venda, objeções comuns, perguntas frequentes, tom de voz…" className={AREA} />
          </Linha>
        )}
      </Grupo>

      {billingConfig && (
        <>
          <Grupo id={id('seguradoras')} titulo="Onde ele procura" descricao="As seguradoras em que ele procura parcelas em atraso.">
            <Linha rotulo="Seguradoras"
              info="Marque quantas quiser. Ele procura em uma por vez e junta tudo num relatório só. Só aparecem prontas as seguradoras que a corretora conectou e em que a cobrança automática já existe.">
              {cobrancaDegradada && (
                <Atencao>
                  Não deu para confirmar quais seguradoras estão prontas agora. Nenhuma aparece como pronta até a
                  confirmação: marcar como pronta sem conferir faz a busca falhar.
                </Atencao>
              )}
              {portais.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Nenhum portal conectado ainda.{' '}
                  <Link href="/dashboard/personalizacao/conectores/portais"
                    className="font-medium text-foreground underline-offset-4 hover:underline dark:text-primary">
                    Conectar um portal →
                  </Link>
                </p>
              ) : (
                <div className="grid gap-1 sm:grid-cols-2">
                  {portais.map((p) => {
                    const disponivel = p.conectado && p.automatizado;
                    return (
                      <label key={p.key}
                        className={cn('flex min-h-[44px] items-start gap-2.5 rounded-lg px-2 py-2 text-sm',
                          disponivel ? 'text-foreground hover:bg-surface-2' : 'text-muted-foreground')}>
                        <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[hsl(var(--primary))]"
                          disabled={!disponivel || desabilitado}
                          checked={disponivel && billingPortalKeys.includes(p.key)}
                          onChange={(e) => f.alternarPortal(p.key, e.target.checked)} />
                        <span>
                          {p.name}
                          {!p.conectado && <span className="block text-xs">sem login desta corretora</span>}
                          {p.conectado && !p.automatizado && <span className="block text-xs">em breve</span>}
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </Linha>
          </Grupo>

          <Grupo id={id('envio')} titulo="Como ele envia" descricao="Para quem vai a mensagem com o boleto, e quem assina.">
            {/* 🔴 SPEC-EXTRA-001 — sem valor quando a config é legada: pré-selecionar "Teste" esconderia o problema e
                pré-selecionar "cliente" ligaria envio real por conta própria. */}
            <div role="radiogroup" aria-label="Modo de envio" className="grid gap-2 p-4">
              {MODOS_COM_MOTOR.map((m) => {
                const marcado = !billingModoLegado && billingSendMode === m.valor;
                const [titulo, explica] = m.rotulo.split(' — ');
                return (
                  <button key={m.valor} type="button" role="radio" aria-checked={marcado} disabled={desabilitado}
                    data-modo={m.valor}
                    onClick={() => f.setBillingConfig({ send_mode: m.valor })}
                    className={cn(
                      'flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60',
                      marcado ? 'border-primary bg-brand-soft' : 'border-border hover:bg-surface-2',
                    )}>
                    <span aria-hidden className={cn('mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border',
                      marcado ? 'border-primary' : 'border-border')}>
                      {marcado && <span className="h-2 w-2 rounded-full bg-primary" />}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-foreground">{titulo}</span>
                      {explica && <span className="mt-0.5 block text-sm text-muted-foreground">{explica}</span>}
                    </span>
                  </button>
                );
              })}
              {billingModoLegado && (
                <Atencao>Esta configuração é antiga e <strong>não envia nada</strong>. Escolha uma modalidade.</Atencao>
              )}
            </div>

            {billingSendMode === 'test' && (
              <Linha rotulo="Número que recebe a simulação" htmlFor={id('teste')}
                info="Em Teste, o segurado nunca recebe nada. A mensagem e o boleto vão só para este número, com um aviso de que é simulação.">
                {/* ⛔ Nunca um telefone real como placeholder: a máscara mostra o FORMATO. */}
                <input id={id('teste')} value={billingTestNumber} disabled={desabilitado} inputMode="tel"
                  onChange={(e) => f.setBillingConfig({ test_number: e.target.value })}
                  placeholder="55 47 9XXXX-XXXX" className={CAMPO} />
                <Ajudinha>Em Teste, o segurado <strong>nunca</strong> recebe nada.</Ajudinha>
              </Linha>
            )}

            {/* 🔴 SPEC-EXTRA-001 §1 — em `equipe` nada sai para o segurado: o envio é interno, para um número só, o da
                própria corretora. Quem repassa é a atendente — e é por isso que existe a fila de pendências. */}
            {billingSendMode === 'equipe' && (
              <Linha rotulo="WhatsApp de quem recebe o pacote" htmlFor={id('equipe')}
                info="A atendente recebe a mensagem pronta e o boleto, e repassa ao cliente. Depois de repassar, ela marca em Cobranças, em Precisa de você: é assim que a parcela sai da fila.">
                <input id={id('equipe')} value={billingTeamNumber} disabled={desabilitado} inputMode="tel"
                  onChange={(e) => f.setBillingConfig({ team_number: e.target.value })}
                  placeholder="55 47 9XXXX-XXXX" className={CAMPO} />
                <Ajudinha>Um número só, de alguém da sua equipe.</Ajudinha>
              </Linha>
            )}

            {/* 🔴 SPEC-EXTRA-001 §1 — o único controle desta tela que faz um segurado receber uma mensagem sem ninguém
                no meio. A confirmação é um ato separado, e o motor recusa sem ela (`confirmacao_cliente`). */}
            {billingSendMode === 'cliente' && (
              <div className="p-4">
                <div className="rounded-lg border border-warning/40 bg-warning/10 p-3">
                  <p className="text-sm leading-6 text-foreground">
                    O cliente vai receber diretamente pelo WhatsApp da corretora. Cada parcela é cobrada uma vez; a
                    resposta dele chega ao atendimento.
                  </p>
                  <label className="mt-2 flex min-h-[44px] items-center gap-2.5 text-sm font-medium text-foreground">
                    <input type="checkbox" className="h-4 w-4 accent-[hsl(var(--primary))]" disabled={desabilitado}
                      checked={billingConfirmacaoCliente}
                      onChange={(e) => f.setBillingConfig({ confirmacao_cliente: e.target.checked })} />
                    <span>Entendi e confirmo o envio direto ao cliente.</span>
                  </label>
                </div>
              </div>
            )}

            {/* 🔴 SPEC-EXTRA-001.6 P0.4 — o nome que o segurado vai ler. Sem ele, em Encaminhar/Enviar a rotina fica
                RETIDA (o motor recusa — não é só a tela). */}
            <Linha rotulo="Quem assina a mensagem" htmlFor={id('assina')}
              info="É o nome que o segurado vai ler. Use o primeiro nome de quem atende. Nos modos Encaminhar e Enviar ao cliente, sem este nome nada sai.">
              <input id={id('assina')} value={billingAttendantName} disabled={desabilitado}
                onChange={(e) => f.setBillingConfig({ attendant_name: e.target.value })}
                placeholder="o primeiro nome de quem atende" className={CAMPO} />
              <Ajudinha>
                O segurado lê: <em>&quot;Aqui é a {billingAttendantName || '…'}, da sua corretora&quot;</em>.
              </Ajudinha>
            </Linha>
          </Grupo>

          <Grupo id={id('mensagem')} titulo="A mensagem" descricao="O texto que vai junto com o boleto.">
            <div className="space-y-3 p-4">
              <label htmlFor={id('texto')} className="text-sm font-medium text-foreground">Mensagem ao cliente</label>
              <textarea id={id('texto')} ref={caixaDaMensagem} value={textoDaMensagem} disabled={desabilitado} rows={8}
                onChange={(e) => f.setBillingConfig({ message_template: e.target.value })}
                className={cn(AREA, 'leading-6')} />
              <div className="space-y-2">
                <p id={id('campos')} className="text-sm text-muted-foreground">
                  Toque num campo para colocá-lo no texto. Na hora de enviar, ele vira o dado de cada segurado.
                </p>
                <div className="flex flex-wrap gap-1.5" role="group" aria-labelledby={id('campos')}>
                  {CAMPOS_DA_MENSAGEM.map((c) => (
                    <button key={c.chave} type="button" disabled={desabilitado} data-campo={c.chave}
                      aria-label={`Colocar o campo ${c.nome} no texto`}
                      onClick={() => inserirCampo(c.chave)}
                      className="inline-flex h-11 items-center gap-1 rounded-full border border-border bg-background px-3 text-sm text-foreground transition-colors hover:bg-surface-2 disabled:opacity-50 sm:h-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                      <Plus size={14} strokeWidth={1.6} className="text-muted-foreground" aria-hidden />
                      {c.nome}
                    </button>
                  ))}
                </div>
              </div>
              {chavesDesconhecidas.length > 0 && (
                <Atencao>
                  Estes campos não existem e vão sair <strong>em branco</strong> na mensagem: {chavesDesconhecidas.join(', ')}
                </Atencao>
              )}
              {/* 🔴 SPEC-078 E.3 — a mensagem EXATA que o segurado leria. Em Teste, o que chega no celular leva um
                  cabeçalho de simulação — e isso FICA: teste indistinguível do real é como se manda o real achando
                  que é teste. */}
              {/* juiz de design 139 (Configurar §4): o indicador de abrir. O `<details>` nativo já anuncia aberto/fechado
                  ao leitor de tela; a seta gira com o estado. */}
              <details className="group rounded-lg border border-border-soft bg-background p-3">
                <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-3 rounded-md text-sm font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
                  Ver como o segurado vai ler
                  <ChevronDown size={18} strokeWidth={1.6} aria-hidden
                    className="shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
                </summary>
                <p className="mt-2 whitespace-pre-wrap rounded-md bg-surface-2 px-3 py-2 text-sm leading-6 text-foreground">
                  {previaDaMensagem}
                </p>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  Exemplo com dados fictícios. Em modo Teste a mensagem chega ao seu número com um cabeçalho dizendo que é
                  simulação.
                </p>
              </details>
            </div>
          </Grupo>
        </>
      )}

      <Grupo id={id('quando')} titulo="Quando" descricao="Em que dias e a que horas ela roda (horário de Brasília).">
        <Linha rotulo="Frequência">
          <Segmentado<'daily' | 'interval'> rotulo="Frequência" desabilitado={desabilitado}
            valor={form.kind === 'interval' ? 'interval' : 'daily'}
            opcoes={[{ valor: 'daily', titulo: 'Diária (horário fixo)' }, { valor: 'interval', titulo: 'A cada N minutos' }]}
            onChange={(k) => f.mudar({ kind: k })} />
        </Linha>
        {form.kind === 'daily' ? (
          <>
            <Linha rotulo="Horário" htmlFor={id('horario')}>
              <input id={id('horario')} type="time" value={form.time} disabled={desabilitado}
                onChange={(e) => f.mudar({ time: e.target.value })} className={cn(CAMPO, 'w-36')} />
            </Linha>
            {/* 🔴 SPEC-078 D.6 — caixa de texto vira seletor: decorar "0=seg" é um detalhe nosso. */}
            <Linha rotulo="Dias da semana">
              <div className="flex flex-wrap gap-1.5" role="group" aria-label="Dias da semana">
                {DIAS_DA_SEMANA.map((d) => {
                  const ativo = marcados.includes(String(d.valor));
                  return (
                    <button key={d.valor} type="button" title={d.longo} aria-label={d.longo} aria-pressed={ativo}
                      disabled={desabilitado} onClick={() => f.alternarDia(d.valor)}
                      className={cn(
                        'h-11 min-w-[44px] rounded-lg border px-2.5 text-sm font-medium transition-colors sm:h-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        ativo ? 'border-primary bg-brand-soft text-foreground' : 'border-border text-muted-foreground hover:bg-surface-2',
                      )}>
                      {d.curto}
                    </button>
                  );
                })}
              </div>
              <Ajudinha>
                {form.weekdays.trim()
                  ? 'Roda só nos dias marcados.'
                  : 'Nenhum dia marcado: vai rodar TODOS os dias, inclusive sábado e domingo.'}
              </Ajudinha>
            </Linha>
          </>
        ) : (
          <Linha rotulo="Intervalo" htmlFor={id('intervalo')} info="De quantos em quantos minutos ela roda. O mínimo é 5.">
            <div className="flex items-center gap-2">
              <input id={id('intervalo')} type="number" min={5} value={form.minutes} disabled={desabilitado}
                onChange={(e) => f.mudar({ minutes: parseInt(e.target.value || '5', 10) })} className={cn(CAMPO, 'w-28')} />
              <span className="text-sm text-muted-foreground">minutos</span>
            </div>
          </Linha>
        )}
      </Grupo>

      <Grupo id={id('relatorio')} titulo={billingConfig ? 'O relatório' : 'Entrega'}
        descricao={billingConfig ? 'Quem recebe o resumo de cada execução.' : 'Para onde vai o resultado de cada execução.'}>
        <Linha rotulo={billingConfig ? 'Relatório de cada execução' : 'Entrega'}>
          <Segmentado<'whatsapp' | 'none'> rotulo={billingConfig ? 'Relatório de cada execução' : 'Entrega'} desabilitado={desabilitado}
            valor={form.channel === 'whatsapp' ? 'whatsapp' : 'none'}
            opcoes={[{ valor: 'whatsapp', titulo: 'WhatsApp' }, { valor: 'none', titulo: 'Só histórico' }]}
            onChange={(c) => f.mudar({ channel: c })} />
        </Linha>
        {form.channel === 'whatsapp' && (
          <Linha rotulo={billingConfig ? 'Número que recebe o relatório' : 'Número'} htmlFor={id('numero')}
            info="Com DDI e DDD: 55, o DDD e o número.">
            <input id={id('numero')} value={form.number} disabled={desabilitado} inputMode="tel"
              onChange={(e) => f.mudar({ number: e.target.value })} placeholder="55 47 9XXXX-XXXX" className={CAMPO} />
          </Linha>
        )}
      </Grupo>

      {(billingConfig || avancadoExtra) && (
        <Collapsible open={avancado} onOpenChange={setAvancado} className="space-y-3">
          <CollapsibleTrigger
            className="flex min-h-[44px] w-full items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <span>
              <span className="block text-base font-semibold text-foreground">Avançado</span>
              <span className="block text-sm text-muted-foreground">
                {billingConfig ? 'Quantos boletos por vez e o intervalo entre cobranças da mesma pessoa.' : 'O que mais dá para fazer aqui.'}
              </span>
            </span>
            <ChevronDown size={18} strokeWidth={1.6} aria-hidden
              className={cn('shrink-0 text-muted-foreground transition-transform', avancado && 'rotate-180')} />
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-8">
            {billingConfig && (
              <Grupo id={id('limites')} titulo="Limites">
                <Linha rotulo="Máximo de boletos por execução" htmlFor={id('max')}
                  info="Para o primeiro teste, 1 ou 2. Quem não couber hoje volta amanhã de onde parou.">
                  {/* 🔴 conserto A da 139 (red team B3): o que se DIGITA grava o MESMO número que o modal de antes
                      (`parseInt(v || '10')`); os botões − / + ficam na faixa. */}
                  <NumeroComBotoes id={id('max')} rotulo="boletos por execução" valor={billingMaxBoletos} min={1} max={50}
                    sufixo="boletos" desabilitado={desabilitado} lerDigitado={(t) => numeroDigitadoNoModal(t, '10')}
                    onChange={(n) => f.setBillingConfig({ max_boletos_por_execucao: n })} />
                </Linha>
                <Linha rotulo="Dias entre cobranças do mesmo segurado" htmlFor={id('dias')}
                  info="A mesma pessoa não é cobrada de novo antes disso — nem por outra seguradora. Quem ficar de fora aparece no relatório, com a data em que volta.">
                  <NumeroComBotoes id={id('dias')} rotulo="dias entre cobranças" valor={billingDiasEntreCobrancas} min={1} max={30}
                    sufixo="dias" desabilitado={desabilitado} lerDigitado={(t) => numeroDigitadoNoModal(t, '7')}
                    onChange={(n) => f.setBillingConfig({ dias_entre_cobrancas_do_mesmo_segurado: n })} />
                </Linha>
              </Grupo>
            )}
            {avancadoExtra}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

export default FormularioDaRotina;
