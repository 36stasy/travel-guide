#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Собирает сайт-гайд из отправленных карточек: docs/index.html и страницу на каждое место.

Сайт лежит в папке docs/ и публикуется через GitHub Pages — открывается с телефона
по ссылке, ноутбук не нужен. Фотографии не копируются, а подтягиваются по ссылке,
поэтому сайт почти ничего не весит.
"""

import html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards"
DOCS = ROOT / "docs"
LOG = ROOT / "data" / "log.json"
PLACES = ROOT / "data" / "places.json"

REGION_RU = {
    "islands": "Острова",
    "asia_se": "Юго-Восточная Азия",
    "asia_himalaya": "Азия и Гималаи",
    "middle_east": "Ближний Восток",
    "africa": "Африка",
    "europe": "Европа",
    "europe_north": "Северная Европа и Британия",
    "americas_south": "Южная Америка",
    "americas_north": "Северная Америка",
    "oceania": "Австралия и Океания",
}

CSS = """
:root{
  --bg:#0f1113; --bg-soft:#171a1d; --card:#1c2024; --line:#2a2f35;
  --ink:#f2efe9; --ink-dim:#a8a49c; --accent:#d8a05a; --accent-soft:#3a2c1c;
  --radius:16px; --maxw:1080px;
  --serif:"Georgia","Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
  line-height:1.65;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 16px}
header.top{padding:48px 0 28px;border-bottom:1px solid var(--line);margin-bottom:28px}
header.top h1{font-family:var(--serif);font-size:clamp(28px,6vw,44px);margin:0 0 8px;
  letter-spacing:-.02em;font-weight:400}
header.top p{color:var(--ink-dim);margin:0;font-size:15px}
.stats{display:flex;gap:22px;flex-wrap:wrap;margin-top:20px}
.stat b{display:block;font-family:var(--serif);font-size:26px;color:var(--accent);font-weight:400}
.stat span{font-size:12px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:.08em}
.tools{display:flex;gap:10px;flex-wrap:wrap;margin:26px 0 18px;align-items:center}
#q{flex:1 1 220px;min-width:180px;background:var(--bg-soft);border:1px solid var(--line);
  color:var(--ink);padding:11px 14px;border-radius:999px;font-size:15px;font-family:inherit}
#q:focus{outline:none;border-color:var(--accent)}
.chip{background:transparent;border:1px solid var(--line);color:var(--ink-dim);
  padding:7px 14px;border-radius:999px;font-size:13px;cursor:pointer;font-family:inherit}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.chip.on{background:var(--accent-soft);border-color:var(--accent);color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;
  padding-bottom:56px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;display:flex;flex-direction:column;transition:transform .18s,border-color .18s}
.card:hover{transform:translateY(-3px);border-color:var(--accent)}
.card .ph{aspect-ratio:4/3;background:var(--bg-soft);overflow:hidden}
.card .ph img{width:100%;height:100%;object-fit:cover;display:block}
.card .body{padding:14px 16px 18px}
.card h3{margin:0 0 3px;font-family:var(--serif);font-size:19px;font-weight:400}
.card .country{font-size:12px;color:var(--accent);text-transform:uppercase;letter-spacing:.08em}
.card .lead{margin:9px 0 0;font-size:14px;color:var(--ink-dim)}
.empty{color:var(--ink-dim);padding:40px 0;text-align:center}
footer{border-top:1px solid var(--line);padding:26px 0 44px;color:var(--ink-dim);font-size:13px}

/* страница места */
.hero{margin:26px 0 8px}
.hero .country{color:var(--accent);text-transform:uppercase;letter-spacing:.1em;font-size:12px}
.hero h1{font-family:var(--serif);font-size:clamp(30px,7vw,52px);margin:6px 0 10px;
  font-weight:400;letter-spacing:-.02em}
.hero .status{display:inline-block;border:1px solid var(--accent);color:var(--accent);
  padding:4px 12px;border-radius:999px;font-size:12px}
.hero .lead{font-family:var(--serif);font-size:clamp(17px,3.4vw,21px);color:var(--ink);
  margin:16px 0 0;font-style:italic}
.gal{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));
  margin:26px 0}
