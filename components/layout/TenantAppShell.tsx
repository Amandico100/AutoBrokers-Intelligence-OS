import { TenantSidebar } from '@/components/layout/TenantSidebar';
import { TenantTopBar } from '@/components/layout/TenantTopBar';

/**
 * Casca visual do dashboard da corretora.
 * Desktop: sidebar fixa + conteúdo. Mobile: top bar (☰ abre a gaveta com os 6 pilares + nova conversa) + conteúdo.
 *
 * SPEC-132-A (D-132A-02) — a barra de 6 atalhos do rodapé SAIU do celular: a navegação é o ☰ do topo, como no
 * ChatGPT e no Claude. 📊 Ela comia ≈ 56 px de toda tela e, com o `body{min-height:100vh}` maior que o
 * `100dvh` daqui, a página "dançava" ao rolar (sobrava espaço abaixo dela).
 *
 * O `main` é o único container de altura; páginas internas gerenciam seu próprio scroll
 * (`h-full overflow-y-auto` ou layout flex como no chat). A página não rola como um todo.
 */
export function TenantAppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
      <TenantSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TenantTopBar />
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
}

export default TenantAppShell;
