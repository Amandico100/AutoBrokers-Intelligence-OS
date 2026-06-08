'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { DetailShell, DetailSection, PermissionList } from '@/components/patterns';
import { ResumoResult } from '@/components/auxiliaries/ResumoResult';
import { resumoPermissions } from '@/lib/mock/tenant-modules';
import { runResumoAtendimentos } from '@/lib/auxiliaries/api';
import type { AuxiliaryRunOutput } from '@/lib/auxiliaries/types';

type RunState = 'idle' | 'loading' | 'success' | 'error';

function friendlyError(err?: string): string {
  const e = (err || '').toLowerCase();
  if (e.includes('conversa') || e.includes('mensage')) {
    return 'Ainda não encontramos conversas suficientes para resumir. Converse com o AutoBrokers ou aguarde novos atendimentos.';
  }
  if (e.includes('autoriz') || e.includes('unauthorized') || e.includes('permiss')) {
    return 'Sua sessão não tem permissão para executar este auxiliar.';
  }
  return 'Não foi possível executar este auxiliar agora. Tente novamente em alguns instantes.';
}

function RunPanel({
  state,
  output,
  errorMsg,
  onExecute,
}: {
  state: RunState;
  output: AuxiliaryRunOutput | null;
  errorMsg: string;
  onExecute: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
        <Icon icon={icons.cadeado} size={14} className="mt-0.5 shrink-0 text-primary" />
        <span>
          Este auxiliar apenas <span className="font-medium text-foreground">lê</span> conversas da sua
          corretora e gera um resumo. Ele não envia mensagens, não altera atendimentos e não executa
          ações externas.
        </span>
      </div>

      {state === 'idle' && (
        <DetailSection>
          <div className="py-6 text-center">
            <p className="text-sm font-medium text-foreground">
              Pronto para resumir o atendimento mais recente.
            </p>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Clique em “Executar resumo agora” para gerar um resumo com pendências e próximos passos.
            </p>
            <Button className="mt-4" onClick={onExecute}>
              <Icon icon={icons.enviar} size={16} className="mr-2" />
              Executar resumo agora
            </Button>
          </div>
        </DetailSection>
      )}

      {state === 'loading' && (
        <DetailSection>
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Icon icon={icons.renovacao} size={16} className="animate-spin" />
            Gerando resumo…
          </div>
        </DetailSection>
      )}

      {state === 'error' && (
        <DetailSection>
          <div className="py-6 text-center">
            <p className="mx-auto max-w-md text-sm font-medium text-foreground">{errorMsg}</p>
            <Button variant="outline" className="mt-4" onClick={onExecute}>
              Tentar novamente
            </Button>
          </div>
        </DetailSection>
      )}

      {state === 'success' && output && (
        <DetailSection title="Resultado">
          <ResumoResult output={output} />
        </DetailSection>
      )}
    </div>
  );
}

export default function ResumoAtendimentosDetailPage() {
  const [state, setState] = useState<RunState>('idle');
  const [output, setOutput] = useState<AuxiliaryRunOutput | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const execute = async () => {
    setState('loading');
    setErrorMsg('');
    setOutput(null);
    try {
      const res = await runResumoAtendimentos();
      if (res.success && res.run?.output) {
        setOutput(res.run.output);
        setState('success');
      } else if (res.success) {
        setErrorMsg('Resumo gerado, mas o formato retornado foi inesperado.');
        setState('error');
      } else {
        setErrorMsg(friendlyError(res.error));
        setState('error');
      }
    } catch {
      setErrorMsg('Não foi possível executar este auxiliar agora. Tente novamente em alguns instantes.');
      setState('error');
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-4 py-10 sm:px-6">
        <DetailShell
          header={{
            icon: icons.auxiliares,
            title: 'Auxiliar de Resumo de Atendimentos',
            subtitle:
              'Resume conversas, identifica pendências e prepara próximos passos — sem envio externo.',
            status: { tone: 'success', label: 'Pronto para ativar' },
            breadcrumb: [
              { label: 'Auxiliares', href: '/dashboard/auxiliares' },
              { label: 'Galeria', href: '/dashboard/auxiliares/galeria' },
              { label: 'Resumo de Atendimentos' },
            ],
            actions: (
              <Button size="sm" onClick={execute} disabled={state === 'loading'}>
                {state === 'loading' ? (
                  <>
                    <Icon icon={icons.renovacao} size={16} className="mr-2 animate-spin" />
                    Executando…
                  </>
                ) : (
                  <>
                    <Icon icon={icons.enviar} size={16} className="mr-2" />
                    Executar resumo agora
                  </>
                )}
              </Button>
            ),
          }}
          tabs={[
            {
              value: 'run',
              label: 'Resumo',
              content: (
                <RunPanel state={state} output={output} errorMsg={errorMsg} onExecute={execute} />
              ),
            },
            {
              value: 'how',
              label: 'Como funciona',
              content: (
                <DetailSection
                  title="Como funciona"
                  description="O AutoBrokers seleciona o atendimento mais recente da sua corretora, analisa o histórico e devolve um resumo operacional com pendências e próximos passos sugeridos, prontos para você revisar."
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
      </div>
    </div>
  );
}
