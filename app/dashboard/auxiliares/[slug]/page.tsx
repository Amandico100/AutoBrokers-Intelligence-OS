// SPEC-064 Bloco C.3 — a página de cada Auxiliar.
//
// Server component: resolve a sessão e a corretora no servidor. O `companyId`
// NUNCA vem do client — é o mesmo princípio de todo o dashboard.
//
// A rota é dinâmica por slug, e é a ÚNICA. A auditoria encontrou duas páginas
// escritas à mão ao lado da rota dinâmica da galeria — `follow-up-whatsapp/` e
// `resumo-atendimentos/` — que é exatamente como a bagunça se reproduz: cada
// Auxiliar novo acha que é exceção. Aqui não há exceção.

import { notFound, redirect } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

import { getSupabaseAdmin, resolveSessionCompany } from '@/lib/auxiliaries/server';
import { auxiliarPorSlug, podeLigar } from '@/lib/auxiliaries/catalog';
import AuxiliarDetalheClient from './AuxiliarDetalheClient';

export const dynamic = 'force-dynamic';

export default async function AuxiliarPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const sessao = await resolveSessionCompany();
  if (!sessao) redirect('/login');

  const item = await auxiliarPorSlug(getSupabaseAdmin(), sessao.companyId, slug);
  if (!item) notFound();

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <Link
          href="/dashboard/auxiliares"
          className="mb-6 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Auxiliares
        </Link>

        <AuxiliarDetalheClient item={item} podeLigar={podeLigar(item)} />
      </div>
    </div>
  );
}
