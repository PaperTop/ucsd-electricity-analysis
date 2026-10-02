"""UCSD reported campus load vs San Diego County: electricity consumption analysis.
Run: python analyze.py
"""
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.mpl-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

RAW = ROOT / 'data/raw'
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
YEARS = [2018, 2019]
TZ = 'America/Los_Angeles'
COLORS = ['#087f8c', '#db6d28']
LABELS = ['UCSD reported campus load', 'San Diego County total']


def read_campus():
    df = pd.read_csv(RAW / 'DemandCharge.csv').iloc[::-1].copy()
    df['DateTime'] = pd.to_datetime(df.DateTime, format='%m/%d/%Y %H:%M')
    df = df[df.DateTime.dt.year.isin(YEARS)].copy()
    # Preserve both readings in the repeated autumn hour by giving them distinct UTC offsets.
    df['DateTime'] = df.DateTime.dt.tz_localize(TZ, ambiguous='infer', nonexistent='raise')
    df['TotalCampusLoad'] = pd.to_numeric(df.TotalCampusLoad, errors='raise')
    if df.TotalCampusLoad.isna().any() or (df.TotalCampusLoad <= 0).any():
        raise ValueError('Missing or non-positive campus load; inspect before integrating.')
    conflicts = df[df.duplicated('DateTime', keep=False)].copy()
    conflicts.to_csv(OUT / 'campus_duplicate_readings.csv', index=False)
    # Four 2019 timestamps have conflicting values. Average each pair once, rather than
    # counting each twice or silently keeping an arbitrary reading. Save the pairs for review.
    series = df.groupby('DateTime').TotalCampusLoad.mean().sort_index()
    expected = pd.date_range('2018-01-01', '2020-01-01', freq='15min', tz=TZ, inclusive='left')
    if not series.index.isin(expected).all():
        raise ValueError('Off-grid campus timestamps.')
    series = series.reindex(expected)
    if series.isna().any():
        raise ValueError('Campus dataset has missing intervals; annual totals would be incomplete.')
    quality = pd.DataFrame([{
        'series': 'UCSD TotalCampusLoad', 'year': y,
        'expected_readings': len(expected[expected.year == y]),
        'valid_readings_after_dedup': int(series[series.index.year == y].count()),
        'missing_readings': 0,
        'conflicting_timestamp_groups_averaged': int(conflicts[conflicts.DateTime.dt.year == y].DateTime.nunique()),
        'coverage_percent': 100,
    } for y in YEARS])
    quality.to_csv(OUT / 'campus_data_quality.csv', index=False)
    # Average power (kW) x 0.25 hours / 1000 = MWh in each labeled interval.
    # Aggregate by recorded timestamp's calendar month; raw labels lack interval boundaries.
    monthly = (series * 0.25 / 1000).resample('MS').sum()
    monthly.index = monthly.index.tz_localize(None)
    # Sensitivity: worst/best choice for the four pairs instead of the mean.
    lower = df.groupby('DateTime').TotalCampusLoad.min().sum() * .25 / 1000
    upper = df.groupby('DateTime').TotalCampusLoad.max().sum() * .25 / 1000
    return monthly, (upper - lower)


def read_county():
    annual = pd.read_excel(RAW / 'county_electricity.xlsx')
    monthly = pd.read_excel(RAW / 'county_electricity_monthly.xlsx')
    annual = annual[annual.COUNTY_NAME.eq('SAN DIEGO') & annual.YEAR.isin(YEARS)].copy()
    monthly = monthly[monthly.COUNTY_NAME.eq('SAN DIEGO') & monthly.YEAR.isin(YEARS)].copy()
    if annual.duplicated(['YEAR', 'COUNTY_NUM', 'SECTOR', 'RNR']).any():
        raise ValueError('Unexpected duplicate county-sector rows.')
    # Monthly workbook omits sector names but retains one row per sector. Repeated
    # YEAR/MONTH/RNR keys are legitimate: sum all published rows, do not deduplicate them.
    for df in [annual, monthly]:
        df['GWH'] = pd.to_numeric(df.GWH, errors='raise')
        if df.GWH.isna().any() or (df.GWH < 0).any():
            raise ValueError('Invalid county consumption values.')
    monthly['date'] = pd.to_datetime(monthly.YEAR.astype(str) + ' ' + monthly.MONTH + ' 01', format='%Y %B %d')
    monthly.to_csv(OUT / 'county_monthly_source_rows.csv', index=False)
    annual.to_csv(OUT / 'county_annual_source_rows.csv', index=False)
    county_months = monthly.groupby('date').GWH.sum() * 1000  # GWh to MWh
    expected = pd.date_range('2018-01-01', '2019-12-01', freq='MS')
    if not county_months.index.equals(expected):
        raise ValueError('County month coverage differs from the expected 24 months.')
    county_years = annual.groupby('YEAR').GWH.sum() * 1000
    monthly_sum = county_months.groupby(county_months.index.year).sum()
    if (monthly_sum - county_years).abs().max() > .01:
        raise ValueError('County monthly sums do not reconcile with annual totals.')
    return county_months, county_years


