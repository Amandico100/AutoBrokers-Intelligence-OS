'use client';

// Prompt Efetivo (SPEC-018 S4) — diagnóstico READ-ONLY de autoridade por agente.
// Só Master. Mostra o que o runtime REALMENTE monta: camadas de prompt
// (redigidas), ferramentas anexadas com a fonte da autorização e divergências.

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Shield, Loader2, AlertTriangle } from 'lucide-react';
import { useAdminRole } from '@/hooks/useAdminRole';

interface CompanyOption {
  id: string;
  name: string;
}

interface AgentOption {
  id: string;
  name: string;
  agent_role: string | null;
  is_active: boolean;
}

interface PromptLayer {
  layer: string;
  source: string;
  present?: boolean;
  chars?: number;
}

interface BoundTool {
  tool: string;
  authority: string;
  active: boolean;
  role_exposure?: string;
  count?: number;
  divergence?: string | null;
}

interface Diagnosis {
  agent_id: string;
  agent_role: string;
  prompt_layers: PromptLayer[];
  rag_scope: string;
  capabilities: Record<string, { status?: string; reason?: string }>;
  bound_tools: BoundTool[];
  divergences: string[];
  read_only: boolean;
}

export default function PromptEffectivePage() {
  const { role, isLoading: roleLoading } = useAdminRole();
  const router = useRouter();

  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [companyId, setCompanyId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!roleLoading && role !== 'master') router.push('/admin');
  }, [role, roleLoading, router]);

  useEffect(() => {
    fetch('/api/admin/companies')
      .then((r) => r.json())
      .then((d) => setCompanies((d.companies || []).map((c: any) => ({ id: c.id, name: c.name }))))
      .catch(() => setError('Falha ao carregar empresas.'));
  }, []);

  useEffect(() => {
    setAgents([]);
    setAgentId('');
    setDiagnosis(null);
    if (!companyId) return;
    fetch(`/api/admin/prompt-effective?action=agents&company_id=${companyId}`)
      .then((r) => r.json())
      .then((d) => setAgents(d.agents || []))
      .catch(() => setError('Falha ao carregar agentes.'));
  }, [companyId]);

  useEffect(() => {
    setDiagnosis(null);
    if (!companyId || !agentId) return;
    setLoading(true);
    setError('');
    fetch(`/api/admin/prompt-effective?company_id=${companyId}&agent_id=${agentId}`)
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) throw new Error(d?.error || d?.detail || 'Falha no diagnóstico.');
        setDiagnosis(d);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyId, agentId]);

  if (roleLoading || role !== 'master') return null;

  const selectClass =
    'w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50';

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center gap-3">
        <Shield className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold text-foreground">Prompt Efetivo</h1>
          <p className="text-sm text-muted-foreground">
            O que o Smith realmente monta para cada agente: camadas, ferramentas e a fonte de cada
            autorização. Somente leitura — instruções do cliente nunca aparecem cruas.
          </p>
        </div>
      </div>

      <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium">Empresa</label>
            <select
              className={selectClass}
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
            >
              <option value="">Selecione a corretora</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium">Agente</label>
            <select
              className={selectClass}
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              disabled={!companyId}
            >
              <option value="">{companyId ? 'Selecione o agente' : 'Escolha a empresa antes'}</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} · {a.agent_role || 'core'}
                  {a.is_active ? '' : ' (inativo)'}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Montando diagnóstico…
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {diagnosis && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">papel: {diagnosis.agent_role}</Badge>
            <Badge variant="secondary">RAG: {diagnosis.rag_scope}</Badge>
            <Badge variant="outline">somente leitura</Badge>
          </div>

          {diagnosis.divergences.length > 0 && (
            <Card className="border-amber-500/50">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-amber-600">
                  <AlertTriangle className="h-4 w-4" />
                  Divergências de autoridade ({diagnosis.divergences.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {diagnosis.divergences.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Camadas do prompt</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {diagnosis.prompt_layers.map((l) => (
                <div key={l.layer} className="rounded-md border p-3 text-sm">
                  <div className="font-medium">{l.layer}</div>
                  <div className="text-muted-foreground">
                    Fonte: {l.source}
                    {typeof l.present === 'boolean' && (
                      <> · {l.present ? `presente (${l.chars} caracteres, conteúdo redigido)` : 'vazia'}</>
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Ferramentas anexadas</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ferramenta</TableHead>
                    <TableHead>Autorizada por</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Observações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {diagnosis.bound_tools.map((t) => (
                    <TableRow key={t.tool}>
                      <TableCell className="font-mono text-xs">{t.tool}</TableCell>
                      <TableCell className="text-sm">{t.authority}</TableCell>
                      <TableCell>
                        <Badge variant={t.active ? 'default' : 'outline'}>
                          {t.active ? 'ativa' : 'inativa'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {[
                          t.role_exposure ? `exposição: ${t.role_exposure}` : null,
                          typeof t.count === 'number' ? `itens: ${t.count}` : null,
                          t.divergence ? `⚠ ${t.divergence}` : null,
                        ]
                          .filter(Boolean)
                          .join(' · ') || '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {Object.keys(diagnosis.capabilities).length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Capabilities resolvidas</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {Object.entries(diagnosis.capabilities).map(([key, info]) => (
                  <Badge
                    key={key}
                    variant={info?.status === 'active' ? 'default' : 'outline'}
                    title={info?.reason || ''}
                  >
                    {key} · {info?.status || '?'}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
      </div>
    </div>
  );
}
