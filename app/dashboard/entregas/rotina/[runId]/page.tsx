// SPEC-078 F.4 — a execução de rotina ganha página, e o relatório vai INTEIRO.
//
// 📊 17/08/2026, medido antes de escrever esta pasta (projeto dcajcvlzcjbmyapmklil):
//
//     routine_runs                       32 linhas
//     com output_preview                 32 de 32
//     com EXATAMENTE 500 caracteres      29   ← o teto, ou seja: truncadas
//     média de caracteres guardados      489
//     tamanho real do relatório          até 4000  (`_format_report` corta aí)
//
// `routine_engine.py:257` fazia `output_preview = output[:500]` e jogava fora o
// resto no ato. 87% de um relatório cheio. E não era 87% qualquer: a seção
// "PRECISA DE VOCE" — as parcelas em atraso SEM boleto, que só uma pessoa
// resolve — e a lista "Clientes encontrados" começam depois do caractere 500
// em toda execução com inadimplente. O produto varria o portal da seguradora,
// baixava boleto, montava fila, escrevia a lista de quem precisa de atendimento
// humano, e guardava o cabeçalho.
//
// Agora `routine_runs.output_full` guarda o texto completo (migration
// 20260817_04) e esta página o mostra.
//
// 🔴 DADO DE SEGURADO EM TEXTO CLARO (CLAUDE.md §7).
//
// O relatório contém CPF/CNPJ e telefone (`billing_collection.py:1069-1140`).
// A proteção é o `.eq('company_id', empresa)` em TODA consulta desta página —
// o backend usa service role e a chave de serviço atravessa policy, então RLS
// sozinha não protege nada contra um filtro esquecido. Execução de outra
// corretora cai em `notFound()`, nunca em conteúdo.
//
// E o que esta página NÃO faz, de propósito: não manda o texto para log, não
// indexa em RAG/Qdrant, não gera link público. O Artifact da cobrança (F.5)
// existe para ser compartilhável — e é justamente por isso que ELE sai sem
// CPF, e o texto integral fica aqui, atrás da sessão.
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { ondeAbrirAuxiliar } from '@/lib/auxiliaries/catalog';
import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Execução · AutoBrokers' };

/** Só uuid entra no banco. Recusar antes evita transformar a rota em sonda. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** O estado da execução em português, com o tom que a tela usa para colorir. */
function estadoDaExecucao(status: string | null): { rotulo: string; tom: string } {
  switch (status) {
    case 'ok':
      return { rotulo: 'Concluída', tom: 'text-emerald-600 dark:text-emerald-400' };
    case 'error':
      return { rotulo: 'Falhou', tom: 'text-red-600 dark:text-red-400' };
    case 'running':
      return { rotulo: 'Em andamento', tom: 'text-amber-600 dark:text-amber-400' };
    case 'delegated':
      return { rotulo: 'Delegada ao motor de trabalhos', tom: 'text-muted-foreground' };
    default:
      return { rotulo: status || 'Desconhecido', tom: 'text-muted-foreground' };
  }
}

function dataLonga(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  });
}

/** Quanto tempo a execução levou. Só aparece quando as duas pontas existem. */
function duracao(inicio: string | null, fim: string | null): string | null {
  if (!inicio || !fim) return null;
  const ms = new Date(fim).getTime() - new Date(inicio).getTime();
  if (!Number.isFinite(ms) || ms < 0) return null;
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
  return `${Math.floor(ms / 60_000)}min ${Math.round((ms % 60_000) / 1000)}s`;
}

export default async function ExecucaoDeRotinaPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  if (!UUID.test(runId)) notFound();

  const auth = await requireCompanyMember({ write: false });
  // Sem sessão o middleware já teria mandado para /login. Chegar aqui sem
  // vínculo válido é o caso "usuário da corretora A com link da corretora B":
  // a resposta é a mesma de execução inexistente.
  if (!auth.ok) notFound();

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  const { data: execucao } = await supabase
    .from('routine_runs')
    // Numa linha só de propósito: o supabase-js LÊ esta string em tempo de
    // tipo. Concatenada, ele desiste e todo campo abaixo perde o tipo.
    .select('id, routine_id, status, output_preview, output_full, error, started_at, finished_at')
    .eq('id', runId)
    .eq('company_id', empresa) // 🔴 CLAUDE.md §7 — o filtro, não a policy, é o que protege
    .maybeSingle();

  if (!execucao) notFound();

  const { data: rotina } = await supabase
    .from('routines')
    .select('id, name, tenant_auxiliary_id, is_active')
    .eq('id', execucao.routine_id)
    .eq('company_id', empresa)
    .maybeSingle();

  const { data: auxiliar } = rotina?.tenant_auxiliary_id
    ? await supabase
        .from('tenant_auxiliaries')
        .select('id, name, slug')
        .eq('id', rotina.tenant_auxiliary_id)
        .eq('company_id', empresa)
        .maybeSingle()
    : { data: null };

  const estado = estadoDaExecucao(execucao.status);
  const tempo = duracao(execucao.started_at, execucao.finished_at);
  const hrefDono = ondeAbrirAuxiliar(auxiliar?.slug);
  const nomeDono = auxiliar?.name ?? auxiliar?.slug ?? null;

  // O texto integral quando ele existe; senão o preview, com o aviso de que é
  // preview. 📊 As 32 execuções gravadas antes da migration 20260817_04 não têm
  // `output_full` e NÃO foram backfilladas: copiar 500 caracteres truncados
  // para a coluna do texto completo apresentaria o corte como se fosse o
  // relatório. A lacuna é dita, não disfarçada.
  const completo = typeof execucao.output_full === 'string' ? execucao.output_full : '';
  const relatorio = completo || execucao.output_preview || '';
  const ehSoPreview = !completo && Boolean(execucao.output_preview);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.auxiliares}
          title={nomeDono ? `${nomeDono} rodou` : `${rotina?.name ?? 'Rotina'} rodou`}
          subtitle={rotina?.name ?? undefined}
          breadcrumb={[
            { label: 'Entregas', href: '/dashboard/entregas' },
            { label: 'Execução' },
          ]}
        />

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className={estado.tom}>{estado.rotulo}</span>
          <span>{dataLonga(execucao.finished_at || execucao.started_at)}</span>
          {tempo && <span>levou {tempo}</span>}
          {nomeDono && hrefDono && (
            <span>
              Produzido por{' '}
              <Link href={hrefDono} className="text-primary underline">
                {nomeDono}
              </Link>
            </span>
          )}
        </div>

        {/* O erro vem ANTES do relatório. Quem abre uma execução que falhou
            quer o motivo, não o cabeçalho do que deu certo antes de falhar. */}
        {execucao.error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3">
            <p className="text-xs font-medium text-red-600 dark:text-red-400">
              O que impediu a execução
            </p>
            <p className="mt-1 whitespace-pre-wrap break-words text-sm text-foreground">
              {execucao.error}
            </p>
          </div>
        )}

        {relatorio ? (
          <div className="space-y-2">
            {ehSoPreview && (
              <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
                Esta execução é anterior ao registro do relatório completo — o
                que está guardado são os primeiros 500 caracteres. As execuções
                a partir de agora guardam o texto inteiro.
              </div>
            )}
            {/* `whitespace-pre-wrap` e fonte monoespaçada porque o relatório é
                TEXTO alinhado por linha, montado em `_format_report`. Renderizar
                como parágrafo juntaria "PRECISA DE VOCE" com a lista embaixo. */}
            <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-xl border border-border bg-surface p-5 font-mono text-xs leading-relaxed text-foreground">
              {relatorio}
            </pre>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">
              Esta execução não deixou relatório
            </p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              O registro existe e o estado é {estado.rotulo.toLowerCase()}, mas
              nenhum texto foi gravado.
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <Link href="/dashboard/entregas" className="text-muted-foreground hover:text-foreground">
            Voltar para Entregas
          </Link>
          {hrefDono && nomeDono && (
            <Link href={hrefDono} className="text-primary hover:underline">
              Ver o {nomeDono}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