.gal figure{margin:0;border-radius:12px;overflow:hidden;background:var(--bg-soft)}
.gal img{width:100%;display:block;cursor:zoom-in;transition:opacity .2s}
.gal img:hover{opacity:.9}
.gal figcaption{font-size:12px;color:var(--ink-dim);padding:7px 10px 9px}
.gal .credit{opacity:.6;font-size:11px}
section.blk{margin:34px 0}
section.blk h2{font-family:var(--serif);font-size:15px;text-transform:uppercase;
  letter-spacing:.14em;color:var(--accent);font-weight:400;margin:0 0 14px;
  padding-bottom:9px;border-bottom:1px solid var(--line)}
section.blk p{margin:0 0 14px}
.item{background:var(--bg-soft);border-left:2px solid var(--accent);border-radius:0 10px 10px 0;
  padding:13px 16px;margin-bottom:11px}
.item b{display:block;margin-bottom:4px}
.item .tip{color:var(--ink-dim);font-size:14px;font-style:italic;margin-top:6px}
ul.clean{list-style:none;padding:0;margin:0}
ul.clean li{padding:9px 0 9px 22px;position:relative;border-bottom:1px solid var(--line)}
ul.clean li:last-child{border-bottom:none}
ul.clean li:before{content:"◆";position:absolute;left:0;color:var(--accent);font-size:11px;top:12px}
dl.facts{margin:0;display:grid;gap:10px}
dl.facts div{background:var(--bg-soft);padding:12px 15px;border-radius:10px}
dl.facts dt{color:var(--accent);font-size:12px;text-transform:uppercase;letter-spacing:.07em}
dl.facts dd{margin:4px 0 0}
.back{display:inline-block;margin:26px 0 0;color:var(--ink-dim);font-size:14px}
.cols{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));
  margin:24px 0 4px}
.col{background:linear-gradient(135deg,var(--accent-soft),var(--card));border:1px solid var(--accent);
  border-radius:var(--radius);padding:16px 18px;display:block;transition:transform .18s}
.col:hover{transform:translateY(-3px);text-decoration:none}
.col b{display:block;font-family:var(--serif);font-size:19px;color:var(--ink);font-weight:400;
  margin-bottom:5px}
.col span{font-size:13px;color:var(--ink-dim)}
.toc{background:var(--bg-soft);border:1px solid var(--line);border-radius:var(--radius);
  padding:18px 22px;margin:26px 0}
.toc h2{font-family:var(--serif);font-size:13px;text-transform:uppercase;letter-spacing:.14em;
  color:var(--accent);font-weight:400;margin:0 0 10px}
.toc ol{margin:0;padding-left:20px;columns:2;column-gap:28px}
.toc li{padding:4px 0;break-inside:avoid}
.toc a{color:var(--ink)}
p.introp{font-family:var(--serif);font-size:17px;margin:0 0 16px}
@media(max-width:600px){.toc ol{columns:1}}
#lb{position:fixed;inset:0;background:rgba(8,9,10,.96);display:none;place-items:center;
  z-index:99;padding:18px;cursor:zoom-out}
#lb.on{display:grid}
#lb img{max-width:100%;max-height:88vh;border-radius:10px}
#lb .cap{color:var(--ink-dim);font-size:13px;text-align:center;margin-top:12px}
@media(max-width:600px){header.top{padding:30px 0 20px}.gal{grid-template-columns:1fr}}
"""

LIGHTBOX_JS = """
const lb=document.getElementById('lb');
if(lb){
  document.querySelectorAll('.gal img').forEach(img=>{
    img.addEventListener('click',()=>{
      lb.querySelector('img').src=img.dataset.full||img.src;
      lb.querySelector('.cap').textContent=img.alt||'';
      lb.classList.add('on');
    });
  });
  lb.addEventListener('click',()=>lb.classList.remove('on'));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')lb.classList.remove('on')});
}
"""

FILTER_JS = """
const q=document.getElementById('q'),cards=[...document.querySelectorAll('.card')],
      chips=[...document.querySelectorAll('.chip')];
let region='all';
function apply(){
  const t=(q?q.value:'').trim().toLowerCase();
  let shown=0;
  cards.forEach(c=>{
    const okR=region==='all'||c.dataset.region===region;
    const okT=!t||c.dataset.search.includes(t);
    const ok=okR&&okT;
    c.style.display=ok?'':'none';
    if(ok)shown++;
  });
  const e=document.getElementById('empty');
  if(e)e.style.display=shown?'none':'block';
}
if(q)q.addEventListener('input',apply);
chips.forEach(ch=>ch.addEventListener('click',()=>{
  chips.forEach(x=>x.classList.remove('on'));ch.classList.add('on');
  region=ch.dataset.region;apply();
}));
"""


def esc(x):
    return html.escape(str(x or ""), quote=True)


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def page(title, body, extra_js=""):
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
{body}
<div id="lb"><div><img alt=""><div class="cap"></div></div></div>
<script>{LIGHTBOX_JS}{extra_js}</script>
</body>
</html>
"""


