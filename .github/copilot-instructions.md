# Alpha Finder - LLM Instruction File

**Read this first.** This file explains the core investment philosophy behind the Alpha Engine. All code, analysis, and recommendations flow from these principles.

---

## 🎯 Core Thesis

> **Today's stock price reflects the last 2 years of company actions.**
> 
> **We find companies where tomorrow's performance is visible today.**

This is not a financial ratio screener. This is a **vision and execution engine**.

## 🚀 Strategic Focus: The "Alpha" Hunt

### Micro Cap & Nano Cap Specialization
We prioritize **undiscovered Micro Cap (<₹500 Cr) and Nano Cap (<₹100 Cr)** stocks. The goal is to identify these companies *before* they are discovered by the broader market, hit upper circuits, or become fully priced.

### High-Growth Sector Priorities (2025-2027)
- **Semiconductors:** OSAT, power electronics, chip design, specialty chemicals for fabrication.
- **Defense:** Specialized batteries, radars, UAVs, automated test equipment, indigenized components.
- **AI Infrastructure:** HPC, data center connectivity, AI-led automation tools.
- **Clean Energy:** Biofuels, green hydrogen infrastructure, EV supply chain (batteries, chargers).
- **Waste Management:** e-Waste recycling, lithium-ion battery recycling, waste-to-energy.

### Finding "Undiscovered" Alpha
- **Look for:** Low trading volume, lack of institutional coverage, and management vision that isn't yet reflected in the price.
- **Avoid:** Stocks already in "upper circuit" mode or where the "good news" is already common knowledge.
- **Goal:** Find the *next* AARON or AARTECH when they were still nano-caps.

---

## The Framework: PAST → PRESENT → FUTURE

```
PAST                    PRESENT                 FUTURE
────────────────────────────────────────────────────────
Financial ratios        Current price           Order book
ROCE, ROE, FCF          (what everyone          Management vision
Historical revenue      can see)                Product pipeline
Balance sheet                                   Market positioning
                                                Regulatory tailwind

← Lagging indicators →  ← Consensus →   ← Where alpha lives →
```

### What This Means

- **PAST (Lagging):** Ratios show what already happened. By the time ROCE improves, the market has repriced.
- **PRESENT (Consensus):** Current stock price = consensus opinion. Everyone knows about the 2% FCF yield.
- **FUTURE (Leading):** Order book commitments, capacity coming online, management executing the vision. **This is what the market hasn't priced yet.**

---

## Why Ratios Fail (Historical Examples)

### Bajaj Finance 2009
- **What Ratios Said:** ROE was weak, NPA ratios looked scary post-crisis. "Avoid."
- **What Vision Said:** Sanjiv Bajaj's clear thesis: *consumer credit for India's aspiring middle class, technology-first.*
- **Outcome:** 100x return. Ratio-watchers missed it entirely.

### Eicher Motors 2010
- **What Ratios Said:** Royal Enfield barely profitable. ROCE mediocre. "Skip."
- **What Vision Said:** Siddharth Lal's vision: *premiumise the motorcycle, own the lifestyle, build a brand.*
- **Outcome:** 30x return. The vision executed exactly as planned.

### Dixon Technologies 2017
- **What Ratios Said:** Thin margins, inconsistent FCF. "Not interesting."
- **What Vision Said:** Order book from Samsung showed China+1 manufacturing coming to India. Transformational.
- **Outcome:** 40x return. Ratios finally caught up 3 years later.

### AARTECH (Current)
- **What Ratios Say:** ROCE 6% (3-yr avg), thin margins from FY25 fire loss. "Avoid."
- **What Vision Says:** 
  - Army validated AAPM product (no other Indian competitor)
  - Beaten ABB in Indonesia bid (first time ever)
  - Order book ₹10 Cr growing to ₹25 Cr by June (binding commitments)
  - TAM ₹500 Cr+ defense energy market (addressable ₹50-100 Cr vs ₹40 Cr current revenue)
  - New facility operational (capacity expansion)
  - Patent pending on tech
  - Management winning against MNCs for the first time
- **Outcome:** Stock repriceable 5-10x when vision executes.

---

## How to Spot Opportunity vs. Traps

### Use Ratios For: ELIMINATION (Remove Traps)
```
Red Flags to Avoid:
─────────────────
✗ Promoter pledge > 30% (personal financial distress)
✗ Debt/equity > 2 and rising (leverage spiral)
✗ Auditor qualifications (revenue recognition issues)
✗ Related party transactions > 10% of revenue (tunneling)
✗ Negative CFO 5 years straight (not viable)
✗ Frequent equity dilution (shareholder value destruction)

Conclusion: REJECT. Ratios predict fraud, not performance.
```

