import csv
import os
import time

class FeatureLogger:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.filename = os.path.join(output_dir, f"features_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        self.file = open(self.filename, 'w', newline='')
        self.writer = csv.writer(self.file)
        self.header = None

    def log(self, timestamp, feature_data):
        # Only log if there is real data
        if not feature_data:
            return
        # Sanity check on timestamp
        if timestamp < 1e9:
            timestamp = time.time()   # fix obviously wrong timestamps

        if self.header is None:
            # Build header from the first feature dict's keys
            first_key = list(feature_data.keys())[0]
            keys = list(feature_data[first_key].keys())
            self.header = ['timestamp']
            for name in feature_data.keys():
                for k in keys:
                    self.header.append(f"{name}_{k}")
            self.writer.writerow(self.header)

        row = [timestamp]
        for name in self.header[1:]:   # skip 'timestamp'
            # name is like "torso_pelvis_torsion_value"
            feature_name, field = name.rsplit('_', 1)
            row.append(feature_data.get(feature_name, {}).get(field, 0.0))
        self.writer.writerow(row)
        self.file.flush()

    def close(self):
        self.file.close()