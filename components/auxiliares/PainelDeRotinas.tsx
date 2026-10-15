'use client';

// F2 — Rotinas agendadas da corretora: lista, pausa/ativa, exclui e mostra as
// últimas execuções. Criação acontece pelo Chat Principal ("todo dia às 8h...").
//
// 🔴 SPEC-139 · L2 (D-139-04) — o FORMULÁRIO do modal foi EXTRAÍDO para
// `components/aplicativos/cobranca-feita/` (`formulario.ts` puro, `useFormularioDaRotina`, `FormularioDaRotina`), e a
// aba Configurar da Cobrança usa o MESMO. Aqui ficou o painel: a lista, as ações da lista e o modal que desenha o
// formulário extraído. A fila de pendências e o reenvio de teste também viraram peças (a aba Cobranças os usa) e
// continuam aqui, iguais. O teste dourado `scripts/a-cobranca-na-casca.test.mjs` prova que o corpo gravado é o mesmo
// de antes da extração.

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Pause, Pencil, Play, Plus, Trash2 } from 'lucide-react';

import { StatusPill } from '@/components/patterns/StatusPill';
import { FormularioDaRotina } from '@/components/aplicativos/cobranca-feita/FormularioDaRotina';
import { LiberarReenvioDeTeste } from '@/components/aplicativos/cobranca-feita/LiberarReenvioDeTeste';
import { PendenciasDaCobranca } from '@/components/aplicativos/cobranca-feita/PendenciasDaCobranca';
import {
  BILLING_KIND,
  ROTA_DAS_ROTINAS,
  ROTINA_DO_AUXILIAR,
  corpoDaAcao,
  rotuloDaAgenda,
  salvarTravado,
  type Routine,
  type Run,
} from '@/components/aplicativos/cobranca-feita/formulario';
import { useFormularioDaRotina } from '@/components/aplicativos/cobranca-feita/useFormularioDaRotina';

