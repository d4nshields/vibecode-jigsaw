# Jigsaw Puzzle Generator and Extractor

NOTE:  the programs in this repository were created as a by-product of an experiment in "Vibe Coding" taking place in early May 2025.   Rather humorously, the original prompts generated some truly awful code, but after I added "Why are you being so stubborn!   Just do it the way I explained"   It all began to fall into place...

This repository contains two complementary Python scripts that work together to create custom jigsaw puzzles:

1. `gen_jigsaw.py` - Generates SVG files with jigsaw puzzle cut patterns
2. `jigsaw_piece_extractor.py` - Cuts an input image into individual puzzle pieces using the SVG pattern

## Installation

### Requirements

- Python 3.6+
- Dependencies from requirements.txt

Install all required dependencies:

```bash
pip install -r requirements.txt
```

Some systems might need Cairo installed for SVG processing:

- **Ubuntu/Debian**: `sudo apt-get install libcairo2-dev`
- **macOS**: `brew install cairo`
- **Windows**: Cairo is included with the pip package

## Workflow Overview

The typical workflow consists of two steps:

1. Generate a jigsaw puzzle pattern as an SVG file
2. Use the SVG pattern to cut an image into individual puzzle pieces

### Example Workflow

```bash
# Set common variables
export DIM="16 16"
export DIM_STR="16x16"

# Step 1: Generate the jigsaw pattern
python gen_jigsaw.py --grid $DIM --jitter 10 --tabsize 22 --seed 42 --width 2048 --height 2048 --radius 3.0 -o jigsaw-$DIM_STR.svg

# Step 2: Cut an image into puzzle pieces
python jigsaw_piece_extractor.py cat1.png jigsaw-$DIM_STR.svg --fixed-size -o cat-$DIM_STR
```

## Script 1: Jigsaw Pattern Generator (`gen_jigsaw.py`)

This script generates an SVG file containing a jigsaw puzzle pattern with customizable parameters.

### Usage

```
python gen_jigsaw.py --grid COLS ROWS [options]
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `--grid COLS ROWS` | Number of columns and rows in the puzzle grid |
| `--width WIDTH` | Width of the output SVG in pixels (default: 1000) |
| `--height HEIGHT` | Height of the output SVG in pixels (default: 1000) |
| `--jitter JITTER` | Random variation in grid line positions (default: 15) |
| `--tabsize SIZE` | Size of the puzzle tabs (default: 20) |
| `--seed SEED` | Random seed for reproducible patterns (default: random) |
| `--radius RADIUS` | Radius for puzzle tab curves (default: 2.5) |
| `-o, --output FILE` | Output SVG filename (default: jigsaw.svg) |

### Examples

Create a simple 4×3 puzzle:
```bash
python gen_jigsaw.py --grid 4 3 -o simple_puzzle.svg
```

Create a detailed 20×20 puzzle with specific parameters:
```bash
python gen_jigsaw.py --grid 20 20 --jitter 8 --tabsize 25 --radius 4.0 --seed 123 -o detailed_puzzle.svg
```

## Script 2: Jigsaw Piece Extractor (`jigsaw_piece_extractor.py`)

This script takes an input image and an SVG puzzle pattern to cut the image into individual puzzle pieces.

### Usage

```
python jigsaw_piece_extractor.py IMAGE SVG [options]
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `IMAGE` | Input image to be cut into puzzle pieces |
| `SVG` | SVG file defining the jigsaw cuts |
| `-o, --output DIR` | Output folder for the puzzle pieces (default: pieces) |
| `--prefix PREFIX` | Prefix for output filenames (default: piece) |
| `--format FORMAT` | Output image format (default: png) |
| `--padding PADDING` | Padding around pieces in pixels (default: 30) |
| `--fixed-size` | Output all pieces with the same dimensions |
| `--output-width WIDTH` | Fixed width for output pieces (default: auto-calculated) |
| `--output-height HEIGHT` | Fixed height for output pieces (default: auto-calculated) |
| `--debug` | Save debug images |

### Examples

Basic usage:
```bash
python jigsaw_piece_extractor.py photo.jpg puzzle.svg -o output_pieces
```

Fixed-size pieces with automatic dimensions:
```bash
python jigsaw_piece_extractor.py photo.jpg puzzle.svg --fixed-size -o output_pieces
```

Specify custom piece dimensions:
```bash
python jigsaw_piece_extractor.py photo.jpg puzzle.svg --fixed-size --output-width 300 --output-height 300 -o output_pieces
```

## Output

The extractor script creates individual puzzle pieces in the specified output directory. The pieces are named according to their position in the grid:

- `piece_00_00.png` - Top-left piece (row 0, column 0)
- `piece_00_01.png` - First row, second column
- etc.

When using the `--fixed-size` option, all pieces will have identical dimensions with their content centered, making them ideal for digital puzzles, printing, or game development.

## Advanced Features

### Debug Mode

Add the `--debug` flag to the extractor script to save intermediate files that can help troubleshoot issues:
```bash
python jigsaw_piece_extractor.py photo.jpg puzzle.svg --debug
```

### Allocation Map

The extractor uses an allocation map system to ensure each pixel is assigned to exactly one piece, preventing duplication or gaps when reassembling the puzzle.

## Troubleshooting

### Common Issues

1. **SVG parsing errors**: Ensure your SVG file has proper structure with horizontal, vertical, and border paths.

2. **Memory errors with large images**: Try reducing the image size or using a smaller grid.

3. **CairoSVG errors**: Verify that Cairo is properly installed on your system.

## License

Copyright (c) Daniel Shields 2025

This project is licensed under the Artistic License 2.0.
You may use, modify, and distribute this software under the terms of that license.
