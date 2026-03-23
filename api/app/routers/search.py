from fastapi import APIRouter

from app.models.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(body: SearchRequest):
    return SearchResponse(
        title=body.title,
        abstract=body.abstract,
        keywords=body.keywords or [],
        ipc_classifications=body.ipc_classifications or [],
        cpc_classifications=body.cpc_classifications or [],
    )
