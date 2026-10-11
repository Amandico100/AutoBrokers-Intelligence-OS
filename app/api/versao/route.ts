import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * 11/10/2026 · Qual versão do site está no ar? (o Founder abre este endereço depois de clicar Implantar)
 *
 * `build_em` e `commit` são gravados pelo `next.config.js` NA HORA DO BUILD — se a data for antiga, o Implantar
 * ainda não terminou ou não pegou a última versão. Público e só leitura: não há segredo aqui.
 */
export async function GET() {
  const buildEm = process.env.AUTOBROKERS_BUILD_EM || '';
  const commit = process.env.AUTOBROKERS_BUILD_COMMIT || 'desconhecido';
  let quando = '';
  if (buildEm) {
    try {
      quando = new Date(buildEm).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    } catch {
      quando = buildEm;
    }
  }
  return NextResponse.json(
    {
      servico: 'smith-web',
      build_em: buildEm,
      build_em_brasilia: quando,
      commit,
      leia_assim: 'se build_em_brasilia for anterior ao seu último Implantar, o site ainda está na versão antiga',
    },
    { headers: { 'Cache-Control': 'no-store' } },
  );
}
