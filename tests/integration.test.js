import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { handleApi } from '../src/worker.js';

function setup() {
  const db = new DatabaseSync(':memory:');
  db.exec('PRAGMA foreign_keys=ON;');
  db.exec(readFileSync(new URL('../migrations/0001_init.sql', import.meta.url), 'utf-8'));
  const DB = { prepare(query) { const params = []; const stmt = db.prepare(query);
    const bound = { bind(...values) { params.splice(0, params.length, ...values); return bound; },
      async first() { return stmt.get(...params) || null; },
      async all() { return { results: stmt.all(...params) }; },
      async run() { return stmt.run(...params); } }; return bound;
  } };
  return { db, env: { DB } };
}
const base = 'https://origin.example';
async function call(env, path, method='GET', data=null, cookie='') {
  const headers = { Origin: base };
  if (cookie) headers.Cookie = cookie;
  const request = new Request(`${base}/api${path}`, { method, headers, ...(data !== null ? { body: JSON.stringify(data) } : {}) });
  const response = await handleApi(request, env);
  return { response, status: response.status, data: await response.json(), cookie: response.headers.get('set-cookie')?.split(';')[0] || cookie };
}
test('register, login, sessions, story CRUD and user isolation', async () => {
  const { env, db } = setup();
  const initial = await call(env, '/overview');
  assert.equal(initial.status, 401);
  const a = await call(env, '/auth/register', 'POST', { email:'one@example.com', password:'a-very-secure-password' });
  assert.equal(a.status, 200, JSON.stringify(a.data));
  assert.match(a.response.headers.get('set-cookie'), /HttpOnly/);
  assert.match(a.response.headers.get('set-cookie'), /SameSite=Lax/);
  const bad = await call(env, '/auth/login', 'POST', { email:'one@example.com', password:'not-correct' });
  assert.equal(bad.status, 401);
  const valid = await call(env, '/auth/login', 'POST', { email:'one@example.com', password:'a-very-secure-password' });
  assert.equal(valid.status, 200);
  const newStory = await call(env, '/stories', 'POST', { name:'Avery', title:'My family story', notes:'Mom remembers a village in Scotland.' }, a.cookie);
  assert.equal(newStory.status, 201, JSON.stringify(newStory.data));
  assert.match(newStory.data.narrative, /not a verified family lineage/);
  const b = await call(env, '/auth/register', 'POST', { email:'two@example.com', password:'another-very-long-password' });
  assert.equal(b.status, 200);
  const someoneElse = await call(env, `/stories/${newStory.data.id}`, 'PATCH', { title:'Tampered!' }, b.cookie);
  assert.equal(someoneElse.status, 404);
  const dataA = await call(env, '/overview', 'GET', null, a.cookie);
  const dataB = await call(env, '/overview', 'GET', null, b.cookie);
  assert.equal(dataA.data.stories.length, 1);
  assert.equal(dataB.data.stories.length, 0);
  const edited = await call(env, `/stories/${newStory.data.id}`, 'PATCH', { title:'A carefully written history' }, a.cookie);
  assert.equal(edited.status, 200);
  const record = await call(env, '/recordings', 'POST', { title:'An interview with Mom', storyId:newStory.data.id }, a.cookie);
  assert.equal(record.status, 201);
  const logout = await call(env, '/auth/logout', 'POST', {}, a.cookie);
  assert.equal(logout.status, 200);
  assert.equal((await call(env, '/overview', 'GET', null, a.cookie)).status, 401);
  db.close();
});
test('D1 rate limits block repeated attempts for same account', async () => {
  const { env, db } = setup();
  let result;
  for (let i=0; i<9; i++) result = await call(env, '/auth/login', 'POST', { email:'guess@example.com', password:'wrong' });
  assert.equal(result.status, 429);
  db.close();
});
