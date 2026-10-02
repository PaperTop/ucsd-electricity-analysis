# Methods and sources

## Data sources

1. **UCSD Microgrid Database**
   - Repository: https://github.com/sushilsilwal3/UCSD-Microgrid-Database
   - Paper: Silwal et al. (2021), *Open-source multi-year power generation,
     consumption, and storage data in a microgrid*, DOI https://doi.org/10.1063/5.0038650
   - `DemandCharge.csv`: DateTime, TotalCampusLoad, OnCampusGeneration,
     SDG&E Import, AdjustedDemand. Main analysis uses DateTime and TotalCampusLoad.
   - Supplemental: BuildingLoad/CenterHall.csv and BuildingLoad/MusicBuilding.csv.
   - Campus readings are treated as average power in kW over 15-minute intervals.
2. **California Energy Commission**
   - Source page: https://www.energy.ca.gov/files/energy-consumption-data-files
   - Definition and documentation:
     https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/california-energy-consumption-dashboards-0
   - Annual county workbook: YEAR, COUNTY_NUM, COUNTY_NAME, SECTOR, RNR, GWH.
   - Monthly county workbook: YEAR, MONTH, COUNTY_NUM, COUNTY_NAME, RNR, GWH.
   - Filter COUNTY_NAME = SAN DIEGO. Sum published sector rows, including
     residential and non-residential use, once per year or month.
   - The monthly file lacks sector names: repeated month/RNR keys are legitimate
     sector rows and must not be dropped as duplicates.

Downloaded September 30, 2026 UTC. Original files and SHA-256 hashes are included
in `data/raw/` and `data/source_manifest.json`. The download script uses live
source URLs; future downloads can differ from the bundled snapshot.

## Processing

1. Read the CSV and Excel files with pandas.
2. Filter to the county and the chosen calendar years.
3. Interpret campus timestamps in America/Los_Angeles local time. Keep both readings
   during autumn's repeated hour and check the spring clock transition against the expected interval grid.
4. Four ordinary 2019 timestamps in the campus file have two conflicting values.
   Average each pair once. Save the original pairs in
   `outputs/campus_duplicate_readings.csv` so this decision is visible.
5. Check that every expected 15-minute interval remains: **35,040 per year**.
6. Convert average campus kW to energy: **MWh = kW × 0.25 / 1,000**.
7. Convert county GWh to MWh: **MWh = GWh × 1,000**.
8. Sum campus interval energy by calendar month and year.
9. Confirm that monthly county values sum to the independently downloaded annual
   county workbook, within 0.01 MWh.
10. Compare annual percent changes, and each 2019 month with the same 2018 month:
    **percent change = (new / old − 1) × 100**.

The four conflicting pairs affect the annual estimate by at most 1.25 MWh
between choosing all lower and all upper values (about 0.0004% of 2019 campus
energy). We do not smooth or arbitrarily replace the remaining readings.

## Reading the charts

- Main top panel: 2018-to-2019 annual percentage changes.
- Main bottom panel: monthly year-over-year changes; zero means unchanged from
  the same month of 2018. This avoids comparing a winter month directly with summer.
- Supplemental building chart: each series starts at 100 in 2017; a value of
  90 means 10% less use than its own 2017 baseline.
- There is **no subtraction** from the county total. UCSD is geographically
  inside the county; the sources have different reporting boundaries and are
  not assumed to be independent.

## Limits

- This is an electricity comparison, not total energy including natural gas or heat.
- Only two full campus years are available in this CSV; this is a historical comparison.
- Published campus and county consumption may use different accounting boundaries.
  We compare their own changes, not precise UCSD shares of the county total.
- The interval energy estimates are grouped by the recorded timestamp. The paper
  describes averages of the preceding 15 minutes; interval endpoints are not
  separately supplied. A boundary interval could belong to the prior month/year.
- Occupancy, weather, floor area, and electricity generated onsite are not
  controlled for. Lower use alone does not demonstrate improved efficiency.
- The two-building supplement excludes centrally supplied heating/cooling energy.


## Source quality and interval boundaries

The source authors already quality-controlled the demand-charge dataset. Complete
timestamp coverage does not establish that every value is an untouched meter
observation. This analysis adds validation and duplicate handling; it does not
fill missing campus intervals.

Assigning readings to the preceding interval instead of the recorded timestamp
gives 302,441.508160 MWh in 2018 and 301,993.585233 MWh in 2019. The annual
change still rounds to −0.15%. Instrument accuracy and source-imputation
uncertainty have not been quantified.
