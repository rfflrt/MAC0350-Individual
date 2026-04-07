from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from models import User, UserPowers, UserStats, BestTime, get_session, create_tables
from typing import Optional
import game as g

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
    create_tables()

def get_active_user(request: Request, session: Session = Depends(get_session)) -> Optional[User]:
    name = request.cookies.get("username")
    if not name:
         return None
    return session.exec(select(User).where(User.name == name)).first()


# LOGIN
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    error = request.query_params.get("error")
    return templates.TemplateResponse(request, "login_signup.html", {"error": error})

@app.post("/login")
async def login_post(
    name: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.name == name)).first()

    if not user or user.password != password:
            return RedirectResponse("/login?error=Invalid+username+or+password", status_code=302)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("username", name)
    return resp

@app.post("/signup")
async def register(
    name: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    existing = session.exec(select(User).where(User.name == name)).first()
    if existing:
         return RedirectResponse("/login?error=Username+already+exists", status_code=302)
    
    user = User(name=name, password=password)
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserPowers(user_id=user.id))
    session.add(UserStats(user_id=user.id))
    session.commit()
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("username", name)
    return resp

# HOME
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login")
    
    powers = session.exec(select(UserPowers).where(UserPowers.user_id == user.id)).first()
    stats  = session.exec(select(UserStats).where(UserStats.user_id == user.id)).first()

    return templates.TemplateResponse(request, "home.html", {
         "user": user, "powers": powers, "stats": stats, "difficulties": g.difficulties})

# SHOP
@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request, user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login")
    powers = session.exec(select(UserPowers).where(UserPowers.user_id == user.id)).first()
    return templates.TemplateResponse(request, "shop.html", {
        "user": user, "powers": powers, "costs": g.POWER_COSTS})

@app.post("/shop/buy", response_class=HTMLResponse)
async def buy(request: Request, power: str = Form(...), user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login")
    
    cost = g.power_costs.get(power, 0)
    powers = session.exec(select(UserPowers).where(UserPowers.user_id == user.id)).first()
    error = None

    if user.points < cost:
        error = "Not enough points"
    else:
        user.points -= cost
        setattr(powers, power, getattr(powers, power) + 1)
        session.add(user)
        session.add(powers)
        session.commit()
        session.refresh(user)
        session.refresh(powers)
    
    resp = templates.TemplateResponse(request, "shop_grid.html", {"user": user, "powers": powers, "costs": g.POWER_COSTS, "error": error})
    return resp

# LEADERBOARD
@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request, user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login")

    best_times = {}
    for diff in ["easy", "medium", "hard"]:
        rows = session.exec(select(BestTime, User).join(User, BestTime.user_id == User.id).where(BestTime.difficulty == diff).order_by(BestTime.time_seconds)).all()
        seen = {}
        for bt, u in rows:
            if u.name not in seen:
                seen[u.name] = round(bt.time_seconds, 1)
        best_times[diff] = list(seen.items())[:10]

    most_wins = session.exec(select(UserStats, User).join(User, UserStats.user_id == User.id).order_by(UserStats.games_won.desc())).all()

    return templates.TemplateResponse(request, "leaderboard.html", {
        "user": user,
        "best_times": best_times,
        "most_wins": [(u.name, s.games_won, s.best_streak) for s, u in most_wins[:10]],
    })