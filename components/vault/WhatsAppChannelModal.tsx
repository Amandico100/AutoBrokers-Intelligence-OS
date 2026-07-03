'use client';

// Modal do canal WhatsApp (SPEC-017 — UX pedida pelo Founder):
// o card "WhatsApp" da galeria abre este modal com o fluxo de QR/alerta/status.
// Conteúdo = WhatsAppChannelCard (montado só com o modal aberto → poll ativo
// apenas enquanto o corretor está conectando).

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { WhatsAppChannelCard } from './WhatsAppChannelCard';

export function WhatsAppChannelModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>WhatsApp da corretora</DialogTitle>
          <DialogDescription>
            Conecte o número de atendimento aos segurados por QR code (Evolution · sem mensalidade).
          </DialogDescription>
        </DialogHeader>
        {open ? <WhatsAppChannelCard /> : null}
      </DialogContent>
    </Dialog>
  );
}