def gallery(card):
    if not card.get("photos"):
        return ""
    out = ['<div class="gal">']
    for ph in card["photos"]:
        cap = esc(ph.get("caption", ""))
        credit = ph.get("credit", "")
        credit_html = ""
        if credit:
            if ph.get("page"):
                credit_html = (f'<span class="credit"> · <a href="{esc(ph["page"])}" '
                               f'target="_blank" rel="noopener">{esc(credit)}</a></span>')
            else:
                credit_html = f'<span class="credit"> · {esc(credit)}</span>'
        out.append(
            f'<figure><img src="{esc(ph["url"])}" alt="{cap}" loading="lazy">'
            f'<figcaption>{cap}{credit_html}</figcaption></figure>'
        )
    out.append("</div>")
    return "".join(out)


def place_page(card, date_sent):
    region = REGION_RU.get(card.get("bucket", ""), "")
    parts = [
        '<div class="wrap">',
        '<a class="back" href="index.html">← весь гайд</a>',
        '<div class="hero">',
        f'<div class="country">{esc(card.get("country"))}{" · " + esc(region) if region else ""}</div>',
        f'<h1>{esc(card["ru"])}</h1>',
    ]
    if card.get("status"):
        parts.append(f'<div class="status">{esc(card["status"])}</div>')
    if card.get("lead"):
        parts.append(f'<p class="lead">{esc(card["lead"])}</p>')
    parts.append("</div>")

    parts.append(gallery(card))

    if card.get("why"):
        parts.append('<section class="blk"><h2>Почему это место</h2>')
        parts += [f"<p>{esc(p)}</p>" for p in card["why"]]
        parts.append("</section>")

    if card.get("must_see"):
        parts.append('<section class="blk"><h2>Что именно смотреть</h2>')
        for it in card["must_see"]:
            block = f'<div class="item"><b>{esc(it["name"])}</b>{esc(it.get("what", ""))}'
            if it.get("tip"):
                block += f'<div class="tip">↳ {esc(it["tip"])}</div>'
            parts.append(block + "</div>")
        parts.append("</section>")

    if card.get("hacks"):
        parts.append('<section class="blk"><h2>Лайфхаки</h2><ul class="clean">')
        for h in card["hacks"]:
            src = (f' <a href="{esc(h["src"])}" target="_blank" rel="noopener">источник</a>'
                   if h.get("src") else "")
            parts.append(f'<li>{esc(h["tip"])}{src}</li>')
        parts.append("</ul></section>")

    season = card.get("season") or {}
    if season:
        parts.append('<section class="blk"><h2>Когда ехать</h2><dl class="facts">')
        for key, label in (("best", "Лучшее время"), ("avoid", "Лучше не ехать"),
                           ("daily", "По часам дня")):
            if season.get(key):
                parts.append(f"<div><dt>{label}</dt><dd>{esc(season[key])}</dd></div>")
        parts.append("</dl></section>")

    safety = card.get("safety") or {}
    if safety:
        parts.append('<section class="blk"><h2>Безопасность</h2>')
        if safety.get("status"):
            parts.append(f'<div class="status">{esc(safety["status"])}</div>')
        if safety.get("text"):
            parts.append(f"<p>{esc(safety['text'])}</p>")
        if safety.get("points"):
            parts.append('<ul class="clean">')
            parts += [f"<li>{esc(p)}</li>" for p in safety["points"]]
            parts.append("</ul>")
        parts.append("</section>")

    if card.get("know"):
        parts.append('<section class="blk"><h2>Что нужно знать</h2><dl class="facts">')
        for item in card["know"]:
            parts.append(f"<div><dt>{esc(item['label'])}</dt><dd>{esc(item['text'])}</dd></div>")
        parts.append("</dl></section>")

    if card.get("cinema"):
        parts.append('<section class="blk"><h2>Здесь снимали</h2><ul class="clean">')
        for c in card["cinema"]:
            year = f" ({esc(c['year'])})" if c.get("year") else ""
            parts.append(f'<li><b>{esc(c["title"])}</b>{year} — {esc(c.get("note", ""))}</li>')
        parts.append("</ul></section>")

    if card.get("facts"):
        parts.append('<section class="blk"><h2>Чего почти никто не знает</h2><ul class="clean">')
        parts += [f"<li>{esc(f)}</li>" for f in card["facts"]]
        parts.append("</ul></section>")

    log = card.get("logistics") or {}
    if log:
        parts.append('<section class="blk"><h2>Практика</h2><dl class="facts">')
        for key, label in (("days", "Сколько дней"), ("how", "Как добраться"),
                           ("base", "Где базироваться"), ("money", "Деньги")):
            if log.get(key):
                parts.append(f"<div><dt>{label}</dt><dd>{esc(log[key])}</dd></div>")
        parts.append("</dl></section>")

    if card.get("route"):
        parts.append('<section class="blk"><h2>Как встроить в маршрут</h2>'
                     f'<p>{esc(card["route"])}</p></section>')

    if card.get("sources"):
        parts.append('<section class="blk"><h2>Откуда информация</h2><ul class="clean">')
        for s in card["sources"]:
            parts.append(f'<li><a href="{esc(s["url"])}" target="_blank" '
                         f'rel="noopener">{esc(s["title"])}</a></li>')
        parts.append("</ul></section>")

    if date_sent:
        parts.append(f'<footer>Пришло в рассылке {esc(date_sent)}</footer>')
    parts.append('<a class="back" href="index.html">← весь гайд</a></div>')
    return page(f'{card["ru"]} — гайд по путешествиям', "".join(parts))


