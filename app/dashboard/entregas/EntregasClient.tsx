'use client';

// SPEC-064 Bloco B/E — Entregas.
//
// Um lugar só para a pergunta "o que já aconteceu aqui?". Antes eram três
// itens de menu (Atividades, Histórico, Pesquisas) e dois produtores sem tela
// nenhuma (artifacts e execuções de auxiliar).
//
// SPEC-078 F.6 — 📊 17/08/2026, dois defeitos medidos aqui:
//
//   1. `?tipo=` era IGNORADO. `/dashboard/historico` redireciona para
//      `/dashboard/entregas?tipo=conversa` e `/dashboard/auxiliares/execucoes`
//      para `?tipo=trabalho` — os dois links funcionavam e a tela abria em
//      "Tudo". Quem vinha do Histórico caía numa lista com artifacts,
//      briefings e atividades no meio, e concluía que o Histórico sumiu.
//
//   2. Linha sem destino tinha a MESMA aparência de linha com destino:
//      mesma borda, mesmo fundo, mesmo tamanho. Só o clique revelava a
//      diferença — e clique que não faz nada é o que ensina o corretor a
//      parar de clicar.

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2, FileText, MessageSquare, Cog, Search } from 'lucide-react';

import { DetailHeader } from '@/components/patterns/DetailHeader';
import { icons } from '@/lib/icons';

type Tipo = 'documento' | 'conversa' | 'trabalho' | 'pesquisa';

interface Entrega {
  id: string;
  tipo: Tipo;
  titulo: string;
  detalhe: string | null;
  quando: string;
  href: string | null;
  origem: string | null;
}

const TIPOS: { chave: Tipo | 'tudo'; rotulo: string; Icone?: typeof FileText }[] = [
  { chave: 'tudo', rotulo: 'Tudo' },
  { chave: 'documento', rotulo: 'Documentos', Icone: FileText },
  { chave: 'conversa', rotulo: 'Conversas', Icone: MessageSquare },
  { chave: 'trabalho', rotulo: 'Trabalhos', Icone: Cog },
  { chave: 'pesquisa', rotulo: 'Pesquisas', Icone: Search },
];

/**
 * Os valores de `?tipo=` que a URL pode pedir.
 *
 * `pesquisa` fica FORA: ele existe em TIPOS como porta para a tela própria de
 * Pesquisas, não como filtro desta lista — aceitá-lo aqui abriria a tela numa
 * seleção que nunca tem resultado.
 */
const FILTROS_DA_URL: string[] = ['tudo', 'documento', 'conversa', 'trabalho'];

const COR: Record<Tipo, string> = {
  documento: 'text-primary',
  conversa: 'text-emerald-600',
  trabalho: 'text-amber-600',
  pesquisa: 'text-purple-500',
};

function quando(iso: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  const agora = new Date();
  const dias = Math.floor((agora.getTime() - d.getTime()) / 86_400_000);
  const hora = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  if (dias === 0) return `hoje ${hora}`;
  if (dias === 1) return `ontem ${hora}`;
  if (dias < 7) return `${dias} dias atrás`;
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
}

function Linha({ item }: { item: Entrega }) {
  const Icone = TIPOS.find((t) => t.chave === item.tipo)?.Icone ?? FileText;
  const corpo = (
    <>
      <span className={`mt-0.5 shrink-0 ${COR[item.tipo]}`}>
        <Icone className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{item.titulo}</p>
        {item.detalhe && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{item.detalhe}</p>
        )}
        <p className="mt-1 text-[11px] text-faint">
          {quando(item.quando)}
          {item.origem ? ` · ${item.origem}` : ''}
        </p>
      </div>
    </>
  );

  const classe = 'flex items-start gap-3 rounded-lg border px-3 py-2.5';

  if (item.href) {
    return (
      <Link
        href={item.href}
        className={`${classe} border-border bg-surface transition-colors hover:border-primary/40`}
      >
        {corpo}
      </Link>
    );
  }

  // SPEC-078 F.6b — a linha sem destino PARECE sem destino.
  //
  // Devolver um <div> com a aparência do <Link> não bastava: o corretor clicava
  // e nada acontecia, o que é pior do que uma linha que se anuncia como
  // registro. Borda tracejada, fundo recuado e `cursor-default` dizem "isto é
  // um registro, não uma porta" antes do clique.
  //
  // O certo continua sendo dar destino — este ramo é para o que ainda não tem
  // (categoria de atividade nova, execução de auxiliar já desinstalado).
  return (
    <div
      className={`${classe} cursor-default border-dashed border-border/60 bg-surface/40`}
      title="Este registro não tem tela para abrir"
    >
      {corpo}
    </div>
  );
}