### Use Vision For: SELECTION (Find Compounders)
```
Selection Criteria:
──────────────────
✓ Order book growing faster than revenue (future visibility)
✓ Capacity expansion started this quarter (revenue coming)
✓ Management with skin in the game (founder/promoter executing)
✓ Product with no Indian competitor (monopoly advantage)
✓ Government policy tailwind (10-year+ regulatory support)
✓ TAM that's 50x current revenue (room to grow)
✓ Winning against MNCs (proof of concept at global standards)

Conclusion: INVESTIGATE. Vision predicts performance.
```

### The Balance
**Ratios = Elimination filter** (remove frauds and value traps)  
**Vision = Selection filter** (find the next 10x compounder)

---

## What the Alpha Engine Actually Does

The Alpha Engine implements this philosophy through:

### 1. **Crawler Engine** (Discovery Phase)
- Finds NSE/BSE corporate filings, concalls, annual reports
- Downloads evidence documents
- Builds filing index (prevents re-crawling)

### 2. **Cleaning Engine** (Preparation)
- Extracts text from PDFs
- Normalizes whitespace and formatting
- Removes boilerplate

### 3. **Analysis Engine** (Signal Detection)
- **Searches for LEADING indicators:**
  - Order book visibility (`+7 pts`)
  - Capacity expansion (`+7 pts`)
  - Backward integration (`+6 pts`)
  - Margin improvement (`+6 pts`)
  - Management vision (`+5 pts`)
  - Export growth (`+4 pts`)
  
- **Detects RISK signals:**
  - Auditor qualifications (`-15 pts`)
  - Payment defaults (`-15 pts`)
  - Going concern issues (`-12 pts`)
  - Promoter pledge (`-8 pts`)
  
- **Ignores lagging indicators:**
  - Current ratio (irrelevant to growth)
  - P/E ratio (already priced in)
  - Debt-to-equity (only matters if execution fails)
  - Historical growth (past ≠ future)

### 4. **Filtering Engine** (Prioritization)
- Scores companies 0-100 based on evidence
- Assigns confidence levels (HIGH/MEDIUM/LOW)
- Research priorities: DEEP_DIVE (>30 pts) → WATCH → NEEDS_DATA → PASS

---

## Investment Timeline: How Repricing Happens

```
Month 0-3: DISCOVERY
├─ Find company with vision + early execution signals
├─ Order book visible in filings
├─ Capacity expansion started
└─ Example: AARON at 30 pts, AARTECH at 26 pts

Month 6-9: VALIDATION
├─ Orders convert to revenue as promised
├─ Capacity comes online, utilization increases
├─ First sign of margin expansion
├─ Stock moves +20-30% (smart money accumulates)
└─ Risk: Execution delays (rare if vision is clear)

Month 12-18: REPRICING
├─ Market recognizes the thesis
├─ Ratios finally improve (ROCE, FCF)
├─ Analyst coverage begins
├─ Stock moves +50-100% (institutional demand)
└─ This is when the 10x happens

Month 18-24: EXIT
├─ Risk/reward becomes unfavorable
├─ Stock fairly valued or expensive
├─ Redeploy capital to next thesis
└─ Cycle repeats
```

---

## Applying This Framework to Code

### For Signal Detection (`constants.py`)
Every signal has a reason. Not every pattern is created equal:
- `+7 pts "order-book"` → Binding customer commitments (future revenue)
- `-15 pts "payment default"` → Survival question
- `+6 pts "margin improvement"` → Operating leverage visible in filings
- `+9 pts "commercial production"` → Vision became reality

### For Analysis (`analysis_engine.py`)
The engine answers: "Given the documents we have, how visible is tomorrow's performance?"
- Looks at concalls (what management says will happen)
- Looks at filings (what evidence supports the vision)
- Scores based on leading indicators, NOT lagging ratios

### For Filtering (`filtering_engine.py`)
Companies are prioritized by:
1. **Score** (evidence of vision)
2. **Confidence** (multiple documents confirming thesis)
3. **Coverage** (do we have enough documents to decide?)
4. **Market cap** (size for position-taking)

---

## Examples: How to Read Companies

### AARON Industries → DEEP_DIVE (30 pts, HIGH confidence)
```
Vision: "Become world's largest energy meter manufacturer"

Evidence:
├─ Order book ₹1,309 Cr (2+ years revenue visibility) ✓
├─ Capacity expansion: New facility operational Q1 FY26 ✓
├─ Margin expansion: EBITDA 18% → 21% (operating leverage) ✓
├─ Backward integration: In-house component manufacturing ✓
├─ Management: 20-year proven track record executing capex ✓
└─ Risk: None detected ✓

Score Breakdown:
+7 (order book) +7 (capacity) +6 (backward integration) 
+6 (margin improvement) +4 (proven execution) = 30 pts

Timeline: Reprice in 12-18 months as capacity comes online
```

