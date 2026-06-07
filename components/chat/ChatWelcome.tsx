import { BrandMark } from '@/components/BrandMark';

/** Saudação do estado inicial do chat-first (sem mensagens). */
export function ChatWelcome() {
  return (
    <div className="flex flex-col items-center text-center">
      <BrandMark size={40} />
      <h1 className="mt-6 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
        Como posso ajudar sua corretora hoje?
      </h1>
      <p className="mt-3 max-w-md text-sm text-muted-foreground">
        Pergunte sobre atendimentos, seguradoras e documentos — ou crie um auxiliar para a sua operação.
      </p>
    </div>
  );
}

export default ChatWelcome;
