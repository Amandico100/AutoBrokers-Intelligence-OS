'use client';

// SPEC-131-B · G1 — as abas de todo aplicativo, por `?aba=` (laudo de design §3).
//
// Radix Tabs controlado pela URL: trocar de aba faz `router.push('?aba=…', { scroll: false })` — "voltar" do
// navegador volta à aba anterior; aba inválida → Início (`abaValida`). Barra grudada no topo, rolagem horizontal no
// celular, gatilho de 44 px, ativo com sublinhado de 2 px.
//
// 🔴 O contrato com G2/G3 (SPEC §5): uma aba com `componente = '<pasta>/Aba<Nome>'` é carregada por import
// dinâmico de `components/aplicativos/<pasta>/Aba<Nome>.tsx` (export default, recebe `PropsDaAba`). A casca NUNCA
// importa esses arquivos estaticamente: cada um só pesa quando a aba abre, e um arquivo que ainda não existe vira
// a frase "esta parte ainda está sendo preparada", não uma tela quebrada.

import { useEffect, useRef, useState, type CSSProperties, type ComponentType, type ReactNode } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import type { AbaDoAplicativo, ItemDoCatalogo, PropsDaAba } from '@/lib/auxiliaries/catalog';

/** Só `<pasta>/Aba<Nome>`, letras, números e hífen — nada de `..` nem caminho arbitrário. */
const FORMA_DO_COMPONENTE = /^([a-z0-9-]+)\/Aba([A-Za-z0-9]+)$/;

/** A altura da barra de abas antes da medida (gatilho h-11 = 44 px + a borda de 1 px): o 1º desenho já gruda certo. */
const ALTURA_INICIAL_DAS_ABAS = '45px';

function AbaCarregada({ componente, item, aba }: { componente: string; item: ItemDoCatalogo; aba: string }) {
  const [Comp, setComp] = useState<ComponentType<PropsDaAba> | null>(null);
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    let vivo = true;
    setComp(null);
    setFalhou(false);
    const m = FORMA_DO_COMPONENTE.exec(componente);
    if (!m) {
      setFalhou(true);
      return;
    }
    const [, pasta, nome] = m;
    // o webpack transforma este template num CONTEXTO: cada aba vira um chunk. 🔴 Conserto K2: sem o
    // `webpackInclude`, o contexto era `components/aplicativos/ lazy ^\.\/.*$` — TODO arquivo da pasta, inclusive os
    // `*.test.mjs` (📊 13/10, `next dev`: um teste com `node:child_process` derrubou a compilação da página do
    // aplicativo inteira, e os testes com `node:fs` iam parar no pacote do navegador). Só `<pasta>/Aba<Nome>.tsx` entra.
    import(
      /* webpackInclude: /[\\/][a-z0-9-]+[\\/]Aba[A-Za-z0-9]+\.tsx$/ */
      `@/components/aplicativos/${pasta}/Aba${nome}`
    )
      .then((mod) => {
        if (!vivo) return;
        if (typeof mod?.default === 'function' || typeof mod?.default === 'object') setComp(() => mod.default);
        else setFalhou(true);
      })
      .catch((e) => {
        console.error('[APLICATIVO] a aba não carregou', componente, e);
        if (vivo) setFalhou(true);
      });
    return () => {
      vivo = false;
    };
  }, [componente]);

  if (falhou) {
    return (
      <p className="rounded-xl border border-border bg-surface p-6 text-sm text-muted-foreground">
        Esta parte do aplicativo ainda está sendo preparada.
      </p>
    );
  }
  if (!Comp) {
    return (
      <p className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Carregando…
      </p>
    );
  }
  return <Comp item={item} aba={aba} />;
}

export interface AbasDoAplicativoProps {
  item: ItemDoCatalogo;
  abas: AbaDoAplicativo[];
  abaAtual: string;
  /** o conteúdo das abas que a casca desenha (`componente === null`), por id */
  conteudo: Record<string, ReactNode>;
  /** um ponto de atenção no gatilho (ex.: Configurar com passo faltando) */
  marcadas?: string[];
}

export function AbasDoAplicativo({ item, abas, abaAtual, conteudo, marcadas = [] }: AbasDoAplicativoProps) {
  const router = useRouter();
  const pathname = usePathname();
  const busca = useSearchParams();
  // `--altura-das-abas`: o que gruda DEBAIXO da barra (ex.: o cabeçalho de grupo da aba Renovações) lê a altura REAL
  // dela, medida — muda com a fonte, o zoom e a quebra de linha, e nenhum número fica escrito em duas telas.
  const raiz = useRef<HTMLDivElement>(null);
  const barra = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = barra.current;
    const alvo = raiz.current;
    if (!el || !alvo || typeof ResizeObserver === 'undefined') return;
    const medir = () => alvo.style.setProperty('--altura-das-abas', `${Math.ceil(el.getBoundingClientRect().height)}px`);
    medir();
    const obs = new ResizeObserver(medir);
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  function trocar(id: string) {
    const p = new URLSearchParams(busca?.toString() ?? '');
    p.set('aba', id);
    // o detalhe de um item (`item=`) é da aba que o abriu
    if (id !== abaAtual) p.delete('item');
    router.push(`${pathname}?${p.toString()}`, { scroll: false });
  }

  return (
    <Tabs ref={raiz} value={abaAtual} onValueChange={trocar} className="mt-6"
      style={{ '--altura-das-abas': ALTURA_INICIAL_DAS_ABAS } as CSSProperties}>
      <div ref={barra} className="sticky top-0 z-10 -mx-4 border-b border-border bg-background/95 px-4 sm:-mx-6 sm:px-6 sm:backdrop-blur">
        <TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto rounded-none bg-transparent p-0">
          {abas.map((a) => (
            <TabsTrigger
              key={a.id}
              value={a.id}
              data-aba={a.id}
              className={cn(
                'relative h-11 shrink-0 rounded-none border-b-2 border-transparent px-3 text-sm font-medium text-muted-foreground shadow-none',
                'data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none',
              )}
            >
              {a.rotulo}
              {marcadas.includes(a.id) && (
                <span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-warning" aria-label="falta um passo" />
              )}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>

      {abas.map((a) => (
        <TabsContent key={a.id} value={a.id} className="mt-0 pt-2 focus-visible:ring-offset-0">
          {a.componente ? (
            <div className="pt-6">
              <AbaCarregada componente={a.componente} item={item} aba={a.id} />
            </div>
          ) : (
            conteudo[a.id] ?? null
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}

export default AbasDoAplicativo;
