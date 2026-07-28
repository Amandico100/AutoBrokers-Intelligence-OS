import * as Sentry from "@sentry/nextjs";

// Sentry no SERVIDOR do Next.js (runtime Node e Edge).
//
// Mesma correção do lado do navegador: `tracesSampleRate: 1.0` fixo queimava a
// cota, e cota esgotada faz o Sentry parar de receber os ERROS também.
//
// `sendDefaultPii: false` explícito: este processo enxerga cookie de sessão e
// corpo de requisição — e aqui o corpo carrega CPF e conversa de segurado. O
// padrão do SDK já é `false`; escrever mesmo assim é deliberado, porque um
// padrão que ninguém vê é um padrão que alguém inverte sem perceber.
const producao = process.env.NODE_ENV === "production";

const comum = {
    dsn: process.env.SENTRY_DSN,
    environment: producao ? "production" : "development",
    // Amostragem vale só para métrica de performance. ERRO é sempre enviado.
    tracesSampleRate: producao ? 0.1 : 1.0,
    debug: false,
    sendDefaultPii: false,
};

export async function register() {
    if (process.env.NEXT_RUNTIME === "nodejs") {
        Sentry.init(comum);
    }

    if (process.env.NEXT_RUNTIME === "edge") {
        Sentry.init(comum);
    }
}

export const onRequestError = Sentry.captureRequestError;
