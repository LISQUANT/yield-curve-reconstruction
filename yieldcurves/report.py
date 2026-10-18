"""A research note generated from one reconstruction run."""

from io import BytesIO
import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, Table, TableStyle
from svglib.svglib import svg2rlg


def write_report(output, summary, curves, validations):
    output = Path(output)
    fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    for name, file in [("Research", "DejaVuSerif.ttf"),
                       ("Research-Bold", "DejaVuSerif-Bold.ttf"),
                       ("Research-Italic", "DejaVuSerif-Italic.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    pdfmetrics.registerFontFamily("Research", normal="Research", bold="Research-Bold",
                                  italic="Research-Italic", boldItalic="Research-Bold")
    red = colors.HexColor("#800020")
    styles = {
        "body": ParagraphStyle("body", fontName="Research", fontSize=9.5,
                               leading=13.5, spaceAfter=8),
        "title": ParagraphStyle("title", fontName="Research", fontSize=22,
                                leading=27, spaceAfter=10),
        "heading": ParagraphStyle("heading", fontName="Research-Bold", fontSize=13,
                                  leading=17, spaceBefore=8, spaceAfter=9, textColor=red),
        "small": ParagraphStyle("small", fontName="Research", fontSize=8,
                                leading=11, spaceAfter=6),
        "subtitle": ParagraphStyle("subtitle", fontName="Research", fontSize=12,
                                   leading=16, spaceAfter=12),
        "caption": ParagraphStyle("caption", fontName="Research-Italic", fontSize=8,
                                  leading=11, spaceAfter=8),
    }
    story = []

    def paragraph(text, style="body"):
        story.append(Paragraph(text, styles[style]))

    def equation(text):
        buffer = BytesIO()
        with matplotlib.rc_context({"mathtext.fontset": "stix", "svg.fonttype": "path"}):
            math_to_image("$" + text + "$", buffer, format="svg",
                          prop=FontProperties(size=13))
        drawing = svg2rlg(BytesIO(buffer.getvalue()))
        factor = min(1, 475 / drawing.width)
        drawing.scale(factor, factor)
        drawing.width *= factor
        drawing.height *= factor
        drawing.hAlign = "CENTER"
        story.extend([Spacer(1, 5), drawing, Spacer(1, 12)])

    def figure(name, width=475):
        drawing = svg2rlg(str(output / "figures" / (name + ".svg")))
        scale = width / drawing.width
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        story.append(drawing)

    def table(rows, widths):
        content = [[Paragraph(escape(str(value)), styles["small"]) for value in row]
                   for row in rows]
        tab = Table(content, colWidths=widths, hAlign="LEFT")
        tab.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.black),
            ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.extend([tab, Spacer(1, 10)])

    date = summary["observation_date"]
    paragraph("Sovereign Yield Curve Reconstruction", "title")
    paragraph("Nelson-Siegel-Svensson Framework", "subtitle")
    paragraph(f"Observation date: {date} | Cutoff: {summary['requested_date']}", "small")
    paragraph("A yield curve shows how interest rates change with maturity. We reconstruct "
              "US and German zero-coupon curves from parameters published by the Federal "
              "Reserve and Bundesbank, and compare the calculated rates with their published "
              "references. For Portugal, six daily Treasury benchmark yields are used to fit "
              "a separate, indicative Nelson-Siegel curve over 2–10 years.")
    paragraph("The procedure is straightforward: obtain the published observations, "
              "evaluate the parametric curve across maturities, check the reconstruction "
              "against the original data, and save the tables and figures. The Portuguese "
              "fit smooths bond yields rather than reconstructing zero-coupon rates.")
    paragraph("1. Method and mathematical framework", "heading")
    paragraph("Svensson describes the spot rate at maturity t using six parameters. "
              "β<sub>0</sub> sets the long-run level and β<sub>1</sub> adjusts the short end. "
              "β<sub>2</sub> and β<sub>3</sub> shape the curve, while τ<sub>1</sub> and "
              "τ<sub>2</sub> determine where those changes occur. Betas are decimal "
              "rates; maturities and positive τ parameters are measured in years.")
    equation(r"y(t)=\beta_0+\beta_1 L(t/\tau_1)+\beta_2 C(t/\tau_1)+\beta_3 C(t/\tau_2)")
    equation(r"L(x)=\frac{1-e^{-x}}{x},\qquad C(x)=L(x)-e^{-x}")
    paragraph("Once the six parameters are known, the formula returns a spot rate "
              "for any chosen maturity. This reproduces an already fitted curve; "
              "it does not estimate the parameters from individual bond prices.")
    equation(r"y(0)=\beta_0+\beta_1,\qquad \lim_{t\to\infty}y(t)=\beta_0")
    paragraph("At zero maturity the loadings are evaluated by their limits. Near zero, "
              "expm1 and a short series expansion avoid cancellation. Percentage betas "
              "are divided by 100; taus are never rescaled.")
    paragraph("Discounting and forward rates", "heading")
    paragraph("Let y<sub>c</sub> denote a continuously compounded spot rate and "
              "y<sub>a</sub> an effective annual spot rate. The discount factor for a unit "
              "payment and the instantaneous forward rate satisfy")
    equation(r"P(0,t)=e^{-t y_c(t)}=(1+y_a(t))^{-t},\qquad y_c(t)=\log(1+y_a(t))")
    equation(r"f(0,t)=-\frac{\mathrm{d}}{\mathrm{d}t}\log P(0,t)=y_c(t)+t\,y_c'(t)")
    paragraph("For native annual parameters the forward calculation uses "
              "log(1+y<sub>a</sub>) + t y'<sub>a</sub>/(1+y<sub>a</sub>). "
              "Converting beta coefficients individually would be incorrect. Negative "
              "rates and discount factors above one are allowed, provided annual rates "
              "remain above minus 100 percent. Forward rates include risk premia and "
              "are not pure forecasts of future policy rates.")
    paragraph("The US source publishes continuously compounded rates; the German "
              "reference uses effective annual rates. Comparisons use each source's "
              "native convention, while cross-country figures use continuous rates.", "small")

    story.append(PageBreak())
    paragraph("2. Reconstructed curves", "heading")
    rows = [["Country", "References passing", "Max error (bp)", "RMSE (bp)"]]
    for country, stats in summary["validation"].items():
        rows.append([country, f"{stats['passed_count']}/{stats['reference_count']}",
                     f"{stats['max_absolute_error_bp']:.6f}", f"{stats['rmse_bp']:.6f}"])
    table(rows, [80, 145, 125, 125])
    paragraph("Table 1. Reconstruction errors against published zero-coupon rates.", "caption")
    if not summary["validation_passed"]:
        paragraph("One published rate falls just outside the rounding margin. "
                  "We keep this difference in the results and look at it "
                  "more closely on the next page.", "small")
    figure("comparison", 465)
    paragraph("Figure 1. Published-parameter reconstructions in continuously compounded annual rates. "
              "Only the 1-30 year maturities have published-rate comparisons; the segment "
              "below one year is model extrapolation. USD and EUR curves are different "
              "currency markets: their difference is not a sovereign credit spread.", "caption")

    story.append(PageBreak())
    paragraph("3. Numerical validation", "heading")
    figure("validation", 470)
    paragraph("Figure 2. Native-convention spot curves and signed reconstruction errors. "
              "Dotted lines show the rounding allowance; crosses identify exceptions. "
              "The error panels use different vertical scales.", "caption")
    paragraph("Each comparison uses the same country, date, maturity and compounding "
              "convention. Signed errors are 10,000 times model minus published decimal "
              "rates. The Fed CSV prints spots to four decimal places in percent; the "
              "Bundesbank CSV prints two. Assuming nearest rounding gives half-step "
              "allowances of 0.005 bp and 0.5 bp, respectively. A conservative bound for "
              "rounding the parameter tokens and a 10<super>-9</super> bp numerical "
              "allowance are added separately. Neither is fitted to the residuals.")
    for country, validation in validations.items():
        failures = validation.loc[~validation.within_tolerance]
        for row in failures.itertuples():
            paragraph(f"{country}, {row.maturity_years:g} year: reconstructed "
                      f"{row.spot_rate_decimal_model * 100:.8f}% versus published "
                      f"{row.spot_rate_decimal_official * 100:.4f}%. The signed error is "
                      f"{row.error_bp:.6f} bp against an allowance of {row.tolerance_bp:.6f} bp. "
                      "This is not explained by the stated rounding bound. Source revisions "
                      "or an additional calculation convention require investigation; no "
                      "cause has been established.", "small")
    history = summary.get("german_rounding_history")
    if history:
        paragraph(f"To look into the German difference, we checked "
                  f"{history['observations']:,} rates across {history['dates']} "
                  f"dates. Rounding directly to two decimals matches "
                  f"{history['direct_matches']:,} published values. Rounding "
                  f"first to three decimals and then to two matches "
                  f"{history['double_matches']:,}, leaving "
                  f"{history['double_unexplained']} unmatched. This suggests "
                  "that an extra rounding step may be involved in publication. "
                  "The Bundesbank has not confirmed it, so the original "
                  "validation and its tolerances remain unchanged.", "small")
    paragraph("This comparison tells us how closely we reproduce the published "
              "curves. It does not tell us how well the underlying model fits "
              "individual bonds or whether it can predict future rates.", "small")
    story.append(PageBreak())
    paragraph("4. Data and empirical interpretation", "heading")
    paragraph("United States. The Federal Reserve's G\u00fcrkaynak, Sack and Wright nominal "
              "Treasury dataset supplies the six parameters and SVENY references. It "
              "covers off-the-run coupon securities and is a staff research product, "
              "not an official Board statistical release. A preserved official CSV is "
              "used when direct downloading returns HTTP 403.")
    paragraph("Germany. The Bundesbank BBSIS API supplies six daily parameter series "
              "and 30 daily zero-coupon spot series for listed Federal securities. "
              "ZST spot series are used; ZAR coupon-bearing yields and Pfandbrief "
              "curves are excluded. Native annual compounding follows the Bundesbank "
              "methodology. The API's published precision is preserved in the raw files.")
    latest = summary["source_last_dates"]
    if latest['DE'] is None:
        paragraph(f"The saved US data end on {latest['US']}. No usable German snapshot "
                  "was available for this run, so no German comparison is presented.")
    else:
        paragraph(f"The saved US and German data end on {latest['US']} and {latest['DE']}, "
                  f"respectively. The selected date, {date}, is the latest complete common "
                  "observation on or before the cutoff. Dates are selected before inspecting "
                  "fit quality; there is no forward filling or substitution of a better-fitting day.")
    rows = [["Market", "1Y spot (%)", "10Y spot (%)", "30Y spot (%)", "10Y-2Y (bp)"]]
    for country, curve in curves.groupby("country"):
        points = curve.set_index("maturity_years").spot_rate_continuous_decimal
        rows.append([country, f"{points[1] * 100:.3f}", f"{points[10] * 100:.3f}",
                     f"{points[30] * 100:.3f}", f"{(points[10]-points[2])*10000:.2f}"])
    table(rows, [70, 95, 100, 100, 110])
    paragraph("Table 2. Model-implied continuously compounded spots. The slope compares "
              "two maturities within each country; it is not a cross-currency spread.", "caption")
    paragraph("Interpretation", "heading")
    paragraph("Using the same compounding convention makes it easier to compare the "
              "shape and slope of the US and German curves. But they refer to "
              "different markets and currencies, so the gap between them is not "
              "a direct measure of sovereign credit risk. We show Portugal "
              "separately because its observations are bond yields rather than "
              "zero-coupon rates.")
    paragraph("A small source bundle accompanies the code: one unaltered Fed date row "
              "with its original preamble and header, the 36 original German series files, "
              "and six BPstat JSON-stat replies. Source URLs, retrieval times and checksums "
              "are retained. The Fed excerpt records its full-file parent hash and the "
              "selection of one date; it is not represented as the complete historical file.")
    story.append(PageBreak())
    paragraph("5. Portugal: indicative benchmark yields", "heading")
    benchmark = summary.get("portugal_benchmarks", {"available": False})
    paragraph("For Portugal, we use BPstat yields for six government-bond maturities, "
              "from two to ten years. These bonds pay coupons, so their yields "
              "are not the same as zero-coupon spot rates. We fit a separate "
              "Nelson-Siegel line to show the overall shape of the yields on that date.")
    if benchmark["available"]:
        drawing = svg2rlg(str(output / "PT_benchmarks/benchmark_yields.svg"))
        factor = 475 / drawing.width
        drawing.scale(factor, factor)
        drawing.width *= factor
        drawing.height *= factor
        story.append(drawing)
        paragraph(f"Figure 3. Observed on {escape(benchmark['observation_date'])}; "
                  f"{benchmark['observation_count']} tenors. Display method: "
                  f"{escape(benchmark['method'])}. Display residual RMSE: "
                  f"{benchmark['display_rmse_bp']:.4f} bp. "
                  + escape(benchmark["residual_note"]), "small")
        paragraph("Source: Banco de Portugal, BPstat daily series 12099454–12099459; "
                  "underlying source LSEG, metric Average, unit percent, status F. "
                  "Original replies and acquisition timestamps accompany the exported observations. "
                  "The fitted line is an LIS calculation, not a Banco de Portugal zero-coupon curve.", "small")
        import pandas as pd
        observations = pd.read_csv(output / "PT_benchmarks/observations.csv")
        table([["Tenor (years)"] + [f"{t:g}" for t in observations.maturity_years],
               ["Observed yield (%)"] + [f"{y:.2f}" for y in observations.yield_percent]],
              [145] + [55] * len(observations))
        paragraph("Table 3. Daily average Portuguese Treasury benchmark yields.", "caption")
    else:
        paragraph("No benchmark observations were included in this run: "
                  + escape(benchmark.get("reason", "No verified snapshot.")), "body")
        paragraph("Investing.com historical yield tables were identified as a possible "
                  "source. Its published terms restrict automated extraction and reuse; "
                  "permission for the intended research distribution has not been "
                  "established. No numerical Portuguese approximation is presented. "
                  "A permitted export is required before producing this panel.")
    paragraph("We choose the Nelson-Siegel parameters to make the fitted line as "
              "close as possible to the six observed yields. Each maturity receives "
              "the same weight, and we check how much the fit changes when a middle "
              "maturity is left out. With only six observations, a full six-parameter "
              "Svensson fit would be hard to assess reliably. The simpler model "
              "is more useful here, provided it passes the stability checks.")
    equation(r"\min_{\theta}\sum_i [100(g(T_i;\theta)-q_i)]^2")
    paragraph("In the equation, q is the observed bond yield and g is the "
              "fitted yield at the same maturity, both in percent. The line "
              "describes the maturities for which we have data, from 2 to 10 "
              "years. We should not use it to calculate discount factors or "
              "forward rates as though it were a zero-coupon curve.", "small")
    story.append(PageBreak())
    paragraph("6. Reproducibility and limitations", "heading")
    paragraph("The workflow checks the input files and keeps a record of where "
              "each source came from and when it was downloaded. The calculations, "
              "figures and PDF are handled separately, which makes it easier to "
              "check how each result was produced.")
    paragraph("Install the project, then run:")
    paragraph("python scripts/run_yield_curves.py --offline --date 2026-10-02", "small")
    paragraph("This command uses the saved data from 2 October 2026. You can "
              "select other dates with --date or try to download newer data with "
              "--refresh. Each run saves the tables, figures and PDF together. "
              "The program may finish with exit code 2 because one German "
              "rate is just outside the rounding margin. The files are still "
              "created; the code simply makes that difference visible.")
    paragraph("The automated tests check the curve calculations, rate conventions, "
              "observation dates and input files. Tests using made-up examples "
              "are separate from the actual market data. The latest executed "
              "checks are recorded in docs/verification.json.")
    paragraph("There are a few limits to what we can conclude. We worked "
              "with one observation date, so the figures show what the curves "
              "looked like then, not how they change over time or how well they "
              "forecast future rates. The US and German curves also come from "
              "different markets and currencies. Comparing their shapes is useful, "
              "but the difference between them is not a pure credit spread. "
              "Finally, we keep the small German validation exception visible "
              "because the suggested rounding explanation has not been confirmed.")
    pt = summary.get("portugal_calibration")
    if pt is None:
        paragraph("For Portugal, we would need one more step to obtain a zero-coupon "
                  "curve comparable to the US and German ones: reliable prices "
                  "for individual bonds and their coupon payments. The project "
                  "already contains code for that calculation, but we have not "
                  "used it here because a suitable bond-price dataset has not "
                  "been verified. For now, the BPstat fit shows the shape of "
                  "Portuguese bond yields, not zero-coupon rates.", "small")
    else:
        paragraph(f"A separate imported panel of {pt['bond_count']} Portuguese bonds was "
                  f"fitted at settlement {pt['settlement_date']}. Dirty-price RMSE is "
                  f"{pt['price_rmse']:.6f} per 100 face value. This is an in-sample price "
                  "fit, not official spot validation. Settlement-based curves and diagnostics "
                  "are exported under PT/. " + escape(" ".join(pt["warnings"])), "small")
    paragraph("References", "heading")
    references = [
        ("G\u00fcrkaynak, R. S., Sack, B. and Wright, J. H. (2006). The U.S. Treasury Yield Curve: 1961 to the Present. FEDS 2006-28.",
         "https://www.federalreserve.gov/pubs/feds/2006/200628/index.html"),
        ("Federal Reserve Board. Nominal yield curve data and CSV download.",
         "https://www.federalreserve.gov/data/nominal-yield-curve.htm"),
        ("Schich, S. T. (1997). Estimating the German term structure. Deutsche Bundesbank Discussion Paper 4/97, section II.1 (annual compounding).",
         "https://www.bundesbank.de/resource/blob/622394/f917db9f2fe9168243f272b535d67858/mL/1997-10-01-dkp-04-data.pdf"),
        ("Deutsche Bundesbank. Daily term structure on listed Federal securities; BBSIS series and API.",
         "https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields/daily-term-structure-on-listed-federal-securities-651570"),
        ("Banco de Portugal. BPstat daily Treasury yields, series 12099454–12099459; source LSEG.",
         "https://bpstat.bportugal.pt/serie/12099456"),
        ("Banco de Portugal. BPstat legal notice: source attribution and disclosure of modifications.",
         "https://bpstat.bportugal.pt/avisos-legais"),
        ("IGCP (2026). Public Debt Monthly Bulletin, March, page 1 (secondary-market yields and auctions).",
         "https://www.igcp.pt/sites/default/files/2026-03/BM_mar26.pdf"),
    ]
    for i, (title, url) in enumerate(references, 1):
        paragraph(f'{i}. {escape(title)} <link href="{escape(url)}" color="#800020">Source</link>.', "small")

    def page_frame(canvas, doc):
        canvas.saveState()
        canvas.setFont("Research-Bold", 9)
        canvas.setFillColor(red)
        canvas.drawString(55, A4[1] - 32, "LIS | Quantitative Research")
        canvas.setStrokeColor(red)
        canvas.setLineWidth(0.5)
        canvas.line(55, A4[1] - 40, A4[0] - 55, A4[1] - 40)
        canvas.restoreState()

    document = SimpleDocTemplate(str(output / "research_note.pdf"), pagesize=A4,
                                 leftMargin=55, rightMargin=55, topMargin=57,
                                 bottomMargin=48, invariant=1, pageCompression=1,
                                 title="Sovereign Yield Curve Reconstruction",
                                 author="LIS | Quantitative Research")
    document.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
    (output / "report_inputs.json").write_text(json.dumps({
        "observation_date": date, "validation": summary["validation"],
        "source_last_dates": summary["source_last_dates"],
        "portugal_benchmarks": summary.get("portugal_benchmarks"),
        "german_rounding_history": summary.get("german_rounding_history"),
    }, indent=2))
