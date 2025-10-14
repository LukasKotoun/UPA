from cassandra.cluster import Cluster
from cassandra import ReadTimeout
import pandas as pd
import os
from datetime import datetime

#  data file path
CSV_FILE = os.path.expanduser('/app/datasets/data-vs-orvr.csv')

#  cassandra connection info
KEYSPACE = "vsorvr"
TABLE = "zaznamy"
HOSTS = ["127.0.0.1"]
USERNAME = "cassandra"
PASSWORD = "cassandra"

#  db setup
def create_cluster():
    cluster = Cluster(HOSTS)
    session = cluster.connect()
    return cluster, session


def create_keyspace(session):
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{ 'class': 'SimpleStrategy', 'replication_factor': '1' }}
    """)
    session.set_keyspace(KEYSPACE)


def safe_int(val):
    try:
        if pd.isna(val):
            return None
        return int(val)
    except ValueError:
        return None


def safe_timestamp(val):
    if pd.isna(val) or val == "":
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

# create db schema
# partition key (klientID), clustering columns (sluzba)
def create_table(session):
    session.execute(f"DROP TABLE IF EXISTS {TABLE};") 
    session.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            klientID int,
            casRezervace timestamp,
            cisloListku int,
            typZaznamu int,
            sluzba int,
            prepazka int,
            rezervace text,
            propadRezervace timestamp,
            prichod timestamp,
            volani timestamp,
            opakovaneVolaniMin timestamp,
            opakovaneVolaniMax timestamp,
            opakovaneVolaniPocet int,
            odchod timestamp,
            odchodPoPreposlani timestamp,
            odchodNeprisel timestamp,
            PRIMARY KEY ((klientID), sluzba)
        );
    """)


#  data import
def load_csv_to_cassandra(session, file_path):
    df = pd.read_csv(file_path, dtype=str, low_memory=False)


    insert_stmt = session.prepare(f"""
        INSERT INTO {TABLE} (
            klientID, typZaznamu, sluzba, cisloListku, prepazka,
            rezervace, casRezervace, propadRezervace, prichod, volani,
            opakovaneVolaniMin, opakovaneVolaniMax, opakovaneVolaniPocet,
            odchod, odchodPoPreposlani, odchodNeprisel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    print("Inserting data into Cassandra...")
    print('Total records to insert:', len(df))
    count = 0
    for row in df.itertuples(index=False):
        try:
            session.execute(insert_stmt, (
                safe_int(getattr(row, "klientID", None)),
                safe_int(getattr(row, "typZaznamu", None)),
                safe_int(getattr(row, "sluzba", None)),
                safe_int(getattr(row, "cisloListku", None)),
                safe_int(getattr(row, "prepazka", None)),
                str(getattr(row, "rezervace", None)) if pd.notna(row.rezervace) else None,
                safe_timestamp(getattr(row, "casRezervace", None)),
                safe_timestamp(getattr(row, "propadRezervace", None)),
                safe_timestamp(getattr(row, "prichod", None)),
                safe_timestamp(getattr(row, "volani", None)),
                safe_timestamp(getattr(row, "opakovaneVolaniMin", None)),
                safe_timestamp(getattr(row, "opakovaneVolaniMax", None)),
                safe_int(getattr(row, "opakovaneVolaniPocet", None)),
                safe_timestamp(getattr(row, "odchod", None)),
                safe_timestamp(getattr(row, "odchodPoPreposlani", None)),
                safe_timestamp(getattr(row, "odchodNeprisel", None))
            ))
            count += 1

        except Exception as e:
            print("Error inserting row:", e)
            continue
        print(f"Inserted {count}/{len(df)} records", end='\r')

    print(f"Imported {count} records into {TABLE}.")


#  SAMPLE QUERY
def query_sample(session):
    rows = session.execute(f"""SELECT casRezervace, sluzba, prepazka, prichod, odchod
                                FROM zaznamy
                                WHERE klientID = 401574;
                                """)
    print("\nRetrieve all reservations of a specific client (by klientID):")
    for r in rows:
        print(f"sluzba={r.sluzba}, prichod={r.prichod}, odchod={r.odchod}")

def query_sample1(session):
    rows = session.execute(f"SELECT * FROM {TABLE} WHERE sluzba = 1 LIMIT 10 ALLOW FILTERING")
    print("\nSample data:")
    for r in rows:
        print(f"klientID={r.klientid}, prichod={r.prichod}, odchod={r.odchod}")

def main():
    cluster, session = create_cluster()
    create_keyspace(session)
    create_table(session)
    
    load_csv_to_cassandra(session, CSV_FILE)
    query_sample(session)
    query_sample1(session)
    cluster.shutdown()


if __name__ == "__main__":
    main()
