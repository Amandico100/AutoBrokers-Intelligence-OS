import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DetailHeader, type DetailHeaderProps } from '@/components/patterns/DetailHeader';

export interface DetailTab {
  value: string;
  label: string;
  content: React.ReactNode;
}

export interface DetailShellProps {
  header: DetailHeaderProps;
  /** Abas internas (opcional). Se ausente, renderiza `children`. */
  tabs?: DetailTab[];
  children?: React.ReactNode;
  /** Bloco lateral opcional (requisitos/resumo/permissões). */
  side?: React.ReactNode;
}

/** Página de detalhe em camadas (header + abas/seções + bloco lateral). Visual, sem lógica. */
export function DetailShell({ header, tabs, children, side }: DetailShellProps) {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <DetailHeader {...header} />
      <div className={side ? 'grid gap-6 lg:grid-cols-[1fr_18rem]' : undefined}>
        <div className="space-y-6">
          {tabs && tabs.length > 0 ? (
            <Tabs defaultValue={tabs[0].value} className="w-full">
              <TabsList className="bg-surface-2">
                {tabs.map((t) => (
                  <TabsTrigger key={t.value} value={t.value}>
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              {tabs.map((t) => (
                <TabsContent key={t.value} value={t.value} className="mt-4 space-y-4">
                  {t.content}
                </TabsContent>
              ))}
            </Tabs>
          ) : (
            children
          )}
        </div>
        {side && <aside className="space-y-4">{side}</aside>}
      </div>
    </div>
  );
}

export default DetailShell;
