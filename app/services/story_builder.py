from typing import Dict, Any, Tuple


def compose_story_from_results(name: str, results: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Compose a narrative paragraph and gather sources from scraper results.
    Returns (narrative, sources_dict)
    """
    parts = []
    sources: Dict[str, Any] = {}

    ety = results.get("etymonline") or {}
    if isinstance(ety, dict):
        snippet = ety.get("snippet") or ety.get("text") or ety.get("summary")
    else:
        snippet = results.get("etymonline_snippet")
    if snippet:
        parts.append(f"According to Etymonline, {snippet}")
        sources["etymonline"] = ety or snippet

    wiki = results.get("wikipedia") or {}
    if isinstance(wiki, dict):
        wint = wiki.get("intro") or wiki.get("summary")
    else:
        wint = results.get("wikipedia_intro")
    if wint:
        parts.append(f"Wikipedia notes: {wint}")
        sources["wikipedia"] = wiki or wint

    btn = results.get("behindthename") or {}
    if isinstance(btn, dict):
        bsum = btn.get("summary") or btn.get("meaning")
    else:
        bsum = results.get("behindthename_snippet")
    if bsum:
        parts.append(f"Behind the Name adds: {bsum}")
        sources["behindthename"] = btn or bsum

    wikt = results.get("wiktionary") or {}
    if isinstance(wikt, dict):
        wsum = wikt.get("summary")
    else:
        wsum = None
    if wsum:
        parts.append(f"Wiktionary etymology: {wsum}")
        sources["wiktionary"] = wikt or wsum

    sdb = results.get("surnamedb") or {}
    if isinstance(sdb, dict):
        sdb_sum = sdb.get("summary")
    else:
        sdb_sum = None
    if sdb_sum:
        parts.append(f"SurnameDB records: {sdb_sum}")
        sources["surnamedb"] = sdb or sdb_sum

    fb = results.get("forebears") or {}
    if isinstance(fb, dict):
        fb_sum = fb.get("summary")
    else:
        fb_sum = None
    if fb_sum:
        parts.append(f"Forebears distribution insight: {fb_sum}")
        sources["forebears"] = fb or fb_sum

    if not parts:
        parts.append(f"A story about the name {name} will appear here once research is available.")

    narrative = "\n\n".join(parts)
    return narrative, sources
