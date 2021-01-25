# Zilgraph - A Zilswap Dashboard
Zilgraph is an open source tool for visualizing Zilswap activity on the Zilliqa blockchain. It provides ZRC-2 token charts, volume, liquitidy distribution and more.

Zilgraph is launched here:  [Zilgraph](https://zilgraph.io)

The Zilliqa blockchain is systematically crawled and all data is stored in elasticsearch. With adequate elasticsearch queries zilswap data is aggregated. This builds the foundation to add more analytics for other smart contracts.

The Zilgraph front-end provides visualized data using bokeh python library and embedded kibana dashboard.

# Dependencies

Add Elasticsearch repository, install and start:

    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
    sudo apt-get install apt-transport-https
    echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-7.x.list
    sudo apt-get update && sudo apt-get install elasticsearch kibana
    sudo service elasticsearch start
    sudo service kibana start
    
Zilgraph package dependencies:

    sudo apt install libgmp-dev mongodb

The Zilgraph python dependencies can be install using the following command:

    pip3 install pyzil pymongo urllib3 requests pandas numpy bokeh elasticsearch

# Zilcrawler

The Zilcrawler is a crawler collecting and processing all the data required for the charts presented on Zilgraph. It is interfacing a Zilliqa seed node. Acquired data is stored in a elasticsearch index. As the crawler is fetching every single transaction ever executed on the Zilliqa blockchain, it is recommended to run a local Zilliqa seed node.

Finally, you can start the crawler:

    ~/zilgraph/zilswap$ python3 crawler.py 

# Start Dashboard

The dashboard is described in *main.py* and makes use of the python bokeh library. The default deployment uses port 5006 on your localhost.

For local development purpose you can use the bokeh server to launch the website at http://localhost:5006

    ~/zilgraph$ bokeh serve --dev --show zilswap


For deployment in the production environment it is recommended using an nginx reverse proxy in front of the bokeh server. Start the bokeh server for zilgraph production environment with:

    ~/zilgraph$ bokeh serve --show zilswap --allow-websocket-origin='zilgraph.io' --dev --use-xheaders


For the nginx config one can use:

    ~/zilgraph$ cp etc/nginx/conf.d/zilgraph.io.conf /etc/nginx/conf.d/zilgraph.io.conf


# Further Work

Community contribution to the project is highly appreciated. If you like to contribute but don't know where to start you could go with one of the open points below.

- [x] Zilswap Dashboard for XSGD, gZIL, BOLT, ZLP and others
- [x] Daily and hourly OHLC charts for all tokens with historic data back to zilswap contract creation
- [x] Current Liquidity distribution and total liquidity
- [x] Current rates and liquidity of the tokens
- [x] Basic zilswap python library (Get current market data, issue ExactZILforToken/TokenForExactZIL smart contract call)
    
- [x] Make Zilgraph viewed better on mobile devices
- [ ] Full-featured python zilswap library
- [ ] Visualization of historic liquidity depth
- [x] Adding trading volume to price chart
- [x] Use local Zilliqa seed node as data provider for the Zilcrawler
- [ ] Visualization of other commonly used Zilliqa smart contracts (e.g. Staking Contract, Unstoppable Domains)
