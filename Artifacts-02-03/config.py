# config.py
"""
CONFIG — EBAY OFFLINE SILVER MONITOR

Single source of truth for:
- scan folder
- market assumptions (spot, pawn exit floor)
- filtering
- EMA capture hygiene
- email delivery

Sprint 05.5 scope: Basic runtime foundation
"""

from __future__ import annotations

import os

# =============================================================================
# FILE SYSTEM
# =============================================================================

# Folder containing saved eBay HTML pages
HTML_FOLDER_PATH = r"C:\Users\Triston Barker\Desktop\EbayMiner\ebay_pages"

# Where we store EMA data (offline price benchmarks)
PRICE_STORE_PATH = os.path.join(os.path.dirname(__file__), "price_store.json")

# Where we store hit dedupe keys
SEEN_HITS_PATH = os.path.join(os.path.dirname(__file__), "seen_hits.json")


# =============================================================================
# CORE MARKET CONFIG
# =============================================================================

SPOT_PRICE = 31.50  # USD per oz (manually updated)

# Pawn payout percent of melt value (guaranteed melt exit reference)
PAWN_PAYOUT_PCT = 80.0

# Dealer payout percent of numismatic FMV benchmark (Sprint 06.3)
NUMISMATIC_PAYOUT_PCT = 60.0

# Margin target for HIT rec-max math
MIN_MARGIN_PCT = 15.0
MAX_MARGIN_PCT = 60.0


# =============================================================================
# TIME & QUANTITY FILTERS
# =============================================================================

# Only consider listings ending within this many hours (None = no limit)
MAX_TIME_HOURS = 24.0

# Default minimum quantity extracted from title (None disables)
DEFAULT_MIN_QUANTITY = None


# =============================================================================
# BLACKLIST
# =============================================================================

# Global keyword blacklist
DEFAULT_BLACKLIST = []


# =============================================================================
# FILE SELECTION (WHICH HTML FILES ARE "SILVER MARKET" PAGES)
# =============================================================================

SILVER_FILENAME_KEYWORDS = [
    "morgan",
    "peace",
    "barber",
    "seated",
    "franklin",
    "kennedy",
    "walking",
    "silver",
]

# Delete HTML files after they are processed
DELETE_PROCESSED_HTML = True


# =============================================================================
# MONITOR LOOP TIMING
# =============================================================================

DEFAULT_CHECK_INTERVAL_MIN = 2.0  # Minutes between scan cycles
SLEEP_JITTER_SEC = 5.0  # Random jitter to avoid patterns


# =============================================================================
# EMAIL SETTINGS (MAILGUN SMTP)
# =============================================================================

EMAIL_ENABLED = True

FROM_EMAIL = "alerts@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
TO_EMAILS = ["johnny.monitor@gmx.com"]

MAILGUN_SMTP_SERVER = "smtp.mailgun.org"
MAILGUN_SMTP_PORT = 587
MAILGUN_SMTP_LOGIN = "johnnymonitor.mailgun.org@sandboxdb0bf36453ab448baf9ac17275a43135.mailgun.org"
MAILGUN_SMTP_PASSWORD = "99Pushups%"


# =============================================================================
# EMA (PRICE CAPTURE) SETTINGS
# =============================================================================

# Price capture only when bids > 0
PRICE_CAPTURE_ONLY_IF_BIDS = True

# EMA capture buffer to simulate late auction bidding
PRICE_CAPTURE_BUMP_PCT = 8.0

# EMA smoothing factor
EMA_ALPHA = 0.40

# Capture only if ending within N minutes
PRICE_CAPTURE_MAX_MINUTES = 30


#EndOfFile


# =============================================================================
# DIAGNOSTICS (Sprint 06.1)
# =============================================================================

# Enable diagnostic output to ./diagnostics/
DEBUG_DIAGNOSTICS = True


# =============================================================================
# FILTER TERMS (Sprint 06)
# =============================================================================

# Blocked terms - listings with these are INELIGIBLE
BLOCKED_TERMS = [
    "lot",
    "roll",
    "set",
    "face value",
    "damaged",
    "money clip",
    "keychain",
    "pendant",
    "jewelry",
    "necklace",
]


#EndOfFile
