'use client';

// Canal WhatsApp da corretora (SPEC-017 / SPEC-049).
// PASSO 1 = QR code com instruções (o que importa). PASSO 2 = aviso de queda,
// OPCIONAL e editável a qualquer momento (número próprio OU o grupo do
// suporte humano — o mesmo dos dossiês). O diagnóstico técnico da Evolution
// saiu da tela (era interno da plataforma e só confundia o corretor).

import { useCallback, useEffect, useRef, useState } from 'react';

import { DetailSection } from '@/components/patterns';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

import { WhatsAppPairingFlow } from './WhatsAppPairingFlow';

type ChannelState = 'unknown' | 'connecting' | 'open' | 'close' | 'error' | 'not_configured';

interface StatusResponse {
  ok?: boolean;
  state?: string;
  connected?: boolean;
  instance?: string;
  detail?: string;
  error?: string;
  alert?: { mode: 'number' | 'support' | null; number: string | null };
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
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  // SPEC-049 — aviso de queda (passo 2, opcional, sempre editável)
  const [alertMode, setAlertMode] = useState<'number' | 'support' | 'off'>('off');
  const [alertNumber, setAlertNumber] = useState('');
  const [alertSaved, setAlertSaved] = useState<{ mode: string | null; number: string | null }>({ mode: null, number: null });
  const [alertBusy, setAlertBusy] = useState(false);
  const [alertMsg, setAlertMsg] = useState('');

  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusInFlightRef = useRef(false);
  const alertLoadedRef = useRef(false);

