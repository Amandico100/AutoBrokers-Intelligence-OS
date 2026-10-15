'use client';

// SPEC-139 · L2 — o Início da Cobrança, para quando a casca carrega a aba por import dinâmico (`cobranca-feita/AbaInicio`).
//
// Não é um Início novo: é o MESMO da casca (`casca/AbaInicio` — o que é → o que faz → o que a corretora ganha → Como
// começar → atividade recente → dúvidas), com os dois dados que a casca só tem no servidor:
//   · os passos do "Como começar" — de `passosDoComoComecar` (o portal conectado · o WhatsApp de envio · a rotina
//     configurada · ligar, com "N de M prontos"); para a Cobrança eles saem só do `item`, sem prontidão;
//   · a atividade recente — as 3 últimas execuções das rotinas DESTE aplicativo, da rota que o painel já usa
//     (`/api/dashboard/rotinas?auxiliar=…`, filtrada pela corretora da sessão), nunca de `last_run_at`.
// Se a casca seguir desenhando o Início (componente `null` no catálogo), este arquivo simplesmente não é carregado.

import { useEffect, useMemo, useState } from 'react';

import { AbaInicio as InicioDaCasca } from '@/components/aplicativos/casca/AbaInicio';
import { passosDoComoComecar, type AtividadeDoAplicativo, type PropsDaAba } from '@/lib/auxiliaries/catalog';

/** O mesmo texto da atividade da casca (`atividadeRecente` em lib/auxiliaries/catalog.ts). */
function atividadeDaExecucao(x: { started_at: string; status: string }): AtividadeDoAplicativo {
  return {
    quando: String(x.started_at),
    texto: x.status === 'ok' ? 'Execução concluída'
      : x.status === 'running' ? 'Execução em andamento'
      : x.status === 'error' ? 'Execução não concluiu'
      : 'Execução registrada',
    tom: x.status === 'ok' ? 'success' : x.status === 'error' ? 'warning' : 'neutral',
  };
}

export function AbaInicio({ item }: PropsDaAba) {
  const [atividade, setAtividade] = useState<AtividadeDoAplicativo[]>([]);
  // a Cobrança usa os passos genéricos: as conexões dela, a configuração e o ligar — nenhum lê a prontidão
  const passos = useMemo(() => passosDoComoComecar(item, { prontidao: null, meuAgger: null }), [item]);

  useEffect(() => {
    if (!item.instalado) return;
    let vivo = true;
    (async () => {
      try {
        const res = await fetch(`/api/dashboard/rotinas?auxiliar=${encodeURIComponent(item.slug)}`, { cache: 'no-store' });
        const j = await res.json().catch(() => ({}));
        if (!vivo || !res.ok) return;
        const runs = ((j.runs || []) as { started_at: string; status: string }[]).slice(0, 3);
        setAtividade(runs.map(atividadeDaExecucao));
      } catch {
        /* sem atividade: a casca diz "Ainda não rodou nenhuma vez" só quando é verdade que não há linha */
      }
    })();
    return () => { vivo = false; };
  }, [item.instalado, item.slug]);

  return (
    <InicioDaCasca item={item} passos={passos} atividade={atividade}
      hrefDuvidas={`/dashboard/auxiliares/${item.slug}?aba=duvidas`} />
  );
}

export default AbaInicio;
