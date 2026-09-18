'use client';

// SPEC-EXTRA-001.5 · BLOCO D ② — a fila da LINHA (não a do documento).
//
// 🔴 O TRECHO VEM DA FONTE, NA HORA. A base guarda o endereço da frase (documento
// e página), não uma cópia dela. Guardar a cópia daria a pior tela possível: a
// que mostra à pessoa um texto que o documento já não tem — e colhe a assinatura
// dela nisso.
//
// ⚠️ Publicar exige ler; rejeitar exige MOTIVO — uma fila em que se recusa sem
// dizer por quê é uma fila que nunca melhora: o extrator repete o mesmo erro e a
// pessoa recusa à mão, para sempre.

import { useState } from 'react';
import { humanizarRamo, humanizarSeguradora } from './CoberturaDePlanos';

type Item = {
  id: string; insurer_key: string; ramo: string; produto: string; plano: string; nivel: number;
  plano_curadoria: string; servico: string; coberto: string; limite_valor: number | null; limite_unidade: string | null;
  limite_texto: string | null; carencia_dias: number | null; condicao: string | null;
  pagina: number | null; plano_pagina: number | null; vigencia_inicio: string | null;
  texto_da_pagina: string | null; termos_do_servico: string[]; conferido_na_proposta: boolean | null;
  motivo_da_fonte?: string;
};

/** Grifa na página os termos do serviço — para o olho achar a frase sem ler
 *  tudo. 🔴 Os termos vêm do vocabulário versionado (o endpoint os manda);
 *  escrever uma segunda lista aqui faria a tela grifar uma coisa e o extrator
 *  procurar outra. */
function comTermosGrifados(texto: string, termos: string[]) {
  const limpos = (termos || []).filter((t) => t && t.length >= 4)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!limpos.length) return texto;
  const partes = texto.split(new RegExp(`(${limpos.join('|')})`, 'gi'));
  return partes.map((p, i) => (
    limpos.some((t) => new RegExp(`^${t}$`, 'i').test(p))
      ? <mark key={i} className="bg-amber-200/60 text-foreground">{p}</mark>
      : <span key={i}>{p}</span>
  ));
}

const SERVICO: Record<string, string> = {
  guincho: 'guincho', carro_reserva: 'carro reserva', chaveiro: 'chaveiro',
  chaveiro_residencial: 'chaveiro residencial', vidros: 'vidros', eletricista: 'eletricista',
  encanador: 'encanador', hidraulica_encanador: 'hidráulica/encanador', hospedagem: 'hospedagem',
  taxi: 'táxi', borracheiro: 'borracheiro', pane_seca: 'pane seca',
  troca_de_pneu: 'troca de pneu', bateria: 'bateria', granizo: 'granizo', alagamento: 'alagamento',
};

function oQueFoiProposto(i: Item): string {
  const nome = SERVICO[i.servico] || i.servico.replace(/_/g, ' ');
  const limite = i.limite_texto
    || (i.limite_valor != null && i.limite_unidade ? `${i.limite_valor} ${i.limite_unidade}` : '');
  if (i.coberto === 'nao') return `${nome}: NÃO está incluído`;
  const base = i.coberto === 'condicionado' ? `${nome}: incluído COM condição` : `${nome}: incluído`;
  return base + (limite ? ` — ${limite}` : '') + (i.carencia_dias ? ` (carência de ${i.carencia_dias} dias)` : '');
}

