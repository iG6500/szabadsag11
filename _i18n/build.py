#!/usr/bin/env python3
"""Builds the English (en/) and German (de/) versions of the listing page.

The pages are single-file bundles: the visible page is an HTML string stored as
JSON in <script type="__bundler/template">. This script
  1. applies the Hungarian content fixes to index.html and mobil.html,
  2. adds the HU · EN · DE language switcher,
  3. translates the template into en/ and de/ copies.

Usage (from the repository root):  python3 _i18n/build.py
Re-run it after editing the Hungarian pages so the translations stay in sync.
The Hungarian fixes and the switcher are idempotent.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from strings import HU_FIXES, T, RAW, HEAD  # noqa: E402

BASE_URL = "https://ig6500.github.io/szabadsag11/"
LANGS = ["hu", "en", "de"]
TPL_RE = re.compile(r'(<script type="__bundler/template">)([\s\S]*?)(</script>)')
HU_CHARS = re.compile(r"[áéíóőúűÁÉÍÓŐÚŰ]")  # not ö/ü: German has them too
# Proper names that keep their Hungarian spelling in every language.
KEEP = ["Süni Plus", "Türr", "István", "Petőfi", "Szentháromság tér", "Sugovica", "Baja",
        "Gorotyák", "Jakarta"]


def get_template(doc):
    m = TPL_RE.search(doc)
    return json.loads(m.group(2))


def put_template(doc, tpl):
    enc = json.dumps(tpl, ensure_ascii=False).replace("</", "<\\u002F")
    return TPL_RE.sub(lambda m: m.group(1) + enc + m.group(3), doc, count=1)


# ---------------------------------------------------------------- switcher
SW_START, SW_END = "<!--lang-switch-->", "<!--/lang-switch-->"


def switcher(lang, mobile):
    up = "" if lang == "hu" else "../"
    hrefs = {"hu": up or "./", "en": up + "en/", "de": up + "de/"}
    if lang == "en":
        hrefs["en"] = "./"
    if lang == "de":
        hrefs["de"] = "./"
    size = "12px" if mobile else "13px"
    links = []
    for code in LANGS:
        cur = code == lang
        style = (f"padding:4px 6px; border-radius:4px; font-size:{size}; font-weight:700; "
                 f"letter-spacing:.04em; color:#fff; opacity:{'1' if cur else '.7'};"
                 + (" background:rgba(255,255,255,.18);" if cur else ""))
        attr = ' aria-current="page"' if cur else ""
        links.append(f'<a href="{hrefs[code]}" hreflang="{code}" lang="{code}"{attr} '
                     f'style="{style}">{code.upper()}</a>')
    label = {"hu": "Nyelv", "en": "Language", "de": "Sprache"}[lang]
    return (f'{SW_START}<nav aria-label="{label}" style="display:flex; align-items:center; gap:2px;">'
            + "".join(links) + f"</nav>{SW_END}")


def add_switcher(tpl, lang, mobile):
    tpl = re.sub(re.escape(SW_START) + r"[\s\S]*?" + re.escape(SW_END), "", tpl)
    sw = switcher(lang, mobile)
    if mobile:
        # Header is flex/space-between; margin-left:auto parks the switcher
        # right next to the menu button.
        sw = sw.replace('style="display:flex; align-items:center; gap:2px;"',
                        'style="margin-left:auto; margin-right:10px; display:flex; align-items:center; gap:2px;"', 1)
        tpl, n = re.subn(r'<button type="button" aria-label="(Menü|Menu)"',
                         lambda m: sw + m.group(0), tpl, count=1)
        assert n == 1, "mobile header slot not found"
    else:
        old = '<div style="display:flex; justify-content:flex-end;">'
        new = '<div style="display:flex; justify-content:flex-end; align-items:center; gap:18px;">'
        tpl = tpl.replace(old, new, 1)
        i = tpl.find(new)
        assert i >= 0, "desktop header slot not found"
        j = i + len(new)
        tpl = tpl[:j] + sw + tpl[j:]
    return tpl


# ---------------------------------------------------------------- translate
def translate(tpl, lang, li):
    pairs = sorted(T, key=lambda p: -len(p[0]))
    unused = []
    for row in pairs:
        hu, tr = row[0], row[li]
        n0 = tpl
        tpl = re.sub(r">(\s*)" + re.escape(hu) + r"(\s*)<",
                     lambda m: ">" + m.group(1) + tr + m.group(2) + "<", tpl)
        tpl = tpl.replace('="' + hu + '"', '="' + tr + '"')
        tpl = tpl.replace("'" + hu + "'", "'" + tr + "'")
        if tpl == n0:
            unused.append(hu)
    for row in RAW:
        hu, tr = row[0], row[li]
        tpl = tpl.replace(hu, tr)
    tpl = tpl.replace('<html lang="hu">', f'<html lang="{lang}">')
    # assets live one folder up
    tpl = re.sub(r"""(["'(])kepek/""", r"\1../kepek/", tpl)
    return tpl, unused


def leftovers(tpl):
    body = re.sub(r"<style[\s\S]*?</style>", "", tpl)
    found = set()
    for chunk in re.findall(r">([^<>]+)<", body) + re.findall(r'="([^"]+)"', body) \
            + re.findall(r"'([^'\n]+)'", body) + re.findall(r"/\^?([^/\n]{2,40})/i?", body):
        s = chunk
        for k in KEEP:
            s = s.replace(k, "")
        if HU_CHARS.search(s) and "//" not in s:
            found.add(chunk.strip()[:120])
    return sorted(found)


def outer(doc, lang, page):
    url = BASE_URL if lang == "hu" else BASE_URL + lang + "/"
    alts = "".join(
        f'\n  <link rel="alternate" hreflang="{c}" href="{BASE_URL if c == "hu" else BASE_URL + c + "/"}">'
        for c in LANGS) + f'\n  <link rel="alternate" hreflang="x-default" href="{BASE_URL}">'
    doc = re.sub(r'\n  <link rel="alternate" hreflang="[^"]+" href="[^"]+">', "", doc)
    doc = doc.replace("\n  <title>", alts + "\n  <title>", 1)
    if lang == "hu":
        return doc
    h = HEAD[lang]
    doc = doc.replace("<html>", f'<html lang="{lang}">', 1)
    doc = re.sub(r"<title>[^<]*</title>", f"<title>{h['title']}</title>", doc, count=1)
    doc = re.sub(r'(<meta name="description" content=")[^"]*', r"\g<1>" + h["desc"], doc, count=1)
    doc = re.sub(r'(<meta property="og:title" content=")[^"]*', r"\g<1>" + h["title"], doc, count=1)
    doc = re.sub(r'(<meta property="og:description" content=")[^"]*', r"\g<1>" + h["desc"], doc, count=1)
    doc = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + url, doc, count=1)
    doc = re.sub(r'(<meta property="og:locale" content=")[^"]*', r"\g<1>" + h["locale"], doc, count=1)
    doc = re.sub(r'(<meta property="og:image:alt" content=")[^"]*', r"\g<1>" + h["imgalt"], doc, count=1)
    doc = doc.replace('<div id="__bundler_placeholder">Eladó lakás</div>',
                      f'<div id="__bundler_placeholder">{h["placeholder"]}</div>')
    return doc


