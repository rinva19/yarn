# Rebecca's Knits

**Live site:** https://rinva19.github.io/yarn/

## To Update the Website

After adding new projects in Airtable, run these two commands:

```bash
python3 ~/Documents/Household/Yarn/generate_knits_gallery.py

cd ~/Documents/Household/Yarn && git add -A && git commit -m "Update gallery" && git push
```

The site updates automatically within a few minutes after pushing.

---

# Yarn Matcher

Match Ravelry knitting patterns with your yarn stash.

### Step 1: Get Pattern JSON

Open Claude (claude.ai) and use this prompt:

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
- notes (single string of relevant construction info)

Format as clean JSON only, no markdown code blocks.
```

### Step 2: Run the Matcher

```bash
python3 ~/Documents/Household/Yarn/yarn_matcher.py
```

Paste the JSON, press Enter, then Ctrl+D.

### Step 3: View Results

The script generates an HTML report and opens it in your browser.

Reports saved to: `pattern_matches/pattern_match_[pattern-name]_[date].html`
