'use client';

import { useState, useEffect } from 'react';
import { TermsAcceptanceModal } from '@/components/TermsAcceptanceModal';
import { TenantAppShell } from '@/components/layout/TenantAppShell';
import { FaixaDaLinha } from '@/components/avisos/FaixaDaLinha';

interface ActiveTerms {
  id: string;
  title: string;
  content: string;
  version: string;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [termsOutdated, setTermsOutdated] = useState(false);
  const [activeTerms, setActiveTerms] = useState<ActiveTerms | null>(null);

  useEffect(() => {
    const checkTerms = async () => {
      try {
        const res = await fetch('/api/auth/me', { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          if (data.termsOutdated && data.activeTerms) {
            setTermsOutdated(true);
            setActiveTerms(data.activeTerms);
          }
        }
      } catch (error) {
        console.error('Error checking terms:', error);
      }
    };
    checkTerms();
  }, []);

  return (
    <>
      <TenantAppShell>
        {/* SPEC-131-0-B2 L3: a faixa "seu WhatsApp desconectou" no topo (só nesse estado). O invólucro é SEMPRE o mesmo
            (a página não remonta quando a faixa aparece) e dá à página a altura que sobra — o `h-full` dela continua valendo. */}
        <div className="flex h-full min-h-0 flex-col">
          <FaixaDaLinha />
          <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
        </div>
      </TenantAppShell>
      {termsOutdated && activeTerms && (
        <TermsAcceptanceModal
          activeTerms={activeTerms}
          onAccepted={() => setTermsOutdated(false)}
        />
      )}
    </>
  );
}
