# Yarn Matcher

Match Ravelry knitting patterns with your personal yarn stash stored in Airtable.

## How to Use

### Step 1: Get Pattern JSON

Open a new Claude chat (claude.ai) and use this prompt:

```
YARN PATTERN ANALYZER

Pattern URL (for reference): [paste URL here]
Size I'm making: [size name/number]

Pattern details:
[paste entire pattern page text here]

Please parse this and return a JSON object with:
- pattern_name
- designer_name
- size
- original_yarn_weight (e.g., "Fingering", "DK", "Worsted")
- needle_sizes (array, e.g., ["US 6 - 4.0mm", "US 8 - 5.0mm"])
- yarns array, where each yarn has:
  - yarn_name
  - grist_yd_per_g (yards per gram - calculate from skein info like "50g/150m")
  - grams_needed (for my size)
  - yards_needed (for my size)
  - color (e.g., "Color A (main)", "Color B (contrast)")
  - held_together_with (null or yarn name if held together)
- combined_grist (if yarns held together)
- notes (any relevant construction info)

Format as clean JSON only, no markdown code blocks.
```

### Step 2: Run the Matcher

```bash
cd /Users/vorimor/Documents/Household/Yarn
python3 yarn_matcher.py
```

Paste the JSON when prompted, press Enter, then Ctrl+D.

### Step 3: View Results

The script generates an HTML report and opens it automatically in your browser.

## Setup Requirements

- Python 3.11+
- Airtable account with Making database
- API credentials in `credentials.py` (see below)

## Credentials Setup

Create `credentials.py` with:

```python
# Ravelry API (not currently used)
RAVELRY_ACCESS_KEY = "your-key"
RAVELRY_PERSONAL_KEY = "your-key"

# Airtable API
AIRTABLE_TOKEN = "your-token"
AIRTABLE_BASE_ID = "your-base-id"
AIRTABLE_TABLE_NAME = "Yarn"
```

## Output

HTML reports saved to: `pattern_matches/pattern_match_[pattern-name]_[date].html`
