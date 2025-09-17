# pipeline/flatten.py
import pandas as pd

def flatten_xyz(df: pd.DataFrame, seq_len: int = 30, time_col: str = "Time") -> pd.DataFrame:
    # make sure required columns exist
    cols = [c for c in ["X","Y","Z", time_col, time_col.lower()] if c in df.columns]
    d = df[cols].copy()
    if time_col not in d.columns and time_col.lower() in d.columns:
        d = d.rename(columns={time_col.lower(): time_col})

    rows_to_keep = (len(d) // seq_len) * seq_len
    d = d.iloc[:rows_to_keep]

    out_rows = []
    for i in range(0, len(d), seq_len):
        block = d.iloc[i:i+seq_len]
        row = {f'x_{j+1}': block["X"].values[j] for j in range(seq_len)}
        row |= {f'y_{j+1}': block["Y"].values[j] for j in range(seq_len)}
        row |= {f'z_{j+1}': block["Z"].values[j] for j in range(seq_len)}
        row[time_col] = block[time_col].iloc[0]
        out_rows.append(row)
    return pd.DataFrame(out_rows)

