# scraper-webUI

A very minimal Python web scraper with a web UI, not very efficient.

## Features

- CSS selector based scraping (via BeautifulSoup)
- Optional attribute extraction (e.g., `src`, `data-id`)
- Robots.txt check (opt-out)
- Export to CSV or JSON

## Quickstart

1. Create a virtual environment and install dependencies (Recommended):

```
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Run the app:

```
python app.py
```

3. Open `http://127.0.0.1:5000` in your browser.

## Usage tips

- Use a broad selector like `a` to list links; add attribute `href` or leave blank to see text.
- Respect target site Terms of Service. Keep request volume low.
- If you need XPATH, wire in `parsel`/`lxml` and extend `scraper/core.py`.

## Licensing

This project is licensed under the GPL-3.0. See `LICENSE` for details.
