#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Tests for the Confluence storage format -> Markdown conversion (EBCONT fork)."""

from unittest.mock import patch

import pytest

from connectors.sources.confluence_markdown import confluence_storage_to_markdown


@pytest.mark.parametrize("value", [None, ""])
def test_empty_input_is_returned_unchanged(value):
    assert confluence_storage_to_markdown(value) == value


def test_plain_paragraph():
    assert confluence_storage_to_markdown("<p>This is a test page</p>") == (
        "This is a test page"
    )


def test_headings_and_lists():
    html = (
        "<h1>Server</h1><p>Intro</p>"
        "<h2>Wartung</h2><ul><li>Patchday Dienstag</li><li>Reboot</li></ul>"
    )
    assert confluence_storage_to_markdown(html) == (
        "# Server\n\nIntro\n\n## Wartung\n\n- Patchday Dienstag\n- Reboot"
    )


def test_table_keeps_rows_and_joins_multi_value_cells():
    html = (
        "<h2>Team</h2>"
        "<table><colgroup><col/><col/><col/></colgroup><tbody>"
        "<tr><th><p>Name</p></th><th><p>Role</p></th>"
        "<th><p>Members</p></th></tr>"
        "<tr><td><p>Alice Example</p></td><td><p>Lead, Group A</p></td>"
        "<td><ul><li>Bob Sample</li><li>Carol Demo</li></ul></td></tr>"
        "<tr><td><p>Dave Test</p></td><td><p>Team Lead</p></td>"
        "<td><p>Erin Mock<br/>Frank Dummy</p></td></tr>"
        "</tbody></table>"
    )
    assert confluence_storage_to_markdown(html) == (
        "## Team\n\n"
        "| Name | Role | Members |\n"
        "| --- | --- | --- |\n"
        "| Alice Example | Lead, Group A | Bob Sample, Carol Demo |\n"
        "| Dave Test | Team Lead | Erin Mock, Frank Dummy |"
    )


def test_table_without_th_uses_first_row_as_header():
    html = (
        "<table><tbody><tr><td>Server</td><td>IP</td></tr>"
        "<tr><td>srv-01</td><td>10.0.0.1</td></tr></tbody></table>"
    )
    assert confluence_storage_to_markdown(html) == (
        "| Server | IP |\n| --- | --- |\n| srv-01 | 10.0.0.1 |"
    )


def test_pipe_in_cell_is_escaped():
    html = (
        "<table><tbody><tr><th>Befehl</th></tr>"
        "<tr><td>grep a | wc -l</td></tr></tbody></table>"
    )
    assert "| grep a \\| wc -l |" in confluence_storage_to_markdown(html)


def test_code_macro_becomes_code_block():
    html = (
        '<ac:structured-macro ac:name="code">'
        '<ac:parameter ac:name="language">bash</ac:parameter>'
        "<ac:plain-text-body><![CDATA[systemctl restart app]]></ac:plain-text-body>"
        "</ac:structured-macro>"
    )
    assert confluence_storage_to_markdown(html) == "```\nsystemctl restart app\n```"


def test_info_macro_becomes_quote_without_parameters():
    html = (
        '<ac:structured-macro ac:name="info">'
        '<ac:parameter ac:name="title">Hinweis</ac:parameter>'
        "<ac:rich-text-body><p>Stand: Q3</p></ac:rich-text-body>"
        "</ac:structured-macro>"
    )
    assert confluence_storage_to_markdown(html) == "> Stand: Q3"


def test_jira_macro_keeps_issue_key():
    html = (
        "<p>Siehe "
        '<ac:structured-macro ac:name="jira">'
        '<ac:parameter ac:name="server">Jira</ac:parameter>'
        '<ac:parameter ac:name="key">PROJ-123</ac:parameter>'
        "</ac:structured-macro></p>"
    )
    assert confluence_storage_to_markdown(html) == "Siehe Jira: PROJ-123"


def test_page_link_without_body_uses_page_title():
    html = '<p>Siehe <ac:link><ri:page ri:content-title="Onboarding"/></ac:link></p>'
    assert confluence_storage_to_markdown(html) == "Siehe Onboarding"


def test_page_link_with_body_uses_link_text():
    html = (
        '<p><ac:link><ri:page ri:content-title="Onboarding"/>'
        "<ac:plain-text-link-body><![CDATA[hier]]></ac:plain-text-link-body>"
        "</ac:link></p>"
    )
    assert confluence_storage_to_markdown(html) == "hier"


def test_conversion_error_returns_none():
    with patch(
        "connectors.sources.confluence_markdown.BeautifulSoup",
        side_effect=ValueError("broken"),
    ):
        assert confluence_storage_to_markdown("<p>x</p>") is None
