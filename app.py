import os

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

BOARD_SIZE = 8
EMPTY, BLACK, WHITE = 0, 1, 2

DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]

PLAYER_NAME = {BLACK: "黒", WHITE: "白"}

# 位置の評価値（角が高く、角の隣が低い）
WEIGHTS = [
    [ 120, -20,  20,   5,   5,  20, -20,  120],
    [ -20, -40,  -5,  -5,  -5,  -5, -40,  -20],
    [  20,  -5,  15,   3,   3,  15,  -5,   20],
    [   5,  -5,   3,   3,   3,   3,  -5,    5],
    [   5,  -5,   3,   3,   3,   3,  -5,    5],
    [  20,  -5,  15,   3,   3,  15,  -5,   20],
    [ -20, -40,  -5,  -5,  -5,  -5, -40,  -20],
    [ 120, -20,  20,   5,   5,  20, -20,  120],
]

AI_DEPTH = 4          # CPUの読みの深さ（大きいほど強いが遅い）
AI_PLAYER = WHITE     # CPUは白（＝後手）


# ---------- 基本ロジック ----------
def initial_board():
    board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    board[3][3] = WHITE
    board[3][4] = BLACK
    board[4][3] = BLACK
    board[4][4] = WHITE
    return board


def find_moves(board, player):
    """player が置けるマスと、そのときに裏返る石の一覧。"""
    moves = {}
    opponent = WHITE if player == BLACK else BLACK

    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] != EMPTY:
                continue
            flips = []
            for dr, dc in DIRECTIONS:
                r, c = row + dr, col + dc
                line = []
                while (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE
                       and board[r][c] == opponent):
                    line.append((r, c))
                    r += dr
                    c += dc
                if (line and 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE
                        and board[r][c] == player):
                    flips.extend(line)
            if flips:
                moves[(row, col)] = flips
    return moves


def count_stones(board):
    black = sum(row.count(BLACK) for row in board)
    white = sum(row.count(WHITE) for row in board)
    return black, white


def apply_move_board(board, row, col, flips, player):
    """新しい盤面を返す（元は変更しない）。"""
    new_board = [r[:] for r in board]
    new_board[row][col] = player
    for r, c in flips:
        new_board[r][c] = player
    return new_board


def next_turn(board, current):
    """次の手番・終了フラグ・メッセージを返す。"""
    opponent = WHITE if current == BLACK else BLACK

    if find_moves(board, opponent):
        return opponent, False, f"{PLAYER_NAME[opponent]}の番です"

    if find_moves(board, current):
        return current, False, (
            f"{PLAYER_NAME[opponent]}は置ける場所がないためパスしました。"
            f"{PLAYER_NAME[current]}の番です"
        )

    black, white = count_stones(board)
    if black > white:
        msg = f"ゲーム終了！ 黒の勝ち（{black} - {white}）"
    elif white > black:
        msg = f"ゲーム終了！ 白の勝ち（{white} - {black}）"
    else:
        msg = f"ゲーム終了！ 引き分け（{black} - {white}）"
    return current, True, msg


def build_state(board, current, finished, message):
    valid = [] if finished else [list(pos) for pos in find_moves(board, current)]
    black, white = count_stones(board)
    return {
        "board": board,
        "current": current,
        "finished": finished,
        "message": message,
        "validMoves": valid,
        "score": {"black": black, "white": white},
    }


# ---------- AI ----------
def evaluate(board, ai_player):
    """ai_player 視点のスコア。位置＋着手可能数。"""
    opponent = WHITE if ai_player == BLACK else BLACK

    positional = 0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            v = board[r][c]
            if v == ai_player:
                positional += WEIGHTS[r][c]
            elif v == opponent:
                positional -= WEIGHTS[r][c]

    my_moves = len(find_moves(board, ai_player))
    opp_moves = len(find_moves(board, opponent))
    mobility = (my_moves - opp_moves) * 8

    return positional + mobility


