from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import json
import sys
from typing import Optional, Sequence

# data file path
GEOJSON_FILE = '/app/datasets/mysliveckehonitby.geojson'

# mongo database connection info
MONGO_URI = "mongodb://admin:admin@mongodb:27017/"
DB_NAME = "upa_test"
COLLECTION_NAME = "hunting"


def create_mongo_connection():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        return client, db, collection
    except ConnectionFailure:
        print("Server not available")
        return None, None, None


def initial_collection_setup(collection):
    # Clear existing data and create geospatial index for geometry field
    collection.delete_many({})
    collection.create_index([("geometry", "2dsphere")])


def load_geojson(file_path: str, collection):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if 'features' in data:
            collection.insert_many(data['features'])
        else:
            print("Invalid GeoJSON format: 'features' key not found.")


def query_data(collection):
    point = {"type": "Point", "coordinates": [13.28946164, 49.76122593]}
    pipeline = [
        {
            "$geoNear": {
                "near": point,
                "distanceField": "distance_m",
                "maxDistance": 5000,
                "spherical": True,
                "query": {}
            }
        },
        {
            "$group": {
                "_id": "$properties.NAZEV",
                "distance_m": {"$first": "$distance_m"},
                "hectars": {"$first": "$properties.VYMERA_HA"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "NAZEV": "$_id",
                "VZDALENOST_KM": {"$round": [{"$divide": ["$distance_m", 1000]}, 3]},
                "VYMERA_KM": {"$divide": ["$hectars", 100]}
            }
        }
    ]

    results = collection.aggregate(pipeline)
    print(f"Honitby do 5 km od bodu: {point['coordinates']}")
    for r in results:
        print("Název: ", r["NAZEV"], "Vzdálenost: ",
              r["VZDALENOST_KM"], "km", "Výmera: ", r["VYMERA_KM"], "km^2")


def main(argv: Optional[Sequence[str]] = None) -> int:
    client, db, collection = create_mongo_connection()
    if (client is None or db is None or collection is None):
        print("Failed to connect to the database.")
        exit(1)

    if (len(argv) > 1 and argv[1] == "--load_data"):
        initial_collection_setup(collection)
        load_geojson(GEOJSON_FILE, collection)

    query_data(collection)
    client.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
