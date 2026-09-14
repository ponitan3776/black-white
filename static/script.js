const boardEl = document.getElementById("board");
const messageEl = document.getElementById("message");
const blackScoreEl = document.getElementById("black-score");
const whiteScoreEl = document.getElementById("white-score");
const newGameBtn = document.getElementById("new-game");

let state = null;
let busy = false;

function createCells() {
  boardEl.innerHTML = "";
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = r;
      cell.dataset.col = c;
      cell.addEventListener("click", () => onCellClick(r, c));
      boardEl.appendChild(cell);
    }
  }
}

function render(s) {
  state = s;
  const cells = boardEl.children;
  const validSet = new Set((s.validMoves || []).map(([r, c]) => r * 8 + c));

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const cell = cells[r * 8 + c];
      cell.className = "cell";

      const v = s.board[r][c];
      if (v === 1) cell.classList.add("black");
      else if (v === 2) cell.classList.add("white");

      if (!s.finished && validSet.has(r * 8 + c)) {
        cell.classList.add("valid");
      }
    }
  }

  blackScoreEl.textContent = s.score.black;
  whiteScoreEl.textContent = s.score.white;
  messageEl.textContent = s.message;
}

async function onCellClick(r, c) {
  if (busy || !state || state.finished) return;

  const validSet = new Set((state.validMoves || []).map(([rr, cc]) => rr * 8 + cc));
  if (!validSet.has(r * 8 + c)) return;

  busy = true;
  try {
    const res = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row: r, col: c }),
    });
    const data = await res.json();

    if (data.error) {
      messageEl.textContent = data.error;
    } else {
      render(data);
    }
  } catch (e) {
    messageEl.textContent = "通信エラーが発生しました";
  } finally {
    busy = false;
  }
}

async function newGame() {
  busy = true;
  try {
    const res = await fetch("/api/new", { method: "POST" });
    render(await res.json());
  } catch (e) {
    messageEl.textContent = "通信エラーが発生しました";
  } finally {
    busy = false;
  }
}

newGameBtn.addEventListener("click", newGame);

createCells();
newGame();
