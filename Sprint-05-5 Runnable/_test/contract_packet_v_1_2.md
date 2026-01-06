## Current State

**Contract Version:** v1.2 + Clarifications
**Last Updated:** December 31, 2025
**Status:** Authoritative

**Known Clarifications Issued:**
1. Counts line exact format: `Found: X | Eligible: Y | HITs: Z | New: W`
2. Target column definition: Static value "Silver" for all listings
3. Parser integration: Uses `parse_listings_from_html(html_text, ...)` returning `List[Dict[str, Any]]`

## Outputs You Produce

1. **Rulings** — Definitive answers to ambiguous requirements
2. **Clarification Addendums** — Append-only additions to contracts
3. **New Contract Versions** — Only when scope fundamentally changes (rare)

## Communication Style

- Precise and unambiguous
- Cite contract sections specifically
- Ask clarifying questions before ruling
- Document edge cases explicitly
- No hedging ("maybe", "could", "might") — rulings are definitive

---

**Contract Vault initialized. Ready to maintain semantic truth.**

What contract materials should I load?

# Contract_Packet_v1.2

**Status:** Immutable once approved  
**Scope:** UX contract, math contract, link contract, EMA & price store semantics, diagnostics invariants, non‑negotiables only  
**Exclusions:** No implementation, debugging, planning, placement decisions, stability judgments, reset mechanics, or inferred rules

---

## 1. Console UX Contract (Authoritative)

- Program runs as a **continuous loop** and must **never exit silently**.
- Every scan cycle renders output, regardless of HITs.

**Cycle structure (fixed order):**
1. Banner header
2. **ACTIVE CONFIG** block (spot, pawn %, offsets, margins, max time)
3. Timestamped line: `[HH:MM:SS] Starting scan cycle #N...`
4. Counts line (Found / Eligible / HITs / PROS)
5. **Per‑file table** preceded by `=== <filename> ===`
6. **EMAIL** section (subject + sent / no‑send)
7. Optional cleanup line
8. Visible sleep line: `Waiting <sec> seconds...`

**Table columns (fixed, in order):**  
`Target | Found | Hit? | Price | QTY | Time Left | Title`

**Time Left formatting:**
- Remaining time plus end clock
- Example: `3h42m (Today 11:18 PM)`

---

## 2. Email UX Contract (Authoritative)

**Subject (exact):**  
`<earliest_time> Offline eBay Silver HITS (<N> new)`

- Email is sent **only if** there are new HITs or PROS.
- Entries are ordered strictly by **earliest time left**.
- Formatting is monospaced; whitespace is significant.

**Body structure (fixed order):**
1. Header title
2. Separator line
3. Summary block (Spot | Pawn, Bid offset, Target margin, Max time left)
4. Blank line
5. `Total HITs: <N>`
6. Divider
7. Entry blocks
8. Final divider
9. `Generated at: YYYY-MM-DD HH:MM:SS`

**Entry rules:**
- Melt entries: no explicit HIT header.
- Numismatic entries: mandatory override line immediately after `Title:`.
- Field labels, order, spacing, and dividers are non‑negotiable.

---

## 3. Math Contract (Frozen)

**Global inputs:**
- Spot price (USD/oz)
- Pawn payout percent
- Bid offset (USD)
- Target margin range (min–max, %)
- Max time left (hours)

**Price math:**
- `current_total = item_price + shipping`

**Silver math:**
- `total_oz = qty × oz_per_coin`
- `melt = total_oz × spot`
- `pawn_payout = melt × pawn_frac`

**Margins:**
- All margins are **cost‑basis**: `profit / cost`

**Pawn profit:**
- `pawn_profit = pawn_payout − current_total`

**Recommended max:**
- Derived from pawn payout and target minimum margin

**Dealer / numismatic math (authoritative for numismatics):**
- FMV floor
- Dealer payout = FMV × dealer payout %
- Dealer profit = dealer payout − current_total

**HIT gates:**
- Melt HIT: `(pawn_profit / current_total) ≥ target_min_margin`
- Numismatic HIT: `dealer_profit > 0`

**Rounding:**
- Currency: 2 decimals
- Percent: 1 decimal
- Oz/coin: 5 decimals
- Total ounces: 2 decimals

---

## 4. Link Contract (Frozen)

- **No raw URLs** are rendered.

**Melt entries include:**
- `Link to Listing`
- `Link to Ebay Sales`

**Numismatic entries include:**
- Above links
- `Link to CoinBook`

**Construction rules:**
- Ebay Sales: SOLD + COMPLETED; series + year + mint (+ grade placeholder)
- CoinBook: **series‑level directory only** (no deep links)

---

## 5. Process Non‑Negotiables

**Hard Sprint Gate:**
- No handoff unless:
  1. Automated preflight (compile + smoke imports)
  2. Human checklist (imports explicit, UX unchanged)

**Handoff rules:**
- Small patch: one contiguous edit in one file
- Larger change: full file(s)
- System‑wide change: full bundle

---

## 6. Unchanging Constants

```text
HTML_FOLDER_PATH = r"C:\Users\Triston Barker\Desktop\EbayMiner\ebay_pages"
MAILGUN_SMTP_SERVER = "smtp.mailgun.org"
MAILGUN_SMTP_PORT = 587
MAILGUN_SMTP_LOGIN = "johnnymonitor.mailgun.org@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
MAILGUN_SMTP_PASSWORD = "99Pushups%"
MAILGUN_DOMAIN = MAILGUN_SMTP_LOGIN.split("@", 1)[1]
FROM_EMAIL = "alerts@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
TO_EMAILS = ["johnny.monitor@gmx.com"]
```

---

## 7. EMA & Price Store Contract (Required Semantics)

### EMA eligibility (STRICT, SILENT)
EMA-eligible only if all are true:
- `qty == 1`
- `bids ≥ 1`
- NOT lot / roll / set / face value
- NOT album / folder / book / “NO COINS”
- NOT accessory (money clip, keychain, pendant, jewelry, cutout)
- NOT damaged (holed, hole, pierced, drilled)

### Capture rules
- Write-time only
- +8% bump applied once at capture
- No read-time stacking
- One capture per listing per scan
- One capture per benchmark key per scan

### price_store.json schema
- `price_store.json` value = `[ema_value, sample_count, last_total, last_timestamp, observers_total]`

### Source rendering (user-facing semantics)
- Static defaults → `Source: Static Default`
- EMA → `Source: Offline EMA o.`

---

## 8. Diagnostic Observability Addendum (Sprint 06)

**Purpose:** Define invariant semantics for internal diagnostics only.

- Diagnostics are **non‑user‑facing** and must not alter console or email UX in any form.
- Diagnostics are written **to disk only** and are **gated by `DEBUG_DIAGNOSTICS`**.
- Diagnostics report **classification outcomes only**: `HIT`, `PROS`, `MISS`, `Ineligible`.
- Diagnostics **do not affect** EMA capture, EMA eligibility, EMA math, or rendering.
- **PROS must never override a Melt HIT**.

No other behavior, ordering, storage, lifecycle, or reset semantics are defined here.

---

**End of Contract_Packet_v1.2**