from sqlmodel import SQLModel, Field, Relationship, Session

class User(SQLModel, table=True):
    id: int | None = Field(default = None, primary_key=True)
    name: str
    password: str