// SPEC-131-B · G2 — o vocabulário da aba Renovações (tipos, colunas, atalhos e formatos).
// A COLUNA e os ATALHOS de cada item vêm PRONTOS do backend (`backend/app/api/renovacoes.py`): a tela não deduz
// estado nenhum — ela só mostra.

import type { StatusTone } from '@/components/patterns/StatusPill';
import type { ColunaDoQuadro } from '@/components/aplicativos/QuadroOuLista';

export interface CalculoDaOpcao {
  opcao: string;
  rotulo: string;
  status: string;
  status_rotulo: string;
  menor_preco: number | null;
  seguradora_do_menor: string | null;
  franquia_do_menor: number | null;
  seguradoras: number;
  agger_url: string | null;
}

export type Atalho = 'para_enviar_hoje' | 'precisa_de_voce' | 'vence_esta_semana' | 'enviadas';

export interface Renovacao {
  id: string;
  cliente: string | null;
  documento: string | null;
  ramo: string | null;
  ramo_rotulo: string | null;
  vence_em: string | null;
  dias_para_vencer: number | null;
  seguradora_atual: string | null;
  seguradora_nova: string | null;
  premio_atual: number | null;
  premio_novo: number | null;
  variacao_pct: number | null;
  responsavel: { user_id: string; nome: string } | null;
  dono_user_id: string | null;
  estado: string;
  estado_rotulo: string;
  coluna: string | null;
  precisa_de_voce: boolean;
  motivo: string | null;
  motivo_frase: string | null;
  calculos: CalculoDaOpcao[];
  pode_enviar: boolean;
  atalhos: Atalho[];
  atualizado_em?: string | null;
  versao?: number | null;
}

export interface DetalheDaRenovacao extends Renovacao {
  eventos: { quando: string | null; para: string | null; frase: string }[];
  proximo_passo: string;
  agger_url: string | null;
}

export interface ListaDeRenovacoes {
  itens: Renovacao[];
  total: number;
  contagens: Record<Atalho, number>;
  escopo: 'minhas' | 'todas';
  eu: string;
  hoje: string;
  ligado: boolean;
  tem_alguma: boolean;
  seguradoras: string[];
  ramos: { id: string; rotulo: string }[];
}

/** As colunas do quadro (SPEC §4): as três de todo dia e as quatro que só aparecem quando alguém chega lá. */
export const COLUNAS_DA_RENOVACAO: ColunaDoQuadro[] = [
  { id: 'vai_calcular', titulo: 'Vai calcular', descricao: 'Entrou na janela e ainda não calculou', tom: 'info' },
  { id: 'calculada', titulo: 'Calculada', descricao: 'Pronta para conferir e enviar', tom: 'success' },
  { id: 'enviada', titulo: 'Enviada', descricao: 'Saiu para o cliente', tom: 'neutral' },
  { id: 'em_negociacao', titulo: 'Em negociação', descricao: 'O cliente respondeu', tom: 'warning', esconderSeVazia: true },
  { id: 'fechada', titulo: 'Fechada', descricao: 'O cliente aceitou', tom: 'success', esconderSeVazia: true },
  {
    id: 'emitida',
    titulo: 'Emitida e registrada',
    descricao: 'Na seguradora e na InfoCap',
    tom: 'success',
    esconderSeVazia: true,
  },
  { id: 'perdida', titulo: 'Perdida', descricao: 'Não renovou, com o motivo', tom: 'neutral', esconderSeVazia: true },
];

export const ATALHOS: { id: Atalho; rotulo: string; vazio: string }[] = [
  { id: 'para_enviar_hoje', rotulo: 'Para enviar hoje', vazio: 'Nenhuma renovação pronta para enviar agora.' },
  { id: 'precisa_de_voce', rotulo: 'Precisa de você', vazio: 'Nada precisa de você agora.' },
  { id: 'vence_esta_semana', rotulo: 'Vence esta semana', vazio: 'Nenhuma renovação vence nos próximos 7 dias.' },
  { id: 'enviadas', rotulo: 'Enviadas', vazio: 'Nenhuma renovação enviada ainda.' },
];

export function tomDoEstado(r: Pick<Renovacao, 'coluna' | 'precisa_de_voce' | 'estado'>): StatusTone {
  if (r.precisa_de_voce) return 'warning';
  switch (r.coluna) {
    case 'calculada':
      return 'success';
    case 'enviada':
      return 'info';
    case 'perdida':
      return 'neutral';
    case 'fechada':
    case 'emitida':
      return 'success';
    default:
      return 'neutral';
  }
}

const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

export function reais(v: number | null | undefined): string {
  return typeof v === 'number' && Number.isFinite(v) ? BRL.format(v) : '—';
}

export function variacao(v: number | null | undefined): { texto: string; tom: 'sobe' | 'desce' | 'igual' } | null {
  if (typeof v !== 'number' || !Number.isFinite(v)) return null;
  if (Math.abs(v) < 0.05) return { texto: '0%', tom: 'igual' };
  const t = `${v > 0 ? '+' : '−'}${Math.abs(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
  return { texto: t, tom: v > 0 ? 'sobe' : 'desce' };
}

export function dataCurta(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [a, m, d] = iso.slice(0, 10).split('-');
  return a && m && d ? `${d}/${m}` : '—';
}

export function venceEm(dias: number | null | undefined): string {
  if (typeof dias !== 'number') return '';
  if (dias < -1) return `venceu há ${-dias} dias`;
  if (dias === -1) return 'venceu ontem';
  if (dias === 0) return 'vence hoje';
  if (dias === 1) return 'vence amanhã';
  return `em ${dias} dias`;
}

/** O título de um grupo da lista (o dia de vencimento). */
export function tituloDoDia(iso: string | null, hoje: string): string {
  if (!iso) return 'Sem data de vencimento';
  const dia = new Date(`${iso}T12:00:00`);
  const base = new Date(`${hoje}T12:00:00`);
  const dias = Math.round((dia.getTime() - base.getTime()) / 86_400_000);
  const semana = dia.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit' });
  const prefixo = dias === 0 ? 'Hoje · ' : dias === 1 ? 'Amanhã · ' : '';
  return prefixo + semana.charAt(0).toUpperCase() + semana.slice(1);
}

export function horaCurta(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}
