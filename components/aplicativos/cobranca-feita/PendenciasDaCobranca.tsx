'use client';

// SPEC-139 · L2 — a FILA da cobrança real (SPEC-EXTRA-001 §6), MOVIDA do `PainelDeRotinas` sem mudar uma regra: as
// mesmas rotas (`pendencias`, `encaminhado`, `liberar`), os mesmos estados, o mesmo motivo obrigatório. Ela mora
// agora em dois lugares que a importam — o painel de rotinas e a aba Cobranças da Cobrança ("Precisa de você") — e
// por isso virou componente: com a Cobrança fora do painel, a fila não podia ficar para trás.
//
// Sem esta lista, `entregue_equipe` (a atendente recebeu, o cliente ainda não) e `parcial` (o texto foi, o PDF não)
// ficariam pendurados no banco sem ninguém para vê-los: o relatório da rotina é uma foto do dia, não uma fila.

import { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { Selo, type TomDoSelo } from '@/components/aplicativos/casca/Selo';
import { cn } from '@/lib/utils';

/**
 * Uma parcela da cobrança REAL que ainda espera alguém. Os campos são exatamente os que a rota `pendencias` devolve.
 * Note o que NÃO está aqui: telefone. Só `to_last4` (CLAUDE.md §7).
 */
interface PendenciaDaCobranca {
  id: string;
  status: string;
  modalidade: string | null;
  portal_key: string | null;
  recibo: string | null;
  cliente_nome: string | null;
  apolice_susep: string | null;
  to_last4: string | null;
  sent_at: string | null;
  updated_at: string | null;
  retorno_do_cliente: string | null;
  retorno_em: string | null;
  encaminhado_ao_cliente_em: string | null;
  motivo: string | null;
}

/**
 * O nome que a corretora lê no lugar da chave do portal. 📊 Cópia de `NOME_DA_SEGURADORA` (`billing_collection.py`),
 * com o mesmo fallback: portal novo sem entrada vira o prefixo em maiúsculas (`sancor_corretor` → "SANCOR") —
 * nunca a palavra genérica "seguradora", que parece defeito para quem lê.
 */
export const NOME_DA_SEGURADORA: Record<string, string> = {
  allianz_corretor: 'ALLIANZ',
  hdi_corretor: 'HDI SEGUROS',
  porto_corretor: 'PORTO SEGURO',
  yelum_corretor: 'YELUM',
  tokiomarine_corretor: 'TOKIO MARINE',
  bradesco_corretor: 'BRADESCO SEGUROS',
  mapfre_corretor: 'MAPFRE',
  azul_corretor: 'AZUL SEGUROS',
  alfa_corretor: 'ALFA SEGURADORA',
  sulamerica_corretor: 'SULAMERICA',
  sompo_corretor: 'SOMPO SEGUROS',
  suhai_corretor: 'SUHAI',
  sura_corretor: 'SURA',
  zurich_corretor: 'ZURICH',
  segurosunimed_corretor: 'SEGUROS UNIMED',
};

export function nomeDaSeguradora(portalKey: string): string {
  const chave = String(portalKey || '').trim().toLowerCase();
  if (!chave) return 'seguradora não identificada';
  if (NOME_DA_SEGURADORA[chave]) return NOME_DA_SEGURADORA[chave];
  if (chave.endsWith('_corretor')) return chave.slice(0, -'_corretor'.length).replace(/_/g, ' ').toUpperCase();
  return chave.toUpperCase();
}

/**
 * O que a corretora vê no lugar do estado do ledger — SPEC-EXTRA-001 §2. `parcial` diz "o texto foi e o PDF não";
 * `incerto` diz "não sei se saiu". A diferença decide se alguém reenvia ou confere antes — e chega ao segurado.
 */
const RETORNO_DO_CLIENTE: Record<string, string> = {
  ja_paguei: 'já paguei',
  nao_sou: 'não sou essa pessoa',
  nao_quero: 'não quer receber',
  segunda_via: 'pediu segunda via',
  duvida: 'ficou com dúvida',
  outro: 'respondeu algo fora do previsto',
};

const SITUACAO_HUMANA: Record<string, string> = {
  entregue_equipe: 'Entregue à equipe — falta encaminhar ao cliente',
  parcial: 'Texto foi, PDF não',
  incerto: 'Não sei se saiu — precisa de conferência',
  suprimido: 'Cliente pediu para não receber',
  falhou: 'Não saiu',
  adiado: 'Adiado — tenta na próxima execução',
  liberado: 'Liberada — sai na próxima execução da rotina, pela modalidade configurada',
};

function situacaoEmPortugues(item: PendenciaDaCobranca): string {
  if (item.status === 'contestado') {
    const retorno = RETORNO_DO_CLIENTE[String(item.retorno_do_cliente || '')] || 'respondeu';
    return `Cliente respondeu: ${retorno}`;
  }
  return SITUACAO_HUMANA[item.status] || item.status;
}

/**
 * Estados de onde NÃO se libera reenvio, e o porquê ao lado. ⛔ `suprimido` é terminal: o cliente pediu para não
 * receber. A rota responde 409 de qualquer jeito — desabilitar aqui é para a pessoa ler o motivo em vez de um erro.
 */
const NAO_LIBERA: Record<string, string> = {
  suprimido: 'O cliente pediu para não receber. Essa decisão é dele.',
  incerto: 'Confira antes: liberar sem saber se saiu pode cobrar o cliente duas vezes.',
  liberado: 'Já liberada — sai na próxima execução da rotina.',
};

function fmt(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function tomDaPendencia(status: string): TomDoSelo {
  if (status === 'entregue_equipe') return 'warning';
  if (status === 'suprimido' || status === 'falhou') return 'danger';
  return 'neutral';
}

const BOTAO =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-sm text-foreground transition-colors hover:bg-surface-2 disabled:opacity-50 sm:min-h-[36px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export function PendenciasDaCobranca({ titulo = 'Pendências da cobrança', className }: { titulo?: string; className?: string }) {
  // `null` = ainda carregando; `[]` = carregou e não há nada.
  const [pendencias, setPendencias] = useState<PendenciaDaCobranca[] | null>(null);
  const [erroPendencias, setErroPendencias] = useState('');
  const [agindoNaPendencia, setAgindoNaPendencia] = useState<string>('');
  const [motivoDaLiberacao, setMotivoDaLiberacao] = useState<Record<string, string>>({});

  const carregarPendencias = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/auxiliaries/cobranca/pendencias', { cache: 'no-store' });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || !j?.ok) {
        // Dizer "não consegui carregar" é diferente de mostrar lista vazia: uma fila vazia por engano é uma fila
        // que ninguém trabalha.
        setErroPendencias(j?.error || 'Não consegui carregar as pendências.');
        setPendencias([]);
        return;
      }
      setErroPendencias('');
      setPendencias((j.itens || []) as PendenciaDaCobranca[]);
    } catch {
      setErroPendencias('Não consegui carregar as pendências.');
      setPendencias([]);
    }
  }, []);

  useEffect(() => { carregarPendencias(); }, [carregarPendencias]);

  /**
   * As duas decisões humanas da fila. Elas não enviam nada: `encaminhado` carimba quem repassou e quando; `liberar`
   * devolve a parcela ao estado que a próxima execução pode reclamar, e por isso exige motivo escrito.
   */
  const decidirPendencia = async (item: PendenciaDaCobranca, acao: 'encaminhado' | 'liberar') => {
    const motivo = (motivoDaLiberacao[item.id] || '').trim();
    if (acao === 'liberar' && !motivo) {
      setErroPendencias('Escreva o motivo da liberação — ele fica registrado junto com a parcela.');
      return;
    }
    if (acao === 'liberar' && !confirm(
      'Liberar esta parcela para ser cobrada de novo?\n\n'
      + 'A próxima execução da rotina vai tentar entregá-la outra vez.',
    )) return;
    setAgindoNaPendencia(item.id);
    setErroPendencias('');
    try {
      const res = await fetch(`/api/dashboard/auxiliaries/cobranca/${acao}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: item.id, ...(motivo ? { motivo } : {}) }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || !j?.ok) {
        setErroPendencias(j?.error || 'Não foi possível concluir a ação.');
      } else {
        setMotivoDaLiberacao((m) => ({ ...m, [item.id]: '' }));
      }
    } catch {
      setErroPendencias('Falha de conexão.');
    }
    setAgindoNaPendencia('');
    carregarPendencias();
  };

  return (
    <div className={cn('rounded-xl border border-border bg-surface p-4', className)} data-pendencias-da-cobranca>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-base font-semibold text-foreground">{titulo}</h2>
        <p className="text-sm text-muted-foreground">O que já saiu e ainda espera alguém. Envios em teste não aparecem aqui.</p>
      </div>

      {erroPendencias && (
        <p className="mt-3 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-foreground" role="alert">
          {erroPendencias}
        </p>
      )}

      {pendencias === null ? (
        <p className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Carregando pendências…
        </p>
      ) : pendencias.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">Nenhuma pendência. Tudo que saiu já foi resolvido.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {pendencias.map((p) => {
            const bloqueio = NAO_LIBERA[p.status];
            const ocupado = agindoNaPendencia === p.id;
            return (
              <li key={p.id} className="rounded-lg border border-border-soft bg-background p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">{p.cliente_nome || 'Cliente sem nome no portal'}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {nomeDaSeguradora(String(p.portal_key || ''))}
                      {p.recibo ? ` · parcela/recibo ${p.recibo}` : ''}
                      {/* ⛔ O telefone NUNCA aparece inteiro — só os últimos 4 dígitos (CLAUDE.md §7). */}
                      {p.to_last4 ? ` · para …${p.to_last4}` : ''}
                      {' · '}{fmt(p.sent_at || p.updated_at)}
                    </p>
                  </div>
                  <Selo tom={tomDaPendencia(p.status)} rotulo={situacaoEmPortugues(p)} className="whitespace-normal text-left leading-5" />
                </div>

                {p.motivo && <p className="mt-1.5 text-sm text-muted-foreground">Observação: {p.motivo}</p>}

                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {p.status === 'entregue_equipe' && (
                    <button type="button" onClick={() => decidirPendencia(p, 'encaminhado')} disabled={ocupado} className={BOTAO}>
                      {ocupado && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
                      Marcar como encaminhado ao cliente
                    </button>
                  )}
                  <input
                    value={motivoDaLiberacao[p.id] || ''}
                    onChange={(e) => setMotivoDaLiberacao((m) => ({ ...m, [p.id]: e.target.value }))}
                    disabled={!!bloqueio || ocupado}
                    aria-label="Motivo da liberação"
                    placeholder="Motivo da liberação"
                    className="h-11 min-w-[10rem] flex-1 rounded-lg border border-border bg-surface px-3 text-sm text-foreground disabled:opacity-50 sm:h-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  <button type="button" onClick={() => decidirPendencia(p, 'liberar')}
                    disabled={!!bloqueio || ocupado || !(motivoDaLiberacao[p.id] || '').trim()} className={BOTAO}>
                    {ocupado && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
                    Liberar reenvio
                  </button>
                  {/* O porquê fica AO LADO do botão desabilitado: um controle apagado sem explicação é tentado de novo. */}
                  {bloqueio && <span className="text-sm text-muted-foreground">{bloqueio}</span>}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default PendenciasDaCobranca;