### AARTECH → WATCH (26 pts, HIGH confidence)
```
Vision: "Become India's leading defense electronics player"

Evidence:
├─ Order book: ₹10 Cr growing to ₹25 Cr (binding commitments) ✓
├─ Product: Army-validated AAPM (no Indian competitor) ✓
├─ Execution: Beaten ABB in Indonesia bid (1st time) ✓
├─ Capacity: New facility coming online next quarter ✓
├─ TAM: Defense market ₹500 Cr+, addressable ₹50-100 Cr ✓
└─ Risk: Execution dependent (but vision is proven) ⚠️

Score Breakdown:
+7 (order book) +7 (capacity) +5 (customer addition: ABB win)
+4 (export growth) +3 (strategic positioning) = 26 pts

Timeline: Reprice as facility comes online, orders accelerate
```

### INA (3-in-1 Oils) → VERIFY_MCAP (38 pts, needs verification)
```
Vision: "Dominant lubricants player for Indian automotive"

Evidence:
├─ Order growth clear in documents
├─ Margin expansion evident
├─ Management credible
└─ BUT: Market cap unclear (need verification)

Action: Verify market cap before investing. If ₹200 Cr, DEEP_DIVE.
        If ₹600 Cr, just WATCH.
```

---

## When Working on This Codebase

### For Modifications:
1. **Always check the signal** you're adding/modifying
   - Does it represent a LEADING indicator (future performance)?
   - Or a LAGGING indicator (past performance)?
   - LEADING: Keep it. LAGGING: Remove it.

2. **When adding companies to analysis:**
   - Read the concalls first (what management says will happen)
   - Read the quarterly updates (what actually happened)
   - Search for order book, capacity, margin signals
   - Ignore "net profit increased" (lagging) and search for "order book ₹X Cr" (leading)

3. **When debugging scoring:**
   - High-scoring companies should have visible order books, capacity expansion, margin improvement
   - If a company scores 35 pts but has no order book mention, something is wrong
   - If a company scores 5 pts but the concall is bullish, we're detecting signals wrong

4. **When discussing companies:**
   - Use the PAST → PRESENT → FUTURE framework
   - "Current ratios are fine, but order book is ₹500 Cr?" → INVESTIGATE
   - "ROCE is 8%, but capacity coming online?" → The ratio catches up in 18 months
   - "Promoter has 40% pledge" → REJECT (fraud risk, not performance risk)

---

## The One Non-Negotiable

The **only** time ratios are non-negotiable is for **governance red flags**:
- Promoter pledge > 30% (personal distress)
- Auditor qualifications (revenue recognition doubts)
- Related party loans > 10% of revenue (tunneling)
- Frequent equity dilution (shareholder value destruction)

These predict **fraud**, not performance. Everything else is negotiable if the vision is clear.

---

## Summary

```
                    Traditional Approach          Alpha Finder Approach
                    ─────────────────────         ──────────────────────
What do you read?   Balance sheet, ratios         Concalls, order book, vision
Timeline            "What happened?"              "What will happen?"
Risk filter         Low debt, high liquidity      Execution risk, vision clarity
Outcome             Miss 10x because cheap        Catch 30x because obvious

Example             "AARTECH: 6% ROCE, skip"      "AARTECH: Army validated, ABB winner,
                                                   ₹25 Cr order book, skip? DEEP_DIVE."
```

---

## Key Files to Read (In Order)

1. **[scripts/INVESTMENT_PHILOSOPHY.md](../scripts/INVESTMENT_PHILOSOPHY.md)** — Full thesis with case studies
2. **[scripts/PHILOSOPHY_GUIDE.md](../scripts/PHILOSOPHY_GUIDE.md)** — Where philosophy lives in code
3. **[scripts/utils/constants.py](../scripts/utils/constants.py)** — Each signal with WHY it matters
4. **[scripts/engines/analysis_engine.py](../scripts/engines/analysis_engine.py)** — How scoring works
5. **[ALPHA_MASTER_WATCHLIST.md](../ALPHA_MASTER_WATCHLIST.md)** — Current company rankings and evidence

---

## Questions This Codebase Answers

- ✅ Which small-cap companies have visible order books?
- ✅ Which are expanding capacity this year?
- ✅ Which have proven management executing a clear vision?
- ✅ Which are winning market share from global competitors?
- ✅ Which will likely reprice in 12-18 months as vision executes?

Questions it **ignores**:
- ❌ "Is the P/E cheap?" (Irrelevant, already priced)
- ❌ "Is the current ratio high?" (Irrelevant to growth)
- ❌ "Did EPS grow last quarter?" (Lagging, not leading)
- ❌ "Is debt/equity low?" (Only matters if execution fails)

---

**Created for:** GitHub Copilot, Claude, and any LLM analyzing ALPHA_FINDER code  
**Read this first:** Before modifying signals, scoring, or analyzing companies  
**Philosophy:** Today's price = last 2 years. Find where next 2 years are visible today.

🎯 **Build for the future. Find it in today's order books.**
