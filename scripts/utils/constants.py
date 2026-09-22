"""Constants and signal definitions for analysis."""

# NSE/BSE API endpoints
NSE_HOME = "https://www.nseindia.com/"
NSE_SECURITIES_PAGE = "https://www.nseindia.com/static/market-data/securities-available-for-trading"
NSE_ANNOUNCEMENTS = "https://www.nseindia.com/api/corporate-announcements"
NSE_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_SME_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv"
NSE_PREOPEN_URL = "https://www.nseindia.com/api/market-data-pre-open"
NSE_QUOTE_URL = "https://www.nseindia.com/api/quote-equity"
BSE_API = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_SECURITIES_PAGE = "https://www.bseindia.com/corporates/list_scrips"
BSE_SME_MARKET_PAGE = "https://m.bseindia.com/smemarket.aspx"
BSE_SEARCH = f"{BSE_API}/GetQuoteAllSearchDatabeta/w"
BSE_SCRIP_LIST_URL = f"{BSE_API}/ListofScripData/w"
BSE_ANNOUNCEMENTS = f"{BSE_API}/AnnSubCategoryGetData/w"
BSE_ATTACHMENT = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"

# Market-cap segment thresholds (INR crore)
SEGMENT_NANO_MAX_CR = 100.0
SEGMENT_MICRO_MAX_CR = 500.0
# Research scope: ₹1,000 Cr is the preferred hunting ground.  ₹1,000–3,000 Cr
# is retained as an extended watchlist so a promising company is not discarded
# merely because it has crossed an arbitrary line.
SEGMENT_IDEAL_MAX_CR = 1000.0
# The scanner's active ceiling is configured separately (default ₹3,000 Cr).
# This is only the maximum band the code supports, allowing a deliberate
# expansion beyond the default without a code change.
SEGMENT_CEILING_CR = 5000.0

def classify_segment(market_cap_cr: float | None) -> str | None:
    """Classify a company into nano / micro / small_micro by market cap (INR Cr)."""
    if market_cap_cr is None or market_cap_cr <= 0:
        return None
    if market_cap_cr < SEGMENT_NANO_MAX_CR:
        return "nano"
    if market_cap_cr <= SEGMENT_MICRO_MAX_CR:
        return "micro"
    if market_cap_cr <= SEGMENT_IDEAL_MAX_CR:
        return "small_micro"
    if market_cap_cr <= SEGMENT_CEILING_CR:
        return "extended_micro"
    return None


def segments_for_filter(filter_name: str) -> set[str]:
    """Map CLI segment filter to universe segment labels."""
    mapping = {
        "nano": {"nano"},
        "micro": {"micro"},
        "nano_micro": {"nano", "micro"},
        "ideal": {"nano", "micro", "small_micro"},
        "all": {"nano", "micro", "small_micro", "extended_micro"},
    }
    return mapping.get(filter_name, {"nano", "micro"})

# Document classification rules
DOCUMENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "concall_transcript",
        (
            "transcript",
            "earnings call",
            "earnings conference call",
            "conference call",
            "concall",
        ),
    ),
    (
        "financial_results",
        (
            "financial result",
            "audited result",
            "unaudited result",
            "standalone and consolidated results",
            "quarterly results",
            "quarter ended",
        ),
    ),
    ("annual_report", ("annual report",)),
    ("investor_presentation", ("investor presentation", "corporate presentation")),
    (
        "strategic_update",
        (
            "order received",
            "receipt of order",
            "order win",
            "press release",
            "media release",
            "business update",
            "capacity expansion",
            "commercial production",
            "commissioning",
            "acquisition",
            "joint venture",
            "credit rating",
        ),
    ),
)

