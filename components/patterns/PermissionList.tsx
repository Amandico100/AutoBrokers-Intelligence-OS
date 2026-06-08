import { cn } from '@/lib/utils';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

export interface PermissionItem {
  label: string;
  /** false = não vai poder (mostra X); padrão = pode (mostra check). */
  allowed?: boolean;
}

export interface PermissionGroup {
  title?: string;
  items: PermissionItem[];
}

/** Lista de permissões agrupadas (linguagem de corretora, sem jargão técnico). */
export function PermissionList({ groups }: { groups: PermissionGroup[] }) {
  return (
    <div className="space-y-4">
      {groups.map((g, gi) => (
        <div key={gi} className="space-y-2">
          {g.title && (
            <p className="font-mono text-[10px] uppercase tracking-[0.06em] text-faint">{g.title}</p>
          )}
          <ul className="space-y-1.5">
            {g.items.map((it, i) => {
              const denied = it.allowed === false;
              return (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className={cn('mt-0.5 shrink-0', denied ? 'text-danger' : 'text-success')}>
                    <Icon icon={denied ? icons.negado : icons.check} size={15} />
                  </span>
                  <span className={cn(denied ? 'text-muted-foreground' : 'text-foreground-2')}>
                    {it.label}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default PermissionList;
