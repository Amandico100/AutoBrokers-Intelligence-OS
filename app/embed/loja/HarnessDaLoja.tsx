'use client';

// modelo: claude-opus-5-5
//
// ⚠️ HARNESS TEMPORÁRIO DE CAPTURA — SPEC-139 · L6 (o mesmo expediente da SPEC-131-B, apagado ao fim da SPEC).
//
// Monta as telas REAIS da loja (os mesmos componentes do produto) com DADOS DE EXEMPLO, para o juiz de design capturar
// sem login. Nada chama o banco nem a sessão: todo `fetch` a `/api/...` desta página é respondido aqui, em memória,
// por `respostaDeExemplo` (dados inventados e marcados "exemplo"); POST não faz nada. O que não tem exemplo responde
// 404 e a tela mostra o estado de erro dela — também é uma captura válida.
//
// Endereços (todos com `&tema=claro|escuro`, e `&limpo=1` tira a faixa amarela):
//   /embed/loja                                          o índice
//   /embed/loja?tela=galeria                             a loja (Todos; "Em breve" no fim, ou o filtro do segmentado)
//   /embed/loja?tela=grade                               as 18 capas em cards, numa grade só
//   /embed/loja?tela=app&slug=renovacao                  a página de um aplicativo (&aba=… para cada aba)
//   /embed/loja?tela=app&slug=cobranca-feita&estado=nao-instalada | &aba=configurar | &aba=cobrancas
//   /embed/loja?tela=app&slug=checklist-6h&aba=hoje · follow-up-whatsapp&aba=follow-ups · resumo-atendimentos&aba=resumos
//   /embed/loja?tela=app&slug=caca-comissao             um "Em breve"

import { useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useTheme } from 'next-themes';
import { ArrowLeft } from 'lucide-react';

import AuxiliaresClient from '@/app/dashboard/auxiliares/AuxiliaresClient';
import AuxiliarDetalheClient from '@/app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient';
import { CardDoAplicativo } from '@/components/aplicativos/casca/CardDoAplicativo';
import { LarguraDoAplicativo } from '@/components/aplicativos/casca/LarguraDoAplicativo';
import { abasDoAplicativo, abasLargas, podeLigar } from '@/lib/auxiliaries/catalog';

import { FONTES_DE_EXEMPLO, SLUGS_DE_EXEMPLO, cobrancaDeExemplo, itemDeExemplo, respostaDeExemplo } from './dados-de-exemplo';

// O dublê de `fetch` entra quando o módulo carrega no navegador — ANTES de qualquer efeito dos filhos (os efeitos dos
// filhos rodam antes dos do pai; instalar num useEffect daqui chegaria tarde).
if (typeof window !== 'undefined' && !(window as unknown as { __lojaDeExemplo?: boolean }).__lojaDeExemplo) {
  (window as unknown as { __lojaDeExemplo?: boolean }).__lojaDeExemplo = true;
  const real = window.fetch.bind(window);
  window.fetch = async (entrada: RequestInfo | URL, init?: RequestInit) => {
    const bruto = typeof entrada === 'string' ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
    const url = new URL(bruto, window.location.origin);
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return real(entrada, init);
    const metodo = (init?.method || (entrada instanceof Request ? entrada.method : 'GET')).toUpperCase();
    const corpo = respostaDeExemplo(url.pathname, url.searchParams, metodo, new URLSearchParams(window.location.search));
    await new Promise((r) => setTimeout(r, 120));
    return new Response(JSON.stringify(corpo ?? { ok: false, error: 'Sem dado de exemplo para esta parte (harness).' }), {
      status: corpo === null ? 404 : 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
}

function Tema({ tema }: { tema: string | null }) {
  const { setTheme } = useTheme();
  useEffect(() => {
    if (tema === 'claro') setTheme('light');
    else if (tema === 'escuro') setTheme('dark');
  }, [tema, setTheme]);
  return null;
}

function Faixa() {
  return (
    <p className="border-b border-warning/40 bg-warning/10 px-4 py-2 text-center text-sm text-foreground" role="note">
      Harness de captura da SPEC-139 — dados de EXEMPLO, nada vem do banco. Temporário: sai ao fim da SPEC.
    </p>
  );
}

const TELAS: [string, string][] = [
  ['tela=galeria', 'A loja (Todos · Em breve)'],
  ['tela=grade', 'As 18 capas no card'],
  ['tela=app&slug=renovacao', 'Renovação — Início'],
  ['tela=app&slug=cobranca-feita&estado=nao-instalada', 'Cobrança — não instalada'],
  ['tela=app&slug=cobranca-feita&aba=configurar', 'Cobrança — Configurar'],
  ['tela=app&slug=cobranca-feita&aba=cobrancas', 'Cobrança — Cobranças'],
  ['tela=app&slug=checklist-6h&aba=hoje', 'Checklist das 6h — Hoje'],
  ['tela=app&slug=follow-up-whatsapp&aba=follow-ups', 'Follow-up — Follow-ups'],
  ['tela=app&slug=resumo-atendimentos&aba=resumos', 'Resumo — Resumos'],
  ['tela=app&slug=caca-comissao', 'Um "Em breve"'],
];

export default function HarnessDaLoja() {
  const busca = useSearchParams();
  const tela = busca?.get('tela') ?? 'indice';
  const slug = busca?.get('slug') ?? 'renovacao';
  const estado = busca?.get('estado') ?? null;
  const tema = busca?.get('tema') ?? null;
  const limpo = busca?.get('limpo') === '1';

  const item = useMemo(() => (slug === 'cobranca-feita' ? cobrancaDeExemplo(estado) : itemDeExemplo(slug)), [slug, estado]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Tema tema={tema} />
      {!limpo && <Faixa />}

      {tela === 'galeria' && <AuxiliaresClient />}

      {tela === 'grade' && (
        <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6">
          <h1 className="mb-6 text-2xl font-semibold tracking-tight">As 18 capas (exemplo)</h1>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {SLUGS_DE_EXEMPLO.map((s) => (
              <CardDoAplicativo key={s} item={{ ...itemDeExemplo(s), estado: 'disponivel', estado_catalogo: 'available' }} />
            ))}
          </div>
        </div>
      )}

      {tela === 'app' && (
        <div className="h-full overflow-y-auto">
          <LarguraDoAplicativo largas={abasLargas(abasDoAplicativo(item))}>
            <Link
              href="/embed/loja?tela=galeria"
              className="mb-4 inline-flex min-h-[44px] items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
              Aplicativos
            </Link>
            <AuxiliarDetalheClient
              key={`${slug}-${estado ?? ''}`}
              item={item}
              podeLigar={podeLigar(item)}
              atividade={[]}
              fontes={slug === 'renovacao' ? FONTES_DE_EXEMPLO : { prontidao: null, meuAgger: null }}
            />
          </LarguraDoAplicativo>
        </div>
      )}

      {tela === 'indice' && (
        <div className="mx-auto max-w-2xl space-y-4 px-4 py-10">
          <h1 className="text-2xl font-semibold tracking-tight">Harness da loja (SPEC-139)</h1>
          <ul className="space-y-2">
            {TELAS.map(([q, rotulo]) => (
              <li key={q} className="flex flex-wrap gap-3 text-sm">
                <span className="w-56">{rotulo}</span>
                <Link className="underline" href={`/embed/loja?${q}&tema=claro`}>claro</Link>
                <Link className="underline" href={`/embed/loja?${q}&tema=escuro`}>escuro</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
