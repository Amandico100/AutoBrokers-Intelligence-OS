'use client';

import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { icons } from '@/lib/icons';
import {
  GalleryGrid,
  GalleryCard,
  GalleryFilters,
  StatusPill,
  DetailShell,
  DetailSection,
  PermissionList,
  PermissionModal,
  type StatusTone,
  type PermissionGroup,
} from '@/components/patterns';

type CardItem = {
  key: string;
  icon: LucideIcon;
  title: string;
  description: string;
  category: string;
  status: { tone: StatusTone; label: string };
  cta: string;
  disabled?: boolean;
};

const AUX_CATEGORIES = ['Todos', 'Análise', 'Financeiro', 'Comercial', 'Documentos'];

const auxiliares: CardItem[] = [
  { key: 'resumo', icon: icons.auxiliares, title: 'Resumo de Atendimentos', description: 'Resume conversas e destaca pendências e próxima ação.', category: 'Análise', status: { tone: 'success', label: 'Ativo' }, cta: 'Ver detalhes' },
  { key: 'cobranca', icon: icons.cobranca, title: 'Cobrança Inteligente', description: 'Prepara mensagens para clientes com parcelas pendentes.', category: 'Financeiro', status: { tone: 'approval', label: 'Aguardando aprovação' }, cta: 'Ver detalhes' },
  { key: 'followup', icon: icons.enviar, title: 'Follow-up de Propostas', description: 'Acompanha propostas paradas e sugere o próximo contato.', category: 'Comercial', status: { tone: 'warning', label: 'Precisa configurar' }, cta: 'Configurar' },
  { key: 'docs', icon: icons.documento, title: 'Conferência de Documentos', description: 'Verifica documentos faltantes e organiza pendências.', category: 'Documentos', status: { tone: 'neutral', label: 'Em breve' }, cta: 'Em breve', disabled: true },
];

const conectores: CardItem[] = [
  { key: 'whatsapp', icon: icons.whatsapp, title: 'WhatsApp', description: 'Converse e prepare mensagens para clientes.', category: 'Comunicação', status: { tone: 'success', label: 'Conectado' }, cta: 'Gerenciar' },
  { key: 'drive', icon: icons.drive, title: 'Google Drive', description: 'Use documentos da corretora como fonte.', category: 'Documentos', status: { tone: 'neutral', label: 'Disponível' }, cta: 'Conectar' },
  { key: 'banco', icon: icons.banco, title: 'Base de Dados', description: 'Dados internos da corretora.', category: 'Dados', status: { tone: 'success', label: 'Conectado' }, cta: 'Gerenciar' },
  { key: 'portal', icon: icons.seguradoras, title: 'Portal Seguradora', description: 'Consulta assistida em portais de seguradora.', category: 'Seguradoras', status: { tone: 'warning', label: 'Precisa configurar' }, cta: 'Conectar' },
];

const permGroups: PermissionGroup[] = [
  {
    title: 'O AutoBrokers vai poder',
    items: [
      { label: 'Consultar conversas e atendimentos', allowed: true },
      { label: 'Preparar mensagens para clientes', allowed: true },
      { label: 'Sugerir próximos passos', allowed: true },
    ],
  },
  {
    title: 'Não vai poder',
    items: [
      { label: 'Enviar mensagens sem a sua aprovação', allowed: false },
      { label: 'Alterar dados de apólice', allowed: false },
    ],
  },
];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="font-mono text-[11px] uppercase tracking-[0.12em] text-faint">{children}</h2>;
}

