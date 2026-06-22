import csv
import os
import time


class FeatureLogger:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.filename = os.path.join(
            output_dir, f"features_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        self.file = open(self.filename, "w", newline="")
        self.writer = csv.writer(self.file)
        self.header = None

    def log(self, timestamp, feature_data, extra=None):
        if not feature_data and not extra:
            return
        if timestamp < 1e9:
            timestamp = time.time()

        flat = {}
        for fname, fdict in feature_data.items():
            for key, val in fdict.items():
                flat[f"{fname}_{key}"] = val
        if extra:
            flat.update(extra)

        if self.header is None:
            self.header = ["timestamp"] + sorted(flat.keys())
            self.writer.writerow(self.header)

        row = [timestamp] + [flat.get(col, "") for col in self.header[1:]]
        self.writer.writerow(row)
        self.file.flush()

    def close(self):
        self.file.close()
