# Synthetic Market Data Methodology

The synthetic market is generated from explicit category profiles and regime parameters rather than independent random columns. Every category defines price ranges, COGS and fulfillment ratios, shipping profiles, return-rate baselines, regulatory baselines, and seasonality. Ten market regimes (emerging, growing, mature, saturated, declining, seasonal, high-margin-niche, high-demand-high-risk, low-competition-niche, commodity) influence search volume, growth, seller count, review depth, CPC, margin, differentiation, and risk.

Derived scores use documented formulas. Demand combines volume, growth, and seasonality. Competition combines seller count, review depth, CPC, and concentration. Risk combines physical product flags, return rate, regulatory exposure, and saturation. Gross margin equals selling price minus COGS and fulfillment cost. The latent opportunity score is a fixed weighted combination of demand, margin, differentiation, competition, and risk.

The latent opportunity and risk scores are hidden from research agents. Only the benchmark evaluator reads them. These results evaluate Agent behavior inside a deterministic synthetic environment; they are not claims about real product-market performance.
