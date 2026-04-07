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

    window.toggleFlag = function () {
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

}