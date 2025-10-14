from dataclasses import dataclass
from neo4j import GraphDatabase
import csv
import pandas as pd
from pathlib import Path

URI = "bolt://neo4j:7687"
DRIVER = GraphDatabase.driver(URI, auth=("neo4j", "adminadmin"))
DATA_FOLDER=Path("/app/datasets/gtfs")


def clear_db(session):
    session.run("MATCH (n) DETACH DELETE n;")


def insert_stop(session, stop_id: int, stop_name: str):
    cmd = f"CREATE (s:Stop {{stop_id: {stop_id}, stop_name: '{stop_name}'}})"
    session.run(cmd)


def insert_next_stop(session, from_stop: int, to_stop: int):
    cmd = f"""
        MATCH (s1:Stop {{stop_id: {from_stop}}})
        MATCH (s2:Stop {{stop_id: {to_stop}}})
        MERGE (s1)-[:NEXT_STOP]->(s2)
        """
    session.run(cmd)  


def insert_transfer(session, from_stop: int, to_stop: int):
    cmd = f"""
        MATCH (s1:Stop {{stop_id: {from_stop}}})
        MATCH (s2:Stop {{stop_id: {to_stop}}})
        MERGE (s1)-[:TRANFER]->(s2) 
    """



with DRIVER.session() as session:
    clear_db(session)
    
    with open(DATA_FOLDER/"stops.txt", "r", encoding='utf-8-sig') as f:
        csv_reader = csv.DictReader(f)
        for line in csv_reader:
            stop_id, stop_name = int(line["stop_id"]), line["stop_name"]
            insert_stop(session, stop_id, stop_name)
    
    # with open("gtfs/transfers.txt", "r", encoding='utf-8-sig') as f:
    #     csv_reader = csv.DictReader(f)
    #     for line in csv_reader:
    #         from_stop, to_stop = int(line["from_stop_id"]), int(line["to_stop_id"])
    #         insert_transfer(session, from_stop, to_stop)
    
    df = pd.read_csv(DATA_FOLDER/"stop_times.txt")
    df.columns = ["trip_id","arrival_time","departure_time","stop_id","stop_sequence","pickup_type","drop_off_type","original_stop_id"]

    for trip in df.groupby("trip_id")["stop_id"].apply(list).reset_index().stop_id.values:
        for from_stop, to_stop in zip(trip, trip[1:]):
            insert_next_stop(session, from_stop, to_stop)

    

