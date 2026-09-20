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
// 🔴 SPEC-EXTRA-001.5.1 (D5) — A PÁGINA CHEGA QUANDO A LINHA ABRE.
//
// 📊 A fila vinha com o texto das 60 páginas dentro dela, e montar isso custava
// 65,3 s em produção (24 PDFs baixados do MinIO em série) para mostrar a
// primeira linha. Agora a lista chega em segundos e cada linha busca a SUA
// página quando a pessoa a abre — que é como ela revisa: uma de cada vez.
//
// ⚠️ E a regra que NÃO mudou: só se aprova depois de ler a página. O botão
// continua travado enquanto o texto não estiver na tela (D9 explica por quê
// quando ele não vem), e agora também quando o PLANO PAI está em `rascunho`
// (D7): 📊 4 das 73 linhas estavam nesse caso, e o clique falhava calado.

import { useState } from 'react';
import { humanizarRamo, humanizarSeguradora } from './CoberturaDePlanos';

type Item = {
  id: string; insurer_key: string; ramo: string; produto: string; plano: string; nivel: number;
  plano_curadoria: string; servico: string; coberto: string; limite_valor: number | null; limite_unidade: string | null;
  limite_texto: string | null; carencia_dias: number | null; condicao: string | null;
  pagina: number | null; plano_pagina: number | null; vigencia_inicio: string | null;
  termos_do_servico?: string[];
  /** 🔴 D7 — a fila diz se a linha PODE ser publicada, e por que não. */
  pode_publicar?: boolean;
  motivo_de_nao_publicar?: string | null;
  /** 🔴 D8 — o motivo do rascunho, gravado no banco desde 19/09/2026. */
  motivo_do_rascunho?: string | null;
  plano_motivo_do_rascunho?: string | null;
  /** 🔴 EXTRA-001.5.2 (F) — o parecer automático contra a PÁGINA, escrito antes
   *  de a linha chegar aqui. `null` = ainda não conferida (fila antiga). */
  veredito_do_conferente?: 'CONFERE' | 'DIVERGE' | 'NAO_CONSEGUI' | null;
  conferencia?: { campos?: Record<string, string>; motivos?: string[]; pagina?: number | null } | null;
  conferido_em?: string | null;
  /** 🔴 EXTRA-001.5.2 (B) — de qual cláusula a linha saiu. */
  caminho_da_clausula?: string | null;
};

/** O que a rota devolve. 🔴 `ok` é obrigatório: é ele que separa "deu erro" de
 *  "está vazia" — as duas coisas que a tela confundia. `total` é a base inteira;
 *  `mostrando` é o que coube nesta página. */
type Fila = {
  ok?: boolean; itens?: Item[]; total?: number; mostrando?: number; limite?: number;
  error?: string; status?: number;
};

/** A página de UMA linha, buscada quando ela abre. `carregando` é um estado de
 *  verdade, e não a ausência dos outros: sem ele a linha recém-aberta fica
 *  idêntica a uma linha cuja página não veio, e a pessoa lê "não consegui"
 *  enquanto o servidor ainda está respondendo. */
type Pagina = {
  carregando?: boolean;
  ok?: boolean;
  texto_da_pagina?: string | null;
  pagina?: number | null;
  total_de_paginas?: number | null;
  termos_do_servico?: string[];
  motivo_da_fonte?: string;
  error?: string;
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
  if (codigo === 'sem_documento_registrado') return 'esta linha não registrou o documento';
  if (codigo === 'pagina_fora_do_documento') return 'a página indicada não existe no documento';
  if (codigo === 'pagina_ilegivel') return 'a página indicada não é um número que eu entenda';
  if (codigo === 'linha_inexistente') return 'esta linha não está mais na base';
  if (codigo && codigo.startsWith('pdf_ilegivel')) return 'o PDF não abriu';
  if (codigo === 'indisponivel' || codigo === 'servico_com_erro' || codigo === 'resposta_ilegivel') {
    return 'o serviço de conhecimento não respondeu agora';
  }
  return 'não consegui abrir o documento agora';
}

/** 🔴 D7 — por que esta linha não pode subir. O texto diz o que FAZER, porque
 *  a alternativa (um botão cinza) faz a pessoa clicar de novo, achar que a tela
 *  está quebrada, e ir embora. */
