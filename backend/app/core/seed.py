"""基础数据初始化：schools 学校字典 seed（ADR-008 / DATA-011）。

- 幂等：按 (name, stage) 查重，缺失才插入；重复执行结果一致（测试断言依据）。
- V1 起步以 stage=primary 常见小学为主，附带 junior/senior 少量样例供过滤验证
  （学校补录/改名 V1 无运行期手段：seed 变更走部署升级，需求变更走 CR，契约 REQ-009）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import School

# (name, stage)
DEFAULT_SEED_SCHOOLS: list[tuple[str, str]] = [
    ("实验小学", "primary"),
    ("第一小学", "primary"),
    ("第二小学", "primary"),
    ("阳光小学", "primary"),
    ("育才小学", "primary"),
    ("师范附属小学", "primary"),
    ("外国语小学", "primary"),
    ("滨江小学", "primary"),
    ("朝阳小学", "primary"),
    ("北山小学", "primary"),
    ("第一初级中学", "junior"),
    ("实验中学", "junior"),
    ("第二初级中学", "junior"),
    ("第一高级中学", "senior"),
    ("外国语高级中学", "senior"),
]


def seed_schools(session: Session, schools: list[tuple[str, str]] | None = None) -> int:
    """幂等写入学校字典，返回本次新增条数。"""
    sources = schools if schools is not None else DEFAULT_SEED_SCHOOLS
    added = 0
    for name, stage in sources:
        exists = session.scalar(
            select(School.school_id).where(School.name == name, School.stage == stage)
        )
        if exists is None:
            session.add(School(name=name, stage=stage))
            added += 1
    session.flush()
    return added
