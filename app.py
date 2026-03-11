#!/usr/bin/env python3
"""Chess Analyzer Web UI — powered by Stockfish."""

from flask import Flask, render_template, jsonify, request, session
import chess
import chess.engine
import random
import shutil
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chess-analyzer-secret-key-2026")

STOCKFISH_PATH = shutil.which("stockfish") or os.environ.get("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")
DEPTH = 20
TOP_MOVES = 5

engine = None


def get_engine():
    global engine
    if engine is None:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception as e:
            print(f"Stockfish error: {e}")
            print(f"Stockfish path: {STOCKFISH_PATH}")
            return None
    return engine


def get_board():
    """Get board from session FEN, or create new one."""
    fen = session.get("fen")
    if fen:
        try:
            return chess.Board(fen)
        except ValueError:
            pass
    return chess.Board()


def save_board(board):
    """Save board FEN + move history to session."""
    session["fen"] = board.fen()
    # Store move stack as UCI strings
    moves = []
    temp = chess.Board()
    for m in board.move_stack:
        moves.append(m.uci())
        temp.push(m)
    session["moves"] = moves


def load_board_with_history():
    """Load board and replay move history from session."""
    move_list = session.get("moves", [])
    board = chess.Board()
    for uci in move_list:
        try:
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                board.push(move)
        except Exception:
            break
    return board


def format_score(score):
    pov = score.white()
    if pov.is_mate():
        mate_in = pov.mate()
        return f"M{mate_in}" if mate_in > 0 else f"M{mate_in}"
    cp = pov.score()
    return cp


def analyze_position(brd, depth=DEPTH, top_n=TOP_MOVES):
    eng = get_engine()
    if eng is None:
        return []
    try:
        results = eng.analyse(brd, chess.engine.Limit(depth=depth), multipv=top_n)
    except Exception as e:
        print(f"Analysis error: {e}")
        return []
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
    if not moves or len(moves) == 1:
        return 0
    roll = random.random() * 100
    if roll < accuracy:
        return 0
    weights = []
    for i in range(1, len(moves)):
        weights.append(1.0 / i)
    total = sum(weights)
    weights = [w / total for w in weights]
    return random.choices(range(1, len(moves)), weights=weights, k=1)[0]


def board_state(board):
    return {
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "moveNumber": board.fullmove_number,
        "isGameOver": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None,
        "isCheck": board.is_check(),
        "legalMoves": [board.san(m) for m in board.legal_moves],
        "moveStack": get_move_history(board),
    }


def get_move_history(board):
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
    board = load_board_with_history()
    return jsonify(board_state(board))


@app.route("/api/move", methods=["POST"])
def make_move():
    data = request.json
    uci = data.get("uci", "")
    accuracy = data.get("accuracy", 65)
    board = load_board_with_history()
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            move = chess.Move.from_uci(uci + "q")
            if move not in board.legal_moves:
                return jsonify({"error": "Illegal move"}), 400
        board.push(move)
        save_board(board)
        result = board_state(board)
        if not board.is_game_over():
            analysis = analyze_position(board)
            result["analysis"] = analysis
            if analysis:
                pick = pick_human_move(analysis, accuracy)
                result["recommended"] = pick
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/analyze", methods=["POST"])
def analyze():
    board = load_board_with_history()
    if board.is_game_over():
        return jsonify({"error": "Game is over"})
    data = request.json or {}
    accuracy = data.get("accuracy", 65)
    analysis = analyze_position(board)
    result = board_state(board)
    result["analysis"] = analysis
    if analysis:
        pick = pick_human_move(analysis, accuracy)
        result["recommended"] = pick
    return jsonify(result)


@app.route("/api/undo", methods=["POST"])
def undo():
    board = load_board_with_history()
    if board.move_stack:
        board.pop()
    save_board(board)
    return jsonify(board_state(board))


@app.route("/api/reset", methods=["POST"])
def reset():
    board = chess.Board()
    save_board(board)
    return jsonify(board_state(board))


@app.route("/api/fen", methods=["POST"])
def load_fen():
    data = request.json
    fen = data.get("fen", "")
    try:
        board = chess.Board(fen)
        save_board(board)
        return jsonify(board_state(board))
    except ValueError:
        return jsonify({"error": "Invalid FEN"}), 400


@app.route("/api/debug")
def debug():
    """Debug endpoint to check Stockfish status."""
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
