"""Convert map.pdf to SVG and extract clickable link areas for HTML overlay."""
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "map.pdf"
SVG_PATH = ROOT / "map.svg"


def link_href(link: dict) -> str | None:
    kind = link.get("kind", fitz.LINK_NONE)
    if kind == fitz.LINK_URI:
        return link.get("uri")
    if kind == fitz.LINK_NAMED:
        name = link.get("nameddest")
        return f"#{name}" if name else None
    if kind in (fitz.LINK_GOTO, fitz.LINK_GOTOR):
        page = link.get("page", -1)
        if page >= 0:
            return f"#page-{page + 1}"
    return None


def rect_to_percent(rect: fitz.Rect, page_rect: fitz.Rect) -> dict:
    return {
        "left": round((rect.x0 / page_rect.width) * 100, 4),
        "top": round((rect.y0 / page_rect.height) * 100, 4),
        "width": round((rect.width / page_rect.width) * 100, 4),
        "height": round((rect.height / page_rect.height) * 100, 4),
    }


def main() -> None:
    doc = fitz.open(PDF_PATH)
    page = doc[0]
    page_rect = page.rect

    svg = page.get_svg_image()
    SVG_PATH.write_text(svg, encoding="utf-8")

    links = []
    for link in page.get_links():
        href = link_href(link)
        rect = link.get("from")
        if not href or not rect:
            continue
        links.append(
            {
                "href": href,
                "title": link.get("title") or "",
                **rect_to_percent(rect, page_rect),
            }
        )

    payload = {
        "width": round(page_rect.width, 3),
        "height": round(page_rect.height, 3),
        "links": links,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    index_path = ROOT / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    marker_start = '<script id="map-link-data" type="application/json">'
    marker_end = "</script>"
    start = index_html.index(marker_start) + len(marker_start)
    end = index_html.index(marker_end, start)
    index_path.write_text(
        index_html[:start] + "\n    " + payload_json + "\n  " + index_html[end:],
        encoding="utf-8",
    )

    doc.close()
    print(f"Wrote {SVG_PATH.name} ({SVG_PATH.stat().st_size:,} bytes)")
    print(f"Updated index.html with {len(links)} clickable area(s)")


if __name__ == "__main__":
    main()
