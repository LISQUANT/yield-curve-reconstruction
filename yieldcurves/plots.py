"""Plot reconstructed curves and source-validation errors.

US-only until the Bundesbank source and latest common date are implemented.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_fed_curve(curve, validation, target):
    """Plot native continuous USD spots and same-date SVENY residuals."""
    years = curve.maturity_years
    date = curve.observation_date.iloc[0]
    fig, (ax, errors) = plt.subplots(2, 1, figsize=(9, 6), layout="constrained")
    ax.plot(years, curve.spot_rate_decimal * 100, label="Reconstructed NSS spot")
    ax.scatter(validation.maturity_years,
               validation.spot_rate_decimal_official * 100,
               s=15, color="#b27730", label="Published SVENY")
    ax.set(title=f"US Treasury off-the-run curve | {date} | USD",
           ylabel="Continuous spot rate (% p.a.)")
    ax.axvspan(0, 1, color="grey", alpha=0.12, label="Below 1Y: extrapolation")
    ax.legend(frameon=False)
    errors.bar(validation.maturity_years, validation.error_bp, color="#173a59")
    errors.plot(validation.maturity_years, validation.tolerance_bp,
                "--", color="#b27730", label="Rounding tolerance")
    errors.plot(validation.maturity_years, -validation.tolerance_bp,
                "--", color="#b27730")
    errors.set(xlabel="Maturity (years)", ylabel="Model minus SVENY (bp)")
    errors.legend(frameon=False)
    fig.suptitle("Federal Reserve GSW staff research data | Not synthetic inputs")
    fig.savefig(target, dpi=180)
    plt.close(fig)
