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
 * O nome que a corretora lê no lugar da chave do portal — o mesmo fallback do motor (`NOME_DA_SEGURADORA` de
 * `billing_collection.py`): portal sem entrada vira o prefixo em maiúsculas, nunca a palavra genérica "seguradora".
 */
const NOME_DA_SEGURADORA: Record<string, string> = {
  allianz_corretor: 'ALLIANZ',
  hdi_corretor: 'HDI SEGUROS',
  porto_corretor: 'PORTO SEGURO',
  yelum_corretor: 'YELUM',
  tokiomarine_corretor: 'TOKIO MARINE',
  bradesco_corretor: 'BRADESCO SEGUROS',
  mapfre_corretor: 'MAPFRE',
  azul_corretor: 'AZUL SEGUROS',
  alfa_corretor: 'ALFA SEGURADORA',
  sulamerica_corretor: 'SULAMERICA',
  sompo_corretor: 'SOMPO SEGUROS',
  suhai_corretor: 'SUHAI',
  sura_corretor: 'SURA',
  zurich_corretor: 'ZURICH',
  segurosunimed_corretor: 'SEGUROS UNIMED',
};

export function nomeDaSeguradora(portalKey: string | null | undefined): string {
  const chave = String(portalKey || '').trim().toLowerCase();
  if (!chave) return 'Seguradora não identificada';
  if (NOME_DA_SEGURADORA[chave]) return NOME_DA_SEGURADORA[chave];
  if (chave.endsWith('_corretor')) return chave.slice(0, -'_corretor'.length).replace(/_/g, ' ').toUpperCase();
  return chave.toUpperCase();
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

/** Uma linha do ledger como a rota lê (só as colunas que a tela pode ver: nada de `to_phone`). */
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
}

/** O que a tela recebe por linha. */
export interface CobrancaQueSaiu {
  id: string;
  quando: string;
  segurado: string | null;
  seguradora: string;
  parcela: string | null;
  situacao: string;
  tom: TomDaSituacao;
  teste: boolean;
  para_final: string | null;
}

export function paraATela(l: LinhaDoLedger): CobrancaQueSaiu {
  const s = situacaoDaLinha(l.status, l.encaminhado_ao_cliente_em);
  return {
    id: String(l.id),
    quando: String(l.sent_at || l.created_at || ''),
    segurado: mascararNome(l.cliente_nome),
    seguradora: nomeDaSeguradora(l.portal_key),
    parcela: l.recibo ? String(l.recibo) : null,
    situacao: s.texto,
    tom: s.tom,
    teste: l.send_mode === 'test',
    para_final: l.to_last4 ? String(l.to_last4).slice(-4) : null,
  };
}
