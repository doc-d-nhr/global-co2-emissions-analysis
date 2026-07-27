
-- Global CO2 & Energy Analysis — SQL Queries
-- Database: co2_emissions.db (SQLite)
-- Source data: Our World in Data (github.com/owid/co2-data)
--
-- Notes on the data before you run anything:
--   - `is_country` = 1 for actual countries, 0 for continent/income-group
--     rollups OWID includes in the same file (e.g. "World", "Africa",
--     "European Union (27)"). Almost every query below filters to
--     is_country = 1 unless it's explicitly comparing a country to a region.
--   - Coverage is much better after ~1950 and especially after ~1990 —
--     early years are dominated by a handful of industrialized countries
--     because that's genuinely who was emitting, not a data gap, but I've
--     restricted most queries to 1990+ anyway to keep comparisons fair.




-- Q1. Sanity check: how many countries actually have usable CO2 data in 2023?
SELECT COUNT(*) AS countries_with_2023_data
FROM co2_emissions
WHERE is_country = 1 AND year = 2023 AND co2 IS NOT NULL;



-- Q2. Top 15 emitters in the most recent year available (2023)

SELECT country, co2 AS co2_mt, co2_per_capita, share_global_co2
FROM co2_emissions
WHERE is_country = 1 AND year = 2023 AND co2 IS NOT NULL
ORDER BY co2 DESC
LIMIT 15;



-- Q3. Same top emitters, but ranked by per-capita emissions instead.
-- Filtering out tiny populations (<1M) so it's not just petro-states with
-- 400,000 people skewing the list.

SELECT country, population, co2, co2_per_capita
FROM co2_emissions
WHERE is_country = 1 AND year = 2023 AND population > 1000000 AND co2_per_capita IS NOT NULL
ORDER BY co2_per_capita DESC
LIMIT 15;



-- Q4. Window function: rank every country's emissions within its own year,
-- then pull out just the current top 10 (2023) with their rank.
-- (RANK() over PARTITION BY year -- classic "top N per group" pattern)

WITH ranked AS (
    SELECT
        country, year, co2,
        RANK() OVER (PARTITION BY year ORDER BY co2 DESC) AS emissions_rank
    FROM co2_emissions
    WHERE is_country = 1 AND co2 IS NOT NULL
)
SELECT * FROM ranked
WHERE year = 2023 AND emissions_rank <= 10
ORDER BY emissions_rank;



-- Q5. Year-over-year growth using LAG() -- for each of the top 6 current
-- emitters, show their CO2 total alongside the prior year's, and the
-- percent change. This is the kind of thing you'd otherwise need a
-- self-join for; LAG() makes it one pass.

WITH top6 AS (
    SELECT country FROM co2_emissions
    WHERE is_country = 1 AND year = 2023 AND co2 IS NOT NULL
    ORDER BY co2 DESC LIMIT 6
),
yoy AS (
    SELECT
        c.country, c.year, c.co2,
        LAG(c.co2) OVER (PARTITION BY c.country ORDER BY c.year) AS prev_year_co2
    FROM co2_emissions c
    JOIN top6 t ON c.country = t.country
    WHERE c.year BETWEEN 2018 AND 2023
)
SELECT
    country, year, co2, prev_year_co2,
    ROUND((co2 - prev_year_co2) / prev_year_co2 * 100, 2) AS pct_change_yoy
FROM yoy
WHERE prev_year_co2 IS NOT NULL
ORDER BY country, year;



-- Q6. Running total: cumulative emissions for the US since 1900, to see
-- how much of "cumulative_co2" (the OWID column) actually built up during
-- different eras. (SUM() OVER with an ORDER BY = running total)

SELECT
    year, co2,
    SUM(co2) OVER (ORDER BY year) AS running_total_co2
FROM co2_emissions
WHERE country = 'United States' AND year >= 1900 AND co2 IS NOT NULL
ORDER BY year;



-- Q7. CTE + aggregation: decade-by-decade global emissions, and the
-- decade-over-decade change, to show the acceleration (or not) of the
-- problem over time.

WITH decades AS (
    SELECT
        (year / 10) * 10 AS decade,
        SUM(co2) AS decade_total_co2
    FROM co2_emissions
    WHERE is_country = 1 AND co2 IS NOT NULL AND year >= 1900
    GROUP BY decade
)
SELECT
    decade,
    decade_total_co2,
    decade_total_co2 - LAG(decade_total_co2) OVER (ORDER BY decade) AS change_vs_prev_decade
