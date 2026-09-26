from datetime import datetime

from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import DATABASE_URL


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    intensity: Mapped[str] = mapped_column(String(40), nullable=False)
    schedule: Mapped[int] = mapped_column(Integer, nullable=False, default=7)


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    original_plan: Mapped[str] = mapped_column(Text, nullable=False)
    updated_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


Base.metadata.create_all(bind=engine)


def _migrate_workout_plan_columns() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("workout_plans")}
    if "updated_plan" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE workout_plans ADD COLUMN updated_plan TEXT")
            )


_migrate_workout_plan_columns()


def save_user(
    user_id: int,
    name: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
) -> None:
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                name=name,
                age=age,
                weight=weight,
                goal=goal,
                intensity=intensity,
                schedule=7,
            )
            db.add(user)
            return

        user.name = name
        user.age = age
        user.weight = weight
        user.goal = goal
        user.intensity = intensity


def save_plan(user_id: int, plan: str) -> None:
    with SessionLocal.begin() as db:
        if db.get(User, user_id) is None:
            raise ValueError(f"User {user_id} does not exist")

        db.add(WorkoutPlan(user_id=user_id, original_plan=plan))


def save_user_with_plan(
    user_id: int,
    name: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    schedule: int,
    plan: str,
) -> None:
    with SessionLocal.begin() as db:
        user = db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                name=name,
                age=age,
                weight=weight,
                goal=goal,
                intensity=intensity,
                schedule=schedule,
            )
            db.add(user)
        else:
            user.name = name
            user.age = age
            user.weight = weight
            user.goal = goal
            user.intensity = intensity
            user.schedule = schedule

        db.add(WorkoutPlan(user_id=user_id, original_plan=plan))


def update_plan(user_id: int, updated_text: str) -> bool:
    with SessionLocal.begin() as db:
        workout = db.scalar(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.id.desc())
            .limit(1)
        )
        if workout is None:
            return False

        workout.updated_plan = updated_text
        return True


def get_original_plan(user_id: int) -> str | None:
    with SessionLocal() as db:
        workout = db.scalar(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.id.desc())
            .limit(1)
        )
        return workout.original_plan if workout else None


def get_user(user_id: int) -> User | None:
    with SessionLocal() as db:
        return db.get(User, user_id)


def get_all_users_with_plans() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        users = db.scalars(select(User).order_by(User.id)).all()
        plans = db.scalars(select(WorkoutPlan).order_by(WorkoutPlan.id.desc())).all()

        plans_by_user: dict[int, list[dict[str, Any]]] = {}
        for plan in plans:
            plans_by_user.setdefault(plan.user_id, []).append(
                {
                    "original_plan": plan.original_plan,
                    "updated_plan": plan.updated_plan,
                    "created_at": (
                        plan.created_at.strftime("%Y-%m-%d %H:%M")
                        if plan.created_at
                        else ""
                    ),
                }
            )

        return [
            {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "weight": user.weight,
                "goal": user.goal,
                "intensity": user.intensity,
                "schedule": user.schedule,
                "plans": plans_by_user.get(user.id, []),
            }
            for user in users
        ]