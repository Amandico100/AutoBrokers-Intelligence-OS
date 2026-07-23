'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';

import { PairingState, PairingStateView } from './PairingStateView';

const STORAGE_KEY = 'autobrokers-whatsapp-observer-attempt';
const TERMINAL = new Set([
  'connected', 'already_connected', 'qr_expired', 'passkey_expired', 'passkey_failed',
  'passkey_socket_restarted', 're_pair_required', 'provider_unavailable',
  'db_pool_exhausted', 'configuration_error', 'timed_out', 'recoverable_error',
  'technical_error', 'cancelled',
]);

export function WhatsAppPairingFlow({ onConnected }: { onConnected?: () => void }) {
  const [pairing, setPairing] = useState<PairingState | null>(null);
  const [busy, setBusy] = useState(false);
  const [phoneMode, setPhoneMode] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clockTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inFlightRef = useRef(false);
  const mountedRef = useRef(true);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    pollTimerRef.current = null;
  }, []);

  const resetToStart = useCallback(() => {
    stopPolling();
    sessionStorage.removeItem(STORAGE_KEY);
    if (!mountedRef.current) return;
    setPairing(null);
    setSecondsLeft(null);
  }, [stopPolling]);

  const applyState = useCallback((next: PairingState) => {
    if (!mountedRef.current) return;
    setPairing(next);
    if (TERMINAL.has(next.state)) {
      sessionStorage.removeItem(STORAGE_KEY);
    } else if (next.attempt_id) {
      sessionStorage.setItem(STORAGE_KEY, next.attempt_id);
    }
    if (next.state === 'connected' || next.state === 'already_connected') {
      onConnected?.();
    }
  }, [onConnected]);

  const poll = useCallback(async (attemptId: string) => {
    if (inFlightRef.current || !mountedRef.current) return;
    inFlightRef.current = true;
    try {
      const response = await fetch(
        `/api/dashboard/whatsapp-channel?action=pairing&attempt_id=${encodeURIComponent(attemptId)}`,
        { cache: 'no-store' },
      );
      const json = (await response.json().catch(() => ({}))) as PairingState & { detail?: string };
      if (!response.ok) {
        const detail = String(json.detail || '');
        if (response.status === 404 || detail === 'pairing_not_found') {
          resetToStart();
          return;
        }
        applyState({
          attempt_id: attemptId,
          state: response.status === 504 ? 'timed_out' : 'technical_error',
          error: detail || 'Falha ao consultar a tentativa.',
        });
        return;
      }
      applyState(json);
      if (!TERMINAL.has(json.state) && json.attempt_id) {
        stopPolling();
        pollTimerRef.current = setTimeout(
          () => void poll(json.attempt_id!),
          Math.max(800, Number(json.poll_after_ms || 1500)),
        );
      }
    } catch {
      applyState({ attempt_id: attemptId, state: 'provider_unavailable', error: 'Falha de comunicação com o servidor.' });
    } finally {
      inFlightRef.current = false;
    }
  }, [applyState, resetToStart, stopPolling]);

  const start = useCallback(async (action: 'pairing' | 'retry' = 'pairing') => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setBusy(true);
    stopPolling();
    if (action === 'pairing') {
      sessionStorage.removeItem(STORAGE_KEY);
      setPairing(null);
      setSecondsLeft(null);
    }
    try {
      const response = await fetch('/api/dashboard/whatsapp-channel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          attempt_id: action === 'retry' ? pairing?.attempt_id : undefined,
          method: phoneMode ? 'phone' : 'qr',
          phone_number: phoneMode ? phoneNumber : undefined,
        }),
      });
      const json = (await response.json().catch(() => ({}))) as PairingState & { detail?: string };
      if (!response.ok) {
        const detail = String(json.detail || json.error || '');
        if (response.status === 404 || detail === 'pairing_not_found') {
          resetToStart();
          return;
        }
        applyState({
          attempt_id: action === 'retry' ? pairing?.attempt_id : undefined,
          state: response.status === 409 ? 'recoverable_error' : response.status === 504 ? 'timed_out' : 'technical_error',
          error: detail || 'Não foi possível iniciar o pareamento.',
        });
        return;
      }
      applyState(json);
      if (!TERMINAL.has(json.state) && json.attempt_id) {
        pollTimerRef.current = setTimeout(
          () => void poll(json.attempt_id!),
          Math.max(800, Number(json.poll_after_ms || 1200)),
        );
      }
    } catch {
      applyState({
        attempt_id: action === 'retry' ? pairing?.attempt_id : undefined,
        state: 'provider_unavailable',
        error: 'Falha de comunicação com o servidor.',
      });
    } finally {
      inFlightRef.current = false;
      setBusy(false);
    }
  }, [applyState, pairing?.attempt_id, phoneMode, phoneNumber, poll, resetToStart, stopPolling]);

  const cancel = useCallback(async () => {
    if (!pairing?.attempt_id || inFlightRef.current) return;
    inFlightRef.current = true;
    stopPolling();
    try {
      const response = await fetch('/api/dashboard/whatsapp-channel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'cancel', attempt_id: pairing.attempt_id }),
      });
      const json = (await response.json().catch(() => ({}))) as PairingState & { detail?: string };
      if (!response.ok) {
        applyState({
          attempt_id: pairing.attempt_id,
          state: 'recoverable_error',
          error: String(json.detail || json.error || 'Não foi possível cancelar agora.'),
          error_code: response.status === 409 ? 'pairing_state_busy' : 'cancel_failed',
        });
        return;
      }
      applyState(json.state ? json : { attempt_id: pairing.attempt_id, state: 'cancelled' });
    } catch {
      applyState({
        attempt_id: pairing.attempt_id,
        state: 'provider_unavailable',
        error: 'Falha de comunicação com o servidor.',
      });
    } finally {
      inFlightRef.current = false;
    }
  }, [applyState, pairing?.attempt_id, stopPolling]);

  useEffect(() => {
    mountedRef.current = true;
    const previous = sessionStorage.getItem(STORAGE_KEY);
    if (previous) void poll(previous);
    return () => {
      mountedRef.current = false;
      stopPolling();
      if (clockTimerRef.current) clearTimeout(clockTimerRef.current);
    };
  }, [poll, stopPolling]);

  useEffect(() => {
    if (clockTimerRef.current) clearTimeout(clockTimerRef.current);
    const tick = () => {
      const expiry = pairing?.expires_at ? Date.parse(pairing.expires_at) : Number.NaN;
      setSecondsLeft(Number.isFinite(expiry) ? Math.max(0, Math.ceil((expiry - Date.now()) / 1000)) : null);
      if (Number.isFinite(expiry) && expiry > Date.now() && !TERMINAL.has(pairing?.state || '')) {
        clockTimerRef.current = setTimeout(tick, 1000);
      }
    };
    tick();
    return () => {
      if (clockTimerRef.current) clearTimeout(clockTimerRef.current);
    };
  }, [pairing?.expires_at, pairing?.state]);

  if (pairing) {
    return (
      <PairingStateView
        pairing={pairing}
        secondsLeft={secondsLeft}
        onRetry={() => void start(TERMINAL.has(pairing.state) ? 'pairing' : pairing.attempt_id ? 'retry' : 'pairing')}
        onCancel={() => void cancel()}
        onContinuePasskey={() => pairing.attempt_id && void poll(pairing.attempt_id)}
      />
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-primary/30 bg-surface p-3">
      <p className="text-xs font-semibold text-foreground">Passo 1 — Conectar o número de trabalho</p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Use o número que a equipe já utiliza. O celular continuará funcionando normalmente.
      </p>
      {phoneMode && (
        <div className="space-y-1">
          <label className="text-xs font-medium text-foreground" htmlFor="pairing-phone">Número com DDI e DDD</label>
          <input
            id="pairing-phone"
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
            placeholder="Ex.: 5548999998888"
            className="w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none focus:border-primary/60"
          />
          <p className="text-[11px] text-muted-foreground">
            Esse método não evita a confirmação por chave de acesso quando o WhatsApp a exige.
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void start()} disabled={busy || (phoneMode && phoneNumber.replace(/\D/g, '').length < 10)}>
          {busy ? 'Preparando a conexão…' : phoneMode ? 'Gerar código de pareamento' : 'Gerar QR code'}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setPhoneMode((value) => !value)} disabled={busy}>
          {phoneMode ? 'Voltar ao QR code' : 'Conectar usando número'}
        </Button>
      </div>
    </div>
  );
}
