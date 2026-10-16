import { cleanName, lookupName, composeStory } from './research.js';

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' };
const SESSION_AGE = 60 * 60 * 24 * 14;
const encoder = new TextEncoder();

class ApiError extends Error { constructor(code, message) { super(message); this.status = code; } }
function json(payload, status = 200, headers = {}) { return new Response(JSON.stringify(payload), { status, headers: { ...JSON_HEADERS, ...headers } }); }
function assert(condition, message, status = 400) { if (!condition) throw new ApiError(status, message); }
function failOnWrongOrigin(request) {
  const origin = request.headers.get('Origin');
  if (origin && new URL(origin).origin !== new URL(request.url).origin) throw new ApiError(403, 'Invalid request origin.');
}
async function body(request) {
  const size = Number(request.headers.get('content-length') || 0);
  assert(size <= 100_000, 'Request too large.', 413);
  let text;
  try { text = await request.text(); } catch { throw new ApiError(400, 'Invalid body.'); }
  assert(text.length < 100_000, 'Request too large.', 413);
  let data;
  try { data = JSON.parse(text); } catch { throw new ApiError(400, 'Expected a JSON request.'); }
  assert(data && typeof data === 'object' && !Array.isArray(data), 'Expected a JSON object.');
  return data;
}
function requiredString(value, field, max = 5000) {
  assert(typeof value === 'string' && value.trim().length > 0 && value.trim().length <= max, `${field} must be 1–${max} characters.`);
  return value.trim();
}
function optionalString(value, field, max = 5000) {
  if (value == null || value === '') return '';
  assert(typeof value === 'string' && value.length <= max, `${field} must be at most ${max} characters.`);
  return value.trim();
}
function cookieValue(request, name) {
  const cookies = request.headers.get('Cookie') || '';
  return cookies.split(';').map(v => v.trim()).find(v => v.startsWith(name + '='))?.slice(name.length + 1) || '';
}
function sessionCookie(token, request) {
  const secure = new URL(request.url).protocol === 'https:' ? '; Secure' : '';
  return `origin_session=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${SESSION_AGE}${secure}`;
}
function clearCookie(request) { return sessionCookie('', request).replace(`Max-Age=${SESSION_AGE}`, 'Max-Age=0'); }
function hex(bytes) { return [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2, '0')).join(''); }
async function sha256(value) { return hex(await crypto.subtle.digest('SHA-256', encoder.encode(value))); }
async function hashPassword(password, salt) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(password), 'PBKDF2', false, ['deriveBits']);
  const hash = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: encoder.encode(salt), iterations: 100000, hash: 'SHA-256' }, key, 256);
  return hex(hash);
}
async function authenticated(request, env) {
  const token = cookieValue(request, 'origin_session');
  if (!token || !/^[a-f0-9]{64}$/.test(token)) throw new ApiError(401, 'Sign in to continue.');
  const key = await sha256(token);
  const account = await env.DB.prepare('SELECT users.id, users.email FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token_hash = ? AND sessions.expires_at > ?').bind(key, Date.now()).first();
  if (!account) throw new ApiError(401, 'Session expired. Sign in again.');
  return account;
}
async function checkAuthRateLimit(request, env, email) {
  const windowStart = Math.floor(Date.now() / 900000) * 900000;
  const ip = request.headers.get('CF-Connecting-IP');
  const keys = [{ key: `email:${await sha256(email)}`, limit: 8 }];
  if (ip) keys.push({ key: `ip:${await sha256(ip)}`, limit: 30 });
  for (const item of keys) {
    await env.DB.prepare(`INSERT INTO auth_limits(key,window_start,hits) VALUES(?,?,1)
      ON CONFLICT(key) DO UPDATE SET
      hits=CASE WHEN auth_limits.window_start < excluded.window_start THEN 1 ELSE auth_limits.hits+1 END,
      window_start=CASE WHEN auth_limits.window_start < excluded.window_start THEN excluded.window_start ELSE auth_limits.window_start END`)
      .bind(item.key, windowStart).run();
    const row = await env.DB.prepare('SELECT hits FROM auth_limits WHERE key = ?').bind(item.key).first();
    if (row.hits > item.limit) throw new ApiError(429, 'Too many sign-in attempts. Please try again in 15 minutes.');
  }
}

