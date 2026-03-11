from sqlalchemy import and_, exists, extract, func, select

from backend.storage_access_layer.db.schema import (
    LocalMetrics,
    LocalSwipeEvent,
    ManifestMetrics,
    ManifestSwipeEvent,
)

from ..db.db import DB


class SalMetrics:
    def __init__(self, db: DB, common):
        self.db = db
        self.common = common

    def get_available_metrics(self) -> list[str]:
        columns = ManifestMetrics.__table__.columns.keys()
        # just getting the metric names from the manfestmetrics table, not necessary to get event_id
        return [col for col in columns if col != "event_id"]

    def get_swipe_event_summary_plot_data(
        self, x: str, y: str, filters: dict | None = None
    ):
        # ------------------------------------------------------------------
        # Validate requested metrics
        #
        # The frontend must provide two metric names (x and y).
        # We verify that both exist in the ManifestMetrics table
        # to prevent invalid or arbitrary column access.
        # ------------------------------------------------------------------
        available = self.get_available_metrics()

        if x not in available:
            raise ValueError(f"Invalid metric requested for x-axis: {x}")

        if y not in available:
            raise ValueError(f"Invalid metric requested for y-axis: {y}")

        # ------------------------------------------------------------------
        # Build dynamic SELECT query
        #
        # Only select event_id and the requested metric columns.
        # This ensures the response payload contains exactly the
        # metrics needed for scatter plotting.
        # ------------------------------------------------------------------

        with self.db._get_session() as session:
            query = (
                select(
                    LocalMetrics.event_id,
                    getattr(LocalMetrics, x).label(x),
                    getattr(LocalMetrics, y).label(y),
                )
                .select_from(LocalMetrics)
                .join(
                    ManifestSwipeEvent,
                    ManifestSwipeEvent.event_id == LocalMetrics.event_id,
                )
            )

            query = self._apply_local_availability_filter(query)
            query = self._apply_summary_filters(query, filters)

            results = session.execute(query).all()
        # ------------------------------------------------------------------
        # Format results
        #
        # Convert each SQLAlchemy row into a dictionary keyed by event_id.
        # The inner dictionary contains only the requested metrics.
        # ------------------------------------------------------------------
        output = {}

        for row in results:
            if hasattr(row, "_mapping"):
                row_dict = dict(row._mapping)
            else:
                row_dict = dict(row)

            event_id = row_dict.pop("event_id")
            output[event_id] = row_dict

        return output

    def get_date_bounds(self, filters: dict | None = None):
        with self.db._get_session() as session:
            query = (
                select(
                    func.min(ManifestSwipeEvent.date),
                    func.max(ManifestSwipeEvent.date),
                )
                .select_from(LocalMetrics)
                .join(
                    ManifestSwipeEvent,
                    ManifestSwipeEvent.event_id == LocalMetrics.event_id,
                )
            )

            query = self._apply_local_availability_filter(query)
            query = self._apply_summary_filters(query, filters)

            row = session.execute(query).first()

        if not row or row[0] is None or row[1] is None:
            return {"min_date": None, "max_date": None}

        return {
            "min_date": row[0].isoformat(),
            "max_date": row[1].isoformat(),
        }

    def get_distinct_date_values(self, part: str, filters: dict | None = None):
        if part not in {"year", "month", "day"}:
            raise ValueError("Invalid date part")

        with self.db._get_session() as session:
            query = (
                select(extract(part, ManifestSwipeEvent.date).label(part))
                .select_from(LocalMetrics)
                .join(
                    ManifestSwipeEvent,
                    ManifestSwipeEvent.event_id == LocalMetrics.event_id,
                )
                .distinct()
                .order_by(part)
            )

            query = self._apply_local_availability_filter(query)
            query = self._apply_summary_filters(query, filters)

            rows = session.execute(query).all()

        return sorted({int(r[0]) for r in rows if r[0] is not None})

    def _apply_local_availability_filter(self, query):
        return query.where(
            exists().where(
                and_(
                    LocalSwipeEvent.event_id == ManifestSwipeEvent.event_id,
                    LocalSwipeEvent.present.is_(True),
                )
            )
        )

    # filter specifically for participant query
    def _apply_participant_filter(self, query, filters: dict | None):
        if not filters:
            return query

        if "participants" in filters:
            participants = filters["participants"]

            if participants:
                query = query.where(ManifestSwipeEvent.participant.in_(participants))

        return query

    # filter specifically for date query
    def _apply_date_filter(self, query, filters: dict | None):
        if not filters:
            return query

        if "year" in filters:
            year = filters["year"]
            if year:
                query = query.where(
                    extract("year", ManifestSwipeEvent.date) == int(year)
                )

        if "month" in filters:
            month = filters["month"]
            if month:
                query = query.where(
                    extract("month", ManifestSwipeEvent.date) == int(month)
                )

        if "day" in filters:
            day = filters["day"]
            if day:
                query = query.where(extract("day", ManifestSwipeEvent.date) == int(day))

        return query

    # full filter applier function. when adding new filters, update this helper.

    def _apply_summary_filters(self, query, filters: dict | None):
        if not filters:
            return query

        query = self._apply_participant_filter(query, filters)
        query = self._apply_date_filter(query, filters)

        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        if date_from:
            query = query.where(ManifestSwipeEvent.date >= date_from)

        if date_to:
            query = query.where(ManifestSwipeEvent.date <= date_to)

        return query