export function FilaDeCuradoria({ itens, onMudou }: { itens: Item[]; onMudou: () => void }) {
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);

  const agir = async (id: string, acao: 'publicar' | 'rejeitar') => {
    if (ocupado) return;
    if (acao === 'rejeitar' && !(motivos[id] || '').trim()) {
      setErro('Para recusar, escreva o motivo — é ele que faz a próxima proposta vir melhor.');
      return;
    }
    setOcupado(id);
    setErro(null);
    try {
      const r = await fetch('/api/dashboard/knowledge/planos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, acao, motivo: motivos[id] || '' }),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok || !j?.ok) setErro('Não consegui registrar sua decisão. Tente de novo.');
      else onMudou();
    } catch {
      setErro('Não consegui registrar sua decisão. Tente de novo.');
    } finally {
      setOcupado(null);
    }
  };

  if (!itens.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-sm font-medium text-foreground">Nada esperando revisão</p>
        <p className="mt-1 text-[11px] text-faint">
          Quando lermos novas condições gerais, cada item aparece aqui com a frase e a página ao
          lado, para você confirmar antes de o assistente passar a dizer isso a um cliente.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div>
        <p className="text-sm font-medium text-foreground">Esperando sua revisão ({itens.length})</p>
        <p className="mt-1 text-[11px] text-faint">
          Nada disto chega a um cliente antes de você aprovar. A frase abaixo foi lida agora do
          documento — confira se ela diz o que a linha afirma.
        </p>
      </div>
      {erro && <p className="text-[11px] text-red-600">{erro}</p>}

      <div className="divide-y divide-border">
        {itens.map((i) => (
          <div key={i.id} className="py-3 space-y-2">
            <p className="text-xs text-muted-foreground">
              {humanizarSeguradora(i.insurer_key)} · {humanizarRamo(i.ramo)} · {i.produto}
              {i.plano ? ` · plano ${i.plano}` : ''}{i.nivel ? ` (nível ${i.nivel})` : ''}
              {i.plano_pagina ? ` · plano na p. ${i.plano_pagina}` : ''}
            </p>
            {/* 🔴 Aprovar esta linha também libera o PLANO acima dela — sem o
                plano liberado, nada do que se aprova chega ao cliente. Quem
                clica precisa saber que está aprovando os dois. */}
            {i.plano_curadoria === 'proposto' && (
              <p className="text-[10px] text-amber-600">
                Ao aprovar, o plano <strong>{i.plano}</strong>
                {i.nivel ? ` (nível ${i.nivel})` : ''} também passa a valer
                {i.plano_pagina ? ` — está na página ${i.plano_pagina} do documento` : ''}.
              </p>
            )}
            <p className="text-sm text-foreground">{oQueFoiProposto(i)}</p>
            {i.condicao && <p className="text-[11px] text-muted-foreground">Condição: {i.condicao}</p>}

            <div className="rounded-md border border-border bg-background p-2">
              <p className="text-[10px] uppercase tracking-wide text-faint">
                {i.pagina ? `Condições gerais · página ${i.pagina}` : 'Sem página registrada'}
              </p>
              {i.texto_da_pagina ? (
                <p className="mt-1 max-h-64 overflow-y-auto whitespace-pre-line text-[11px] leading-snug text-muted-foreground">
                  {comTermosGrifados(i.texto_da_pagina, i.termos_do_servico)}
                </p>
              ) : (
                <p className="mt-1 text-[11px] text-amber-600">
                  Não consegui abrir o documento agora para mostrar a frase. Isso não quer dizer que
                  a linha esteja errada — quer dizer que não dá para conferir neste momento.
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => agir(i.id, 'publicar')}
                disabled={ocupado === i.id || !i.texto_da_pagina}
                className="h-7 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:opacity-40"
              >
                Confere — pode usar
              </button>
              <input
                value={motivos[i.id] || ''}
                onChange={(e) => setMotivos((m) => ({ ...m, [i.id]: e.target.value }))}
                placeholder="motivo da recusa"
                className="h-7 flex-1 min-w-[160px] rounded-md border border-border bg-background px-2 text-xs text-foreground"
              />
              <button
                onClick={() => agir(i.id, 'rejeitar')}
                disabled={ocupado === i.id}
                className="h-7 rounded-md border border-border px-3 text-xs text-muted-foreground disabled:opacity-40"
              >
                Não confere
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