def collection_page(col):
    """Большой тематический раздел: гайд по региону, подборка троп или пляжей."""
    parts = ['<div class="wrap">', '<a class="back" href="index.html">← весь гайд</a>',
             '<div class="hero">']
    if col.get("kicker"):
        parts.append(f'<div class="country">{esc(col["kicker"])}</div>')
    parts.append(f'<h1>{esc(col["title"])}</h1>')
    if col.get("lead"):
        parts.append(f'<p class="lead">{esc(col["lead"])}</p>')
    parts.append("</div>")

    sections = col.get("sections", [])
    if len(sections) > 2:
        parts.append('<nav class="toc"><h2>Содержание</h2><ol>')
        for i, s in enumerate(sections):
            parts.append(f'<li><a href="#s{i}">{esc(s["title"])}</a></li>')
        parts.append("</ol></nav>")

    for para in col.get("intro", []):
        parts.append(f'<p class="introp">{esc(para)}</p>')

    for i, s in enumerate(sections):
        parts.append(f'<section class="blk" id="s{i}">')
        parts.append(f'<h2>{esc(s["title"])}</h2>')
        if s.get("kicker"):
            parts.append(f'<div class="status">{esc(s["kicker"])}</div>')
        if s.get("summary"):
            parts.append(f'<p class="lead">{esc(s["summary"])}</p>')
        if s.get("photos"):
            parts.append(gallery(s))
        for para in s.get("text", []):
            parts.append(f"<p>{esc(para)}</p>")
        for it in s.get("items", []):
            block = f'<div class="item"><b>{esc(it["name"])}</b>{esc(it.get("what", ""))}'
            if it.get("tip"):
                block += f'<div class="tip">↳ {esc(it["tip"])}</div>'
            parts.append(block + "</div>")
        if s.get("facts"):
            parts.append('<ul class="clean">')
            parts += [f"<li>{esc(f)}</li>" for f in s["facts"]]
            parts.append("</ul>")
        if s.get("practical"):
            parts.append('<dl class="facts">')
            for p in s["practical"]:
                parts.append(f'<div><dt>{esc(p["label"])}</dt><dd>{esc(p["text"])}</dd></div>')
            parts.append("</dl>")
        parts.append("</section>")

    if col.get("sources"):
        parts.append('<section class="blk"><h2>Откуда информация</h2><ul class="clean">')
        for s in col["sources"]:
            parts.append(f'<li><a href="{esc(s["url"])}" target="_blank" '
                         f'rel="noopener">{esc(s["title"])}</a></li>')
        parts.append("</ul></section>")

    if col.get("updated"):
        parts.append(f'<footer>Обновлено {esc(col["updated"])}</footer>')
    parts.append('<a class="back" href="index.html">← весь гайд</a></div>')
    return page(f'{col["title"]} — гайд по путешествиям', "".join(parts))


