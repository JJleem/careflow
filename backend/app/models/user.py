from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_enum
from app.models.enums import SubjectRelation, UserRole


class User(CreatedAtMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"))
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))

    subjects: Mapped[list["Subject"]] = relationship(back_populates="owner")


class Subject(CreatedAtMixin, Base):
    """피검자. 검사 결과·예약·기록은 계정이 아닌 피검자에 귀속된다 (docs/04 §4.3-1).

    접근 제어는 owner_user_id 하나로 판정: 가족 결과 상담(P2)이 별도 기능이 아니라
    '내 계정 아래 피검자가 여럿'이라는 구조의 자연스러운 결과가 된다.
    """

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(50))
    birth_date: Mapped[date] = mapped_column(Date)
    relation: Mapped[SubjectRelation] = mapped_column(
        pg_enum(SubjectRelation, "subject_relation")
    )

    owner: Mapped[User] = relationship(back_populates="subjects")


class CounselorProfile(CreatedAtMixin, Base):
    __tablename__ = "counselor_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    specialty: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship()
