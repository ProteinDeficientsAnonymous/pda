import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const shotCall = /\bshot\(\s*[^,\n]+,\s*(['"])([^'"]+)\1/g;
const screenCall = /\bscreen\(\s*(['"])([^'"]+)\1/g;

export function duplicateShotNames(files) {
  const seen = new Map();
  const errors = [];
  for (const file of files) {
    for (const match of file.source.matchAll(shotCall)) {
      const name = match[2];
      const prior = seen.get(name);
      if (prior) errors.push(`duplicate shot name "${name}" in ${prior} and ${file.path}`);
      else seen.set(name, file.path);
    }
    for (const match of file.source.matchAll(screenCall)) {
      const name = match[2];
      const prior = seen.get(name);
      if (prior) errors.push(`duplicate shot name "${name}" in ${prior} and ${file.path}`);
      else seen.set(name, file.path);
    }
  }
  return errors;
}

const isMain = import.meta.url === pathToFileURL(process.argv[1] ?? '').href;
if (isMain) {
  const dir = path.dirname(fileURLToPath(import.meta.url));
  const names = (await readdir(dir)).filter((name) => name.endsWith('.spec.ts'));
  const files = await Promise.all(
    names.map(async (name) => ({
      path: name,
      source: await readFile(path.join(dir, name), 'utf8'),
    })),
  );
  const errors = duplicateShotNames(files);
  if (errors.length > 0) {
    console.error(errors.join('\n'));
    process.exit(1);
  }
}
