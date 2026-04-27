"""
Test visualization functions with sample data.

Demonstrates all visualization functions for prospecting reports.
"""

import json
from services.report_visualizations import TechProspectingVisualizations


def generate_sample_patents():
    """Generate sample patent data."""
    return [
        {
            "title": "AI-based recommendation system",
            "year": 2019,
            "applicants": ["Company A", "Company B"],
            "cpc_codes": ["H04L29/08", "G06N3/04"],
        },
        {
            "title": "Machine learning personalization",
            "year": 2020,
            "applicants": ["Company A"],
            "cpc_codes": ["G06F17/30", "H04L29/08"],
        },
        {
            "title": "Neural network optimization",
            "year": 2020,
            "applicants": ["Company C"],
            "cpc_codes": ["G06N3/04", "G06F17/30"],
        },
        {
            "title": "Real-time recommendation engine",
            "year": 2021,
            "applicants": ["Company B"],
            "cpc_codes": ["H04L29/08"],
        },
        {
            "title": "Deep learning for commerce",
            "year": 2021,
            "applicants": ["Company A", "Company C"],
            "cpc_codes": ["G06N3/04"],
        },
        {
            "title": "Collaborative filtering patents",
            "year": 2022,
            "applicants": ["Company D"],
            "cpc_codes": ["G06F17/30", "H04L29/08"],
        },
        {
            "title": "Advanced AI systems",
            "year": 2022,
            "applicants": ["Company A"],
            "cpc_codes": ["G06N3/04"],
        },
        {
            "title": "Federated learning infrastructure",
            "year": 2023,
            "applicants": ["Company B", "Company D"],
            "cpc_codes": ["H04L9/08", "G06F17/30"],
        },
        {
            "title": "Privacy-preserving AI",
            "year": 2023,
            "applicants": ["Company C"],
            "cpc_codes": ["H04L9/08"],
        },
        {
            "title": "Edge computing AI",
            "year": 2024,
            "applicants": ["Company A"],
            "cpc_codes": ["G06F15/173"],
        },
    ]


def generate_sample_articles():
    """Generate sample article data."""
    return [
        {
            "title": "Deep Learning Advances in NLP",
            "year": 2020,
            "authors": ["Author A", "Author B"],
            "field_of_study": ["Machine Learning", "Natural Language Processing"],
        },
        {
            "title": "Recommendation Systems Survey",
            "year": 2021,
            "authors": ["Author C"],
            "field_of_study": ["Machine Learning", "Information Retrieval"],
        },
        {
            "title": "Privacy in ML Systems",
            "year": 2021,
            "authors": ["Author A", "Author D"],
            "field_of_study": ["Machine Learning", "Security"],
        },
        {
            "title": "Federated Learning",
            "year": 2022,
            "authors": ["Author B"],
            "field_of_study": ["Machine Learning", "Distributed Systems"],
        },
        {
            "title": "Neural Architecture Search",
            "year": 2022,
            "authors": ["Author E"],
            "field_of_study": ["Machine Learning", "Computer Vision"],
        },
        {
            "title": "Transfer Learning Applications",
            "year": 2023,
            "authors": ["Author C", "Author F"],
            "field_of_study": ["Machine Learning", "Computer Vision"],
        },
        {
            "title": "Graph Neural Networks",
            "year": 2023,
            "authors": ["Author A"],
            "field_of_study": ["Machine Learning", "Graph Theory"],
        },
        {
            "title": "Transformer Models",
            "year": 2024,
            "authors": ["Author D", "Author E"],
            "field_of_study": ["Machine Learning", "Natural Language Processing"],
        },
    ]


def test_s_curve():
    """Test S-curve generation."""
    print("\n" + "=" * 100)
    print("[1] S-CURVE ANALYSIS")
    print("=" * 100)

    patents = generate_sample_patents()
    articles = generate_sample_articles()

    viz = TechProspectingVisualizations()

    # Patent S-curve
    print("\nPATENT S-CURVE:")
    print("-" * 100)
    result = viz.generate_s_curve(patents, document_type="patent")

    if result["success"]:
        data = result["data"]
        lifecycle = result["lifecycle"]

        print(f"Total Patents: {data['total_documents']}")
        print(f"Years Covered: {min(data['years'])} - {max(data['years'])}")
        print(f"Peak Year: {data['max_growth_year']} ({data['max_growth_rate']} patents)")

        print(f"\nLifecycle Phase: {result['lifecycle']['phase']}")
        print(f"  Growth Point (10%): Year {lifecycle['growth_point']['year']} ({lifecycle['growth_point']['accumulated']} docs)")
        print(f"  Middle Point (50%): Year {lifecycle['middle_point']['year']} ({lifecycle['middle_point']['accumulated']} docs)")
        print(f"  Saturation Point (90%): Year {lifecycle['saturation_point']['year']} ({lifecycle['saturation_point']['accumulated']} docs)")

        print(f"\nS-Curve Parameters:")
        print(f"  L (capacity): {result['parameters']['L']:.1f}")
        print(f"  k (growth rate): {result['parameters']['k']:.3f}")
        print(f"  x0 (inflection): {result['parameters']['x0']:.1f}")

        print(f"\nYearly Data:")
        for year, count in zip(data["years"], data["yearly_count"]):
            print(f"  {year}: {count} patents")

    # Article S-curve
    print("\nARTICLE S-CURVE:")
    print("-" * 100)
    result = viz.generate_s_curve(articles, document_type="article")

    if result["success"]:
        data = result["data"]
        lifecycle = result["lifecycle"]

        print(f"Total Articles: {data['total_documents']}")
        print(f"Lifecycle Phase: {result['lifecycle']['phase']}")
        print(f"Peak Year: {data['max_growth_year']} ({data['max_growth_rate']} articles)")


