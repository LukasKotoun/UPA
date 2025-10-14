# UPA

## Run examples
1. Build the images
```bash
docker compose build
```
2. Start the images
```bash
docker compose up -d
```
3. Open python image shell
```bash
docker exec -it python bash
```
4. Running python scripts
```bash
python scripts/cassandraDB.py # Cassandra
python scripts/influxDB.py    # InfluxDB
python scripts/mongoDB.py     # MongoDB
python scripts/neo4jDB.py     # Neo4jDB
```
