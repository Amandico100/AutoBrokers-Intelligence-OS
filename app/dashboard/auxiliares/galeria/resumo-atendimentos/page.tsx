'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { icons } from '@/lib/icons';
import { DetailShell, DetailSection, PermissionList, PermissionModal } from '@/components/patterns';
import { resumoPermissions } from '@/lib/mock/tenant-modules';

export default function ResumoAtendimentosDetailPage() {
  const [open, setOpen] = useState(false);

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-4 py-10 sm:px-6">
        <DetailShell
          header={{
            icon: icons.auxiliares,
            title: 'Auxiliar de Resumo de Atendimentos',
            subtitle: 'Resume conversas, identifica pendências e prepara próximos passos — sem envio externo.',
            status: { tone: 'success', label: 'Pronto para ativar' },
            breadcrumb: [
              { label: 'Auxiliares', href: '/dashboard/auxiliares' },
              { label: 'Galeria', href: '/dashboard/auxiliares/galeria' },
              { label: 'Resumo de Atendimentos' },
            ],
            actions: (
              <Button size="sm" onClick={() => setOpen(true)}>
                Ativar com segurança
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
                  description="Lê uma conversa selecionada, gera um resumo claro, destaca pendências e sugere a próxima ação. Não envia nada externamente — a sugestão nunca é executada sozinha."
                />
              ),
            },
            {
              value: 'how',
              label: 'Como funciona',
              content: (
                <DetailSection
                  title="Como funciona"
                  description="Você escolhe a conversa do atendimento. O AutoBrokers analisa o histórico e devolve um resumo operacional com pendências e próximos passos sugeridos, prontos para você revisar."
                />
              ),
            },
            {
              value: 'perms',
              label: 'Permissões',
              content: (
                <DetailSection title="Permissões">
                  <PermissionList groups={resumoPermissions} />
                </DetailSection>
              ),
            },
            {
              value: 'runs',
              label: 'Execuções',
              content: (
                <DetailSection
                  title="Execuções"
                  description="O histórico de execuções deste auxiliar aparecerá aqui (custo, duração e resultado)."
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
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Configuração</dt>
                  <dd className="text-foreground">~1 min</dd>
                </div>
              </dl>
            </DetailSection>
          }
        />

        <PermissionModal
          open={open}
          onOpenChange={setOpen}
          icon={icons.auxiliares}
          title="Ativar Auxiliar de Resumo de Atendimentos"
          description="Confirme o que o AutoBrokers poderá fazer ao executar este auxiliar."
          groups={resumoPermissions}
          requiresHumanApproval
          confirmLabel="Ativar com segurança"
        />
      </div>
    </div>
  );
}
