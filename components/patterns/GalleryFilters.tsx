import { cn } from '@/lib/utils';
import { Icon } from '@/components/ui/Icon';
import { icons } from '@/lib/icons';

export interface GalleryFiltersProps {
  search?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  categories?: string[];
  activeCategory?: string;
  onCategoryChange?: (category: string) => void;
}

/** Busca + filtros de categoria do padrão Galeria. Controlado (estado fica no pai). */
export function GalleryFilters({
  search,
  onSearchChange,
  searchPlaceholder = 'Buscar…',
  categories,
  activeCategory,
  onCategoryChange,
}: GalleryFiltersProps) {
  return (
    <div className="space-y-3">
      {onSearchChange && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <Icon icon={icons.buscar} size={16} className="text-muted-foreground" />
          <input
            value={search ?? ''}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>
      )}

      {categories && categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {categories.map((c) => {
            const active = c === activeCategory;
            return (
              <button
                key={c}
                type="button"
                onClick={() => onCategoryChange?.(c)}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs transition-colors',
                  active
                    ? 'border-primary/40 bg-brand-soft text-primary'
                    : 'border-border text-muted-foreground hover:text-foreground',
                )}
              >
                {c}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default GalleryFilters;
