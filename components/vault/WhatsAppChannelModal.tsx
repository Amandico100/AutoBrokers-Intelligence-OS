'use client';

// Modal do canal WhatsApp (SPEC-017 / S17-14 — UX pedida pelo Founder):
// o card "WhatsApp" da galeria abre este modal com a ESCOLHA do provedor
// (Evolution QR hoje; API Oficial da Meta em preparação) e depois o fluxo
// de conexão do provedor escolhido.

import { useState } from 'react';
import { ArrowLeft, QrCode, ShieldCheck } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { StatusPill } from '@/components/patterns/StatusPill';

import { WhatsAppChannelCard } from './WhatsAppChannelCard';

type Step = 'choose' | 'evolution';

export function WhatsAppChannelModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [step, setStep] = useState<Step>('choose');

  const close = (o: boolean) => {
    onOpenChange(o);
    if (!o) setStep('choose');
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {step === 'evolution' && (
              <button
                onClick={() => setStep('choose')}
                className="rounded-md border border-border bg-surface-2 p-1 text-muted-foreground transition-colors hover:text-foreground"
                aria-label="Voltar para a escolha de provedor"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
              </button>
            )}
            WhatsApp da corretora
          </DialogTitle>
          <DialogDescription>
            {step === 'choose'
              ? 'Escolha como conectar o número de atendimento aos segurados.'
              : 'Conecte por QR code (Evolution · sem mensalidade).'}
          </DialogDescription>
        </DialogHeader>

        {open && step === 'choose' && (
          <div className="space-y-3">
            <button
              onClick={() => setStep('evolution')}
              className="flex w-full items-start gap-3 rounded-xl border border-border bg-surface p-4 text-left transition-colors hover:border-primary/40 hover:bg-surface-2"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-brand-soft text-primary">
                <QrCode className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">Conexão por QR code</span>
                  <StatusPill tone="success" label="Disponível" />
                </span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  Usa o número que você já tem (WhatsApp comum). Sem mensalidade. Escaneia o QR e
                  pronto — ideal para começar e para números de atendimento dedicados.
                </span>
              </span>
            </button>

            <div className="flex w-full items-start gap-3 rounded-xl border border-dashed border-border bg-surface p-4 text-left opacity-80">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">API Oficial da Meta (Cloud API)</span>
                  <StatusPill tone="info" label="Em preparação" />
                </span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  Canal empresarial oficial: sem QR code, sem celular ligado, com selo e maior
                  estabilidade. Requer cadastro da corretora na Meta e tem custo por mensagem.
                  Em breve nesta tela.
                </span>
              </span>
            </div>
          </div>
        )}

        {open && step === 'evolution' && <WhatsAppChannelCard />}
      </DialogContent>
    </Dialog>
  );
}
