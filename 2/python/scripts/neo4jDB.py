from dataclasses import dataclass
from neo4j import GraphDatabase
import neo4j
import csv
import pandas as pd
from pathlib import Path
from typing import Optional, Sequence
import sys

URI = "bolt://neo4j:7687"
AUTH = ("neo4j", "password123")
DATA_FOLDER=Path("/app/datasets/gtfs")





def initial_db_setup(driver: neo4j.Driver):
    with driver.session() as tx:
        tx.run("MATCH (n) DETACH DELETE n;")
        tx.run("CREATE CONSTRAINT unique_trip_id  IF NOT EXISTS FOR (t:Trip) REQUIRE t.trip_id IS UNIQUE")
        tx.run("CREATE CONSTRAINT unique_stop_id  IF NOT EXISTS FOR (s:Stop) REQUIRE s.stop_id IS UNIQUE")
        tx.run("CREATE CONSTRAINT unique_route_id IF NOT EXISTS FOR (r:Route) REQUIRE r.route_id IS UNIQUE")


def insert_stop(driver: neo4j.Driver, **params):
    with driver.session() as tx:
        tx.run("""
            MERGE (s:Stop { stop_id: $stop_id })
            SET s.stop_code = $stop_code, 
                s.stop_name = $stop_name,
                s.stop_lat = $stop_lat, 
                s.stop_lon = $stop_lon,
                s.zone_id = $zone_id, 
                s.location_type = $location_type,
                s.wheelchair_boarding = $wheelchair_boarding,
                s.original_stop_id = $original_stop_id
        """, **params)


def insert_next_stop(driver: neo4j.Driver, from_stop: str, to_stop: str):
    with driver.session() as tx:
        
        tx.run("""
            MATCH (s1:Stop {stop_id: $from_stop})
            MATCH (s2:Stop {stop_id: $to_stop})
            MERGE (s1)-[:NEXT_STOP]->(s2)
            """,
        from_stop=from_stop,
        to_stop=to_stop)


def insert_stop_on_route(driver: neo4j.Driver, **params):
    with driver.session() as tx:
        tx.run("""
            MATCH (s:Stop {stop_id: $stop_id})
            MATCH (r:Route {route_id: $route_id})
            MERGE (s)-[:STOP_ON_ROUTE {order: $order}]->(r)
            """,
        **params)


def insert_transfer(driver: neo4j.Driver, **params):
    with driver.session() as tx:
        tx.run(
            """
            MATCH (s1:Stop {stop_id: $from_stop_id})
            MATCH (s2:Stop {stop_id: $to_stop_id})
            MERGE (s1)-[:TRANFER]->(s2)
            """,
            **params
        )


def insert_route(driver: neo4j.Driver, **params):
    with driver.session() as tx:
        tx.run("""
            MERGE (r:Route {route_id: $route_id})
            SET 
                 r.agency_id = $agency_id,
                 r.route_short_name = $route_short_name,
                 r.route_long_name = $route_long_name,
                 r.route_type = $route_type,
                 r.dir_1_from = $dir_1_from,
                 r.dir_1_to = $dir_1_to,
                 r.dir_2_from = $dir_2_from,
                 r.dir_2_to = $dir_2_to
        """, **params)


def insert_trip(driver: neo4j.Driver, **params):
    with driver.session() as tx:
        tx.run("""
            MERGE (t:Trip {trip_id:  $trip_id})
            SET t.service_id =  $service_id,
                t.trip_short_name =  $trip_short_name,
                t.direction_id =  $direction_id,
                t.wheelchair_accessible = $wheelchair_accessible
            WITH t
            MATCH (r:Route {route_id: $route_id})
            MERGE (t)-[:TRIP_ON_ROUTE]->(r)
        """, **params)


def find_shortest_paths(driver: neo4j.Driver, start_stop_code: str, destination_stop_code: str):
    with driver.session() as tx:
        results = tx.run("""
        MATCH p = ALL SHORTEST (:Stop {stop_code: $start})-[:NEXT_STOP*]->(:Stop {stop_code: $destination}) RETURN p
        """,
        start = start_stop_code,
        destination = destination_stop_code
        )
        records = list(results)

        if records:
            return [[s.start_node["stop_name"] for s in record["p"].relationships] + [record["p"].relationships[-1].end_node["stop_name"]] for record in records]
        return []

def get_route_stops(driver: neo4j.Driver, route_long_name: str):
    with driver.session() as tx:
        result = tx.run("""
            MATCH (s:Stop)-[e:STOP_ON_ROUTE]->(:Route {route_long_name: $route_long_name}) 
            ORDER BY e.order
            RETURN s.stop_lat, s.stop_lon
        """, route_long_name=route_long_name)
    
        return [str((lat, long)) for [lat, long] in result.values()]


def load_dataset(driver):

    with open(DATA_FOLDER/"routes.txt", "r", encoding='utf-8-sig') as f:
        csv_reader = csv.DictReader(f)
        for record in csv_reader:
            insert_route(driver, **record)

    with open(DATA_FOLDER/"stops.txt", "r", encoding='utf-8-sig') as f:
        csv_reader = csv.DictReader(f)
        for record in csv_reader:
            insert_stop(driver, **record)
    
    with open(DATA_FOLDER/"transfers.txt", "r", encoding='utf-8-sig') as f:
        csv_reader = csv.DictReader(f)
        for record in csv_reader:
            insert_transfer(driver, **record)

    with open(DATA_FOLDER/"trips.txt", "r", encoding='utf-8-sig') as f:
        csv_reader = csv.DictReader(f)
        for record in csv_reader:
            insert_trip(driver, **record)


    # next stop edges
    trips = pd.read_csv(DATA_FOLDER/"trips.txt")
    trips.columns = ["route_id","service_id","trip_id","trip_short_name","direction_id","wheelchair_accessible"]
    route_representants = trips.groupby("route_id")["trip_id"].apply(list).to_dict()
    route_representants = {representants[0]: route_id for (route_id, representants) in route_representants.items()}

    stop_times = pd.read_csv(DATA_FOLDER/"stop_times.txt")
    stop_times.columns = ["trip_id","arrival_time","departure_time","stop_id","stop_sequence","pickup_type","drop_off_type","original_stop_id"]
    stop_sequences = stop_times[stop_times["trip_id"].isin(route_representants.keys())].groupby("trip_id")["stop_id"].apply(list).to_dict()
    stop_sequences = {route_representants[trip_id]: stops for (trip_id, stops) in stop_sequences.items()}

    for route_id, stops in stop_sequences.items():
        for order, stop_id in enumerate(stops, start=1):
            insert_stop_on_route(driver, stop_id=str(stop_id), route_id=str(route_id), order=order)

        for from_stop, to_stop in zip(stops, stops[1:]):
                insert_next_stop(driver, str(from_stop), str(to_stop))

def main(argv: Optional[Sequence[str]] = None) -> int:


    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        try:
            driver.verify_connectivity()
        except Exception as e:
            print(f"Failed to establish connection: {e}", file=sys.stderr)
            return 1


        try:
            if (len(argv) > 1 and argv[1] == "--load_data"):
                initial_db_setup(driver)
                load_dataset(driver)
            
            
            paths = find_shortest_paths(driver, '50733/3', '57135/1')
            print("Found paths:")
            for path in paths:
                print(" -> ".join(path))
            
            print("Route stop GPS coordinates:")
            stops = get_route_stops(driver, "Slovany - Bolevec")
            print(" -> ".join(stops))


        except Exception as e:
            print(f"Query error: {e}", file=sys.stderr)
            return 1


    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
