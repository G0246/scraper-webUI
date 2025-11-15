# scraper-webUI
# A not very efficient scraper web UI.
# app.py
# By G0246

import os
import io
import re
import csv
import json
import zipfile
import concurrent.futures
import requests
from typing import Optional, List
from urllib.parse import urlparse

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    flash,
)

from scraper.core import (
    is_allowed_by_robots,
    scrape_with_selector,
    scrape_paginated,
    ScrapeResult,
)

from scraper.presets import load_presets_any, save_or_update_preset, delete_preset

# Flask route handlers
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            target_url = request.form.get("target_url", "").strip()
            selector_type = request.form.get("selector_type", "css").strip()
            selector = request.form.get("selector", "").strip()
            attribute = request.form.get("attribute", "").strip()
            user_agent = request.form.get("user_agent", "").strip()
            max_items = request.form.get("max_items", "").strip()
            fast_mode = request.form.get("fast_mode") is not None
            randomize_user_agent = request.form.get("randomize_user_agent") is not None
            next_selector = request.form.get("next_selector", "").strip()
            max_pages = request.form.get("max_pages", "").strip()
            detail_url_selector = request.form.get("detail_url_selector", "").strip()
            detail_url_attribute = request.form.get("detail_url_attribute", "").strip()
            detail_image_selector = request.form.get("detail_image_selector", "").strip()
            detail_image_attribute = request.form.get("detail_image_attribute", "").strip()
            respect_robots = request.form.get("respect_robots") is not None

            if not target_url:
                flash("Please provide a URL to scrape.", "error")
                return redirect(url_for("index"))

            if not selector:
                flash("Please provide a selector.", "error")
                return redirect(url_for("index"))

            query_args = {
                "url": target_url,
                "selector_type": selector_type or "css",
                "selector": selector,
                "attribute": attribute,
                "user_agent": user_agent,
                "respect_robots": "1" if respect_robots else "0",
            }

            if max_items.isdigit():
                query_args["max_items"] = max_items
            if next_selector:
                query_args["next_selector"] = next_selector
            if max_pages.isdigit():
                query_args["max_pages"] = max_pages
            if fast_mode:
                query_args["fast_mode"] = "1"
            if randomize_user_agent:
                query_args["randomize_user_agent"] = "1"
            if detail_url_selector:
                query_args["detail_url_selector"] = detail_url_selector
            if detail_url_attribute:
                query_args["detail_url_attribute"] = detail_url_attribute
            if detail_image_selector:
                query_args["detail_image_selector"] = detail_image_selector
            if detail_image_attribute:
                query_args["detail_image_attribute"] = detail_image_attribute

            return redirect(url_for("results", **query_args))

        # Prefill support via query params on GET
        presets = load_presets_any(os.path.dirname(__file__))
        return render_template("index.html", presets=presets)

    @app.route("/presets/save", methods=["POST"])
    def api_save_preset():
        try:
            data = request.get_json(silent=True) or {}
            normalized = save_or_update_preset(os.path.dirname(__file__), data)
            return {"ok": True, "preset": normalized}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 400

    @app.route("/presets/delete", methods=["POST"])
    def api_delete_preset():
        try:
            data = request.get_json(silent=True) or {}
            pid = (data.get("id") or "").strip()
            if not pid:
                return {"ok": False, "error": "id is required"}, 400
            existed = delete_preset(os.path.dirname(__file__), pid)
            return {"ok": True, "deleted": existed}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 400

    # Results page
    @app.route("/results", methods=["GET"])
    def results():
        target_url = request.args.get("url", "").strip()
        selector_type = request.args.get("selector_type", "css").strip().lower()
        selector = request.args.get("selector", "").strip()
        attribute = request.args.get("attribute", "").strip() or None
        user_agent = request.args.get("user_agent", "").strip() or None
        max_items_raw = request.args.get("max_items", "").strip()
        fast_mode = (request.args.get("fast_mode", "").strip().lower() in {"1", "true", "on", "yes"})
        next_selector = request.args.get("next_selector", "").strip() or None
        max_pages_raw = request.args.get("max_pages", "").strip()
        detail_url_selector = request.args.get("detail_url_selector", "").strip() or None
        detail_url_attribute = request.args.get("detail_url_attribute", "").strip() or "href"
        detail_image_selector = request.args.get("detail_image_selector", "").strip() or None
        detail_image_attribute = request.args.get("detail_image_attribute", "").strip() or "src"
        respect_raw = request.args.get("respect_robots", "1").strip().lower()
        respect_robots = respect_raw in {"1", "true", "yes", "on"}
        randomize_user_agent = (request.args.get("randomize_user_agent", "").strip().lower() in {"1", "true", "on", "yes"})

        try:
            max_items: Optional[int] = int(max_items_raw) if max_items_raw else None
        except ValueError:
            max_items = None
        try:
            max_pages: Optional[int] = int(max_pages_raw) if max_pages_raw else None
        except ValueError:
            max_pages = None

        error_message: Optional[str] = None
        result: Optional[ScrapeResult] = None
        breadcrumb_trail: List[dict] = []

        if not target_url or not selector:
            error_message = "URL and selector are required."
        else:
            try:
                def is_canceled() -> bool:
                    return False
                def track_the_journey(event: dict) -> None:
                    breadcrumb_trail.append(event)
                if respect_robots and not is_allowed_by_robots(target_url, user_agent or "scraper-webUI"):
                    error_message = "Scraping is disallowed by robots.txt for the provided URL."
                else:
                    if next_selector or max_pages:
                        result = scrape_paginated(
                            url=target_url,
                            selector_type=selector_type,
                            selector=selector,
                            next_selector=next_selector,
                            attribute_name=attribute,
                            user_agent=(None if randomize_user_agent else user_agent),
                            max_items=max_items,
                            max_pages=max_pages,
                            fast_mode=fast_mode,
                            is_canceled=is_canceled,
                            progress_cb=track_the_journey,
                            detail_url_selector=detail_url_selector,
                            detail_url_attribute=detail_url_attribute,
                            detail_image_selector=detail_image_selector,
                            detail_image_attribute=detail_image_attribute,
                        )
                    else:
                        result = scrape_with_selector(
                            url=target_url,
                            selector_type=selector_type,
                            selector=selector,
                            attribute_name=attribute,
                            user_agent=(None if randomize_user_agent else user_agent),
                            max_items=max_items,
                            fast_mode=fast_mode,
                            is_canceled=is_canceled,
                            progress_cb=track_the_journey,
                            detail_url_selector=detail_url_selector,
                            detail_url_attribute=detail_url_attribute,
                            detail_image_selector=detail_image_selector,
                            detail_image_attribute=detail_image_attribute,
                        )
            except Exception as exc:
                error_message = f"Error while scraping: {exc}"

        return render_template(
            "results.html",
            query={
                "url": target_url,
                "selector_type": selector_type,
                "selector": selector,
                "attribute": attribute or "",
                "user_agent": user_agent or "",
                "max_items": max_items or "",
                "next_selector": next_selector or "",
                "max_pages": max_pages or "",
                "fast_mode": fast_mode,
                "detail_url_selector": detail_url_selector or "",
                "detail_url_attribute": detail_url_attribute or "",
                "detail_image_selector": detail_image_selector or "",
                "detail_image_attribute": detail_image_attribute or "",
                "respect_robots": respect_robots,
                "randomize_user_agent": randomize_user_agent,
            },
            result=result,
            error_message=error_message,
            progress_events=breadcrumb_trail,
        )

    # Export functionality
    @app.route("/export", methods=["GET"])
    def export():
        export_format = request.args.get("format", "csv").strip().lower()
        target_url = request.args.get("url", "").strip()
        selector_type = request.args.get("selector_type", "css").strip().lower()
        selector = request.args.get("selector", "").strip()
        attribute = request.args.get("attribute", "").strip() or None
        user_agent = request.args.get("user_agent", "").strip() or None
        max_items_raw = request.args.get("max_items", "").strip()
        fast_mode = (request.args.get("fast_mode", "").strip().lower() in {"1", "true", "on", "yes"})
        next_selector = request.args.get("next_selector", "").strip() or None
        max_pages_raw = request.args.get("max_pages", "").strip()
        detail_url_selector = request.args.get("detail_url_selector", "").strip() or None
        detail_url_attribute = request.args.get("detail_url_attribute", "").strip() or "href"
        detail_image_selector = request.args.get("detail_image_selector", "").strip() or None
        detail_image_attribute = request.args.get("detail_image_attribute", "").strip() or "src"
        respect_raw = request.args.get("respect_robots", "1").strip().lower()
        respect_robots = respect_raw in {"1", "true", "yes", "on"}
        randomize_user_agent = (request.args.get("randomize_user_agent", "").strip().lower() in {"1", "true", "on", "yes"})

        try:
            max_items: Optional[int] = int(max_items_raw) if max_items_raw else None
        except ValueError:
            max_items = None
        try:
            max_pages: Optional[int] = int(max_pages_raw) if max_pages_raw else None
        except ValueError:
            max_pages = None

        if not target_url or not selector:
            flash("URL and selector are required to export.", "error")
            return redirect(url_for("index"))

        if respect_robots and not is_allowed_by_robots(target_url, user_agent or "scraper-webUI"):
            flash("Export blocked by robots.txt.", "error")
            return redirect(url_for("index"))

        def nobody_canceled_yet() -> bool:
            return False

        if next_selector or max_pages:
            result = scrape_paginated(
                url=target_url,
                selector_type=selector_type,
                selector=selector,
                next_selector=next_selector,
                attribute_name=attribute,
                user_agent=(None if randomize_user_agent else user_agent),
                max_items=max_items,
                max_pages=max_pages,
                fast_mode=fast_mode,
                is_canceled=nobody_canceled_yet,
                detail_url_selector=detail_url_selector,
                detail_url_attribute=detail_url_attribute,
                detail_image_selector=detail_image_selector,
                detail_image_attribute=detail_image_attribute,
            )
        else:
            result = scrape_with_selector(
                url=target_url,
                selector_type=selector_type,
                selector=selector,
                attribute_name=attribute,
                user_agent=(None if randomize_user_agent else user_agent),
                max_items=max_items,
                fast_mode=fast_mode,
                is_canceled=nobody_canceled_yet,
                detail_url_selector=detail_url_selector,
                detail_url_attribute=detail_url_attribute,
                detail_image_selector=detail_image_selector,
                detail_image_attribute=detail_image_attribute,
            )

        if export_format == "json":
            json_goodies = json.dumps([item for item in result.items], ensure_ascii=False, indent=2)
            buffer = io.BytesIO(json_goodies.encode("utf-8"))
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype="application/json; charset=utf-8",
                as_attachment=True,
                download_name="scrape.json",
            )

        # Default to CSV
        text_buffer = io.StringIO()
        csv_wizard = csv.DictWriter(
            text_buffer,
            fieldnames=["index", "tag", "text", "href", "attribute_value", "image_url", "html"],
            extrasaction="ignore",
        )
        csv_wizard.writeheader()
        for item in result.items:
            csv_wizard.writerow(item)
        data = text_buffer.getvalue().encode("utf-8")
        buffer = io.BytesIO(data)
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name="scrape.csv",
        )

    @app.route("/download-image", methods=["GET"])
    def download_image():
        image_url = request.args.get("url", "").strip()
        if not image_url:
            flash("Missing image URL", "error")
            return redirect(url_for("index"))

        try:
            headers = {"User-Agent": request.args.get("user_agent", "scraper-webUI")}
            resp = requests.get(image_url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            flash(f"Failed to fetch image: {exc}", "error")
            return redirect(url_for("index"))

        parsed = urlparse(image_url)
        filename = os.path.basename(parsed.path) or "image"
        content_type = resp.headers.get("Content-Type", "application/octet-stream")

        return send_file(
            io.BytesIO(resp.content),
            mimetype=content_type,
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/download-all-images", methods=["GET"])
    def download_all_images():
        target_url = request.args.get("url", "").strip()
        selector_type = request.args.get("selector_type", "css").strip().lower()
        selector = request.args.get("selector", "").strip()
        attribute = request.args.get("attribute", "").strip() or None
        user_agent = request.args.get("user_agent", "").strip() or None
        max_items_raw = request.args.get("max_items", "").strip()
        next_selector = request.args.get("next_selector", "").strip() or None
        max_pages_raw = request.args.get("max_pages", "").strip()
        detail_url_selector = request.args.get("detail_url_selector", "").strip() or None
        detail_url_attribute = request.args.get("detail_url_attribute", "").strip() or "href"
        detail_image_selector = request.args.get("detail_image_selector", "").strip() or None
        detail_image_attribute = request.args.get("detail_image_attribute", "").strip() or "src"
        fast_mode = (request.args.get("fast_mode", "").strip().lower() in {"1", "true", "on", "yes"})
        randomize_user_agent = (request.args.get("randomize_user_agent", "").strip().lower() in {"1", "true", "on", "yes"})
        respect_raw = request.args.get("respect_robots", "1").strip().lower()
        respect_robots = respect_raw in {"1", "true", "yes", "on"}

        try:
            max_items: Optional[int] = int(max_items_raw) if max_items_raw else None
        except ValueError:
            max_items = None
        try:
            max_pages: Optional[int] = int(max_pages_raw) if max_pages_raw else None
        except ValueError:
            max_pages = None

        if not target_url or not selector:
            flash("URL and selector are required.", "error")
            return redirect(url_for("index"))

        if respect_robots and not is_allowed_by_robots(target_url, user_agent or "scraper-webUI"):
            flash("Download blocked by robots.txt.", "error")
            return redirect(url_for("index"))

        def still_not_canceled() -> bool:
            return False

        if next_selector or max_pages:
            result = scrape_paginated(
                url=target_url,
                selector_type=selector_type,
                selector=selector,
                next_selector=next_selector,
                attribute_name=attribute,
                user_agent=(None if randomize_user_agent else user_agent),
                max_items=max_items,
                max_pages=max_pages,
                fast_mode=fast_mode,
                is_canceled=still_not_canceled,
                detail_url_selector=detail_url_selector,
                detail_url_attribute=detail_url_attribute,
                detail_image_selector=detail_image_selector,
                detail_image_attribute=detail_image_attribute,
            )
        else:
            result = scrape_with_selector(
                url=target_url,
                selector_type=selector_type,
                selector=selector,
                attribute_name=attribute,
                user_agent=(None if randomize_user_agent else user_agent),
                max_items=max_items,
                fast_mode=fast_mode,
                is_canceled=still_not_canceled,
                detail_url_selector=detail_url_selector,
                detail_url_attribute=detail_url_attribute,
                detail_image_selector=detail_image_selector,
                detail_image_attribute=detail_image_attribute,
            )

        treasure_trove = [it for it in result.items if it.get("image_url")]
        if not treasure_trove:
            flash("No images detected to download.", "error")
            return redirect(url_for("results", **request.args))

        def sanitize(name: str) -> str:
            return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120]

        # Use a session for connection pooling across image downloads
        img_session = requests.Session()
        img_session.headers.update({"User-Agent": user_agent or "scraper-webUI"})
        zip_buffer = io.BytesIO()

        def fetch(idx_and_url):
            idx, img_url = idx_and_url
            try:
                resp = img_session.get(img_url, timeout=20)
                resp.raise_for_status()
                return idx, img_url, resp
            except Exception:
                return idx, img_url, None

        # Use ZIP_DEFLATED with compression level for better performance
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                for idx, img_url, resp in ex.map(fetch, [(i, it["image_url"]) for i, it in enumerate(treasure_trove)]):
                    if resp is None:
                        continue
                    parsed = urlparse(img_url)
                    base = os.path.basename(parsed.path) or f"image_{idx}"
                    root, ext = os.path.splitext(base)
                    if not ext:
                        ct = resp.headers.get("Content-Type", "")
                        if "png" in ct:
                            ext = ".png"
                        elif "webp" in ct:
                            ext = ".webp"
                        elif "gif" in ct:
                            ext = ".gif"
                        else:
                            ext = ".jpg"
                    filename = f"{idx:04d}_{sanitize(root)}{ext}"
                    zf.writestr(filename, resp.content)

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="images.zip",
        )

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
