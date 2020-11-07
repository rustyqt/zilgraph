# Zilgraph - A Zilswap Dashboard
Zilgraph is an open source tool for visualizing Zilswap activity on the Zilliqa blockchain. It provides token OHLC charts - daily and hourly, liquitidy distribution and more.

Zilgraph is launched here:  [Zilgraph](http://zilgraph.ddns.net)

The data is acquired from the zilswap smart contract and stored in a local MongoDB database.

The Zilgraph front-end provides visualized data using bokeh python library.

# Dependencies

The Zilgraph depencies can be install using the following command:

    pip3 install pyzil pymongo urllib3 requests pandas numpy bokeh

# Zilcrawler

The Zilcrawler is a crawler collecting and processing all the data required for the charts presented on Zilgraph. It is interfacing the zilswap smart contract through pyzil API as well as the viewblock API. For the latter we need an API-KEY which can be acquired from viewblock for free after registration. (see https://viewblock.io/api)

Once obtained, the API-KEY need to be stored in your home folder in ~/.viewblock.json with the following format:

    {
        "X-APIKEY": {
            "key"    : "<key_string>",
            "secret" : "<secret_string>"
        }
    }

Finally, you can start the crawler:

    ~/zilgraph/dash$ python3 zilcrawl.py 

# Start Dashboard

The dashboard is described in *main.py* and makes use of the python bokeh library. The default deployment uses port 5006 on your localhost.

For development purpose you can use the bokeh server to launch the website at http://localhost:5006

    ~/zilgraph$ bokeh serve --dev --show dash


For deployment in the production environment it is recommended using an nginx reverse proxy in front of the bokeh server. Start the bokeh server for zilgraph production environment with:

    ~/zilgraph$ bokeh serve --show dash --allow-websocket-origin="zilgraph.ddns.net"


For the nginx config one can use:

    ~$ cat /etc/nginx/sites-enabled/default 
    server {
        listen 80;

        location / {
            proxy_pass http://127.0.0.1:5006;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host:$server_port;
            proxy_buffering off;
        }
    }
