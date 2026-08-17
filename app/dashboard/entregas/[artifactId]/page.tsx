// SPEC-078 Bloco F.1 — a tela que faltava: o Artifact que o corretor ABRE.
//
// 📊 17/08/2026, medido antes de escrever esta pasta:
//
//     find app -type d -iname "*artifact*"        → ZERO
//     artifacts                                    36 linhas, todas kind='report',
//                                                  status='ready'
//     artifact_renders                             36 de 36, format='html',
//                                                  status='ready', inline_content
//                                                  presente, storage_ref em nenhuma,
//                                                  entre 22.709 e 24.666 bytes
//
// Ou seja: o produto renderizava 36 relatórios completos e não tinha uma única
// rota para mostrá-los. A rota de Entregas os listava com `href: null` e o
// comentário "ainda não há rota de tenant". Esta é a rota de tenant. É a queixa
// literal do Founder — "não consigo acessar as coisas que ficam prontas".
//
// 🔴 MULTI-TENANT (CLAUDE.md §7). O backend usa service role: RLS sozinho NÃO
// protege, porque a chave de serviço atravessa policy. A proteção real é o
// `.eq('company_id', empresa)` em TODA consulta desta página — inclusive nas
// tabelas filhas, que têm `company_id` próprio justamente para isso. Um
// artifact de outra corretora cai em `notFound()`, nunca em conteúdo.
//
// Por que o conteúdo vai num iframe e não direto no JSX: o render do Artifact
// Hub é um documento HTML COMPLETO, com <head>, variáveis de marca da corretora
// e CSS de impressão (é o mesmo arquivo que a rota pública `/r/[token]` serve
// cru, e pela mesma razão). Injetá-lo no meio do dashboard aninharia dois
// documentos: o CSS de impressão pararia de valer e a marca da corretora
// competiria com a do produto.
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { ondeAbrirAuxiliar } from '@/lib/auxiliaries/catalog';
import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Documento · AutoBrokers' };

/** Só uuid entra no banco. Recusar antes evita transformar a rota em sonda. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * O Auxiliar que produziu o documento.
 *
 * 📊 17/08/2026: os 36 artifacts têm `template_key` `briefing.daily_operational`
 * (30) ou `briefing.weekly_executive` (6), e os 36 estão referenciados em
 * `briefing_publications.artifact_id`. Os dois caminhos apontam para o mesmo
 * Auxiliar — o mapa existe para que o próximo produtor seja UMA LINHA aqui.
 *
 * `artifacts` não tem coluna de dono; inventar uma seria migration numa SPEC de
 * funcionalidade. Derivar do `template_key` é honesto: quem escolhe o template
 * é quem produz.
 */
const AUXILIAR_DO_TEMPLATE: Record<string, string> = {
  'briefing.daily_operational': 'checklist-6h',
  'briefing.weekly_executive': 'checklist-6h',
};

const NOME_DO_AUXILIAR: Record<string, string> = {
  'checklist-6h': 'Checklist das 6h',
};

