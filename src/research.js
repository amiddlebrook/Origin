export function cleanName(value) {
  if (typeof value !== 'string') throw new Error('Enter a name to research.');
  const name = value.trim().replace(/\s+/g, ' ');
  if (name.length < 2 || name.length > 80 || !/^[\p{L}\p{M}\p{N} .,'’\-]+$/u.test(name)) {
    throw new Error('Use a name between 2 and 80 characters (letters, spaces, apostrophes or hyphens).');
  }
  return name;
}

export function researchLinks(name) {
  const q = encodeURIComponent(name);
  return [
    { title: 'Wiktionary', url: `https://en.wiktionary.org/w/index.php?search=${q}`, description: 'Word origins and language usage' },
    { title: 'Wikipedia', url: `https://en.wikipedia.org/w/index.php?search=${q}`, description: 'Historical and biographical context' },
    { title: 'FamilySearch', url: `https://www.familysearch.org/search/`, description: 'Genealogical records and family trees' },
    { title: 'Forebears', url: `https://forebears.io/`, description: 'Surname distribution research' }
  ];
}

export function composeStory(name, sources, notes = '') {
  const n = cleanName(name);
  const verified = Array.isArray(sources) ? sources.filter(s => s && s.excerpt) : [];
  const intro = `Every name carries a trail of language, geography and individual lives. This is a research notebook for “${n}” — a starting point, not a verified family lineage.`;
  const evidence = verified.map(s => `${s.provider} — ${s.excerpt}`).join('\n\n');
  const context = String(notes || '').trim();
  return [intro, evidence ? `Sources to investigate\n\n${evidence}` : 'No source excerpts were available yet. Follow the research links and add evidence before making claims about this name.', context ? `Family context\n\n${context}` : '', 'Next steps\n\nCompare primary records, dates and locations. Shared surnames do not establish a family relationship.'].filter(Boolean).join('\n\n');
}

async function lookupProvider(provider, url, fallbackUrl, signal) {
  try {
    const response = await fetch(url, {
      headers: { Accept: 'application/json', 'User-Agent': 'OriginResearch/1.0 (personal historical research; contact via GitHub amiddlebrook/Origin)' },
      signal
    });
    if (!response.ok) return [];
    const data = await response.json();
    const pages = Array.isArray(data.pages) ? data.pages : [];
    return pages.slice(0, 3).filter(p => p.title && (p.excerpt || p.description)).map(p => ({
      provider,
      title: String(p.title).slice(0, 180),
      excerpt: String((p.excerpt || p.description || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ')).slice(0, 500),
      url: `https://${provider === 'Wiktionary' ? 'en.wiktionary.org' : 'en.wikipedia.org'}/wiki/${encodeURIComponent(String(p.key || p.title).replace(/ /g, '_'))}`
    }));
  } catch { /* External providers can block automated requests or time out. */ }
  return [];
}

export async function lookupName(rawName) {
  const name = cleanName(rawName);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4500);
  try {
    const queries = [
      ['Wiktionary', `https://en.wiktionary.org/w/rest.php/v1/search/page?q=${encodeURIComponent(name)}&limit=3`],
      ['Wikipedia', `https://en.wikipedia.org/w/rest.php/v1/search/page?q=${encodeURIComponent(name + ' surname')}&limit=3`]
    ];
    const found = await Promise.all(queries.map(([p, url]) => lookupProvider(p, url, '', controller.signal)));
    const sources = found.flat();
    return { name, sources, links: researchLinks(name), researchedAt: new Date().toISOString(),
      notice: sources.length ? 'Reference excerpts are leads, not proof of ancestry or name etymology.' : 'Reference providers did not return verified excerpts. Use the source links below to continue manually.' };
  } finally { clearTimeout(timeout); }
}
