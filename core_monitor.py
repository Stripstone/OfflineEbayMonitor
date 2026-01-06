# core_monitor.py

import os
import random
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import smtplib
import re
from bs4 import BeautifulSoup


# ---------- EMAIL SENDING ----------

def send_mailgun_email(subject: str, body_html: str, mailgun_config: dict) -> None:
    """Generic Mailgun email sender used by all markets."""
    from_email = mailgun_config["from_email"]
    to_emails = mailgun_config["to_emails"]

    msg = MIMEText(body_html, "html")
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    print(f"\n[EMAIL] From: {from_email}")
    print(f"[EMAIL] To:   {', '.join(to_emails)}")
    print(f"[EMAIL] Subj: {subject}")

    try:
        server = smtplib.SMTP(
            mailgun_config["server"],
            mailgun_config["port"],
        )
        server.starttls()
        server.login(mailgun_config["login"], mailgun_config["password"])
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        print(f"✓ Email sent to: {', '.join(to_emails)}")
    except Exception as e:
        print(f"✗ Failed to send email: {e}")


# ---------- LISTINGS HELPER (SHARED) ----------

def parse_ebay_search_html(path):
    """
    Extract standardized listing data from ANY eBay layout (s-card, s-item, legacy).
    Returns a list of dicts containing:
    title, item_price, shipping, price (total), link, time_left
    
    This is the SINGLE SOURCE OF TRUTH for HTML parsing.
    All monitors should use this function.
    """
    results = []

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
    except Exception as e:
        print(f"  [ERROR] Could not read {path}: {e}")
        return results

    soup = BeautifulSoup(html, "html.parser")

    # --- Collect nodes from multiple possible layouts ---
    container_selectors = [
        "li.s-card",
        "li.s-item",
        "ul.srp-results.srp-list > li",
        "div.s-card",
        "div.s-item",
    ]

    nodes = []
    for sel in container_selectors:
        found = soup.select(sel)
        if found:
            #print(f"  [DEBUG] Selector '{sel}' matched {len(found)} elements")
            nodes = found
            break

    if not nodes:
        print("  [WARN] No result containers found with known selectors.")
        return results

    print(f"  [DEBUG] Using {len(nodes)} elements as result items")

    for node in nodes:
        try:
            # -------------------------------
            # TITLE
            # -------------------------------
            title_elem = node.select_one(
                ".s-item__title, .s-card__title, .s-item__info .s-item__title, [data-testid='item-title']"
            )
            if not title_elem:
                continue
            
            title = title_elem.get_text(" ", strip=True)
            
            # Clean artifact phrases
            artifact_phrases = [
                "Opens in a new window or tab",
                "Opens in a new window or tab.",
            ]
            for phrase in artifact_phrases:
                if phrase in title:
                    title = title.replace(phrase, "").strip()
            
            # Skip non-listing elements
            if title.lower() in ("shop on ebay", "new listing"):
                continue

            # -------------------------------
            # PRICE
            # -------------------------------
            price_elem = node.select_one(
                ".s-card__price, .s-item__price, .s-item__detail .s-item__price, [data-testid='item-price']"
            )
            if not price_elem:
                continue

            price_text = price_elem.get_text(strip=True)
            m = re.search(r"\$?([\d,]+\.?\d*)", price_text)
            if not m:
                continue

            item_price = float(m.group(1).replace(",", ""))

            # -------------------------------
            # SHIPPING (ROBUST - handles multiple formats)
            # -------------------------------
            shipping_cost = 0.0
            shipping_text = ""

            # Try explicit shipping elements first
            ship_elem = node.select_one(
                ".s-card__shipping, .s-card__logisticsCost, "
                ".s-item__shipping, .s-item__logisticsCost, "
                "[data-testid='item-shipping']"
            )

            if ship_elem:
                shipping_text = ship_elem.get_text(" ", strip=True)
                shipping_lower = shipping_text.lower()
                
                if "free" in shipping_lower:
                    shipping_cost = 0.0
                else:
                    ship_match = re.search(r"\$([\d,]+\.?\d*)", shipping_text)
                    if ship_match:
                        shipping_cost = float(ship_match.group(1).replace(",", ""))

            # Fallback #1: detect "+$4.52 shipping" or "+$4.52 delivery" in full card text
            if shipping_cost == 0.0 and (not shipping_text or "free" not in shipping_text.lower()):
                full_text = node.get_text(" ", strip=True)
                # Look for patterns like "+$4.52", "+ $4.52", "+$4.52 shipping"
                fallback_match = re.search(r"\+\s*\$([\d,]+\.?\d*)", full_text)
                if fallback_match:
                    try:
                        shipping_cost = float(fallback_match.group(1).replace(",", ""))
                        #print(f"  [DEBUG] Fallback shipping detected: ${shipping_cost:.2f}")
                    except ValueError:
                        pass

            # -------------------------------
            # TIME LEFT
            # -------------------------------
            time_left_elem = node.select_one(
                ".s-item__time-left, .s-card__time-left, .s-item__dynamic .LIGHT_HIGHLIGHT"
            )
            time_end_elem = node.select_one(".s-card__time-end, .s-item__time-end")
            
            if time_left_elem:
                time_left = time_left_elem.get_text(strip=True)
                if time_end_elem:
                    time_left += " " + time_end_elem.get_text(strip=True)
            else:
                time_left = ""

            # -------------------------------
            # LINK
            # -------------------------------
            link_elem = node.select_one(
                "a.s-item__link, a.s-card__link, a[href*='itm/'], a"
            )
            link = ""
            if link_elem and link_elem.has_attr("href"):
                link = link_elem["href"]

            # -------------------------------
            # BUILD RESULT DICT
            # -------------------------------
            listing = {
                "title": title,
                "item_price": item_price,
                "shipping": shipping_cost,
                "price": item_price + shipping_cost,  # total price
                "link": link,
                "time_left": time_left,
            }

            results.append(listing)

        except Exception as e:
            print(f"  [ERROR] Error parsing listing: {e}")
            continue

    print(f"  [DEBUG] Successfully parsed {len(results)} listings from file")
    return results


