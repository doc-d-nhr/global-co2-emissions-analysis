# Who's Actually Emitting the World's CO2? (And Who's Cutting Back?)

A SQL + Python project using real data from [Our World in Data](https://github.com/owid/co2-data) — 218 countries, 1750 to 2024, pulled straight from their GitHub repo.

## Why this dataset

I wanted something that wasn't another Netflix-titles-and-Titanic-CSV project, and something where SQL would actually be *necessary* rather than decorative — where you genuinely need window functions and CTEs to answer the interesting questions instead of just doing `df.groupby()` in five seconds. Global emissions data turned out to be perfect for that: you want running totals, year-over-year growth, "top N per group per year," and before/after comparisons, all of which read a lot more naturally in SQL than in pandas once you're past the basics.

I also just find the questions genuinely interesting — not "which brand of car is more expensive" interesting, but "is the UK's emissions drop real policy success or just deindustrialization" interesting. More on that below.

## What's in here

- `owid-co2-data.csv` — the raw file as downloaded from OWID's GitHub (79 columns, everything they publish)
- `00_build_database.py` — loads it into a proper SQLite database (`co2_emissions.db`), trims to the ~24 columns actually used here, adds an `is_country` flag since OWID mixes real countries in with continent/income-group rollups in the same table (more on that gotcha below)
- `queries.sql` — 13 SQL queries, commented, covering CTEs, window functions (RANK, LAG, running SUM() OVER), subqueries, joins, and HAVING — all tested and confirmed working against the actual database, not just written and hoped for
- `analyze.py` — Python/matplotlib layer for the visuals, run against the same SQLite DB
- 6 chart PNGs
- this README

## The gotcha that cost me twenty minutes

First pass at the top-emitters query, "Asia" and "High-income countries" showed up in my top 10 list next to China and the US. OWID's CSV includes continent and income-group aggregates as rows in the *same table*, using the same `country` column, distinguished only by a slightly different ISO code convention (`OWID_ASI` instead of a real 3-letter code, or just a blank ISO code entirely). Nothing in the column names flags this. I added an `is_country` boolean during the load step specifically so every query downstream doesn't have to remember this quirk — but it's the kind of thing that's genuinely easy to miss and would quietly wreck any "top country" ranking if you didn't catch it. Worth checking any dataset for something similar before trusting a groupby.

## What the data actually shows

**China, the US, and India are the top 3 emitters by a wide margin** — China alone is ~32% of global CO2 in 2023. But per-capita tells a different story: Saudi Arabia, Canada, and the US are far higher per person than China, and India (despite being #3 in total) is way down the per-capita list. Total emissions and per-capita emissions are basically two different rankings, and conflating them is a common mistake in how this topic gets talked about casually.

**Some countries are genuinely cutting emissions, not just talking about it.** Using 2005 as a baseline (common Kyoto/Paris-era reference point), the UK is down ~46%, Denmark ~44%, Finland ~44%. That's not noise — it's a real, sustained trend, mostly driven by coal phase-out. I didn't dig into *why* for every country here (that's really an energy-policy research project on its own), but the SQL makes it trivial to pull the list and go investigate further.

**Growth is now concentrated in a different set of countries than the ones usually discussed.** Looking at 2014-2023 average annual growth, the fastest-growing emitters aren't China or India anymore — they're Laos, Mozambique, Cambodia, Tajikistan: smaller, lower-income economies growing off a small base. This doesn't mean they're "the problem" (their absolute totals are tiny), but it's a useful reminder that the next decade's emissions story may not look like the last one.

**Fuel mix matters as much as total volume.** For the current top 5 emitters, comparing 2000 vs 2023 coal/oil/gas shares shows meaningfully different transition paths — some are shifting hard toward gas, others are still coal-heavy. (Chart included; I didn't write this up exhaustively per-country since that's really its own report.)

## Honest limitations

- This is production, not consumption, emissions — a country that's offshored its manufacturing looks "cleaner" here than it might be on a consumption-adjusted basis. OWID has a `consumption_co2` column but it's ~90% missing for most country-years, so I didn't build analysis on top of it here — flagging it rather than pretending it doesn't exist.
- GDP coverage is ~70% missing across the full historical range, so the emissions-per-GDP query (Q10) is really only reliable for major economies in recent decades, which is why I scoped it that way rather than running it globally.
- "Biggest cutters since 2005" is a simple before/after comparison, not a trend line — a country could have dropped in 2023 specifically due to one unusual year rather than a real sustained decline. Worth a follow-up query checking multi-year trends before treating this list as gospel.

## If I kept going

- Pull in a population-weighted global average instead of using OWID's own "World" row, to double check Q9 isn't quietly biased by how they calculate it
- Multi-year trend lines instead of single before/after snapshots for the "biggest cutters" analysis
- A proper consumption-vs-production comparison for the subset of countries where OWID actually has both

---

**Data source:** Our World in Data, CO2 and Greenhouse Gas Emissions dataset — [github.com/owid/co2-data](https://github.com/owid/co2-data), downloaded 2026-07-27. OWID's data is itself compiled from the Global Carbon Project, so credit really goes further upstream than just OWID.
