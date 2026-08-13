#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AZAL bilet yoxlayicisi — GitHub Actions ucun.

Her islediyinde sadece BIR defe yoxlayir ve bitir.
Nece tez-tez isleyecegi  .github/workflows/bilet.yml  faylinda yazilib.

Iki rejimi var:
  yoxla  -> normal is: yer varsa Telegram-a mesaj atir
  dump   -> sehifenin metnini logda gosterir (kalibrasiya ucun)
"""

import os
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright


# ==========================================================
#   BURANI SEN DOLDURACAQSAN
# ==========================================================

# azal.az-da axtarisi bir defe elinle edib, netice sehifesinin
# unvan setrinden kopyaladigin linkleri bura yapisdir.
URLS = {
    "https://www.azal.az/book/select?lang=az&from=BAK&to=NAJ&departure_date=2026-08-13&tripType=OW&adult_count=1&child_count=0&infant_count=0&is_student=0&timestamp=1786649362889&is_citizen=1&currency=AZN",
    "https://www.azal.az/book/select?lang=az&from=BAK&to=NAJ&departure_date=2026-08-13&tripType=OW&adult_count=1&child_count=0&infant_count=0&is_student=0&timestamp=1786649362889&is_citizen=1&currency=AZN",
}

# Yer OLMAYANDA sehifede gorunen metnler (hamisi kicik herfle).
# "dump" rejimini isledib buranı duzeltmelisen.
NO_SEAT_MARKERS = [
    "reys tapilmadi",
    "reys tapılmadı",
    "ucus tapilmadi",
    "uçuş tapılmadı",
    "no flights found",
    "no flights available",
    "yer yoxdur",
]

# Sehifenin tam yuklendiyini bildiren soz.
# Bu gorunmurse, bot "hele yuklenmeyib" deyir ve bos siqnal vermir.
LOAD_MARKERS = ["azn"]

# ==========================================================


MOD = os.environ.get("MOD", "yoxla").strip().lower()
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def telegram(text):
    """Telefona mesaj atir."""
    if not TOKEN or not CHAT_ID:
        print("!! Telegram acarlari qoyulmayib, mesaj gonderilmedi.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        urllib.request.urlopen(url, data=data, timeout=20)
        print(">> Telegram mesaji gonderildi.")
    except Exception as e:
        print(f"!! Telegram xetasi: {e}")


def sehifeni_oxu(page, url):
    """Sehifeni acir ve butun metnini kicik herfle qaytarir."""
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(3000)
    return (page.inner_text("body") or "").lower()


def yer_varmi(text):
    """(netice, sebeb) qaytarir."""
    if not text or len(text) < 200:
        return False, "sehife bos geldi"

    if LOAD_MARKERS and not any(m in text for m in LOAD_MARKERS):
        return False, "netice bloku hele yuklenmeyib"

    for m in NO_SEAT_MARKERS:
        if m in text:
            return False, f"'{m}' gorunur"

    return True, "yer var"


def main():
    if any(u.startswith("BURA_") for u in URLS.values()):
        print("XETA: bilet.py faylinda URLS bolmesini doldurmamisan.")
        return

    print(f"Rejim: {MOD}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="az-AZ")

        for ad, url in URLS.items():
            try:
                text = sehifeni_oxu(page, url)
            except Exception as e:
                print(f"{ad}: sehife acilmadi -> {e}")
                continue

            if MOD == "dump":
                print("=" * 60)
                print(f"{ad} — sehife metni (ilk 4000 herf):")
                print("=" * 60)
                print(text[:4000])
                print("=" * 60)
                continue

            var, sebeb = yer_varmi(text)
            if var:
                print(f"*** {ad}: BILET VAR ***")
                telegram(f"BILET CIXDI!\n{ad}\n\nDerhal al:\n{url}")
            else:
                print(f"{ad}: hele yoxdur ({sebeb})")

        browser.close()


if __name__ == "__main__":
    main()
