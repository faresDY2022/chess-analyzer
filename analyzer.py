#!/usr/bin/env python3
"""
Chess Move Analyzer — powered by Stockfish.
Use for learning and post-game analysis only.

Usage:
  python3 analyzer.py                  # Interactive mode
  python3 analyzer.py --fen "FEN"      # Analyze a specific position
"""

import chess
import chess.engine
import sys
import argparse

STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"
DEPTH = 20
TOP_MOVES = 3


def get_engine():
    try:
        return chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception as e:
        print(f"Error: Could not start Stockfish at {STOCKFISH_PATH}")
        print(f"  {e}")
        sys.exit(1)


def format_score(score, board):
    """Format score from white's perspective, then adjust for side to move."""
    pov = score.white()
    if pov.is_mate():
        mate_in = pov.mate()
        return f"Mate in {mate_in}" if mate_in > 0 else f"Mated in {abs(mate_in)}"
    cp = pov.score()
    return f"{cp / 100:+.2f}"


def analyze_position(engine, board, depth=DEPTH, top_n=TOP_MOVES):
    """Analyze a position and return top moves."""
    results = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=top_n)
    moves = []
    for info in results:
        move = info["pv"][0]
        score = info["score"]
        pv = " ".join(board.san(m) for m in info["pv"][:6])
        moves.append({
            "move": board.san(move),
            "uci": move.uci(),
            "score": format_score(score, board),
            "line": pv,
            "depth": info.get("depth", depth),
        })
    return moves


def print_analysis(moves, board):
    turn = "White" if board.turn == chess.WHITE else "Black"
    print(f"\n  {'=' * 50}")
    print(f"  {turn} to move | Top {len(moves)} moves (depth {moves[0]['depth']})")
    print(f"  {'=' * 50}")
    for i, m in enumerate(moves, 1):
        marker = " <<< BEST" if i == 1 else ""
        print(f"  {i}. {m['move']:>7}  [{m['score']:>8}]  {m['line']}{marker}")
    print(f"  {'=' * 50}\n")


def print_board(board):
    print()
    print(board.unicode(borders=True))


def interactive_mode():
    engine = get_engine()
    board = chess.Board()

    print("\n  Chess Analyzer — Stockfish Engine")
    print("  Commands:")
    print("    <move>     Enter a move (e.g. e4, Nf3, O-O)")
    print("    fen <FEN>  Load a FEN position")
    print("    analyze    Analyze current position")
    print("    undo       Take back last move")
    print("    reset      Reset to starting position")
    print("    board      Show current board")
    print("    moves      Show legal moves")
    print("    quit       Exit")
    print()

    print_board(board)

    while True:
        turn = "White" if board.turn == chess.WHITE else "Black"
        move_num = board.fullmove_number
        prompt = f"  [{move_num}. {turn}] > "

        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "reset":
            board = chess.Board()
            print("  Board reset.")
            print_board(board)
        elif cmd == "undo":
            if board.move_stack:
                board.pop()
                print("  Move undone.")
                print_board(board)
            else:
                print("  No moves to undo.")
        elif cmd == "board":
            print_board(board)
        elif cmd == "moves":
            legal = sorted(board.san(m) for m in board.legal_moves)
            print(f"  Legal moves: {', '.join(legal)}")
        elif cmd in ("analyze", "a", "best"):
            if board.is_game_over():
                print(f"  Game over: {board.result()}")
            else:
                moves = analyze_position(engine, board)
                print_analysis(moves, board)
        elif cmd.startswith("fen "):
            fen = user_input[4:].strip()
            try:
                board = chess.Board(fen)
                print(f"  Position loaded.")
                print_board(board)
            except ValueError:
                print("  Invalid FEN string.")
        else:
            # Try to parse as a chess move
            try:
                move = board.parse_san(user_input)
                board.push(move)
                print_board(board)
                # Auto-analyze after each move
                if not board.is_game_over():
                    moves = analyze_position(engine, board)
                    print_analysis(moves, board)
                else:
                    print(f"  Game over: {board.result()}")
            except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
                print(f"  Invalid move: {user_input} ({e})")

    engine.quit()
    print("  Goodbye!")


def one_shot(fen):
    engine = get_engine()
    board = chess.Board(fen)
    print_board(board)
    moves = analyze_position(engine, board)
    print_analysis(moves, board)
    engine.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chess Analyzer powered by Stockfish")
    parser.add_argument("--fen", type=str, help="Analyze a FEN position")
    args = parser.parse_args()

    if args.fen:
        one_shot(args.fen)
    else:
        interactive_mode()
