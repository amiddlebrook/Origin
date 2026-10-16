import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const configPath = 'wrangler.jsonc';
const config = JSON.parse(readFileSync(configPath, 'utf8'));
const binding = config.d1_databases?.find((item) => item.binding === 'DB');
const validId = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;

if (!binding?.database_name || !process.env.CLOUDFLARE_API_TOKEN || !process.env.CLOUDFLARE_ACCOUNT_ID) {
  throw new Error('D1 binding or required Cloudflare API token/account ID is missing.');
}

function wrangler(...args) {
  try {
    return execFileSync('npx', ['--no-install', 'wrangler', ...args], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 120_000,
      maxBuffer: 4 * 1024 * 1024,
    }).trim();
  } catch (error) {
    throw new Error(`wrangler ${args.join(' ')} failed: ${error.stderr?.toString().trim() || error.message}`);
  }
}

function findDatabase() {
  const output = wrangler('d1', 'list', '--json');
  let data;
  try {
    data = JSON.parse(output);
  } catch {
    throw new Error('Unable to parse `wrangler d1 list --json` response.');
  }
  const databases = Array.isArray(data) ? data : data.result ?? data.databases;
  if (!Array.isArray(databases)) throw new Error('Wrangler returned an unexpected D1 list format.');
  const matches = databases.filter((item) => (item.name ?? item.database_name) === binding.database_name);
  if (matches.length > 1) throw new Error('Multiple D1 databases have the same configured name.');
  return matches[0] ?? null;
}

let database = findDatabase();
if (!database) {
  console.log(`Creating Cloudflare D1 database ${binding.database_name} using Wrangler...`);
  wrangler('d1', 'create', binding.database_name, '--update-config=false');
  database = findDatabase();
  if (!database) throw new Error('D1 was created but cannot yet be found. Re-run the workflow.');
} else {
  console.log(`Reusing existing Cloudflare D1 database ${binding.database_name}.`);
}

const id = database.uuid ?? database.id ?? database.database_id;
if (!validId.test(id ?? '')) throw new Error('Wrangler returned an invalid D1 database UUID.');

const override = process.env.CLOUDFLARE_D1_DATABASE_ID?.trim();
if (override && override !== id) {
  throw new Error('Optional CLOUDFLARE_D1_DATABASE_ID does not match the database found by Wrangler.');
}

binding.database_id = id;
writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n');
console.log(`D1 binding ${binding.binding} configured for ${binding.database_name} (${id}).`);