function motivoDeNaoPublicar(codigo?: string | null, motivoDoPlano?: string | null): string {
  const base = codigo === 'plano_pai_rascunho'
    ? 'o plano acima desta linha foi recusado, e publicar a linha sem o plano não faria o assistente responder nada'
    : codigo === 'plano_pai_ausente'
      ? 'esta linha não aponta para nenhum plano'
      : 'o plano acima desta linha ainda não está pronto para valer';
  return motivoDoPlano ? `${base} — motivo: ${motivoDoPlano}` : base;
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

/** 🔴 EXTRA-001.5.2 (F) — O SELO DO CONFERENTE, EM LINGUAGEM DE GENTE.
 *
 * 📊 19/09/2026: conferir 81 linhas à mão custou abrir 27 PDFs e 3.052 páginas,
 * e 58 delas ficaram paradas por isso. O selo é o que faz a curadoria caber num
 * dia: a pessoa lê o parecer ao lado da linha e decide.
 *
 * ⚠️ `NÃO CONSEGUI` **não** é `DIVERGE`, e por isso tem selo próprio: "o PDF não
 * abriu" e "a página não confirma" mandam a pessoa fazer coisas opostas. E o
 * selo NUNCA decide: quem publica continua sendo gente, com revisor.
 */
const SELO: Record<string, { texto: string; classe: string; explica: string }> = {
  CONFERE: {
    texto: 'a página confirma',
    classe: 'border-emerald-600/40 text-emerald-600',
    explica: 'conferi esta linha contra a página do documento e ela bate',
  },
  DIVERGE: {
    texto: 'a página não confirma',
    classe: 'border-amber-600/40 text-amber-600',
    explica: 'algo nesta linha não bate com a página — vale abrir antes de aprovar',
  },
  NAO_CONSEGUI: {
    texto: 'não consegui conferir',
    classe: 'border-border text-muted-foreground',
    explica: 'não deu para conferir esta linha contra o documento — não é o mesmo que estar errada',
  },
};

/** O campo do parecer em português. 🔴 `pagina`, `trecho`, `coberto`… são nomes
 *  de coluna; quem cura não tem por que aprendê-los. */
const CAMPO: Record<string, string> = {
  pagina: 'página', trecho: 'trecho', coberto: 'está coberto?',
  limite: 'limite', plano: 'plano', produto: 'produto',
};

function SeloDoConferente({ i }: { i: Item }) {
  const selo = i.veredito_do_conferente ? SELO[i.veredito_do_conferente] : null;
  if (!selo) return null;
  const motivos = (i.conferencia?.motivos || []).filter(Boolean);
  const divergentes = Object.entries(i.conferencia?.campos || {})
    .filter(([, estado]) => estado === 'diverge')
    .map(([campo]) => CAMPO[campo] || campo);
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2 py-[1px] text-[10px] ${selo.classe}`}>
          {selo.texto}
        </span>
        <span className="text-[10px] text-faint">{selo.explica}</span>
      </div>
      {divergentes.length > 0 && (
        <p className="text-[11px] text-muted-foreground">
          Não bate em: {divergentes.join(', ')}.
        </p>
      )}
      {motivos.map((m, n) => (
        <p key={n} className="text-[11px] text-muted-foreground">· {m}</p>
      ))}
    </div>
  );
}

export function FilaDeCuradoria({ fila, onMudou }: { fila: Fila; onMudou: () => void }) {
  const itens: Item[] = Array.isArray(fila?.itens) ? fila.itens : [];
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);
  const [abertas, setAbertas] = useState<Record<string, boolean>>({});
  const [paginas, setPaginas] = useState<Record<string, Pagina>>({});

  /** Busca a página DAQUELA linha. ⚠️ Uma chamada por linha aberta, e o
   *  resultado fica guardado: reabrir a mesma linha não pede de novo. */
  const buscarPagina = async (id: string) => {
    setPaginas((p) => ({ ...p, [id]: { carregando: true } }));
    try {
      const r = await fetch(`/api/dashboard/knowledge/planos?servico_id=${encodeURIComponent(id)}`, {
        cache: 'no-store',
      });
      const j = await r.json().catch(() => null);
      if (!r.ok || !j || typeof j !== 'object') {
        setPaginas((p) => ({ ...p, [id]: { ok: false, motivo_da_fonte: 'indisponivel' } }));
        return;
      }
      setPaginas((p) => ({ ...p, [id]: { ...j, carregando: false } }));
    } catch {
      setPaginas((p) => ({ ...p, [id]: { ok: false, motivo_da_fonte: 'indisponivel' } }));
    }
  };

  const alternar = (id: string) => {
    const vaiAbrir = !abertas[id];
    setAbertas((a) => ({ ...a, [id]: vaiAbrir }));
    if (vaiAbrir && !paginas[id]) void buscarPagina(id);
  };

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
          Nada disto chega a um cliente antes de você aprovar. Abra a linha para ler a página do
          documento — ela é lida na hora — e confira se ela diz o que a linha afirma.
        </p>
      </div>
      {erro && <p className="text-[11px] text-red-600">{erro}</p>}

      <div className="divide-y divide-border">
        {itens.map((i) => {
          const pag = paginas[i.id];
          const aberta = !!abertas[i.id];
          const leu = pag?.ok === true && !!pag.texto_da_pagina;
          // 🔴 A fila mais antiga não mandava `pode_publicar`. `!== false`
          // mantém a tela funcionando contra um backend anterior, em vez de
          // travar todos os botões por causa de um campo que não veio.
          const podePublicar = i.pode_publicar !== false;
          return (
            <div key={i.id} className="py-3 space-y-2">
              <p className="text-xs text-muted-foreground">
                {humanizarSeguradora(i.insurer_key)} · {humanizarRamo(i.ramo)} · {i.produto}
                {i.plano ? ` · plano ${i.plano}` : ''}{i.nivel ? ` (nível ${i.nivel})` : ''}
                {i.plano_pagina ? ` · plano na p. ${i.plano_pagina}` : ''}
              </p>
              {/* 🔴 Aprovar esta linha também libera o PLANO acima dela — sem o
                  plano liberado, nada do que se aprova chega ao cliente. Quem
                  clica precisa saber que está aprovando os dois. */}
              {podePublicar && i.plano_curadoria === 'proposto' && (
                <p className="text-[10px] text-amber-600">
                  Ao aprovar, o plano <strong>{i.plano}</strong>
                  {i.nivel ? ` (nível ${i.nivel})` : ''} também passa a valer
                  {i.plano_pagina ? ` — está na página ${i.plano_pagina} do documento` : ''}.
                </p>
              )}
              {/* 🔴 D7 — a linha que não sobe diz POR QUE não sobe. 📊 Eram 4 de
                  73, indistinguíveis das outras, e o clique falhava calado. */}
              {!podePublicar && (
                <p className="text-[10px] text-amber-600">
                  Esta linha não pode ser publicada agora:{' '}
                  {motivoDeNaoPublicar(i.motivo_de_nao_publicar, i.plano_motivo_do_rascunho)}.
                </p>
              )}
              <p className="text-sm text-foreground">{oQueFoiProposto(i)}</p>
              {/* 🔴 EXTRA-001.5.2 (B) — de qual cláusula esta linha saiu. É o
                  que mostra, sem abrir o PDF, que um "não" foi lido de dentro
                  da cláusula de OUTRA cobertura. */}
              {i.caminho_da_clausula && (
                <p className="text-[11px] text-faint">Lido em: {i.caminho_da_clausula}</p>
              )}
              {i.condicao && <p className="text-[11px] text-muted-foreground">Condição: {i.condicao}</p>}
              {/* 🔴 EXTRA-001.5.2 (F) — o parecer automático, ao lado da linha. */}
              <SeloDoConferente i={i} />

              <div className="rounded-md border border-border bg-background p-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[10px] uppercase tracking-wide text-faint">
                    {i.pagina ? `Condições gerais · página ${i.pagina}` : 'Sem página registrada'}
                  </p>
                  <button
                    type="button"
                    onClick={() => alternar(i.id)}
                    className="h-6 rounded-md border border-border px-2 text-[11px] text-foreground"
                  >
                    {aberta ? 'Ocultar a página' : 'Ler a página do documento'}
                  </button>
                </div>

                {aberta && pag?.carregando && (
                  <p className="mt-1 text-[11px] text-muted-foreground">carregando a página…</p>
                )}
                {aberta && !pag?.carregando && leu && (
                  <p className="mt-1 max-h-64 overflow-y-auto whitespace-pre-line text-[11px] leading-snug text-muted-foreground">
                    {comTermosGrifados(pag!.texto_da_pagina as string,
                      pag!.termos_do_servico || i.termos_do_servico || [])}
                  </p>
                )}
                {/* 🔴 D9 — a página que não vem EXPLICA, e oferece tentar de
                    novo: o que falta aqui costuma ser passageiro (o arquivo não
                    respondeu), então "desista" seria a mensagem errada. */}
                {aberta && !pag?.carregando && pag && !leu && (
                  <p className="mt-1 text-[11px] text-amber-600">
                    Não dá para mostrar a frase: {motivoDaFonte(pag.motivo_da_fonte)}. Isso não
                    quer dizer que a linha esteja errada — quer dizer que não dá para conferir
                    neste momento.
                    <button
                      type="button"
                      onClick={() => void buscarPagina(i.id)}
                      className="ml-2 underline underline-offset-2"
                    >
                      Tentar de novo
                    </button>
                  </p>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => agir(i.id, 'publicar')}
                  disabled={ocupado === i.id || !leu || !podePublicar}
                  className="h-7 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:opacity-40"
                >
                  Confere — pode usar
                </button>
                {/* ⚠️ O botão cinza nunca fica sem legenda: cada motivo tem a
                    sua, e "leia a página primeiro" é diferente de "o plano pai
                    foi recusado" — a primeira é uma ação, a segunda não é. */}
                {!podePublicar ? (
                  <span className="text-[11px] text-amber-600">
                    Não dá para aprovar enquanto o plano acima estiver recusado.
                  </span>
                ) : !leu && (
                  <span className="text-[11px] text-amber-600">
                    {aberta && pag && !pag.carregando
                      ? <>Só dá para aprovar depois de ler a página — {motivoDaFonte(pag.motivo_da_fonte)}.</>
                      : 'Abra a página acima para poder aprovar.'}
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
          );
        })}
      </div>
    </div>
  );
}