def plot(monthly, annual):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.5, 9), gridspec_kw={'height_ratios': [1, 1.8]}, facecolor='#fafbf8')
    for ax in (ax1, ax2):
        ax.set_facecolor('#fafbf8')
        ax.grid(axis='y', alpha=.18)
        ax.set_axisbelow(True)
    changes = (annual.iloc[-1] / annual.iloc[0] - 1) * 100
    bars = ax1.barh(LABELS, changes, color=COLORS, height=.48)
    ax1.invert_yaxis()
    ax1.axvline(0, color='#52625b', lw=1)
    ax1.set_xlim(min(changes) - 1.4, 1)
    ax1.set_xlabel('Change in annual electricity use (%)')
    ax1.set_title('Annual change · 2018 to 2019', loc='left', fontsize=13, weight='bold', pad=14)
    for bar, value in zip(bars, changes):
        ax1.text(value - .12, bar.get_y() + bar.get_height()/2, f'{value:+.2f}%', ha='right', va='center', weight='bold')
    yoy = monthly.pct_change(periods=12).loc['2019'] * 100
    for col, label, color in zip(monthly.columns, LABELS, COLORS):
        ax2.plot(range(1, 13), yoy[col], marker='o', lw=2.4, color=color, label=label)
    ax2.axhline(0, color='#52625b', lw=1)
    ax2.set_xticks(range(1,13), ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    ax2.set_ylabel('Change from same month in 2018 (%)')
    ax2.set_title('Monthly change · each month of 2019 versus the same month of 2018', loc='left', fontsize=12, weight='bold', pad=16)
    ax2.legend(frameon=False, fontsize=10, loc='best')
    fig.suptitle('UCSD vs San Diego County', x=.08, ha='left', y=.96, fontsize=24, weight='bold')
    fig.text(.08, .913, 'Electricity use trends · reported main-campus load and county total · no subtraction', fontsize=11, color='#52625b')
    fig.text(.08,.045,'Campus: TotalCampusLoad in UCSD DemandCharge.csv; county: California Energy Commission.\nFour conflicting campus timestamps were averaged. Both full years have complete interval coverage.\nThis is an observational comparison of electricity use; it does not establish energy efficiency or causes.',fontsize=9,color='#52625b',linespacing=1.5)
    fig.subplots_adjust(left=.25, right=.95, top=.84, bottom=.16, hspace=.62)
    fig.savefig(OUT / 'campus_comparison.png', dpi=180, facecolor=fig.get_facecolor())
    fig.savefig(OUT / 'campus_comparison.svg', facecolor=fig.get_facecolor())
    plt.close(fig)
    return changes, yoy


def main():
    campus, sensitivity_mwh = read_campus()
    county, county_annual = read_county()
    monthly = pd.DataFrame({'ucsd_campus_mwh': campus, 'san_diego_county_mwh': county})
    monthly.index.name = 'month'
    monthly.to_csv(OUT / 'campus_monthly_comparison.csv', float_format='%.6f')
    annual = pd.DataFrame({'ucsd_campus_mwh': campus.groupby(campus.index.year).sum(), 'san_diego_county_mwh': county_annual})
    annual.index.name = 'year'
    annual.to_csv(OUT / 'campus_annual_comparison.csv', float_format='%.6f')
    (annual / annual.iloc[0] * 100).to_csv(OUT / 'campus_annual_index.csv', float_format='%.6f')
    changes, yoy = plot(monthly, annual)
    yoy.index.name = 'month'
    yoy.to_csv(OUT / 'campus_monthly_yoy_percent.csv', float_format='%.6f')
    print(annual.round(2).to_string())
    print('\n2018 to 2019 changes (%):\n', changes.round(4).to_string())
    print(f'Four conflicting timestamp pairs: min/max handling changes annual energy by at most {sensitivity_mwh:.4f} MWh.')
    print('Verified: full time coverage; timezone repeats preserved; monthly county sums match annual workbook.')


if __name__ == '__main__':
    main()
