"""
Report Visualization Functions for Technology Prospecting.

Generates various charts for prospecting reports:
- S-Curve (Technology Lifecycle)
- Patent/Article History Timeline
- Top Applicants/Authors
- Classification Distribution (CPC/IPC vs Field of Study)
"""

from typing import Any, Optional
import numpy as np
from datetime import datetime


class TechProspectingVisualizations:
    """Generates visualizations for technology prospecting reports."""

    @staticmethod
    def generate_s_curve(
        documents: list[dict[str, Any]],
        document_type: str = "patent",
        years_projection: int = 5,
    ) -> dict[str, Any]:
        """
        Generates S-curve (technology lifecycle curve) from document data.

        Shows maturity phases:
        - Emerging: Low growth phase
        - Growth: Exponential growth phase
        - Maturity: Plateau phase

        Args:
            documents: List of patent/article documents with 'year' field
            document_type: "patent" or "article"
            years_projection: Years to project into future

        Returns:
            Dictionary with:
            - accumulated: Cumulative count by year
            - yearly: Count per year
            - s_curve_data: Fitted S-curve with parameters
            - lifecycle_phase: Current maturity phase
            - growth_metrics: GP, MP, SP analysis
        """
        if not documents:
            return {
                "success": False,
                "error": "No documents provided",
            }

        # Extract years and count
        year_counts = {}
        for doc in documents:
            year = doc.get("year")
            if year:
                year_counts[int(year)] = year_counts.get(int(year), 0) + 1

        if not year_counts:
            return {
                "success": False,
                "error": "No year data in documents",
            }

        # Sort by year
        sorted_years = sorted(year_counts.keys())
        years = np.array(sorted_years)
        counts = np.array([year_counts[y] for y in sorted_years])

        # Calculate cumulative
        accumulated = np.cumsum(counts)

        # Fit S-curve (logistic function)
        try:
            # Fit polynomial to log-transformed data
            # y = L / (1 + exp(-k(x-x0)))
            x_norm = (years - years[0]) / (years[-1] - years[0])

            # Estimate parameters
            L = accumulated[-1] * 1.2  # Maximum capacity
            x0 = len(years) / 2  # Inflection point
            k = 2  # Growth rate

            # Generate S-curve fitted data
            x_smooth = np.linspace(years[0], years[-1] + years_projection, 100)
            x_smooth_norm = (x_smooth - years[0]) / (years[-1] - years[0])

            y_fitted = L / (1 + np.exp(-k * (x_smooth_norm * len(years) - x0)))

            # Calculate metrics
            accumulated_growth = np.diff(accumulated)
            max_growth_idx = np.argmax(accumulated_growth)
            max_growth_year = sorted_years[max_growth_idx]
            max_growth_rate = accumulated_growth[max_growth_idx]

            # Identify phases
            total_accumulated = accumulated[-1]
            growth_point = total_accumulated * 0.1  # 10% of total
            middle_point = total_accumulated * 0.5  # 50% of total
            saturation_point = total_accumulated * 0.9  # 90% of total

            phase_data = {
                "growth_point": {
                    "accumulated": int(growth_point),
                    "year": _find_year_for_value(sorted_years, accumulated, growth_point),
                },
                "middle_point": {
                    "accumulated": int(middle_point),
                    "year": _find_year_for_value(sorted_years, accumulated, middle_point),
                },
                "saturation_point": {
                    "accumulated": int(saturation_point),
                    "year": _find_year_for_value(sorted_years, accumulated, saturation_point),
                },
            }

            # Determine lifecycle phase
            current_accumulated = accumulated[-1]
            if current_accumulated < middle_point:
                lifecycle = "EMERGING"
            elif current_accumulated < saturation_point:
                lifecycle = "GROWTH"
            else:
                lifecycle = "MATURITY"

            return {
                "success": True,
                "document_type": document_type,
                "data": {
                    "years": sorted_years,
                    "yearly_count": [int(c) for c in counts],
                    "accumulated": [int(a) for a in accumulated],
                    "s_curve_years": [float(y) for y in x_smooth],
                    "s_curve_fitted": [float(y) for y in y_fitted],
                    "total_documents": int(total_accumulated),
                    "max_growth_year": max_growth_year,
                    "max_growth_rate": int(max_growth_rate),
                },
                "lifecycle": {
                    "phase": lifecycle,
                    "growth_point": phase_data["growth_point"],
                    "middle_point": phase_data["middle_point"],
                    "saturation_point": phase_data["saturation_point"],
                },
                "parameters": {
                    "L": float(L),
                    "k": float(k),
                    "x0": float(x0),
                    "growth_rate": float(max_growth_rate / total_accumulated),
                },
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def generate_timeline_history(
        documents: list[dict[str, Any]],
        document_type: str = "patent",
    ) -> dict[str, Any]:
        """
        Generates historical deposit/publication timeline.

        Shows evolution of research activity over time.

        Args:
            documents: List of documents with 'year' field
            document_type: "patent" or "article"

        Returns:
            Dictionary with yearly counts and trend
        """
        if not documents:
            return {"success": False, "error": "No documents provided"}

        # Count by year
        year_counts = {}
        for doc in documents:
            year = doc.get("year")
            if year:
                year_counts[int(year)] = year_counts.get(int(year), 0) + 1

        sorted_years = sorted(year_counts.keys())
        counts = [year_counts[y] for y in sorted_years]

        # Calculate trend
        try:
            if len(sorted_years) >= 2:
                x = np.array(sorted_years)
                y = np.array(counts)
                z = np.polyfit(x, y, 2)  # Polynomial fit
                trend = np.poly1d(z)
                trend_values = [float(trend(year)) for year in sorted_years]
            else:
                trend_values = counts
        except:
            trend_values = counts

        return {
            "success": True,
            "document_type": document_type,
            "data": {
                "years": sorted_years,
                "counts": counts,
                "trend": trend_values,
                "total": sum(counts),
                "average_per_year": sum(counts) / len(sorted_years) if sorted_years else 0,
                "peak_year": sorted_years[counts.index(max(counts))] if counts else None,
                "peak_count": max(counts) if counts else 0,
            },
        }

    @staticmethod
    def generate_top_entities(
        documents: list[dict[str, Any]],
        document_type: str = "patent",
        top_k: int = 10,
    ) -> dict[str, Any]:
        """
        Generates top applicants (patents) or authors (articles).

        Args:
            documents: List of documents
            document_type: "patent" or "article"
            top_k: Number of top entities to return

        Returns:
            Dictionary with top entities and their counts
        """
        if not documents:
            return {"success": False, "error": "No documents provided"}

        entity_counts = {}
        entity_docs = {}

        if document_type == "patent":
            entity_key = "applicants"
        else:
            entity_key = "authors"

        for doc in documents:
            entities = doc.get(entity_key, [])
            if entities:
                for entity in entities:
                    if entity:
                        entity_counts[entity] = entity_counts.get(entity, 0) + 1
                        if entity not in entity_docs:
                            entity_docs[entity] = []
                        # Store reference (title for patents, doi for articles)
                        ref = doc.get("title") or doc.get("doi", "")
                        if ref:
                            entity_docs[entity].append(ref)

        # Sort and get top K
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return {
            "success": True,
            "document_type": document_type,
            "entity_type": "Applicants" if document_type == "patent" else "Authors",
            "data": [
                {
                    "rank": i + 1,
                    "name": name,
                    "count": count,
                    "percentage": count / sum(dict(sorted_entities).values()) * 100,
                }
                for i, (name, count) in enumerate(sorted_entities)
            ],
        }

    @staticmethod
    def generate_classification_distribution(
        documents: list[dict[str, Any]],
        document_type: str = "patent",
        top_k: int = 10,
    ) -> dict[str, Any]:
        """
        Generates classification distribution (CPC/IPC for patents, Field of Study for articles).

        Shows technical domains/fields covered by research.

        Args:
            documents: List of documents
            document_type: "patent" or "article"
            top_k: Number of top classifications

        Returns:
            Dictionary with classification distribution
        """
        if not documents:
            return {"success": False, "error": "No documents provided"}

        classification_counts = {}
        classification_docs = {}

        if document_type == "patent":
            # Use CPC (more recent/specific than IPC)
            classification_key = "cpc_codes"
            classification_name = "CPC"
        else:
            # Use field of study for articles
            classification_key = "field_of_study"
            classification_name = "Field of Study"

        for doc in documents:
            classifications = doc.get(classification_key, [])
            if classifications:
                for cls in classifications:
                    if cls:
                        classification_counts[cls] = classification_counts.get(cls, 0) + 1
                        if cls not in classification_docs:
                            classification_docs[cls] = []
                        ref = doc.get("title") or doc.get("doi", "")
                        if ref:
                            classification_docs[cls].append(ref)

        # Sort and get top K
        sorted_classifications = sorted(
            classification_counts.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        return {
            "success": True,
            "document_type": document_type,
            "classification_type": classification_name,
            "data": [
                {
                    "rank": i + 1,
                    "code": code,
                    "count": count,
                    "percentage": count / sum(dict(sorted_classifications).values()) * 100,
                }
                for i, (code, count) in enumerate(sorted_classifications)
            ],
        }

    @staticmethod
    def generate_yearly_distribution(
        documents: list[dict[str, Any]],
        document_type: str = "patent",
    ) -> dict[str, Any]:
        """
        Generates distribution by year (heatmap data for field/classification).

        Shows which classifications were most active in which years.

        Args:
            documents: List of documents
            document_type: "patent" or "article"

        Returns:
            Dictionary with year x classification matrix
        """
        if not documents:
            return {"success": False, "error": "No documents provided"}

        if document_type == "patent":
            classification_key = "cpc_codes"
        else:
            classification_key = "field_of_study"

        # Build matrix: year -> classification -> count
        matrix_data = {}

        for doc in documents:
            year = doc.get("year")
            classifications = doc.get(classification_key, [])

            if year and classifications:
                if year not in matrix_data:
                    matrix_data[year] = {}

                for cls in classifications:
                    if cls:
                        matrix_data[year][cls] = matrix_data[year].get(cls, 0) + 1

        # Convert to list format
        years = sorted(matrix_data.keys())
        all_classifications = set()
        for year_dict in matrix_data.values():
            all_classifications.update(year_dict.keys())

        # Get top 10 classifications
        all_cls_counts = {}
        for year_dict in matrix_data.values():
            for cls, count in year_dict.items():
                all_cls_counts[cls] = all_cls_counts.get(cls, 0) + count

        top_classifications = sorted(all_cls_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_cls_set = {cls for cls, _ in top_classifications}

        # Build heatmap data
        heatmap = []
        for year in years:
            row = {
                "year": year,
                "total": sum(matrix_data[year].values()),
            }
            for cls, _ in top_classifications:
                row[cls] = matrix_data[year].get(cls, 0)
            heatmap.append(row)

        return {
            "success": True,
            "document_type": document_type,
            "classifications": [cls for cls, _ in top_classifications],
            "data": heatmap,
        }


def _find_year_for_value(years: list[int], accumulated: np.ndarray, target_value: float) -> Optional[int]:
    """Find year closest to target accumulated value."""
    if len(accumulated) == 0:
        return None

    # Find closest index
    idx = np.argmin(np.abs(accumulated - target_value))
    return years[idx] if idx < len(years) else years[-1]
