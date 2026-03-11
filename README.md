# Chess Analyzer — Stockfish

A web-based chess analysis tool powered by the Stockfish engine. Features an interactive drag-and-drop board, real-time position analysis, and a human-like accuracy mode that recommends moves at a configurable skill level.

## Features

- Interactive chess board with drag-and-drop pieces
- Stockfish engine analysis (depth 20, top 5 moves)
- Accuracy slider (40%–100%) — simulates human-level play by occasionally recommending suboptimal moves
- "Play This Move" panel — shows the recommended move with quality tags (Best / Good / Inaccuracy)
- Evaluation bar and score
- Full move history
- FEN position loading
- Flip board, undo, new game controls

## Requirements

- Python 3.9+
- macOS (Homebrew) or Linux

## Installation

### 1. Install Stockfish

**macOS:**
```bash
brew install stockfish
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install stockfish
```

### 2. Install Python dependencies

```bash
pip3 install flask python-chess
```

### 3. Verify Stockfish path

The app expects Stockfish at `/opt/homebrew/bin/stockfish` (default Homebrew path on Apple Silicon). If your path is different, update `STOCKFISH_PATH` in `app.py`:

```bash
which stockfish
```

## How to Run

```bash
cd chess-analyzer
python3 app.py
```

Then open **http://localhost:8080** in your browser.

## Usage

1. **Make moves** — drag and drop pieces on the board
2. **Set accuracy** — use the slider under the board (65% = human-like, 100% = perfect engine play)
3. **Play This Move** — shows the recommended move based on your accuracy setting
4. **Best Moves panel** — always shows the top 5 engine moves with evaluations
5. **Load a position** — paste a FEN string in the input field and click Load
6. **Analyze** — click the Analyze button to evaluate the current position without making a move

## Project Structure

```
chess-analyzer/
├── app.py                    # Flask backend + Stockfish integration
├── analyzer.py               # CLI version (standalone)
├── templates/
│   └── index.html            # Web UI
├── static/
│   ├── css/
│   │   └── chessboard.min.css
│   ├── js/
│   │   ├── jquery.min.js
│   │   ├── chessboard.min.js
│   │   └── chess.min.js
│   └── img/
│       └── pieces/           # Chess piece images (PNG)
└── README.md
```
