// SPEC-139 · L2 — o leitor PURO da aba Cobranças (o que saiu): período, máscara do segurado e situação em português.
// Sem rede e sem banco: a rota (`route.ts`, ao lado) lê `billing_sent_log` e passa cada linha por aqui. Testado em
// `scripts/a-cobranca-na-casca.test.mjs`.

/** Os períodos que a tela oferece, em dias. Qualquer outro valor cai no padrão — nunca em "tudo". */
export const PERIODOS = [7, 30, 90] as const;
export const PERIODO_PADRAO = 30;
/** Quantas linhas a tela recebe no máximo (a mais recente primeiro). */
export const LIMITE_DE_LINHAS = 500;

export function periodoValido(bruto: string | null | undefined): number {
  const n = Number(bruto);
  return (PERIODOS as readonly number[]).includes(n) ? n : PERIODO_PADRAO;
}

/** O instante a partir do qual se lê (ISO), contado do relógio recebido — o teste passa o relógio. */
export function desdeDoPeriodo(dias: number, agora: Date): string {
  return new Date(agora.getTime() - dias * 86_400_000).toISOString();
}

/** Partículas que não viram inicial ("Fulana de Tal" → "Fulana T."). */
const PARTICULAS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'di', 'du']);

/**
 * O segurado MASCARADO: o primeiro nome e as iniciais do resto ("Ana Maria Ribeiro" → "Ana M. R."). É o bastante para
 * a corretora reconhecer a linha sem que a tela exiba o nome inteiro (CLAUDE.md §7). `null` = sem nome no portal.
 */
export function mascararNome(nome: string | null | undefined): string | null {
  const partes = String(nome || '').trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return null;
  const [primeiro, ...resto] = partes;
  const iniciais = resto
    .filter((p) => !PARTICULAS.has(p.toLowerCase()))
    .map((p) => `${p.charAt(0).toUpperCase()}.`);
  return [primeiro, ...iniciais].join(' ');
}

/**
 * O nome que a corretora lê NA TELA no lugar da chave do portal — nome próprio, capitalizado, a mesma grafia que o
 * Configurar mostra ("Allianz", nunca "ALLIANZ" numa lista e "Allianz" na outra: juiz de design 139, Cobranças §2).
 * A lista "O que saiu" e a fila "Precisa de você" usam ESTA função. ⚠️ A MENSAGEM ao segurado é outra coisa: ela usa
 * o `NOME_DA_SEGURADORA` do motor (`billing_collection.py`, em maiúsculas) e não muda aqui.
 * Portal sem entrada: o prefixo da chave com a 1ª letra maiúscula (siglas de até 3 letras inteiras em maiúsculas) —
 * nunca a palavra genérica "seguradora", que parece defeito para quem lê.
 */
const NOME_DA_SEGURADORA: Record<string, string> = {
  allianz_corretor: 'Allianz',
  hdi_corretor: 'HDI Seguros',
  porto_corretor: 'Porto Seguro',
  yelum_corretor: 'Yelum',
  tokiomarine_corretor: 'Tokio Marine',
  bradesco_corretor: 'Bradesco Seguros',
  mapfre_corretor: 'Mapfre',
  azul_corretor: 'Azul Seguros',
  alfa_corretor: 'Alfa Seguradora',
  sulamerica_corretor: 'SulAmérica',
  sompo_corretor: 'Sompo Seguros',
  suhai_corretor: 'Suhai',
  sura_corretor: 'Sura',
  zurich_corretor: 'Zurich',
  segurosunimed_corretor: 'Seguros Unimed',
};

export function nomeDaSeguradora(portalKey: string | null | undefined): string {
  const chave = String(portalKey || '').trim().toLowerCase();
  if (!chave) return 'Seguradora não identificada';
  if (NOME_DA_SEGURADORA[chave]) return NOME_DA_SEGURADORA[chave];
  const base = chave.endsWith('_corretor') ? chave.slice(0, -'_corretor'.length) : chave;
  return base.split('_').filter(Boolean)
    .map((p) => (p.length <= 3 ? p.toUpperCase() : p.charAt(0).toUpperCase() + p.slice(1)))
    .join(' ');
}

export type TomDaSituacao = 'success' | 'warning' | 'neutral';

/**
 * O estado do ledger em português (📊 os estados do COMMENT de `billing_sent_log.status`, migration 20260907_01).
 * "Enviada" quer dizer ACEITA pelo WhatsApp — o canal não diz se o cliente leu, e a tela não promete isso.
 */
