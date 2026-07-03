'use client';

// Canal WhatsApp da corretora (SPEC-017 P1.3) — Evolution + QR code.
// Card autocontido: status ao vivo, conexão por QR e número de alerta de
// desconexão (S17-3). Fala apenas com /api/dashboard/whatsapp-channel (sessão).

import { useCallback, useEffect, useRef, useState } from 'react';

import { DetailSection } from '@/components/patterns';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

type ChannelState = 'unknown' | 'connecting' | 'open' | 'close' | 'error' | 'not_configured';

interface StatusResponse {
  ok?: boolean;
  state?: string;
  connected?: boolean;
  instance?: string;
  detail?: string;
  error?: string;
}

const POLL_MS = 5000;

function stateLabel(state: ChannelState, connected: boolean): { text: string; tone: string } {
  if (connected) return { text: 'Conectado', tone: 'text-success' };
  if (state === 'connecting') return { text: 'Aguardando QR code…', tone: 'text-warning' };
  if (state === 'close') return { text: 'Desconectado', tone: 'text-destructive' };
  if (state === 'not_configured') return { text: 'Não configurado', tone: 'text-muted-foreground' };
  if (state === 'error') return { text: 'Indisponível', tone: 'text-destructive' };
  return { text: 'Verificando…', tone: 'text-muted-foreground' };
}

export function WhatsAppChannelCard() {
  const [state, setState] = useState<ChannelState>('unknown');
  const [connected, setConnected] = useState(false);
  const [qr, setQr] = useState<string | null>(null);
  const [alertNumber, setAlertNumber] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [diag, setDiag] = useState<Record<string, unknown> | null>(null);

  const loadDiagnostics = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/whatsapp-channel?action=diagnostics', { cache: 'no-store' });
      const json = await res.json().catch(() => ({}));
      setDiag(json && typeof json === 'object' ? json : null);
    } catch {
      setDiag(null);
    }
  }, []);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wantQrRef = useRef(false);

  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/whatsapp-channel?action=status', { cache: 'no-store' });
      const json: StatusResponse = await res.json().catch(() => ({}));
      if (res.status === 503 || json.detail === 'evolution_not_configured') {
        setState('not_configured');
        setConnected(false);
        return;
      }
      if (!res.ok) {
        setState('error');
        return;
      }
      const s = String(json.state || 'unknown').toLowerCase();
      setConnected(Boolean(json.connected));
      setState((s as ChannelState) || 'unknown');
      if (json.connected) {
        setQr(null);
        wantQrRef.current = false;
      } else if (wantQrRef.current) {
        const qres = await fetch('/api/dashboard/whatsapp-channel?action=qr', { cache: 'no-store' });
        const qjson = await qres.json().catch(() => ({}));
        if (qres.ok && qjson.qr_base64) {
          const raw = String(qjson.qr_base64);
          // Só renderiza como imagem o que É imagem (data URI ou base64 puro).
          const looksBase64 = raw.startsWith('data:') || (raw.length > 200 && !raw.includes(' '));
          if (looksBase64) setQr(raw.startsWith('data:') ? raw : `data:image/png;base64,${raw}`);
        } else if (qres.ok && qjson.qr_text) {
          setMessage('QR gerado em formato texto pelo servidor — clique em "Gerar novo QR" para tentar a imagem novamente.');
        }
      }
    } catch {
      setState('error');
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    loadDiagnostics();
    pollRef.current = setInterval(refreshStatus, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [refreshStatus, loadDiagnostics]);

  const handleConnect = async () => {
    setBusy(true);
    setMessage('');
    try {
      const res = await fetch('/api/dashboard/whatsapp-channel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'setup', alert_number: alertNumber || undefined }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || json.ok === false) {
        setMessage(String(json.error || json.detail || 'Não foi possível iniciar a conexão.'));
        await loadDiagnostics();
      } else {
        wantQrRef.current = true;
        setMessage('Instância pronta. Escaneie o QR code com o WhatsApp da corretora (Aparelhos conectados).');
        await refreshStatus();
      }
    } catch {
      setMessage('Falha de comunicação com o servidor.');
    } finally {
      setBusy(false);
    }
  };

  const label = stateLabel(state, connected);

  return (
    <DetailSection>
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2">
              <Icon icon={icons.whatsapp ?? icons.conectores} size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">WhatsApp da corretora</p>
              <p className="text-xs text-muted-foreground">
                Canal de atendimento aos segurados (Evolution · QR code · sem mensalidade).
              </p>
            </div>
          </div>
          <span className={`text-xs font-medium ${label.tone}`}>{label.text}</span>
        </div>

        {state === 'not_configured' && (
          <p className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
            O serviço Evolution ainda não foi configurado pela plataforma (EVOLUTION_BASE_URL/EVOLUTION_API_KEY).
          </p>
        )}

        {!connected && state !== 'not_configured' && (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-foreground-2">
              <span className="font-semibold">É AQUI que você conecta o WhatsApp de atendimento da corretora.</span>{' '}
              Clique em “Gerar QR code” e escaneie com o celular do número de atendimento.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-foreground-2">
                  Passo 1 (opcional) — número de ALERTA se a conexão cair (outro número, nunca o de atendimento)
                </label>
                <input
                  value={alertNumber}
                  onChange={(e) => setAlertNumber(e.target.value)}
                  placeholder="Ex.: 5548999998888"
                  className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none focus:border-primary/60"
                />
              </div>
              <Button onClick={handleConnect} disabled={busy}>
                {busy ? 'Preparando…' : qr ? 'Gerar novo QR' : 'Passo 2 — Gerar QR code'}
              </Button>
            </div>
          </div>
        )}

        {diag && !connected && (
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-foreground-2">
            <p className="mb-1 font-semibold text-foreground">Diagnóstico do canal</p>
            <ul className="space-y-0.5">
              <li>{diag.evolution_base_url_set ? '✅' : '❌'} EVOLUTION_BASE_URL configurada</li>
              <li>{diag.evolution_api_key_set ? '✅' : '❌'} EVOLUTION_API_KEY configurada</li>
              <li>{diag.public_backend_url_set ? '✅' : '❌'} PUBLIC_BACKEND_URL configurada</li>
              <li>
                {diag.evolution_reachable ? '✅' : '❌'} Servidor Evolution alcançável
                {diag.evolution_http_status ? ` (HTTP ${String(diag.evolution_http_status)})` : ''}
                {diag.evolution_version ? ` · v${String(diag.evolution_version)}` : ''}
              </li>
              <li>ℹ️ Instância: {String(diag.instance || '-')} · estado: {String(diag.instance_state || '-')}</li>
              {typeof diag.error === 'string' && diag.error ? <li>❗ {diag.error}</li> : null}
            </ul>
            <p className="mt-1 text-faint">Me envie um print deste diagnóstico se continuar falhando.</p>
          </div>
        )}

        {qr && !connected && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-border bg-white p-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qr} alt="QR code do WhatsApp" className="h-56 w-56" />
            <p className="text-center text-xs text-neutral-600">
              WhatsApp → Configurações → Aparelhos conectados → Conectar aparelho.
              O QR expira rápido; se falhar, clique em “Gerar novo QR”.
            </p>
          </div>
        )}

        {connected && (
          <p className="rounded-lg border border-success/40 bg-surface-2 px-3 py-2 text-xs text-foreground-2">
            ✅ WhatsApp conectado. Se cair, o número de alerta configurado recebe aviso imediato para reconectar.
          </p>
        )}

        {message && <p className="text-xs text-muted-foreground">{message}</p>}
      </div>
    </DetailSection>
  );
}
