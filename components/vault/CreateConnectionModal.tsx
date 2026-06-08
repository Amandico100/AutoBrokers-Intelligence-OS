'use client';

import { useEffect, useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';
import { StatusPill } from '@/components/patterns';
import { createTenantConnection } from '@/lib/vault/api';
import type { ConnectorTemplate } from '@/lib/vault/types';
import { riskPill, slugIcon } from '@/components/vault/labels';

export function CreateConnectionModal({
  open,
  onOpenChange,
  template,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  template: ConnectorTemplate | null;
  onCreated?: () => void;
}) {
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open && template) {
      setName(template.name);
      setError('');
    }
  }, [open, template]);

  const submit = async () => {
    if (!template) return;
    setSaving(true);
    setError('');
    try {
      const res = await createTenantConnection({
        connector_template_slug: template.slug,
        name: name.trim() || template.name,
        status: 'draft',
      });
      if (res.connection) {
        onCreated?.();
        onOpenChange(false);
      } else {
        setError(res.error || 'Não foi possível preparar a conexão.');
      }
    } catch {
      setError('Não foi possível preparar a conexão agora.');
    } finally {
      setSaving(false);
    }
  };

  const rp = riskPill(template?.risk_level);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-surface sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
              <Icon icon={slugIcon(template?.slug)} size={18} />
            </span>
            <DialogTitle className="text-base">{template ? `Preparar ${template.name}` : 'Preparar conexão'}</DialogTitle>
          </div>
          <DialogDescription className="pt-1">
            A conexão é criada em <span className="font-medium text-foreground">rascunho</span>. Nenhuma senha ou
            chave é solicitada aqui.
          </DialogDescription>
        </DialogHeader>

        {template && (
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={rp.tone} label={rp.label} />
            <span className="rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
              {template.category}
            </span>
            <span className="rounded-full border border-border-soft px-2 py-0.5 font-mono text-[10px] text-faint">
              {template.auth_type}
            </span>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="vault-conn-name" className="text-foreground">Nome da conexão</Label>
          <Input
            id="vault-conn-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex.: Documentos da corretora"
            className="bg-background"
          />
        </div>

        {error && <p className="text-xs text-danger">{error}</p>}

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={saving || !template}>
            {saving ? 'Preparando…' : 'Preparar conexão'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default CreateConnectionModal;