/** O tipo do documento em português. `kind` é a palavra do banco, não do corretor. */
function tipoEmPortugues(kind: string | null): string {
  switch (kind) {
    case 'report':
      return 'Relatório';
    case 'proposal':
      return 'Proposta';
    case 'letter':
      return 'Carta';
    case 'dashboard':
      return 'Painel';
    default:
      return kind || 'Documento';
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

export default async function ArtifactPage({
  params,
}: {
  params: Promise<{ artifactId: string }>;
}) {
  const { artifactId } = await params;
  if (!UUID.test(artifactId)) notFound();

  const auth = await requireCompanyMember({ write: false });
  // Sem sessão o middleware já teria mandado para /login. Chegar aqui sem
  // vínculo válido é o caso "usuário da corretora A com link da corretora B":
  // a resposta é a mesma de documento inexistente.
  if (!auth.ok) notFound();

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  const { data: artifact } = await supabase
    .from('artifacts')
    // Numa linha só de propósito: o supabase-js LÊ esta string em tempo de
    // tipo. Concatenada, ele desiste e o resultado vira `GenericStringError` —
    // e todo campo abaixo perde o tipo.
    .select('id, kind, title, subtitle, summary, template_key, origin, status, current_version, created_at, updated_at, archived_at')
    .eq('id', artifactId)
    .eq('company_id', empresa) // 🔴 CLAUDE.md §7 — o filtro, não a policy, é o que protege
    .is('archived_at', null)
    .maybeSingle();

  if (!artifact) notFound();

  // A versão publicada é a mais alta. `current_version` existe em `artifacts`,
  // mas ordenar por `version` não depende de os dois campos concordarem — e um
  // documento cuja última versão ainda não publicou continua abrindo.
  const { data: versoes } = await supabase
    .from('artifact_versions')
    .select('id, version, status, published_at, data_as_of, confidence_note, created_at')
    .eq('artifact_id', artifact.id)
    .eq('company_id', empresa)
    .order('version', { ascending: false })
    .limit(1);

  const versao = versoes?.[0] ?? null;

  const { data: render } = versao
    ? await supabase
        .from('artifact_renders')
        .select('inline_content, byte_size, status, created_at')
        .eq('artifact_version_id', versao.id)
        .eq('company_id', empresa)
        .eq('format', 'html')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()
    : { data: null };

  const html: string | null =
    render?.status === 'ready' && typeof render?.inline_content === 'string'
      ? render.inline_content
      : null;

  const slugDono = AUXILIAR_DO_TEMPLATE[artifact.template_key ?? ''] ?? null;
  const hrefDono = ondeAbrirAuxiliar(slugDono);
  const nomeDono = slugDono ? (NOME_DO_AUXILIAR[slugDono] ?? slugDono) : null;

  const arquivo = `/dashboard/entregas/${artifact.id}/arquivo`;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.documento}
          title={artifact.title || 'Documento sem título'}
          subtitle={artifact.subtitle ?? artifact.summary ?? undefined}
          breadcrumb={[
            { label: 'Entregas', href: '/dashboard/entregas' },
            { label: tipoEmPortugues(artifact.kind) },
          ]}
          actions={
            html ? (
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={`${arquivo}?baixar=1`}
                  className="rounded-md border border-primary bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:opacity-90"
                >
                  Baixar
                </a>
                {/* Abrir cru é o mesmo arquivo que vira PDF na impressão do
                    navegador — dentro do iframe o CSS de impressão não alcança
                    o diálogo de imprimir. */}
                <a
                  href={arquivo}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40"
                >
                  Abrir em nova aba
                </a>
              </div>
            ) : undefined
          }
        />

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>{dataLonga(versao?.published_at ?? artifact.created_at)}</span>
          {nomeDono && hrefDono && (
            <span>
              Produzido por{' '}
              <Link href={hrefDono} className="text-primary underline">
                {nomeDono}
              </Link>
            </span>
          )}
          {!nomeDono && artifact.origin && <span>Origem: {artifact.origin}</span>}
          {versao && <span>versão {versao.version}</span>}
        </div>

        {/* A nota de confiança e a data dos dados vêm da SPEC-057 e não são
            decoração: um relatório sem "de quando é este dado" faz o corretor
            defender um número velho na frente do cliente. */}
        {(versao?.data_as_of || versao?.confidence_note) && (
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
            {versao.data_as_of && <p>Dados de {dataLonga(versao.data_as_of)}.</p>}
            {versao.confidence_note && <p className="mt-0.5">{versao.confidence_note}</p>}
          </div>
        )}

        {html ? (
          // `sandbox` sem `allow-scripts`: o render é HTML+CSS, não precisa de
          // script para nada, e o documento carrega dado de segurado. O que não
          // precisa executar, não executa.
          <iframe
            title={artifact.title || 'Documento'}
            srcDoc={html}
            sandbox=""
            className="h-[75vh] w-full rounded-xl border border-border bg-white"
          />
        ) : (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">
              Este documento ainda não tem versão para abrir
            </p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              O registro existe, mas o arquivo renderizado não está pronto
              {artifact.status ? ` (estado: ${artifact.status})` : ''}. Se ele foi
              gerado agora, tente de novo em instantes.
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <Link href="/dashboard/entregas" className="text-muted-foreground hover:text-foreground">
            ← Voltar para Entregas
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
