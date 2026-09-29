#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утренняя рассылка: берёт следующие неотправленные места и отправляет их в Telegram.

Запускается сам на GitHub Actions каждое утро. Ноутбук для этого не нужен.

Главное свойство: повтор невозможен. Что отправлено — записано в data/log.json,
и больше никогда не берётся. Порядок мест считается по кругу через все регионы,
поэтому два дня подряд не приходит из одной части мира.

Используется только стандартная библиотека Python — ничего устанавливать не нужно.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    MSK = ZoneInfo("Europe/Moscow")
except Exception:  # на всякий случай, если нет базы часовых поясов
    MSK = None

ROOT = Path(__file__).resolve().parent.parent
PLACES = ROOT / "data" / "places.json"
LOG = ROOT / "data" / "log.json"
CARDS = ROOT / "cards"
CONFIG = ROOT / "data" / "config.json"

API = "https://api.telegram.org/bot{token}/{method}"
TG_TEXT_LIMIT = 4096
TG_CAPTION_LIMIT = 1024


# ─────────────────────────── файлы ───────────────────────────

def read_json(path, default=None):
    if not Path(path).exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ─────────────────────── порядок мест ────────────────────────

def rotation_order(places, bucket_order):
    """По кругу через регионы, избегая одной страны рядом.

    Результат одинаков при каждом запуске — порядок не «плавает».
    """
    by_bucket = defaultdict(deque)
    for p in places:
        by_bucket[p["bucket"]].append(p)

    buckets = [b for b in bucket_order if by_bucket[b]]
    for b in by_bucket:
        if b not in buckets:
            buckets.append(b)

    order, recent = [], []
    i = 0
    guard = 0
    while any(by_bucket[b] for b in buckets) and guard < 100000:
        guard += 1
        bucket = buckets[i % len(buckets)]
        i += 1
        dq = by_bucket[bucket]
        if not dq:
            continue
        chosen = None
        for _ in range(len(dq)):
            if dq[0]["country"] not in recent[-6:]:
                chosen = dq.popleft()
                break
            dq.rotate(-1)
        if chosen is None:
            chosen = dq.popleft()
        order.append(chosen)
        recent.append(chosen["country"])
    return order


def pick_today(order, sent_ids, count):
    """Следующие неотправленные места, у которых уже написана карточка."""
    picked = []
    waiting_without_card = 0
    for place in order:
        if place["id"] in sent_ids:
            continue
        card_path = CARDS / f"{place['id']}.json"
        if not card_path.exists():
            waiting_without_card += 1
            continue
        card = read_json(card_path)
        card.setdefault("id", place["id"])
        card.setdefault("ru", place["ru"])
        card.setdefault("country", place["country"])
        card.setdefault("bucket", place["bucket"])
        picked.append(card)
        if len(picked) >= count:
            break
    return picked, waiting_without_card


# ─────────────────────── текст сообщения ─────────────────────

def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_caption(card):
    head = f"<b>{esc(card['ru']).upper()}</b> · {esc(card['country'])}"
    lead = esc(card.get("lead", ""))
    caption = f"{head}\n<i>{lead}</i>" if lead else head
    return caption[:TG_CAPTION_LIMIT]


