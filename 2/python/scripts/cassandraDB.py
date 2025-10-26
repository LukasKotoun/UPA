from cassandra.cluster import Cluster
from cassandra import ReadTimeout
from cassandra.query import BatchStatement

import pandas as pd
import os
import sys
from typing import Optional, Sequence
from datetime import datetime
from pathlib import Path

#  data file path
CSV_FILE = os.path.expanduser('/app/datasets/data-vs-orvr.csv')
FLAG_FILE = Path("/app/datasets/.loaded")

#  cassandra connection info
KEYSPACE = "cassandratest"
TABLE = "zaznamy"
HOSTS = ["cassandra"]

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
            PRIMARY KEY ((sluzba), klientID)
        );
    """)


#  data import
def load_csv_to_cassandra(session, file_path: str):
    df = pd.read_csv(file_path, dtype=str, low_memory=False)

    insert_stmt = session.prepare(f"""
        INSERT INTO {TABLE} (
            klientID, typZaznamu, sluzba, cisloListku, prepazka,
            rezervace, casRezervace, propadRezervace, prichod, volani,
            opakovaneVolaniMin, opakovaneVolaniMax, opakovaneVolaniPocet,
            odchod, odchodPoPreposlani, odchodNeprisel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    for start in range(0, len(df), 100):
        batch = BatchStatement()
        for row in df.iloc[start:start + 100].itertuples(index=False):
            batch.add(insert_stmt, (
                safe_int(getattr(row, "klientID", None)),
                safe_int(getattr(row, "typZaznamu", None)),
                safe_int(getattr(row, "sluzba", None)),
                safe_int(getattr(row, "cisloListku", None)),
                safe_int(getattr(row, "prepazka", None)),
                str(getattr(row, "rezervace", None)) if pd.notna(
                    row.rezervace) else None,
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
        session.execute(batch)


# first query ilustrating efecctiveness of cassandra primary key design
def query_sample(session):
    rows = session.execute(f"""SELECT klientid, prepazka, prichod, odchod, rezervace
                                FROM zaznamy
                                WHERE sluzba = 4 LIMIT 20;
                                """)
    print("Prvních 20 záznamů pro službu 4, seřazeno podle klientID (clustering key):")
    print("\nklient   | přepážka |        příchod      |        odchod       | rezervace")
    print("----------------------------------------------------------------------------")
    for r in rows:
        print(f"{r.klientid}  |     {r.prepazka}   | {r.prichod} | {r.odchod} |     {r.rezervace}")
        

# second query illustrating ALLOW FILTERING usage - nonefficient way of querying
def query_sample1(session):
    rows = session.execute(f"""SELECT klientid, prepazka, prichod, odchod, rezervace
                                FROM zaznamy
                                WHERE sluzba = 21 AND klientid > 3617628 and prichod > '2025-10-07 00:00:00' ALLOW FILTERING;
                                """)
    print("\n\nVšechny záznamy pro službu 21 s klientským ID vyšším 3617628 a příchodem po 2025-10-07 00:00:00:")
    print("\nklient   | přepážka |        příchod      |        odchod       | rezervace")
    print("----------------------------------------------------------------------------")
    for r in rows:
        print(f"{r.klientid}  |     {r.prepazka}   | {r.prichod} | {r.odchod} |     {r.rezervace}")

def main(argv: Optional[Sequence[str]] = None) -> int:
    cluster, session = create_cluster()
    create_keyspace(session)
    
    if (len(argv) > 1 and argv[1] == "--load_data"):
        create_table(session)
        load_csv_to_cassandra(session, CSV_FILE)

    query_sample(session)
    query_sample1(session)
    cluster.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
