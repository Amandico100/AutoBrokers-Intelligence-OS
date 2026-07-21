'use client';

import { useCallback, useEffect, useState } from 'react';

type Option = { value: string; label: string };
type Variable = { key: string; label: string; value: string; input_kind: 'text' | 'textarea' | 'select'; options: Option[]; max_length: number };
type OverrideField = { key: string; input_kind: 'text' | 'textarea' | 'select' | 'url' | 'number'; options: Option[] };
type Config = {
  blueprint_version: string;
  role: string;
  brand_locked_name: string | null;
  display_name: string;
  editable_variables: Variable[];
  editable_override_fields: OverrideField[];
  current_overrides: Record<string, unknown>;
};

const OVERRIDE_LABEL: Record<string, string> = {
  avatar_url: 'Avatar (URL https da imagem)',
  voice: 'Voz',
  llm_temperature: 'Criatividade (0.0–1.0)',
  idioma: 'Idioma',
};

const inputCls = 'mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground';

export function AgentConfigClient({ agentKey }: { agentKey: 'autobrokers' | 'even' }) {
  const [config, setConfig] = useState<Config | null>(null);
  const [provisioned, setProvisioned] = useState(true);
  const [isActive, setIsActive] = useState<boolean | null>(null); // SPEC-045: toggle (attendance)
  const [vars, setVars] = useState<Record<string, string>>({});
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [errors, setErrors] = useState<string[]>([]);

  const load = useCallback(async () => {
    const j = await fetch(`/api/dashboard/agents/${agentKey}`).then((r) => r.json()).catch(() => ({}));
    if (j?.ok) {
      setProvisioned(Boolean(j.provisioned));
      setIsActive(typeof j?.agent?.is_active === 'boolean' ? j.agent.is_active : null);
      const c: Config = j.config;
      setConfig(c);
      const v: Record<string, string> = {};
      for (const it of c.editable_variables) v[it.key] = it.value;
      setVars(v);
      const o: Record<string, string> = {};
      for (const f of c.editable_override_fields) o[f.key] = c.current_overrides?.[f.key] != null ? String(c.current_overrides[f.key]) : '';
      setOverrides(o);
    } else setNotice(j?.error || 'Falha ao carregar.');
  }, [agentKey]);
  useEffect(() => { load(); }, [load]);

  // SPEC-045 — botão LIGAR/DESLIGAR (só o agente de atendimento). O Observador
  // e o Espelho NUNCA desligam — o botão governa apenas se o agente RESPONDE.
  const toggleActive = async () => {
    if (isActive === null || busy) return;
    const turningOn = !isActive;
    const msg = turningOn
      ? 'Ligar o agente? A partir de agora ELE responde os segurados neste número (a captura e o aprendizado continuam).'
      : 'Desligar o agente? O número continua conectado: a equipe humana atende e o sistema segue observando e aprendendo — o agente só para de responder.';
    if (!window.confirm(msg)) return;
    setBusy(true); setNotice('');
    const r = await fetch(`/api/dashboard/agents/${agentKey}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: turningOn }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setIsActive(Boolean(j.is_active)); setNotice(turningOn ? 'Agente LIGADO — atendendo os segurados.' : 'Agente DESLIGADO — modo observação (equipe humana atende).'); }
    else setNotice(`Não foi possível alterar: ${j?.error || r.status}`);
    setBusy(false);
  };

  const save = async () => {
    setBusy(true); setNotice(''); setErrors([]);
    const overridesPayload: Record<string, unknown> = {};
    for (const f of config?.editable_override_fields ?? []) {
      const val = overrides[f.key];
      if (val === '' || val == null) continue;
      overridesPayload[f.key] = f.input_kind === 'number' ? Number(val) : val;
    }
    const r = await fetch(`/api/dashboard/agents/${agentKey}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ variables: vars, overrides: overridesPayload }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setNotice('Alterações salvas.'); await load(); }
    else { setNotice('Não foi possível salvar.'); if (Array.isArray(j?.errors)) setErrors(j.errors); else setNotice(`Falha: ${j?.error || r.status}`); }
    setBusy(false);
  };
  const reset = async () => {
    setBusy(true); setNotice(''); setErrors([]);
    const r = await fetch(`/api/dashboard/agents/${agentKey}/reset`, { method: 'POST' });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setNotice('Restaurado ao padrão.'); await load(); }
    else setNotice(`Falha ao restaurar: ${j?.error || r.status}`);
    setBusy(false);
  };

  if (!config) return <p className="text-sm text-muted-foreground">Carregando…</p>;
  const opening = vars.opening_message;

  const renderVar = (v: Variable) => {
    if (v.input_kind === 'select') {
      return (
        <select value={vars[v.key] ?? ''} onChange={(e) => setVars((p) => ({ ...p, [v.key]: e.target.value }))} className={inputCls}>
          {v.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    if (v.input_kind === 'textarea') {
      return <textarea rows={3} maxLength={v.max_length} value={vars[v.key] ?? ''} onChange={(e) => setVars((p) => ({ ...p, [v.key]: e.target.value }))} className={inputCls} />;
    }
    return <input maxLength={v.max_length} value={vars[v.key] ?? ''} onChange={(e) => setVars((p) => ({ ...p, [v.key]: e.target.value }))} className={inputCls} />;
  };

  const renderOverride = (f: OverrideField) => {
    if (f.input_kind === 'select') {
      return (
        <select value={overrides[f.key] ?? ''} onChange={(e) => setOverrides((p) => ({ ...p, [f.key]: e.target.value }))} className={inputCls}>
          <option value="">— padrão —</option>
          {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    if (f.input_kind === 'number') {
      return <input type="number" step="0.1" min="0" max="1" value={overrides[f.key] ?? ''} onChange={(e) => setOverrides((p) => ({ ...p, [f.key]: e.target.value }))} className={inputCls} />;
    }
    return <input type={f.input_kind === 'url' ? 'url' : 'text'} placeholder={f.input_kind === 'url' ? 'https://…' : undefined} value={overrides[f.key] ?? ''} onChange={(e) => setOverrides((p) => ({ ...p, [f.key]: e.target.value }))} className={inputCls} />;
  };

  return (
    <div className="space-y-6">
      {/* SPEC-045 — LIGAR/DESLIGAR (só atendimento). Observador nunca desliga. */}
      {agentKey === 'even' && provisioned && isActive !== null && (
        <div className={`rounded-lg border p-4 ${isActive ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-border bg-card'}`}>
          <div className="flex flex-wrap items-center gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">
                {isActive ? '💬 Atendendo os segurados' : '👁 Observando em silêncio'}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {isActive
                  ? 'O agente responde os segurados no WhatsApp da corretora. O aprendizado contínuo segue normalmente.'
                  : 'A equipe humana atende pelo celular e o sistema observa e aprende. Quando você ligar, o agente assume as respostas NESTE MESMO número — sem re-parear nada.'}
              </p>
            </div>
            <button
              onClick={toggleActive}
              disabled={busy}
              className={`shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 ${
                isActive
                  ? 'border border-border bg-surface-2 text-foreground hover:bg-background'
                  : 'border border-emerald-500/50 bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20'
              }`}
            >
              {busy ? '…' : isActive ? 'Desligar agente' : 'Ligar agente'}
            </button>
          </div>
        </div>
      )}

      {/* Identidade / prévia */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-[11px] uppercase tracking-wide text-faint">Apresentação</p>
        <p className="mt-1 text-lg font-semibold text-foreground">{config.display_name}</p>
        {config.brand_locked_name && <p className="mt-1 text-[11px] text-amber-600">A marca “AutoBrokers” é fixa e não pode ser renomeada.</p>}
        {opening && <p className="mt-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">“{opening}”</p>}
        {opening && agentKey === 'even' && (
          <p className="mt-1.5 text-[11px] text-muted-foreground">
            É o ponto de partida — se o cliente já contar o que precisa, o agente pula a abertura e vai direto ao assunto.
          </p>
        )}
        {!provisioned && <p className="mt-2 text-[11px] text-amber-600">Agente ainda não provisionado para esta corretora.</p>}
      </div>

      {/* Campos editáveis (dropdowns onde a opção é previsível) */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="mb-3 text-sm font-medium text-foreground">Personalização</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {config.editable_variables.map((v) => (
            <label key={v.key} className={`block text-[12px] ${v.input_kind === 'textarea' ? 'sm:col-span-2' : ''}`}>
              <span className="text-muted-foreground">{v.label}</span>
              {renderVar(v)}
            </label>
          ))}
          {config.editable_override_fields.map((f) => (
            <label key={f.key} className="block text-[12px]">
              <span className="text-muted-foreground">{OVERRIDE_LABEL[f.key] ?? f.key}</span>
              {renderOverride(f)}
            </label>
          ))}
        </div>

        {errors.length > 0 && (
          <ul className="mt-3 space-y-1 rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-[11px] text-red-600">
            {errors.map((e) => <li key={e}>• Campo inválido: {e}</li>)}
          </ul>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button onClick={save} disabled={busy} className="rounded-lg border border-primary/40 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50">{busy ? 'Salvando…' : 'Salvar alterações'}</button>
          <button onClick={reset} disabled={busy} className="rounded-lg border border-border px-4 py-1.5 text-sm text-muted-foreground hover:bg-surface-2 disabled:opacity-50">Restaurar padrão</button>
          {notice && <span className="text-[12px] text-muted-foreground">{notice}</span>}
        </div>
        <p className="mt-2 text-[10px] text-faint">As instruções protegidas, regras de segurança e o modelo não são editáveis — garantem qualidade e segurança em todas as corretoras.</p>
      </div>
    </div>
  );
}
