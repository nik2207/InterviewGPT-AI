import json
from functools import lru_cache
from pathlib import Path

from schemas.company_prep_schema import (
    CompanyCatalogueEntry,
    CompanyCatalogueListResponse,
    CompanyPrepMaterialItem,
)

_CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "data" / "company_catalogue.json"


class CompanyCatalogueError(Exception):
    pass


@lru_cache(maxsize=1)
def _load_raw_catalogue() -> dict:
    if not _CATALOGUE_PATH.is_file():
        raise CompanyCatalogueError("Company catalogue file is missing.")
    try:
        return json.loads(_CATALOGUE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompanyCatalogueError("Invalid company catalogue.") from exc


def reload_catalogue_cache() -> None:
    _load_raw_catalogue.cache_clear()


def list_companies(search: str | None = None) -> CompanyCatalogueListResponse:
    raw = _load_raw_catalogue()
    disclaimer = str(raw.get("disclaimer", ""))
    entries: list[CompanyCatalogueEntry] = []
    query = (search or "").strip().lower()

    for item in raw.get("companies", []):
        entry = CompanyCatalogueEntry.model_validate(item)
        if query:
            haystack = " ".join(
                [entry.name, entry.id, entry.industry, *entry.aliases, *entry.public_prep_topics]
            ).lower()
            if query not in haystack:
                continue
        entries.append(entry)

    return CompanyCatalogueListResponse(disclaimer=disclaimer, companies=entries)


def get_company(company_id: str) -> CompanyCatalogueEntry | None:
    raw = _load_raw_catalogue()
    for item in raw.get("companies", []):
        if item.get("id") == company_id:
            return CompanyCatalogueEntry.model_validate(item)
    return None


def catalogue_material_for_company(company_id: str) -> list[CompanyPrepMaterialItem]:
    company = get_company(company_id)
    if company is None:
        return []
    return list(company.prep_material)
