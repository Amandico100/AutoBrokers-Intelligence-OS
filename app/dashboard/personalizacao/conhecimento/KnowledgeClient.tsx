'use client';

import { useEffect, useState } from 'react';

type Doc = { file_name: string; file_type: string | null; status: string; scope: string; knowledge_class: string | null; visibility: string | null; chunks: number; created_at: string | null };
type Data = { documents: Doc[]; total: number; ready: number };

const statusCls = (s: string) => /ready|done|completed|processed|ingested/i.test(s) ? 'text-emerald-600' : /error|fail/i.test(s) ? 'text-red-600' : 'text-amber-600';

export function KnowledgeClient() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => { fetch('/api/dashboard/knowledge').then((r) => r.json()).then((j) => { if (j?.ok) setD(j); }).catch(() => {}); }, []);
  if (!d) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-sm text-foreground">Conhecimento privado da corretora: <span className="font-semibold">{d.total}</span> documento(s), {d.ready} processado(s).</p>
        <p className="mt-1 text-[11px] text-faint">O AutoBrokers também usa o conhecimento global curado da plataforma e das seguradoras. O RAG explica regras e condições — não confirma cobertura.</p>
      </div>

      {d.documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum documento privado ainda. O envio de documentos será habilitado quando o pipeline de ingestão isolada por corretora estiver pronto.</p>
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
      <p className="text-[10px] text-faint">Somente leitura nesta fase. Documentos de outras corretoras nunca aparecem aqui.</p>
    </div>
  );
}
