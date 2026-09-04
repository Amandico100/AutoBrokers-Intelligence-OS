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
//
// ─────────────────────────────────────────────────────────────────────────────
// SPEC-095 BLOCO E — versões, fontes, e o direito de perguntar.
//
// 📊 04/09/2026, quatro coisas medidas nesta página:
//
//   1. `AUXILIAR_DO_TEMPLATE` local conhecia 3 chaves de 7 → 35 de 136 peças
//      (25,7%) abriam SEM produtor, e um Pulso 360 dizia "Origem: chat"
//   2. "versão N" era texto morto: nunca houve uma v2 (max(version) = 1) e não
//      havia como ver, abrir nem baixar uma versão anterior
//   3. 🔴 a página afirmava, com data e hora, que o DADO era daquele instante
//      ("…de 4 de setembro de 2026, 02:55") — e
//      `data_as_of` é `now()` da ESCRITA em 136/136 versões, 30 delas no FUTURO
//      do próprio `created_at`. Era uma afirmação de frescor que o sistema não
//      tem como sustentar, e ela chegava à corretora
//   4. `notFound()` em peça arquivada — e a limpeza do B.4 arquiva 35 peças
//      cujos links o chat JÁ ENTREGOU
//
// O mapa de tipos agora é UM só (`lib/relatorios/tipos.ts`), lido por esta
// página e pela lista: é o que impede as duas telas de responderem coisas
// diferentes à pergunta "o que é isto?".
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { ondeAbrirAuxiliar } from '@/lib/auxiliaries/catalog';
import { DetailHeader } from '@/components/patterns/DetailHeader';
import { StatusPill } from '@/components/patterns/StatusPill';
import { icons } from '@/lib/icons';
import {
  ehPecaDeTeste,
  periodoDoRelatorio,
  produtor,
  tipoDoRelatorio,
  tipoHumanoPorKind,
} from '@/lib/relatorios/tipos';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Relatório · AutoBrokers' };

/** Só uuid entra no banco. Recusar antes evita transformar a rota em sonda. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Quantas versões a lista mostra. 📊 A peça com mais versões hoje tem 1. */
const LIMITE_DE_VERSOES = 24;

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

function dataCurta(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  });
}

/** Uma fonte de dado, nas duas formas que o banco tem hoje. */
interface Fonte {
  rotulo: string;
  detalhe: string;
  data: string;
}

/**
 * 📊 04/09/2026: 96 das 136 versões têm `data_sources` preenchido, e as chaves
 * são `{rotulo, detalhe, data}` (`workflows.py:257-264`). Outros produtores
 * gravam `{label, detail}` (`report_tool.py:271`). Ler as duas formas custa
 * três `??` e evita que a seção "De onde veio" fique vazia por causa do idioma
 * de quem escreveu a linha.
 */
function lerFontes(bruto: unknown): Fonte[] {
  if (!Array.isArray(bruto)) return [];
  const fontes: Fonte[] = [];
  for (const item of bruto) {
    if (!item || typeof item !== 'object') continue;
    const f = item as Record<string, unknown>;
    const rotulo = texto(f.rotulo) || texto(f.label) || texto(f.kind);
    if (!rotulo) continue;
    fontes.push({
      rotulo,
      detalhe: texto(f.detalhe) || texto(f.detail),
      data: texto(f.data) || texto(f.as_of),
    });
  }
  return fontes;
}

/** Um achado, na forma que o BLOCO D grava (`narrativa.py`). */
interface Achado {
  titulo: string;
  porQueImporta: string;
  oQueFazer: string;
  pergunta: string;
}

/**
 * Os achados da versão, e só os campos que são para o corretor LER.
 *
 * ⛔ O achado cru carrega `subject_id`, `metric_refs` e `producer_ref` — chaves
 * opacas de máquina. Nada disso entra na tela: quem quiser o rastro abre o
 * relatório. Um achado sem `o_que_fazer` não vira linha, porque uma seção
 * "Próximos passos" sem passo nenhum é pior que seção nenhuma.
 */
