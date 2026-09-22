"""Reproducible scenario valuation from analyst inputs sourced to disclosures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..data_models import ValuationScenario
from ..utils import Config


REQUIRED_COLUMNS = {
    "Symbol", "TargetRevenueCr", "TargetOPM", "OtherIncomeCr", "InterestCr",
    "DepreciationCr", "TaxRate", "ShareCountCr", "LowPE", "HighPE", "Source",
}


class ValuationEngine:
    """Calculate target-year EPS and fair-value range; never invent inputs."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.inputs = self._load_inputs()

    def _load_inputs(self) -> dict[str, dict]:
        path = Path(self.config.valuation_inputs_path)
        if not path.exists():
            return {}
        frame = pd.read_csv(path)
        missing = REQUIRED_COLUMNS.difference(frame.columns)
        if missing:
            raise ValueError("valuation_inputs.csv missing columns: " + ", ".join(sorted(missing)))
        frame["Symbol"] = frame["Symbol"].astype(str).str.upper().str.strip()
        if "Scenario" not in frame.columns:
            frame["Scenario"] = "base"
        # One row is one explicit scenario (bear/base/bull). The engine never
        # blends them, because a blended target hides the actual assumptions.
        frame["Scenario"] = frame["Scenario"].fillna("base").astype(str).str.lower().str.strip()
        return {row["Symbol"]: row.to_dict() for _, row in frame.iterrows()}

    @staticmethod
    def _number(row: dict, name: str) -> float | None:
        value = pd.to_numeric(row.get(name), errors="coerce")
        return None if pd.isna(value) else float(value)

    def value(self, symbol: str) -> ValuationScenario:
        row = self.inputs.get(symbol)
        if not row:
            return ValuationScenario(status="MISSING_INPUTS")
        values = {name: self._number(row, name) for name in REQUIRED_COLUMNS - {"Symbol", "Source"}}
        if any(value is None for value in values.values()) or not str(row.get("Source") or "").strip():
            return ValuationScenario(status="INCOMPLETE_INPUTS")

        revenue, opm = values["TargetRevenueCr"], values["TargetOPM"]
        shares, tax_rate = values["ShareCountCr"], values["TaxRate"]
        low_pe, high_pe = values["LowPE"], values["HighPE"]
        if revenue <= 0 or shares <= 0 or not 0 <= tax_rate <= 100 or low_pe <= 0 or high_pe < low_pe:
            return ValuationScenario(status="INVALID_INPUTS")

        pbt = revenue * opm / 100 + values["OtherIncomeCr"] - values["InterestCr"] - values["DepreciationCr"]
        pat = max(0.0, pbt * (1 - tax_rate / 100))
        eps = pat / shares  # INR crore / INR crore shares = INR per share
        current_price = self._number(row, "CurrentPrice")
        current_eps = self._number(row, "CurrentEPS")
        fair_low, fair_high = eps * low_pe, eps * high_pe
        return ValuationScenario(
            status="READY", target_year=str(row.get("TargetYear") or ""),
            projected_revenue_cr=revenue, projected_opm_pct=opm, projected_pat_cr=pat,
            projected_eps=eps, low_pe=low_pe, high_pe=high_pe,
            fair_value_low=fair_low, fair_value_high=fair_high, current_price=current_price,
            upside_low_pct=((fair_low / current_price) - 1) * 100 if current_price and current_price > 0 else None,
            upside_high_pct=((fair_high / current_price) - 1) * 100 if current_price and current_price > 0 else None,
            source=str(row.get("Source") or ""), notes=str(row.get("Notes") or ""),
            scenario=str(row.get("Scenario") or "base"), current_eps=current_eps,
            trailing_pe=(current_price / current_eps if current_price and current_eps and current_eps > 0 else None),
            forward_pe=(current_price / eps if current_price and eps > 0 else None),
            assumptions_verified=True,
        )
