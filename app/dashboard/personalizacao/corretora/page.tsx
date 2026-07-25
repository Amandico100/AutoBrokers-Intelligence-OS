import { DetailHeader, GalleryGrid, GalleryCard } from '@/components/patterns';
import { icons } from '@/lib/icons';

export const metadata = { title: 'Corretora · AutoBrokers' };

// SPEC-045 — o HUB da empresa: tudo que é da CORRETORA (compartilhado pela
// equipe) mora aqui. O que é pessoal vive em Configurações.
export default function CorretoraPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.corretora}
          title="Corretora"
          subtitle="Tudo da sua empresa em um lugar — o que é seu (pessoal) fica em Configurações."
          breadcrumb={[{ label: 'Personalização', href: '/dashboard/personalizacao' }, { label: 'Corretora' }]}
        />
        <GalleryGrid>
          {/* Vem primeiro: é a identidade que todas as peças geradas carregam. */}
          <GalleryCard
            icon={icons.corretora}
            title="Identidade da corretora"
            description="Logo, cores e tipografia da sua marca — capturados do seu site. Todo relatório e PDF sai com esta identidade."
            status={{ tone: 'info', label: 'Automático' }}
            cta="Montar"
            href="/dashboard/personalizacao/corretora/identidade"
          />
          <GalleryCard
            icon={icons.corretora}
            title="Dados da corretora"
            description="Nome, razão social, CNPJ, contato e endereço."
            status={{ tone: 'success', label: 'Editável' }}
            cta="Editar"
            href="/dashboard/personalizacao/corretora/dados"
          />
          <GalleryCard
            icon={icons.atendimentos}
            title="Agente de Atendimento"
            description="Quem atende seus segurados no WhatsApp. Nome, tom, mensagens — e o botão de ligar/desligar."
            status={{ tone: 'info', label: 'Da corretora' }}
            cta="Configurar"
            href="/dashboard/personalizacao/agentes/even"
          />
          <GalleryCard
            icon={icons.whatsapp}
            title="WhatsApp da corretora"
            description="Os números conectados, por função: atendimento & acionamentos, auxiliares & avisos."
            status={{ tone: 'success', label: 'Canais' }}
            cta="Gerenciar"
            href="/dashboard/personalizacao/corretora/whatsapp"
          />
          <GalleryCard
            icon={icons.atendimentos}
            title="Suporte humano"
            description="Destino para dossiês e transferências quando o agente precisar escalar um atendimento."
            status={{ tone: 'success', label: 'Ativo' }}
            cta="Configurar"
            href="/dashboard/personalizacao/corretora/suporte-humano"
          />
          <GalleryCard
            icon={icons.equipe}
            title="Equipe"
            description="Usuários da corretora e papéis (dono, admin, membro)."
            cta="Gerenciar"
            href="/dashboard/personalizacao/equipe"
          />
          <GalleryCard
            icon={icons.conhecimento}
            title="Conhecimento da corretora"
            description="Documentos e fontes que TODOS os assistentes da equipe usam."
            cta="Alimentar"
            href="/dashboard/personalizacao/conhecimento"
          />
          <GalleryCard
            icon={icons.cobranca}
            title="Custos e Uso"
            description="Saldo e consumo da corretora — total e por pessoa (30 dias)."
            cta="Ver consumo"
            href="/dashboard/personalizacao/custos"
          />
        </GalleryGrid>
      </div>
    </div>
  );
}
