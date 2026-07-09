from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models import SubjectRelation


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    birth_date: date
    relation: SubjectRelation


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    birth_date: date
    relation: SubjectRelation
