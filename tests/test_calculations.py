import pytest
from src.calculations import Calculator

class FakeApi:
    """
    Minimal fake Fiindo API for testing Calculator.

    It returns deterministic data so we can verify:
    - pe_ratio
    - revenue_growth
    - net_income_ttm
    - debt_ratio
    - latest_revenue
    """

    def get_financials(self, symbol: str, statement: str):
        if statement == "income_statement":
            # 4 quarterly rows, latest first by date
            return {
                "fundamentals": {
                    "financials": {
                        "income_statement": {
                            "data": [
                                {
                                    "period": "Q4",
                                    "date": "2024-12-31",
                                    "revenue": 200.0,
                                    "netIncome": 20.0,
                                    "eps": 0.5,
                                },
                                {
                                    "period": "Q3",
                                    "date": "2024-09-30",
                                    "revenue": 150.0,
                                    "netIncome": 15.0,
                                    "eps": 0.4,
                                },
                                {
                                    "period": "Q2",
                                    "date": "2024-06-30",
                                    "revenue": 120.0,
                                    "netIncome": 12.0,
                                    "eps": 0.3,
                                },
                                {
                                    "period": "Q1",
                                    "date": "2024-03-31",
                                    "revenue": 100.0,
                                    "netIncome": 10.0,
                                    "eps": 0.25,
                                },
                            ]
                        }
                    }
                }
            }

        if statement == "balance_sheet_statement":
            # One FY row
            return {
                "fundamentals": {
                    "financials": {
                        "balance_sheet_statement": {
                            "data": [
                                {
                                    "period": "FY",
                                    "date": "2024-12-31",
                                    "totalDebt": 300.0,
                                    "totalEquity": 150.0,
                                }
                            ]
                        }
                    }
                }
            }

        # Not needed for this test
        return {}

    def get_eod(self, symbol: str):
        # Last closing price is 50.0
        return {
            "stockprice": {
                "data": [
                    {"close": 40.0},
                    {"close": 50.0},
                ]
            }
        }


def test_calculator_computes_expected_metrics():
    """
    Calculator should return the correct metrics for a symbol
    given our synthetic FakeApi responses.
    """
    calc = Calculator()
    # overwrite real FiindoAPI with our fake one
    calc.api = FakeApi()
    result = calc.calculate_all("TEST")
    assert result is not None

    # latest quarter = Q4 2024
    # revenue_growth = (200 - 150) / 150 = 0.3333...
    assert result["revenue_growth"] == pytest.approx( (200.0 - 150.0) / 150.0 )

    # net_income_ttm = 20 + 15 + 12 + 10 = 57
    assert result["net_income_ttm"] == pytest.approx(57.0)

    # debt_ratio = totalDebt / totalEquity = 300 / 150 = 2.0
    assert result["debt_ratio"] == pytest.approx(2.0)

    # latest_price = 50, eps (latest quarter) = 0.5 → PE = 100
    assert result["pe_ratio"] == pytest.approx(100.0)

    # latest_revenue should be revenue of latest quarter (200)
    assert result["latest_revenue"] == pytest.approx(200.0)


def test_calculator_returns_none_if_not_enough_quarters():
    """
    If there are less than 4 quarterly rows, Calculator should
    return None (not enough data for TTM etc.).
    """
    class FakeApiTooShort(FakeApi):
        def get_financials(self, symbol: str, statement: str):
            if statement == "income_statement":
                return {
                    "fundamentals": {
                        "financials": {
                            "income_statement": {
                                "data": [
                                    {
                                        "period": "Q4",
                                        "date": "2024-12-31",
                                        "revenue": 200.0,
                                        "netIncome": 20.0,
                                        "eps": 0.5,
                                    },
                                    {
                                        "period": "Q3",
                                        "date": "2024-09-30",
                                        "revenue": 150.0,
                                        "netIncome": 15.0,
                                        "eps": 0.4,
                                    },
                                ]
                            }
                        }
                    }
                }
            return super().get_financials(symbol, statement)

    calc = Calculator()
    calc.api = FakeApiTooShort()
    result = calc.calculate_all("TEST")
    assert result is None
