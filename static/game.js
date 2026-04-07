document.addEventListener("htmx:afterSwap", () => {
  const gd = document.getElementById("game-data");
  if(gd) initGame(gd.dataset);
});

timerInterval = null;

function initGame(dataset){
    const game_id = parseInt(dataset.gameId)
    const rows = parseInt(dataset.rows)
    const cols = parseInt(dataset.cols)

    let flagMode = false;
    let gameOver = false;
    let hintCell = null;
    let timerStart = null;

    timerInterval = setInterval(() => {
    if(!timerStart || gameOver) return;
    const s = Math.floor((Date.now() - timerStart) / 1000);
    const timer = document.getElementById("timer");
    if (timer) timer.textContent =
      `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    }, 500);

    window.toggleFlag = function (){
    flagMode = !flagMode;
    const lbl = document.getElementById("flag-label");
    const btn = document.getElementById("flag-btn");
    if (lbl) lbl.textContent = flagMode ? "ON" : "OFF";
    if (btn) btn.classList.toggle("active", flagMode);
    };

    function calcCellSize(){
        const hud = document.querySelector(".hud");
        const powers = document.querySelector(".powers-bar");
        const nav = document.querySelector("nav");
        const usedH  = nav.offsetHeight + hud.offsetHeight + powers.offsetHeight + 24;

        const availH = window.innerHeight - usedH;
        const availW = window.innerWidth  - 16;

        const byH = Math.floor(availH / rows);
        const byW = Math.floor(availW / cols);

        return Math.max(14, Math.min(byH, byW, 40));
    }

      function applySize(){
    const el = document.getElementById("board");
    if (!el) return;
    const size = calcCellSize();
    el.style.gridTemplateColumns = `repeat(${COLS}, ${size}px)`;
    el.style.fontSize = `${Math.max(8, Math.floor(size * 0.5))}px`;
    el.querySelectorAll(".cell").forEach(c => {
      c.style.width  = size + "px";
      c.style.height = size + "px";
    });
  }

    window.addEventListener("resize", applySize);

    function renderBoard(board){
        const board = document.getElementById("board");
        if(!board) return;

        if(!board.children.length){
            const size = calcCellSize();
            board.style.gridTemplateColumns = `repeat(${cols}, ${size}px)`;
            board.style.fontSize = `${Math.max(8, Math.floor(size * 0.5))}px`;

            for(let r = 0; r < rows; r++){
                for(let c = 0; c < cols; c++){
                    const div = document.createElement("div");
                    div.id = `c-${r}-${c}`;
                    div.style.width  = size + "px";
                    div.style.height = size + "px";
                    div.addEventListener("click", ()  => handleClick(r, c));
                    div.addEventListener("contextmenu", e => { e.preventDefault(); handleRightClick(r, c); });
                    let pressTimer;
                    div.addEventListener("touchstart", () => {
                        pressTimer = setTimeout(() => { handleRightClick(r, c); pressTimer = null; }, 500);
                    }, { passive: true });
                    div.addEventListener("touchend", () => { if (pressTimer) clearTimeout(pressTimer); });
                    board.appendChild(div);
                }
            }
        }
        for(const row of board)
            for(const cell of row)
                paintCell(cell);
    }

    function paintCell(data){
        const cell = document.getElementById(`c-${data.r}-${data.c}`);
        if(!cell) return;
        cell.className = "cell";
        cell.textContent = "";

        const isHint = hintCell && hintCell[0] === data.r && hintCell[1] === data.c;

        if (data.state === "flag"){
            cell.classList.add("cell-flag");
            cell.textContent = "🚩";
        }
        else if(data.state === "open"){
            if(data.mine){
                cell.classList.add("cell-mine");
                cell.textContent = "💣";
            }
            else{
                cell.classList.add("cell-open");
                if(data.adj > 0){
                    cell.textContent = data.adj;
                    cell.classList.add(`n${data.adj}`);
                }
            }
        }
        else
        el.classList.add(isHint ? "cell-hint" : "cell-hidden");
    }

    function handleClick(r, c){
        if (gameOver) return;
        if(flagMode) sendAction("flag", r, c);
        else sendAction("reveal", r, c);
    }
    
    function handleRightClick(r, c){
        if (gameOver) return;
        sendAction("flag", r, c);
    }
}