#!/usr/bin/env python3
"""
Generate a static HTML knitting gallery from Airtable data.
Downloads project photos and creates a photo grid with project details.
"""

import os
import requests
import hashlib
from datetime import datetime
from credentials import AIRTABLE_TOKEN, AIRTABLE_BASE_ID

OUTPUT_DIR = '/Users/vorimor/Documents/Household/Yarn'
PHOTOS_DIR = os.path.join(OUTPUT_DIR, 'photos')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'index.html')


def fetch_all_records(table_name):
    """Fetch all records from an Airtable table, handling pagination."""
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}'
    headers = {'Authorization': f'Bearer {AIRTABLE_TOKEN}'}
    records = []

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        records.extend(data.get('records', []))
        offset = data.get('offset')
        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}?offset={offset}' if offset else None

    return records


def fetch_knitting_stats():
    """Fetch total yards knitted and available from Summary Tables."""
    records = fetch_all_records('Summary Tables')

    total_knitted = sum(r['fields'].get('Yards knitted', 0) for r in records)
    total_available = sum(r['fields'].get('Yards available', 0) for r in records)

    miles_knitted = round(total_knitted / 1760, 1)
    miles_available = round(total_available / 1760, 1)

    return miles_knitted, miles_available


def build_lookup_table(records, fields):
    """Build a lookup dict from record ID to specified fields."""
    lookup = {}
    for record in records:
        record_id = record['id']
        lookup[record_id] = {field: record['fields'].get(field, '') for field in fields}
    return lookup


def download_photo(photo_url, project_name):
    """Download a photo and save to photos/ folder. Returns local filename."""
    os.makedirs(PHOTOS_DIR, exist_ok=True)

    # Create a safe filename using hash of URL + project name
    url_hash = hashlib.md5(photo_url.encode()).hexdigest()[:8]
    safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in project_name)[:50]
    filename = f'{safe_name}_{url_hash}.jpg'
    filepath = os.path.join(PHOTOS_DIR, filename)

    # Skip if already downloaded
    if os.path.exists(filepath):
        return f'photos/{filename}'

    try:
        response = requests.get(photo_url, timeout=30)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return f'photos/{filename}'
    except Exception as e:
        print(f'  Error downloading photo for {project_name}: {e}')
        return None


def format_date(date_str):
    """Format date string for display."""
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %Y')
    except ValueError:
        return date_str


