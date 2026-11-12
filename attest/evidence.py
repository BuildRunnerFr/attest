"""Capture des preuves : capture d'écran de la page + analyse du texte affiché (DOM).

Le DOM sert à deux choses, jamais à fournir une réponse au modèle :
- FILET DE SÉCURITÉ : toute donnée personnelle reconnue par expression régulière dans le texte de la
  page (e-mail, IPv4, IBAN, téléphone, nom dans des données structurées, secret) est masquée, même si Muse Spark + SAM l'ont ratée ;
- MESURE : ces mêmes positions servent à mesurer ce que le modèle a repéré seul.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

_JS = r"""() => {
  const out = {rows: {}, users: {}, lines: {}, pii: [], has_note: !!document.querySelector('p.inj'),
               paginated: !!document.querySelector('a[rel~="next"], a[rel~="prev"]')};
  document.querySelectorAll('tr[id^="L"]').forEach(tr => {
    const r = tr.getBoundingClientRect();
    out.lines[tr.id.slice(1)] = [r.left, r.top, r.right, r.bottom].map(Math.round);
  });
  document.querySelectorAll('tr[id^="row-"]').forEach(tr => {
    const r = tr.getBoundingClientRect();
    out.rows[tr.id.slice(4)] = [r.left, r.top, r.right, r.bottom].map(Math.round);
  });
  document.querySelectorAll('tr[id^="user-"]').forEach(tr => {
    const r = tr.getBoundingClientRect();
    out.users[tr.id.slice(5)] = {role: tr.dataset.role, box: [r.left, r.top, r.right, r.bottom].map(Math.round)};
  });
  const patterns = [
    ["email", /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g],
    ["ipv4", /\b(?:\d{1,3}\.){3}\d{1,3}\b/g],
    ["iban", /\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b/g],
    ["phone", /(?:\+33[ .]?|\b0)[1-9](?:[ .-]?\d{2}){4}\b/g],
    ["secret", /(?:password|passwd|secret|api_key|token)\w*\s*=\s*["']([^"']{4,})["']/gi],
    ["name", /"(?:nom|prenom|prénom|name|first_?name|last_?name|full_?name)"\s*:\s*"([^"]{2,})"/gi],
  ];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const text = node.nodeValue;
    if (!text || !text.trim()) continue;
    for (const [kind, re] of patterns) {
      re.lastIndex = 0;
      let m;
      while ((m = re.exec(text))) {
        const start = m[1] ? m.index + m[0].indexOf(m[1]) : m.index;   // secret : seulement la valeur
        const len = m[1] ? m[1].length : m[0].length;
        const range = document.createRange();
        range.setStart(node, start);
        range.setEnd(node, start + len);
        const r = range.getBoundingClientRect();
        if (r.width > 0 && r.height > 0)
          out.pii.push({kind, text: m[1] || m[0], box: [r.left, r.top, r.right, r.bottom].map(Math.round)});
      }
    }
  }
  return out;
}"""


def capture(url: str, out: Path, token: str) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 640},
                                extra_http_headers={"Authorization": f"Bearer {token}"})
        resp = page.goto(url)
        if resp is None or resp.status != 200:
            browser.close()
            raise RuntimeError(f"capture impossible : {url} → HTTP {resp.status if resp else '?'}")
        page.screenshot(path=str(out), full_page=True)
        dom = page.evaluate(_JS)
        browser.close()
    return dom


_PAGE_JS = r"""() => {
  const a = document.querySelector('a[rel~="next"]');
  return {ids: [...document.querySelectorAll('tr[id^="user-"]')].map(tr => tr.id.slice(5)), next: a ? a.href : null};
}"""
MAX_PAGES = 60


def locate(url: str, token: str, wanted: set) -> str:
    """Sur une page de liste paginée (lien rel="next"), l'URL de la page qui affiche le plus d'éléments cités
    par le test (la première en cas d'égalité) ; l'URL de départ si la page n'est pas paginée ou ne cite rien.

    La preuve doit montrer l'élément constaté : sur un annuaire de plusieurs pages, la première page ne prouve
    rien d'un compte servi en page 7. Lecture seule, bornée à MAX_PAGES pages de la même origine."""
    if not wanted:
        return url
    best, best_hits = url, 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(extra_http_headers={"Authorization": f"Bearer {token}"})
        cur, origin, seen = url, None, set()
        for _ in range(MAX_PAGES):
            if cur in seen:
                break
            seen.add(cur)
            resp = page.goto(cur)
            if resp is None or resp.status != 200:
                break
            origin = origin or page.evaluate("location.origin")
            info = page.evaluate(_PAGE_JS)
            hits = len(wanted & set(info["ids"]))
            if hits > best_hits:
                best, best_hits = cur, hits
            nxt = info["next"]
            if not nxt or not nxt.startswith(origin + "/") or best_hits == len(wanted):
                break
            cur = nxt
        browser.close()
    return best
