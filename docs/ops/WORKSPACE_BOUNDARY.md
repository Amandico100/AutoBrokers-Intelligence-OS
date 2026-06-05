# AutoBrokers Intelligence OS Workspace Boundary

## Official Sandbox Directory

The official editable sandbox for this project is:

```txt
C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Intelligence-OS
```

All implementation, diagnostics, Git operations, builds, commits, and pushes for the Smith-based sandbox must happen inside this directory.

## Allowed To Edit

- Files tracked by this repository.
- New project files created inside this repository for the AutoBrokers Intelligence OS sandbox.
- Documentation, configuration examples, frontend, backend, and operational files that belong to this repository.

## Legacy And Quarantine Areas

The following folders are not executable sources for this sandbox:

- `.worktrees/`
- `AUTOBROKERS_AGENT_OS_WORKSPACE/`
- `AUTOBROKERS_RESULTA_INTAKE/`
- `ResultVision/`
- `ResultVision_block2a_clean/`
- `QUARENTENA_LEGADO*/`

They may exist as local reference, quarantine, or historical material outside this repository, but they must not be copied into this sandbox without explicit written approval from the Architect/Fundador.

## Required Batch Start Check

Every new batch must start by confirming the Git top-level:

```bash
git rev-parse --show-toplevel
```

The command must return the official sandbox directory above. If it does not, stop.

## Local Settings And Secrets

- Do not use old `.claude/settings.json` or `.claude/settings.local.json` files as operational rules.
- Do not commit secrets.
- Do not commit `.env` files.
- Keep only safe example env files such as `.env.example` and `.env.local.example`.
- Never print credential values in logs, reports, commits, or screenshots.

## Sandbox Services

EasyPanel and Supabase are sandbox services for this project unless explicitly promoted later. They must not be treated as production infrastructure.
