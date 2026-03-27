from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    code: int
    name: str
    icon: str | None = None
    description: str | None = None


class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True
