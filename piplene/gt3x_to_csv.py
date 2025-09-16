# pipeline/gt3x_to_csv.py
import pandas as pd
from pygt3x.reader import FileReader

def gt3x_to_df(path: str) -> pd.DataFrame:
    # path must be a filesystem path (not a file-like object)
    with FileReader(path) as reader:
        df = reader.to_pandas()
    if "Timestamp" in df.columns:
        df = df.rename(columns={"Timestamp": "Time"})
    return df[["Time","X","Y","Z"]]