def generate_html(projects, finished_count, miles_knitted, miles_available):
    """Generate the HTML gallery page."""

    # Generate project cards
    cards_html = []
    for project in projects:
        photo_path = project.get('photo_path', '')
        name = project.get('name', 'Untitled')
        date_finished = project.get('date_finished', '')
        yarn_name = project.get('yarn_name', '')
        grams = project.get('grams', '')
        pattern_name = project.get('pattern_name', '')
        designer = project.get('designer', '')

        if not photo_path:
            continue

        card = f'''      <div class="project-card">
        <div class="card-image">
          <img src="{photo_path}" alt="{name}" loading="lazy" />
        </div>
        <div class="card-content">
          <h3 class="project-name">{name}</h3>
          {f'<p class="project-date">{date_finished}</p>' if date_finished else ''}
          {f'<p class="project-yarn">{yarn_name}</p>' if yarn_name else ''}
          {f'<p class="project-grams">{grams}g</p>' if grams else ''}
          {f'<p class="project-pattern">{pattern_name}</p>' if pattern_name else ''}
          {f'<p class="project-designer">by {designer}</p>' if designer else ''}
        </div>
      </div>'''
        cards_html.append(card)

    cards_joined = '\n'.join(cards_html)

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
      margin-bottom: 1.5rem;
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

    .photo-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1.5rem;
    }}

    .project-card {{
      background: var(--warm-white);
      border-radius: 12px;
      overflow: hidden;
      box-shadow:
        0 4px 6px rgba(61, 34, 20, 0.06),
        0 10px 40px rgba(61, 34, 20, 0.1),
        0 0 0 1px rgba(196, 113, 74, 0.15);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }}

    .project-card:hover {{
      transform: translateY(-4px);
      box-shadow:
        0 8px 12px rgba(61, 34, 20, 0.08),
        0 16px 48px rgba(61, 34, 20, 0.15),
        0 0 0 1px rgba(196, 113, 74, 0.2);
    }}

    .card-image {{
      aspect-ratio: 4 / 3;
      overflow: hidden;
      background: var(--cream);
    }}

    .card-image img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
    }}

    .project-card:hover .card-image img {{
      transform: scale(1.05);
    }}

    .card-content {{
      padding: 1rem 1.25rem 1.25rem;
    }}

    .project-name {{
      font-family: 'Playfair Display', serif;
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--deep-brown);
      margin-bottom: 0.5rem;
      line-height: 1.3;
    }}

    .project-date {{
      font-size: 0.8rem;
      color: var(--terracotta);
      font-style: italic;
      margin-bottom: 0.4rem;
    }}

    .project-yarn {{
      font-size: 0.85rem;
      color: var(--deep-brown);
      margin-bottom: 0.25rem;
    }}

    .project-grams {{
      font-size: 0.8rem;
      color: var(--rust);
      opacity: 0.8;
      margin-bottom: 0.4rem;
    }}

    .project-pattern {{
      font-size: 0.85rem;
      color: var(--deep-brown);
      font-style: italic;
    }}

    .project-designer {{
      font-size: 0.75rem;
      color: var(--rust);
      opacity: 0.7;
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
      .photo-grid {{ grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1rem; }}
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
        <span class="stat-number">{finished_count}</span>
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
    <div class="photo-grid">
{cards_joined}
    </div>
  </main>

  <footer>
    handcrafted stitch by stitch ✦ needles always busy
  </footer>

</body>
</html>'''


def main():
    print('Fetching data from Airtable...')

    # Fetch all needed tables
    print('  Fetching projects...')
    project_records = fetch_all_records('Projects')
    print(f'    Found {len(project_records)} projects')

    print('  Fetching patterns...')
    pattern_records = fetch_all_records('Patterns')
    patterns = build_lookup_table(pattern_records, ['Name', 'Designer'])
    print(f'    Found {len(pattern_records)} patterns')

    print('  Fetching yarn...')
    yarn_records = fetch_all_records('Yarn')
    yarns = build_lookup_table(yarn_records, ['Name', 'Brand', 'Color Name'])
    print(f'    Found {len(yarn_records)} yarns')

    print('  Fetching stats...')
    miles_knitted, miles_available = fetch_knitting_stats()
    print(f'    Miles knitted: {miles_knitted}, Miles in stash: {miles_available}')

    # Process projects
    print('\nProcessing projects and downloading photos...')
    projects = []

    for record in project_records:
        fields = record['fields']
        name = fields.get('Name', 'Untitled')

        # Get first photo
        photos = fields.get('Finished Photos', [])
        if not photos:
            print(f'  Skipping {name} (no photo)')
            continue

        photo_url = photos[0].get('url')
        if not photo_url:
            print(f'  Skipping {name} (no photo URL)')
            continue

        print(f'  Processing: {name}')
        photo_path = download_photo(photo_url, name)

        # Get pattern info
        pattern_ids = fields.get('Pattern', [])
        pattern_info = patterns.get(pattern_ids[0], {}) if pattern_ids else {}

        # Get yarn info
        yarn_ids = fields.get('Yarn', [])
        yarn_info = yarns.get(yarn_ids[0], {}) if yarn_ids else {}
        yarn_name_parts = [yarn_info.get('Brand', ''), yarn_info.get('Name', ''), yarn_info.get('Color Name', '')]
        yarn_name = ' '.join(part for part in yarn_name_parts if part)

        projects.append({
            'name': name,
            'photo_path': photo_path,
            'date_finished_raw': fields.get('Date Finished', ''),
            'date_finished': format_date(fields.get('Date Finished', '')),
            'yarn_name': yarn_name,
            'grams': fields.get('Total Grams Used (from Yarn Usage)', ''),
            'pattern_name': pattern_info.get('Name', ''),
            'designer': pattern_info.get('Designer', ''),
        })

    # Sort by date finished (most recent first) using raw YYYY-MM-DD format
    projects.sort(key=lambda p: p.get('date_finished_raw', ''), reverse=True)

    # Generate HTML
    print(f'\nGenerating HTML with {len(projects)} projects...')
    finished_count = len(project_records)
    html = generate_html(projects, finished_count, miles_knitted, miles_available)

    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)

    print(f'\nDone! Generated: {OUTPUT_FILE}')
    print(f'Photos saved to: {PHOTOS_DIR}')


if __name__ == '__main__':
    main()
