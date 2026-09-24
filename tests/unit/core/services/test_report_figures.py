from app.core.services.report_figures import CatalogEntry, place_figures


def _catalog():
    return [
        CatalogEntry(id="article_yearly_volume", kind="figura", caption="Histórico.", filename="article_yearly_volume.png"),
        CatalogEntry(id="article_top10_heatmap", kind="quadro", caption="Áreas.", filename="article_top10_heatmap.png"),
    ]


def test_markers_are_replaced_in_place():
    text = (
        "Como mostra a Figura [[REF:article\\_yearly\\_volume]], o volume cresceu.\n\n"
        "[[FIG:article\\_yearly\\_volume]]\n\n"
        "O Quadro [[REF:article_top10_heatmap]] lista as áreas.\n\n"
        "[[FIG:article_top10_heatmap]]"
    )

    result, warnings = place_figures(text, _catalog())

    assert warnings == []
    assert r"Como mostra a Figura \ref{fig:article_yearly_volume}, o volume cresceu." in result
    assert r"\figura[O autor.]{Histórico.\label{fig:article_yearly_volume}}{article_yearly_volume.png}" in result
    assert r"\quadroimg[O autor.]{Áreas.\label{quadro:article_top10_heatmap}}{article_top10_heatmap.png}" in result
    # figura logo depois do parágrafo que a discute, antes do próximo
    assert result.index(r"\figura") < result.index("O Quadro")


def test_unplaced_and_ref_only_figures_go_to_the_end():
    text = "A Figura [[REF:article_yearly_volume]] mostra algo."

    result, warnings = place_figures(text, _catalog())

    assert result.startswith(r"A Figura \ref{fig:article_yearly_volume} mostra algo.")
    assert result.index(r"\figura") < result.index(r"\quadroimg")  # ordem do catálogo
    assert len(warnings) == 2


def test_unknown_id_is_removed_with_warning():
    result, warnings = place_figures("Texto [[FIG:inexistente]].\n\n[[REF:outro]]", [])

    assert result == "Texto."
    assert len(warnings) == 2


def test_figure_placed_twice_keeps_first_only():
    text = "P1.\n\n[[FIG:article_yearly_volume]]\n\nP2.\n\n[[FIG:article_yearly_volume]]"

    result, warnings = place_figures(text, _catalog()[:1])

    assert result.count(r"\figura") == 1
    assert result.index(r"\figura") < result.index("P2.")
    assert any("mais de uma vez" in w for w in warnings)


def test_legacy_text_without_markers_gets_all_figures_at_the_end():
    result, _ = place_figures("Texto antigo.", _catalog())

    assert result.startswith("Texto antigo.\n\n\\figura")
