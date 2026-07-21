'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Bot, Plus, Loader2, ArrowLeft, Building2, Lock as LockIcon, SearchCheck } from 'lucide-react';
import { useAdminRole } from '@/hooks/useAdminRole';
import { AgentConfigModal } from '@/components/admin/AgentConfigModal';
import { AgentFlowView } from '@/components/agents/AgentFlowView';
import type { AgentWithDelegations } from '@/components/agents/hooks/useAgentFlowLayout';
import { Agent } from '@/types/agent';
import { useToast } from '@/hooks/use-toast';

export default function AdminCompanyAgentsPage() {
  const { role, isLoading: roleLoading } = useAdminRole();
  const router = useRouter();
  const params = useParams();
  const companyId = params.companyId as string;
  const { toast } = useToast();

  const [agents, setAgents] = useState<AgentWithDelegations[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(undefined);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [companyName, setCompanyName] = useState<string>('');
  const [companyKind, setCompanyKind] = useState<string>('client'); // SPEC-013: Studio/Knowledge ≠ cliente
  const [canonical, setCanonical] = useState<any>(null); // SPEC-013 B2: Core/Even protegidos (Even sempre visível)
  const [health, setHealth] = useState<any>(null); // SPEC-013 FB-2: diagnóstico + manutenção (folded)
  const [caps, setCaps] = useState<any>(null); // SPEC-014 C1: cockpit de capabilities (folded)
  const [contractProbeMode, setContractProbeMode] = useState<'policy_chain_contract' | 'official_document_source_audit' | 'policy_identity_integrity_audit'>('policy_chain_contract');
  const [contractQueryType, setContractQueryType] = useState<'cpf' | 'name'>('cpf');
  const [contractQuery, setContractQuery] = useState('');
  const [contractPolicyRef, setContractPolicyRef] = useState('');
  const [contractRunning, setContractRunning] = useState(false);
  const [contractResult, setContractResult] = useState<any>(null);

  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  const connectionSelectionLabel = (status?: string) => {
    if (status === 'connection_usable') return 'conexao utilizavel';
    if (status === 'manual_connection_cleanup_required') return 'limpeza necessaria';
    if (status === 'reconnect_required') return 'reconexao necessaria';
    return 'aguardando diagnostico';
  };

  // Verificar permissão Super Admin
  useEffect(() => {
    if (!roleLoading && role !== 'master') {
      router.push('/admin');
    }
  }, [role, roleLoading, router]);

  // Carregar nome da empresa
  useEffect(() => {
    if (companyId) {
      loadCompanyInfo();
      loadAgents();
      // SPEC-013 B2: Core/Even canônicos (Supabase, Even sempre visível mesmo inativa)
      fetch(`/api/admin/companies/${companyId}/core-even`).then((r) => r.json()).then((j) => { if (j?.ok) setCanonical(j); }).catch(() => {});
      loadHealth();
      loadCaps();
    }
  }, [companyId]);

  const loadHealth = async () => {
    try { const j = await fetch(`/api/admin/companies/${companyId}/agent-health`).then((r) => r.json()); if (j?.ok) setHealth(j); } catch { /* silencioso */ }
  };

  const loadCaps = async () => {
    try { const j = await fetch(`/api/admin/companies/${companyId}/capabilities`).then((r) => r.json()); if (j?.ok) setCaps(j); } catch { /* silencioso */ }
  };

  const syncCaps = async () => {
    try {
      const r = await fetch(`/api/admin/companies/${companyId}/capabilities`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'sync_runtime_flags' }),
      });
      const j = await r.json().catch(() => ({}));
      if (j?.ok) { toast({ title: 'Acessos sincronizados', description: `Core web: ${j.cores_web_on} · Even web off: ${j.even_web_off}` }); loadCaps(); }
      else toast({ title: 'Falha', description: j?.error || 'erro', variant: 'destructive' });
    } catch { /* ignore */ }
  };

  const runInfocapContractProbe = async () => {
    if (!contractQuery.trim()) {
      toast({ title: 'Informe um termo de teste', description: 'Use CPF ou nome de um segurado de teste.', variant: 'destructive' });
      return;
    }
    if ((contractProbeMode === 'official_document_source_audit' || contractProbeMode === 'policy_identity_integrity_audit') && !contractPolicyRef.trim()) {
      toast({ title: 'Informe a referencia da apolice', description: 'Esta auditoria precisa do numero humano da apolice de teste.', variant: 'destructive' });
      return;
    }
    setContractRunning(true);
    setContractResult(null);
    try {
      const r = await fetch('/api/attendance/connectors/infocap/probe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: contractProbeMode,
          company_id: companyId,
          query_type: contractQueryType,
          query: contractQuery,
          policy_ref: contractPolicyRef.trim() || undefined,
        }),
      });
      const j = await r.json().catch(() => ({}));
      setContractResult(j);
      if (!r.ok || j?.ok === false) {
        toast({ title: 'Diagnóstico não concluído', description: j?.error || j?.status || 'erro', variant: 'destructive' });
      }
    } catch (error) {
      toast({ title: 'Falha no diagnóstico', description: error instanceof Error ? error.message : 'erro', variant: 'destructive' });
    } finally {
      setContractRunning(false);
    }
  };

  const runMaintenance = async (action: string, agentId: string) => {
    try {
      const r = await fetch(`/api/admin/companies/${companyId}/agent-actions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, agent_id: agentId }),
      });
      const j = await r.json().catch(() => ({}));
      if (j?.ok) { await loadHealth(); loadAgents(); } else { toast({ title: 'Falha', description: j?.error || 'erro', variant: 'destructive' }); }
    } catch { /* ignore */ }
  };

  const loadCompanyInfo = async () => {
    try {
      const response = await fetch(`/api/admin/company-info?companyId=${companyId}`, {
        credentials: 'include',
      });

      if (!response.ok) throw new Error('Failed to load company info');

      const data = await response.json();
      setCompanyName(data?.company_name || 'Empresa');
    } catch (error) {
      console.error('Error loading company info:', error);
    }
    // SPEC-013: detecta empresa-plataforma (Studio/Knowledge) para não exibir o editor de cliente.
    try {
      const kr = await fetch(`/api/admin/companies/${companyId}/kind`).then((r) => r.json());
      if (kr?.ok && typeof kr.company_kind === 'string') setCompanyKind(kr.company_kind);
    } catch { /* default client */ }
  };

  const loadAgents = async () => {
    setLoadingAgents(true);
    try {
      const response = await fetch(`/api/admin/agents/company/${companyId}/with-delegations`);
      if (response.ok) {
        const data = await response.json();
        // SPEC-013 P0: Core/Even são geridos pela seção canônica (acima) e pelo Blueprint Center.
        // Não duplicar no canvas legado nem permitir editor técnico errado por aqui.
        const filtered = Array.isArray(data)
          ? data.filter((a: any) => a?.agent_role !== 'core' && a?.agent_role !== 'attendance')
          : data;
        setAgents(filtered);
      } else {
        throw new Error('Failed to load agents');
      }
    } catch (error) {
      console.error('Error loading agents:', error);
      toast({
        title: 'Erro',
        description: 'Falha ao carregar agentes',
        variant: 'destructive',
      });
    } finally {
      setLoadingAgents(false);
    }
  };

  const handleCreateAgent = () => {
    setSelectedAgentId(undefined);
    setIsModalOpen(true);
  };

  const handleEditAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
    setIsModalOpen(true);
  };

  const handleArchiveAgent = async (agentId: string) => {
    if (!confirm('Tem certeza que deseja arquivar este agente?')) return;

    try {
      const response = await fetch(`/api/admin/proxy/agents/${agentId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast({
          title: 'Sucesso',
          description: 'Agente arquivado com sucesso',
        });
        loadAgents();
      } else {
        throw new Error('Failed to archive agent');
      }
    } catch (error) {
      console.error('Error archiving agent:', error);
      toast({
        title: 'Erro',
        description: 'Falha ao arquivar agente',
        variant: 'destructive',
      });
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedAgentId(undefined);
    loadAgents();
  };

  if (roleLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (role !== 'master') {
    return (
      <div className="p-8">
        <div className="text-red-400">
          Acesso negado. Apenas Super Admin pode acessar esta página.
        </div>
      </div>
    );
  }

  // SPEC-013: empresa-plataforma (Blueprint Studio / Global Knowledge) não usa o editor
  // de agentes de cliente. A autoria global acontece no Blueprint Center.
  if (companyKind && companyKind.startsWith('platform_')) {
    return (
      <div className="p-8">
        <button onClick={() => router.push('/admin/companies')} className="mb-4 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Voltar para Empresas
        </button>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <LockIcon className="h-5 w-5 text-amber-500" />
              <h1 className="text-lg font-semibold text-foreground">{companyName} — empresa técnica da plataforma</h1>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {companyKind === 'platform_blueprint_studio'
                ? 'Esta é a empresa de autoria global (Blueprint Studio). Os Source Agents globais (AutoBrokers e Even) são criados e versionados no Blueprint Center, e ficam inativos por serem de autoria — não atendem clientes. Não use o editor de agentes de cliente aqui.'
                : 'Esta é a empresa de conhecimento global (RAG/Seed Packs). Não gerencie agentes de cliente aqui.'}
            </p>
            {companyKind === 'platform_blueprint_studio' && (
              <Button className="mt-4" onClick={() => router.push('/admin/blueprint-center')}>Abrir Blueprint Center</Button>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        {/* Breadcrumb / Back */}
        <Button
          variant="ghost"
          onClick={() => router.push('/admin/companies')}
          className="mb-4 text-muted-foreground hover:text-foreground hover:bg-muted -ml-2"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar para Empresas
        </Button>

        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-lg flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Configuração completa da corretora</p>
                <h1 className="text-2xl font-bold text-foreground">{companyName}</h1>
              </div>
            </div>
            <p className="text-muted-foreground mt-2">
              Identidade, HTTP Tools, MCP, WhatsApp, agentes e subagentes — tudo desta empresa num lugar só.
            </p>
          </div>
          <Button
            onClick={handleCreateAgent}
            className="bg-blue-600 hover:bg-blue-700 text-white gap-2"
          >
            <Plus className="w-4 h-4" />
            Novo Agente Personalizado
          </Button>
        </div>
      </div>

      {/* SPEC-013 B2 — Agentes canônicos protegidos (Core + Even). Even aparece mesmo inativa.
          Edição global vai pelo Blueprint Center; personalização local pelo Dashboard tenant. */}
      {canonical && (
        <div className="mb-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[canonical.core, canonical.even].map((a: any) => (
            <Card key={a.blueprint_key} className="bg-card border-border">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {a.type === 'Atendimento' ? <Bot className="w-4 h-4 text-cyan-500" /> : <Bot className="w-4 h-4 text-blue-500" />}
                    <p className="font-semibold text-foreground">{a.label}</p>
                  </div>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${a.is_active ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' : 'border-amber-500/30 bg-amber-500/10 text-amber-600'}`}>
                    {a.provisioned ? (a.is_active ? 'Ativo' : 'Inativo') : 'Aguardando provisionamento'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{a.type} · blueprint {a.blueprint_key}{a.applied_release?.version ? ` · release v${a.applied_release.version}` : ' · sem rollout'}</p>
                <p className="mt-2 text-[11px] text-muted-foreground">A edição técnica global (prompt-base, guardrails, Tools/MCP) é feita no Blueprint Center. A personalização local, no Dashboard da corretora.</p>
                <div className="mt-3 flex gap-2">
                  <Button variant="outline" className="h-7 text-xs" onClick={() => router.push('/admin/blueprint-center')}>Blueprint Center</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* SPEC-013 FB-2 — Diagnóstico & manutenção (folded; sem página nova). Colapsável. */}
      {health && (
        <details className="mb-8">
          <summary className="cursor-pointer list-none select-none">
            <span className="text-sm font-medium text-foreground">▸ Diagnóstico & manutenção</span>
            <span className={`ml-2 rounded-full border px-2 py-0.5 text-[10px] ${health.healthy ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' : 'border-amber-500/30 bg-amber-500/10 text-amber-600'}`}>{health.healthy ? 'saudável' : 'requer atenção'}</span>
          </summary>
          <Card className="mt-3 bg-card border-border"><CardContent className="p-4 space-y-3">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 text-[12px]">
              <div className="rounded-md border border-border bg-background px-3 py-2">AutoBrokers · modelo <span className="text-foreground">{health.core?.model_effective ?? '—'}</span></div>
              <div className="rounded-md border border-border bg-background px-3 py-2">Even · {health.even?.present ? (health.even?.is_active ? 'ativa' : 'inativa') : 'ausente'}</div>
              <div className="rounded-md border border-border bg-background px-3 py-2">Saldo R$ {Number(health.balance_brl ?? 0).toFixed(2)} · Conhecimento {health.knowledge?.private_docs ?? 0} doc(s)</div>
            </div>
            {Array.isArray(health.divergences) && health.divergences.length > 0 ? (
              <div className="divide-y divide-border">
                {health.divergences.map((d: any, i: number) => (
                  <div key={i} className="flex items-center justify-between py-1.5 text-[12px]">
                    <span className="text-muted-foreground">{d.label}</span>
                    {d.action && d.agent_id && (
                      <button onClick={() => runMaintenance(d.action, d.agent_id)} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-0.5 text-[12px] font-medium text-primary hover:bg-primary/10">
                        Arquivar
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : <p className="text-[12px] text-muted-foreground">Nenhuma pendência. Core e Even canônicos OK.</p>}
            <p className="text-[10px] text-faint">Modelo do Core é promovido por política (temporário). Edição global no Blueprint Center; personalização local no Dashboard. Sem segredos aqui.</p>
            <details className="rounded-md border border-border bg-background px-3 py-2">
              <summary className="flex cursor-pointer list-none items-center gap-2 text-[12px] font-medium text-foreground">
                <SearchCheck className="h-4 w-4 text-primary" />
                Diagnosticar contrato InfoCap
                <span className="text-[10px] font-normal text-muted-foreground">Somente leitura · não altera dados · não exibe segurados</span>
              </summary>
              <div className="mt-3 space-y-3">
                <div className="grid grid-cols-1 gap-2 md:grid-cols-[220px_140px_1fr_1fr_auto]">
                  <label className="text-[11px] text-muted-foreground">
                    Modo
                    <select
                      value={contractProbeMode}
                      onChange={(e) => {
                        const value = e.target.value;
                        setContractProbeMode(
                          value === 'official_document_source_audit'
                            ? 'official_document_source_audit'
                            : value === 'policy_identity_integrity_audit'
                              ? 'policy_identity_integrity_audit'
                              : 'policy_chain_contract'
                        );
                      }}
                      className="mt-1 h-9 w-full rounded-md border border-border bg-card px-2 text-[12px] text-foreground"
                    >
                      <option value="policy_chain_contract">Diagnosticar contrato InfoCap</option>
                      <option value="official_document_source_audit">Auditar fonte oficial da apolice</option>
                      <option value="policy_identity_integrity_audit">Auditar integridade de identidade da apolice</option>
                    </select>
                  </label>
                  <label className="text-[11px] text-muted-foreground">
                    Metodo
                    <select
                      value={contractQueryType}
                      onChange={(e) => setContractQueryType(e.target.value === 'name' ? 'name' : 'cpf')}
                      className="mt-1 h-9 w-full rounded-md border border-border bg-card px-2 text-[12px] text-foreground"
                    >
                      <option value="cpf">CPF</option>
                      <option value="name">Nome</option>
                    </select>
                  </label>
                  <label className="text-[11px] text-muted-foreground">
                    Termo de teste
                    <input
                      value={contractQuery}
                      onChange={(e) => setContractQuery(e.target.value)}
                      placeholder={contractQueryType === 'cpf' ? 'CPF de teste' : 'Nome de teste'}
                      className="mt-1 h-9 w-full rounded-md border border-border bg-card px-2 text-[12px] text-foreground"
                    />
                  </label>
                  <label className="text-[11px] text-muted-foreground">
                    Referencia da apolice
                    <input
                      value={contractPolicyRef}
                      onChange={(e) => setContractPolicyRef(e.target.value)}
                      placeholder="Opcional"
                      className="mt-1 h-9 w-full rounded-md border border-border bg-card px-2 text-[12px] text-foreground"
                    />
                  </label>
                  <Button
                    type="button"
                    variant="outline"
                    className="mt-5 h-9 gap-2 text-[12px]"
                    onClick={runInfocapContractProbe}
                    disabled={contractRunning}
                  >
                    {contractRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <SearchCheck className="h-3.5 w-3.5" />}
                    Executar
                  </Button>
                </div>
                {contractProbeMode === 'official_document_source_audit' && (
                  <p className="rounded-md border border-border bg-card px-3 py-2 text-[11px] text-muted-foreground">
                    Esta auditoria nao baixa documentos no Chat, nao processa PDF e nao altera dados. Ela apenas verifica se a fonte oficial da apolice pode ser acessada com seguranca.
                  </p>
                )}
                {contractProbeMode === 'policy_identity_integrity_audit' && (
                  <p className="rounded-md border border-border bg-card px-3 py-2 text-[11px] text-muted-foreground">
                    Esta auditoria nao baixa PDF, nao consulta evidencia documental e nao exibe dados de segurados. Ela verifica se o numero humano da apolice pertence ao cliente canonico antes de permitir detalhe.
                  </p>
                )}
                {contractResult && (
                  <div className="space-y-2">
                    {contractResult.connection_resolution && (
                      <div className="rounded-md border border-border bg-card px-3 py-2 text-[11px] text-muted-foreground">
                        <p className="font-medium text-foreground">Status da conexao para diagnostico</p>
                        <div className="mt-1 grid grid-cols-1 gap-1 md:grid-cols-4">
                          <span>Conexoes InfoCap encontradas: {contractResult.connection_resolution.total_infocap_connections ?? 0}</span>
                          <span>Conexoes elegiveis: {contractResult.connection_resolution.eligible_connection_count ?? 0}</span>
                          <span>Vault configurado: {contractResult.connection_resolution.vault_configured ? 'sim' : 'nao'}</span>
                          <span>Selecao: {connectionSelectionLabel(contractResult.connection_resolution.selection_status)}</span>
                        </div>
                      </div>
                    )}
                    <pre className="max-h-96 overflow-auto rounded-md border border-border bg-card p-3 text-[11px] leading-relaxed text-muted-foreground">
                      {JSON.stringify(contractResult, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          </CardContent></Card>
        </details>
      )}

      {/* SPEC-014 C1 — Capacidades (Capability Registry), folded. Quem usa o quê + sincronizar runtime. */}
      {caps && (
        <details className="mb-8">
          <summary className="cursor-pointer list-none select-none">
            <span className="text-sm font-medium text-foreground">▸ Capacidades (Capability Registry)</span>
            <span className={`ml-2 rounded-full border px-2 py-0.5 text-[10px] ${caps.web_search_operational === true ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' : caps.web_search_operational === false ? 'border-amber-500/30 bg-amber-500/10 text-amber-600' : 'border-border bg-background text-muted-foreground'}`}>
              busca web {caps.web_search_operational === true ? 'operacional' : caps.web_search_operational === false ? 'sem TAVILY no backend' : 'verificar'}
            </span>
          </summary>
          <Card className="mt-3 bg-card border-border"><CardContent className="p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[12px] text-muted-foreground">Core, Even e Auxiliares usam capacidades governadas — sem flag solta. Internas nascem ligadas; externas pedem conexão/aprovação.</p>
              <button onClick={syncCaps} className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-1 text-[12px] font-medium text-primary hover:bg-primary/10">Sincronizar acessos do runtime</button>
            </div>
            {!caps.entitlements_table && (
              <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-600">Aplique o runbook SPEC-014-01 para ativar a governança completa por corretora (entitlements).</div>
            )}
            {(['core', 'attendance', 'auxiliary'] as const).map((role) => (
              <div key={role}>
                <p className="mb-1 text-[12px] font-medium text-foreground">{role === 'core' ? 'AutoBrokers (Core)' : role === 'attendance' ? 'Atendimento' : 'Auxiliares (teto permitido)'}</p>
                <div className="flex flex-wrap gap-1.5">
                  {(caps[role] ?? []).filter((c: any) => c.status !== 'not_allowed_for_role').map((c: any) => (
                    <span key={c.key} title={`${c.key} — ${c.reason}`}
                      className={`rounded-md border px-2 py-0.5 text-[11px] ${c.status === 'active' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600' : c.status === 'needs_connection' ? 'border-sky-500/30 bg-sky-500/10 text-sky-600' : 'border-border bg-background text-muted-foreground'}`}>
                      {c.capability?.name ?? c.key}{c.status === 'needs_connection' ? ' · conectar' : c.status === 'disabled' ? ' · off' : ''}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-[10px] text-faint">Busca web usa Tavily (chave da plataforma via env TAVILY_API_KEY). InfoCap/portais/WhatsApp pedem conexão no Dashboard. Governança em SPEC-014.</p>
          </CardContent></Card>
        </details>
      )}

      {/* SPEC-013 P0 — Seção 2: agentes personalizados (Core/Even ficam na seção canônica acima). */}
      <p className="mb-3 text-sm font-medium text-muted-foreground">Agentes personalizados da corretora</p>

      {/* Agents Flow View */}
      {loadingAgents ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : agents.length === 0 ? (
        <Card className="bg-card border-border">
          <CardContent className="py-12 text-center">
            <Bot className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-foreground mb-2">Nenhum agente personalizado adicional</h3>
            <p className="text-muted-foreground mb-6">
              O AutoBrokers e a Even desta corretora aparecem acima, em “Agentes canônicos”.
              O padrão global deles é editado no Blueprint Center. Aqui ficam apenas agentes
              extras/subagentes específicos desta corretora.
            </p>
            <Button
              onClick={handleCreateAgent}
              className="bg-blue-600 hover:bg-blue-700 text-white gap-2"
            >
              <Plus className="w-4 h-4" />
              Novo Agente Personalizado
            </Button>
          </CardContent>
        </Card>
      ) : (
        <AgentFlowView
          agents={agents}
          onEdit={handleEditAgent}
          onArchive={handleArchiveAgent}
        />
      )}

      {/* Info */}
      <div className="mt-6 p-4 bg-blue-600 border border-blue-700 rounded-lg">
        <p className="text-sm text-white">
          <LockIcon className="w-4 h-4 inline-block mr-2 text-blue-200" />
          <strong>Modo Super Admin:</strong> Você está visualizando os agentes como administrador
          do sistema. As alterações feitas aqui afetarão diretamente a experiência do cliente.
        </p>
      </div>

      {/* Modal - passa o companyId da URL */}
      {isModalOpen && (
        <AgentConfigModal
          companyId={companyId}
          agentId={selectedAgentId}
          open={isModalOpen}
          onOpenChange={handleModalClose}
        />
      )}
    </div>
  );
}
