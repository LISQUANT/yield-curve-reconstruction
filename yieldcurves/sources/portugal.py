"""Import a documented same-date Portuguese bond-price and payment panel."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_panel(folder):
    folder = Path(folder)
    meta = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    required = ["source_url", "retrieved_at_utc", "observation_date", "settlement_date",
                "price_basis", "cashflow_conventions", "data_kind", "sha256"]
    if any(not meta.get(key) for key in required):
        raise ValueError("Incomplete Portuguese panel provenance.")
    if (meta["data_kind"] != "market_observations"
            or meta["price_basis"] != "per_100_face"
            or meta.get("curve_time_basis") != "ACT/365F"
            or not meta["source_url"].startswith("https://")):
        raise ValueError("Require market observations, HTTPS provenance and explicit units.")
    observation = pd.Timestamp(meta["observation_date"])
    settlement = pd.Timestamp(meta["settlement_date"])
    retrieved = pd.Timestamp(meta["retrieved_at_utc"])
    if (pd.isna(observation) or pd.isna(settlement) or pd.isna(retrieved)
            or observation.tz is not None or settlement.tz is not None
            or observation != observation.normalize() or settlement != settlement.normalize()
            or settlement < observation or (settlement-observation).days > 7
            or retrieved.tz is None or retrieved.date() < observation.date()):
        raise ValueError("Invalid observation, settlement or retrieval dates.")
    frames = []
    for name in ["bonds.csv", "cashflows.csv"]:
        raw = (folder / name).read_bytes()
        if meta["sha256"].get(name) != sha256(raw).hexdigest():
            raise ValueError(f"Checksum mismatch for {name}.")
        frames.append(pd.read_csv(folder / name))
    bonds, flows = frames
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
