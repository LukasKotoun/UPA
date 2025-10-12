from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import json

# data file path
GEOJSON_FILE = 'mysliveckehonitby.geojson'

# mongo database connection info
MONGO_URI = "mongodb://admin:admin@localhost:27017/"
DB_NAME = "upa_test"
COLLECTION_NAME = "hunting"


def create_mongo_connection():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        # Clear existing data and create geospatial index for geometry field
        collection.delete_many({})
        collection.create_index([("geometry", "2dsphere")])
        return client, db, collection
    except ConnectionFailure:
        print("Server not available")
        return None, None, None


def load_geojson(file_path, collection):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if 'features' in data:
            collection.insert_many(data['features'])
        else:
            print("Invalid GeoJSON format: 'features' key not found.")


def query_data(collection):
    point = {"type": "Point", "coordinates": [13.28946164, 49.76122593]}

    # MongoDB analyzuje dotaz a zkontroluje, zda existují relevantní shardy nebo indexy => v tomto konkrétním případě existuje 2dsphere index.
    # Příslušné shard uzly nebo collection partitions vyberou dokumenty, které splňují podmínku v $geoIntersects. filtrování probíhá lokálně na každém uzlu.
    # Výsledky z uzlů jsou seskupeny a odeslány na řídící server, který je serializuje a doručí klientovi. Ten pak iteruje přes dokumenty které splňují podmínku a může je dále zpracovávat.
    results = collection.find({
        "geometry": {
            "$geoIntersects": {
                "$geometry": point
            }
        }
    })
    print("Honitby obsahující bod [13.28946164, 49.76122593]:")
    for r in results:
        print("Název: ", r["properties"]["NAZEV"], "HA: ", r["properties"]
              ["VYMERA_HA"] if "VYMERA_HA" in r["properties"] else "N/A")


if __name__ == "__main__":
    client, db, collection = create_mongo_connection()
    if (client is None or db is None or collection is None):
        print("Failed to connect to the database.")
        exit(1)

    load_geojson(GEOJSON_FILE, collection)
    query_data(collection)
    client.close()
    pass
