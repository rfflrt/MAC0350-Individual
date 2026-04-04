from sqlmodel import SQLModel, Field, Relationship, Session, create_engine

engine = create_engine("sqlite:///minesweeper.db")

class User(SQLModel, table=True):
    id: int | None = Field(default = None, primary_key=True)
    name: str
    password: str
    points: int = Field(default=0)

class UserPowers(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    good_start: int = Field(default=0)
    russian_roulette: int = Field(default=0)
    mine_freeze: int = Field(default=0)
    hint: int = Field(default=0)

class UserStats(SQLModel, table=True):
    id:             int = Field(default=None, primary_key=True)
    user_id:        int = Field(foreign_key="user.id", unique=True)
    games_won:      int = Field(default=0)
    games_lost:     int = Field(default=0)
    current_streak: int = Field(default=0)
    best_streak:    int = Field(default=0)

def create_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session