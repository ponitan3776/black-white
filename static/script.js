const boardEl = document.getElementById("board");
const messageEl = document.getElementById("message");
const blackScoreEl = document.getElementById("black-score");
const whiteScoreEl = document.getElementById("white-score");
const newGameBtn = document.getElementById("new-game");
const modeInputs = document.querySelectorAll('input[name="mode"]');

const AI_PLAYER = 2; // WHITE
const FLIP_MS = 500;  // アニメーション時間

let state = null;
let prevBoard = null;
let busy = false;

function currentMode() {
  for (const input of modeInputs) {
    if (input.checked) return input.value;
  }
  return "pvp";
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createCells() {
  boardEl.innerHTML = "";
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = r;
      cell.dataset.col = c;

      // コイン（表裏2面）
      const disc = document.createElement("div");
      disc.className = "disc";
      const f1 = document.createElement("div");
      f1.className = "face face-black";
      const f2 = document.createElement("div");
      f2.className = "face face-white";
      disc.appendChild(f1);
      disc.appendChild(f2);
      cell.appendChild(disc);

      cell.addEventListener("click", () => onCellClick(r, c));
      boardEl.appendChild(cell);
    }
  }
}

function clearAnimClasses(cell) {
  cell.classList.remove(
    "anim-appear-black", "anim-appear-white",
    "anim-flip-black", "anim-flip-white"
  );
}

function render(s) {
  state = s;
  const cells = boardEl.children;
  const validSet = new Set((s.validMoves || []).map(([r, c]) => r * 8 + c));

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const idx = r * 8 + c;
      const cell = cells[idx];
      const newVal = s.board[r][c];
      const oldVal = prevBoard ? prevBoard[r][c] : newVal;

      const isNew = prevBoard && oldVal === 0 && newVal !== 0;
      const isFlip = prevBoard && oldVal !== 0 && newVal !== 0 && oldVal !== newVal;

      // 状態クラス更新
      cell.classList.remove("black", "white", "valid");
      if (newVal === 1) cell.classList.add("black");
      else if (newVal === 2) cell.classList.add("white");
      if (!s.finished && validSet.has(idx)) cell.classList.add("valid");

      // アニメーション
      if (isNew || isFlip) {
        clearAnimClasses(cell);
        // 強制リフロー（連続アニメーションを確実に発火させる）
        void cell.offsetWidth;
        if (isNew) {
          cell.classList.add(newVal === 1 ? "anim-appear-black" : "anim-appear-white");
        } else {
          cell.classList.add(newVal === 1 ? "anim-flip-black" : "anim-flip-white");
        }
      }
    }
  }

  prevBoard = s.board.map((row) => row.slice());
  blackScoreEl.textContent = s.score.black;
  whiteScoreEl.textContent = s.score.white;
  messageEl.textContent = s.message;
}

// アニメ終了時にクラスを掃除
boardEl.addEventListener("animationend", (e) => {
  const cell = e.target.closest(".cell");
  if (cell) clearAnimClasses(cell);
});

async function onCellClick(r, c) {
  if (busy || !state || state.finished) return;

  const validSet = new Set((state.validMoves || []).map(([rr, cc]) => rr * 8 + cc));
  if (!validSet.has(r * 8 + c)) return;

  busy = true;
  try {
    // --- 1) プレイヤーの手を送る ---
    const res = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row: r, col: c }),
    });
    const data = await res.json();

    if (data.error) {
      messageEl.textContent = data.error;
      return;
    }

    render(data);

    // --- 2) CPUの手番なら順番に処理 ---
    const mode = currentMode();
    let cur = data;
    // パスが続く場合に備えてループ（安全のため最大3回）
    for (let i = 0; i < 3; i++) {
      if (mode !== "cpu" || cur.finished || cur.current !== AI_PLAYER) break;

      await sleep(FLIP_MS + 80); // プレイヤーの反転を見せてから
      messageEl.textContent = "CPU考え中…";
      await sleep(120); // 描画反映

      const cpuRes = await fetch("/api/cpu", { method: "POST" });
      const cpuData = await cpuRes.json();
      if (cpuData.error) {
        messageEl.textContent = cpuData.error;
        break;
      }
      render(cpuData);
      cur = cpuData;
    }
  } catch (e) {
    messageEl.textContent = "通信エラーが発生しました";
  } finally {
    busy = false;
  }
}

async function newGame() {
  const mode = currentMode();
  busy = true;
  try {
    const res = await fetch("/api/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    const data = await res.json();
    prevBoard = null; // アニメ抑制（初期配置）
    render(data);
    // 初期盤面を prevBoard に記録して次回からアニメ対象にする
    prevBoard = data.board.map((row) => row.slice());
  } catch (e) {
    messageEl.textContent = "通信エラーが発生しました";
  } finally {
    busy = false;
  }
}

newGameBtn.addEventListener("click", newGame);
for (const input of modeInputs) {
  input.addEventListener("change", newGame);
}

createCells();
newGame();