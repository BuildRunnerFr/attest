"""Capture des preuves : capture d'écran de la page + position réelle des éléments (DOM).

Les positions DOM servent de vérité terrain pour MESURER la précision de Muse Spark + SAM
(et pour le mode mock). Elles ne sont jamais données au modèle.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

_JS = """() => {
  const out = {rows: {}, users: {}, pii: []};
  document.querySelectorAll('tr[id^="row-"]').forEach(tr => {
    const r = tr.getBoundingClientRect();
    out.rows[tr.id.slice(4)] = [r.left, r.top, r.right, r.bottom].map(Math.round);
  });
  document.querySelectorAll('tr[id^="user-"]').forEach(tr => {
    const r = tr.getBoundingClientRect();
    out.users[tr.id.slice(5)] = {role: tr.dataset.role, box: [r.left, r.top, r.right, r.bottom].map(Math.round)};
  });
  const piiRe = /@|^\\d{1,3}(\\.\\d{1,3}){3}$/;
  document.querySelectorAll('td').forEach(td => {
    if (piiRe.test(td.innerText.trim())) {
      const range = document.createRange(); range.selectNodeContents(td);
      const r = range.getBoundingClientRect();
      out.pii.push({text: td.innerText.trim(), box: [r.left, r.top, r.right, r.bottom].map(Math.round)});
    }
  });
  return out;
}"""


def capture(url: str, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 640})
        page.goto(url)
        page.screenshot(path=str(out), full_page=True)
        dom = page.evaluate(_JS)
        browser.close()
    return dom
