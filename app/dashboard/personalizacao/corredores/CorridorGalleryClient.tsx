'use client';

// SPEC-063 (03/08/2026) — UM CARD POR (SEGURADORA × RAMO).
//
// Decisão do founder, literal:
//   "o corretor não quer saber se tem subcorredores, subserviços... vai
//    confundir ele. Allianz Residencial e aí já vai tudo no pacote. Ele só
//    precisa saber que Allianz Residencial está sendo atendida."
//
// Então os subserviços aparecem DENTRO do card, como TEXTO. Nunca como coisa
// ligável: quem liga e desliga é o corredor. Antes esta tela mostrava
// "Allianz Residencial" E "Allianz Residencial — Eletricista" como dois cards
// (e só esses dois, porque lia `corridor_templates` em vez do código).
//
// E O CARD DIZ A VERDADE SOBRE O QUE FAZ. Alguns corredores ABREM o chamado até
// o protocolo; outros só ENCAMINHAM — 📊 o vidro da Porto termina num
// formulário e o da Zurich numa orientação. Prometer abertura onde só há
// encaminhamento é a mentira que a SPEC-063 acabou de tirar da tela de
// Seguradoras; ela não volta por aqui.

import { useCallback, useEffect, useState } from 'react';

type Subservice = {
  key: string;
  label: string;
  outcome: string;           // 'abre' | 'encaminha'
  referral_kind: string | null;
  menu_mapeado: boolean;
};

type Item = {
  corridor_id: string;
  title: string;
  insurer_key: string | null;
  insurer_label: string;
  line_label: string;
  channel_label: string;
  subservices: Subservice[];
  outcome_summary: string;   // 'abre' | 'encaminha' | 'misto'
  handoff_sinistro: boolean;
  menu_mapeado: boolean;
  status: 'available' | 'active' | 'paused';
  installed: boolean;
  next_step: string;
};

const STATUS_META: Record<string, { label: string; cls: string }> = {
  active: { label: 'Ativo', cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' },
  paused: { label: 'Pausado', cls: 'border-amber-500/30 bg-amber-500/10 text-amber-600' },
  available: { label: 'Disponível', cls: 'border-border bg-surface-2 text-muted-foreground' },
};

/** Como a seguradora entrega o encaminhamento (vem do playbook). */
const REFERRAL_LABEL: Record<string, string> = {
  formulario: 'um formulário',
  orientacao: 'uma orientação',
};

export function CorridorGalleryClient() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [busy, setBusy] = useState<string>('');
  const [notice, setNotice] = useState('');
  const [erroDeLeitura, setErroDeLeitura] = useState('');

  const load = useCallback(async () => {
    const j = await fetch('/api/dashboard/corridors').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) { setItems(j.items); setErroDeLeitura(''); return; }
    // Sem catálogo, a tela NÃO inventa uma lista menor: ela diz que não leu.
    setItems([]);
    setErroDeLeitura(
      j?.error === 'catalogo_indisponivel'
        ? 'Não consegui ler o catálogo de corredores do motor de atendimento. Nada foi alterado — tente de novo em instantes.'
        : `Falha ao carregar os corredores (${j?.error || 'erro desconhecido'}).`,
    );
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (corridorId: string, action: 'activate' | 'pause' | 'resume') => {
    setBusy(corridorId); setNotice('');
    const r = await fetch(`/api/dashboard/corridors/${encodeURIComponent(corridorId)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) await load(); else setNotice(`Falha: ${j?.error || r.status}`);
    setBusy('');
  };

  if (!items) return <p className="text-sm text-muted-foreground">Carregando…</p>;
  if (erroDeLeitura) return <p className="text-sm text-amber-600">{erroDeLeitura}</p>;
  if (items.length === 0) return <p className="text-sm text-muted-foreground">Nenhum corredor disponível ainda.</p>;

  return (
    <div className="space-y-3">
      {notice && <p className="text-[12px] text-amber-600">{notice}</p>}
      {items.map((it) => {
        const meta = STATUS_META[it.status] ?? STATUS_META.available;
        const abrem = it.subservices.filter((s) => s.outcome !== 'encaminha');
        const encaminham = it.subservices.filter((s) => s.outcome === 'encaminha');
        return (
          <div key={it.corridor_id} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">{it.title}</p>
                <p className="mt-0.5 text-[11px] text-faint">{it.channel_label}</p>
              </div>
              <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${meta.cls}`}>{meta.label}</span>
            </div>

            {/* Os subserviços do pacote — TEXTO. Não há nada para ligar aqui. */}
            {it.subservices.length > 0 && (
              <p className="mt-2 text-[12px] text-muted-foreground">
                {it.subservices.map((s) => s.label).join(' · ')}
              </p>
            )}

            <div className="mt-3 space-y-1 text-[11px] text-muted-foreground">
              {abrem.length > 0 && (
                <p>
                  {it.menu_mapeado
                    ? 'Atende sozinho até o protocolo.'
                    : 'Chega até a seguradora e uma pessoa assume: o menu de serviço desta seguradora ainda não foi mapeado.'}
                </p>
              )}
              {encaminham.map((s) => (
                <p key={s.key}>
                  {s.label}: a seguradora não abre chamado por aqui — ela entrega{' '}
                  {REFERRAL_LABEL[s.referral_kind ?? ''] ?? 'um caminho'} e o atendimento encerra com isso.
                </p>
              ))}
              {it.handoff_sinistro && <p>Sinistro e risco grave sempre vão para um humano.</p>}
            </div>

            <p className="mt-2 text-[11px] text-faint">{it.next_step}</p>

            <div className="mt-3 flex flex-wrap gap-2">
              {it.status === 'available' && (
                <button onClick={() => act(it.corridor_id, 'activate')} disabled={busy === it.corridor_id} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Ativar</button>
              )}
              {it.status === 'active' && (
                <button onClick={() => act(it.corridor_id, 'pause')} disabled={busy === it.corridor_id} className="rounded-lg border border-border px-3 py-1 text-[12px] text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Pausar</button>
              )}
              {it.status === 'paused' && (
                <button onClick={() => act(it.corridor_id, 'resume')} disabled={busy === it.corridor_id} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50">Retomar</button>
              )}
            </div>
          </div>
        );
      })}
      <p className="text-[10px] text-faint">
        Ativar um corredor apenas o disponibiliza para a corretora: registra que ela usa este
        corredor. Quem aciona a seguradora é o roteiro de atendimento, e ele é o mesmo para
        todas — nenhuma ação externa, envio ou portal é executado por esta tela.
      </p>
    </div>
  );
}
