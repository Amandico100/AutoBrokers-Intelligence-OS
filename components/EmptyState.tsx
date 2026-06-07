'use client';

/**
 * Estado vazio do chat. Limpeza B0: removida a dependência de `smith-logo.png`,
 * substituída pelo BrandMark geométrico provisório do AutoBrokers (inline, herda cor do tema).
 * A experiência chat-first final (saudação + 2 atalhos) será entregue no B2 — aqui não há lógica de chat.
 */
export default function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      <div className="flex flex-col items-center gap-6 max-w-2xl w-full">
        <div className="flex items-center gap-3 mb-4">
          <span className="flex h-16 w-16 items-center justify-center text-primary">
            <svg width="44" height="44" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <rect
                x="1.2"
                y="1.2"
                width="19.6"
                height="19.6"
                rx="6"
                stroke="currentColor"
                strokeWidth="1.4"
              />
              <rect
                x="7.2"
                y="7.2"
                width="7.6"
                height="7.6"
                rx="2"
                transform="rotate(45 11 11)"
                stroke="currentColor"
                strokeWidth="1.4"
              />
            </svg>
          </span>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
            AutoBrokers
          </h1>
        </div>

        <div className="text-center space-y-2">
          <h2 className="text-2xl font-semibold text-foreground">Bem-vindo ao AutoBrokers</h2>
          <p className="text-lg text-muted-foreground">Seu copiloto operacional para seguros</p>
        </div>
      </div>
    </div>
  );
}
