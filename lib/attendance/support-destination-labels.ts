// Rótulos/placeholders da UI de destinos humanos de suporte. Puro, sem PII.
export const DESTINATION_TYPE_LABEL: Record<string, string> = {
  whatsapp_group: 'WhatsApp grupo',
  whatsapp_individual: 'WhatsApp individual',
  email: 'E-mail',
  internal_queue: 'Fila interna',
  webhook: 'Webhook',
};

export const CHANNEL_PROVIDER_LABEL: Record<string, string> = {
  manual: 'Manual',
  zapi: 'Z-API',
  evolution: 'Evolution',
  meta_cloud: 'Meta Cloud',
};

export const DESTINATION_REF_PLACEHOLDER: Record<string, string> = {
  whatsapp_group: '120363...@g.us',
  whatsapp_individual: '5547999999999',
  email: 'suporte@corretora.com.br',
  webhook: 'https://...',
  internal_queue: 'fila-atendimento',
};

export const DESTINATION_TYPE_OPTIONS = [
  'whatsapp_group',
  'whatsapp_individual',
  'email',
  'internal_queue',
  'webhook',
] as const;

export const CHANNEL_PROVIDER_OPTIONS = ['manual', 'zapi', 'evolution', 'meta_cloud'] as const;

export function destinationTypeLabel(t?: string | null): string {
  return (t && DESTINATION_TYPE_LABEL[t]) || t || '—';
}
export function channelProviderLabel(p?: string | null): string {
  return (p && CHANNEL_PROVIDER_LABEL[p]) || p || '—';
}
