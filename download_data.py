"""Download only public source files used by this analysis; existing copies are reused."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

RAW = Path(__file__).resolve().parent / 'data/raw'
RAW.mkdir(parents=True, exist_ok=True)
FILES = {
    'DemandCharge.csv': 'https://raw.githubusercontent.com/sushilsilwal3/UCSD-Microgrid-Database/master/Data%20Files/DemandCharge.csv',
    'CenterHall.csv': 'https://raw.githubusercontent.com/sushilsilwal3/UCSD-Microgrid-Database/master/Data%20Files/BuildingLoad/CenterHall.csv',
    'MusicBuilding.csv': 'https://raw.githubusercontent.com/sushilsilwal3/UCSD-Microgrid-Database/master/Data%20Files/BuildingLoad/MusicBuilding.csv',
    'county_electricity.xlsx': 'https://www.energy.ca.gov/filebrowser/download/8144?fid=8144',
    'county_electricity_monthly.xlsx': 'https://www.energy.ca.gov/filebrowser/download/9968?fid=9968',
}


def download(item):
    name, url = item
    dest = RAW / name
    if dest.exists():
        print(f'Reusing {name}')
        return
    req = urllib.request.Request(url, headers={'User-Agent': 'UCSD-electricity-analysis/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    dest.write_bytes(data)
    print(f'Downloaded {name}: {len(data):,} bytes')


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(download, FILES.items()))
