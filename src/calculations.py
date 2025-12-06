"""
Business logic to compute all required metrics per ticker.
Metrics:
- PE Ratio: latest closing price / EPS of last quarter
- Revenue Growth: QoQ revenue growth (last quarter vs previous quarter)
- NetIncomeTTM: sum of netIncome from last 4 quarters
- DebtRatio: totalDebt / totalEquity from last full year
"""
import logging
from typing import Optional, Dict, Any, List
from src.api_client import FiindoAPI

logger = logging.getLogger(__name__)

class Calculator:
    """Fetches raw financials for a symbol and derives all required KPIs."""

    def __init__(self) -> None:
        self.api = FiindoAPI()

    def calculate_all(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Central function to calculate all metrics for one symbol.
        Returns a dict with:
        - pe_ratio
        - revenue_growth
        - net_income_ttm
        - debt_ratio
        - latest_revenue
        or None if calculation is not possible.
        """
        logger.info("Starting calculations for %s", symbol)

        # Income Statement (quarters) 
        income = self.api.get_financials(symbol, "income_statement")
        if not income:
            logger.warning("No income_statement data for %s", symbol)
            return None
        try:
            inc_data: List[Dict[str, Any]] = (
                income["fundamentals"]["financials"]["income_statement"]["data"]
            )
        except KeyError as exc:
            logger.error("Unexpected income_statement format for %s: %s", symbol, exc)
            return None

        quarters = [row for row in inc_data if str(row.get("period", "")).startswith("Q")]
        quarters.sort(key=lambda x: x.get("date", ""), reverse=True)

        if len(quarters) < 4:
            logger.warning("Not enough quarterly income data for %s", symbol)
            return None
        Q1, Q2, Q3, Q4 = quarters[:4]

        # Revenue Growth (QoQ)
        revenue_growth = None
        try:
            rev1 = float(Q1["revenue"])
            rev2 = float(Q2["revenue"])
            if rev2 != 0:
                revenue_growth = (rev1 - rev2) / rev2
        except Exception as exc:
            logger.warning("Failed to compute revenue growth for %s: %s", symbol, exc)

        # Net Income TTM
        net_income_ttm = None
        try:
            net_income_ttm = float(Q1["netIncome"]) + float(Q2["netIncome"]) + float(Q3["netIncome"]) + float(Q4["netIncome"])
        except Exception as exc:
            logger.warning("Failed to compute net_income_ttm for %s: %s", symbol, exc)

        # Balance Sheet (full years) 
        balance = self.api.get_financials(symbol, "balance_sheet_statement")
        if not balance:
            logger.warning("No balance_sheet_statement data for %s", symbol)
            return None
        try:
            bs_data: List[Dict[str, Any]] = (
                balance["fundamentals"]["financials"]["balance_sheet_statement"]["data"]
            )
        except KeyError as exc:
            logger.error("Unexpected balance_sheet format for %s: %s", symbol, exc)
            return None

        years = [row for row in bs_data if row.get("period") == "FY"]
        years.sort(key=lambda x: x.get("date", ""), reverse=True)
        if not years:
            logger.warning("No full-year balance sheet data for %s", symbol)
            return None
        FY = years[0]

        # Debt Ratio
        debt_ratio = None
        try:
            total_debt = float(FY["totalDebt"])
            total_equity = float(FY["totalEquity"])
            if total_equity != 0:
                debt_ratio = total_debt / total_equity
        except Exception as exc:
            logger.warning("Failed to compute debt_ratio for %s: %s", symbol, exc)

        # EOD price 
        eod = self.api.get_eod(symbol)
        if not eod or "stockprice" not in eod:
            logger.warning("No EOD data for %s", symbol)
            return None
        try:
            stock_list: List[Dict[str, Any]] = eod["stockprice"]["data"]
            latest_price = float(stock_list[-1]["close"])
        except Exception as exc:
            logger.error("Failed to get latest price for %s: %s", symbol, exc)
            return None

        # PE Ratio 
        pe_ratio = None
        try:
            eps = float(Q1["eps"])
            if eps != 0:
                pe_ratio = latest_price / eps
        except Exception as exc:
            logger.warning("Failed to compute PE ratio for %s: %s", symbol, exc)

        result = {
            "pe_ratio": pe_ratio,
            "revenue_growth": revenue_growth,
            "net_income_ttm": net_income_ttm,
            "debt_ratio": debt_ratio,
            "latest_revenue": float(Q1["revenue"]) if Q1.get("revenue") is not None else None,
        }

        logger.info("Finished calculations for %s", symbol)
        return result

if __name__ == "__main__":
    from src.logging_setup import setup_logging
    setup_logging()
    calc = Calculator()
