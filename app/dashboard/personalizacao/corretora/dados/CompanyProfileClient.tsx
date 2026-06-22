'use client';

import { useCallback, useEffect, useState } from 'react';

type Field = { key: string; label: string; input_kind: 'text' | 'select' | 'email' | 'cnpj'; options?: string[]; max_length: number; required?: boolean };

const inputCls = 'mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground';

export function CompanyProfileClient() {
  const [fields, setFields] = useState<Field[] | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [errors, setErrors] = useState<string[]>([]);

  const load = useCallback(async () => {
    const j = await fetch('/api/dashboard/company-profile').then((r) => r.json()).catch(() => ({}));
    if (j?.ok) { setFields(j.fields); setValues(j.values); }
    else setNotice(j?.error || 'Falha ao carregar.');
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true); setNotice(''); setErrors([]);
    const r = await fetch('/api/dashboard/company-profile', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ values }),
    });
    const j = await r.json().catch(() => ({}));
    if (j?.ok) { setNotice('Dados salvos.'); setValues(j.values); }
    else { setNotice('Não foi possível salvar.'); if (Array.isArray(j?.errors)) setErrors(j.errors); else setNotice(`Falha: ${j?.error || r.status}`); }
    setBusy(false);
  };

  if (!fields) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {fields.map((f) => (
          <label key={f.key} className="block text-[12px]">
            <span className="text-muted-foreground">{f.label}{f.required ? ' *' : ''}</span>
            {f.input_kind === 'select' ? (
              <select value={values[f.key] ?? ''} onChange={(e) => setValues((p) => ({ ...p, [f.key]: e.target.value }))} className={inputCls}>
                <option value="">—</option>
                {(f.options ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <input type={f.input_kind === 'email' ? 'email' : 'text'} maxLength={f.max_length} value={values[f.key] ?? ''} onChange={(e) => setValues((p) => ({ ...p, [f.key]: e.target.value }))} className={inputCls} />
            )}
          </label>
        ))}
      </div>

      {errors.length > 0 && (
        <ul className="mt-3 space-y-1 rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-[11px] text-red-600">
          {errors.map((e) => <li key={e}>• Campo inválido: {e}</li>)}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button onClick={save} disabled={busy} className="rounded-lg border border-primary/40 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50">{busy ? 'Salvando…' : 'Salvar dados'}</button>
        {notice && <span className="text-[12px] text-muted-foreground">{notice}</span>}
      </div>
      <p className="mt-2 text-[10px] text-faint">Plano, créditos, isolamento e parâmetros técnicos não são editáveis aqui.</p>
    </div>
  );
}
