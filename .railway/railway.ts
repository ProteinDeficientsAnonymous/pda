import { defineRailway, github, preserve, project, service } from "railway/iac";

export const partial = "pda";

const SERVICE_NAMES: Record<string, string> = {
  production: "pda",
  staging: "staging",
};

const PRESERVED_VARIABLES = [
  "ALLOWED_HOSTS",
  "B2_APPLICATION_KEY",
  "B2_BUCKET_NAME",
  "B2_ENDPOINT_URL",
  "B2_KEY_ID",
  "B2_REGION",
  "BREVO_API_KEY",
  "BREVO_FROM_EMAIL",
  "BREVO_FROM_NAME",
  "CORS_ALLOWED_ORIGINS",
  "DATABASE_URL",
  "DEBUG",
  "DEFAULT_FROM_EMAIL",
  "EMAIL_HOST",
  "EMAIL_HOST_PASSWORD",
  "EMAIL_HOST_USER",
  "FRONTEND_BASE_URL",
  "GIPHY_API_KEY",
  "GITHUB_APP_ID",
  "GITHUB_APP_INSTALLATION_ID",
  "GITHUB_APP_PRIVATE_KEY",
  "GITHUB_REPO",
  "PDA_DB_POOL_MAX_SIZE",
  "PDA_MEMORY_PROFILE",
  "PDA_MEMRAY",
  "PDA_MEMRAY_OUTPUT",
  "PDA_WORKER_MAX_AGE",
  "PDA_WORKER_MAX_AGE_JITTER",
  "PEXELS_API_KEY",
  "RESEND_API_KEY",
  "RESEND_FROM_EMAIL",
  "SECRET_KEY",
  "TRUSTED_PROXY_COUNT",
  "VETTING_EMAIL",
  "WEB_CONCURRENCY",
];

export default defineRailway((ctx) => {
  const environment = ctx.environment ?? "";
  const serviceName = SERVICE_NAMES[environment];
  if (!serviceName) {
    throw new Error(`no pda service name for railway environment "${environment}"`);
  }
  const web = service(serviceName, {
    // github() defaults branch to main; null keeps prod's auto-deploy trigger disconnected
    source: github("ProteinDeficientsAnonymous/pda", {
      branch: ctx.isEnvironment("production") ? null : "main",
    }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile",
    },
    deploy: {
      // matches the current dashboard setting; only staging has it on
      ipv6EgressEnabled: ctx.isEnvironment("staging") ? true : null,
    },
    env: Object.fromEntries(PRESERVED_VARIABLES.map((name) => [name, preserve()])),
  });
  return project("protein.deficients.anonymous", {
    resources: [web],
  });
});
