// SPEC-132-B · B3 — o vocabulário da aba Cotações (tipos, estados e formatos).
// O ESTADO de cada cotação (Calculando · Pronta · Sem resposta) vem PRONTO do backend (`backend/app/api/cotacoes.py`):
// a tela não deduz nada — ela só mostra.

import type { TomDoSelo } from '@/components/aplicativos/casca/Selo';

export type EstadoDaCotacao = 'calculando' | 'pronta' | 'sem_resposta';

export interface Parcela {
  vezes: number;
  valor: number;
}

export interface MelhorOferta {
  seguradora: string | null;
  a_vista: number;
  parcela: Parcela | null;
  franquia: number | null;
  opcao: string | null;
}

export interface Cotacao {
  id: string;
  cliente: string | null;
  documento: string | null;
  risco: string | null;
  placa: string | null;
  ramo: number | null;
  ramo_rotulo: string;
  quando: string | null;
  quem_pediu: { user_id: string; nome: string; sou_eu: boolean } | null;
  estado: EstadoDaCotacao;
  estado_rotulo: string;
  seguradoras: number;
  melhor: MelhorOferta | null;
  conta: { onde: 'pessoa' | 'corretora' | null; frase: string | null };
  pode_enviar: boolean;
  tem_apresentacao: boolean;
  da_conversa: boolean;
}

export interface OpcaoDaCotacao {
  opcao: string;
  rotulo: string;
  status: string;
  status_rotulo: string;
  menor_preco: number | null;
  seguradora_do_menor: string | null;
  parcela_do_menor: Parcela | null;
  franquia_do_menor: number | null;
  seguradoras: number;
  agger_url: string | null;
}

export interface DetalheDaCotacao extends Cotacao {
  opcoes: OpcaoDaCotacao[];
  agger_url: string | null;
  proximo_passo: string;
}

export interface ListaDeCotacoes {
  itens: Cotacao[];
  total: number;
  contagens: Record<EstadoDaCotacao, number>;
  escopo: 'minhas' | 'todas';
  eu: string;
  tem_alguma: boolean;
  truncou: boolean;
  dias: number;
}

export const FILTROS_DE_ESTADO: { id: EstadoDaCotacao; rotulo: string; vazio: string }[] = [
  { id: 'pronta', rotulo: 'Prontas', vazio: 'Nenhuma cotação pronta agora.' },
  { id: 'calculando', rotulo: 'Calculando', vazio: 'Nenhuma cotação calculando agora.' },
  { id: 'sem_resposta', rotulo: 'Sem resposta', vazio: 'Nenhuma cotação ficou sem resposta.' },
];

export function tomDoEstado(estado: EstadoDaCotacao): TomDoSelo {
  if (estado === 'pronta') return 'success';
  if (estado === 'calculando') return 'info';
  return 'warning';
}

const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
const BRL_CENTAVOS = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

export function reais(v: number | null | undefined): string {
  return typeof v === 'number' && Number.isFinite(v) ? BRL.format(v) : '—';
}

/** "10x de R$ 312,40" — a parcela leva centavos (é o número que o cliente compara). */
export function parcela(p: Parcela | null | undefined): string | null {
  if (!p || !Number.isFinite(p.valor) || p.vezes < 1) return null;
  return p.vezes === 1 ? `à vista ${BRL_CENTAVOS.format(p.valor)}` : `${p.vezes}x de ${BRL_CENTAVOS.format(p.valor)}`;
}

/** "hoje 14:32" · "ontem 09:10" · "12/10 16:05" — quando a cotação foi pedida, no relógio de quem olha. */
export function quando(iso: string | null | undefined, agora: Date = new Date()): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const hora = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const dia = (x: Date) => `${x.getFullYear()}-${x.getMonth()}-${x.getDate()}`;
  const ontem = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate() - 1);
  if (dia(d) === dia(agora)) return `hoje ${hora}`;
  if (dia(d) === dia(ontem)) return `ontem ${hora}`;
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} ${hora}`;
}

export function nomeDoCliente(c: Pick<Cotacao, 'cliente'>): string {
  return c.cliente || 'Cliente sem nome';
}
