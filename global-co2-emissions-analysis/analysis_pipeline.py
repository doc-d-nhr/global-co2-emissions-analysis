import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 130

conn = sqlite3.connect("co2_emissions.db")

# ---------- 1. Global CO2 trend over time ----------
world = pd.read_sql("SELECT year, co2 FROM co2_emissions WHERE country='World' AND co2 IS NOT NULL", conn)
fig, ax = plt.subplots(figsize=(11, 6))
ax.plot(world.year, world.co2, color="#b23a48", linewidth=2)
ax.fill_between(world.year, world.co2, alpha=0.15, color="#b23a48")
ax.set_title("Global CO2 Emissions, 1900-2024", fontsize=14, fontweight="bold")
ax.set_ylabel("CO2 Emissions (million tonnes)")
ax.set_xlabel("Year")
ax.set_xlim(1900, 2024)
# mark a couple of notable dips
for yr, label in [(1929, "Great Depression"), (2009, "Financial Crisis"), (2020, "COVID-19")]:
    row = world[world.year == yr]
    if not row.empty:
        ax.annotate(label, (yr, row.co2.values[0]), textcoords="offset points",
                    xytext=(0, -35), ha="center", fontsize=8.5, color="#444",
                    arrowprops=dict(arrowstyle="->", color="#888", lw=0.8))
plt.tight_layout()
plt.savefig("chart_global_trend.png")
plt.close()

# ---------- 2. Top 10 emitters 2023 ----------
top10 = pd.read_sql("""
    SELECT country, co2 FROM co2_emissions
    WHERE is_country=1 AND year=2023 AND co2 IS NOT NULL
    ORDER BY co2 DESC LIMIT 10
""", conn)
fig, ax = plt.subplots(figsize=(9.5, 6.5))
bars = ax.barh(top10.country[::-1], top10.co2[::-1], color=sns.color_palette("crest", 10))
ax.set_title("Top 10 CO2 Emitters, 2023", fontsize=14, fontweight="bold")
ax.set_xlabel("CO2 Emissions (million tonnes)")
for b in bars:
    ax.annotate(f"{b.get_width():,.0f} Mt", (b.get_width(), b.get_y()+b.get_height()/2),
                va="center", ha="left", fontsize=9, xytext=(5,0), textcoords="offset points")
plt.tight_layout()
plt.savefig("chart_top10_emitters.png")
plt.close()

# ---------- 3. Per-capita vs total (bubble = population) for major economies ----------
major = pd.read_sql("""
    SELECT country, co2, co2_per_capita, population FROM co2_emissions
    WHERE is_country=1 AND year=2023 AND population > 20000000
    AND co2 IS NOT NULL AND co2_per_capita IS NOT NULL
""", conn)
fig, ax = plt.subplots(figsize=(10, 7))
sizes = (major.population / major.population.max()) * 3000 + 30
sc = ax.scatter(major.co2, major.co2_per_capita, s=sizes, alpha=0.55, c=major.co2_per_capita,
                 cmap="rocket_r", edgecolors="white", linewidth=0.6)
for _, r in major.nlargest(12, "co2").iterrows():
    ax.annotate(r.country, (r.co2, r.co2_per_capita), fontsize=8, xytext=(5, 3), textcoords="offset points")
ax.set_xscale("log")
ax.set_title("Total vs Per-Capita Emissions, 2023\n(bubble size = population, countries >20M only)",
             fontsize=13, fontweight="bold")
ax.set_xlabel("Total CO2 Emissions, log scale (million tonnes)")
ax.set_ylabel("CO2 per Capita (tonnes)")
plt.tight_layout()
plt.savefig("chart_total_vs_percapita.png")
plt.close()

# ---------- 4. Fuel mix shift for big 5 (2000 vs 2023) ----------
big5 = pd.read_sql("""
    WITH b AS (SELECT country FROM co2_emissions WHERE is_country=1 AND year=2023 AND co2 IS NOT NULL ORDER BY co2 DESC LIMIT 5)
    SELECT c.country, c.year, c.coal_co2, c.oil_co2, c.gas_co2
    FROM co2_emissions c JOIN b ON c.country=b.country
    WHERE c.year IN (2000, 2023)
""", conn)
big5m = big5.melt(id_vars=["country","year"], value_vars=["coal_co2","oil_co2","gas_co2"],
                   var_name="fuel", value_name="co2")
big5m["fuel"] = big5m["fuel"].str.replace("_co2","").str.title()
fig, ax = plt.subplots(figsize=(12, 6.5))
sns.barplot(data=big5m, x="country", y="co2", hue="fuel", ax=ax, palette=["#3a3a3a", "#b23a48", "#4c72b0"])
for i, c in enumerate(big5.country.unique()):
    pass
ax.set_title("Fuel Mix of Emissions — Top 5 Emitters, 2000 vs 2023 (stacked by year not shown, grouped)",
             fontsize=12.5, fontweight="bold")
ax.set_ylabel("CO2 Emissions (million tonnes)")
ax.set_xlabel("")
plt.tight_layout()
plt.savefig("chart_fuel_mix_big5.png")
plt.close()

# ---------- 5. Decade totals ----------
decades = pd.read_sql("""
    SELECT (year/10)*10 AS decade, SUM(co2) AS total_co2
    FROM co2_emissions WHERE is_country=1 AND co2 IS NOT NULL AND year>=1900
    GROUP BY decade ORDER BY decade
""", conn)
fig, ax = plt.subplots(figsize=(11, 6))
bars = ax.bar(decades.decade.astype(str)+"s", decades.total_co2, color=sns.color_palette("crest", len(decades)))
ax.set_title("Global CO2 Emissions by Decade", fontsize=14, fontweight="bold")
ax.set_ylabel("Total CO2 (million tonnes, summed across countries/years)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("chart_decades.png")
plt.close()

# ---------- 6. Who's cutting emissions the most since 2005 (developed economies context) ----------
cutters = pd.read_sql("""
    WITH y2005 AS (SELECT country, co2 AS co2_2005 FROM co2_emissions WHERE is_country=1 AND year=2005 AND co2>20),
    y2023 AS (SELECT country, co2 AS co2_2023 FROM co2_emissions WHERE is_country=1 AND year=2023)
    SELECT a.country, a.co2_2005, b.co2_2023,
    ROUND((b.co2_2023-a.co2_2005)/a.co2_2005*100,1) AS pct_chg
    FROM y2005 a JOIN y2023 b ON a.country=b.country
    WHERE b.co2_2023 < a.co2_2005 ORDER BY pct_chg ASC LIMIT 12
""", conn)
fig, ax = plt.subplots(figsize=(10, 6.5))
bars = ax.barh(cutters.country[::-1], cutters.pct_chg[::-1], color="#2f6f4f")
ax.set_title("Biggest CO2 Cuts Since 2005 (countries emitting >20 Mt in 2005)", fontsize=12.5, fontweight="bold")
ax.set_xlabel("% Change in CO2, 2005 → 2023")
for b in bars:
    ax.annotate(f"{b.get_width():.1f}%", (b.get_width(), b.get_y()+b.get_height()/2),
                va="center", ha="right" if b.get_width()<0 else "left", fontsize=9,
                xytext=(-5 if b.get_width()<0 else 5, 0), textcoords="offset points", color="white" if b.get_width()<0 else "black")
plt.tight_layout()
plt.savefig("chart_biggest_cutters.png")
plt.close()

conn.close()
print("Charts generated.")
