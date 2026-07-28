import * as Sentry from "@sentry/nextjs";

// Sentry no NAVEGADOR do corretor.
//
// Duas coisas foram corrigidas aqui em 28/07/2026. As duas vinham do Smith
// original e nenhuma tinha sido olhada.
//
// 1. SESSION REPLAY ESTAVA LIGADO.
//    `replayIntegration()` grava um filme da tela. As telas deste produto
//    mostram CPF do segurado, número de apólice e conversa de WhatsApp — isso
//    subiria para o Sentry, contradizendo frontalmente o `send_default_pii=False`
//    que o backend declara em nome da LGPD.
//    O valor de assistir ao filme é menor que o risco de gravá-lo. Desligado.
//    Se um dia fizer falta, volta em uma linha — e COM `maskAllText: true` e
//    `blockAllMedia: true`, nunca sem.
//
// 2. `tracesSampleRate: 1.0` EM PRODUÇÃO.
//    Cem por cento das transações, sempre. Isso queima a cota da conta em dias
//    — e quando a cota acaba, o Sentry para de receber TAMBÉM os erros. Ou
//    seja: o excesso de zelo com métrica de performance derrubaria justamente
//    a coisa para a qual instalamos o Sentry.
//    Agora segue a mesma regra do backend: 10% em produção, 100% fora dela.
const producao = process.env.NODE_ENV === "production";

Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    environment: producao ? "production" : "development",
    // Amostragem vale só para métrica de performance. ERRO é sempre enviado.
    tracesSampleRate: producao ? 0.1 : 1.0,
    debug: false,
    sendDefaultPii: false,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
