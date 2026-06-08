'use client';

import type { LucideIcon } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { PermissionList, type PermissionGroup } from '@/components/patterns/PermissionList';

export interface PermissionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  icon?: LucideIcon;
  title: string;
  description?: string;
  groups: PermissionGroup[];
  /** Mostra a faixa "ações externas exigem aprovação humana". */
  requiresHumanApproval?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm?: () => void;
}

/** Modal de permissão/ativação (estilo apps/connectors). Controlado via open/onOpenChange. */
export function PermissionModal({
  open,
  onOpenChange,
  icon,
  title,
  description,
  groups,
  requiresHumanApproval,
  confirmLabel = 'Permitir e continuar',
  cancelLabel = 'Cancelar',
  onConfirm,
}: PermissionModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-surface sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            {icon && (
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                <Icon icon={icon} size={18} />
              </span>
            )}
            <DialogTitle className="text-base">{title}</DialogTitle>
          </div>
          {description && <DialogDescription className="pt-1">{description}</DialogDescription>}
        </DialogHeader>

        <div className="py-1">
          <PermissionList groups={groups} />
        </div>

        {requiresHumanApproval && (
          <div className="flex items-start gap-2 rounded-lg border border-dashed border-primary/50 bg-brand-soft p-3 text-xs text-foreground-2">
            <Icon icon={icons.aprovacao} size={16} className="mt-0.5 shrink-0 text-primary" />
            <span>
              Ações externas reais passam por{' '}
              <span className="font-medium text-foreground">aprovação humana</span> antes de acontecer.
            </span>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {cancelLabel}
          </Button>
          <Button
            onClick={() => {
              onConfirm?.();
              onOpenChange(false);
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default PermissionModal;
