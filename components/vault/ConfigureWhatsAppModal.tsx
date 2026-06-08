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
import { configureWhatsAppConnection } from '@/lib/vault/api';

const DEFAULT_BASE_URL = 'https://api.z-api.io/instances';

export function ConfigureWhatsAppModal({
  open,
  onOpenChange,
  connectionId,
  onConfigured,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  connectionId: string | null;
  onConfigured?: () => void;
}) {
  const [identifier, setIdentifier] = useState('');
  const [instanceId, setInstanceId] = useState('');
  const [token, setToken] = useState('');
  const [clientToken, setClientToken] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const clearSecrets = () => {
    setToken('');
    setClientToken('');
  };

  // Limpa o formulário ao abrir (nunca pré-preenche segredo).
  useEffect(() => {
    if (open) {
      setIdentifier('');
      setInstanceId('');
      setToken('');
      setClientToken('');
      setBaseUrl('');
      setError('');
    }
  }, [open, connectionId]);

  const close = (o: boolean) => {
    if (!o) clearSecrets();
    onOpenChange(o);
  };

  const submit = async () => {
    if (!connectionId) return;
    setSaving(true);
    setError('');
    try {
      const res = await configureWhatsAppConnection(connectionId, {
        identifier: identifier.trim(),
        instance_id: instanceId.trim(),
        token: token.trim(),
        client_token: clientToken.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
      });
      if (res.success) {
        clearSecrets();
        onConfigured?.();
        onOpenChange(false);
      } else {
        setError(res.error || 'Não foi possível configurar a conexão.');
      }
    } catch {
      setError('Não foi possível configurar a conexão agora.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="border-border bg-surface sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
              <Icon icon={icons.whatsapp} size={18} />
            </span>
            <DialogTitle className="text-base">Configurar WhatsApp com segurança</DialogTitle>
          </div>
          <DialogDescription className="pt-1">
            As credenciais serão <span className="font-medium text-foreground">criptografadas no servidor</span>.
            Nenhuma mensagem será enviada neste passo.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="wa-identifier" className="text-foreground">Telefone conectado</Label>
            <Input id="wa-identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="5548999999999" className="bg-background" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="wa-instance" className="text-foreground">Instance ID</Label>
            <Input id="wa-instance" value={instanceId} onChange={(e) => setInstanceId(e.target.value)} className="bg-background" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="wa-token" className="text-foreground">Token</Label>
            <Input id="wa-token" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} className="bg-background" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="wa-client-token" className="text-foreground">Client Token (opcional)</Label>
            <Input id="wa-client-token" type="password" autoComplete="off" value={clientToken} onChange={(e) => setClientToken(e.target.value)} className="bg-background" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="wa-base-url" className="text-foreground">Base URL (opcional)</Label>
            <Input id="wa-base-url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder={DEFAULT_BASE_URL} className="bg-background" />
          </div>
        </div>

        <p className="text-[11px] text-muted-foreground">
          Esta conexão só será usada mediante permissões e aprovações.
        </p>

        {error && <p className="text-xs text-danger">{error}</p>}

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={() => close(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={saving || !connectionId}>
            {saving ? 'Salvando…' : 'Salvar com segurança'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ConfigureWhatsAppModal;
