"""Yield curves and published-rate comparisons."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({"font.family": "serif", "font.size": 10,
                            "axes.spines.top": False, "axes.spines.right": False,
                            "svg.hashsalt": "lis-yield-curves", "pdf.fonttype": 42})


def plot_fed_curve(curve, validation, target):
    """Plot the US curve and its differences from SVENY."""
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


def save_figure(fig, target):
    """Export the same figure as vector PDF/SVG and a preview PNG."""
    fig.savefig(target.with_suffix(".pdf"), bbox_inches="tight",
                metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(target.with_suffix(".svg"), bbox_inches="tight",
                metadata={"Date": None})
    fig.savefig(target.with_suffix(".png"), bbox_inches="tight", dpi=180)
    plt.close(fig)


def plot_benchmarks(observations, curve, target):
    fig, ax = plt.subplots(figsize=(6.4, 3.4), layout="constrained")
    ax.plot(curve.maturity_years, curve.yield_percent, color="#800020",
            label=curve.method.iloc[0].replace("_", " "))
    ax.scatter(observations.maturity_years, observations.yield_percent,
               color="black", s=18, zorder=3, label="Observed benchmark yields")
    ax.set(xlabel="Benchmark tenor (years)", ylabel="Yield (% p.a.)",
           xlim=(observations.maturity_years.min(), observations.maturity_years.max()),
           title="Portugal - indicative benchmark yields (not zero-coupon rates)\n"
                 + observations.observation_date.iloc[0])
    ax.legend(frameon=False, fontsize=8)
    save_figure(fig, target)


def plot_research(curves, validations, output):
    colors = {"US": "#213b50", "DE": "#800020"}
    names = {"US": "United States (USD)", "DE": "Germany (EUR)"}
    fig, axes = plt.subplots(2, 1, figsize=(6.4, 4.5), layout="constrained")
    dates = set(curves.observation_date)
    if len(dates) != 1:
        raise ValueError("Country comparison requires one common date.")
    date = next(iter(dates))
    for country, curve in curves.groupby("country", sort=True):
        for ax, column in zip(axes, ["spot_rate_continuous_decimal",
                                    "forward_rate_continuous_decimal"]):
            ax.plot(curve.maturity_years, curve[column] * 100,
                    label=names[country], color=colors[country],
                    linestyle="-" if country == "US" else "--")
            ax.grid(axis="y", alpha=0.15)
    axes[0].set(ylabel="Continuous spot (% p.a.)", title=f"Common date: {date}")
    axes[0].legend(frameon=False, fontsize=9)
    axes[1].set(ylabel="Continuous forward (% p.a.)", xlabel="Maturity (years)")
    save_figure(fig, output / "comparison")

    fig, axes = plt.subplots(2, len(validations), figsize=(6.4, 4.8),
                             squeeze=False, layout="constrained")
    for col, (country, validation) in enumerate(validations.items()):
        curve = curves.loc[curves.country == country]
        ax, error_ax = axes[:, col]
        convention = curve.native_compounding.iloc[0]
        ax.plot(curve.maturity_years, curve.spot_rate_decimal * 100,
                color=colors[country], label="NSS reconstruction")
        ax.scatter(validation.maturity_years,
                   validation.spot_rate_decimal_official * 100,
                   color="black", s=7, label="Published spots")
        ax.set(title=names[country], ylabel=f"{convention.title()} spot (% p.a.)")
        ax.legend(frameon=False, fontsize=7)
        error_ax.bar(validation.maturity_years, validation.error_bp,
                     color=colors[country], width=0.7)
        for sign in [-1, 1]:
            error_ax.plot(validation.maturity_years, sign * validation.tolerance_bp,
                          color="black", linestyle=":", linewidth=0.8)
        failed = validation.loc[~validation.within_tolerance]
        error_ax.scatter(failed.maturity_years, failed.error_bp,
                         color="#b22222", marker="x", zorder=4)
        error_ax.set(xlabel="Maturity (years)", ylabel="Model minus published (bp)")
    save_figure(fig, output / "validation")

    for country, curve in curves.groupby("country"):
        fig, ax = plt.subplots(figsize=(6.4, 3), layout="constrained")
        ax.plot(curve.maturity_years, curve.discount_factor, color=colors[country])
        ax.set(xlabel="Maturity (years)", ylabel="Discount factor",
               title=f"{names[country]} | {date}")
        save_figure(fig, output / f"discount_{country}")
