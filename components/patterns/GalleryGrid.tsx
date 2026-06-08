import { cn } from '@/lib/utils';

/** Grade responsiva do padrão Galeria (1 / 2 / 3 colunas). */
export function GalleryGrid({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3', className)}>
      {children}
    </div>
  );
}

export default GalleryGrid;