# ---------- TIME-LEFT HELPERS (SHARED) ----------

def parse_time_left_to_minutes_for_sort(time_left_str: str) -> int:
    """
    Lightweight time-left parser for sorting hits in the email.
    Returns minutes (int) or a large number if parsing fails.
    """
    if not time_left_str:
        return 10**9

    s = time_left_str.lower()
    matches = re.findall(r"(\d+)\s*([dhm])", s)
    if not matches:
        return 10**9

    total_minutes = 0
    for num_str, unit in matches:
        n = int(num_str)
        if unit == "d":
            total_minutes += n * 24 * 60
        elif unit == "h":
            total_minutes += n * 60
        elif unit == "m":
            total_minutes += n
    return total_minutes


def parse_end_datetime_from_time_left(time_left_str: str):
    """
    Try to parse a real datetime for the auction end time from the parenthetical
    part of the 'time left' string.
    Returns a datetime or None.
    """
    if not time_left_str:
        return None

    s = time_left_str.strip()

    # 1) Full date format like '(Dec 10, 2025 3:30 PM)'
    m = re.search(r"\(([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)\)", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%b %d, %Y %I:%M %p")
        except ValueError:
            pass

    # 2) Today / Tomorrow formats
    m = re.search(r"\((Today|Tomorrow)\s+(\d{1,2}:\d{2}\s*[AP]M)\)", s, re.IGNORECASE)
    if m:
        day_word = m.group(1).lower()
        time_part = m.group(2)
        try:
            base_date = datetime.now().date()
            if day_word == "tomorrow":
                base_date = base_date + timedelta(days=1)
            dt = datetime.strptime(time_part, "%I:%M %p")
            return datetime.combine(base_date, dt.time())
        except ValueError:
            pass

    return None


# ---------- CLEANUP ----------

def delete_processed_html(file_paths):
    """
    Delete only the HTML files that were actually processed
    by this market's monitor.
    """
    for full_path in file_paths:
        filename = os.path.basename(full_path)
        if not filename.lower().endswith(".html"):
            continue
        try:
            os.remove(full_path)
            print(f"[CLEANUP] Deleted: {filename}")
        except Exception as e:
            print(f"[CLEANUP] Could not delete {filename}: {e}")


# ---------- HIT DE-DUPE KEY ----------

def make_hit_key(filename_label: str, listing: dict):
    """
    Build a stable key for a HIT so we can avoid duplicate alerts.

    Prefer the eBay item ID from the link (/itm/1234567890).
    If there's no usable link, fallback to (filename, title, price).
    """
    link = listing.get("link") or ""
    # Try to extract item ID from the URL
    m = re.search(r"/itm/(\d+)", link)
    if m:
        return ("itm", m.group(1))

    # Fallback: use filename + title + rounded total price
    title = listing.get("title", "")
    price = round(listing.get("price", 0.0), 2)
    return ("fallback", filename_label, title, price)


# ---------- CORE LOOP ----------

def run_monitor(
    *,
    folder_path: str,
    analyzer,
    config: dict,
    build_email_body,          # function (hits, config) -> body_html
    mailgun_config: dict,
    check_interval_min: float,
    filename_filter,           # function (filename: str) -> bool
):
    """
    Shared monitoring loop.

    - analyzer must implement: analyze_file(path, config) -> (oz_per_coin, listings, hits)
      where hits is a list of (filename_label, listing, calc, extra_data).

    - build_email_body(hits, config) returns an HTML string for the email body.

    - filename_filter(filename) returns True for files that belong to this market.
    """
    print("\n" + "=" * 60)
    print(f"  EBAY OFFLINE {config.get('market_name', 'MARKET').upper()} MONITOR")
    print("=" * 60 + "\n")

    print("\nACTIVE CONFIG")
    print("-------------")
    print(f"Folder:         {folder_path}")
    if "spot_price" in config:
        print(f"Spot price:     ${config['spot_price']:.2f}")
    else:
        print("Spot price:     (n/a)")
    if "pawn_payout_pct" in config:
        print(f"Pawn payout:    {config['pawn_payout_pct']:.1f}%")
    if "bid_offset" in config:
        print(f"Bid offset:     ${config['bid_offset']:.2f}")
    if "min_margin" in config and "max_margin" in config:
        print(f"Margin target:  {config['min_margin']:.1f}%–{config['max_margin']:.1f}%")
    if config.get("max_time_hours"):
        print(f"Max time left:  {config['max_time_hours']:.2f} hours")
    else:
        print("Max time left:  (none)")
    print(f"Min quantity:   {config['min_quantity'] if config.get('min_quantity') else '(none)'}")
    print(f"Blacklist:      {', '.join(config['blacklist']) if config.get('blacklist') else '(none)'}")
    print(f"Check interval: {check_interval_min} minutes")
    print("\nPress Ctrl+C to stop.\n")

    if not os.path.isdir(folder_path):
        print("ERROR: folder_path does not exist. Please update it.")
        return

    seen_hits = set()
    cycle_index = 0
    cycles_with_files = 0

    while True:
        try:
            cycle_index += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scan cycle #{cycle_index}...")

            # Only pick files that:
            #   - are HTML
            #   - match this market's filename_filter
            html_files = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith(".html") and filename_filter(f)
            ]

            if not html_files:
                print(
                    "  No matching HTML files found in folder for this market. "
                    f"(cycles with files so far: {cycles_with_files} out of {cycle_index})"
                )
            else:
                cycles_with_files += 1
                print(
                    f"  Found {len(html_files)} HTML file(s) for this market in folder. "
                    f"(cycles with files so far: {cycles_with_files}, total cycles: {cycle_index})"
                )

            all_hits = []

            for fpath in sorted(html_files):
                _, _, hits = analyzer.analyze_file(fpath, config)
                all_hits.extend(hits)

            # Filter out hits we've already alerted on
            new_hits = []
            for hit_entry in all_hits:
                # hit_entry is (filename_label, listing, calc, extra_data)
                filename_label, listing = hit_entry[0], hit_entry[1]
                key = make_hit_key(filename_label, listing)
                if key not in seen_hits:
                    new_hits.append(hit_entry)

            if html_files:
                if new_hits:
                    # Determine earliest ending time for subject line
                    earliest_dt = None

                    for hit_entry in new_hits:
                        listing = hit_entry[1]
                        tl = listing.get("time_left")
                        if not tl:
                            continue

                        dt = parse_end_datetime_from_time_left(tl)
                        if dt is None:
                            mins = parse_time_left_to_minutes_for_sort(tl)
                            dt = datetime.now() + timedelta(minutes=mins)

                        if earliest_dt is None or dt < earliest_dt:
                            earliest_dt = dt

                    if earliest_dt is None:
                        earliest_clock = datetime.now().strftime("%I:%M %p")
                    else:
                        earliest_clock = earliest_dt.strftime("%I:%M %p")

                    subject = f"{earliest_clock} Offline eBay {config.get('market_name', 'Market')} HITS ({len(new_hits)} new)"
                    body_html = build_email_body(new_hits, config)
                    send_mailgun_email(subject, body_html, mailgun_config)

                    for hit_entry in new_hits:
                        filename_label, listing = hit_entry[0], hit_entry[1]
                        key = make_hit_key(filename_label, listing)
                        seen_hits.add(key)
                else:
                    print(
                        "\nNo NEW HITs found across processed files. No email sent.\n"
                        f"(cycles with files so far: {cycles_with_files} out of {cycle_index})"
                    )
            else:
                # No files this cycle; we've already logged that fact above.
                pass

            # Delete only the HTML files we actually processed for this market
            if html_files:
                delete_processed_html(html_files)

            # Jittered sleep: +/- 60 seconds, never below 60s
            base_seconds = check_interval_min * 60
            jitter = random.randint(-60, 60)
            wait_time = max(60, base_seconds + jitter)
            print(f"  Waiting {wait_time/60:.2f} minutes (with randomness)...\n")
            time.sleep(wait_time)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            print("Sleeping 60 seconds before retry...\n")
            time.sleep(60)
