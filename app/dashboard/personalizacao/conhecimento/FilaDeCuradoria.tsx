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
//
// 🔴 SPEC-EXTRA-001.5.1 (D2, D3, D9) — TRÊS ESTADOS, NÃO DOIS.
//
// Até 19/09/2026 havia dois: lista, e "Nada esperando revisão". Falha de rede,
// backend em 500 e fila genuinamente vazia caíam todos no segundo — e 📊 o
// backend respondia 500 desde que a 001.5 subiu. A tela dizia "nada esperando"
// para 73 linhas esperando.
//
// ```
// ERRO    "Não consegui carregar a fila agora: <motivo>" + tentar de novo
// VAZIO   "Nada esperando revisão"  <- SÓ quando a chamada deu certo e veio 0
// LISTA   "Esperando sua revisão — mostrando N de M"
// ```
//
// E o botão que morre por falta da página (D9) agora diz POR QUÊ e oferece
// tentar de novo: 📊 `disabled={… || !i.texto_da_pagina}` virava um botão cinza
// sem explicação sempre que o MinIO falhava.

import { useState } from 'react';
import { humanizarRamo, humanizarSeguradora } from './CoberturaDePlanos';

type Item = {
  id: string; insurer_key: string; ramo: string; produto: string; plano: string; nivel: number;
  plano_curadoria: string; servico: string; coberto: string; limite_valor: number | null; limite_unidade: string | null;
  limite_texto: string | null; carencia_dias: number | null; condicao: string | null;
  pagina: number | null; plano_pagina: number | null; vigencia_inicio: string | null;
  texto_da_pagina: string | null; termos_do_servico: string[];
  motivo_da_fonte?: string;
};

/** O que a rota devolve. 🔴 `ok` é obrigatório: é ele que separa "deu erro" de
 *  "está vazia" — as duas coisas que a tela confundia. `total` é a base inteira;
 *  `mostrando` é o que coube nesta página. */
type Fila = {
  ok?: boolean; itens?: Item[]; total?: number; mostrando?: number; limite?: number;
  error?: string; status?: number;
};

/** O motivo em português, sem nome de tabela, coluna nem código HTTP solto.
 *  ⚠️ O corpo do erro do backend NUNCA chega aqui (pode ter traceback): o que
 *  viaja é um código curto, e é aqui que ele vira frase de gente. */
function motivoHumano(f: Fila): string {
  if (f.error === 'indisponivel') return 'o serviço de conhecimento não respondeu';
  if (f.error === 'resposta_ilegivel') return 'o serviço respondeu algo que não consegui ler';
  if (f.error === 'servico_com_erro') return 'o serviço de conhecimento respondeu com erro';
  return 'não consegui falar com o serviço de conhecimento';
}

/** Por que a página não veio — para o botão cinza parar de ser um mistério. */
function motivoDaFonte(codigo?: string): string {
  if (codigo === 'fonte_ausente') return 'o documento original não está arquivado';
  if (codigo === 'documento_sem_versao') return 'este documento não tem versão arquivada';
  if (codigo === 'minio_indisponivel') return 'o arquivo do documento não respondeu agora';
  if (codigo === 'sem_extrator_de_pdf') return 'não consigo abrir PDF neste servidor';
  if (codigo === 'sem_pagina_registrada') return 'esta linha não registrou a página';
  if (codigo === 'pagina_fora_do_documento') return 'a página indicada não existe no documento';
  if (codigo === 'pagina_ilegivel') return 'a página indicada não é um número que eu entenda';
  if (codigo && codigo.startsWith('pdf_ilegivel')) return 'o PDF não abriu';
  return 'não consegui abrir o documento agora';
}

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

export function FilaDeCuradoria({ fila, onMudou }: { fila: Fila; onMudou: () => void }) {
  const itens: Item[] = Array.isArray(fila?.itens) ? fila.itens : [];
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

  // ① ERRO — a chamada não deu certo. ⛔ NUNCA cair no estado vazio por aqui.
  if (fila?.ok !== true) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-sm font-medium text-foreground">
          Não consegui carregar a fila agora: {motivoHumano(fila || {})}.
        </p>
        <p className="mt-1 text-[11px] text-faint">
          Isso não quer dizer que não haja nada esperando revisão — quer dizer que não deu para
          perguntar neste momento.
        </p>
        <button
          type="button"
          onClick={onMudou}
          className="mt-2 h-7 rounded-md border border-border px-3 text-xs text-foreground"
        >
          Tentar de novo
        </button>
      </div>
    );
  }

  // ② VAZIO honesto — a chamada deu certo e não veio nada.
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

  // ③ LISTA — e o cabeçalho diz quanto do todo está na tela (D3).
  const total = typeof fila.total === 'number' ? fila.total : itens.length;
  const mostrando = typeof fila.mostrando === 'number' ? fila.mostrando : itens.length;

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div>
        <p className="text-sm font-medium text-foreground">
          Esperando sua revisão{' '}
          {total > mostrando ? `— mostrando ${mostrando} de ${total}` : `(${total})`}
        </p>
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
                  Não dá para mostrar a frase: {motivoDaFonte(i.motivo_da_fonte)}. Isso não quer
                  dizer que a linha esteja errada — quer dizer que não dá para conferir neste
                  momento.
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
              {/* 🔴 D9 — o botão cinza EXPLICA. Um botão que não clica e não diz
                  por quê ensina a pessoa a desconfiar da tela inteira; e o que
                  falta aqui costuma ser passageiro (o arquivo não respondeu),
                  então "tentar de novo" é a ação certa, não "desista". */}
              {!i.texto_da_pagina && (
                <span className="text-[11px] text-amber-600">
                  Só dá para aprovar depois de ler a página — {motivoDaFonte(i.motivo_da_fonte)}.
                  <button
                    type="button"
                    onClick={onMudou}
                    className="ml-2 underline underline-offset-2"
                  >
                    Tentar de novo
                  </button>
                </span>
              )}
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