export function PatternsShowcase() {
  const [cat, setCat] = useState('Todos');
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);

  const filteredAux = auxiliares.filter(
    (a) =>
      (cat === 'Todos' || a.category === cat) &&
      (q === '' || a.title.toLowerCase().includes(q.toLowerCase())),
  );

  return (
    <div className="space-y-14">
      {/* Estados */}
      <section className="space-y-4">
        <SectionTitle>Estados · StatusPill</SectionTitle>
        <div className="flex flex-wrap gap-2">
          <StatusPill tone="success" label="Ativo" />
          <StatusPill tone="success" label="Pronto" />
          <StatusPill tone="neutral" label="Em breve" />
          <StatusPill tone="warning" label="Precisa configurar" />
          <StatusPill tone="info" label="Em teste" />
          <StatusPill tone="danger" label="Bloqueado" />
          <StatusPill tone="approval" label="Aguardando aprovação" />
        </div>
      </section>

      {/* Galeria · Auxiliares (com filtros) */}
      <section className="space-y-4">
        <SectionTitle>Padrão Galeria · Auxiliares</SectionTitle>
        <GalleryFilters
          search={q}
          onSearchChange={setQ}
          searchPlaceholder="Buscar auxiliar…"
          categories={AUX_CATEGORIES}
          activeCategory={cat}
          onCategoryChange={setCat}
        />
        <GalleryGrid>
          {filteredAux.map((a) => (
            <GalleryCard
              key={a.key}
              icon={a.icon}
              title={a.title}
              description={a.description}
              category={a.category}
              status={a.status}
              cta={a.cta}
              disabled={a.disabled}
            />
          ))}
        </GalleryGrid>
      </section>

      {/* Galeria · Conectores (clique abre modal) */}
      <section className="space-y-4">
        <SectionTitle>Padrão Galeria · Conectores</SectionTitle>
        <GalleryGrid>
          {conectores.map((c) => (
            <GalleryCard
              key={c.key}
              icon={c.icon}
              title={c.title}
              description={c.description}
              category={c.category}
              status={c.status}
              cta={c.cta}
              onClick={() => setOpen(true)}
            />
          ))}
        </GalleryGrid>
      </section>

      {/* Detalhe */}
      <section className="space-y-4">
        <SectionTitle>Padrão Detalhe</SectionTitle>
        <DetailShell
          header={{
            icon: icons.auxiliares,
            title: 'Auxiliar de Resumo de Atendimentos',
            subtitle: 'Resume conversas e destaca pendências — sem envio externo.',
            status: { tone: 'success', label: 'Ativo' },
            breadcrumb: [{ label: 'Auxiliares', href: '#' }, { label: 'Resumo de Atendimentos' }],
            actions: (
              <Button size="sm" onClick={() => setOpen(true)}>
                Ativar
              </Button>
            ),
          }}
          tabs={[
            {
              value: 'overview',
              label: 'Visão geral',
              content: (
                <DetailSection
                  title="O que faz"
                  description="Lê uma conversa selecionada e gera um resumo com pendências e próxima ação sugerida. Não envia nada externamente."
                />
              ),
            },
            {
              value: 'how',
              label: 'Como funciona',
              content: (
                <DetailSection
                  title="Como funciona"
                  description="Você seleciona a conversa, o AutoBrokers resume e sugere a próxima ação. A sugestão nunca é executada sozinha."
                />
              ),
            },
            {
              value: 'perms',
              label: 'Permissões',
              content: (
                <DetailSection title="Permissões">
                  <PermissionList groups={permGroups} />
                </DetailSection>
              ),
            },
            {
              value: 'runs',
              label: 'Execuções',
              content: (
                <DetailSection
                  title="Execuções"
                  description="O histórico de execuções aparecerá aqui (custo, duração e resultado)."
                />
              ),
            },
          ]}
          side={
            <DetailSection title="Resumo">
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Categoria</dt>
                  <dd className="text-foreground">Análise</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Risco</dt>
                  <dd className="text-success">Baixo</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Envio externo</dt>
                  <dd className="text-foreground">Não</dd>
                </div>
              </dl>
            </DetailSection>
          }
        />
      </section>

      {/* Modal de Permissão */}
      <section className="space-y-4">
        <SectionTitle>Modal de Permissão</SectionTitle>
        <Button onClick={() => setOpen(true)}>Abrir modal de permissão</Button>
        <PermissionModal
          open={open}
          onOpenChange={setOpen}
          icon={icons.whatsapp}
          title="Conectar WhatsApp ao AutoBrokers"
          description="Defina o que o AutoBrokers poderá fazer com esta conexão."
          groups={permGroups}
          requiresHumanApproval
          confirmLabel="Permitir e continuar"
        />
      </section>
    </div>
  );
}

export default PatternsShowcase;
