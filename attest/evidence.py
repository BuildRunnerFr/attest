"""Capture des preuves : capture d'écran de la page + analyse du texte affiché (DOM).

Le DOM sert à deux choses, jamais à fournir une réponse au modèle :
- FILET DE SÉCURITÉ : toute donnée personnelle reconnue par expression régulière dans le texte de la
  page (e-mail, IPv4, IBAN, téléphone) est masquée, même si Muse Spark + SAM l'ont ratée ;
- MESURE : ces mêmes positions servent à mesurer ce que le modèle a repéré seul.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

_JS = r"""() => {
  const out = {rows: {}, users: {}, pii: [], has_note: !!document.querySelector('p.inj')};
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
        const range = document.createRange();
        range.setStart(node, m.index);
        range.setEnd(node, m.index + m[0].length);
        const r = range.getBoundingClientRect();
        if (r.width > 0 && r.height > 0)
          out.pii.push({kind, text: m[0], box: [r.left, r.top, r.right, r.bottom].map(Math.round)});
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
