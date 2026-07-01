from app.adapters.interfaces import LeadSource
from app.sources.fl.broward_tax_deed import BrowardTaxDeedSource
from app.sources.fl.hillsborough_tax_deed import HillsboroughTaxDeedSource
from app.sources.fl.miami_dade_delinquent import MiamiDadeDelinquentSource
from app.sources.tx.dallas_trw import DallasTrwSource
from app.sources.tx.harris_tax_sale import HarrisTaxSaleSource
from app.sources.tx.tarrant_tax_sale import TarrantTaxSaleSource

SOURCE_REGISTRY: dict[str, LeadSource] = {
    "tx.harris.tax_sale": HarrisTaxSaleSource(),
    "tx.dallas.trw": DallasTrwSource(),
    "tx.tarrant.tax_sale": TarrantTaxSaleSource(),
    "fl.miami_dade.delinquent": MiamiDadeDelinquentSource(),
    "fl.broward.tax_deed": BrowardTaxDeedSource(),
    "fl.hillsborough.tax_deed": HillsboroughTaxDeedSource(),
}

DEFAULT_TX_SOURCES = ["tx.harris.tax_sale", "tx.dallas.trw", "tx.tarrant.tax_sale"]
DEFAULT_FL_SOURCES = [
    "fl.miami_dade.delinquent",
    "fl.broward.tax_deed",
    "fl.hillsborough.tax_deed",
]
DEFAULT_ALL_SOURCES = DEFAULT_TX_SOURCES + DEFAULT_FL_SOURCES


def get_source(key: str) -> LeadSource:
    if key not in SOURCE_REGISTRY:
        raise KeyError(f"Unknown source: {key}. Available: {list(SOURCE_REGISTRY)}")
    return SOURCE_REGISTRY[key]


def list_sources(state: str | None = None) -> list[dict]:
    items = [
        {
            "key": key,
            "name": src.name,
            "state": src.state,
            "county": src.county,
            "description": getattr(src, "description", ""),
        }
        for key, src in SOURCE_REGISTRY.items()
    ]
    if state:
        state = state.upper()
        items = [item for item in items if item["state"] == state]
    return items
