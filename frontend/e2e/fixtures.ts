import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export type SeedScenario =
  | 'member'
  | 'public-new'
  | 'public-returning'
  | 'comments'
  | 'my-rsvps'
  | 'live-updates';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '../..');
const BACKEND_DIR = path.resolve(ROOT_DIR, 'backend');

function resolveDatabaseUrl(): string {
  return execFileSync('./scripts/dev_pg_db.sh', ['url'], {
    cwd: ROOT_DIR,
    encoding: 'utf-8',
  }).trim();
}

export function seed<T = Record<string, string>>(scenario: SeedScenario): T {
  const output = execFileSync('uv', ['run', 'python', 'manage.py', 'e2e_seed', scenario], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
    env: { ...process.env, DATABASE_URL: resolveDatabaseUrl() },
  });
  return JSON.parse(output.trim()) as T;
}