def build_text(card):
    """Полная карточка в виде блоков. Блоки потом склеиваются в сообщения."""
    blocks = []

    title = f"<b>{esc(card['ru']).upper()}</b> · {esc(card['country'])}"
    if card.get("status"):
        title += f"\n<i>{esc(card['status'])}</i>"
    blocks.append(title)

    for para in card.get("why", []):
        blocks.append(esc(para))

    if card.get("must_see"):
        rows = ["🎯 <b>ЧТО ИМЕННО СМОТРЕТЬ</b>"]
        for item in card["must_see"]:
            row = f"\n<b>{esc(item['name'])}</b>\n{esc(item.get('what', ''))}"
            if item.get("tip"):
                row += f"\n<i>↳ {esc(item['tip'])}</i>"
            rows.append(row)
        blocks.append("\n".join(rows))

    if card.get("hacks"):
        rows = ["🧭 <b>ЛАЙФХАКИ</b>"]
        for h in card["hacks"]:
            line = f"\n• {esc(h['tip'])}"
            if h.get("src"):
                line += f" <a href=\"{esc(h['src'])}\">·источник</a>"
            rows.append(line)
        blocks.append("\n".join(rows))

    season = card.get("season") or {}
    if season:
        rows = ["🗓 <b>КОГДА ЕХАТЬ</b>"]
        if season.get("best"):
            rows.append(f"\n<b>Лучшее время:</b> {esc(season['best'])}")
        if season.get("avoid"):
            rows.append(f"\n<b>Не стоит:</b> {esc(season['avoid'])}")
        if season.get("daily"):
            rows.append(f"\n<b>По часам:</b> {esc(season['daily'])}")
        blocks.append("".join(rows))

    safety = card.get("safety") or {}
    if safety:
        rows = ["🛡 <b>БЕЗОПАСНОСТЬ</b>"]
        if safety.get("status"):
            rows.append(f"\n<b>{esc(safety['status'])}</b>")
        if safety.get("text"):
            rows.append(f"\n{esc(safety['text'])}")
        for point in safety.get("points", []):
            rows.append(f"\n• {esc(point)}")
        blocks.append("".join(rows))

    if card.get("know"):
        rows = ["📋 <b>ЧТО НУЖНО ЗНАТЬ</b>"]
        for item in card["know"]:
            rows.append(f"\n<b>{esc(item['label'])}:</b> {esc(item['text'])}")
        blocks.append("".join(rows))

    if card.get("cinema"):
        rows = ["🎬 <b>ЗДЕСЬ СНИМАЛИ</b>"]
        for c in card["cinema"]:
            year = f" ({esc(c['year'])})" if c.get("year") else ""
            rows.append(f"\n• <b>{esc(c['title'])}</b>{year} — {esc(c.get('note', ''))}")
        blocks.append("".join(rows))

    if card.get("facts"):
        rows = ["💡 <b>ЧЕГО ПОЧТИ НИКТО НЕ ЗНАЕТ</b>"]
        for fact in card["facts"]:
            rows.append(f"\n• {esc(fact)}")
        blocks.append("".join(rows))

    log = card.get("logistics") or {}
    if log:
        rows = ["🧳 <b>ПРАКТИКА</b>"]
        labels = [("days", "Сколько дней"), ("how", "Как добраться"),
                  ("base", "Где базироваться"), ("money", "Деньги")]
        for key, label in labels:
            if log.get(key):
                rows.append(f"\n<b>{label}:</b> {esc(log[key])}")
        blocks.append("".join(rows))

    if card.get("route"):
        blocks.append(f"🧩 <b>КАК ВСТРОИТЬ В МАРШРУТ</b>\n{esc(card['route'])}")

    if card.get("sources"):
        links = ", ".join(
            f"<a href=\"{esc(s['url'])}\">{esc(s['title'])}</a>" for s in card["sources"]
        )
        blocks.append(f"📚 <b>Откуда всё это:</b> {links}")

    return blocks


def pack_blocks(blocks, limit=TG_TEXT_LIMIT):
    """Склеивает блоки в сообщения, не разрывая блок посередине."""
    messages, current = [], ""
    for block in blocks:
        candidate = block if not current else current + "\n\n" + block
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                messages.append(current)
            while len(block) > limit:
                cut = block.rfind("\n", 0, limit)
                cut = cut if cut > limit // 2 else limit
                messages.append(block[:cut])
                block = block[cut:].lstrip("\n")
            current = block
    if current:
        messages.append(current)
    return messages


# ────────────────────────── Telegram ─────────────────────────

class Telegram:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = str(chat_id)

    def call(self, method, payload, retries=3):
        url = API.format(token=self.token, method=method)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last = None
        for attempt in range(retries):
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                last = f"HTTP {e.code}: {detail}"
                # 429 — слишком часто, ждём столько, сколько просит Telegram
                if e.code == 429:
                    try:
                        wait = json.loads(detail)["parameters"]["retry_after"]
                    except Exception:
                        wait = 5
                    time.sleep(wait + 1)
                    continue
                if 500 <= e.code < 600:
                    time.sleep(3 * (attempt + 1))
                    continue
                break
            except Exception as e:  # сеть
                last = repr(e)
                time.sleep(3 * (attempt + 1))
        raise RuntimeError(f"Telegram {method} не ответил: {last}")

    def album(self, photos, caption):
        media = []
        for i, photo in enumerate(photos):
            item = {"type": "photo", "media": photo["url"]}
            if i == 0 and caption:
                item["caption"] = caption
                item["parse_mode"] = "HTML"
            media.append(item)
        return self.call("sendMediaGroup", {"chat_id": self.chat_id, "media": media})

    def photo(self, url, caption=None):
        payload = {"chat_id": self.chat_id, "photo": url}
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        return self.call("sendPhoto", payload)

    def text(self, message, preview=False):
        return self.call("sendMessage", {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": not preview},
        })


