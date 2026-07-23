import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export interface SeedScenarioMap {
  member: {
    event_id: string;
    event_title: string;
    event_location: string;
    user_phone: string;
    user_password: string;
    access_token: string;
  };
  'public-new': { event_id: string; event_title: string; event_location: string };
  'public-recognized': { event_id: string; event_title: string; user_phone: string };
  'public-returning': {
    event_id: string;
    event_title: string;
    user_phone: string;
    rsvp_token: string;
  };
  comments: { event_id: string; event_title: string; rsvp_token: string };
  'my-rsvps': { event_id: string; event_title: string; rsvp_token: string };
  'live-updates': {
    event_id: string;
    event_title: string;
    user_a_phone: string;
    user_a_password: string;
    user_b_phone: string;
    user_b_password: string;
  };
  'attendance-report': {
    event_id: string;
    event_title: string;
    host_phone: string;
    host_password: string;
  };
  'attendance-analytics': {
    admin_phone: string;
    admin_password: string;
    compliant_name: string;
    at_risk_name: string;
  };
}

export type SeedScenario = keyof SeedScenarioMap;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '../..');
const BACKEND_DIR = path.resolve(ROOT_DIR, 'backend');

function resolveDatabaseUrl(): string {
  // falls back to per-worktree postgres (make dev-pg) when DATABASE_URL is unset locally
  if (process.env.DATABASE_URL) {
    return process.env.DATABASE_URL;
  }
  return execFileSync('./scripts/dev_pg_db.sh', ['url'], {
    cwd: ROOT_DIR,
    encoding: 'utf-8',
  }).trim();
}

export function seed<S extends SeedScenario>(scenario: S): SeedScenarioMap[S] {
  const output = execFileSync('uv', ['run', 'python', 'manage.py', 'e2e_seed', scenario], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
    env: { ...process.env, DATABASE_URL: resolveDatabaseUrl() },
  });
  return JSON.parse(output.trim()) as SeedScenarioMap[S];
}
