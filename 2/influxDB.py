from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import pandas as pd

# data file path
CSV_FILE = 'jalud_cidla.csv'

# influx database connection info
DB_URL = "http://localhost:8086"
DB_TOKEN = "ZHSlnEVHUpoyzzq5MGKCZvJQ93-7mxy8Rfnw1Z-_1BeQNJjr7sfd0dqoW4JDqlFUaVtYhPUKZSlMNR4zPANQ6g=="
DB_ORG = "localInfluxText"
DB_BUCKET = "SoundDetectorTest"


def create_influx_client():
    return InfluxDBClient(url=DB_URL, token=DB_TOKEN, org=DB_ORG)

def load_csv(file_path):
    client = create_influx_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    df = pd.read_csv(file_path)
    df.columns = ['id', 'serial_number', 'device_name', 'time', 'ambient_energy', 'max_energy', 'min_energy']
    # influxdb creates schema automatically based on the first write
    for _, row in df.iterrows():
        point = Point("sound_measurement") \
            .tag("serial_number", str(row['serial_number'])) \
            .tag("device_name", row["device_name"]) \
            .field("energy", float(row["ambient_energy"])) \
            .field("max_energy", float(row["max_energy"])) \
            .field("min_energy", float(row["min_energy"])) \
            .time(datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S"), WritePrecision.S)
        write_api.write(bucket=DB_BUCKET, org=DB_ORG, record=point)

    client.close()


def query_data():
    client = create_influx_client()
    query_api = client.query_api()
    query = f'''
    from(bucket: "{DB_BUCKET}")
      |> range(start: 2025-08-31, stop: 2025-09-30)
      |> filter(fn: (r) => r._measurement == "sound_measurement")
      |> filter(fn: (r) => r._field == "energy")
      |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
      |> group(columns: ["device_name"])
      |> keep(columns: ["_time", "_value", "device_name"])
    '''
    tables = query_api.query(query, org=DB_ORG)

    print("Průměrná hodnota energie zvuku za každý den v září roku 2025 podle zařízení:")
    for table in tables:
        for record in table.records:
            date = record.get_time().strftime("%d.%m.%Y")
            print(f"{record['device_name']} | {date}: {record.get_value():.2f}")
            
    client.close()


if __name__ == "__main__":
    load_csv(CSV_FILE)
    query_data()
    pass