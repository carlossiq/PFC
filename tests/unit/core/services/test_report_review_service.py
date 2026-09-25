import httpx
import pytest

from app.core.services.report_review_service import ReportReviewService, _parse_corrections

DOC = (
    "\\documentclass{article}\n\\begin{document}\n"
    "\\section{CONCLUSÃO}\n"
    "Os resultados mostra que as tecnologias crescem, e os modulos (SILVA et al., 2020) cresceram 17,3\\% em P\\&D.\n"
    "\\end{document}\n"
)


def test_parse_corrections_tolerates_latex_backslashes_inside_json():
    raw = (
        '```json\n{"correcoes": [{"original": "17,3\\% de", "corrigido": "17,3\\% dos", "motivo": "x"}]}\n```'
    )
    assert _parse_corrections(raw) == [{"original": "17,3\\% de", "corrigido": "17,3\\% dos", "motivo": "x"}]


def test_parse_corrections_without_json_returns_empty():
    assert _parse_corrections("Nenhum erro encontrado.") == []


class _FakeGenerator:
    def __init__(self, response: str) -> None:
        self.response = response

    async def generate(self, prompt: str, system=None, temperature=None) -> str:
        return self.response


class _FakeResolver:
    def __init__(self, response: str) -> None:
        self.generator = _FakeGenerator(response)

    async def resolve_text_generation(self, call_site: str):
        assert call_site == "report_review"
        return self.generator


def _languagetool_transport(matches_for: dict[str, str]):
    """LanguageTool fake: marca cada palavra de `matches_for` (palavra -> substituição),
    tanto no texto anotado (revisão) quanto no texto puro (conferência das correções da IA)."""

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        from urllib.parse import parse_qs

        form = parse_qs(request.content.decode("utf-8"))
        if "data" in form:
            segments = json.loads(form["data"][0])["annotation"]
            original = "".join(s.get("text", s.get("markup", "")) for s in segments)
        else:
            original = form["text"][0]
        matches = [
            {
                "offset": original.index(word),
                "length": len(word),
                "message": "Possível erro de ortografia.",
                "replacements": [{"value": fix}],
                "rule": {"id": "MORFOLOGIK_RULE_PT_BR", "category": {"id": "TYPOS"}},
            }
            for word, fix in matches_for.items()
            if word in original
        ]
        return httpx.Response(200, json={"matches": matches})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_review_combines_languagetool_and_ai_with_offsets_into_the_tex():
    ai_json = '{"correcoes": [{"original": "resultados mostra", "corrigido": "resultados mostram", "motivo": "concordância verbal"}]}'
    svc = ReportReviewService("http://lt", "pt-BR", _FakeResolver(ai_json))
    svc._client = httpx.AsyncClient(transport=_languagetool_transport({"modulos": "módulos"}))

    result = await svc.review(DOC, DOC, set(), include_ai=True)

    found = {(s.source, s.original, s.replacements[0]) for s in result.suggestions}
    assert found == {("languagetool", "modulos", "módulos"), ("ia", "resultados mostra", "resultados mostram")}
    for suggestion in result.suggestions:
        assert DOC[suggestion.offset: suggestion.offset + suggestion.length] == suggestion.original
    assert result.warnings == []


@pytest.mark.asyncio
async def test_review_reports_languagetool_down_but_keeps_latex_issues():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    svc = ReportReviewService("http://lt", "pt-BR", _FakeResolver("{}"))
    svc._client = httpx.AsyncClient(transport=httpx.MockTransport(down))
    broken = DOC.replace("P\\&D", "P&D")

    result = await svc.review(broken, broken, set())

    assert any("LanguageTool" in w for w in result.warnings)
    assert any('"&" sem escape' in issue.message for issue in result.latex_issues)
    assert result.suggestions == []


@pytest.mark.asyncio
async def test_missing_baseline_warns_that_ai_only_checked_ai_sections():
    svc = ReportReviewService("http://lt", "pt-BR", _FakeResolver("{}"))
    svc._client = httpx.AsyncClient(transport=_languagetool_transport({}))

    assert not any("Remontar .tex" in w for w in (await svc.review(DOC, None, set())).warnings)
    result = await svc.review(DOC, None, set(), include_ai=True)

    assert any("Remontar .tex" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_ai_fix_that_introduces_unknown_word_is_dropped():
    # "resultados mostra" -> "resultados mostram" é flexão válida, mas o
    # dicionário (fake) não conhece "mostram" -> descartada.
    ai_json = '{"correcoes": [{"original": "resultados mostra", "corrigido": "resultados mostram", "motivo": "x"}]}'
    svc = ReportReviewService("http://lt", "pt-BR", _FakeResolver(ai_json))
    svc._client = httpx.AsyncClient(transport=_languagetool_transport({"mostram": "?"}))

    result = await svc.review(DOC, DOC, set(), include_ai=True)

    assert not any(s.source == "ia" for s in result.suggestions)


def test_parse_corrections_keeps_latex_commands_intact():
    raw = '{"correcoes": [{"original": "no Quadro \\ref{quadro:x} mostra", "corrigido": "no Quadro \\ref{quadro:x} mostram"}]}'
    assert _parse_corrections(raw)[0]["original"] == "no Quadro \\ref{quadro:x} mostra"
