from pydantic import BaseModel


class SearchRequest(BaseModel):
    title: str
    abstract: str
    keywords: list[str] | None = None
    ipc_classifications: list[str] | None = None
    cpc_classifications: list[str] | None = None


class SearchResponse(BaseModel):
    title: str
    abstract: str
    keywords: list[str]
    ipc_classifications: list[str]
    cpc_classifications: list[str]
