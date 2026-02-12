import requests
import sys
sys.path.insert(0, '/Users/vorimor/Documents/Household/Yarn')
from credentials import AIRTABLE_TOKEN, AIRTABLE_BASE_ID

TABLE_NAME = 'Summary Tables'
OUTPUT_FILE = '/Users/vorimor/Documents/Household/Yarn/pattern_matches/rebeccas_knits.html'

def fetch_knitting_stats():
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}'
    headers = {'Authorization': f'Bearer {AIRTABLE_TOKEN}'}
    
    total_knitted = 0
    total_available = 0

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        for record in data.get('records', []):
            total_knitted += record['fields'].get('Yards knitted', 0)
            total_available += record['fields'].get('Yards available', 0)
        url = data.get('offset') and f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}?offset={data["offset"]}'

    miles_knitted = round(total_knitted / 1760, 1)
    miles_available = round(total_available / 1760, 1)
    return miles_knitted, miles_available

def generate_html(miles_knitted, miles_available):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Rebecca's Knits</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --cream: #f8f2e8;
      --warm-white: #fdf9f3;
      --terracotta: #c4714a;
      --rust: #a85532;
      --deep-brown: #3d2214;
      --warm-tan: #d4b896;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      background-color: var(--cream);
      font-family: 'Lora', Georgia, serif;
      color: var(--deep-brown);
      min-height: 100vh;
    }}

    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='4'%3E%3Crect width='4' height='4' fill='%23f8f2e8'/%3E%3Ccircle cx='1' cy='1' r='0.5' fill='%23e8ddd0' opacity='0.4'/%3E%3C/svg%3E");
      pointer-events: none;
      z-index: 0;
    }}

    header {{
      position: relative;
      z-index: 1;
      text-align: center;
      padding: 3.5rem 2rem 2rem;
      background: linear-gradient(180deg, var(--warm-white) 0%, var(--cream) 100%);
      border-bottom: 2px solid var(--warm-tan);
    }}

    .yarn-decoration {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      margin-bottom: 1rem;
      opacity: 0.7;
    }}

    .yarn-line {{
      height: 2px;
      width: 60px;
      background: linear-gradient(90deg, transparent, var(--terracotta), transparent);
      border-radius: 2px;
    }}

    .yarn-icon {{ font-size: 1.4rem; }}

    h1 {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: clamp(2.2rem, 5vw, 3.5rem);
      font-weight: 600;
      color: var(--deep-brown);
      letter-spacing: 0.02em;
      line-height: 1.2;
    }}

    h1 em {{ font-style: italic; color: var(--terracotta); }}

    .subtitle {{
      margin-top: 0.6rem;
      font-size: 1rem;
      color: var(--rust);
      font-style: italic;
      letter-spacing: 0.05em;
    }}

    .stats-bar {{
      display: flex;
      justify-content: center;
      gap: 2.5rem;
      margin-top: 1.5rem;
      padding-top: 1.2rem;
      border-top: 1px solid var(--warm-tan);
      flex-wrap: wrap;
    }}

    .stat {{ text-align: center; }}

    .stat-number {{
      font-family: 'Playfair Display', serif;
      font-size: 1.6rem;
      font-weight: 600;
      color: var(--terracotta);
      display: block;
    }}

    .stat-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--rust);
      opacity: 0.8;
    }}

    .gallery-wrapper {{
      position: relative;
      z-index: 1;
      max-width: 1400px;
      margin: 2rem auto;
      padding: 0 1.5rem 3rem;
    }}

    .gallery-label {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--rust);
      opacity: 0.75;
    }}

    .gallery-label::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: linear-gradient(90deg, var(--warm-tan), transparent);
    }}

    .embed-frame {{
      border-radius: 12px;
      overflow: hidden;
      box-shadow:
        0 4px 6px rgba(61, 34, 20, 0.06),
        0 10px 40px rgba(61, 34, 20, 0.1),
        0 0 0 1px rgba(196, 113, 74, 0.15);
      background: var(--warm-white);
      animation: fadeUp 0.6s ease both;
    }}

    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(16px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}

    .embed-frame iframe {{
      display: block;
      width: 100%;
      height: 75vh;
      min-height: 500px;
      border: none;
    }}

    footer {{
      position: relative;
      z-index: 1;
      text-align: center;
      padding: 1.5rem;
      font-size: 0.8rem;
      color: var(--rust);
      opacity: 0.6;
      font-style: italic;
      border-top: 1px solid var(--warm-tan);
    }}

    @media (max-width: 600px) {{
      .stats-bar {{ gap: 1.5rem; }}
      .gallery-wrapper {{ padding: 0 0.75rem 2rem; }}
    }}
  </style>
</head>
<body>

  <header>
    <div class="yarn-decoration">
      <div class="yarn-line"></div>
      <span class="yarn-icon">🧶</span>
      <div class="yarn-line"></div>
    </div>
    <h1>Rebecca's <em>Knits</em></h1>
    <p class="subtitle">a collection of finished objects</p>
    <div class="stats-bar">
      <div class="stat">
        <span class="stat-number">226</span>
        <span class="stat-label">Finished Objects</span>
      </div>
      <div class="stat">
        <span class="stat-number">5+</span>
        <span class="stat-label">Years Knitting</span>
      </div>
      <div class="stat">
        <span class="stat-number">{miles_knitted}</span>
        <span class="stat-label">Miles Knitted</span>
      </div>
      <div class="stat">
        <span class="stat-number">{miles_available}</span>
        <span class="stat-label">Miles in Stash</span>
      </div>
    </div>
  </header>

  <main class="gallery-wrapper">
    <div class="gallery-label">Browse the collection</div>
    <div class="embed-frame">
      <iframe
        class="airtable-embed"
        src="https://airtable.com/embed/app2k5u0xNZUAZezv/shrcddFAwt4fXF8Ap?viewControls=on"
        frameborder="0"
        onmousewheel=""
        style="background: transparent;">
      </iframe>
    </div>
  </main>

  <footer>
    handcrafted stitch by stitch ✦ needles always busy
  </footer>

</body>
</html>'''

if __name__ == '__main__':
    print('Fetching stats from Airtable...')
    miles_knitted, miles_available = fetch_knitting_stats()
    print(f'Miles knitted: {miles_knitted}')
    print(f'Miles in stash: {miles_available}')
    
    html = generate_html(miles_knitted, miles_available)
    
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    
    print(f'Page generated: {OUTPUT_FILE}')