const state = { user: null, research: [], stories: [], recordings: [], latest: null, mediaRecorder: null, audioChunks: [], audioStream: null, recordingStarted: 0, recordingTimer: null };
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (input) => String(input ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const formatDate = (date) => { try { return new Date(date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); } catch { return ''; } };
let toastTimer;
function toast(message) { const element = $('#toast'); element.textContent = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => element.textContent = '', 4500); }
async function api(path, opts = {}) {
  let res;
  try { res = await fetch(`/api${path}`, { credentials: 'same-origin', ...opts, headers: { ...(opts.body ? { 'Content-Type': 'application/json' } : {}), ...opts.headers } }); }
  catch { throw new Error('Connection unavailable. Check your internet connection.'); }
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload.error || `Request failed (${res.status})`);
  return payload;
}
function modal(markup) { $('#modal-content').innerHTML = markup; $('#modal-backdrop').hidden = false; $('#modal-content').querySelector('input,textarea,button')?.focus(); }
function closeModal() { $('#modal-backdrop').hidden = true; $('#modal-content').innerHTML = ''; }
function handleError(error) { toast(error?.message || 'Something went wrong.'); }
function navigate(page) {
  if (!['home','explore','stories','memories'].includes(page)) page = 'home';
  document.querySelectorAll('.page').forEach(el => el.classList.toggle('active', el.id === `page-${page}`));
  document.querySelectorAll('.nav-link').forEach(el => { const active = el.dataset.page === page; el.classList.toggle('active', active); if (active) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current'); });
  $('#breadcrumb').textContent = ({ home:'Overview', explore:'Name explorer', stories:'My stories', memories:'Voice archive' })[page];
  $('#sidebar').classList.remove('open');
  window.scrollTo({ top: 0, behavior: 'instant' });
  if (location.hash !== `#${page}`) history.replaceState(null, '', `#${page}`);
}
function setAccount(user) {
  state.user = user;
  $('#account-button').innerHTML = user ? `${escapeHtml(user.email.split('@')[0])} <span>⌄</span>` : 'Sign in <span>↗</span>';
  renderOverview();
}
async function hydrate() {
  try { const data = await api('/auth/me'); setAccount(data.user); await loadOverview(); }
  catch { setAccount(null); renderOverview(); }
}
async function loadOverview() {
  if (!state.user) return;
  try {
    const data = await api('/overview');
    state.research = data.research || [];
    state.stories = data.stories || [];
    state.recordings = data.recordings || [];
    renderOverview();
  } catch (error) { handleError(error); }
}
function renderOverview() {
  $('#stories-count').textContent = state.stories.length;
  $('#story-total').textContent = `${state.stories.length} ${state.stories.length === 1 ? 'STORY' : 'STORIES'}`;
  renderResearchList(); renderStories(); renderRecordings();
}
function noItems(label, message) { return `<div class="empty-state small"><span>✣</span><h3>${label}</h3><p>${message}</p>${state.user ? '' : '<button class="minor-button" data-open-auth="register">Create a free archive</button>'}</div>`; }
function renderResearchList() {
  $('#research-list').innerHTML = state.research.length ? state.research.map(item => `<div class="stack-item"><div class="stack-monogram">${escapeHtml(item.name[0])}</div><div class="stack-body"><strong>${escapeHtml(item.name)}</strong><small>${formatDate(item.createdAt)} · ${(item.sources || []).length} reference leads</small></div><button class="minor-button" data-research-id="${escapeHtml(item.id)}">Open research ↗</button></div>`).join('') : `<p class="subtle">${state.user ? 'Your saved research will appear here after your first search.' : 'Sign in to save your research across visits.'}</p>`;
}
function renderStories() {
  $('#story-list').innerHTML = state.stories.length ? state.stories.map(item => `<article class="story-card"><span class="overline">NAME STORY / ${escapeHtml(item.name.toUpperCase())}</span><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.narrative)}</p><div class="story-card-bottom"><small>UPDATED ${formatDate(item.updatedAt)}</small><button class="minor-button" data-edit-story="${escapeHtml(item.id)}">Read & edit ↗</button></div></article>`).join('') : `<div class="no-items">${noItems('A blank page, full of possibility', 'Your collected stories will have a home here. Start with a name, or write from memory.')}</div>`;
}
function renderRecordings() {
  $('#recordings-list').innerHTML = state.recordings.length ? state.recordings.map(item => `<div class="stack-item"><div class="stack-monogram">♫</div><div class="stack-body"><strong>${escapeHtml(item.title)}</strong><small>${formatDate(item.createdAt)} · Audio stored in this browser only</small></div><button class="minor-button" data-download-recording="${escapeHtml(item.id)}">Download ↓</button><button class="minor-button danger" data-delete-recording="${escapeHtml(item.id)}" aria-label="Delete ${escapeHtml(item.title)}">×</button></div>`).join('') : `<p class="subtle">No voice memories recorded yet. Your audio stays on this device unless you download a copy.</p>`;
}
function showAuth(mode = 'login') {
  const register = mode === 'register';
  modal(`<span class="overline">YOUR PRIVATE ARCHIVE</span><h2>${register ? 'Create your space.' : 'Welcome back.'}</h2><p>${register ? 'Keep your research and stories saved in Cloudflare D1. Audio recordings remain on your device.' : 'Sign in to revisit the stories you are writing and the names you are exploring.'}</p><form id="auth-form"><div class="field"><label for="auth-email">EMAIL ADDRESS</label><input id="auth-email" name="email" type="email" autocomplete="email" required maxlength="254"></div><div class="field"><label for="auth-pass">PASSWORD ${register ? '(12 CHARACTERS MINIMUM)' : ''}</label><input id="auth-pass" name="password" type="password" autocomplete="${register ? 'new-password' : 'current-password'}" required minlength="${register ? 12 : 1}" maxlength="128"></div><div class="modal-actions"><button class="button primary" type="submit">${register ? 'Create archive' : 'Sign in'} ↗</button><button type="button" class="text-button" id="switch-auth">${register ? 'I have an account' : 'Create an account'}</button></div></form>`);
  $('#switch-auth').addEventListener('click', () => showAuth(register ? 'login' : 'register'));
  $('#auth-form').addEventListener('submit', async e => { e.preventDefault(); const submit = $('#auth-form button[type=submit]'); submit.disabled = true; try { const data = await api(`/auth/${register ? 'register' : 'login'}`, { method:'POST', body: JSON.stringify({ email:$('#auth-email').value, password:$('#auth-pass').value }) }); setAccount(data.user); await loadOverview(); closeModal(); toast('Your archive is ready.'); } catch (error) { handleError(error); submit.disabled = false; } });
}
function showAccount() {
  if (!state.user) { showAuth(); return; }
  modal(`<span class="overline">ARCHIVE ACCOUNT</span><h2>Your space.</h2><p>You are signed in as <strong>${escapeHtml(state.user.email)}</strong>.</p><p>Your stories and research sync to your account; audio files are stored only in this browser.</p><div class="modal-actions"><button id="logout-button" class="button primary">Sign out ↗</button></div>`);
  $('#logout-button').addEventListener('click', async () => { try { await api('/auth/logout', { method:'POST' }); } catch {} state.research = []; state.stories = []; state.recordings = []; setAccount(null); closeModal(); toast('Signed out.'); });
}
function safeExternalLink(url) { try { const parsed = new URL(url); return parsed.protocol === 'https:' ? parsed.href : '#'; } catch { return '#'; } }
function showResearch(data) {
  state.latest = data;
  navigate('explore');
  const sources = data.sources || [];
  const links = data.links || [];
  $('#research-result').innerHTML = `<article class="result-panel"><div class="result-head"><div><span class="overline">YOUR RESEARCH NOTES</span><h2>${escapeHtml(data.name)}</h2><p>${sources.length} source excerpts found · ${formatDate(data.createdAt || data.researchedAt || new Date())}</p></div><button class="button primary" id="create-from-research">Make a story →</button></div><div class="result-inner"><h3>What the references say</h3>${sources.length ? sources.map(s => `<div class="source-card"><div><small>${escapeHtml(s.provider.toUpperCase())}</small><strong>${escapeHtml(s.title)}</strong><p>${escapeHtml(s.excerpt)}</p></div><a href="${escapeHtml(safeExternalLink(s.url))}" target="_blank" rel="noopener noreferrer">View source ↗</a></div>`).join('') : '<p class="subtle">No verified text was returned from reference providers. Start with the links below and document primary evidence independently.</p>'}<div class="source-links">${links.map(link => `<a href="${escapeHtml(safeExternalLink(link.url))}" target="_blank" rel="noopener noreferrer">${escapeHtml(link.title)} ↗</a>`).join('')}</div><div class="research-notice">✣ ${escapeHtml(data.notice || 'Treat public references as research leads and verify against original records.')}</div></div></article>`;
  $('#create-from-research').addEventListener('click', () => showStoryEditor(null, data));
}
async function submitResearch(e) {
  e.preventDefault(); const name = $('#name-input').value.trim(); const button = $('#search-button'); button.disabled = true; button.textContent = 'Researching…';
  try {
    let result;
    if (state.user) { result = await api('/research', { method:'POST', body: JSON.stringify({ name }) }); await loadOverview(); }
    else { result = await api(`/research/lookup?name=${encodeURIComponent(name)}`); }
    showResearch(result);
    toast(state.user ? 'Research saved to your archive.' : 'Research complete. Sign in to save it.');
  } catch (error) { handleError(error); }
  finally { button.disabled = false; button.innerHTML = 'Explore name <span>↗</span>'; }
}
function showStoryEditor(story = null, research = null) {
  if (!state.user) { showAuth('register'); toast('Create a free account to save your stories.'); return; }
  const data = story || { name: research?.name || '', title: research ? `The story of ${research.name}` : '', narrative: '', notes: '' };
  const draft = research && (research.sources || []).length ? `Research notes for ${research.name}:\n\n${research.sources.map(s => `${s.provider}: ${s.excerpt}`).join('\n\n')}\n\nAdd verified sources and family memories below.` : '';
  modal(`<span class="overline">STORY STUDIO / ${story ? 'EDIT' : 'NEW'}</span><h2>${story ? 'Shape the story.' : 'Begin your story.'}</h2><p>Write from what you know. Separate documented evidence from family tradition.</p><form id="story-form"><div class="field"><label for="story-name">NAME BEHIND THE STORY</label><input id="story-name" maxlength="80" required ${story ? 'readonly' : ''} value="${escapeHtml(data.name)}" placeholder="A name to remember"></div><div class="field"><label for="story-title">STORY TITLE</label><input id="story-title" maxlength="140" required value="${escapeHtml(data.title)}" placeholder="The story of..."></div><div class="field"><label for="story-narrative">THE NARRATIVE</label><textarea id="story-narrative" class="large" maxlength="30000" placeholder="What do you know? Who told you? Where did the story begin?">${escapeHtml(data.narrative || draft)}</textarea></div><div class="field"><label for="story-notes">ADDITIONAL FAMILY NOTES</label><textarea id="story-notes" maxlength="10000" placeholder="People, places, dates, and what you still want to verify...">${escapeHtml(data.notes)}</textarea></div><div class="modal-actions"><button type="submit" class="button primary">${story ? 'Save changes' : 'Save story'} ↗</button>${story ? '<button type="button" id="export-story" class="minor-button">Download text ↓</button><button type="button" id="delete-story" class="minor-button danger">Delete</button>' : ''}</div></form>`);
  $('#story-form').addEventListener('submit', async e => { e.preventDefault(); const save = $('#story-form button[type=submit]'); save.disabled = true; try { const payload = { name: $('#story-name').value.trim(), title: $('#story-title').value.trim(), narrative: $('#story-narrative').value.trim(), notes: $('#story-notes').value.trim() }; if (research?.id && !story) payload.researchId = research.id; await api(story ? `/stories/${story.id}` : '/stories', { method: story ? 'PATCH' : 'POST', body: JSON.stringify(payload) }); await loadOverview(); closeModal(); navigate('stories'); toast('Story saved.'); } catch (error) { handleError(error); save.disabled = false; } });
  if (story) {
    $('#export-story').addEventListener('click', () => download(new Blob([`${$('#story-title').value}\n\n${$('#story-narrative').value}\n\nNotes\n${$('#story-notes').value}`], { type:'text/plain' }), `${slug(story.title)}.txt`));
    $('#delete-story').addEventListener('click', async () => { if (!confirm('Delete this story permanently?')) return; try { await api(`/stories/${story.id}`, { method:'DELETE' }); await loadOverview(); closeModal(); toast('Story deleted.'); } catch (error) { handleError(error); } });
  }
}
function slug(text) { return String(text).toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-|-$/g, '').slice(0,65) || 'origin-memory'; }
function download(blob, name) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000); }
function audioDb() { return new Promise((resolve, reject) => { const request = indexedDB.open('origin-local-audio', 1); request.onupgradeneeded = () => request.result.createObjectStore('audio'); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); }); }
async function storeAudio(id, blob) { const db = await audioDb(); return new Promise((resolve, reject) => { const tx = db.transaction('audio','readwrite'); tx.objectStore('audio').put(blob, id); tx.oncomplete = () => { db.close(); resolve(); }; tx.onerror = () => { db.close(); reject(tx.error); }; }); }
async function retrieveAudio(id) { const db = await audioDb(); return new Promise((resolve, reject) => { const tx = db.transaction('audio','readonly'); const request = tx.objectStore('audio').get(id); request.onsuccess = () => { db.close(); resolve(request.result); }; request.onerror = () => { db.close(); reject(request.error); }; }); }
async function removeAudio(id) { const db = await audioDb(); return new Promise((resolve, reject) => { const tx = db.transaction('audio','readwrite'); tx.objectStore('audio').delete(id); tx.oncomplete = () => { db.close(); resolve(); }; tx.onerror = () => { db.close(); reject(tx.error); }; }); }
function showTime(seconds) { const n = Math.floor(seconds); return `${String(Math.floor(n / 60)).padStart(2,'0')}:${String(n % 60).padStart(2,'0')}`; }
async function toggleRecording() {
  if (!state.user) { showAuth('register'); toast('Sign in to catalog recordings.'); return; }
  if (state.mediaRecorder?.state === 'recording') { state.mediaRecorder.stop(); return; }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !window.indexedDB) { toast('This browser does not support local recording.'); return; }
  const title = $('#record-title').value.trim(); if (!title) { $('#record-title').focus(); toast('Give your recording a title first.'); return; }
  try {
    state.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(state.audioStream);
    state.audioChunks = [];
    recorder.ondataavailable = e => { if (e.data.size) state.audioChunks.push(e.data); };
    recorder.onerror = () => toast('Recording error. Try again.');
    recorder.onstop = async () => {
      clearInterval(state.recordingTimer); $('#record-button').classList.remove('recording'); $('#record-state').textContent = 'SAVING LOCAL AUDIO';
      state.audioStream?.getTracks().forEach(track => track.stop());
      const blob = new Blob(state.audioChunks, { type: recorder.mimeType || 'audio/webm' });
      if (blob.size === 0) { toast('No audio captured.'); $('#record-state').textContent = 'READY TO RECORD'; return; }
      let item;
      try { item = await api('/recordings', { method:'POST', body: JSON.stringify({ title }) }); await storeAudio(item.id, blob); await loadOverview(); toast('Recording saved to this browser. Download a backup.'); $('#record-title').value = ''; }
      catch (error) { download(blob, `${slug(title)}.webm`); toast('Unable to store locally. An audio download was started as a backup.'); if (item) { try { await api(`/recordings/${item.id}`, { method:'DELETE' }); } catch {} } handleError(error); }
      finally { $('#record-state').textContent = 'READY TO RECORD'; $('#record-clock').textContent = '00:00'; state.mediaRecorder = null; }
    };
    state.mediaRecorder = recorder; state.recordingStarted = Date.now(); recorder.start(1000);
    $('#record-button').classList.add('recording'); $('#record-state').textContent = 'RECORDING · TAP TO STOP';
    state.recordingTimer = setInterval(() => $('#record-clock').textContent = showTime((Date.now() - state.recordingStarted)/1000), 300);
  } catch (error) { state.audioStream?.getTracks().forEach(track => track.stop()); handleError(error); }
}
async function downloadRecording(id) { try { const blob = await retrieveAudio(id); if (!blob) { toast('Audio was not found in this browser. It may be stored on another device or was cleared.'); return; } const title = state.recordings.find(r => r.id === id)?.title || 'voice-memory'; download(blob, `${slug(title)}.${blob.type.includes('mp4') ? 'm4a' : 'webm'}`); } catch (error) { handleError(error); } }
async function deleteRecording(id) { if (!confirm('Delete this recording’s catalog entry and local audio?')) return; try { await api(`/recordings/${id}`, { method:'DELETE' }); await removeAudio(id); await loadOverview(); toast('Recording deleted.'); } catch (error) { handleError(error); } }
$('#nav').addEventListener('click', e => { const link = e.target.closest('[data-page]'); if (link) { e.preventDefault(); navigate(link.dataset.page); } });
document.addEventListener('click', e => { const nav = e.target.closest('[data-navigate]'); if (nav) navigate(nav.dataset.navigate); const auth = e.target.closest('[data-open-auth]'); if (auth) showAuth(auth.dataset.openAuth); const research = e.target.closest('[data-research-id]'); if (research) { const item = state.research.find(r => r.id === research.dataset.researchId); if (item) showResearch(item); } const story = e.target.closest('[data-edit-story]'); if (story) { const item = state.stories.find(s => s.id === story.dataset.editStory); if (item) showStoryEditor(item); } const down = e.target.closest('[data-download-recording]'); if (down) downloadRecording(down.dataset.downloadRecording); const del = e.target.closest('[data-delete-recording]'); if (del) deleteRecording(del.dataset.deleteRecording); });
$('#search-form').addEventListener('submit', submitResearch);
$('#new-story-button').addEventListener('click', () => showStoryEditor());
$('#record-button').addEventListener('click', toggleRecording);
$('#account-button').addEventListener('click', showAccount);
$('#modal-close').addEventListener('click', closeModal);
$('#modal-backdrop').addEventListener('click', e => { if (e.target.id === 'modal-backdrop') closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#modal-backdrop').hidden) closeModal(); });
$('#menu-toggle').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
window.addEventListener('hashchange', () => navigate(location.hash.slice(1)));
navigate(location.hash.slice(1) || 'home');
hydrate();
