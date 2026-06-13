import type { LucideIcon } from 'lucide-react';

import { icons } from '@/lib/icons';
import type { StatusTone, PermissionGroup } from '@/components/patterns';
import type { ModuleArea } from '@/components/modules/ModuleIndex';

/**
 * Dados MOCK estáticos dos módulos do tenant (B4). Sem PII, sem backend, sem chamadas reais.
 * Servem apenas para demonstrar os padrões-mestre nas rotas /dashboard/*.
 */

export type GalleryItem = {
  key: string;
  icon: LucideIcon;
  title: string;
  description: string;
  category?: string;
  status?: { tone: StatusTone; label: string };
  href?: string;
  cta?: string;
};

// ---------- Atendimentos ----------
export const atendimentoAreas: ModuleArea[] = [
  { key: 'fila', icon: icons.fila, title: 'Fila', description: 'Casos aguardando atendimento.', href: '/dashboard/atendimentos/fila', status: { tone: 'info', label: 'MVP ativo' } },
  { key: 'casos', icon: icons.casos, title: 'Casos', description: 'Detalhe, timeline e ações.', href: '/dashboard/atendimentos/casos', status: { tone: 'neutral', label: 'Em breve' } },
  { key: 'conversas', icon: icons.conversas, title: 'Conversas', description: 'Histórico por canal.', href: '/dashboard/atendimentos/conversas', status: { tone: 'neutral', label: 'Em breve' } },
  { key: 'segurados', icon: icons.equipe, title: 'Segurados', description: 'Clientes e apólices.', href: '/dashboard/atendimentos/segurados', status: { tone: 'neutral', label: 'Em breve' } },
];

// ---------- Auxiliares ----------
export const auxiliaresAreas: ModuleArea[] = [
  { key: 'meus', icon: icons.auxiliares, title: 'Meus Auxiliares', description: 'Auxiliares ativados pela corretora.', href: '/dashboard/auxiliares/meus' },
  { key: 'galeria', icon: icons.galeria, title: 'Galeria', description: 'Modelos prontos para ativar.', href: '/dashboard/auxiliares/galeria' },
  { key: 'execucoes', icon: icons.historico, title: 'Execuções', description: 'Histórico do que foi feito.', href: '/dashboard/auxiliares/execucoes' },
];

export const auxiliaresGaleria: GalleryItem[] = [
  { key: 'resumo', icon: icons.auxiliares, title: 'Resumo de Atendimentos', description: 'Resume conversas recentes, identifica pendências e prepara próximos passos.', category: 'Análise', status: { tone: 'success', label: 'Pronto para ativar' }, href: '/dashboard/auxiliares/galeria/resumo-atendimentos', cta: 'Ver detalhes' },
  { key: 'cobranca', icon: icons.cobranca, title: 'Cobrança Inteligente', description: 'Prepara lembretes de pagamento e boletos pendentes.', category: 'Financeiro', status: { tone: 'neutral', label: 'Em breve' }, cta: 'Em breve' },
  { key: 'followup', icon: icons.enviar, title: 'Follow-up de Propostas', description: 'Identifica propostas paradas e sugere a próxima mensagem.', category: 'Comercial', status: { tone: 'neutral', label: 'Em breve' }, cta: 'Em breve' },
  { key: 'docs', icon: icons.documento, title: 'Conferência de Documentos', description: 'Verifica documentos faltantes em assistências e sinistros.', category: 'Documentos', status: { tone: 'neutral', label: 'Em breve' }, cta: 'Em breve' },
];

export const resumoPermissions: PermissionGroup[] = [
  {
    title: 'O AutoBrokers vai poder',
    items: [
      { label: 'Consultar conversas recentes', allowed: true },
      { label: 'Ler documentos anexados', allowed: true },
      { label: 'Preparar resumo operacional', allowed: true },
      { label: 'Sugerir próximos passos', allowed: true },
    ],
  },
  {
    title: 'Não vai poder',
    items: [
      { label: 'Enviar mensagens externas sem a sua aprovação', allowed: false },
      { label: 'Alterar dados de apólice ou de cliente', allowed: false },
    ],
  },
];

// ---------- Personalização ----------
export const personalizacaoAreas: ModuleArea[] = [
  { key: 'conectores', icon: icons.conectores, title: 'Conectores', description: 'Integrações reutilizáveis.', href: '/dashboard/personalizacao/conectores' },
  { key: 'seguradoras', icon: icons.seguradoras, title: 'Seguradoras', description: 'Canais, portais e corredores.', href: '/dashboard/personalizacao/seguradoras' },
  { key: 'conhecimento', icon: icons.conhecimento, title: 'Conhecimento', description: 'Documentos e fontes da corretora.', href: '/dashboard/personalizacao/conhecimento' },
  { key: 'corretora', icon: icons.corretora, title: 'Corretora', description: 'Dados e identidade.', href: '/dashboard/personalizacao/corretora' },
  { key: 'equipe', icon: icons.equipe, title: 'Equipe', description: 'Usuários e permissões.', href: '/dashboard/personalizacao/equipe' },
];

export const conectores: GalleryItem[] = [
  { key: 'whatsapp', icon: icons.whatsapp, title: 'WhatsApp', description: 'Converse e prepare mensagens para clientes.', category: 'Comunicação', status: { tone: 'success', label: 'Pronto para conectar' } },
  { key: 'drive', icon: icons.drive, title: 'Google Drive', description: 'Use documentos da corretora como fonte.', category: 'Documentos', status: { tone: 'neutral', label: 'Em breve' } },
  { key: 'banco', icon: icons.banco, title: 'Base de Dados', description: 'Dados internos da corretora.', category: 'Dados', status: { tone: 'warning', label: 'Precisa configurar' } },
  { key: 'n8n', icon: icons.auxiliares, title: 'n8n', description: 'Automações e fluxos auxiliares.', category: 'Automação', status: { tone: 'neutral', label: 'Em breve' } },
  { key: 'portal', icon: icons.seguradoras, title: 'Portal Seguradora', description: 'Consulta assistida em portais de seguradora.', category: 'Seguradoras', status: { tone: 'warning', label: 'Precisa configurar' } },
];

export const connectorPermissions: PermissionGroup[] = [
  {
    title: 'O AutoBrokers vai poder',
    items: [
      { label: 'Usar esta conexão nas áreas autorizadas', allowed: true },
      { label: 'Consultar/preparar conteúdo permitido', allowed: true },
    ],
  },
  {
    title: 'Não vai poder',
    items: [
      { label: 'Executar ações externas sem a sua aprovação', allowed: false },
      { label: 'Acessar credenciais sensíveis no navegador', allowed: false },
    ],
  },
];

export const seguradoras: GalleryItem[] = [
  { key: 'allianz', icon: icons.seguradoras, title: 'Allianz', description: 'Assistência, sinistro e canais.', status: { tone: 'success', label: 'Pronta' } },
  { key: 'porto', icon: icons.seguradoras, title: 'Porto', description: 'Auto, residencial e assistência.', status: { tone: 'warning', label: 'Em configuração' } },
  { key: 'tokio', icon: icons.seguradoras, title: 'Tokio Marine', description: 'Ramos diversos.', status: { tone: 'warning', label: 'Portal pendente' } },
  { key: 'bradesco', icon: icons.seguradoras, title: 'Bradesco', description: 'Ramos diversos.', status: { tone: 'neutral', label: 'Em breve' } },
  { key: 'hdi', icon: icons.seguradoras, title: 'HDI', description: 'Auto e assistência.', status: { tone: 'neutral', label: 'Em breve' } },
];
