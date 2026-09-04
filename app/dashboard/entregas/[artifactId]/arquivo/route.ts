// SPEC-078 Bloco F.1 — o arquivo do documento: abrir cru e baixar.
//
// É uma rota e não uma página, pela mesma razão que `/r/[token]` é: o render do
// Artifact Hub já é um documento HTML completo, com <head>, marca da corretora
// e CSS de impressão. Servido cru, o que o corretor abre (e manda para o
// cliente, e imprime em PDF) é exatamente o mesmo arquivo que a página mostra
// no iframe.
//
// 🔴 MULTI-TENANT (CLAUDE.md §7). Esta rota é a que ENTREGA BYTES — é a que
// mais precisa do filtro. Ela repete a checagem inteira em vez de confiar na
// página que a chamou: um endereço é um endereço, e ninguém precisa passar pela
// página para chegar aqui. Toda consulta leva `.eq('company_id', empresa)`.
//
// 📊 17/08/2026: os 36 renders existentes são `format='html'`,
// `status='ready'`, `inline_content` presente e `storage_ref` em nenhum — por
// isso não há caminho de MinIO aqui. Quando houver, ele entra como um segundo
// ramo, não como outra rota.
import { NextRequest, NextResponse } from 'next/server';

import { requireCompanyMember } from '@/lib/admin/admin-auth';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Nome de arquivo previsível e sem acento — ele vai parar no Downloads de alguém.
 *
 * A versão entra no nome quando a peça tem mais de uma: duas versões do mesmo
 * relatório baixadas no mesmo dia colidiriam no mesmo arquivo, e o corretor
 * mandaria ao cliente a que o navegador deixou por último.
 */
function nomeDeArquivo(titulo: string | null, quando: string | null, versao?: number): string {
  const base = (titulo || 'documento')
    .normalize('NFD')
    // Tira o acento pela faixa de marcas combinantes (a forma NFD separa a marca da letra).
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
    .slice(0, 60) || 'documento';
  const dia = (quando || new Date().toISOString()).slice(0, 10);
  return `${base}-${dia}${versao ? `-v${versao}` : ''}.html`;
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ artifactId: string }> },
) {
  const { artifactId } = await params;
  if (!UUID.test(artifactId)) {
    return new NextResponse('nao encontrado', { status: 404 });
  }

  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) {
    // Mesma resposta para "não é sua" e "não existe": distinguir os dois
    // transformaria a rota em sonda de existência de documento alheio.
    return new NextResponse('nao encontrado', { status: auth.status === 401 ? 401 : 404 });
  }

  const { supabase, ctx } = auth;
  const empresa = ctx.companyId;

  // SPEC-095 BLOCO E — a peça arquivada continua baixando.
  //
  // 📊 A limpeza do B.4 arquiva 35 peças de teste, e o chat já entregou os links
  // delas. O filtro que protege é o de EMPRESA; o de arquivo era só um filtro de
  // listagem que virou um 404 na cara de quem clicou.
  const { data: artifact } = await supabase
    .from('artifacts')
    .select('id, title, created_at')
    .eq('id', artifactId)
    .eq('company_id', empresa) // 🔴 o filtro é a proteção — service role atravessa RLS
    .maybeSingle();

  if (!artifact) return new NextResponse('nao encontrado', { status: 404 });

  // SPEC-095 BLOCO E — `?versao=` baixa a VERSÃO PEDIDA, não sempre a última.
  //
  // 📊 Nunca existiu uma v2 até esta SPEC (max(version) = 1 em 136 versões), e
  // por isso "baixar sempre a última" e "baixar a que está na tela" davam o
  // mesmo arquivo. A partir do BLOCO B eles divergem — e o corretor que abriu a
  // versão 2 e clicou em Baixar levaria a 5 sem perceber, para o cliente dele.
  //
  // 🔴 O `?versao=` é filtrado por `artifact_id` E por `company_id`: um id de
  // versão de outra corretora não abre atalho para os bytes dela.
  const pedida = req.nextUrl.searchParams.get('versao');
  const { data: versoes } = await supabase
    .from('artifact_versions')
    .select('id, version, published_at')
    .eq('artifact_id', artifact.id)
    .eq('company_id', empresa)
    .order('version', { ascending: false })
    .limit(60);

  const lista = versoes ?? [];
  // Versão pedida que não seja desta peça simplesmente não está na lista: a
  // resposta é a peça atual, não um 404 que denunciaria a existência dela.
  const versao = (pedida ? lista.find((v) => v.id === pedida) : null) ?? lista[0] ?? null;
  if (!versao) return new NextResponse('sem versao', { status: 404 });

  const { data: render } = await supabase
    .from('artifact_renders')
    .select('inline_content, status')
    .eq('artifact_version_id', versao.id)
    .eq('company_id', empresa)
    .eq('format', 'html')
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (render?.status !== 'ready' || typeof render?.inline_content !== 'string') {
    return new NextResponse('render indisponivel', { status: 404 });
  }

  const baixar = req.nextUrl.searchParams.get('baixar');
  const nome = nomeDeArquivo(
    artifact.title,
    versao.published_at ?? artifact.created_at,
    lista.length > 1 ? versao.version : undefined,
  );

  return new NextResponse(render.inline_content, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      // O documento tem CPF/CNPJ e telefone de segurado. Ele não entra em cache
      // de intermediário nem sobrevive num proxy compartilhado.
      'Cache-Control': 'private, no-store',
      'X-Robots-Tag': 'noindex, nofollow',
      ...(baixar
        ? { 'Content-Disposition': `attachment; filename="${nome}"` }
        : {}),
    },
  });
}
