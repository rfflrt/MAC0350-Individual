import random

difficulties = {"easy": {"rows": 9, "cols": 9, "mines": 10},
                "medium": {"rows": 16, "cols": 16, "mines": 40},
                "hard": {"rows": 16, "cols": 30, "mines": 99}}

power_costs = {"good_start": 30, "russian_roulette": 20,
                "mine_freeze": 40, "hint": 25}

points_base = {"easy": 50, "medium": 150, "hard": 400}

def place_mines(rows, cols, count, safeR, safeC):
    safe = {(safeR + r, safeC + c)
        for r in range(-1, 1) for c in range(-1, 1)
        if 0 <= safeR+r and safeR+r < rows and
        0 <= safeC+c and safeC+c < cols}
    
    candidates = [(r,c) for r in range(rows) for c in range(cols)
                  if (r,c) not in safe]
    mines = random.sample(candidates, count)

    movers_qty = len(mines) * 0.1
    movers = set(random.sample(range(len(mines)), movers_qty))

    return mines, movers