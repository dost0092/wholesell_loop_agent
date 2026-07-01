"""Phase 1 parser tests — no network or database required."""

from app.sources.tx.dallas_trw import parse_dallas_unpaid_summary
from app.sources.tx.harris_tax_sale import parse_harris_tax_sale_html
from app.sources.tx.tarrant_tax_sale import parse_tarrant_sale_html
from app.sources.http import load_fixture


def test_harris_parser_reads_fixture():
    html = load_fixture("harris_tax_sale_listing.html")
    leads = parse_harris_tax_sale_html(html)
    assert len(leads) >= 5
    assert leads[0].state == "TX"
    assert leads[0].county == "Harris"
    assert leads[0].parcel_id == "1032000000008"
    assert "tax_sale_scheduled" in leads[0].distress_signals


def test_dallas_parser_reads_fixture():
    text = load_fixture("dallas_trw_unpaid_sample.txt")
    leads = parse_dallas_unpaid_summary(text)
    assert len(leads) == 5
    assert leads[0].county == "Dallas"
    assert leads[0].raw_data["delinquent_amount"] > 0


def test_tarrant_parser_reads_fixture():
    html = load_fixture("tarrant_tax_sale_list.html")
    leads = parse_tarrant_sale_html(html)
    assert len(leads) == 4
    assert leads[0].parcel_id == "0123456789"
