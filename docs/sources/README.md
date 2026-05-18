# Industry benchmark sources

The PDFs themselves are not committed to this repo (copyright restrictions + ~50MB total size). To reproduce, download them from the URLs below into this folder.

## Reports used

| Report | Publisher | Published | Local filename | Source URL |
|---|---|---|---|---|
| The State of Fashion 2026 | McKinsey & Co. + Business of Fashion | Feb 2026 | `the-state-of-fashion-2026_feb.pdf` | https://www.mckinsey.com/industries/retail/our-insights/state-of-fashion |
| D2C 3.0: The Next Big Wave In Indian Ecommerce, Report 2026 | Inc42 Datalabs | 2026 | `D2C-3.0-Ecommerce-report_Final.pdf` | https://inc42.com/reports/d2c-3-0-the-next-big-wave-in-indian-ecommerce-report-2026/ |
| Annual Report (Ministry of Textiles, Govt. of India) | Government of India | 2024-25 *(confirm year on cover)* | `textiles-ministry-annual-report.pdf` | https://texmin.gov.in/ |

## What each report contributes

- **McKinsey State of Fashion** — global context. Industry-wide return rates, supply chain disruption costs, lead time trends, consumer behavior shifts. Used as the world-context benchmark for the synthetic data layer.
- **Inc42 D2C 3.0** — India-specific D2C ecosystem data. Brand profiles, GMV, customer behavior, channel mix. The most directly relevant report for Snitch and the broader D2C menswear target segment.
- **Ministry of Textiles Annual Report** — granular Indian production-side data. Cluster-level activity (Tirupur, Bangalore, Ludhiana, Surat), exports by category, employment by region. Used to calibrate realistic vendor and lead-time distributions in the synthetic PO dataset.

## How these inform ThreadTrack

The synthetic purchase-order dataset generated in Phase 2 will use distributions calibrated to numbers extracted from these reports. Each cited benchmark in `docs/benchmarks.md` references one of the reports above with a page number.

---

*Sources retrieved 2026-05-19.*
