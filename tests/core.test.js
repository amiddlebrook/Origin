import test from 'node:test';
import assert from 'node:assert/strict';
import { cleanName, researchLinks, composeStory } from '../src/research.js';
import { handleApi } from '../src/worker.js';

test('normalizes valid international names', () => {
  assert.equal(cleanName('  de   la  Cruz '), 'de la Cruz');
  assert.equal(cleanName('Ó Briain'), 'Ó Briain');
  assert.throws(() => cleanName('<script>alert(1)</script>'));
  assert.throws(() => cleanName(''));
});
test('source URLs are encoded and point to credible resources', () => {
  const links = researchLinks('Avery & family');
  assert.equal(links.length, 4);
  assert.ok(links[0].url.includes('Avery%20%26%20family'));
});
test('stories never claim unverified facts or manufacture citations', () => {
  const result = composeStory('Avery', [], 'Family memory passed down through generations.');
  assert.match(result, /not a verified family lineage/);
  assert.match(result, /Family memory/);
  assert.match(result, /No source excerpts/);
});
test('health endpoint works without D1 setup', async () => {
  const response = await handleApi(new Request('https://example.com/api/health'), {});
  assert.equal(response.status, 200);
  assert.equal((await response.json()).status, 'ok');
});
test('unknown authenticated endpoints require a session', async () => {
  const response = await handleApi(new Request('https://example.com/api/stories'), { DB: {} });
  assert.equal(response.status, 401);
});
test('cross-origin mutations are rejected', async () => {
  const response = await handleApi(new Request('https://example.com/api/auth/register', { method: 'POST', headers: { Origin: 'https://evil.example' }, body: '{}' }), { DB: {} });
  assert.equal(response.status, 403);
});
