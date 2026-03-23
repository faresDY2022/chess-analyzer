#!/usr/bin/env python3
"""Chess Analyzer Web UI — powered by Stockfish. Stateless API."""

from flask import Flask, render_template, jsonify, request
import chess
import chess.engine
import random
import shutil
import os
import threading

app = Flask(__name__)


def find_stockfish():
    found = shutil.which("stockfish")
    if found:
        return found
    env = os.environ.get("STOCKFISH_PATH")
    if env and os.path.isfile(env):
        return env
    for path in ["/usr/games/stockfish", "/usr/bin/stockfish", "/usr/local/bin/stockfish", "/opt/homebrew/bin/stockfish"]:
        if os.path.isfile(path):
            return path
    return "stockfish"


STOCKFISH_PATH = find_stockfish()
DEPTH = 20
TOP_MOVES = 5

engine = None
engine_lock = threading.Lock()


def get_engine():
    global engine
    if engine is None:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception as e:
            print(f"Stockfish error: {e}")
            return None
    return engine


def format_score(score):
    pov = score.white()
    if pov.is_mate():
        mate_in = pov.mate()
        return f"M{mate_in}" if mate_in > 0 else f"M{mate_in}"
    return pov.score()


def analyze_position(brd, depth=DEPTH, top_n=TOP_MOVES):
    eng = get_engine()
    if eng is None:
        return []
    try:
        with engine_lock:
            results = eng.analyse(brd, chess.engine.Limit(depth=depth), multipv=top_n)
    except chess.engine.EngineTerminatedError:
        print("Engine crashed, restarting...")
        global engine
        engine = None
        return []
    except Exception as e:
        print(f"Analysis error: {e}")
        return []
    moves = []
    for info in results:
        move = info["pv"][0]
        raw_score = format_score(info["score"])
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
    if not moves or len(moves) == 1:
        return 0
    if random.random() * 100 < accuracy:
        return 0
    weights = [1.0 / i for i in range(1, len(moves))]
    total = sum(weights)
    weights = [w / total for w in weights]
    return random.choices(range(1, len(moves)), weights=weights, k=1)[0]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Stateless: client sends FEN, server returns analysis."""
    data = request.json or {}
    fen = data.get("fen", chess.STARTING_FEN)
    accuracy = data.get("accuracy", 65)
    try:
        board = chess.Board(fen)
    except ValueError:
        return jsonify({"error": "Invalid FEN"}), 400

    if board.is_game_over():
        return jsonify({"analysis": [], "recommended": 0})

    analysis = analyze_position(board)
    result = {"analysis": analysis}
    if analysis:
        result["recommended"] = pick_human_move(analysis, accuracy)
    return jsonify(result)


@app.route("/api/debug")
def debug():
    eng = get_engine()
    return jsonify({
        "stockfish_path": STOCKFISH_PATH,
        "stockfish_found": shutil.which("stockfish"),
        "engine_loaded": eng is not None,
    })


if __name__ == "__main__":
    print("\n  Chess Analyzer UI")
    print("  Open http://localhost:8080 in your browser\n")
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
