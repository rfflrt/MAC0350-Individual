from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from models import User, UserPowers, UserStats, BestTime, Game, get_session, create_tables
from typing import Optional
import game as G
import json
import time

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
         "user": user, "powers": powers, "stats": stats, "difficulties": G.difficulties})

# SHOP
@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request, user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login")
    powers = session.exec(select(UserPowers).where(UserPowers.user_id == user.id)).first()
    return templates.TemplateResponse(request, "shop.html", {
        "user": user, "powers": powers, "costs": G.power_costs})

@app.post("/shop/buy", response_class=HTMLResponse)
async def buy(request: Request, power: str = Form(...), user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login")
    
    cost = G.power_costs.get(power, 0)
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
    
    resp = templates.TemplateResponse(request, "shop_grid.html", {"user": user, "powers": powers, "costs": G.POWER_COSTS, "error": error})
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

# GAME
@app.post("/game/new", response_class=HTMLResponse)
async def new_game(request: Request, difficulty: str = Form(...),
    custom_rows:  int = Form(None),
    custom_cols:  int = Form(None),
    custom_mines: int = Form(None),
    user: User = Depends(get_active_user),
    session: Session = Depends(get_session)):
    
    if not user:
        return RedirectResponse("/login")

    if difficulty in G.difficulties:
        d = G.difficulties[difficulty]
        rows, cols, mines = d["rows"], d["cols"], d["mines"]
    
    else:
        difficulty = "custom"
        rows  = max(5,  min(30,  custom_rows  or 10))
        cols  = max(5,  min(50,  custom_cols  or 10))
        mines = max(1,  min(rows * cols - 9, custom_mines or 10))

    g = Game(user_id=user.id, difficulty=difficulty,
             rows=rows, cols=cols, mine_count=mines)
    
    session.add(g)
    session.commit()
    session.refresh(g)

    powers = session.exec(select(UserPowers).where(UserPowers.user_id == user.id)).first()

    return templates.TemplateResponse(request, "game.html", {
        "user": user, "game": g, "powers": powers,
        "power_costs": G.power_costs})

@app.post("/game/{game_id}/action")
def game_action(
    game_id: int,
    action: str = Form(...),
    row: int = Form(None),
    col: int = Form(None),
    user: User = Depends(get_active_user),
    session: Session = Depends(get_session)):
    if not user:
        return JSONResponse({"error": "not logged in"}, status_code=401)

    g = session.get(Game, game_id)
    if not g or g.user_id != user.id or g.status != "active":
        return JSONResponse({"error": "invalid game"}, status_code=400)

    mines = G.to_set(g.mines)
    open = G.to_set(g.open)
    flags = G.to_set(g.flags)
    result = {}

    if action == "reveal":
        if (row, col) in open:
            mines = {(m[0], m[1]) for m in json.loads(g.mines)}
            chord = G.reveal_numbered(row, col, g.rows, g.cols, mines, open, flags)
            if chord["hit_mine"]:
                g.status = "lost"
                g.end_time = time.time()
                finish_game(user, g, won=False, session=session)
                result["status"] = "lost"
                result["mine"] = chord["mine_cell"]
            else:
                open |= chord["newly_open"]
                g.open = G.to_json(open)
                if G.won(g.rows, g.cols, g.mine_count, open):
                    g.status   = "won"
                    g.end_time = time.time()
                    pts = finish_game(user, g, won=True, session=session)
                    result["status"] = "won"
                    result["points_earned"] = pts

        elif (row, col) not in flags:
            if not g.first_click:
                mine_list, mover_idxs = G.place_mines(g.rows, g.cols, g.mine_count, row, col)
                g.mines = json.dumps(mine_list)
                g.mover_index = json.dumps(list(mover_idxs))
                g.first_click = True
                g.start_time = time.time()

            mine_set = {(m[0], m[1]) for m in json.loads(g.mines)}

            if (row, col) in mine_set:
                g.status   = "lost"
                g.end_time = time.time()
                finish_game(user, g, won=False, session=session)
                result["status"] = "lost"
                result["mine"] = [row, col]
            
            else:
                new = G.reveal(row, col, g.rows, g.cols, mine_set, open, flags)
                open |= new
                g.open = G.to_json(open)
                if G.is_won(g.rows, g.cols, g.mine_count, open):
                    g.status   = "won"
                    g.end_time = time.time()
                    pts = finish_game(user, g, won=True, session=session)
                    result["status"]        = "won"
                    result["points_earned"] = pts

    elif action == "flag":
        if (row, col) not in open:
            if (row, col) in flags:
                flags.discard((row, col))
            else:
                flags.add((row, col))
            g.flags = G.to_json(flags)

    session.add(g)
    session.commit()

    mines = G.to_set(g.mines)

    result.setdefault("status", "ok")
    result["board"] = G.build_board(g.rows, g.cols, mine_set, open, flags, reveal_all=(g.status != "active"))
    result["flags_remaining"] = g.mine_count - len(flags)
    result["freeze_ticks"] = g.freeze_ticks
    return JSONResponse(result)

@app.post("/game/{game_id}/power", response_class=HTMLResponse)
def use_power(request: Request, game_id: int, power: str = Form(...),
    user: User = Depends(get_active_user), session: Session = Depends(get_session)):

    if not user:
        return HTMLResponse("", status_code=401)

    g = session.get(Game, game_id)
    powers = session.exec(select(UserPowers).where(UserPowers.user_id == user.id)).first()

    if not g or g.user_id != user.id or g.status != "active":
        return HTMLResponse("", status_code=400)

    owned = getattr(powers, power, 0)
    if owned <= 0:
        return HTMLResponse("", status_code=400)

    mines = G.to_set(g.mines_json)
    open = G.to_set(g.open_json)
    flags = G.to_set(g.flags_json)

    setattr(powers, power, owned - 1)
    used = json.loads(g.powers_used)
    used.append(power)
    g.powers_used = json.dumps(used)

    board_data = {}

    if power == "russian_roulette":
        res = G.power_roulette(g.rows, g.cols, mines, open, flags)
        if res["hit"]:
            g.status   = "lost"
            g.end_time = time.time()
            finish_game(user, g, won=False, session=session)
            board_data["status"]   = "lost"
            board_data["mine"]     = res["mine_cell"]
        else:
            for r, c in res["newly_open"]:
                open.add((r, c))
            g.open = G.to_json(open)
    
    elif power == "mine_freeze":
        g.freeze_ticks = 5
    
    elif power == "hint":
        hint = G.power_hint(g.rows, g.cols, mine_set, open, flags)
        board_data["hint_cell"] = hint

    if g.status == "active" and G.won(g.rows, g.cols, g.mine_count, open):
        g.status = "won"
        g.end_time = time.time()
        pts = finish_game(user, g, won=True, session=session)
        board_data["status"] = "won"
        board_data["points_earned"] = pts

    session.add(g)
    session.add(powers)
    session.commit()

    mine_set = G.to_set(g.mines)

    board_data["board"] = G.build_board(g.rows, g.cols, mine_set, open, flags,
                                        reveal_all=(g.status != "active"))
    board_data["flags_remaining"] = g.mine_count - len(flags)
    board_data["freeze_ticks"] = g.freeze_ticks

    response = templates.TemplateResponse(request, "powers_bar.html", {
        "game": g, "powers": powers, "power_costs": G.power_costs})
    response.headers["HX-Trigger"] = json.dumps({"boardUpdate": board_data})
    return response

@app.post("/game/{game_id}/tick")
def game_tick(game_id: int, user: User = Depends(get_active_user), session: Session = Depends(get_session)):
    if not user:
        return JSONResponse({"moved": False})

    g = session.get(Game, game_id)
    if not g or g.user_id != user.id or g.status != "active" or not g.first_click:
        return JSONResponse({"moved": False})

    mines = G.to_set(g.mines)
    open = G.to_set(g.open)
    flags = G.to_set(g.flags)

    if g.freeze_ticks > 0:
        g.freeze_ticks -= 1
        session.add(g)
        session.commit()
        return JSONResponse({
            "moved": False, "frozen": True,
            "freeze_ticks": g.freeze_ticks,
            "board": G.build_board(g.rows, g.cols, mine_set, open, flags)})

    mine_list = json.loads(g.mines)
    mover_idxs = set(json.loads(g.mover_index))
    mine_list  = G.move_mines(mine_list, mover_idxs, g.rows, g.cols, open, flags)
    mine_set = {(m[0], m[1]) for m in mine_list}
    g.mines = json.dumps(mine_list)
    session.add(g)
    session.commit()

    return JSONResponse({
        "moved": True, "freeze_ticks": 0,
        "board": G.build_board(g.rows, g.cols, mine_set, open, flags)})

def finish_game(user: User, g: Game, won: bool, session: Session):
    stats = session.exec(select(UserStats).where(UserStats.user_id == user.id)).first()
    if won:
        stats.games_won += 1
        stats.current_streak += 1
        stats.best_streak = max(stats.best_streak, stats.current_streak)
        elapsed = g.end_time - g.start_time
        pts     = G.points(g.difficulty, elapsed)
        user.points += pts
        session.add(user)
        if g.difficulty != "custom":
            session.add(BestTime(user_id=user.id, difficulty=g.difficulty, time_seconds=elapsed))
    else:
        stats.games_lost     += 1
        stats.current_streak  = 0
        pts = 0
    session.add(stats)
    return pts
