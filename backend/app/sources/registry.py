from app.adapters.interfaces import LeadSource
from app.sources.tx.dallas_trw import DallasTrwSource
from app.sources.tx.harris_tax_sale import HarrisTaxSaleSource
from app.sources.tx.tarrant_tax_sale import TarrantTaxSaleSource

SOURCE_REGISTRY: dict[str, LeadSource] = {
    "tx.harris.tax_sale": HarrisTaxSaleSource(),
    "tx.dallas.trw": DallasTrwSource(),
    "tx.tarrant.tax_sale": TarrantTaxSaleSource(),
}


def get_source(key: str) -> LeadSource:
    if key not in SOURCE_REGISTRY:
        raise KeyError(f"Unknown source: {key}. Available: {list(SOURCE_REGISTRY)}")
    return SOURCE_REGISTRY[key]


def list_sources() -> list[dict]:
    return [
        {
            "key": key,
            "name": src.name,
            "state": src.state,
            "county": src.county,
            "description": getattr(src, "description", ""),
        }
        for key, src in SOURCE_REGISTRY.items()
    ]
