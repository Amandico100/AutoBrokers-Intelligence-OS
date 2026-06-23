'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Bot, Plus, Loader2, ArrowLeft, Building2, Lock as LockIcon } from 'lucide-react';
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

  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

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
    }
  }, [companyId]);

  const loadHealth = async () => {
    try { const j = await fetch(`/api/admin/companies/${companyId}/agent-health`).then((r) => r.json()); if (j?.ok) setHealth(j); } catch { /* silencioso */ }
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
                <p className="text-sm text-muted-foreground">Gerenciando agentes de</p>
                <h1 className="text-2xl font-bold text-foreground">{companyName}</h1>
              </div>
            </div>
            <p className="text-muted-foreground mt-2">Configure os agentes de IA desta empresa</p>
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
                        {d.action === 'rename_attendance_even' ? 'Renomear para Even' : 'Arquivar'}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : <p className="text-[12px] text-muted-foreground">Nenhuma pendência. Core e Even canônicos OK.</p>}
            <p className="text-[10px] text-faint">Modelo do Core é promovido por política (temporário). Edição global no Blueprint Center; personalização local no Dashboard. Sem segredos aqui.</p>
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
