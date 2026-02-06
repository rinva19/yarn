#!/usr/bin/env python3
"""
Yarn Matcher - Match pattern yarn requirements with personal stash.

Accepts JSON input with pattern details and matches against Airtable stash.
Outputs a beautiful HTML report and opens it in the browser.
"""

import json
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import requests

from credentials import (
    AIRTABLE_TOKEN,
    AIRTABLE_BASE_ID,
    AIRTABLE_TABLE_NAME,
)


# =============================================================================
# Airtable Functions
# =============================================================================

def fetch_stash() -> list:
    """Fetch all yarn records from Airtable stash."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }

    all_records = []
    offset = None

    while True:
        params = {}
        if offset:
            params['offset'] = offset

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        all_records.extend(data.get('records', []))

        offset = data.get('offset')
        if not offset:
            break

    stash = []
    for record in all_records:
        fields = record.get('fields', {})
        yarn = {
            'name': fields.get('Name', 'Unknown'),
            'grist': fields.get('Grist - Yardage per gram'),
            'available_grams': fields.get('Available - Grams'),
            'available_yards': fields.get('Available - Yards'),
            'color': fields.get('Color description', ''),
        }
        if yarn['grist'] is not None:
            stash.append(yarn)

    return stash


# =============================================================================
# Matching Functions
# =============================================================================

def grist_matches(target: float, yarn: float, tolerance: float = 0.10) -> bool:
    """Check if yarn grist is within tolerance of target."""
    if not target or not yarn:
        return False
    return target * (1 - tolerance) <= yarn <= target * (1 + tolerance)


def calculate_combined_grist(grists: list) -> float:
    """
    Calculate combined grist for yarns held together.

    Formula: 1 / sum(1/grist for each yarn)
    """
    valid_grists = [g for g in grists if g and g > 0]
    if not valid_grists:
        return None
    return 1 / sum(1/g for g in valid_grists)


def fuzzy_color_match(c1: str, c2: str) -> bool:
    """Check if two colors are similar."""
    if not c1 or not c2:
        return False
    c1, c2 = c1.lower(), c2.lower()
    if c1 == c2 or c1 in c2 or c2 in c1:
        return True

    colors = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
              'brown', 'black', 'white', 'grey', 'gray', 'cream', 'beige', 'navy',
              'teal', 'coral', 'burgundy', 'maroon', 'olive']
    c1_base = next((c for c in colors if c in c1), None)
    c2_base = next((c for c in colors if c in c2), None)

    if c1_base and c2_base and c1_base == c2_base:
        return True
    if ('grey' in c1 or 'gray' in c1) and ('grey' in c2 or 'gray' in c2):
        return True
    return False


def find_single_matches(target_grist: float, target_yardage: float, stash: list) -> tuple:
    """Find single yarns that match the target grist."""
    enough, not_enough, unknown = [], [], []

    for yarn in stash:
        if grist_matches(target_grist, yarn['grist']):
            available = yarn.get('available_yards') or 0
            info = {
                'yarn': yarn,
                'grist_diff': abs(target_grist - yarn['grist']) / target_grist * 100
            }

            if not target_yardage:
                if available > 0:
                    info['have'] = available
                    unknown.append(info)
            elif available >= target_yardage:
                info['have'] = available
                enough.append(info)
            else:
                info['needed'] = target_yardage
                info['have'] = available
                not_enough.append(info)

    enough.sort(key=lambda x: x['grist_diff'])
    not_enough.sort(key=lambda x: x['grist_diff'])
    unknown.sort(key=lambda x: (-x.get('have', 0), x['grist_diff']))
    return enough, not_enough, unknown


def find_combo_matches(target_grist: float, target_yardage: float, stash: list, max_combos: int = 10) -> list:
    """Find yarn combinations that match the target grist."""
    combos = []

    for i, yarn_a in enumerate(stash):
        for yarn_b in stash[i+1:]:
            if not fuzzy_color_match(yarn_a['color'], yarn_b['color']):
                continue

            combined = calculate_combined_grist([yarn_a['grist'], yarn_b['grist']])
            if not combined or not grist_matches(target_grist, combined):
                continue

            has_a = yarn_a.get('available_yards') or 0
            has_b = yarn_b.get('available_yards') or 0

            both_enough = True
            if target_yardage:
                both_enough = has_a >= target_yardage and has_b >= target_yardage

            combos.append({
                'yarns': [yarn_a, yarn_b],
                'combined_grist': combined,
                'grist_diff': abs(target_grist - combined) / target_grist * 100,
                'has': [has_a, has_b],
                'enough': [has_a >= target_yardage if target_yardage else True,
                          has_b >= target_yardage if target_yardage else True],
                'both_enough': both_enough,
                'shared_color': yarn_a['color'] or yarn_b['color']
            })

            if len(combos) >= max_combos * 2:
                break
        if len(combos) >= max_combos * 2:
            break

    combos.sort(key=lambda x: (not x['both_enough'], x['grist_diff']))
    return combos[:max_combos]


# =============================================================================
# HTML Generation
# =============================================================================

def get_color_hex(color_name: str) -> str:
    """Convert color name to approximate hex color for display."""
    if not color_name:
        return '#ccc'

    color_lower = color_name.lower()

    color_map = {
        'red': '#e74c3c', 'blue': '#3498db', 'navy': '#2c3e50',
        'green': '#27ae60', 'yellow': '#f1c40f', 'orange': '#e67e22',
        'purple': '#9b59b6', 'pink': '#ff6b9d', 'brown': '#8b4513',
        'black': '#2c2c2c', 'white': '#f8f8f8', 'grey': '#95a5a6',
        'gray': '#95a5a6', 'cream': '#f5f5dc', 'beige': '#d4c4a8',
        'teal': '#1abc9c', 'coral': '#ff7f7f', 'burgundy': '#800020',
        'maroon': '#800000', 'olive': '#808000', 'gold': '#ffd700',
        'silver': '#c0c0c0', 'tan': '#d2b48c', 'charcoal': '#36454f',
    }

    for name, hex_val in color_map.items():
        if name in color_lower:
            return hex_val

    return '#a8d5ba'


def generate_html(pattern_data: dict, stash: list) -> str:
    """Generate beautiful HTML report."""

    pattern_name = pattern_data.get('pattern_name', 'Unknown Pattern')
    size = pattern_data.get('size', '')
    yarns = pattern_data.get('yarns', [])
    combined_grist = pattern_data.get('combined_grist')
    notes = pattern_data.get('notes', '')
    designer_name = pattern_data.get('designer_name', '')
    original_yarn_weight = pattern_data.get('original_yarn_weight', '')
    needle_sizes = pattern_data.get('needle_sizes', [])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yarn Match: {pattern_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            min-height: 100vh; padding: 2rem; color: #333; line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 2rem; border-radius: 16px; margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }}
        .header h1 {{ font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .header .size {{ font-size: 1.1rem; opacity: 0.9; }}
        .header .pattern-meta {{
            display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1rem; font-size: 0.95rem;
        }}
        .header .pattern-meta-item {{ display: flex; align-items: center; gap: 0.4rem; }}
        .header .pattern-meta-label {{ opacity: 0.7; }}
        .header .pattern-meta-value {{ font-weight: 500; }}
        .header .notes {{
            margin-top: 1rem; padding: 0.75rem 1rem;
            background: rgba(255,255,255,0.15); border-radius: 8px; font-size: 0.95rem;
        }}
        .section {{
            background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        .section-title {{
            font-size: 1.25rem; font-weight: 600; color: #667eea; margin-bottom: 1rem;
            display: flex; align-items: center; gap: 0.5rem;
        }}
        .requirements-table {{ width: 100%; border-collapse: collapse; }}
        .requirements-table th {{
            text-align: left; padding: 0.75rem; background: #f8f9fa;
            border-bottom: 2px solid #e9ecef; font-weight: 600; color: #495057;
        }}
        .requirements-table td {{ padding: 0.75rem; border-bottom: 1px solid #e9ecef; }}
        .grist-badge {{
            display: inline-block; padding: 0.25rem 0.75rem; background: #e9ecef;
            border-radius: 20px; font-size: 0.85rem; font-weight: 500;
        }}
        .combined-grist {{
            margin-top: 1rem; padding: 0.75rem 1rem;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            border-radius: 8px; font-weight: 500;
        }}
        .match-group {{ margin-bottom: 2rem; }}
        .match-group-title {{
            font-size: 1.1rem; font-weight: 600; color: #333; margin-bottom: 1rem;
            padding-bottom: 0.5rem; border-bottom: 2px solid #e9ecef;
        }}
        .match-card {{
            display: grid; grid-template-columns: auto 1fr auto; gap: 1rem; padding: 1rem;
            background: #f8f9fa; border-radius: 10px; margin-bottom: 0.75rem; align-items: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .match-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .match-icon {{
            width: 40px; height: 40px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-size: 1.25rem;
        }}
        .match-icon.enough {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .match-icon.not-enough {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .match-icon.combo {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .match-icon.unknown {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .match-details {{ min-width: 0; }}
        .match-name {{ font-weight: 600; color: #333; margin-bottom: 0.25rem; }}
        .match-meta {{ font-size: 0.85rem; color: #666; }}
        .match-meta span {{ margin-right: 1rem; }}
        .match-yardage {{ text-align: right; white-space: nowrap; }}
        .yardage-have {{ font-size: 1.1rem; font-weight: 600; }}
        .yardage-have.enough {{ color: #11998e; }}
        .yardage-have.not-enough {{ color: #eb3349; }}
        .yardage-need {{ font-size: 0.8rem; color: #666; }}
        .combo-card {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9f4ff 100%); border: 1px solid #c5dff8; }}
        .combo-yarns {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        .combo-yarn {{ display: flex; align-items: center; gap: 0.5rem; }}
        .combo-yarn-status {{ font-size: 0.9rem; }}
        .no-matches {{ text-align: center; padding: 2rem; color: #666; font-style: italic; }}
        .footer {{ text-align: center; padding: 1.5rem; color: #888; font-size: 0.85rem; }}
        .color-dot {{
            display: inline-block; width: 12px; height: 12px; border-radius: 50%;
            margin-right: 0.5rem; border: 1px solid rgba(0,0,0,0.1);
        }}
        @media (max-width: 600px) {{
            body {{ padding: 1rem; }}
            .match-card {{ grid-template-columns: auto 1fr; grid-template-rows: auto auto; }}
            .match-yardage {{ grid-column: 2; text-align: left; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{pattern_name}</h1>
            {f'<div class="size">Size: {size}</div>' if size else ''}
            <div class="pattern-meta">
                {f'<div class="pattern-meta-item"><span class="pattern-meta-label">Designer:</span> <span class="pattern-meta-value">{designer_name}</span></div>' if designer_name else ''}
                {f'<div class="pattern-meta-item"><span class="pattern-meta-label">Yarn Weight:</span> <span class="pattern-meta-value">{original_yarn_weight}</span></div>' if original_yarn_weight else ''}
                {f'<div class="pattern-meta-item"><span class="pattern-meta-label">Needles:</span> <span class="pattern-meta-value">{", ".join(needle_sizes)}</span></div>' if needle_sizes else ''}
            </div>
            {f'<div class="notes">{notes}</div>' if notes else ''}
        </div>

        <div class="section">
            <div class="section-title"><span>🧶</span> Yarn Requirements</div>
            <table class="requirements-table">
                <thead><tr><th>Yarn</th><th>Grist</th><th>Needed</th></tr></thead>
                <tbody>
'''

    for yarn in yarns:
        name = yarn.get('yarn_name', 'Unknown')
        grist = yarn.get('grist_yd_per_g')
        yardage = yarn.get('yards_needed')
        grams = yarn.get('grams_needed')
        grist_str = f"{grist:.3f} yd/g" if grist else "Unknown"
        yardage_str = f"{yardage:.0f} yards" if yardage else "Not specified"
        if grams:
            yardage_str += f" ({grams:.0f}g)"
        html += f'''<tr><td><strong>{name}</strong></td><td><span class="grist-badge">{grist_str}</span></td><td>{yardage_str}</td></tr>\n'''

    html += '''</tbody></table>\n'''

    if combined_grist:
        html += f'''<div class="combined-grist">⚠️ <strong>Held Together</strong> — Combined grist: <span class="grist-badge">{combined_grist:.3f} yd/g</span></div>\n'''

    html += '''</div><div class="section"><div class="section-title"><span>✨</span> Your Stash Matches</div>\n'''

    # Process each yarn requirement
    for yarn in yarns:
        target_grist = yarn.get('grist_yd_per_g')
        target_yardage = yarn.get('yards_needed')
        yarn_name = yarn.get('yarn_name', 'Unknown')

        if not target_grist:
            html += f'''<div class="match-group"><div class="match-group-title">Matches for: {yarn_name}</div><div class="no-matches">Cannot match — missing grist information</div></div>\n'''
            continue

        enough, not_enough, unknown = find_single_matches(target_grist, target_yardage, stash)
        combos = find_combo_matches(target_grist, target_yardage, stash)

        html += f'''<div class="match-group"><div class="match-group-title">Matches for: {yarn_name} <span style="font-weight: normal; color: #888;">(grist: {target_grist:.3f} yd/g{f", need {target_yardage:.0f} yards" if target_yardage else ""})</span></div>\n'''

        for match in enough:
            y = match['yarn']
            html += f'''<div class="match-card"><div class="match-icon enough">✓</div><div class="match-details"><div class="match-name">{y['name']}</div><div class="match-meta"><span>Grist: {y['grist']:.3f} yd/g ({match['grist_diff']:.1f}% diff)</span>{f'<span><span class="color-dot" style="background: {get_color_hex(y["color"])}"></span>{y["color"]}</span>' if y.get('color') else ''}</div></div><div class="match-yardage"><div class="yardage-have enough">{match.get("have", y.get("available_yards", 0)):.0f} yards</div><div class="yardage-need">✓ Enough!</div></div></div>\n'''

        for match in unknown[:10]:
            y = match['yarn']
            html += f'''<div class="match-card"><div class="match-icon unknown">?</div><div class="match-details"><div class="match-name">{y['name']}</div><div class="match-meta"><span>Grist: {y['grist']:.3f} yd/g ({match['grist_diff']:.1f}% diff)</span>{f'<span><span class="color-dot" style="background: {get_color_hex(y["color"])}"></span>{y["color"]}</span>' if y.get('color') else ''}</div></div><div class="match-yardage"><div class="yardage-have">{match.get("have", 0):.0f} yards</div><div class="yardage-need">available</div></div></div>\n'''

        for match in not_enough[:8]:
            y = match['yarn']
            html += f'''<div class="match-card"><div class="match-icon not-enough">✗</div><div class="match-details"><div class="match-name">{y['name']}</div><div class="match-meta"><span>Grist: {y['grist']:.3f} yd/g ({match['grist_diff']:.1f}% diff)</span>{f'<span><span class="color-dot" style="background: {get_color_hex(y["color"])}"></span>{y["color"]}</span>' if y.get('color') else ''}</div></div><div class="match-yardage"><div class="yardage-have not-enough">{match.get("have", 0):.0f} yards</div><div class="yardage-need">Need {match.get("needed", target_yardage):.0f}</div></div></div>\n'''

        for combo in combos[:5]:
            ya, yb = combo['yarns']
            status_a = "✓" if combo['enough'][0] else "✗"
            status_b = "✓" if combo['enough'][1] else "✗"
            html += f'''<div class="match-card combo-card"><div class="match-icon combo">🔗</div><div class="match-details"><div class="match-name">Combo: {ya['name']} + {yb['name']}</div><div class="match-meta"><span>Combined grist: {combo['combined_grist']:.3f} yd/g ({combo['grist_diff']:.1f}% diff)</span><span><span class="color-dot" style="background: {get_color_hex(combo['shared_color'])}"></span>{combo['shared_color']}</span></div><div class="combo-yarns" style="margin-top: 0.5rem; font-size: 0.9rem;"><div class="combo-yarn"><span class="combo-yarn-status">{status_a}</span><span>{ya['name']}: {combo['has'][0]:.0f} yards</span></div><div class="combo-yarn"><span class="combo-yarn-status">{status_b}</span><span>{yb['name']}: {combo['has'][1]:.0f} yards</span></div></div></div></div>\n'''

        if not enough and not not_enough and not unknown and not combos:
            html += '''<div class="no-matches">No matches found in your stash for this grist range.</div>\n'''

        html += '''</div>\n'''

    # Match combined grist if specified
    if combined_grist:
        max_yardage = max((y.get('yards_needed') or 0) for y in yarns) if yarns else None
        enough, not_enough, unknown = find_single_matches(combined_grist, max_yardage, stash)

        html += f'''<div class="match-group"><div class="match-group-title" style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); padding: 0.75rem; border-radius: 8px; border-bottom: none;">🧵 Single Yarns Matching Combined Grist <span style="font-weight: normal; color: #666;">({combined_grist:.3f} yd/g{f", need {max_yardage:.0f} yards" if max_yardage else ""})</span></div>\n'''

        for match in enough:
            y = match['yarn']
            html += f'''<div class="match-card"><div class="match-icon enough">✓</div><div class="match-details"><div class="match-name">{y['name']}</div><div class="match-meta"><span>Grist: {y['grist']:.3f} yd/g ({match['grist_diff']:.1f}% diff)</span>{f'<span><span class="color-dot" style="background: {get_color_hex(y["color"])}"></span>{y["color"]}</span>' if y.get('color') else ''}</div></div><div class="match-yardage"><div class="yardage-have enough">{match.get("have", y.get("available_yards", 0)):.0f} yards</div><div class="yardage-need">✓ Enough!</div></div></div>\n'''

        for match in unknown[:10]:
            y = match['yarn']
            html += f'''<div class="match-card"><div class="match-icon unknown">?</div><div class="match-details"><div class="match-name">{y['name']}</div><div class="match-meta"><span>Grist: {y['grist']:.3f} yd/g ({match['grist_diff']:.1f}% diff)</span>{f'<span><span class="color-dot" style="background: {get_color_hex(y["color"])}"></span>{y["color"]}</span>' if y.get('color') else ''}</div></div><div class="match-yardage"><div class="yardage-have">{match.get("have", 0):.0f} yards</div><div class="yardage-need">available</div></div></div>\n'''

        for match in not_enough[:5]:
            y = match['yarn']
            html += f'''<div class="match-card"><div class="match-icon not-enough">✗</div><div class="match-details"><div class="match-name">{y['name']}</div><div class="match-meta"><span>Grist: {y['grist']:.3f} yd/g ({match['grist_diff']:.1f}% diff)</span>{f'<span><span class="color-dot" style="background: {get_color_hex(y["color"])}"></span>{y["color"]}</span>' if y.get('color') else ''}</div></div><div class="match-yardage"><div class="yardage-have not-enough">{match.get("have", 0):.0f} yards</div><div class="yardage-need">Need {max_yardage:.0f}</div></div></div>\n'''

        if not enough and not not_enough and not unknown:
            html += '''<div class="no-matches">No single-yarn matches for combined grist.</div>\n'''

        html += '''</div>\n'''

    html += f'''</div><div class="footer">Generated by Yarn Matcher • {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div></div></body></html>'''

    return html


def sanitize_filename(name: str) -> str:
    """Sanitize pattern name for use in filename."""
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[-\s]+', '-', sanitized)
    return sanitized.strip('-').lower()[:50]


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point."""
    print("=" * 60)
    print("YARN MATCHER - Match pattern yarns with your stash")
    print("=" * 60)
    print()
    print("Paste your pattern JSON (press Enter, then Ctrl+D when done):")
    print("-" * 60)

    # Read JSON from stdin
    try:
        json_input = sys.stdin.read().strip()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return

    if not json_input:
        print("No JSON provided.")
        return

    # Parse JSON
    try:
        pattern_data = json.loads(json_input)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return

    pattern_name = pattern_data.get('pattern_name', 'Unknown Pattern')
    size = pattern_data.get('size', '')
    yarns = pattern_data.get('yarns', [])

    print()
    print(f"Pattern: {pattern_name}")
    if size:
        print(f"Size: {size}")
    print(f"Yarns: {len(yarns)}")

    for y in yarns:
        grist_str = f"{y['grist_yd_per_g']:.3f} yd/g" if y.get('grist_yd_per_g') else "unknown"
        print(f"  - {y.get('yarn_name', 'Unknown')}: {grist_str}")

    # Fetch stash
    print()
    print("Fetching your yarn stash from Airtable...")
    try:
        stash = fetch_stash()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching stash: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"Found {len(stash)} yarns in your stash")

    # Generate HTML
    print()
    print("Generating HTML report...")
    html = generate_html(pattern_data, stash)

    # Save file
    safe_name = sanitize_filename(pattern_name)
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"pattern_match_{safe_name}_{date_str}.html"

    output_dir = Path(__file__).parent / 'pattern_matches'
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Saved: {filepath}")

    # Open in browser
    print("Opening in browser...")
    webbrowser.open(f'file://{filepath.absolute()}')

    print()
    print("Done!")


if __name__ == "__main__":
    main()