def minimax(board, player, depth, alpha, beta, ai_player):
    """αβ枝刈り付きミニマックス。戻り値: (評価値, 最善手)"""
    opponent = WHITE if player == BLACK else BLACK
    moves = find_moves(board, player)

    if not moves:
        # パス or 終局
        if not find_moves(board, opponent):
            black, white = count_stones(board)
            diff = (black - white) if ai_player == BLACK else (white - black)
            return diff * 10000, None
        return minimax(board, opponent, depth, alpha, beta, ai_player)

    if depth == 0:
        return evaluate(board, ai_player), None

    # ムーブオーダリング（評価の高いマスから読むと枝刈りが効く）
    ordered = sorted(moves.items(), key=lambda x: -WEIGHTS[x[0][0]][x[0][1]])

    best_move = None
    if player == ai_player:
        max_eval = -float("inf")
        for (r, c), flips in ordered:
            nb = apply_move_board(board, r, c, flips, player)
            val, _ = minimax(nb, opponent, depth - 1, alpha, beta, ai_player)
            if val > max_eval:
                max_eval, best_move = val, (r, c)
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float("inf")
        for (r, c), flips in ordered:
            nb = apply_move_board(board, r, c, flips, player)
            val, _ = minimax(nb, opponent, depth - 1, alpha, beta, ai_player)
            if val < min_eval:
                min_eval, best_move = val, (r, c)
            beta = min(beta, val)
            if beta <= alpha:
                break
        return min_eval, best_move


def choose_ai_move(board, ai_player, depth=AI_DEPTH):
    moves = find_moves(board, ai_player)
    if not moves:
        return None
    if len(moves) == 1:
        return next(iter(moves))
    _, move = minimax(board, ai_player, depth, -float("inf"), float("inf"), ai_player)
    return move


# ---------- セッション操作 ----------
def start_new_game(mode="pvp"):
    board = initial_board()
    session["board"] = board
    session["current"] = BLACK
    session["finished"] = False
    session["mode"] = mode
    return build_state(board, BLACK, False, "黒の番です")


# ---------- ルーティング ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/new", methods=["POST"])
def api_new():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "pvp")
    if mode not in ("pvp", "cpu"):
        mode = "pvp"
    return jsonify(start_new_game(mode))


@app.route("/api/move", methods=["POST"])
def api_move():
    if "board" not in session:
        return jsonify(start_new_game())

    board = session["board"]
    current = session["current"]
    finished = session["finished"]
    mode = session.get("mode", "pvp")

    if finished:
        return jsonify({"error": "ゲームは終了しています"}), 400

    data = request.get_json(silent=True) or {}
    row = data.get("row")
    col = data.get("col")
    if not isinstance(row, int) or not isinstance(col, int):
        return jsonify({"error": "座標が不正です"}), 400
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        return jsonify({"error": "座標が不正です"}), 400

    moves = find_moves(board, current)
    if (row, col) not in moves:
        return jsonify({"error": "そこには置けません"}), 400

    # プレイヤーの手を適用
    board = apply_move_board(board, row, col, moves[(row, col)], current)
    current, finished, message = next_turn(board, current)

    # CPUの手番ならAIで指す
    if not finished and mode == "cpu" and current == AI_PLAYER:
        ai_move = choose_ai_move(board, AI_PLAYER)
        if ai_move is not None:
            ai_flips = find_moves(board, AI_PLAYER)[ai_move]
            board = apply_move_board(board, ai_move[0], ai_move[1], ai_flips, AI_PLAYER)
            current, finished, message2 = next_turn(board, current)
            message = f"CPUが ({ai_move[0]}, {ai_move[1]}) に置きました。{message2}"
        else:
            # ありえないが念のため
            current, finished, message = next_turn(board, current)

    session["board"] = board
    session["current"] = current
    session["finished"] = finished

    return jsonify(build_state(board, current, finished, message))


if __name__ == "__main__":
    app.run(debug=True)
