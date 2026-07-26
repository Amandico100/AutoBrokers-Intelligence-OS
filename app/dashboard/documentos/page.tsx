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

  // SPEC-061 §6 — o guard de PAPEL foi removido.
  //
  // Ele perguntava "qual é o seu papel?" e mandava para /admin quem não fosse
  // `company_admin`. Duas coisas erradas nisso:
  //
  // 1. **O nome do papel me traiu duas vezes.** A sessão grava `master_admin`,
  //    o hook devolve `master`, e o guard comparava com uma terceira coisa.
  //    Um teste de igualdade de string entre três vocabulários é frágil por
  //    natureza.
  //
  // 2. **Devolver para /admin criou um vaivém.** `/admin/documents`
  //    redirecionava para cá, e daqui voltava para /admin. Da cadeira de quem
  //    testa, isso é indistinguível de "o redirecionamento não funciona" — e
  //    foi exatamente assim que o Founder relatou, duas vezes.
  //
  // A pergunta certa não é sobre papel: é **"eu tenho uma corretora para
  // mostrar?"**. É disso que a tela depende, e a resposta já era tratada
  // abaixo, com uma mensagem clara em vez de um empurrão. Mensagem explica;
  // redirecionamento silencioso não.

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
