'use client';

import { useEffect, useState } from 'react';

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

/**
 * SPEC-014 C-FIX-1 (F) — conectar a InfoCap de forma simples e segura.
 * Login/senha vão APENAS server-side (rota cifra no Vault/Fernet). A URL é global (não pedimos).
 * Conectar NÃO exige aprovação humana — o próprio corretor está autorizando.
 */
export function ConfigureInfocapModal({
  open, onOpenChange, onConfigured,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onConfigured?: () => void;
}) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [okMsg, setOkMsg] = useState('');

  useEffect(() => {
    if (open) { setUsername(''); setPassword(''); setError(''); setOkMsg(''); }
  }, [open]);

  const close = (o: boolean) => { if (!o) { setPassword(''); } onOpenChange(o); };

  const submit = async () => {
    if (!username.trim() || !password) { setError('Informe login e senha.'); return; }
    setSaving(true); setError(''); setOkMsg('');
    try {
      const res = await fetch('/api/attendance/connectors/infocap/secret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        setPassword('');
        setOkMsg('InfoCap conectada com segurança.');
        onConfigured?.();
        setTimeout(() => onOpenChange(false), 700);
      } else {
        setError(data.error || 'Não foi possível conectar a InfoCap.');
      }
    } catch {
      setError('Não foi possível conectar agora. Tente novamente.');
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
              <Icon icon={icons.seguradoras} size={18} />
            </span>
            <DialogTitle className="text-base">Conectar InfoCap</DialogTitle>
          </div>
          <DialogDescription className="pt-1">
            Informe o login e a senha da InfoCap da sua corretora. Eles são{' '}
            <span className="font-medium text-foreground">criptografados no servidor</span> e nunca exibidos de novo.
            Cada corretora usa as próprias credenciais.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="ic-user" className="text-foreground">Login (e-mail InfoCap)</Label>
            <Input id="ic-user" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="corretora@api.com.br" autoComplete="off" className="bg-background" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ic-pass" className="text-foreground">Senha</Label>
            <Input id="ic-pass" type="password" autoComplete="off" value={password} onChange={(e) => setPassword(e.target.value)} className="bg-background" />
          </div>
        </div>

        <p className="text-[11px] text-muted-foreground">
          A InfoCap é usada apenas para <span className="font-medium text-foreground">consultar apólices</span> (somente leitura). Conectar não dispara nenhuma ação.
        </p>

        {error && <p className="text-xs text-danger">{error}</p>}
        {okMsg && <p className="text-xs text-success">{okMsg}</p>}

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={() => close(false)} disabled={saving}>Cancelar</Button>
          <Button onClick={submit} disabled={saving || !username.trim() || !password}>
            {saving ? 'Conectando…' : 'Conectar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ConfigureInfocapModal;
