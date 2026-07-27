"""
Load the OWID global CO2 & energy dataset into a proper SQLite database
so the project can be queried with real SQL instead of just pandas.

Source: Our World in Data, https://github.com/owid/co2-data
(pulled straight from their GitHub repo )
"""
import pandas as pd
import sqlite3

df = pd.read_csv("owid-co2-data.csv")

# OWID mixes real countries in with continent/income-group aggregates
# (e.g. "World", "Africa", "European Union (27)", "High-income countries").
# Both are useful, so I'm keeping everything but adding a flag so queries
# can easily filter to actual countries only.
region_like = df["iso_code"].isna() | df["iso_code"].str.startswith("OWID_", na=False)
df["is_country"] = ~region_like

# trim to the columns that actually matter for this project instead of
# hauling around all 79 OWID columns (a lot of them are extremely sparse
# sub-breakdowns like "other_industry_co2" that aren't useful here)
keep_cols = [
    "country", "year", "iso_code", "is_country", "population", "gdp",
    "co2", "co2_per_capita", "co2_growth_prct", "cumulative_co2",
    "share_global_co2", "coal_co2", "oil_co2", "gas_co2", "cement_co2",
    "flaring_co2", "methane", "nitrous_oxide", "total_ghg",
    "energy_per_capita", "energy_per_gdp", "primary_energy_consumption",
    "temperature_change_from_co2", "temperature_change_from_ghg",
    "land_use_change_co2",
]
df = df[keep_cols].copy()

conn = sqlite3.connect("co2_emissions.db")
df.to_sql("co2_emissions", conn, if_exists="replace", index=False)

# a couple of indexes since this will get queried by country and by year a lot
conn.execute("CREATE INDEX idx_country ON co2_emissions(country)")
conn.execute("CREATE INDEX idx_year ON co2_emissions(year)")
conn.execute("CREATE INDEX idx_country_year ON co2_emissions(country, year)")
conn.commit()

n_rows = conn.execute("SELECT COUNT(*) FROM co2_emissions").fetchone()[0]
n_countries = conn.execute("SELECT COUNT(DISTINCT country) FROM co2_emissions WHERE is_country=1").fetchone()[0]
yr_range = conn.execute("SELECT MIN(year), MAX(year) FROM co2_emissions").fetchone()
print(f"Loaded {n_rows} rows into co2_emissions.db")
print(f"{n_countries} real countries, years {yr_range[0]}-{yr_range[1]}")
conn.close()
