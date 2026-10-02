"""Compare two UCSD building meters with San Diego County, 2017–2019.
Run: python building_analysis.py (after installing requirements.txt).
"""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).parent / '.mpl-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
YEARS = [2017, 2018, 2019]
BUILDINGS = {'Center Hall': 'CenterHall.csv', 'Music Building': 'MusicBuilding.csv'}


def building_energy():
    """Each average-kW reading represents 0.25 hours. Do not fill gaps with zero."""
    totals = []
    quality = []
    for building, filename in BUILDINGS.items():
        df = pd.read_csv(RAW / filename, encoding='utf-8-sig')
        df['DateTime'] = pd.to_datetime(df['DateTime'], format='%m/%d/%Y %H:%M')
        df['RealPower'] = pd.to_numeric(df['RealPower'], errors='coerce')
        df = df[df.DateTime.dt.year.isin(YEARS)].copy()
        # Raw files are in reverse chronological order. Preserve autumn clock
        # repeats: these are separate intervals, not duplicate measurements.
        df = df.iloc[::-1].copy()
        df['DateTime'] = df.DateTime.dt.tz_localize(
            'America/Los_Angeles', ambiguous='infer', nonexistent='raise')
        if df.duplicated('DateTime').any():
            raise ValueError(f'{building}: duplicate absolute timestamps.')
        series = df.set_index('DateTime').RealPower.sort_index()
        for year in YEARS:
            expected = pd.date_range(f'{year}-01-01', f'{year + 1}-01-01', freq='15min', inclusive='left', tz='America/Los_Angeles')
            annual = series.reindex(expected)
            missing = int(annual.isna().sum())
            negative = int((annual < 0).sum())
            quality.append({'building': building, 'year': year,
                            'expected_readings': len(expected), 'valid_readings': int(annual.count()),
                            'missing_readings': missing, 'negative_readings': negative,
                            'coverage_percent': round(annual.count() / len(expected) * 100, 3)})
            if missing or negative or not series[series.index.year == year].index.isin(expected).all():
                raise ValueError(f'{building}, {year}: incomplete or invalid readings. Do not report a complete annual total.')
            totals.append({'building': building, 'year': year,
                           'electricity_mwh': float(annual.sum() * 0.25 / 1000)})
    return pd.DataFrame(totals), pd.DataFrame(quality)


def county_energy():
    """CEC workbook contains distinct sector rows; sum all sectors once per year."""
    df = pd.read_excel(RAW / 'county_electricity.xlsx')
    sd = df[df.COUNTY_NAME.str.upper().eq('SAN DIEGO') & df.YEAR.isin(YEARS)].copy()
    if sd.duplicated(['YEAR', 'COUNTY_NUM', 'SECTOR', 'RNR']).any():
        raise ValueError('Duplicate county-sector rows found.')
    sd['GWH'] = pd.to_numeric(sd.GWH, errors='raise')
    if sd.GWH.isna().any() or (sd.GWH < 0).any():
        raise ValueError('Invalid county consumption value.')
    sd.to_csv(OUT / 'san_diego_sectors.csv', index=False)
    annual = sd.groupby('YEAR').GWH.sum().reindex(YEARS) * 1000
    if annual.isna().any() or (annual <= 0).any():
        raise ValueError('Missing county year.')
    annual.index.name = 'year'
    return annual


def main():
    buildings, quality = building_energy()
    buildings.to_csv(OUT / 'building_annual.csv', index=False)
    quality.to_csv(OUT / 'data_quality.csv', index=False)
    comparison = pd.DataFrame({
        'ucsd_two_buildings_mwh': buildings.groupby('year').electricity_mwh.sum(),
        'san_diego_county_mwh': county_energy(),
    })
    for prefix in ['ucsd_two_buildings', 'san_diego_county']:
        values = comparison[f'{prefix}_mwh']
        comparison[f'{prefix}_index'] = values / values.iloc[0] * 100
        comparison[f'{prefix}_yoy_percent'] = values.pct_change() * 100
    comparison.to_csv(OUT / 'annual_comparison.csv', float_format='%.6f')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(10.5, 6.3), facecolor='#fafbf8')
    ax.set_facecolor('#fafbf8')
    colors = ['#087f8c', '#db6d28']
    for col, label, color in zip(
        ['ucsd_two_buildings_index', 'san_diego_county_index'],
        ['UCSD: Center Hall + Music Building', 'San Diego County total'], colors):
        ax.plot(comparison.index, comparison[col], marker='o', linewidth=2.8, markersize=7, color=color, label=label)
        last = comparison[col].iloc[-1]
        ax.annotate(f'{last - 100:+.1f}% since 2017', (2019, last), xytext=(12, 0),
                    textcoords='offset points', color=color, va='center', weight='bold')
    ax.axhline(100, color='#89928e', linewidth=1, linestyle='--', alpha=.6)
    ax.set_xlim(2016.9, 2019.72)
    ax.set_xticks(YEARS)
    ax.set_ylim(min(comparison.filter(like='_index').min()) - 3, 103)
    ax.set_ylabel('Electricity use index (2017 = 100)')
    ax.grid(axis='y', alpha=.18)
    ax.legend(frameon=False, loc='lower left')
    fig.suptitle('How did electricity use change?', x=.11, ha='left', fontsize=22, weight='bold', y=.95)
    ax.set_title('Two UCSD campus buildings compared with San Diego County · 2017–2019', loc='left', pad=20, fontsize=11)
    fig.text(.11, .06, 'UCSD series covers two building meters, not the entire campus. County total is not adjusted for UCSD.\nSources: UCSD Microgrid Database (Silwal et al.); California Energy Commission annual county workbook.',
             fontsize=9, color='#52625b', linespacing=1.5)
    fig.subplots_adjust(left=.11, right=.95, top=.80, bottom=.22)
    fig.savefig(OUT / 'electricity_comparison.png', dpi=180, facecolor=fig.get_facecolor())
    fig.savefig(OUT / 'electricity_comparison.svg', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(comparison.round(2).to_string())
    print('\nCoverage checks passed: both building files have every expected reading for 2017–2019.')


if __name__ == '__main__':
    main()
