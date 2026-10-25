"""Import a documented same-date Portuguese bond-price and payment panel."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_panel(folder):
    folder = Path(folder)
    bonds = pd.read_csv(folder / "bonds.csv")
    flows = pd.read_csv(folder / "cashflows.csv")
    provenance = folder / "provenance.json"
    legacy = json.loads(provenance.read_text(encoding="utf-8")) if provenance.exists() else {}
    if not isinstance(legacy, dict):
        raise ValueError("Expected a JSON object in optional provenance.json.")
    conventions = ["observation_date", "settlement_date", "price_basis", "curve_time_basis",
                   "cashflow_conventions", "data_kind"]
    for key in conventions:
        if key in bonds and key in legacy:
            if not bonds[key].eq(legacy[key]).all():
                raise ValueError(f"Conflicting convention in bonds.csv and provenance.json: {key}.")
        elif key not in bonds and key in legacy and key not in conventions[:2]:
            bonds[key] = legacy[key]
    if any(key not in bonds or bonds[key].isna().any() or bonds[key].nunique() != 1
           for key in conventions):
        raise ValueError("Require consistent dates and explicit price/cash-flow conventions in bonds.csv.")
    meta = {key: bonds[key].iloc[0] for key in conventions}
    if (meta["data_kind"] != "market_observations" or meta["price_basis"] != "per_100_face"
            or meta["curve_time_basis"] != "ACT/365F"):
        raise ValueError("Require market observations, prices per 100 and ACT/365F discount times.")
    meta["source_url"] = bonds["source_url"].iloc[0] if "source_url" in bonds else legacy.get("source_url", "imported_bond_prices")
    observation = pd.Timestamp(meta["observation_date"])
    settlement = pd.Timestamp(meta["settlement_date"])
    if (pd.isna(observation) or pd.isna(settlement)
            or observation.tz is not None or settlement.tz is not None
            or observation != observation.normalize() or settlement != settlement.normalize()
            or settlement < observation or (settlement-observation).days > 7):
        raise ValueError("Invalid observation or settlement dates.")
    bond_columns = {"isin", "observation_date", "settlement_date", "currency",
                    "issuer", "instrument_type", "clean_price", "accrued_interest"}
    if not bond_columns.issubset(bonds) or not {"isin", "payment_date", "amount"}.issubset(flows):
        raise ValueError("Missing bond or cash-flow columns.")
    if (bonds.empty or flows.empty or bonds[list(bond_columns)].isna().any().any()
            or flows[["isin", "payment_date", "amount"]].isna().any().any()
            or bonds["isin"].duplicated().any()
            or flows.duplicated(["isin", "payment_date"]).any()
            or set(bonds["isin"]) != set(flows["isin"])):
        raise ValueError("Missing, duplicate or unmatched bonds and cash flows.")
    for column, value in {"observation_date": meta["observation_date"],
                          "settlement_date": meta["settlement_date"], "currency": "EUR",
                          "issuer": "Republic of Portugal",
                          "instrument_type": "nominal_fixed_rate"}.items():
        if not bonds[column].eq(value).all():
            raise ValueError(f"Inconsistent Portuguese panel: {column}.")
    if not bonds["isin"].str.fullmatch(r"PT[A-Z0-9]{9}[0-9]").all():
        raise ValueError("Expected Portuguese ISIN identifiers.")
    prices = bonds[["clean_price", "accrued_interest"]].to_numpy(dtype=float)
    amounts = flows.amount.to_numpy(dtype=float)
    if (not np.isfinite(prices).all() or not np.isfinite(amounts).all()
            or (prices[:, 0] <= 0).any() or (prices[:, 1] < 0).any() or (amounts <= 0).any()):
        raise ValueError("Prices and cash flows must be finite with valid signs.")
    dates = pd.to_datetime(flows.payment_date, format="%Y-%m-%d", errors="raise")
    if dates.isna().any() or (dates <= settlement).any():
        raise ValueError("Every entitled payment must follow settlement.")
    flows = flows.assign(time_years=(dates-settlement).dt.days / 365)
    matrix = flows.pivot(index="isin", columns="time_years", values="amount").fillna(0)
    matrix = matrix.reindex(bonds["isin"]).sort_index(axis=1)
    return bonds, matrix, meta