def send_card(tg, card):
    """Альбом фотографий, затем структурированный текст."""
    photos = [p for p in card.get("photos", []) if p.get("url")][:10]
    sent_photos = 0

    if photos:
        try:
            tg.album(photos, build_caption(card))
            sent_photos = len(photos)
        except RuntimeError as e:
            print(f"  ! альбом не ушёл ({e}); пробую по одной", flush=True)
            for i, photo in enumerate(photos):
                try:
                    tg.photo(photo["url"], build_caption(card) if i == 0 else None)
                    sent_photos += 1
                    time.sleep(1)
                except RuntimeError as inner:
                    print(f"  ! фото пропущено: {photo['url']} ({inner})", flush=True)
        time.sleep(2)

    for message in pack_blocks(build_text(card)):
        tg.text(message)
        time.sleep(1)

    return sent_photos


# ──────────────────────────── main ───────────────────────────

def main():
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv

    config = read_json(CONFIG, {}) or {}
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID")
               or str(config.get("chatId", ""))).strip()
    per_day = int(config.get("placesPerDay", 2))

    catalog = read_json(PLACES)
    order = rotation_order(catalog["places"], catalog["bucketOrder"])

    log = read_json(LOG, {"days": [], "sent": []}) or {"days": [], "sent": []}
    sent_ids = set(log.get("sent", []))

    now = datetime.now(MSK) if MSK else datetime.now()
    today = now.strftime("%Y-%m-%d")

    if not force and any(d["date"] == today for d in log.get("days", [])):
        print(f"За {today} уже отправлено — выхожу, чтобы не дублировать.")
        return 0

    cards, waiting = pick_today(order, sent_ids, per_day)
    total_written = len(list(CARDS.glob("*.json")))
    left = total_written - len(sent_ids)

    print(f"Дата: {today}")
    print(f"Написано карточек: {total_written}, отправлено ранее: {len(sent_ids)}, в запасе: {left}")
    print("Сегодня: " + (", ".join(c["ru"] for c in cards) if cards else "нечего отправить"))

    if dry_run:
        for card in cards:
            print("─" * 50)
            print(build_caption(card))
            for message in pack_blocks(build_text(card)):
                print(message)
            print(f"[фото: {len(card.get('photos', []))}]")
        return 0

    if not token:
        print("ОШИБКА: нет TELEGRAM_BOT_TOKEN. Добавь его в Secrets репозитория.",
              file=sys.stderr)
        return 1
    if not chat_id:
        print("ОШИБКА: нет chatId.", file=sys.stderr)
        return 1

    tg = Telegram(token, chat_id)

    if not cards:
        tg.text(
            "🧭 <b>Запас карточек кончился</b>\n\n"
            f"В каталоге ещё {waiting} мест, но тексты к ним не написаны. "
            "Включи ноутбук и скажи Claude: «допиши карточки для утренней рассылки» — "
            "он добавит следующую пачку, и рассылка пойдёт дальше сама."
        )
        return 0

    date_ru = now.strftime("%d.%m.%Y")
    tg.text(f"☀️ <b>Доброе утро!</b>  <i>{date_ru}</i>\nСегодня два места — {len(cards)} карточки ниже.")
    time.sleep(1)

    delivered = []
    for card in cards:
        print(f"Отправляю: {card['ru']}", flush=True)
        photos_sent = send_card(tg, card)
        print(f"  фото отправлено: {photos_sent}", flush=True)
        delivered.append(card)
        time.sleep(2)

    log.setdefault("days", []).append({
        "date": today,
        "ids": [c["id"] for c in delivered],
        "places": [f"{c['ru']} ({c['country']})" for c in delivered],
    })
    log["sent"] = sorted(sent_ids | {c["id"] for c in delivered})
    write_json(LOG, log)

    left_after = total_written - len(log["sent"])
    if left_after <= 4:
        tg.text(
            f"⚠️ <b>Осталось карточек: {left_after}</b>\n\n"
            "Включи ноутбук и скажи Claude: «допиши карточки для утренней рассылки»."
        )
    print(f"Готово. В запасе осталось: {left_after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
