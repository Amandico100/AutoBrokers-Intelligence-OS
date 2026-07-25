import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { BrandIdentityClient } from './BrandIdentityClient';

export const metadata = { title: 'Identidade da Corretora · AutoBrokers' };

// SPEC-057 — a identidade que toda peça gerada vai carregar. Fica no hub da
// Corretora porque é da empresa, não da pessoa.
export default function BrandIdentityPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-10 sm:px-6">
        <DetailHeader
          icon={icons.corretora}
          title="Identidade da Corretora"
          subtitle="Logo, cores, tipografia e o que sua corretora faz. Todo relatório, PDF e proposta que o AutoBrokers gerar sai com esta identidade."
          breadcrumb={[
            { label: 'Personalização', href: '/dashboard/personalizacao' },
            { label: 'Corretora', href: '/dashboard/personalizacao/corretora' },
            { label: 'Identidade' },
          ]}
        />
        <BrandIdentityClient />
      </div>
    </div>
  );
}