function lerAchados(bruto: unknown): Achado[] {
  if (!Array.isArray(bruto)) return [];
  const achados: Achado[] = [];
  for (const item of bruto) {
    if (!item || typeof item !== 'object') continue;
    const a = item as Record<string, unknown>;
    const oQueFazer = texto(a.o_que_fazer);
    if (!oQueFazer) continue;
    achados.push({
      titulo: texto(a.titulo) || texto(a.summary) || 'Ponto de atenção',
      porQueImporta: texto(a.por_que_importa) || texto(a.why_now),
      oQueFazer,
      pergunta: texto(a.pergunta),
    });
  }
  return achados;
}

function texto(v: unknown): string {
  return typeof v === 'string' ? v.trim() : '';
}

export default async function ArtifactPage({
  params,
  searchParams,
}: {
  params: Promise<{ artifactId: string }>;
  searchParams: Promise<{ versao?: string }>;
}) {
  const { artifactId } = await params;
  if (!UUID.test(artifactId)) notFound();

  const { versao: versaoPedida } = await searchParams;

  const auth = await requireCompanyMember({ write: false });
  // Sem sessão o middleware já teria mandado para /login. Chegar aqui sem
  // vínculo válido é o caso "usuário da corretora A com link da corretora B":
  // a resposta é a mesma de documento inexistente.
  if (!auth.ok) notFound();

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  // 🔴 SEM `.is('archived_at', null)` — a página ACEITA peça arquivada.
  //
  // 📊 A limpeza do B.4 arquiva 35 peças de teste da Resulta, e o `_link()` do
  // chat JÁ ENTREGOU os endereços delas. Devolver 404 para um link que o
  // próprio produto mandou é transformar uma limpeza reversível numa quebra
  // visível. A peça abre, com o banner dizendo que foi arquivada e quando.
  // O que protege continua sendo o filtro de empresa, não o de arquivo.
  const { data: artifact } = await supabase
    .from('artifacts')
    // Numa linha só de propósito: o supabase-js LÊ esta string em tempo de
    // tipo. Concatenada, ele desiste e o resultado vira `GenericStringError` —
    // e todo campo abaixo perde o tipo.
    .select('id, kind, title, subtitle, summary, template_key, origin, status, current_version, subject_ref, tags, created_at, updated_at, archived_at')
    .eq('id', artifactId)
    .eq('company_id', empresa) // 🔴 CLAUDE.md §7 — o filtro, não a policy, é o que protege
    .maybeSingle();

  if (!artifact) notFound();

  // Todas as versões, da mais nova para a mais velha (§3 ④ Figma: uma
  // identidade, muitas versões). `current_version` existe em `artifacts`, mas
  // ordenar por `version` não depende de os dois campos concordarem — e uma
  // peça cuja última versão ainda não publicou continua abrindo.
  const { data: versoes } = await supabase
    .from('artifact_versions')
    .select('id, version, status, published_at, data_as_of, confidence_note, data_sources, created_at')
    .eq('artifact_id', artifact.id)
    .eq('company_id', empresa)
    .order('version', { ascending: false })
    .limit(LIMITE_DE_VERSOES);

  const lista = versoes ?? [];
  // `?versao=` abre a versão exata. Um id que não seja desta peça (ou de outra
  // corretora) simplesmente não está na lista — e a página cai na atual, em vez
  // de virar sonda de existência.
  const versao = lista.find((v) => v.id === versaoPedida) ?? lista[0] ?? null;
  const ehAtual = versao ? versao.id === lista[0]?.id : true;

  // 🔴 O payload é lido SÓ pelo caminho `payload->findings`.
  //
  // 📊 O payload de uma versão tem 64.246 bytes, 5.890 deles em
  // `rotulos_de_produtor` — o nome do produtor, que não pode sair do Artifact
  // do tenant (SPEC-094 §2). ⚠️ E a linha volta pelo ÚLTIMO segmento do
  // caminho: `{ id, findings }`, nunca a coluna com o objeto dentro
  // (📊 supabase-js 2.58 / postgrest-js 1.21). Ler pelo caminho antigo — a
  // coluna e depois a chave — daria `undefined`, e a seção ficaria vazia em
  // silêncio.
  const { data: comAchados } = versao
    ? await supabase
        .from('artifact_versions')
        .select('id, payload->findings')
        .eq('id', versao.id)
        .eq('company_id', empresa)
        .maybeSingle()
    : { data: null };

  const achados = lerAchados((comAchados as { findings?: unknown } | null)?.findings);

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

  // O mapa único (A.2): o mesmo que a lista lê.
  const tipo = tipoDoRelatorio(artifact.template_key);
  // Peça sem `template_key` não tem entrada no mapa; aí o `kind` em português é
  // a melhor resposta que existe ("Proposta", "Carta") — e ela já era a de antes.
  const tipoHumano = artifact.template_key ? tipo.tipoHumano : tipoHumanoPorKind(artifact.kind);
  const quem = produtor(artifact.origin, artifact.template_key, artifact.subject_ref);
  const periodo = periodoDoRelatorio(artifact.subject_ref, artifact.created_at);
  const hrefDono = ondeAbrirAuxiliar(tipo.slugDoAuxiliar);
  const ehTeste = ehPecaDeTeste(artifact.tags);
  const Icone = icons[tipo.icone];

  const fontes = lerFontes(versao?.data_sources);

  /**
   * 🔴 A frase de frescor — e por que ela tem TRÊS formas.
   *
   * 📊 `data_as_of` é o carimbo da ESCRITA em 136/136 versões de hoje
   * (`service.py:155-160`), e em 30 delas está no futuro do próprio
   * `created_at` — desvio de relógio entre processos. Apresentar esse número
   * como a hora em que o DADO foi lido é afirmar um frescor que o sistema não
   * mede.
   *
   * O que distingue uma data confiável de um carimbo é quem publicou: as peças
   * do BLOCO B gravam `subject_ref.produtor` junto com a data real de leitura.
   * Sem produtor declarado, a peça é uma das 136 antigas e a frase é "gerado
   * em" — que é verdade sobre qualquer uma delas.
   */
  const rotuloDaData = !versao?.data_as_of
    ? null
    : quem.origem === 'inferido'
      ? `Gerado em ${dataLonga(versao.data_as_of)}.`
      : tipo.slugDoAuxiliar === 'checklist-6h'
        ? `Período ${periodo || dataLonga(versao.data_as_of)}.`
        : `Dados lidos em ${dataLonga(versao.data_as_of)}.`;

  const arquivo = `/dashboard/entregas/${artifact.id}/arquivo`;
  const arquivoDaVersao = versao ? `${arquivo}?versao=${versao.id}` : arquivo;
  const baixarDaVersao = `${arquivoDaVersao}${versao ? '&' : '?'}baixar=1`;
  const id8 = artifact.id.slice(0, 8);
  const perguntaSobreAPeca = `Sobre o relatório «${artifact.title || 'sem título'}» (${id8}): `;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={Icone}
          title={artifact.title || 'Documento sem título'}
          subtitle={artifact.subtitle ?? artifact.summary ?? undefined}
          breadcrumb={[
            { label: 'Relatórios', href: '/dashboard/entregas' },
            { label: tipoHumano },
          ]}
          actions={
            html ? (
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={baixarDaVersao}
                  className="rounded-md border border-primary bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:opacity-90"
                >
                  Baixar
                </a>
                {/* Abrir cru é o mesmo arquivo que vira PDF na impressão do
                    navegador — dentro do iframe o CSS de impressão não alcança
                    o diálogo de imprimir. */}
                <a
                  href={arquivoDaVersao}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40"
                >
                  Abrir em nova aba
                </a>
                <Link
                  href={`/dashboard/chat?pergunta=${encodeURIComponent(perguntaSobreAPeca)}`}
                  className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:border-primary/40"
                >
                  Perguntar ao AutoBrokers
                </Link>
              </div>
            ) : undefined
          }
        />

        {/* O que é, de quem é, de quando é — a mesma resposta da lista, do mesmo
            mapa. 📊 Antes esta linha dizia "Origem: chat" para um Pulso 360. */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>{tipoHumano}</span>
          <span>
            {hrefDono ? (
              <>
                Produzido por{' '}
                <Link href={hrefDono} className="text-primary underline">
                  {quem.nome}
                </Link>
              </>
            ) : (
              <>Produzido por {quem.nome}</>
            )}
          </span>
          {periodo && <span>{periodo}</span>}
          {versao && (
            <span>
              versão {versao.version}
              {!ehAtual ? ' (anterior)' : ''}
            </span>
          )}
        </div>

        {ehTeste && (
          <div className="rounded-lg border border-dashed border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
            <StatusPill tone="neutral" label="peça de teste" className="mr-2" />
            Peça gerada por um teste do produto. Ela não entra na sua biblioteca
            de relatórios.
          </div>
        )}

        {artifact.archived_at && (
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
            <StatusPill tone="neutral" label="arquivado" className="mr-2" />
            Arquivado em {dataLonga(artifact.archived_at)}. O conteúdo continua
            aqui — arquivar não apaga nada.
          </div>
        )}

        {/* A data e a nota de confiança vêm da SPEC-057 e não são decoração: um
            relatório sem "de quando é este dado" faz o corretor defender um
            número velho na frente do cliente. E uma data que o sistema não mede
            é pior que nenhuma — por isso a frase muda com quem publicou. */}
        {(rotuloDaData || versao?.confidence_note) && (
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
            {rotuloDaData && <p>{rotuloDaData}</p>}
            {versao?.confidence_note && <p className="mt-0.5">{versao.confidence_note}</p>}
          </div>
        )}

        {achados.length > 0 && (
          <section className="rounded-xl border border-border bg-surface p-4">
            <h2 className="text-sm font-medium text-foreground">Próximos passos</h2>
            <ul className="mt-3 space-y-3">
              {achados.map((a, i) => (
                <li key={i} className="border-l-2 border-primary/40 pl-3">
                  <p className="text-sm text-foreground">{a.titulo}</p>
                  {a.porQueImporta && (
                    <p className="mt-0.5 text-xs text-muted-foreground">{a.porQueImporta}</p>
                  )}
                  <p className="mt-1 text-xs text-foreground">{a.oQueFazer}</p>
                  {a.pergunta && (
                    <Link
                      href={`/dashboard/chat?pergunta=${encodeURIComponent(a.pergunta)}`}
                      className="mt-1 inline-block text-xs text-primary hover:underline"
                    >
                      Perguntar sobre isto →
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </section>
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

        {fontes.length > 0 && (
          <section className="rounded-xl border border-border bg-surface p-4">
            <h2 className="text-sm font-medium text-foreground">De onde veio</h2>
            <ul className="mt-2 space-y-1">
              {fontes.map((f, i) => (
                <li key={i} className="text-xs text-muted-foreground">
                  <span className="text-foreground">{f.rotulo}</span>
                  {f.detalhe ? ` · ${f.detalhe}` : ''}
                  {f.data ? ` · ${dataCurta(f.data) || f.data}` : ''}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* §3 ④ (Figma) e ⑥ (Claude Artifacts): a lista mostra a PEÇA, e o
            seletor de versões mora dentro dela. 📊 Era isto que transformava
            cinco Pulsos idênticos na lista em um Pulso com cinco versões. */}
        {lista.length > 1 && (
          <section className="rounded-xl border border-border bg-surface p-4">
            <h2 className="text-sm font-medium text-foreground">Versões</h2>
            <ul className="mt-2 space-y-1">
              {lista.map((v) => (
                <li key={v.id} className="text-xs">
                  <Link
                    href={`/dashboard/entregas/${artifact.id}?versao=${v.id}`}
                    className={
                      v.id === versao?.id
                        ? 'font-medium text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }
                  >
                    versão {v.version}
                  </Link>
                  <span className="text-faint">
                    {' · '}
                    {dataCurta(v.published_at ?? v.created_at)}
                    {v.id === lista[0]?.id ? ' · atual' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <Link href="/dashboard/entregas" className="text-muted-foreground hover:text-foreground">
            ← Voltar para Relatórios
          </Link>
          {hrefDono && (
            <Link href={hrefDono} className="text-primary hover:underline">
              Ver o {quem.nome}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
