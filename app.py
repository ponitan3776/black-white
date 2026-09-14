import os

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

BOARD_SIZE = 8
EMPTY = 0
BLACK = 1
WHITE = 2

DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]

PLAYER_NAME = {BLACK: "黒", WHITE: "白"}


def initial_board():
    """オセロの初期盤面を作る。"""
    board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    board[3][3] = WHITE
    board[3][4] = BLACK
    board[4][3] = BLACK
    board[4][4] = WHITE
    return board


def find_moves(board, player):
    """player が置けるマスと、そのときに裏返る石の一覧を返す。"""
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


def build_state(board, current, finished, message):
    """フロントに返すJSONを組み立てる。"""
    black, white = count_stones(board)
    valid = [] if finished else [list(pos) for pos in find_moves(board, current)]
    return {
        "board": board,
        "current": current,
        "finished": finished,
        "message": message,
        "validMoves": valid,
        "score": {"black": black, "white": white},
    }


def start_new_game():
    board = initial_board()
    session["board"] = board
    session["current"] = BLACK
    session["finished"] = False
    return build_state(board, BLACK, False, "黒の番です")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/new", methods=["POST"])
def api_new():
    return jsonify(start_new_game())


@app.route("/api/move", methods=["POST"])
def api_move():
    if "board" not in session:
        return jsonify(start_new_game())

    board = session["board"]
    current = session["current"]
    finished = session["finished"]

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

    # 石を置いて裏返す
    board[row][col] = current
    for r, c in moves[(row, col)]:
        board[r][c] = current

    opponent = WHITE if current == BLACK else BLACK

    if find_moves(board, opponent):
        current = opponent
        message = f"{PLAYER_NAME[current]}の番です"
    elif find_moves(board, current):
        message = (f"{PLAYER_NAME[opponent]}は置ける場所がないためパスしました。"
                   f"{PLAYER_NAME[current]}の番です")
    else:
        finished = True
        black, white = count_stones(board)
        if black > white:
            message = f"ゲーム終了！ 黒の勝ち（{black} - {white}）"
        elif white > black:
            message = f"ゲーム終了！ 白の勝ち（{white} - {black}）"
        else:
            message = f"ゲーム終了！ 引き分け（{black} - {white}）"

    session["board"] = board
    session["current"] = current
    session["finished"] = finished

    return jsonify(build_state(board, current, finished, message))


if __name__ == "__main__":
    app.run(debug=True)
