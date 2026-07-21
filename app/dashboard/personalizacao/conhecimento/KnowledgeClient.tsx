'use client';

// SPEC-036 Etapa 2 — a corretora alimenta o próprio cérebro pelo dashboard.
// Linguagem de corretor (sem jargão de RAG/chunking): escolhe o arquivo, diz
// qual assistente vai usar, envia. A estratégia de processamento é automática.

import { useCallback, useEffect, useRef, useState } from 'react';

type Doc = { file_name: string; file_type: string | null; status: string; scope: string; knowledge_class: string | null; visibility: string | null; chunks: number; created_at: string | null };
type Data = { documents: Doc[]; total: number; ready: number };
type Agent = { id: string; name: string };

const statusCls = (s: string) => /ready|done|completed|processed|ingested/i.test(s) ? 'text-emerald-600' : /error|fail/i.test(s) ? 'text-red-600' : 'text-amber-600';

export function KnowledgeClient() {
  const [d, setD] = useState<Data | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState('');
  const [target, setTarget] = useState<'company' | 'personal'>('company');
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    fetch('/api/dashboard/knowledge').then((r) => r.json()).then((j) => { if (j?.ok) setD(j); }).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    fetch('/api/dashboard/knowledge/upload')
      .then((r) => r.json())
      .then((j) => {
        const list: Agent[] = j?.agents || [];
        setAgents(list);
        if (list.length === 1) setAgentId(list[0].id);
      })
      .catch(() => {});
  }, [load]);

  const send = async () => {
    if (!file || !agentId || sending) return;
    setSending(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.set('file', file);
      fd.set('agent_id', agentId);
      fd.set('target', target); // SPEC-044: corretora (todos) ou pessoal (só você)
      const res = await fetch('/api/dashboard/knowledge/upload', { method: 'POST', body: fd });
      if (res.ok) {
        setMsg('Documento recebido! Estou processando — em alguns minutos ele entra no conhecimento do assistente.');
        setFile(null);
        if (fileRef.current) fileRef.current.value = '';
        setTimeout(load, 4000);
      } else {
        const j = await res.json().catch(() => null);
        setMsg(j?.error || j?.detail || 'Não consegui enviar. Tente novamente.');
      }
    } catch {
      setMsg('Não consegui enviar. Tente novamente.');
    } finally {
      setSending(false);
    }
  };

  if (!d) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-sm text-foreground">Conhecimento da corretora: <span className="font-semibold">{d.total}</span> documento(s), {d.ready} pronto(s) para uso.</p>
        <p className="mt-1 text-[11px] text-faint">Tudo que você subir aqui vira memória dos seus assistentes — tabelas, manuais internos, metas, scripts. Documentos de outras corretoras nunca aparecem aqui.</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-4 space-y-3">
        <p className="text-sm font-medium text-foreground">Adicionar conhecimento</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,.csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-xs text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground"
        />
        {/* SPEC-044: destino do conhecimento — 3 camadas em linguagem humana */}
        <div className="flex gap-2">
          {([
            { id: 'company', label: '🏢 Da corretora', hint: 'todo mundo da equipe usa' },
            { id: 'personal', label: '👤 Só para mim', hint: 'ninguém mais vê' },
          ] as const).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTarget(t.id)}
              className={`flex-1 rounded-md border px-3 py-2 text-left text-xs transition-colors ${
                target === t.id
                  ? 'border-primary/50 bg-primary/5 text-foreground'
                  : 'border-border bg-background text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className="block font-medium">{t.label}</span>
              <span className="block text-[10px] opacity-80">{t.hint}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="h-8 flex-1 rounded-md border border-border bg-background px-2 text-xs text-foreground"
          >
            <option value="">Qual assistente vai usar?</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <button
            onClick={send}
            disabled={!file || !agentId || sending}
            className="h-8 rounded-md bg-primary px-4 text-xs font-medium text-primary-foreground disabled:opacity-40"
          >
            {sending ? 'Enviando…' : 'Enviar'}
          </button>
        </div>
        <p className="text-[10px] text-faint">PDF, DOCX, TXT, MD ou CSV (até 10MB). O processamento é automático — sem configuração.</p>
        {msg && <p className="text-[11px] text-foreground">{msg}</p>}
      </div>

      {d.documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum documento ainda — suba o primeiro acima e veja o cérebro da corretora nascer.</p>
      ) : (
        <div className="rounded-lg border border-border bg-card divide-y divide-border">
          {d.documents.map((doc, i) => (
            <div key={i} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{doc.file_name}</p>
                <p className="text-[11px] text-faint">{[doc.knowledge_class, doc.scope, doc.file_type].filter(Boolean).join(' · ')}{doc.chunks ? ` · ${doc.chunks} trechos` : ''}</p>
              </div>
              <span className={`shrink-0 text-[11px] ${statusCls(doc.status)}`}>{doc.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