# Evidence signals with patterns, point values, and labels
# 
# INVESTMENT PHILOSOPHY: We search for LEADING INDICATORS of future profitability,
# not a trailing P/E alone. Why?
# - Order book = Future revenue (customers already committed)
# - Capacity expansion = Revenue scaling (tomorrow's growth, visible today)
# - Margin improvement = Operating leverage (visibility into profitability)
# - Management vision = Strategic direction (predicts capital allocation)
#
# Trailing ratios are context and risk checks; they cannot replace a sourced
# forward earnings scenario.
#
SIGNALS: dict[str, list[tuple[str, int, str]]] = {
    "execution": [
        # Highest conviction: Actual production is live and running
        # This is PROOF of execution, not promise
        (
            r"\bcommercial production (?:commenced|started|began)\b|"
            r"\bcommissioned (?:our |the |a )?(?:plant|project|facility|unit|line)\b",
            9,
            "commercial execution",
        ),
        # Capacity expansion = Tomorrow's revenue capacity visible today
        # When capex completes, company scales revenue without proportional cost
        (r"\bcapacity (?:expanded|expansion|addition)\b", 7, "capacity expansion"),
        # Order book = Actual customer commitments for future delivery
        # Unlike guidance (which can change), order book is binding revenue
        (r"\b(?:order book|unexecuted orders?)\b", 7, "order-book visibility"),
        # New customer/client wins = Revenue diversification and growth pipes
        (r"\bnew (?:customer|client)s?\b|\bcustomer addition", 5, "customer addition"),
        # Backward integration = Margin expansion + supply chain control
        # When company controls production, margins improve automatically
        (r"\bbackward integration\b", 6, "backward integration"),
        # Trial/pilot = Pre-commercialization stage, less proven
        (r"\btrial production\b|\bpilot plant\b", 4, "trial-stage progress"),
    ],
    "guidance": [
        # Management revenue guidance = Explicit visibility into growth trajectory
        # When conservative management gives guidance, it's usually achievable
        (r"\b(?:revenue|sales) guidance\b|\btarget(?:ing)? revenue\b", 7, "revenue guidance"),
        # Margin guidance = Management expecting operating leverage
        (r"\bmargin guidance\b|\btarget(?:ing)? (?:an? )?margin\b", 6, "margin guidance"),
        # Quantified capex = Proof of commitment to growth investment
        (r"\bcapex\b.{0,80}\b(?:crore|cr\.?|million|billion)\b", 5, "quantified capex"),
        # Time-bound guidance = Specific targets show planning confidence
        # Vague guidance is noise; specific targets matter
        (r"\b(?:expect|target|guidance).{0,70}\b(?:fy2[5-9]|q[1-4])\b", 5, "time-bound guidance"),
    ],
    "financial_quality": [
        # Positive FCF = Proof of cash generation (most important metric)
        # Unlike accounting profits, FCF is hard to manipulate
        (
            r"\b(?:generated|reported|delivered) positive free cash flow\b|"
            r"\bfree cash flow (?:turned|was|remained) positive\b",
            8,
            "positive free cash flow",
        ),
        # Deleveraging = Company uses cash for debt reduction, not acquisitions
        # Shows financial discipline and improves leverage metrics
        (
            r"\b(?:net )?debt (?:reduced|declined|decreased)\b|"
            r"\breduced (?:our |the )?(?:net )?debt\b",
            7,
            "deleveraging",
        ),
        # Working capital improvement = Cash unlocked from operations
        # Better collection, inventory turns, payables management
        (r"\bworking capital\b.{0,50}\b(?:improv|reduc)", 5, "working-capital improvement"),
        # EBITDA/margin expansion = Operating leverage is kicking in
        # This is the FIRST signal of improving profitability
        (r"\b(?:ebitda|operating) margin\b.{0,60}\b(?:improv|expand|increase)", 6, "margin improvement"),
        # Export growth = New revenue geography, higher margins typically
        (r"\bexport(?:s| revenue)?\b.{0,50}\b(?:grew|growth|increase)", 4, "export growth"),
    ],
    "promoter_alignment": [
        (r"\bpromoter(?:s)?\b.{0,50}\b(?:infus|subscribe|warrant)", 5, "promoter capital infusion"),
        (r"\bno pledge\b|\bpromoter pledge.{0,20}\bnil\b", 5, "no promoter pledge"),
    ],
    "migration_catalyst": [
        (
            r"\bmain board\b.{0,50}\b(?:migration|transfer|listing)\b|"
            r"\bsme.{0,30}main board\b|"
            r"\bin-principle approval\b",
            15,
            "mainboard_migration_signal",
        ),
        (
            r"\bpostal ballot\b.{0,50}\b(?:migration|mainboard)\b",
            10,
            "migration_in_progress",
        ),
    ],
    "risk": [
        # Auditor qualification = Hidden weakness in financials or controls
        # Qualified opinion means auditor couldn't verify all claims
        (r"\bqualified opinion\b|\badverse opinion\b", -15, "auditor qualification"),
        # Material internal control weakness = Red flag for financial manipulation
        (
            r"\bmaterial weakness (?:was|has been|is) "
            r"(?:identified|found|reported)\b|"
            r"\bidentified (?:a )?material weakness\b|"
            r"\binternal control weakness (?:was|has been|is) "
            r"(?:identified|found|reported)\b",
            -12,
            "control weakness",
        ),
        # Payment defaults = Company in distress, can't pay bills
        # This is survival question, not execution issue
        (r"\bdefault(?:ed)?\b.{0,50}\b(?:loan|debt|payment)", -15, "payment default"),
        # Going concern risk = Auditor questions if company will survive
        # This is existential risk, avoids at all costs
        (
            r"\bmaterial uncertainty\b.{0,100}\bgoing concern\b|"
            r"\bsubstantial doubt\b.{0,100}\bgoing concern\b",
            -12,
            "going-concern risk",
        ),
        # Promoter pledge = Founder in distress, selling company through market
        # Massive dilution risk if stock crashes
        (
            r"\b(?:promoter pledge|shares pledged)\b.{0,50}\b(?:[1-9]\d*(?:\.\d+)?%)\b",
            -8,
            "promoter pledge",
        ),
        # Related party exposure = Potential for value transfer, accounting games
        (r"\brelated party\b.{0,60}\b(?:loan|advance|receivable)", -7, "related-party exposure"),
        # Execution delays = Management over-promises, under-delivers
        # Capacity commissioned late = revenue recognition delays
        (r"\bdelay(?:ed)?\b.{0,50}\b(?:project|commission|capex)", -7, "execution delay"),
        # Key resignations = Loss of institutional knowledge or distress signal
        (
            r"\b(?:auditor|director|cfo)\b.{0,40}\b(?:has|have|had) resigned\b|"
            r"\bresignation of (?:the )?(?:statutory )?(?:auditor|director|cfo)"
            r"\b.{0,50}\b(?:effective|accepted|received)\b",
            -8,
            "key resignation",
        ),
        # Regulatory issues = Future cash drain for penalties/legal
        (
            r"\bshow cause notice\b|\bsearch and seizure\b|"
            r"\b(?:fraud (?:was|has been) (?:detected|reported)|alleged fraud)\b",
            -15,
            "regulatory risk",
        ),
    ],
    "promotion_risk": [
        (r"\bmultibagger\b|\b1000x\b|\bguaranteed return\b", -8, "promotional language"),
    ],
}