def main():
    ok = True
    for page in ["index.html", "mobil.html"]:
        mobile = page == "mobil.html"
        src = ROOT / page
        doc = src.read_text(encoding="utf-8")
        tpl = get_template(doc)

        # 1. Hungarian content fixes (idempotent)
        for item in HU_FIXES:
            old, new = item[0], item[1]
            if new not in tpl:
                tpl = tpl.replace(old, new)
        # Service-charge row, inserted before the utilities row
        if ">Közös költség<" not in tpl:
            m = re.search(r'(<div style="[^"]*"><dt style="[^"]*">)Környezet(</dt><dd style="[^"]*">)'
                          r'[^<]*(</dd></div>)', tpl)
            row = m.group(1) + "Közös költség" + m.group(2) + "10 000 Ft / hó" + m.group(3)
            k = tpl.rfind("<div", 0, tpl.find(">Rezsi<"))
            tpl = tpl[:k] + row + tpl[k:]

        hu_tpl = add_switcher(tpl, "hu", mobile)
        doc_hu = outer(put_template(doc, hu_tpl), "hu", page)
        src.write_text(doc_hu, encoding="utf-8")

        for li, lang in enumerate(["en", "de"], start=1):
            t, unused = translate(tpl, lang, li)
            t = add_switcher(t, lang, mobile)
            left = leftovers(t)
            out = ROOT / lang / page
            out.parent.mkdir(exist_ok=True)
            out.write_text(outer(put_template(doc, t), lang, page), encoding="utf-8")
            print(f"{lang}/{page}: {len(left)} untranslated")
            for x in left:
                print("   ", x)
                ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
