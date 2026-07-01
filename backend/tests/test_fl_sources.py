"""Phase 2 parser tests — no network or database required."""

from app.sources.fl.broward_tax_deed import parse_broward_tax_deed_html
from app.sources.fl.hillsborough_tax_deed import parse_hillsborough_tax_deed_html
from app.sources.fl.miami_dade_delinquent import parse_miami_dade_delinquent_text
from app.sources.http import load_fixture


def test_miami_dade_parser_reads_fixture():
    text = load_fixture("miami_dade_delinquent_sample.txt")
    leads = parse_miami_dade_delinquent_text(text)
    assert len(leads) == 8
    assert leads[0].state == "FL"
    assert leads[0].county == "Miami-Dade"
    assert leads[0].parcel_id == "01010401020"
    assert leads[0].raw_data["delinquent_amount"] > 0
    assert "tax_delinquent" in leads[0].distress_signals


def test_broward_parser_reads_fixture():
    html = load_fixture("broward_tax_deed_list.html")
    leads = parse_broward_tax_deed_html(html)
    assert len(leads) == 4
    assert leads[0].county == "Broward"
    assert leads[0].parcel_id == "484213-10-1234"
    assert "tax_deed_scheduled" in leads[0].distress_signals


def test_hillsborough_parser_reads_fixture():
    html = load_fixture("hillsborough_tax_deed_list.html")
    leads = parse_hillsborough_tax_deed_html(html)
    assert len(leads) == 4
    assert leads[0].county == "Hillsborough"
    assert "TAMPA" in leads[0].property_address
    assert leads[0].zip_code == "33602"
