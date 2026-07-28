/** @type {import('next').NextConfig} */
const { withSentryConfig } = require("@sentry/nextjs");

const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { unoptimized: true },
  // 43P-FINAL-2: playwright-core é server-only (CDP remoto via connectOverCDP);
  // nunca deve ser bundled pelo webpack.
  serverExternalPackages: ['playwright-core'],
  webpack: (config) => {
    config.ignoreWarnings = [
      { module: /node_modules\/@supabase\/realtime-js/ },
    ];
    return config;
  },
};

// Sentry — a organização e o projeto vinham CRAVADOS do Smith original:
//
//     org: "smith-v2-lionlabs"
//     project: "javascript-nextjs"
//
// Isso não impedia o erro de chegar (quem manda o evento é o DSN), mas
// impedia o que torna o erro útil: os *source maps*. Sem eles, o Sentry
// mostra `chunk-89133.js linha 1` em vez de `MessageBubble.tsx linha 87` — e
// aí o alerta chega, ninguém entende, e todo mundo passa a ignorar.
//
// Agora vem do ambiente. Sem as variáveis, o build segue normalmente e só o
// upload de source map não acontece: preferível a quebrar o build de quem
// clonar o repositório sem conta no Sentry.
module.exports = withSentryConfig(nextConfig, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  // Sem token de autenticação não há para onde subir source map. Declarar
  // explicitamente evita o build gastar tempo tentando e falhando em silêncio.
  disableSourceMapUpload: !process.env.SENTRY_AUTH_TOKEN,
});