FROM decades
ORDER BY decade;



-- Q8. Who's actually cutting emissions? Countries where 2023 CO2 is lower
-- than 2005 CO2 (a common Kyoto/Paris-era baseline), among countries big
-- enough to matter (>5 Mt in 2005).

WITH y2005 AS (
    SELECT country, co2 AS co2_2005 FROM co2_emissions
    WHERE is_country = 1 AND year = 2005 AND co2 > 5
),
y2023 AS (
    SELECT country, co2 AS co2_2023 FROM co2_emissions
    WHERE is_country = 1 AND year = 2023
)
SELECT
    a.country, a.co2_2005, b.co2_2023,
    ROUND((b.co2_2023 - a.co2_2005) / a.co2_2005 * 100, 1) AS pct_change_2005_to_2023
FROM y2005 a
JOIN y2023 b ON a.country = b.country
WHERE b.co2_2023 < a.co2_2005
ORDER BY pct_change_2005_to_2023 ASC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- Q9. Subquery: countries whose 2023 per-capita emissions are above the
-- (population-weighted-ish) world average per-capita figure for that year.
-- ----------------------------------------------------------------------------
SELECT country, co2_per_capita
FROM co2_emissions
WHERE is_country = 1
  AND year = 2023
  AND co2_per_capita > (
        SELECT co2_per_capita FROM co2_emissions
        WHERE country = 'World' AND year = 2023
      )
ORDER BY co2_per_capita DESC;


-- ----------------------------------------------------------------------------
-- Q10. Energy intensity vs emissions: is CO2 per unit of GDP actually
-- falling for the biggest economies, or is growth just outrunning
-- efficiency gains? (basic multi-column trend check)
-- ----------------------------------------------------------------------------
SELECT country, year, gdp, co2, ROUND(co2 * 1000000 / NULLIF(gdp, 0), 4) AS co2_per_dollar_gdp
FROM co2_emissions
WHERE country IN ('United States', 'China', 'India', 'Germany')
  AND year IN (2000, 2010, 2023)
  AND gdp IS NOT NULL AND co2 IS NOT NULL
ORDER BY country, year;


-- ----------------------------------------------------------------------------
-- Q11. Temperature contribution: top 10 all-time cumulative emitters and
-- their estimated share of observed warming attributable to their CO2
-- (OWID's temperature_change_from_co2 column, degrees C).
-- ----------------------------------------------------------------------------
SELECT country, cumulative_co2, temperature_change_from_co2
FROM co2_emissions
WHERE is_country = 1 AND year = 2023 AND cumulative_co2 IS NOT NULL
ORDER BY cumulative_co2 DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Q12. Fuel mix shift: for the world's 5 biggest current emitters, how has
-- the coal/oil/gas split within their own emissions changed between 2000
-- and 2023? (multi-metric comparison across two points in time)
-- ----------------------------------------------------------------------------
WITH big5 AS (
    SELECT country FROM co2_emissions
    WHERE is_country = 1 AND year = 2023 AND co2 IS NOT NULL
    ORDER BY co2 DESC LIMIT 5
)
SELECT
    c.country, c.year, c.coal_co2, c.oil_co2, c.gas_co2,
    ROUND(c.coal_co2 / c.co2 * 100, 1) AS coal_share_pct,
    ROUND(c.gas_co2 / c.co2 * 100, 1) AS gas_share_pct
FROM co2_emissions c
JOIN big5 b ON c.country = b.country
WHERE c.year IN (2000, 2023) AND c.co2 IS NOT NULL
ORDER BY c.country, c.year;



-- Q13. HAVING clause: which countries have averaged >5%/year emissions
-- growth over the last 10 years of data (2014-2023)? These are the ones
-- worth watching going forward, not just the current biggest emitters.

SELECT country, AVG(co2_growth_prct) AS avg_annual_growth_pct, COUNT(*) AS years_counted
FROM co2_emissions
WHERE is_country = 1 AND year BETWEEN 2014 AND 2023 AND co2_growth_prct IS NOT NULL
GROUP BY country
HAVING AVG(co2_growth_prct) > 5 AND COUNT(*) >= 8
ORDER BY avg_annual_growth_pct DESC;