export function situacaoDaLinha(status: string | null | undefined, encaminhadoEm: string | null | undefined): { texto: string; tom: TomDaSituacao } {
  switch (String(status || '')) {
    case 'aceito_pelo_canal':
    case 'entregue':
      return { texto: 'Enviada', tom: 'success' };
    case 'entregue_equipe':
      return encaminhadoEm
        ? { texto: 'Encaminhada ao cliente pela equipe', tom: 'success' }
        : { texto: 'Com a equipe, falta encaminhar', tom: 'warning' };
    case 'parcial':
      return { texto: 'Texto foi, boleto não', tom: 'warning' };
    case 'incerto':
      return { texto: 'Não se sabe se saiu', tom: 'warning' };
    case 'falhou':
      return { texto: 'Não saiu', tom: 'warning' };
    case 'adiado':
      return { texto: 'Adiada para a próxima execução', tom: 'neutral' };
    case 'liberado':
      return { texto: 'Liberada para reenviar', tom: 'neutral' };
    case 'suprimido':
      return { texto: 'O cliente pediu para não receber', tom: 'neutral' };
    case 'contestado':
      return { texto: 'O cliente respondeu', tom: 'warning' };
    case 'reservado':
      return { texto: 'Saindo agora', tom: 'neutral' };
    default:
      return { texto: 'Registrada', tom: 'neutral' };
  }
}

/**
 * Uma linha do ledger como a rota lê (só as colunas que a tela pode ver: nada de `to_phone`). `canario` é LIDO para
 * decidir o destino e NUNCA devolvido à tela (o canário manda para um número da lista interna, não ao segurado).
 */
export interface LinhaDoLedger {
  id: string;
  status: string | null;
  send_mode: string | null;
  modalidade: string | null;
  portal_key: string | null;
  recibo: string | null;
  cliente_nome: string | null;
  to_last4: string | null;
  sent_at: string | null;
  created_at: string | null;
  encaminhado_ao_cliente_em: string | null;
  canario?: boolean | null;
}

/**
 * PARA QUEM a mensagem foi (conserto A da 139 — o juiz B2b e o red team B1): o ledger grava `send_mode='real'` também
 * quando o pacote foi à ATENDENTE (`modalidade='equipe'`) e no canário (`canario=true`, número da lista interna).
 * Só `cliente`, real e fora do canário chegou ao SEGURADO.
 */
export type DestinoDaCobranca = 'segurado' | 'equipe' | 'teste' | 'outro';

export function destinoDaLinha(l: Pick<LinhaDoLedger, 'send_mode' | 'modalidade' | 'canario'>): DestinoDaCobranca {
  if (l.send_mode === 'test' || l.canario === true) return 'teste';
  if (l.modalidade === 'equipe') return 'equipe';
  if (l.modalidade === 'cliente') return 'segurado';
  return 'outro';
}

/**
 * O que a tela recebe por linha. 🔴 CLAUDE.md §12.1: o campo se chama `recibo` porque guarda o RECIBO do portal — o
 * nome antigo (`parcela`) mentia: o motor trata `{numero_parcela}` (ex.: 3/12) e `{recibo}` como coisas diferentes, e
 * o ledger não tem número de parcela.
 */
export interface CobrancaQueSaiu {
  id: string;
  quando: string;
  segurado: string | null;
  seguradora: string;
  recibo: string | null;
  situacao: string;
  tom: TomDaSituacao;
  teste: boolean;
  destino: DestinoDaCobranca;
  para_final: string | null;
}

export function paraATela(l: LinhaDoLedger): CobrancaQueSaiu {
  const s = situacaoDaLinha(l.status, l.encaminhado_ao_cliente_em);
  const destino = destinoDaLinha(l);
  return {
    id: String(l.id),
    quando: String(l.sent_at || l.created_at || ''),
    segurado: mascararNome(l.cliente_nome),
    seguradora: nomeDaSeguradora(l.portal_key),
    recibo: l.recibo ? String(l.recibo) : null,
    situacao: s.texto,
    tom: s.tom,
    teste: destino === 'teste',
    destino,
    para_final: l.to_last4 ? String(l.to_last4).slice(-4) : null,
  };
}

/**
 * A frase da contagem de "O que saiu". "N a segurados" conta SÓ o que chegou ao segurado (`destino === 'segurado'`):
 * o pacote da equipe, o canário e o teste são ditos pelo nome. Pura — o teste chama ESTA função, e a aba também.
 */
export function resumoDoQueSaiu(itens: Pick<CobrancaQueSaiu, 'destino'>[], periodo: number | string): string {
  const total = itens.length;
  if (total === 0) return `Nos últimos ${periodo} dias.`;
  const conta = (d: DestinoDaCobranca) => itens.filter((c) => c.destino === d).length;
  const segurados = conta('segurado');
  const base = `${total === 1 ? '1 cobrança' : `${total} cobranças`} nos últimos ${periodo} dias`;
  if (segurados === total) return `${base}, ${total === 1 ? 'ao segurado' : 'todas a segurados'}.`;
  const partes = [segurados === 1 ? '1 a segurado' : `${segurados} a segurados`];
  const equipe = conta('equipe');
  const teste = conta('teste');
  const outro = conta('outro');
  if (equipe) partes.push(`${equipe} à equipe`);
  if (teste) partes.push(`${teste} em teste`);
  if (outro) partes.push(`${outro} sem destino identificado`);
  return `${base} · ${partes.join(', ')}.`;
}
