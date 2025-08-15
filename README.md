# scraper-webUI

A very simple Python web scraper with a web UI, not very efficient.

## Features

- CSS selector based scraping (via BeautifulSoup)
- Optional attribute extraction (e.g., `src`, `data-id`)
- Robots.txt check (opt-out)
- Export to CSV, JSON or direct download for images

## Quickstart

1. Clone the repository.

2. Install dependencies:

```
pip install -r requirements.txt
```

3. Run it:

```
python app.py
```

3. Open `http://127.0.0.1:5000` in your browser.

## Direct URL usage

You can call endpoints directly by query string.

### Results page
GET `/results` with params:

- `url`: target page to scrape (required)
- `selector_type`: `css` (default)
- `selector`: CSS selector to match (required)
- `attribute`: optional attribute to extract from each element (e.g. `href`, `src`)
- `user_agent`: optional custom UA
- `max_items`: optional cap (integer)
- `respect_robots`: `1`/`0`, `true`/`false` (default `1`)
- `next_selector`: CSS selector for the next page link (pagination)
- `max_pages`: max pages to follow (integer)
- `detail_url_selector`: CSS selector (relative to each result element) to find its detail link
- `detail_url_attribute`: attribute for the detail link (default `href`)
- `detail_image_selector`: CSS selector on the detail page to find the full image
- `detail_image_attribute`: attribute for the full image (default `src`)

Examples:

- Links on example.com (hrefs):
  - `/results?url=https://example.com/&selector=a&attribute=href`
- Quotes text:
  - `/results?url=https://quotes.toscrape.com/&selector=.quote%20.text`
- Books to Scrape images (thumbnails):
  - `/results?url=https://books.toscrape.com/&selector=img&attribute=src&max_items=20`

### Export

GET `/export` with the same params as `/results`, plus:

- `format`: `csv` (default) or `json`

Examples:

- CSV of example.com links: `/export?format=csv&url=https://example.com/&selector=a&attribute=href`
- JSON of books images: `/export?format=json&url=https://books.toscrape.com/&selector=img&attribute=src&max_items=20`

### Download images

- Single image: `/download-image?url=FULL_IMAGE_URL`
- All detected images as ZIP (uses same scrape params as `/results`):
  - `/download-all-images?url=...&selector=...&detail_image_selector=...&...`

## Presets (JSON)

Presets are loaded from `presets.json` at startup. Each entry is an object with:

- `id`, `name`, `url`, `selector`, `attribute`, `user_agent`, `max_items`,
  `next_selector`, `max_pages`, `respect_robots`, `detail_url_selector`,
  `detail_url_attribute`, `detail_image_selector`, `detail_image_attribute`.

Editing `presets.json` updates the dropdown on the home page automatically.

## Usage tips

- Use a broad selector like `a` to list links; add attribute `href` or leave blank to see text.
- Respect target site Terms of Service. Keep request volume low.
- If you need XPATH, wire in `parsel`/`lxml` and extend `scraper/core.py`.

## Licensing
```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