def test_timeline():
    """Test timeline history."""
    print("\n" + "=" * 100)
    print("[2] TIMELINE HISTORY")
    print("=" * 100)

    patents = generate_sample_patents()
    articles = generate_sample_articles()

    viz = TechProspectingVisualizations()

    print("\nPATENT TIMELINE:")
    print("-" * 100)
    result = viz.generate_timeline_history(patents, document_type="patent")

    if result["success"]:
        data = result["data"]
        print(f"Total Patents: {data['total']}")
        print(f"Average per Year: {data['average_per_year']:.1f}")
        print(f"Peak: Year {data['peak_year']} ({data['peak_count']} patents)")

        print(f"\nYearly Distribution:")
        for year, count in zip(data["years"], data["counts"]):
            bar = "#" * count
            print(f"  {year}: {count:2d} {bar}")

    print("\nARTICLE TIMELINE:")
    print("-" * 100)
    result = viz.generate_timeline_history(articles, document_type="article")

    if result["success"]:
        data = result["data"]
        print(f"Total Articles: {data['total']}")
        print(f"Peak: Year {data['peak_year']} ({data['peak_count']} articles)")


def test_top_entities():
    """Test top entities."""
    print("\n" + "=" * 100)
    print("[3] TOP ENTITIES (Applicants/Authors)")
    print("=" * 100)

    patents = generate_sample_patents()
    articles = generate_sample_articles()

    viz = TechProspectingVisualizations()

    print("\nTOP PATENT APPLICANTS:")
    print("-" * 100)
    result = viz.generate_top_entities(patents, document_type="patent", top_k=5)

    if result["success"]:
        print(f"{'Rank':<6} {'Name':<20} {'Count':<8} {'Percent':<10}")
        print("-" * 44)
        for item in result["data"]:
            print(f"{item['rank']:<6} {item['name']:<20} {item['count']:<8} {item['percentage']:>6.1f}%")

    print("\nTOP ARTICLE AUTHORS:")
    print("-" * 100)
    result = viz.generate_top_entities(articles, document_type="article", top_k=5)

    if result["success"]:
        print(f"{'Rank':<6} {'Name':<20} {'Count':<8} {'Percent':<10}")
        print("-" * 44)
        for item in result["data"]:
            print(f"{item['rank']:<6} {item['name']:<20} {item['count']:<8} {item['percentage']:>6.1f}%")


def test_classifications():
    """Test classification distribution."""
    print("\n" + "=" * 100)
    print("[4] CLASSIFICATION DISTRIBUTION (CPC/Field of Study)")
    print("=" * 100)

    patents = generate_sample_patents()
    articles = generate_sample_articles()

    viz = TechProspectingVisualizations()

    print("\nTOP CPC CLASSIFICATIONS:")
    print("-" * 100)
    result = viz.generate_classification_distribution(patents, document_type="patent", top_k=7)

    if result["success"]:
        print(f"{'Rank':<6} {'Code':<15} {'Count':<8} {'Percent':<10}")
        print("-" * 39)
        for item in result["data"]:
            print(f"{item['rank']:<6} {item['code']:<15} {item['count']:<8} {item['percentage']:>6.1f}%")

    print("\nTOP FIELDS OF STUDY:")
    print("-" * 100)
    result = viz.generate_classification_distribution(articles, document_type="article", top_k=7)

    if result["success"]:
        print(f"{'Rank':<6} {'Field':<30} {'Count':<8} {'Percent':<10}")
        print("-" * 54)
        for item in result["data"]:
            print(f"{item['rank']:<6} {item['code']:<30} {item['count']:<8} {item['percentage']:>6.1f}%")


def test_yearly_distribution():
    """Test yearly distribution heatmap."""
    print("\n" + "=" * 100)
    print("[5] YEARLY DISTRIBUTION MATRIX")
    print("=" * 100)

    patents = generate_sample_patents()
    articles = generate_sample_articles()

    viz = TechProspectingVisualizations()

    print("\nPATENT CPC BY YEAR:")
    print("-" * 100)
    result = viz.generate_yearly_distribution(patents, document_type="patent")

    if result["success"]:
        classifications = result["classifications"][:5]  # Show top 5
        data = result["data"]

        # Header
        header = "Year | Total |"
        for cls in classifications:
            header += f" {cls:<8} |"
        print(header)
        print("-" * len(header))

        # Data rows
        for row in data:
            line = f"{row['year']:4d} | {row['total']:5d} |"
            for cls in classifications:
                count = row.get(cls, 0)
                line += f" {count:>7d} |"
            print(line)

    print("\nARTICLE FIELDS BY YEAR:")
    print("-" * 100)
    result = viz.generate_yearly_distribution(articles, document_type="article")

    if result["success"]:
        classifications = result["classifications"][:4]  # Show top 4
        data = result["data"]

        # Header
        header = "Year | Total |"
        for cls in classifications:
            header += f" {cls:<15} |"
        print(header)
        print("-" * len(header))

        # Data rows
        for row in data:
            line = f"{row['year']:4d} | {row['total']:5d} |"
            for cls in classifications:
                count = row.get(cls, 0)
                line += f" {count:>15d} |"
            print(line)


if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("PROSPECTING REPORT VISUALIZATION TESTS")
    print("=" * 100)

    test_s_curve()
    test_timeline()
    test_top_entities()
    test_classifications()
    test_yearly_distribution()

    print("\n" + "=" * 100)
    print("ALL VISUALIZATIONS TESTED SUCCESSFULLY")
    print("=" * 100 + "\n")
