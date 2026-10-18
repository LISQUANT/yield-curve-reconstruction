"""An offline teaching example, using explicitly synthetic NSS parameters."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from yieldcurves.svensson import (
    SvenssonParameters,
    discount_factor,
    instantaneous_forward,
    spot_rate,
)


def main(output=None):
    if output is None:
        output = Path(__file__).resolve().parents[1] / "outputs" / "demo"
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    parameters = SvenssonParameters(0.035, -0.015, 0.012, -0.006, 1.8, 7.0)
    maturity = np.linspace(0, 30, 301)
    spots = spot_rate(maturity, parameters)
    discounts = discount_factor(maturity, parameters, compounding="continuous")
    forwards = instantaneous_forward(maturity, parameters, compounding="continuous")
    curve = pd.DataFrame(
        {
            "maturity_years": maturity,
            "spot_rate_decimal": spots,
            "discount_factor": discounts,
            "forward_rate_continuous_decimal": forwards,
        }
    )
    curve.to_csv(output / "synthetic_curve.csv", index=False)
    selected = curve[curve["maturity_years"].isin([0, 1, 2, 5, 10, 20, 30])]
    selected.to_csv(output / "synthetic_selected_maturities.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 3.4), layout="constrained")
    ax.plot(
        maturity,
        curve["spot_rate_decimal"] * 100,
        color="#173a59",
        linewidth=2.2,
        label="Zero-coupon spot",
    )
    ax.plot(
        maturity,
        curve["forward_rate_continuous_decimal"] * 100,
        color="#b27730",
        linewidth=1.7,
        label="Instantaneous forward",
    )
    ax.set(
        xlabel="Maturity (years)",
        ylabel="Continuous annualised rate (%)",
        title="Synthetic example - no country or market observation",
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False)
    fig.savefig(output / "synthetic_curve.png", dpi=220)
    plt.close(fig)

    artifacts = [
        "synthetic_curve.csv",
        "synthetic_selected_maturities.csv",
        "synthetic_curve.png",
    ]
    metadata = {
        "data_kind": "synthetic",
        "country": None,
        "observation_date": None,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": "Nelson-Siegel-Svensson",
        "parameters": asdict(parameters),
        "rate_unit": "decimal",
        "tau_and_maturity_unit": "years",
        "native_compounding": "continuous",
        "validation_status": "mathematical_tests_only; synthetic_example",
        "model_sha256": sha256(
            (
                Path(__file__).resolve().parents[1] / "yieldcurves/svensson.py"
            ).read_bytes()
        ).hexdigest(),
        "artifacts": {
            name: sha256((output / name).read_bytes()).hexdigest() for name in artifacts
        },
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Synthetic example saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Synthetic output directory.")
    main(parser.parse_args().output_dir)
