from sqlmodel import SQLModel, Field, Relationship, Session, create_engine

engine = create_engine("sqlite:///minesweeper.db")

class User(SQLModel, table=True):
    id: int | None = Field(default = None, primary_key=True)
    name: str
    password: str
    points: int = Field(default=0)

def create_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session