async function createSession(request, env, user) {
  const token = hex(crypto.getRandomValues(new Uint8Array(32)));
  await env.DB.prepare('INSERT INTO sessions(token_hash, user_id, expires_at) VALUES(?,?,?)').bind(await sha256(token), user.id, Date.now() + SESSION_AGE * 1000).run();
  return json({ user: { id: user.id, email: user.email } }, 200, { 'set-cookie': sessionCookie(token, request) });
}
function publicResearch(row) { return { id: row.id, name: row.name, sources: parseJson(row.sources_json, []), links: parseJson(row.links_json, []), notice: row.notice, createdAt: row.created_at }; }
function publicStory(row) { return { id: row.id, title: row.title, name: row.name, narrative: row.narrative, notes: row.notes || '', sources: parseJson(row.sources_json, []), createdAt: row.created_at, updatedAt: row.updated_at }; }
function publicRecording(row) { return { id: row.id, title: row.title, storyId: row.story_id || null, description: row.description || '', createdAt: row.created_at }; }
function parseJson(value, fallback) { try { return JSON.parse(value); } catch { return fallback; } }
function now() { return new Date().toISOString(); }

export async function handleApi(request, env) {
  try {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/$/, '') || '/';
    const method = request.method;
    if (!['GET', 'POST', 'PATCH', 'DELETE'].includes(method)) return json({ error: 'Method not allowed.' }, 405, { Allow: 'GET, POST, PATCH, DELETE' });
    if (method !== 'GET') failOnWrongOrigin(request);
    if (path === '/api/health' && method === 'GET') return json({ status: 'ok', service: 'origin', runtime: 'cloudflare-workers' });
    if (path === '/api/research/lookup' && method === 'GET') {
      const name = cleanName(url.searchParams.get('name') || '');
      return json(await lookupName(name));
    }
    assert(env.DB, 'Cloudflare D1 binding DB is missing.', 503);
    if (path === '/api/auth/register' && method === 'POST') {
      const data = await body(request);
      const email = requiredString(data.email, 'Email', 254).toLowerCase();
      assert(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email), 'Enter a valid email.');
      await checkAuthRateLimit(request, env, email);
      assert(typeof data.password === 'string' && data.password.length >= 12 && data.password.length <= 128, 'Password must contain 12–128 characters.');
      const existing = await env.DB.prepare('SELECT id FROM users WHERE email = ?').bind(email).first();
      assert(!existing, 'An account already exists for that email.', 409);
      const user = { id: crypto.randomUUID(), email };
      const salt = hex(crypto.getRandomValues(new Uint8Array(16)));
      const hash = await hashPassword(data.password, salt);
      try { await env.DB.prepare('INSERT INTO users(id,email,password_salt,password_hash,created_at) VALUES(?,?,?,?,?)').bind(user.id, email, salt, hash, now()).run(); }
      catch { throw new ApiError(409, 'Unable to register this email.'); }
      return createSession(request, env, user);
    }
    if (path === '/api/auth/login' && method === 'POST') {
      const data = await body(request);
      const email = requiredString(data.email, 'Email', 254).toLowerCase();
      await checkAuthRateLimit(request, env, email);
      assert(typeof data.password === 'string', 'Password is required.');
      const row = await env.DB.prepare('SELECT * FROM users WHERE email = ?').bind(email).first();
      // Make invalid accounts and invalid passwords follow the same verification path.
      const calc = await hashPassword(data.password, row?.password_salt || 'invalid-account-salt');
      if (!row || calc !== row.password_hash) throw new ApiError(401, 'Invalid email or password.');
      return createSession(request, env, row);
    }
    if (path === '/api/auth/logout' && method === 'POST') {
      const token = cookieValue(request, 'origin_session');
      if (token) await env.DB.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(await sha256(token)).run();
      return json({ ok: true }, 200, { 'set-cookie': clearCookie(request) });
    }
    const user = await authenticated(request, env);
    if (path === '/api/auth/me' && method === 'GET') return json({ user });
    if (path === '/api/overview' && method === 'GET') {
      const [research, stories, recordings] = await Promise.all([
        env.DB.prepare('SELECT * FROM research WHERE user_id = ? ORDER BY created_at DESC LIMIT 30').bind(user.id).all(),
        env.DB.prepare('SELECT * FROM stories WHERE user_id = ? ORDER BY updated_at DESC LIMIT 30').bind(user.id).all(),
        env.DB.prepare('SELECT * FROM recordings WHERE user_id = ? ORDER BY created_at DESC LIMIT 30').bind(user.id).all()
      ]);
      return json({ research: research.results.map(publicResearch), stories: stories.results.map(publicStory), recordings: recordings.results.map(publicRecording) });
    }
    if (path === '/api/research' && method === 'POST') {
      const data = await body(request);
      const name = cleanName(data.name);
      const result = await lookupName(name);
      const id = crypto.randomUUID();
      const created = now();
      await env.DB.prepare('INSERT INTO research(id,user_id,name,sources_json,links_json,notice,created_at) VALUES(?,?,?,?,?,?,?)').bind(id, user.id, name, JSON.stringify(result.sources), JSON.stringify(result.links), result.notice, created).run();
      return json({ id, ...result, createdAt: created }, 201);
    }
    if (path === '/api/stories' && method === 'POST') {
      const data = await body(request);
      const name = cleanName(data.name);
      const title = requiredString(data.title, 'Title', 140);
      const notes = optionalString(data.notes, 'Notes', 10000);
      let sources = [];
      if (data.researchId) {
        const research = await env.DB.prepare('SELECT * FROM research WHERE id = ? AND user_id = ?').bind(data.researchId, user.id).first();
        assert(research, 'Research not found.', 404);
        assert(research.name === name, 'Story name must match the selected research.');
        sources = parseJson(research.sources_json, []);
      }
      const narrative = data.narrative ? requiredString(data.narrative, 'Narrative', 30000) : composeStory(name, sources, notes);
      const item = { id: crypto.randomUUID(), title, name, narrative, notes, sources, createdAt: now(), updatedAt: now() };
      await env.DB.prepare('INSERT INTO stories(id,user_id,title,name,narrative,notes,sources_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)').bind(item.id, user.id, title, name, narrative, notes, JSON.stringify(sources), item.createdAt, item.updatedAt).run();
      return json(item, 201);
    }
    const storyMatch = path.match(/^\/api\/stories\/([0-9a-f-]{36})$/);
    if (storyMatch && method === 'PATCH') {
      const data = await body(request);
      const old = await env.DB.prepare('SELECT * FROM stories WHERE id = ? AND user_id = ?').bind(storyMatch[1], user.id).first();
      assert(old, 'Story not found.', 404);
      const title = data.title == null ? old.title : requiredString(data.title, 'Title', 140);
      const narrative = data.narrative == null ? old.narrative : requiredString(data.narrative, 'Narrative', 30000);
      const notes = data.notes == null ? old.notes : optionalString(data.notes, 'Notes', 10000);
      await env.DB.prepare('UPDATE stories SET title = ?, narrative = ?, notes = ?, updated_at = ? WHERE id = ? AND user_id = ?').bind(title, narrative, notes, now(), old.id, user.id).run();
      return json({ ok: true });
    }
    if (storyMatch && method === 'DELETE') {
      await env.DB.prepare('DELETE FROM stories WHERE id = ? AND user_id = ?').bind(storyMatch[1], user.id).run();
      return json({ ok: true });
    }
    if (path === '/api/recordings' && method === 'POST') {
      const data = await body(request);
      const id = crypto.randomUUID();
      const title = requiredString(data.title, 'Title', 140);
      const description = optionalString(data.description, 'Description', 2000);
      if (data.storyId) {
        const story = await env.DB.prepare('SELECT id FROM stories WHERE id=? AND user_id=?').bind(data.storyId, user.id).first();
        assert(story, 'Story not found.', 404);
      }
      const createdAt = now();
      await env.DB.prepare('INSERT INTO recordings(id,user_id,title,story_id,description,created_at) VALUES(?,?,?,?,?,?)').bind(id, user.id, title, data.storyId || null, description, createdAt).run();
      return json({ id, title, description, storyId: data.storyId || null, createdAt }, 201);
    }
    const recordingMatch = path.match(/^\/api\/recordings\/([0-9a-f-]{36})$/);
    if (recordingMatch && method === 'DELETE') {
      await env.DB.prepare('DELETE FROM recordings WHERE id=? AND user_id=?').bind(recordingMatch[1], user.id).run();
      return json({ ok: true });
    }
    return json({ error: 'Endpoint not found.' }, 404);
  } catch (error) {
    if (error instanceof ApiError) return json({ error: error.message }, error.status);
    if (error?.message === 'Enter a name to research.' || error?.message?.startsWith('Use a name between')) return json({ error: error.message }, 400);
    console.error('API error', error);
    return json({ error: 'Request failed. Try again later.' }, 500);
  }
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path.startsWith('/api/')) return handleApi(request, env);
    return env.ASSETS.fetch(request);
  }
};
