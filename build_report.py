"""Create a standalone HTML report with embedded charts, tables, and source notes."""
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs'
a = pd.read_csv(OUT / 'campus_annual_comparison.csv').set_index('year')
changes = (a.iloc[-1] / a.iloc[0] - 1) * 100
rows = ''.join(f'<tr><td>{y}</td><td>{r.ucsd_campus_mwh:,.2f}</td><td>{r.san_diego_county_mwh:,.2f}</td></tr>' for y,r in a.iterrows())
def svg(name):
    text=(OUT/name).read_text()
    return text[text.index('<svg'):]
report = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>UCSD Electricity Trends</title><style>
*{box-sizing:border-box}body{margin:0;background:#fafbf8;color:#203b35;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:0 auto;padding:40px 24px}h1{font-size:clamp(32px,5vw,54px);line-height:1.1;letter-spacing:-1px}h2{margin:36px 0 12px}p{max-width:850px}.eyebrow{color:#087f8c;font-size:13px;font-weight:700;letter-spacing:2px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:28px 0}.card{border:1px solid #d8e1db;border-radius:14px;padding:20px;background:white}.number{font-size:34px;line-height:1.5;font-weight:750}.county{color:#db6d28}.campus{color:#087f8c}.muted{color:#60776d;font-size:14px}svg{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border-bottom:1px solid #d8e1db;padding:12px;text-align:right}th:first-child,td:first-child{text-align:left}a{color:#087f8c}details{margin:30px 0;border:1px solid #d8e1db;border-radius:12px;padding:18px}summary{cursor:pointer;font-weight:700}.tablewrap{overflow:auto}
</style><main><div class="eyebrow">ELECTRICITY CONSUMPTION ANALYSIS · 2018–2019</div><h1>UCSD electricity trends<br>in regional context</h1>
<p>Compare the dataset's reported UCSD campus load with San Diego County's total electricity consumption. Both series are compared with their own prior-year values; the county total is not adjusted for UCSD.</p>
<div class="cards"><div class="card"><div>UCSD reported campus load</div><div class="number campus">CAMPUS_CHANGE%</div><div class="muted">Change from 2018 to 2019</div></div><div class="card"><div>San Diego County</div><div class="number county">COUNTY_CHANGE%</div><div class="muted">Change from 2018 to 2019</div></div><div class="card"><div>Difference in changes</div><div class="number">GAP pp</div><div class="muted">Campus consumption fell less</div></div></div>
MAIN_CHART
<h2>The underlying annual values</h2><div class="tablewrap"><table><thead><tr><th>Year</th><th>Reported campus MWh</th><th>County MWh</th></tr></thead><tbody>TABLE_ROWS</tbody></table></div>
<h2>What the graph tells us</h2><p>Reported campus consumption was nearly unchanged annually, while county consumption declined more. Both series show their largest monthly decline in August 2019 compared with August 2018. The graph describes changes; it does not identify their cause or prove improved energy efficiency.</p>
<h2>How the data was processed</h2><ol><li>Load public CSV and Excel files with pandas.</li><li>Resolve local daylight-saving timestamps and check interval coverage.</li><li>Average four conflicting campus timestamp pairs, preserving the original pairs for review.</li><li>Convert campus average kW readings to MWh; convert county GWh to MWh.</li><li>Aggregate by month/year, reconcile county monthly sums with annual totals, and plot percent changes with Matplotlib.</li></ol>
<p class="muted">Every expected 15-minute campus interval is present after cleaning for 2018–2019. Published TotalCampusLoad is used directly rather than summing buildings. The dataset describes its campus microgrid boundary; this does not establish inclusion of every remote UCSD facility. Energy is assigned to the recorded interval's timestamp.</p>
<h2>Sources and scope</h2><p><a href="https://github.com/sushilsilwal3/UCSD-Microgrid-Database">UCSD Microgrid Database</a> · <a href="https://doi.org/10.1063/5.0038650">Silwal et al., 2021</a> · <a href="https://www.energy.ca.gov/files/energy-consumption-data-files">California Energy Commission</a></p><p class="muted">Historical electricity-use comparison. Trade Street is excluded. The county covers a different reporting boundary and includes self-generation in its consumption methodology. Occupancy, weather, and area are not controlled for. See the included README for methods, limitations, and commands.</p></main></html>'''
for k,v in {'CAMPUS_CHANGE':f'{changes.iloc[0]:+.2f}', 'COUNTY_CHANGE':f'{changes.iloc[1]:+.2f}', 'GAP':f'{changes.iloc[0]-changes.iloc[1]:.2f}', 'MAIN_CHART':svg('campus_comparison.svg'), 'TABLE_ROWS':rows}.items(): report=report.replace(k,v)
(OUT/'report.html').write_text(report)
print(OUT/'report.html')
