#!/usr/bin/env python3
# flat.py
import argparse
from pathlib import Path
import pandas as pd

def find_col(df, target, fallbacks):
    cols = {c.lower(): c for c in df.columns}
    for name in [target, *fallbacks]:
        c = cols.get(name.lower())
        if c:
            return c
    raise ValueError(f"Required column '{target}' not found. Available: {list(df.columns)}")

def flatten_file(input_path: Path, output_path: Path, chunk_size: int = 30000, window: int = 30):
    if chunk_size % window != 0:
        raise ValueError(f"chunk_size ({chunk_size}) must be a multiple of window ({window}).")

    flattened_rows = []

    # Process in chunks to keep memory low
    for chunk in pd.read_csv(input_path, chunksize=chunk_size):
        # Resolve column names (case-insensitive + common variants)
        x_col = find_col(chunk, "X", ["x", "acc_x"])
        y_col = find_col(chunk, "Y", ["y", "acc_y"])
        z_col = find_col(chunk, "Z", ["z", "acc_z"])
        t_col = find_col(chunk, "time", ["Time", "timestamp", "datetime"])

        # Keep only needed columns (order matters below)
        chunk = chunk[[x_col, y_col, z_col, t_col]].dropna()

        n = len(chunk)
        if n < window:
            continue  # not enough rows to form a window

        # Convert to numpy for speed
        x = chunk[x_col].to_numpy()
        y = chunk[y_col].to_numpy()
        z = chunk[z_col].to_numpy()
        t = chunk[t_col].to_numpy()

        # Only full windows
        usable = (n // window) * window
        x = x[:usable]; y = y[:usable]; z = z[:usable]; t = t[:usable]

        # Reshape into (num_windows, window)
        xw = x.reshape(-1, window)
        yw = y.reshape(-1, window)
        zw = z.reshape(-1, window)
        tw = t.reshape(-1, window)

        # Build rows
        for i in range(xw.shape[0]):
            row = {}
            for j in range(window):
                row[f"x_{j+1}"] = xw[i, j]
                row[f"y_{j+1}"] = yw[i, j]
                row[f"z_{j+1}"] = zw[i, j]
            # Use the last sample's time in the window (common choice)
            row["Time"] = tw[i, -1]
            flattened_rows.append(row)

    if not flattened_rows:
        # Create empty CSV with expected columns to avoid failing the workflow
        cols = [*(f"x_{i}" for i in range(1, 31)),
                *(f"y_{i}" for i in range(1, 31)),
                *(f"z_{i}" for i in range(1, 31)),
                "Time"]
        pd.DataFrame(columns=cols).to_csv(output_path, index=False)
        return

    pd.DataFrame(flattened_rows).to_csv(output_path, index=False)

def main():
    ap = argparse.ArgumentParser(description="Flatten XYZ time-series into windows.")
    ap.add_argument("--input", "-i", required=True, help="Path to input CSV (e.g., data/foo.csv)")
    ap.add_argument("--output", "-o", help="Output CSV path (default: data/foo__flattened.csv)")
    ap.add_argument("--chunk-size", type=int, default=30000, help="Rows per chunk (multiple of 30)")
    ap.add_argument("--window", type=int, default=30, help="Window size")
    args = ap.parse_args()

    inp = Path(args.input)
    if not args.output:
        out = inp.with_name(f"{inp.stem}__flattened.csv")
    else:
        out = Path(args.output)

    out.parent.mkdir(parents=True, exist_ok=True)
    flatten_file(inp, out, chunk_size=args.chunk_size, window=args.window)
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
