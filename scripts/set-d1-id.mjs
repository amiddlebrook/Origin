import { readFileSync, writeFileSync } from 'node:fs';
const id = process.env.CLOUDFLARE_D1_DATABASE_ID;
if (!id || !/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(id)) {
  console.error('Missing or invalid CLOUDFLARE_D1_DATABASE_ID GitHub Actions secret.');
  process.exit(1);
}
const path = 'wrangler.jsonc';
const settings = JSON.parse(readFileSync(path, 'utf8'));
settings.d1_databases[0].database_id = id;
writeFileSync(path, JSON.stringify(settings, null, 2) + '\n');
console.log('D1 deployment binding configured.');
