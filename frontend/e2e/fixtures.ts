import { execFileSync } from 'node:child_process';
import path from 'node:path';

export type SeedScenario =
  | 'member'
  | 'public-new'
  | 'public-returning'
  | 'comments'
  | 'my-rsvps'
  | 'live-updates';

const BACKEND_DIR = path.resolve(__dirname, '../../backend');

export function seed<T = Record<string, string>>(scenario: SeedScenario): T {
  const output = execFileSync('uv', ['run', 'python', 'manage.py', 'e2e_seed', scenario], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  });
  return JSON.parse(output.trim()) as T;
}
