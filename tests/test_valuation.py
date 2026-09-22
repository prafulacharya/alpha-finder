"""Tests for the spreadsheet-equivalent scenario valuation."""

import tempfile
import unittest
from pathlib import Path

from scripts.engines.valuation_engine import ValuationEngine
from scripts.utils import Config


class TestValuationEngine(unittest.TestCase):
    def test_target_year_valuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inputs.csv"
            path.write_text(
                "Symbol,TargetRevenueCr,TargetOPM,OtherIncomeCr,InterestCr,DepreciationCr,TaxRate,ShareCountCr,LowPE,HighPE,CurrentPrice,Source\n"
                "ABC,100,20,5,2,3,25,2,10,20,50,Q1 FY26 concall p. 4\n",
                encoding="utf-8",
            )
            scenario = ValuationEngine(Config(valuation_inputs_path=str(path))).value("ABC")
            self.assertEqual(scenario.status, "READY")
            self.assertAlmostEqual(scenario.projected_pat_cr, 15)
            self.assertAlmostEqual(scenario.projected_eps, 7.5)
            self.assertAlmostEqual(scenario.fair_value_low, 75)
            self.assertAlmostEqual(scenario.fair_value_high, 150)

    def test_reports_trailing_and_forward_pe_when_current_eps_is_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inputs.csv"
            path.write_text(
                "Symbol,TargetRevenueCr,TargetOPM,OtherIncomeCr,InterestCr,DepreciationCr,TaxRate,ShareCountCr,LowPE,HighPE,CurrentPrice,CurrentEPS,Source\n"
                "ABC,100,20,5,2,3,25,2,10,20,75,5,Q1 FY26 concall p. 4\n",
                encoding="utf-8",
            )
            scenario = ValuationEngine(Config(valuation_inputs_path=str(path))).value("ABC")
            self.assertAlmostEqual(scenario.trailing_pe, 15)
            self.assertAlmostEqual(scenario.forward_pe, 10)

    def test_missing_assumptions_are_not_valued(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = ValuationEngine(
                Config(valuation_inputs_path=str(Path(directory) / "none.csv"))
            ).value("ABC")
            self.assertEqual(scenario.status, "MISSING_INPUTS")


if __name__ == "__main__":
    unittest.main()