  const refreshStatus = useCallback(async () => {
    if (statusInFlightRef.current) return;
    statusInFlightRef.current = true;
    try {
      const res = await fetch('/api/dashboard/whatsapp-channel?action=status', { cache: 'no-store' });
      const json: StatusResponse = await res.json().catch(() => ({}));
      if (res.status === 503 || json.detail === 'evolution_go_not_configured' || json.detail === 'evolution_not_configured') {
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
      // Config do aviso salva no servidor — carrega UMA vez (não sobrescreve
      // o que a pessoa está digitando a cada poll).
      if (!alertLoadedRef.current && json.alert) {
        alertLoadedRef.current = true;
        setAlertSaved(json.alert);
        if (json.alert.mode === 'support') setAlertMode('support');
        else if (json.alert.mode === 'number') { setAlertMode('number'); setAlertNumber(json.alert.number || ''); }
      }
      if (json.connected) {
        setMessage('');
      }
    } catch {
      setState('error');
    } finally {
      statusInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    let active = true;
    const pollStatus = async () => {
      await refreshStatus();
      if (active) pollRef.current = setTimeout(() => void pollStatus(), POLL_MS);
    };
    void pollStatus();
    return () => {
      active = false;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [refreshStatus]);

  const saveAlert = async () => {
    setAlertBusy(true);
    setAlertMsg('');
    try {
      const res = await fetch('/api/dashboard/whatsapp-channel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'set-alert', mode: alertMode, alert_number: alertMode === 'number' ? alertNumber : undefined }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || json.ok === false) {
        const d = String(json.error || json.detail || '');
        setAlertMsg(
          d.includes('numero_igual_ao_pareado') ? 'Use OUTRO número — este é o próprio número pareado.'
            : d.includes('numero_invalido') ? 'Número inválido (use DDI+DDD+número, ex.: 5548999998888).'
              : d.includes('canal_nao_configurado') ? 'Gere o QR code primeiro (Passo 1) — depois configure o aviso.'
                : 'Não foi possível salvar o aviso.',
        );
      } else {
        setAlertSaved(json.alert || { mode: alertMode === 'off' ? null : alertMode, number: alertNumber || null });
        setAlertMsg('Aviso salvo. ✓');
      }
    } catch {
      setAlertMsg('Falha de comunicação com o servidor.');
    } finally {
      setAlertBusy(false);
    }
  };

  // Founder 14/07: sem Desconectar não há como tirar o número pelo dashboard.
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const handleDisconnect = async () => {
    if (!confirmDisconnect) {
      setConfirmDisconnect(true);
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const res = await fetch('/api/dashboard/whatsapp-channel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'disconnect' }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || json.ok === false) {
        setMessage(String(json.error || json.detail || 'Não foi possível desconectar.'));
      } else {
        setConnected(false);
        setState('close');
        setMessage('WhatsApp desconectado. Para reconectar, gere um novo QR code.');
      }
    } catch {
      setMessage('Falha de comunicação com o servidor.');
    } finally {
      setConfirmDisconnect(false);
      setBusy(false);
    }
  };

  const label = stateLabel(state, connected);
  const alertSummary = alertSaved.mode === 'support'
    ? 'Aviso vai para o grupo do suporte humano (o mesmo dos dossiês).'
    : alertSaved.mode === 'number' && alertSaved.number
      ? `Aviso vai para o número ${alertSaved.number}.`
      : 'Nenhum aviso configurado ainda — recomendamos configurar.';

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
                O número que atende seus segurados — conecte por QR code em 2 minutos.
              </p>
            </div>
          </div>
          <span className={`text-xs font-medium ${label.tone}`}>{label.text}</span>
        </div>

        {state === 'not_configured' && (
          <p className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
            O canal ainda não foi liberado pela plataforma para esta corretora — fale com o suporte AutoBrokers.
          </p>
        )}

        {/* ---------- PASSO 1 — PAREAMENTO CONTROLADO ---------- */}
        {!connected && state !== 'not_configured' && (
          <WhatsAppPairingFlow
            onConnected={() => {
              setConnected(true);
              setState('open');
              setMessage('');
            }}
          />
        )}

        {connected && (
          <div className="flex flex-col gap-3">
            <p className="rounded-lg border border-success/40 bg-surface-2 px-3 py-2 text-xs text-foreground-2">
              ✅ WhatsApp conectado. A equipe continua atendendo pelo celular normalmente — e o
              atendimento NÃO cai se o celular ficar sem bateria ou sem internet por um tempo.
            </p>
            <div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-surface-2 px-3 py-2">
              <p className="text-xs text-muted-foreground">
                {confirmDisconnect
                  ? 'Tem certeza? O atendimento por WhatsApp para de funcionar até reconectar.'
                  : 'Precisa trocar de número? Desconecte aqui e gere um novo QR.'}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDisconnect}
                disabled={busy}
                className="shrink-0 border-destructive/50 text-destructive hover:bg-destructive/10"
              >
                {busy ? 'Desconectando…' : confirmDisconnect ? 'Confirmar desconexão' : 'Desconectar'}
              </Button>
            </div>
          </div>
        )}

        {/* ---------- PASSO 2 — AVISO DE QUEDA (opcional, sempre editável) ---------- */}
        {state !== 'not_configured' && (
          <div className="rounded-lg border border-border bg-surface p-3">
            <p className="text-xs font-semibold text-foreground">Passo 2 (opcional) — Aviso se a conexão cair</p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Se o WhatsApp de atendimento desconectar, mandamos um aviso na hora para reconectar.
              {' '}{alertSummary} Você pode configurar ou trocar isso quando quiser.
            </p>
            <div className="mt-2 space-y-2">
              <label className="flex items-start gap-2 text-xs text-foreground">
                <input
                  type="radio"
                  name="alert-mode"
                  checked={alertMode === 'support'}
                  onChange={() => setAlertMode('support')}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium">Grupo do suporte humano</span>{' '}
                  <span className="text-muted-foreground">— o mesmo grupo que já recebe os dossiês; todo mundo vê o aviso. (Recomendado)</span>
                </span>
              </label>
              <label className="flex items-start gap-2 text-xs text-foreground">
                <input
                  type="radio"
                  name="alert-mode"
                  checked={alertMode === 'number'}
                  onChange={() => setAlertMode('number')}
                  className="mt-0.5"
                />
                <span className="flex-1">
                  <span className="font-medium">Outro número de WhatsApp</span>{' '}
                  <span className="text-muted-foreground">— nunca o número pareado (ele estará fora do ar).</span>
                  {alertMode === 'number' && (
                    <input
                      value={alertNumber}
                      onChange={(e) => setAlertNumber(e.target.value)}
                      placeholder="Ex.: 5548999998888"
                      className="mt-1 w-full rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none focus:border-primary/60"
                    />
                  )}
                </span>
              </label>
              <label className="flex items-start gap-2 text-xs text-foreground">
                <input
                  type="radio"
                  name="alert-mode"
                  checked={alertMode === 'off'}
                  onChange={() => setAlertMode('off')}
                  className="mt-0.5"
                />
                <span className="text-muted-foreground">Sem aviso por enquanto</span>
              </label>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={saveAlert} disabled={alertBusy}>
                {alertBusy ? 'Salvando…' : 'Salvar aviso'}
              </Button>
              {alertMsg && <span className="text-[11px] text-muted-foreground">{alertMsg}</span>}
            </div>
          </div>
        )}

        {message && <p className="text-xs text-muted-foreground">{message}</p>}
      </div>
    </DetailSection>
  );
}
