import os
import glob
import pandas as pd

path = "./data/"

all_files = glob.glob(os.path.join(path, "20*.csv"))
df_from_each_file = (pd.read_csv(f, sep=',') for f in all_files)
df_merged = pd.concat(df_from_each_file, ignore_index=True).replace("-", "")
df_merged.drop_duplicates().to_csv("merged.csv", index=False)

atp_df = df_merged.loc[df_merged["tour"] == "atp"]
atp_df.drop_duplicates().to_csv("atp.csv", index=False)

wta_df = df_merged.loc[df_merged["tour"] == "wta"]
wta_df.drop_duplicates().to_csv("wta.csv", index=False)
