'use client';

import { Button } from '@/components/ui/button';

export interface PairingState {
  attempt_id?: string;
  state: string;
  next_action?: string;
  expires_at?: string;
  poll_after_ms?: number;
  support_ref?: string;
  error?: string;
  error_code?: string;
  qr_base64?: string;
  qr_text?: string;
  passkey_stage?: string;
  passkey_open_url?: string;
  passkey_code?: string;
  passkey_error?: string;
  pairing_code?: string;
  provider_version?: string;
}

const TERMINAL_LABELS: Record<string, string> = {
  qr_expired: 'O QR code expirou. Nenhuma alteração foi feita no WhatsApp.',
  passkey_expired: 'A confirmação de segurança expirou. Nenhuma alteração foi feita no WhatsApp.',
  passkey_socket_restarted: 'A confirmação anterior perdeu a validade após uma reconexão segura.',
  re_pair_required: 'Esta sessão precisa ser pareada novamente.',
  provider_unavailable: 'O serviço de conexão está indisponível no momento.',
  db_pool_exhausted: 'O banco de sessões está temporariamente ocupado.',
  configuration_error: 'A configuração do canal precisa de ajuste pelo suporte.',
  timed_out: 'A tentativa terminou por tempo limite.',
  recoverable_error: 'A tentativa pode ser refeita com segurança.',
  technical_error: 'O pareamento encontrou um erro técnico.',
  cancelled: 'A tentativa foi cancelada sem alterar o WhatsApp.',
};

export function PairingStateView({
  pairing,
  secondsLeft,
  onRetry,
  onCancel,
  onContinuePasskey,
}: {
  pairing: PairingState;
  secondsLeft: number | null;
  onRetry: () => void;
  onCancel: () => void;
  onContinuePasskey: () => void;
}) {
  const state = pairing.state;
  const qr = pairing.qr_base64
    ? pairing.qr_base64.startsWith('data:')
      ? pairing.qr_base64
      : `data:image/png;base64,${pairing.qr_base64}`
    : null;
  const passkeyStates = [
    'passkey_required',
    'passkey_challenge',
    'passkey_awaiting_confirmation',
    'passkey_code_available',
  ];
  const passkey = passkeyStates.includes(state) || Boolean(pairing.passkey_stage);
  const terminalMessage = TERMINAL_LABELS[state];
  const canRetry = Boolean(terminalMessage) || state === 'passkey_failed';

  if (state === 'connected' || state === 'already_connected') {
    return (
      <p className="rounded-lg border border-success/40 bg-surface-2 px-3 py-2 text-xs text-foreground-2">
        ✅ WhatsApp conectado. O celular e o WhatsApp Web continuam funcionando normalmente.
      </p>
    );
  }

  if (passkey && state !== 'passkey_failed' && state !== 'passkey_expired') {
    return (
      <div className="space-y-3 rounded-lg border border-primary/30 bg-surface p-4">
        <div>
          <p className="text-sm font-semibold text-foreground">
            O WhatsApp pediu uma confirmação de segurança
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Essa conta exige uma chave de acesso para vincular um novo dispositivo. A confirmação é
            feita pela própria atendente, com biometria ou bloqueio do celular.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          Estágio: <span className="font-medium text-foreground">{pairing.passkey_stage || state}</span>
          {secondsLeft !== null ? ` · ${secondsLeft}s restantes` : ''}
        </p>
        {pairing.passkey_code && (
          <div className="rounded-lg border border-border bg-surface-2 p-3 text-center">
            <p className="text-[11px] text-muted-foreground">Código de confirmação</p>
            <p className="mt-1 font-mono text-xl font-bold tracking-[0.2em] text-foreground">
              {pairing.passkey_code}
            </p>
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          {pairing.passkey_open_url && (
            <Button asChild size="sm">
              <a href={pairing.passkey_open_url} target="_blank" rel="noreferrer">
                Abrir WhatsApp Web
              </a>
            </Button>
          )}
          <Button asChild variant="outline" size="sm">
            <a href="/tools/passkey-helper-autobrokers-0.7.2-ab1.zip" download>
              Instalar assistente de pareamento
            </a>
          </Button>
          <Button variant="outline" size="sm" onClick={onContinuePasskey}>
            Já instalei — continuar
          </Button>
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancelar tentativa
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground">
          O AutoBrokers não pede senha, PIN, passkey nem compartilhamento obrigatório de tela.
          Origem esperada: <span className="font-medium text-foreground">web.whatsapp.com</span>.
        </p>
      </div>
    );
  }

  if (state === 'passkey_failed') {
    return (
      <div className="space-y-3 rounded-lg border border-destructive/40 bg-surface p-4">
        <p className="text-sm font-semibold text-foreground">A confirmação de segurança não terminou</p>
        <p className="text-xs leading-relaxed text-muted-foreground">
          A conta não confirmou a chave de acesso. Não houve alteração no WhatsApp. Use o código de
          suporte abaixo para continuar com acompanhamento.
        </p>
        {pairing.support_ref && <p className="font-mono text-xs text-foreground">{pairing.support_ref}</p>}
        <Button variant="outline" size="sm" onClick={onRetry}>Gerar novo QR</Button>
      </div>
    );
  }

  if (state === 'qr_ready' && qr) {
    return (
      <div className="space-y-3 rounded-lg border border-primary/30 bg-surface p-3">
        <div className="flex flex-col items-center gap-2 rounded-lg border border-border bg-white p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={qr} alt="QR code do WhatsApp" className="h-64 w-64 max-w-full" />
          <p className="text-xs font-medium text-neutral-700">
            {secondsLeft !== null ? `${secondsLeft}s restantes` : 'Aguardando leitura do QR'}
          </p>
        </div>
        <ol className="list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
          <li>No celular, abra WhatsApp → Configurações → Dispositivos conectados.</li>
          <li>Toque em Conectar dispositivo.</li>
          <li>Aponte a câmera para este QR e aguarde a confirmação.</li>
        </ol>
        <p className="text-[11px] text-muted-foreground">
          O celular continuará funcionando normalmente durante e depois do pareamento.
        </p>
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancelar tentativa</Button>
      </div>
    );
  }

  if (pairing.pairing_code && !terminalMessage) {
    return (
      <div className="space-y-3 rounded-lg border border-primary/30 bg-surface p-4">
        <p className="text-sm font-semibold text-foreground">Código de pareamento</p>
        <p className="text-xs text-muted-foreground">
          No WhatsApp do celular, escolha conectar usando o número e informe o código abaixo.
        </p>
        <p className="rounded-lg border border-border bg-surface-2 p-3 text-center font-mono text-2xl font-bold tracking-[0.22em] text-foreground">
          {pairing.pairing_code}
        </p>
        <p className="text-[11px] text-muted-foreground">
          Esse método não evita uma confirmação por chave de acesso quando o WhatsApp a exige.
        </p>
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancelar tentativa</Button>
      </div>
    );
  }

  if (terminalMessage) {
    return (
      <div className="space-y-2 rounded-lg border border-border bg-surface p-3">
        <p className="text-xs text-foreground">{terminalMessage}</p>
        {pairing.support_ref && <p className="font-mono text-[11px] text-muted-foreground">{pairing.support_ref}</p>}
        {canRetry && <Button variant="outline" size="sm" onClick={onRetry}>Gerar novo QR</Button>}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-3 text-xs text-muted-foreground">
      {state === 'preparing_instance' ? 'Preparando a conexão…' : 'Aguardando o WhatsApp…'}
      {secondsLeft !== null ? ` · ${secondsLeft}s restantes` : ''}
    </div>
  );
}
