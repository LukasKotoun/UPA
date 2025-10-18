# Data import and query examples
This README contains a guide on how to run scripts which import data to databases MongoDB, InfluxDB, Cassandra, Neo4jDB from
the according datasets and run examples queries.

## How to run examples
#### 1. Build the images
```bash
docker compose build
```
#### 2. Start the images
```bash
docker compose up -d
```
#### 3. Open python image shell
```bash
docker exec -it python bash
```

#### 4. Running examples

- **Cassandra**
```bash
# 1) Initial run to load data
# Warning: initial data import is time-consuming
python scripts/cassandraDB.py --load_data
# 2) Run only test queries
python scripts/cassandraDB.py
```

- **InfluxDB**
```bash
# 1) Initial run to load data
python scripts/influxDB.py --load_data
# 2) Run only test queries
python scripts/influxDB.py
```

- **MongoDB**
```bash
# 1) Initial run to load data
python scripts/mongoDB.py --load_data
# 2) Run only test queries
python scripts/mongoDB.py
```

- **Neo4jDB**
```bash
# 1) Initial run to load data
# Warning: initial data import is time-consuming
python scripts/neo4j.py --load_data
# 2) Run only test queries
python scripts/neo4j.py
```

