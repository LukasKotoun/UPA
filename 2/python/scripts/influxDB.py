from influxdb_client import InfluxDBClient, Point, WritePrecision, BucketsApi
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import pandas as pd
import sys
from typing import Optional, Sequence

# data file path
CSV_FILE = '/app/datasets/jalud-cidla.csv'

# influx database connection info
DB_URL = "http://influxdb:8086"
DB_TOKEN = "my-token"
DB_ORG = "localInfluxTest"
DB_BUCKET = "SoundDetectorTest"


def create_influx_client():
    return InfluxDBClient(url=DB_URL, token=DB_TOKEN, org=DB_ORG)


def create_bucket():
    client = create_influx_client()
    buckets_api = BucketsApi(client)
    bucket = buckets_api.find_bucket_by_name(DB_BUCKET)
    if not bucket:
        buckets_api.create_bucket(bucket_name=DB_BUCKET, org=DB_ORG)

    client.close()


def clean_bucket():
    client = create_influx_client()
    buckets_api = BucketsApi(client)
    bucket = buckets_api.find_bucket_by_name(DB_BUCKET)
    if bucket:
        buckets_api.delete_bucket(bucket)
        buckets_api.create_bucket(bucket_name=DB_BUCKET, org=DB_ORG)
    client.close()


def load_csv(file_path: str):
    client = create_influx_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)

    df = pd.read_csv(file_path)
    df.columns = ['id', 'serial_number', 'device_name',
                  'time', 'ambient_energy', 'max_energy', 'min_energy']
    
    # influxdb creates schema automatically based on the first write
    points = [
        Point("sound_measurement")
        .tag("serial_number", str(row.serial_number))
        .tag("device_name", row.device_name)
        .field("energy", float(row.ambient_energy))
        .field("max_energy", float(row.max_energy))
        .field("min_energy", float(row.min_energy))
        .time(datetime.strptime(row.time, "%Y-%m-%d %H:%M:%S"), WritePrecision.S)
        for row in df.itertuples(index=False)
    ]
    
    write_api.write(bucket=DB_BUCKET, org=DB_ORG, record=points)

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

    # InfluxDB engine analyzuje dotaz a zjistí který bucket a jaký časový rozsah je potřeba.
    # Podle časového rozsahu a bucketu zjistí které uzly obsahují potřebná data => zjistí které TSM soubory jsou potřeba.
    # V clusterové architektuře vybrané uzly načtou lokálně data ze svých shardů, aplikují filtry a provádějí agregace a seskupení, částečné výsledky se poté sloučí.
    # Řídící uzel serializuje finální tabulku obsahující jen požadované sloupce a doručí ji klientovi přes HTTP(S) rozhraní.
    # Aplikace obdrží data deserializovaná do tabulek a iteruje přes záznamy v tabulkách.
    tables = query_api.query(query, org=DB_ORG)

    print("Průměrná hodnota energie zvuku za každý den v září roku 2025 podle zařízení:")
    for table in tables:
        for record in table.records:
            date = record.get_time().strftime("%d.%m.%Y")
            print(
                f"{record['device_name']} | {date}: {record.get_value():.2f}")

    client.close()

def main(argv: Optional[Sequence[str]] = None) -> int:
    create_bucket()
    
    if (len(argv) > 1 and argv[0] == "--load_data"):
        clean_bucket()
        load_csv(CSV_FILE)

    query_data()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


