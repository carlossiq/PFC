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


def test_cited_figure_without_fig_marker_goes_right_after_the_citing_paragraph():
    # Cenário real: o LLM citou as figuras ([[REF]]) mas não escreveu os
    # [[FIG]] - antes, todas iam empilhadas pro fim da seção, sem texto ao redor.
    text = (
        "Foram 275 publicações. A Figura [[REF:article_yearly_volume]] mostra o histórico.\n\n"
        "O Quadro [[REF:article_top10_heatmap]] lista as áreas.\n\n"
        "Parágrafo final da seção."
    )

    result, warnings = place_figures(text, _catalog())

    paragraphs = result.split("\n\n")
    assert paragraphs[0].endswith("mostra o histórico.")
    assert paragraphs[1].startswith(r"\figura")
    assert paragraphs[2].startswith("O Quadro")
    assert paragraphs[3].startswith(r"\quadroimg")
    assert paragraphs[4] == "Parágrafo final da seção."  # a seção não termina em figura
    assert len(warnings) == 2


def test_two_figures_cited_in_the_same_paragraph_keep_citation_order():
    text = "Ver o Quadro [[REF:article_top10_heatmap]] e a Figura [[REF:article_yearly_volume]].\n\nFim."

    result, _ = place_figures(text, _catalog())

    assert result.index(r"\quadroimg") < result.index(r"\figura") < result.index("Fim.")


def test_uncited_figure_goes_to_the_end():
    text = "A Figura [[REF:article_yearly_volume]] mostra algo."

    result, warnings = place_figures(text, _catalog())

    assert result.startswith(r"A Figura \ref{fig:article_yearly_volume} mostra algo.")
    assert result.index(r"\figura") < result.index(r"\quadroimg")  # heatmap, não citado, no fim
    assert result.rstrip().endswith("{article_top10_heatmap.png}")
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


def test_word_before_ref_follows_the_label_kind():
    text = (
        "Conforme a Figura [[REF:article_top10_heatmap]], e o quadro [[REF:article_yearly_volume]] mostra.\n\n"
        "[[FIG:article_yearly_volume]]\n\n[[FIG:article_top10_heatmap]]"
    )

    result, _ = place_figures(text, _catalog())

    # Nome certo antes do número, com o artigo concordando.
    assert r"Conforme o Quadro \ref{quadro:article_top10_heatmap}" in result
    assert r"e a figura \ref{fig:article_yearly_volume}" in result


def test_contractions_before_the_word_also_agree():
    from app.core.services.report_figures import _fix_figure_word

    assert _fix_figure_word(r"Na Figura \ref{quadro:x} e da figura \ref{quadro:y}.") == (
        r"No Quadro \ref{quadro:x} e do quadro \ref{quadro:y}."
    )
    assert _fix_figure_word(r"pelo Quadro \ref{fig:x}; À Figura \ref{fig:y}") == (
        r"pela Figura \ref{fig:x}; À Figura \ref{fig:y}"
    )
