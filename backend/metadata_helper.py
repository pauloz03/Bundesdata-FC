import pyarrow.parquet as pq
import s3fs
import os

fs = s3fs.S3FileSystem(
    key=os.environ["AWS_ACCESS_KEY_ID"],
    secret=os.environ["AWS_SECRET_ACCESS_KEY"],
    token=os.environ.get("AWS_SESSION_TOKEN")
)

files = {
    "bayern_hamburg":      "s3://hackathon-data-127393434859/Challenge 2 – Unlock the Power of 3D Football Data/Match_Data/Bayern_Hamburg/FCB-HSV.parquet",
    "dortmund_stuttgart":  "s3://hackathon-data-127393434859/Challenge 2 – Unlock the Power of 3D Football Data/Match_Data/Dortmund_Stuttgart/BVB-VFB.parquet",
    "frankfurt_bayern":    "s3://hackathon-data-127393434859/Challenge 2 – Unlock the Power of 3D Football Data/Match_Data/Frankfurt_Bayern/SGE-FCB.parquet",
    "frankfurt_union":     "s3://hackathon-data-127393434859/Challenge 2 – Unlock the Power of 3D Football Data/Match_Data/Frankfurt_Union/SGE-FCU.parquet",
}

for match_id, path in files.items():
    with fs.open(path, "rb") as f:
        meta = pq.ParquetFile(f).metadata.metadata
    print(f"\n{match_id}:")
    for key in [b"phase_1_start", b"phase_1_end", b"phase_2_start", b"phase_2_end", b"framerate", b"home_team_id", b"away_team_id"]:
        print(f"  {key.decode()}: {meta.get(key, b'N/A').decode()}")