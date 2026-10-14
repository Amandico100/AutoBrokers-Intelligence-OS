/** @type {import('next').NextConfig} */
const { withSentryConfig } = require("@sentry/nextjs");

// 11/10/2026 · o Founder não tinha como saber QUAL versão do site está no ar (o Implantar do smith-web leva ~45 min e
// três vezes a tela antiga pareceu "não subiu nada"). O build grava quando foi feito e de qual commit; `/api/versao`
// mostra. Nada de segredo: data, commit curto.
function commitDoBuild() {
  const doAmbiente = process.env.SOURCE_COMMIT || process.env.GIT_SHA || process.env.COMMIT_SHA
    || process.env.RAILWAY_GIT_COMMIT_SHA || process.env.VERCEL_GIT_COMMIT_SHA || '';
  if (doAmbiente) return String(doAmbiente).slice(0, 12);
  try {
    const fs = require('fs');
    const path = require('path');
    let gitDir = '.git';
    if (fs.statSync(gitDir).isFile()) {
      // worktree: `.git` é um arquivo "gitdir: <caminho>"
      gitDir = fs.readFileSync(gitDir, 'utf8').trim().replace(/^gitdir:\s*/, '');
    }
    const head = fs.readFileSync(path.join(gitDir, 'HEAD'), 'utf8').trim();
    if (!head.startsWith('ref:')) return head.slice(0, 12);
    const ref = head.slice(5).trim();
    for (const base of [gitDir, path.join(gitDir, '..', '..')]) {
      try { return fs.readFileSync(path.join(base, ref), 'utf8').trim().slice(0, 12); } catch {}
    }
    const packed = fs.readFileSync(path.join(gitDir, '..', '..', 'packed-refs'), 'utf8');
    const linha = packed.split('\n').find((l) => l.endsWith(' ' + ref));
    return linha ? linha.slice(0, 12) : 'desconhecido';
  } catch {
    return 'desconhecido';
  }
}

const nextConfig = {
  env: {
    AUTOBROKERS_BUILD_EM: new Date().toISOString(),
    AUTOBROKERS_BUILD_COMMIT: commitDoBuild(),
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // 📊 14/10/2026 (SPEC-132): o build do EasyPanel morreu 4× logo depois de "Checking validity of types" (4–7 min;
  // os builds bons levavam 5–10), com o MESMO código que passou `tsc --noEmit` e `next build` completo aqui. É o
  // servidor sem memória na checagem de tipos, não erro de código. A checagem continua sendo GATE de toda SPEC
  // (`npx tsc --noEmit`, CLAUDE.md §9.1 / protocolo §4); o servidor só deixa de repeti-la.
  typescript: {
    ignoreBuildErrors: true,
  },
  images: { unoptimized: true },
  // SPEC-132-A (A4) — o `middleware.ts` intercepta `/api/upload` (o matcher pega toda rota sem ponto), e o Next 15.5
  // corta o corpo que passa pelo middleware em 10 MB (`config-shared.js`: `middlewareClientMaxBodySize: 10485760`).
  // O chat aceita 20 MB por arquivo (B5): sem esta linha, o arquivo de 10–20 MB chegava TRUNCADO à rota de upload.
  // 25 MB = os 20 MB do arquivo + a moldura do multipart, com folga.
  experimental: {
    middlewareClientMaxBodySize: '25mb',
  },
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