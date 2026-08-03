'use client';

// SPEC-045 — Hub de WhatsApp por FUNÇÃO (mobile-first, linguagem humana).
// Função 1: Atendimento & Acionamentos (obrigatória, 1 por corretora).
// Função 2: Auxiliares & Avisos (opcional — por padrão usa o mesmo número,
// com a FILA DE CORTESIA: aviso nunca atropela um atendimento em andamento).

import { useCallback, useEffect, useState } from 'react';
import { Loader2, MessageCircle, ShieldCheck } from 'lucide-react';

import { StatusPill } from '@/components/patterns';
import { WhatsAppChannelModal } from '@/components/vault/WhatsAppChannelModal';

export function WhatsAppHubClient() {
  const [status, setStatus] = useState<{ connected: boolean; instance?: string } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [provaAberta, setProvaAberta] = useState(false);
  const [paraNumero, setParaNumero] = useState('');
  const [provando, setProvando] = useState(false);
  const [resultado, setResultado] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(() => {
    fetch('/api/dashboard/whatsapp-channel?action=status', { cache: 'no-store' })
      .then((r) => r.json())
      .then((j) => setStatus({ connected: Boolean(j?.connected), instance: j?.instance }))
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-4">
      {/* Função 1 — Atendimento & Acionamentos */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
            <MessageCircle className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-foreground">Atendimento & Acionamentos</p>
              {status === null ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
              ) : (
                <StatusPill
                  tone={status.connected ? 'success' : 'warning'}
                  label={status.connected ? 'Conectado' : 'Aguardando conexão'}
                />
              )}
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              O número que recebe os seus segurados e aciona as seguradoras. Na fase de observação,
              a equipe humana atende por ele e o sistema aprende em silêncio — ligar o agente
              (em Corretora → Agente de Atendimento) ativa as respostas automáticas
              <span className="font-medium text-foreground"> neste mesmo número</span>.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => setModalOpen(true)}
                className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/10"
              >
                {status?.connected ? 'Gerenciar conexão' : 'Conectar número (QR code)'}
              </button>
              {status?.connected ? (
                <button
                  onClick={() => setProvaAberta((v) => !v)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-surface-2"
                >
                  Provar envio de formulário
                </button>
              ) : null}
            </div>

            {/* Diagnóstico: algumas seguradoras respondem com um formulário
                dentro do WhatsApp. Saber ANTES se este canal consegue devolvê-lo
                vale mais do que descobrir no meio de um acionamento, onde a URA
                fecha em minutos e não avisa que descartou a resposta. */}
            {provaAberta ? (
              <div className="mt-3 rounded-lg border border-border bg-surface-2 p-3">
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Envia uma resposta de formulário de verdade, deste número para outro. Use um
                  número <span className="font-medium text-foreground">seu</span> — vai chegar uma
                  mensagem técnica lá.
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    value={paraNumero}
                    onChange={(e) => setParaNumero(e.target.value)}
                    placeholder="DDD + número de destino"
                    inputMode="numeric"
                    className="min-w-0 flex-1 rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground"
                  />
                  <button
                    disabled={provando || !paraNumero.replace(/\D/g, '')}
                    onClick={async () => {
                      setProvando(true);
                      setResultado(null);
                      try {
                        const r = await fetch('/api/dashboard/prova-de-formulario', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ para: paraNumero }),
                        });
                        setResultado(await r.json());
                      } catch {
                        setResultado({ success: false, frase: 'Não consegui enviar.' });
                      } finally {
                        setProvando(false);
                      }
                    }}
                    className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
                  >
                    {provando ? 'Enviando…' : 'Enviar prova'}
                  </button>
                </div>
                {resultado ? (
                  <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-border bg-card p-2 text-[11px] leading-relaxed text-muted-foreground">
                    {JSON.stringify(resultado, null, 2)}
                  </pre>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Função 2 — Auxiliares & Avisos */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-foreground">Auxiliares & Avisos</p>
              <StatusPill tone="info" label="Usa o número do Atendimento" />
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Cobranças, campanhas e avisos saem pelo número do atendimento — com a
              <span className="font-medium text-foreground"> fila de cortesia</span>: se o cliente
              estiver em atendimento, o aviso espera a conversa terminar. E quando ele responde a uma
              cobrança, o agente já sabe do que se trata. Para corretoras com muito volume, um número
              dedicado para esta função poderá ser conectado aqui em breve.
            </p>
          </div>
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground">
        Regra de ouro: números são por <span className="font-medium text-foreground">função</span>,
        nunca por pessoa. Relatórios pessoais dos usuários chegam pelo número da corretora,
        endereçados ao WhatsApp de cada um.
      </p>

      <WhatsAppChannelModal open={modalOpen} onOpenChange={(o) => { setModalOpen(o); if (!o) load(); }} />
    </div>
  );
}
