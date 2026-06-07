import { TenantNav } from '@/components/layout/TenantNav';

/** Sidebar tenant — visível apenas no desktop (lg+). */
export function TenantSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-border bg-surface lg:flex lg:flex-col">
      <TenantNav />
    </aside>
  );
}

export default TenantSidebar;
