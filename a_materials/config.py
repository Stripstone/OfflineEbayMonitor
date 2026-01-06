"""
CONFIG — EBAY OFFLINE SILVER MONITOR

Single source of truth for:
- scan folder
- market assumptions (spot, pawn/dealer exit floors)
- filtering (negative + positive page-sanity)
- EMA capture hygiene
- PROS tuning (business-case knobs)
- email delivery
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
# CORE MARKET CONFIG (HITs)
# =============================================================================

SPOT_PRICE = 62.00

# Pawn payout percent of melt value (your guaranteed melt exit reference)
PAWN_PAYOUT_PCT = 82.0  # ||| 84 -- Dealers changing prices

# Dealer payout percent of numismatic FMV benchmark (your guaranteed numismatic exit reference)
NUMISMATIC_PAYOUT_PCT = 60.0

# Bid offset applied when calculating recommended max bid (item only)
BID_OFFSET = 0.00

# Margin target range (for HIT rec-max math)
MIN_MARGIN_PCT = 12.0
MAX_MARGIN_PCT = 60.0

# Only consider listings ending within this many hours (set None to disable)
MAX_TIME_HOURS = 0.50

# Default minimum quantity extracted from title (None disables)
DEFAULT_MIN_QUANTITY = None

# Default blacklist keywords (global)
DEFAULT_BLACKLIST = []


# =============================================================================
# FILE SELECTION (WHICH HTML FILES ARE “SILVER MARKET” PAGES)
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


# =============================================================================
# POSITIVE PAGE-SANITY FILTERS (PREVENT OFF-TOPIC LISTINGS FROM ENTERING PIPELINE)
# =============================================================================

POSITIVE_REQUIRED_TERMS_RULES = [
    # ------------------------
    # KENNEDY HALF DOLLARS
    # ------------------------
    {
        "source_regex": r"(?i)kennedy|jfk",
        "groups": [
            ["kennedy", "jfk"],
            ["half", "50c", "50¢"],
        ],
    },

    # ------------------------
    # FRANKLIN HALF DOLLARS
    # ------------------------
    {
        "source_regex": r"(?i)franklin",
        "groups": [
            ["franklin"],
            ["half", "50c", "50¢"],
        ],
    },

    # ------------------------
    # WALKING LIBERTY HALF DOLLARS
    # ------------------------
    {
        "source_regex": r"(?i)walking|walker",
        "groups": [
            ["walking", "walker"],
            ["liberty"],
            ["half", "50c", "50¢"],
        ],
    },

    # ------------------------
    # PEACE DOLLARS
    # ------------------------
    {
        "source_regex": r"(?i)peace",
        "groups": [
            ["peace"],
            ["dollar", "$1", "one dollar"],
        ],
    },

    # ------------------------
    # BARBER (default: HALF DOLLAR pages)
    # ------------------------
    {
        "source_regex": r"(?i)barber",
        "groups": [
            ["barber"],
            ["half", "50c", "50¢"],
        ],
    },

    # ------------------------
    # SEATED LIBERTY (dollar/half/quarter pages)
    # ------------------------
    {
        "source_regex": r"(?i)seated",
        "groups": [
            ["seated"],
            ["liberty"],
            ["dollar", "$1", "half", "50c", "50¢", "quarter", "25c", "25¢"],
        ],
    },
]

# Delete HTML files after they are processed (only those that actually parsed listings)
DELETE_PROCESSED_HTML = True


# =============================================================================
# MONITOR LOOP TIMING
# =============================================================================

DEFAULT_CHECK_INTERVAL_MIN = 1.10
SLEEP_JITTER_SEC = 5.0


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
MAILGUN_SMTP_DEBUG = 0


# =============================================================================
# ADVANCED / FUTURE TOGGLES
# =============================================================================

# Keep false unless you explicitly want interactive prompts again.
PROMPT_FOR_FILTERS = False


# =============================================================================
# EMA (PRICE CAPTURE) SETTINGS
# =============================================================================

# Price capture only when bids > 0
PRICE_CAPTURE_ONLY_IF_BIDS = True

# EMA capture buffer to simulate late auction bidding (your original “bump_pct” lever)
PRICE_CAPTURE_BUMP_PCT = 0.08 #recommended 0.08

# EMA smoothing factor
EMA_ALPHA = 0.40

# Capture only if ending within N minutes
PRICE_CAPTURE_MAX_MINUTES = 30


# =============================================================================
# PROS / PROSPECT SCORING (BUSINESS-CASE KNOBS)
# =============================================================================

# Informational “market exit” reference (NOT used to raise floors)
EBAY_NET_PAYOUT_PCT = 78.0

# Risk profile for early learning volume
PROS_MODE = "aggressive"  # "conservative" | "balanced" | "aggressive"


# Hard business gates for PROS alerts
#PROS_MAX_TOTAL = 5000.00

if PROS_MODE == "conservative":
    PROS_MIN_DEALER_MARGIN_PCT = 22.0
    PROS_MIN_SCORE = 80
elif PROS_MODE == "aggressive":
    PROS_MIN_DEALER_MARGIN_PCT = 05.0
    PROS_MIN_SCORE = 60
else:  # balanced
    PROS_MIN_DEALER_MARGIN_PCT = 15.0
    PROS_MIN_SCORE = 70

# Cat-3 “premium language priced like raw” knobs (PROS-only; must never feed EMA)
PROS_CAT3_MISPRICE_TOL_PCT = 5.0
PROS_CAT3_MISPRICE_BONUS = 35
PROS_CAT3_REQUIRE_ENDING_SOON = True
PROS_CAT3_MAX_MINUTES = 30

# PROS-only hard disqualifiers (do NOT affect HIT logic)
# Mirrors your stated “YES disqualify” list: problem coins, replicas, unclear metal content.
PROS_DISQUALIFY_KEYWORDS = [
    # problem coins / damage
    "holed", "hole", "drilled", "pierced", "plugged",
    "bent", "damaged", "broken", "scratched", "details",
    "harshly cleaned", "cleaned",

    # replica / copy / fantasy
    "replica", "copy", "fantasy", "reproduction",

    # unclear metal content
    "plated", "clad", "silver plate", "silver plated", "silver tone", "silver toned",
    "gold tone", "gold toned",
]

PROS_DISQUALIFY_REGEX = [
    r"\b(?:replica|copy|fantasy|reproduction)\b",
]

# Text-proxy scoring lists (tune freely)
PROS_HYPE_KEYWORDS = [
    # General hype / sales language (often priced-in)
    "monster", "wow", "elite", "rare!!", "superb", "amazing",
    "beautiful", "blazing", "choice", "gem", "premium", "rare", "key date",
    "clearance", "start", "starts", "start$", "start $", "nr", "no reserve",

    # Grade / surface pumping
    "ms", "pf", "proof", "dmpl", "pl", "deep mirror",
    "bu", "unc", "uncirculated", "brilliant uncirculated",

    # Slab/cert signals
    "pcgs", "ngc", "anacs", "icg", "cac", "slab", "graded", "certified",
]

PROS_UNDERDESCRIBED_KEYWORDS = [
    "estate", "old collection", "attic", "found", "as is", "no reserve",
    "better date", "scarce date",
]

# Signals that often indicate priced-in premium (reduce PCX)
PROS_HIGH_GRADE_KEYWORDS = [
    # Slab / grading signals
    "pcgs", "ngc", "anacs", "icg", "cac",
    # Grade / condition marketing
    "ms", "ms-", "ms60", "ms61", "ms62", "ms63", "ms64", "ms65", "ms66", "ms67", "ms68", "ms69", "ms70",
    "au", "a.u.", "about uncirculated", "unc", "uncirculated", "bu", "brilliant uncirculated",
    "proof", "pr", "pf", "deep cameo", "dcam", "ultra cameo", "ucam", "cameo",
    "pl", "prooflike", "dmpl", "deep mirror prooflike",
    "gem", "choice", "blast white", "monster toning", "full bands", "full bell lines",
]

PRICE_CAPTURE_DISQUALIFY_KEYWORDS = [
    # multi / bulk / bundle language (EMA must be singles-only)
    "lot", "lots", "group", "collection", "estate", "hoard",
    "mixed", "bundle", "set", "roll", "bag", "coins",

    # grade/hype/special surfaces (EMA baseline is raw G/VG, conservative)
    "bu", "brilliant uncirculated", "unc", "uncirculated",
    "au", "xf", "ef", "ms", "choice", "gem",
    "pl", "dmpl", "proof",

    # slabs/certs
    "pcgs", "ngc", "anacs", "icg", "slab", "graded", "certified", "holder",

    # obvious non-coin accessories
    "no coins", "coin book", "folder", "album",
    "money clip", "keychain", "cutout", "pendant", "necklace",
]

PRICE_CAPTURE_DISQUALIFY_REGEX = [
    r"\b\d+\s*x\b",
    r"\b\d+\s*(?:coin|coins|pc|pcs|piece|pieces)\b",
    r"\(\s*\d+\s*(?:coin|coins|pc|pcs|piece|pieces)\s*(?:lot)?\s*\)",
    r"\blot\s*(?:of\s*)?\d+\b",
    r"\bms\s*\d{2}\b",
    r"\bpf\s*\d{2}\b",
]

