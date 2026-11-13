import { defineRailway, github, preserve, project, service } from "railway/iac";

const SERVICE_NAME = "pda";

export const partial = SERVICE_NAME;

const PRESERVED_VARIABLES = [
  "ALLOWED_HOSTS",
  "B2_APPLICATION_KEY",
  "B2_BUCKET_NAME",
  "B2_ENDPOINT_URL",
  "B2_KEY_ID",
  "B2_REGION",
  "BREVO_API_KEY",
  "BREVO_FROM_EMAIL",
  "DATABASE_URL",
  "DEBUG",
  "FRONTEND_BASE_URL",
  "GIPHY_API_KEY",
  "GITHUB_APP_ID",
  "GITHUB_APP_INSTALLATION_ID",
  "GITHUB_APP_PRIVATE_KEY",
  "GITHUB_REPO",
  "PEXELS_API_KEY",
  "RESEND_API_KEY",
  "RESEND_FROM_EMAIL",
  "SECRET_KEY",
  "VETTING_EMAIL",
];

export default defineRailway(() => {
  const pda = service(SERVICE_NAME, {
    source: github("ProteinDeficientsAnonymous/pda"),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile",
    },
    deploy: {
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 10,
    },
    env: Object.fromEntries(PRESERVED_VARIABLES.map((name) => [name, preserve()])),
  });
  return project("protein.deficients.anonymous", {
    resources: [pda],
  });
});
