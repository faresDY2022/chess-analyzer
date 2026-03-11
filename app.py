#!/usr/bin/env python3
"""Chess Analyzer Web UI — powered by Stockfish."""

from flask import Flask, render_template, jsonify, request
import chess
import chess.engine
import random
import shutil
import os

app = Flask(__name__)

STOCKFISH_PATH = shutil.which("stockfish") or os.environ.get("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")
DEPTH = 20
TOP_MOVES = 5

engine = None
board = chess.Board()


def get_engine():
    global engine
    if engine is None:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    return engine


def format_score(score):
    pov = score.white()
    if pov.is_mate():
        mate_in = pov.mate()
        return f"M{mate_in}" if mate_in > 0 else f"M{mate_in}"
    cp = pov.score()
    return cp


def analyze_position(brd, depth=DEPTH, top_n=TOP_MOVES):
    eng = get_engine()
    results = eng.analyse(brd, chess.engine.Limit(depth=depth), multipv=top_n)
    moves = []
    for info in results:
        move = info["pv"][0]
        score = info["score"]
        raw_score = format_score(score)
        pv_moves = []
        temp = brd.copy()
        for m in info["pv"][:8]:
            pv_moves.append(temp.san(m))
            temp.push(m)
        moves.append({
            "move": brd.san(move),
            "uci": move.uci(),
            "score": raw_score,
            "line": " ".join(pv_moves),
            "depth": info.get("depth", depth),
        })
    return moves


def pick_human_move(moves, accuracy):
    """Pick a move based on accuracy%. Higher accuracy = more likely to pick the best move.
    accuracy=100 always picks best, accuracy=60 picks best ~60% of the time."""
    if not moves or len(moves) == 1:
        return 0
    roll = random.random() * 100
    if roll < accuracy:
        return 0  # best move
    # Pick from remaining moves, weighted towards 2nd best
    weights = []
    for i in range(1, len(moves)):
        weights.append(1.0 / i)  # 2nd=1.0, 3rd=0.5, 4th=0.33, 5th=0.25
    total = sum(weights)
    weights = [w / total for w in weights]
    return random.choices(range(1, len(moves)), weights=weights, k=1)[0]


def board_state():
    return {
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "moveNumber": board.fullmove_number,
        "isGameOver": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
        "isCheck": board.is_check(),
        "legalMoves": [board.san(m) for m in board.legal_moves],
        "moveStack": get_move_history(),
    }


def get_move_history():
    moves = []
    temp = chess.Board()
    for move in board.move_stack:
        san = temp.san(move)
        moves.append({
            "san": san,
            "uci": move.uci(),
            "number": temp.fullmove_number,
            "color": "white" if temp.turn == chess.WHITE else "black",
        })
        temp.push(move)
    return moves


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def state():
    return jsonify(board_state())


@app.route("/api/move", methods=["POST"])
def make_move():
    global board
    data = request.json
    uci = data.get("uci", "")
    accuracy = data.get("accuracy", 65)
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            move = chess.Move.from_uci(uci + "q")
            if move not in board.legal_moves:
                return jsonify({"error": "Illegal move"}), 400
        board.push(move)
        result = board_state()
        if not board.is_game_over():
            analysis = analyze_position(board)
            result["analysis"] = analysis
            pick = pick_human_move(analysis, accuracy)
            result["recommended"] = pick
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if board.is_game_over():
        return jsonify({"error": "Game is over"})
    data = request.json or {}
    accuracy = data.get("accuracy", 65)
    analysis = analyze_position(board)
    pick = pick_human_move(analysis, accuracy)
    return jsonify({"analysis": analysis, "recommended": pick, **board_state()})


@app.route("/api/undo", methods=["POST"])
def undo():
    global board
    if board.move_stack:
        board.pop()
    return jsonify(board_state())


@app.route("/api/reset", methods=["POST"])
def reset():
    global board
    board = chess.Board()
    return jsonify(board_state())


@app.route("/api/fen", methods=["POST"])
def load_fen():
    global board
    data = request.json
    fen = data.get("fen", "")
    try:
        board = chess.Board(fen)
        return jsonify(board_state())
    except ValueError:
        return jsonify({"error": "Invalid FEN"}), 400


if __name__ == "__main__":
    print("\n  Chess Analyzer UI")
    print("  Open http://localhost:8080 in your browser\n")
    app.run(debug=False, port=8080)
