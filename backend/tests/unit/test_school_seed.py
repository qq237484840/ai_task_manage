"""单测：schools seed 幂等性（DATA-011/ADR-008）—— 独立空库验证（与 app lifespan 预 seed 解耦）。"""

import pytest
from sqlalchemy import func, select

from app.core.database import Base, build_engine, build_session_factory
from app.core.seed import DEFAULT_SEED_SCHOOLS, seed_schools
from app.modules.m001.models.orm import School


@pytest.fixture
def seed_factory(tmp_path):
    engine = build_engine("sqlite:///" + (tmp_path / "seed.db").as_posix())
    Base.metadata.create_all(engine)
    return build_session_factory(engine)


def test_seed_is_idempotent(seed_factory):
    with seed_factory() as session:
        first = seed_schools(session)
        assert first == len(DEFAULT_SEED_SCHOOLS)
        second = seed_schools(session)  # 再次执行不得重复插入
        assert second == 0
        total = session.scalar(select(func.count()).select_from(School))
        assert total == len(DEFAULT_SEED_SCHOOLS)


def test_seed_adds_missing_only(seed_factory):
    custom = [("新增小学", "primary"), ("新增中学", "junior")]
    with seed_factory() as session:
        added = seed_schools(session, schools=custom)
        assert added == 2
        again = seed_schools(session, schools=custom)
        assert again == 0
        names = set(session.scalars(select(School.name)))
        assert {"新增小学", "新增中学"} <= names