export default function EntregasClient() {
  const [itens, setItens] = useState<Entrega[] | null>(null);
  const [contagem, setContagem] = useState<Record<string, number>>({});
  const [aviso, setAviso] = useState('');
  const [filtro, setFiltro] = useState<Tipo | 'tudo'>('tudo');
  const [busca, setBusca] = useState('');

  const carregar = useCallback(async () => {
    try {
      const r = await fetch('/api/dashboard/entregas', { cache: 'no-store' });
      const j = await r.json();
      if (!r.ok || !j?.ok) {
        setAviso(j?.error || 'Não foi possível carregar.');
        setItens([]);
        return;
      }
      setItens(j.itens || []);
      setContagem(j.contagem || {});
    } catch {
      setAviso('Falha de conexão.');
      setItens([]);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // SPEC-078 F.6 — `?tipo=` passa a valer.
  //
  // 📊 17/08/2026 este estado nascia em 'tudo' e nunca olhava a URL, enquanto
  // DOIS redirects permanentes já mandavam o filtro:
  //     /dashboard/historico            → /dashboard/entregas?tipo=conversa
  //     /dashboard/auxiliares/execucoes → /dashboard/entregas?tipo=trabalho
  //
  // Lido em `useEffect` e não em `useState(() => …)` de propósito: o
  // inicializador rodaria no cliente com uma URL que o servidor não viu, e a
  // hidratação acusaria diferença nas classes dos botões. É o mesmo padrão que
  // já funciona em app/dashboard/auxiliares/rotinas/page.tsx.
  useEffect(() => {
    try {
      const t = new URLSearchParams(window.location.search).get('tipo');
      // Só valor que FILTRA alguma coisa entra. `?tipo=lixo` deixaria a lista
      // vazia e o corretor sem entender por quê; `?tipo=pesquisa` faria o
      // mesmo, porque pesquisa não é um tipo desta lista — é a porta para a
      // tela própria (ver o botão mais abaixo).
      if (t && FILTROS_DA_URL.includes(t)) setFiltro(t as Tipo | 'tudo');
    } catch {
      /* sem query — abre em "Tudo", que é o padrão */
    }
  }, []);

  const filtrados = useMemo(() => {
    if (!itens) return [];
    const termo = busca.trim().toLowerCase();
    return itens.filter((i) => {
      if (filtro !== 'tudo' && i.tipo !== filtro) return false;
      if (!termo) return true;
      return (
        i.titulo.toLowerCase().includes(termo) ||
        (i.detalhe || '').toLowerCase().includes(termo) ||
        (i.origem || '').toLowerCase().includes(termo)
      );
    });
  }, [itens, filtro, busca]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.success}
          title="Entregas"
          subtitle="Tudo que o AutoBrokers fez por você — documentos, conversas, trabalhos e pesquisas, num lugar só."
          breadcrumb={[{ label: 'Entregas' }]}
        />

        {aviso && <p className="text-sm text-danger">{aviso}</p>}

        <div className="flex flex-wrap items-center gap-2">
          {TIPOS.map((t) => {
            const n = t.chave === 'tudo' ? (itens?.length ?? 0) : (contagem[t.chave] ?? 0);
            const classe = `rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
              filtro === t.chave
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-surface text-muted-foreground hover:border-primary/40'
            }`;

            // Pesquisa tem tela própria — ela veio de /dashboard/pesquisas e
            // mostra procedência, fontes e o que foi verificado, coisas que
            // uma linha de timeline não comporta. O filtro leva para lá em vez
            // de fingir que cabe aqui.
            //
            // Sem este link a tela ficaria órfã: foi exatamente o que o
            // test_navegacao_sem_pagina_orfa pegou quando eu a movi.
            //
            // ── SPEC-078 F.6, decisão registrada (regra 0–100 do §14) ──
            //
            // 📊 17/08/2026: `contagem['pesquisa']` é PROVADAMENTE zero — ela é
            // derivada de `itens`, e nenhuma das cinco fontes da rota produz
            // `tipo: 'pesquisa'`. O `(${n})` aqui era código morto que fingia
            // ser um contador.
            //
            //   A) dar fonte: ler research_* como sexta fonte ............ 55
            //      Duplicaria a pesquisa em dois lugares e a linha de timeline
            //      não comporta procedência nem fontes — que é exatamente a
            //      razão de a tela própria existir. Mais uma consulta por
            //      carga para mostrar de novo o que já tem tela melhor.
            //   B) remover o botão ...................................... 30
            //      Deixa /dashboard/entregas/pesquisas órfã. Já aconteceu uma
            //      vez e o guarda de página órfã pegou.
            //   C) assumir que é PORTA, não filtro: tirar o contador morto
            //      e marcar que o clique sai daqui .................... 85
            //      Nada mente, nada fica órfão, nenhuma consulta a mais.
            //
            // Executada a C.
            if (t.chave === 'pesquisa') {
              return (
                <Link
                  key={t.chave}
                  href="/dashboard/entregas/pesquisas"
                  className={classe}
                  title="As pesquisas têm tela própria, com as fontes de cada afirmação"
                >
                  {t.rotulo} ↗
                </Link>
              );
            }

            return (
              <button key={t.chave} onClick={() => setFiltro(t.chave)} className={classe}>
                {t.rotulo}
                {n > 0 ? ` (${n})` : ''}
              </button>
            );
          })}

          <div className="relative ml-auto">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="buscar"
              className="w-40 rounded-md border border-border bg-surface py-1 pl-7 pr-2 text-xs text-foreground placeholder:text-faint focus:border-primary focus:outline-none"
            />
          </div>
        </div>

        {itens === null ? (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
          </div>
        ) : filtrados.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface p-8 text-center">
            <p className="text-sm font-medium text-foreground">
              {itens.length === 0 ? 'Nada foi entregue ainda' : 'Nada com esse filtro'}
            </p>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              {itens.length === 0 ? (
                <>
                  Quando você ligar um Auxiliar, o que ele fizer aparece aqui.{' '}
                  <Link href="/dashboard/auxiliares" className="text-primary underline">
                    Ver Auxiliares
                  </Link>
                </>
              ) : (
                'Tente outro tipo, ou limpe a busca.'
              )}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtrados.map((i) => (
              <Linha key={i.id} item={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
