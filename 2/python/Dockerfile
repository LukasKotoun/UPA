FROM python:3.11-slim

RUN pip install --no-cache-dir cassandra-driver pymongo neo4j influxdb-client pandas
RUN apt-get update && apt-get install -y gcc g++ curl unzip wget && rm -rf /var/lib/apt/lists/*

COPY ./scripts /app/scripts
RUN mkdir -p /app/datasets
# Cassandra dataset
RUN curl https://onlinedata.plzen.eu/data-vs-orvr.php -o /app/datasets/data-vs-arvr.csv
# Neo4j dataset
RUN curl https://jizdnirady.pmdp.cz/jr/gtfs -o /tmp/gtfs.zip && \
    unzip /tmp/gtfs.zip -d /app/datasets/gtfs && \
    rm /tmp/gtfs.zip
# InfluxDB dataset
RUN curl https://opendata.plzen.eu/public/opendata/jalud-sensor-data/2490631311115202204 -o /app/datasets/jalud-cidla.csv 
# MongoDB dataset
RUN wget "https://opendata.plzen.eu/public/opendata/download-file/271" -O /tmp/honitby.zip && \
    unzip /tmp/honitby.zip -d /app/datasets && \
    rm /tmp/honitby.zip 


WORKDIR /app
CMD ["bash"]