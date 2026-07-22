'use client';

// Modal do canal WhatsApp (SPEC-017 / SPEC-047).
// SPEC-047: a "escolha de provedor" saiu — GO e "clássico" abriam o MESMO
// fluxo (o provedor real é decidido pelo backend), o que só confundia.
// O modal vai direto ao pareamento por QR; a API Oficial da Meta fica
// anunciada como caminho futuro. O provedor clássico segue vivo no backend.

import { ShieldCheck } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { StatusPill } from '@/components/patterns/StatusPill';

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
          <DialogTitle>Conectar WhatsApp da corretora</DialogTitle>
          <DialogDescription>
            Use o número de trabalho que a equipe já atende. O celular e o WhatsApp Web
            continuarão funcionando normalmente.
          </DialogDescription>
        </DialogHeader>

        {open && <WhatsAppChannelCard />}

        {open && (
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
        )}
      </DialogContent>
    </Dialog>
  );
}
