#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
# EBCONT fork: converts Confluence storage format (XHTML) to Markdown so that
# structure such as tables, headings and lists survives indexing.
#
"""Confluence storage format -> Markdown conversion (EBCONT fork)."""

import re

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

from connectors.logger import logger

# Macros whose rich text body is rendered as a quote block
PANEL_MACROS = {"info", "note", "warning", "tip", "panel"}
# Macros whose plain text body is rendered as a code block
CODE_MACROS = {"code", "noformat"}

_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")


class _ConfluenceMarkdownConverter(MarkdownConverter):
    def convert_td(self, el, text, parent_tags):
        # Line breaks inside a cell would break the Markdown table row.
        cell = " ".join(text.split()).replace("|", "\\|")
        colspan = 1
        if el.has_attr("colspan") and str(el["colspan"]).isdigit():
            colspan = max(1, min(1000, int(el["colspan"])))
        return " " + cell + " |" * colspan

    convert_th = convert_td


def _macro_name(macro):
    return (macro.get("ac:name") or "").lower()


def _replace_macros(soup):
    for macro in soup.find_all("ac:structured-macro"):
        if macro.parent is None:  # already removed together with an outer macro
            continue
        name = _macro_name(macro)

        if name in CODE_MACROS:
            body = macro.find("ac:plain-text-body")
            pre = soup.new_tag("pre")
            pre.string = body.get_text() if body else ""
            macro.replace_with(pre)

        elif name in PANEL_MACROS:
            quote = soup.new_tag("blockquote")
            rich_body = macro.find("ac:rich-text-body")
            if rich_body:
                quote.extend(list(rich_body.contents))
            macro.replace_with(quote)

        elif name == "jira":
            key = macro.find("ac:parameter", {"ac:name": "key"})
            if key and key.get_text(strip=True):
                macro.replace_with(f"Jira: {key.get_text(strip=True)}")
            else:
                macro.decompose()

    # Remaining macro parameters (e.g. code language, panel titles) are noise
    for parameter in soup.find_all("ac:parameter"):
        parameter.decompose()


def _replace_links(soup):
    """Links to other pages: keep the visible text, fall back to the page title."""
    for link in soup.find_all("ac:link"):
        text = link.get_text(" ", strip=True)
        if not text:
            page = link.find("ri:page")
            text = page.get("ri:content-title", "") if page else ""
        link.replace_with(text)


def _flatten_table_cells(soup):
    """Join multiple values in one cell (<li>, <br>, several <p>) with ', '."""
    for cell in soup.find_all(["td", "th"]):
        for br in cell.find_all("br"):
            br.replace_with("\n")
        for block in cell.find_all(["li", "p", "div"]):
            block.insert_after("\n")
        parts = [" ".join(part.split()) for part in cell.get_text().split("\n")]
        cell.clear()
        cell.string = ", ".join(part for part in parts if part)


def confluence_storage_to_markdown(html):
    """Convert Confluence storage format to Markdown.

    Returns the input unchanged when it is empty/None and None when the
    conversion fails, so a single broken page never fails the whole sync.
    """
    if not html:
        return html
    try:
        soup = BeautifulSoup(html, "html.parser")
        _replace_macros(soup)
        _replace_links(soup)
        _flatten_table_cells(soup)
        for tag in soup.find_all("colgroup"):
            tag.decompose()

        markdown = _ConfluenceMarkdownConverter(
            heading_style="ATX",
            bullets="-",
            table_infer_header=True,
        ).convert_soup(soup)
        return _MULTIPLE_BLANK_LINES.sub("\n\n", markdown).strip()
    except Exception as e:
        logger.warning(f"Could not convert Confluence content to Markdown: {e}")
        return None