# Default configuration values
DEFAULT_MIN_MARKET_CAP_CR = 100
DEFAULT_MARKET_CAP_LIMIT_CR = 3500
DEFAULT_LOOKBACK_DAYS = 365
DEFAULT_MAX_DOCUMENTS_PER_COMPANY = 30
DEFAULT_REQUEST_DELAY_SECONDS = 0.15
DEFAULT_CRAWL_SEGMENT = "all"
DEFAULT_UNIVERSE_MAX_QUOTE_LOOKUPS = 2500

# Data directories
DATA_DIR = "data"
TRANSCRIPT_DIR = "data/documents"
OUTPUT_JSON = "data/output/analysis_results.json"
OUTPUT_REPORT = "data/output/ALPHA_MASTER_WATCHLIST.md"
OUTPUT_MEMOS_DIR = "data/output/company_memos"
VALUATION_INPUTS_PATH = "data/inputs/valuation_scenarios.csv"
UNIVERSE_PATH = "data/universe/company_universe.csv"
UNIVERSE_PARQUET_PATH = "data/universe/company_universe.parquet"
BSE_CODE_CACHE_PATH = "data/bse_code_cache.json"
SOURCES_PATH = "data/inputs/manual_sources.csv"
FILING_INDEX = "data/filing_index.json"