function fmt(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

/**
 * SPEC-078 C.4 — este painel MUDOU DE CASA.
 *
 * Ele era `app/dashboard/auxiliares/rotinas/page.tsx`, uma página autônoma com
 * botão "Nova rotina", listando as rotinas de TODA a corretora.
 *
 * 📊 O achado que motivou a mudança: a SPEC-064 §B.3 mandou absorver QUATRO
 * rotas. Três viraram stub de redirect com a frase "O CONTEUDO FOI ABSORVIDO"
 * (`galeria`, `meus`, `execucoes`). Esta é a quarta, e a única que não foi.
 *
 * E o preço apareceu: `ONTOLOGIA-DO-TRABALHO.md:51` diz "Rotina nunca existe
 * sozinha", mas o botão "Nova rotina" numa lista sem dono criava exatamente
 * isso — a rotina órfã de 17/08 às 13:01 saiu dele.
 *
 * Agora o painel vive DENTRO da tela do Auxiliar, mostra só as rotinas DELE, e
 * a criação sempre sabe de quem é. O possessivo do título ("Rotinas deste
 * Auxiliar") faz o trabalho que o cânone pede: diz que é Rotina e diz de quem.
 */
export default function PainelDeRotinas({
  auxiliarSlug,
  auxiliarNome,
  auxiliarLigado,
}: {
  auxiliarSlug: string;
  auxiliarNome: string;
  /** `tenant_auxiliaries.status === 'active'`. Ver o aviso em D.9. */
  auxiliarLigado: boolean;
}) {
  const [routines, setRoutines] = useState<Routine[] | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [notice, setNotice] = useState('');
  // SPEC-078 D.5 — separado do `notice` da lista, porque o `notice` é
  // renderizado ATRÁS do overlay do modal e o corretor não o vê.
  const [erroDoModal, setErroDoModal] = useState('');
  const ehAuxiliarDeCobranca = ROTINA_DO_AUXILIAR[auxiliarSlug] === BILLING_KIND;

  // SPEC-019 B — o modal de criação/edição manual. O estado e a gravação são do formulário EXTRAÍDO (SPEC-139).
  const f = useFormularioDaRotina({ auxiliarSlug, auxiliarNome });

  const load = useCallback(async () => {
    try {
      // O `?auxiliar=` vai para a API, que filtra pelo dono. Filtrar aqui no
      // navegador funcionaria e seria pior: a corretora baixaria a lista das
      // rotinas de todos os Auxiliares para mostrar as de um.
      const res = await fetch(`/api/dashboard/rotinas?auxiliar=${encodeURIComponent(auxiliarSlug)}`,
        { cache: 'no-store' });
      const j = await res.json();
      if (!res.ok) {
        setNotice(j.error || 'Erro ao carregar rotinas.');
        setRoutines([]);
        return;
      }
      setRoutines(j.routines || []);
      setRuns(j.runs || []);
    } catch {
      setNotice('Falha de conexão.');
      setRoutines([]);
    }
  }, [auxiliarSlug]);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  /** Abre o modal: "Nova rotina" NASCE PREENCHIDA pelo modelo do Auxiliar (SPEC-078 D); editar abre como está gravada. */
  const openEditor = async (r: Routine | 'new') => {
    setErroDoModal('');
    await f.abrir(r);
  };

  const saveRoutine = async () => {
    setNotice('');
    const r = await f.salvar();
    if (!r.ok) {
      // 🔴 SPEC-078 D.5 — o erro vai para DENTRO do modal (o `notice` fica atrás do overlay). `details[0]` carrega a
      // mensagem crua do banco quando o erro não tem texto próprio — descartá-la é o defeito do `install_failed`.
      setErroDoModal(r.erro || 'Erro ao salvar rotina.');
      return;
    }
    f.fechar();
    setErroDoModal('');
    load();
  };

  const act = async (id: string, action: 'pause' | 'activate' | 'delete') => {
    if (action === 'delete' && !confirm('Excluir esta rotina? O histórico de execuções também será removido.')) return;
    setNotice('');
    const res = await fetch(ROTA_DAS_ROTINAS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpoDaAcao(id, action)),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setNotice(j.error || 'Não foi possível concluir a ação.');
    }
    load();
  };

  return (
    <div>
      <div className="space-y-4">
        {/* 🔴 SPEC-078 A.3 — o aviso que fecha o buraco que o Founder viu.
            Rotina ativa com Auxiliar desligado NÃO roda mais (o motor consulta
            `tenant_auxiliaries.status`). Antes disso rodava, e a tela não dizia
            nada — ele criou a rotina, desligou o Auxiliar e a varredura de
            portal aconteceria mesmo assim. Dizer isso aqui é o que impede o
            corretor de achar que configurou e esperar sentado. */}
        {!auxiliarLigado && (routines?.length ?? 0) > 0 && (
          <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
            Este Auxiliar está <strong>desligado</strong>. Enquanto estiver, nenhuma
            rotina dele roda — nem as que aparecem como ativas abaixo. Ligue o Auxiliar
            para que ele volte a trabalhar.
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          {notice ? <p className="text-sm text-danger">{notice}</p> : <span />}
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {/* 🔴 SPEC-078 E.4 — a dedup é PERMANENTE e não tinha desfazer.
                O botão limpa APENAS `send_mode='test'`. Nunca `live`. */}
            {ehAuxiliarDeCobranca && <LiberarReenvioDeTeste onAviso={setNotice} />}
            <button
              onClick={() => openEditor('new')}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              <Plus className="h-4 w-4" /> Nova rotina deste Auxiliar
            </button>
          </div>
        </div>

        {routines === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando rotinas…
          </div>
        ) : routines.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">Nenhuma rotina ainda</p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              Abra o chat AutoBrokers e peça, por exemplo: &quot;Crie uma rotina que todo dia às 8h
              me mande no WhatsApp um resumo das notícias de seguros&quot;. Ela aparece aqui.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {routines.map((r) => {
              const rRuns = runs.filter((x) => x.routine_id === r.id).slice(0, 3);
              return (
                <div key={r.id} className="rounded-xl border border-border bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">{r.name}</p>
                        <StatusPill
                          tone={r.is_active ? 'success' : 'neutral'}
                          label={r.is_active ? 'ativa' : 'pausada'}
                        />
                        {r.consecutive_failures >= 5 && (
                          <StatusPill tone="danger" label="desativada por falhas" />
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {rotuloDaAgenda(r.schedule)} · entrega: {r.delivery?.channel || 'histórico'}
                        {r.delivery?.number ? ` (${r.delivery.number})` : ''} · próxima: {fmt(r.next_run_at)} · última: {fmt(r.last_run_at)}
                      </p>
                      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{r.instructions}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <button
                        onClick={() => openEditor(r)}
                        className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                        title="Editar rotina"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      {r.is_active ? (
                        <button
                          onClick={() => act(r.id, 'pause')}
                          className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                          title="Pausar rotina"
                        >
                          <Pause className="h-3.5 w-3.5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => act(r.id, 'activate')}
                          className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-foreground"
                          title="Reativar rotina"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => act(r.id, 'delete')}
                        className="rounded-md border border-border bg-surface-2 p-2 text-muted-foreground transition-colors hover:text-danger"
                        title="Excluir rotina"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {rRuns.length > 0 && (
                    <div className="mt-3 space-y-1 border-t border-border pt-2">
                      {rRuns.map((run) => (
                        <p key={run.id} className="truncate text-[11px] text-muted-foreground">
                          <span className={run.status === 'ok' ? 'text-success' : run.status === 'error' ? 'text-danger' : ''}>
                            {run.status === 'ok' ? '✓' : run.status === 'error' ? '✗' : '…'}
                          </span>{' '}
                          {fmt(run.started_at)} · {run.error || run.output_preview || 'executando…'}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 🔴 SPEC-EXTRA-001 §6 — PENDÊNCIAS DA COBRANÇA: a fila do que a cobrança real deixou esperando decisão de
            gente. Fora do modal de propósito (o modal configura; isto é trabalho do dia). Só no Auxiliar de Cobrança —
            em qualquer outro não existe ledger para ler. SPEC-139: a mesma peça mora na aba Cobranças. */}
        {ehAuxiliarDeCobranca && <PendenciasDaCobranca />}

        {f.editing !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !f.saving && f.fechar()}>
            <div
              className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-border bg-background p-5"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-label={f.editing === 'new' ? `Nova rotina · ${auxiliarNome}` : `Editar rotina · ${auxiliarNome}`}
            >
              <h2 className="text-base font-semibold text-foreground">
                {f.editing === 'new' ? `Nova rotina · ${auxiliarNome}` : `Editar rotina · ${auxiliarNome}`}
              </h2>

              {/* 🔴 SPEC-078 D.5 — o erro mora DENTRO do modal. */}
              {erroDoModal && (
                <p className="mt-3 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
                  {erroDoModal}
                </p>
              )}

              <div className="mt-4">
                <FormularioDaRotina f={f} auxiliarNome={auxiliarNome} prefixo="modal" />
              </div>

              {f.motivo && <p className="mt-4 text-sm text-muted-foreground" role="status">{f.motivo}</p>}
              <div className="mt-5 flex justify-end gap-2">
                <button
                  onClick={() => { f.fechar(); setErroDoModal(''); }}
                  disabled={f.saving}
                  className="rounded-md border border-border bg-surface-2 px-4 py-2 text-sm text-foreground"
                >
                  Cancelar
                </button>
                <button
                  onClick={saveRoutine}
                  // 🔴 SPEC-078 D.5 — o botão exige o que o servidor exige (as condições moram em
                  // `motivoParaNaoSalvar`, as MESMAS do modal de antes — o teste dourado compara passo a passo).
                  disabled={salvarTravado(f.form, f.saving, f.portais)}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                >
                  {f.saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {f.editing === 'new' ? 'Criar rotina' : 'Salvar alterações'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
