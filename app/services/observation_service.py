from datetime import date
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.data_revision import DataRevision
from app.models.indicator import Indicator
from app.models.observation import Observation
from app.schemas.observation import (
    ChartSeriesResponse,
    ObservationCreate,
    TimeSeriesPoint,
)


class ObservationService:
    @staticmethod
    def get_by_id(db: Session, observation_id: int) -> Optional[Observation]:
        return db.get(Observation, observation_id)

    @staticmethod
    def get_for_indicator(
        db: Session,
        indicator_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: str = "ACTIVE",
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Observation], int]:
        filters = [Observation.indicator_id == indicator_id]
        if status:
            filters.append(Observation.status == status)
        if start_date:
            filters.append(Observation.observation_date >= start_date)
        if end_date:
            filters.append(Observation.observation_date <= end_date)

        total_stmt = select(func.count(Observation.id)).where(*filters)
        total = db.execute(total_stmt).scalar() or 0

        order_col = (
            Observation.observation_date.asc()
            if sort_order == "asc"
            else Observation.observation_date.desc()
        )
        stmt = (
            select(Observation)
            .where(*filters)
            .order_by(order_col)
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
        return items, total

    @staticmethod
    def get_chart_series(
        db: Session,
        indicator_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[ChartSeriesResponse]:
        indicator = db.get(Indicator, indicator_id)
        if not indicator:
            return None

        filters = [
            Observation.indicator_id == indicator_id,
            Observation.status == "ACTIVE",
        ]
        if start_date:
            filters.append(Observation.observation_date >= start_date)
        if end_date:
            filters.append(Observation.observation_date <= end_date)

        stmt = (
            select(Observation)
            .where(*filters)
            .order_by(Observation.observation_date.asc())
        )
        observations = list(db.execute(stmt).scalars().all())

        data_points = [
            TimeSeriesPoint(
                date=obs.observation_date,
                value=obs.value,
                yoy_change=obs.yoy_change,
                mom_change=obs.mom_change,
                moving_avg_3m=obs.moving_avg_3m,
                moving_avg_12m=obs.moving_avg_12m,
                is_provisional=obs.is_provisional,
                is_revised=obs.is_revised,
            )
            for obs in observations
        ]

        return ChartSeriesResponse(
            indicator_id=indicator.id,
            indicator_code=indicator.code,
            indicator_name=indicator.name,
            units=indicator.units,
            frequency=indicator.frequency,
            data_points=data_points,
            latest_date=indicator.latest_observation_date,
            latest_value=indicator.latest_value,
        )

    @staticmethod
    def upsert_observation(
        db: Session,
        obj_in: ObservationCreate,
        revision_reason: Optional[str] = None,
    ) -> Tuple[Observation, bool, Optional[DataRevision]]:
        """
        Upsert observation preserving revision history (FR-13).
        Returns (observation, is_created, optional_revision).
        """
        stmt = select(Observation).where(
            Observation.indicator_id == obj_in.indicator_id,
            Observation.observation_date == obj_in.observation_date,
            Observation.status == "ACTIVE",
        )
        existing = db.execute(stmt).scalar_one_or_none()

        if existing is None:
            new_obs = Observation(
                indicator_id=obj_in.indicator_id,
                raw_file_id=obj_in.raw_file_id,
                observation_date=obj_in.observation_date,
                value=obj_in.value,
                units=obj_in.units,
                is_provisional=obj_in.is_provisional,
                is_revised=False,
                revision_number=0,
                status="ACTIVE",
                yoy_change=obj_in.yoy_change,
                mom_change=obj_in.mom_change,
                moving_avg_3m=obj_in.moving_avg_3m,
                moving_avg_12m=obj_in.moving_avg_12m,
                metadata_json=obj_in.metadata_json,
            )
            db.add(new_obs)
            db.flush()

            # Update indicator latest date/value if this observation is newer
            ObservationService._update_indicator_latest(db, obj_in.indicator_id, new_obs)
            db.commit()
            db.refresh(new_obs)
            return new_obs, True, None

        # If value has changed, record a revision (FR-13)
        revision = None
        if abs(existing.value - obj_in.value) > 1e-6:
            diff = obj_in.value - existing.value
            pct_change = (diff / existing.value * 100.0) if existing.value != 0 else None

            revision = DataRevision(
                indicator_id=existing.indicator_id,
                observation_id=existing.id,
                raw_file_id=obj_in.raw_file_id,
                observation_date=existing.observation_date,
                previous_value=existing.value,
                new_value=obj_in.value,
                difference=diff,
                percentage_change=pct_change,
                revision_reason=revision_reason or "Updated value from source file",
            )
            db.add(revision)

            existing.value = obj_in.value
            existing.raw_file_id = obj_in.raw_file_id
            existing.is_revised = True
            existing.is_provisional = obj_in.is_provisional
            existing.revision_number += 1
            if obj_in.units:
                existing.units = obj_in.units
            if obj_in.metadata_json:
                existing.metadata_json = obj_in.metadata_json

            ObservationService._update_indicator_latest(db, existing.indicator_id, existing)
            db.commit()
            db.refresh(existing)
            return existing, False, revision

        # Values are identical; no update needed
        return existing, False, None

    @staticmethod
    def _update_indicator_latest(db: Session, indicator_id: int, obs: Observation) -> None:
        indicator = db.get(Indicator, indicator_id)
        if indicator:
            if (
                indicator.latest_observation_date is None
                or obs.observation_date >= indicator.latest_observation_date
            ):
                indicator.latest_observation_date = obs.observation_date
                indicator.latest_value = obs.value