def index_page(cards, dates, waiting, collections=None):
    countries = sorted({c.get("country", "") for c in cards})
    regions = []
    for c in cards:
        r = c.get("bucket")
        if r and r not in regions:
            regions.append(r)

    head = [
        '<div class="wrap"><header class="top">',
        "<h1>Мой гайд по путешествиям</h1>",
        "<p>Собирается сам, по два места каждое утро. Каждое место — один раз.</p>",
        '<div class="stats">',
        f'<div class="stat"><b>{len(cards)}</b><span>мест</span></div>',
        f'<div class="stat"><b>{len(countries)}</b><span>стран</span></div>',
        f'<div class="stat"><b>{len(dates)}</b><span>дней</span></div>',
        f'<div class="stat"><b>{waiting}</b><span>в очереди</span></div>',
        "</div></header>",
    ]

    if collections:
        head.append('<div class="cols">')
        for col in collections:
            head.append(
                f'<a class="col" href="{esc(col["id"])}.html">'
                f'<b>{esc(col["title"])}</b>'
                f'<span>{esc(col.get("lead", ""))}</span></a>'
            )
        head.append("</div>")

    head += [
        '<div class="tools">',
        '<input id="q" type="search" placeholder="Поиск: страна, место, слово…">',
        '<button class="chip on" data-region="all">Всё</button>',
    ]
    for r in regions:
        head.append(f'<button class="chip" data-region="{esc(r)}">{esc(REGION_RU.get(r, r))}</button>')
    head.append("</div>")

    if not cards:
        head.append('<div class="empty">Пока ничего не пришло. Первая рассылка — в 9 утра.</div>')

    head.append('<div class="grid">')
    for c in cards:
        photo = (c.get("photos") or [{}])[0].get("url", "")
        search = " ".join([c.get("ru", ""), c.get("en", ""), c.get("country", ""),
                           c.get("lead", ""), REGION_RU.get(c.get("bucket", ""), "")]).lower()
        thumb = (f'<div class="ph"><img src="{esc(photo)}" alt="" loading="lazy"></div>'
                 if photo else "")
        head.append(
            f'<a class="card" href="{esc(c["id"])}.html" data-region="{esc(c.get("bucket", ""))}" '
            f'data-search="{esc(search)}">{thumb}<div class="body">'
            f'<div class="country">{esc(c.get("country"))}</div>'
            f'<h3>{esc(c["ru"])}</h3>'
            f'<p class="lead">{esc(c.get("lead", ""))}</p></div></a>'
        )
    head.append('</div><div class="empty" id="empty" style="display:none">Ничего не нашлось</div>')
    head.append(f'<footer>Обновлено {datetime.now().strftime("%d.%m.%Y")} · '
                f'ещё {waiting} мест ждут своей очереди</footer></div>')
    return page("Мой гайд по путешествиям", "".join(head), FILTER_JS)


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    log = read_json(LOG, {"days": [], "sent": []}) or {"days": [], "sent": []}
    catalog = read_json(PLACES, {"places": []})
    meta = {p["id"]: p for p in catalog.get("places", [])}

    sent_date = {}
    for day in log.get("days", []):
        for pid in day.get("ids", []):
            sent_date[pid] = day["date"]

    # На сайт попадают только уже отправленные места — чтобы утро оставалось сюрпризом.
    cards = []
    for pid in log.get("sent", []):
        card = read_json(CARDS / f"{pid}.json")
        if not card:
            continue
        base = meta.get(pid, {})
        for key in ("ru", "en", "country", "bucket"):
            card.setdefault(key, base.get(key, ""))
        cards.append(card)

    cards.sort(key=lambda c: sent_date.get(c["id"], ""), reverse=True)

    for card in cards:
        (DOCS / f"{card['id']}.html").write_text(
            place_page(card, sent_date.get(card["id"], "")), encoding="utf-8")

    collections = []
    col_dir = ROOT / "data" / "collections"
    for path in sorted(col_dir.glob("*.json")) if col_dir.exists() else []:
        col = read_json(path)
        if not col:
            continue
        col.setdefault("id", path.stem)
        (DOCS / f"{col['id']}.html").write_text(collection_page(col), encoding="utf-8")
        collections.append(col)

    written = {p.stem for p in CARDS.glob("*.json")}
    waiting = len(written - set(log.get("sent", [])))
    dates = [d["date"] for d in log.get("days", [])]
    (DOCS / "index.html").write_text(
        index_page(cards, dates, waiting, collections), encoding="utf-8")

    print(f"Сайт собран: {len(cards)} мест, {len(dates)} дней, в очереди {waiting}, "
          f"больших разделов {len(collections)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
