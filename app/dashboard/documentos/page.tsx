'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, Sparkles } from 'lucide-react';
import { useAdminRole } from '@/hooks/useAdminRole';
import { DocumentManagementModal } from '@/components/admin/DocumentManagementModal';
import Link from 'next/link';

export default function DocumentsPage() {
  const { role, companyId, isLoading } = useAdminRole();
  const router = useRouter();

  useEffect(() => {
    // SPEC-061 §6 — `master` NÃO é expulso.
    //
    // Este guard nasceu quando a tela morava em /admin: lá, "não é
    // company_admin" queria dizer "não é seu". Depois da separação, ela mora
    // no /dashboard e o efeito virou o oposto do pretendido: /admin/documents
    // redirecionava para cá, e daqui o master voltava para /admin. Do lado de
    // quem testa, isso é indistinguível de "o redirecionamento não funciona" —
    // e foi exatamente assim que o Founder relatou.
    //
    // O master de plataforma precisa navegar estas telas: é como ele confere a
    // experiência da corretora sem mexer numa de verdade (a corretora de
    // ensaio existe para isso). Mesmo padrão já usado em /dashboard/equipe.
    if (!isLoading && role !== 'company_admin' && role !== 'master') {
      router.push('/admin');
    }
  }, [role, isLoading, router]);

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="text-foreground">Carregando...</div>
      </div>
    );
  }

  if (!companyId) {
    return (
      <div className="p-8">
        <div className="text-red-400">Erro: Empresa não encontrada</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
          <FileText className="w-8 h-8" />
          Base de Conhecimento
        </h1>
        <p className="text-muted-foreground">
          Faça upload de documentos para treinar seu agente com informações específicas da sua
          empresa
        </p>
      </div>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-foreground">Gerenciar Documentos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm mb-6">
            Envie PDFs, documentos e outros arquivos que o agente deve conhecer. O sistema
            processará automaticamente e utilizará essas informações para responder aos clientes.
          </p>
          <div className="flex items-center gap-3">
            <DocumentManagementModal companyId={companyId} companyName="Sua Empresa" />
            <Link href="/admin/knowledge-base/sanitize">
              <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors">
                <Sparkles className="w-4 h-4" />
                Sanitizar Documentos
              </button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
