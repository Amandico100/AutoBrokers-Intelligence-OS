import { TenantSidebar } from '@/components/layout/TenantSidebar';
import { TenantTopBar } from '@/components/layout/TenantTopBar';
import { TenantBottomNav } from '@/components/layout/TenantBottomNav';

/**
 * Casca visual do dashboard da corretora.
 * Desktop: sidebar fixa + conteúdo. Mobile: top bar (drawer) + conteúdo + bottom nav.
 * O `main` é o único container de altura; páginas internas gerenciam seu próprio scroll
 * (`h-full overflow-y-auto` ou layout flex como no chat).
 */
export function TenantAppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <TenantSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TenantTopBar />
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
        <TenantBottomNav />
      </div>
    </div>
  );
}

export default TenantAppShell;
