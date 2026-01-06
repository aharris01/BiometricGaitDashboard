import csv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
data_path = "..\..\data"
for file in list(Path(data_path).rglob('metadata.csv')):
    try:
        with file.open(newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except:
        print(f"{file}: Error occurred while opening file")
        continue
    box_sizes = []
    box_sizes_sum = 0
    for row in rows:
        try:
            x_min = int(float(row["XMin"]))
            x_max = int(float(row["XMax"]))
            y_min = int(float(row["YMin"]))
            y_max = int(float(row["YMax"]))
        except:
            print("Missing data, skipping this footstep...")
            continue
        bounding_box_size = abs(x_max - x_min) * abs(y_max - y_min)
        box_sizes.append(bounding_box_size)
        box_sizes_sum += bounding_box_size
    avg_box_size = box_sizes_sum / len(box_sizes)
    footstep_count = len(box_sizes)
    print(f"{file}: {int(avg_box_size)}, {footstep_count}")

