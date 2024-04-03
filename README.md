# Cactus Coin Bot
Discord Currency Bot with support for various bets and support for graphing various statistics for user's wallets. This bot stores wallet amounts in a server role to make it easy for a user to see their wallet amount at a glance.

## Installation

### PIP

Install python version >= 3.11 and run the following:
```commandline
python -m pip install -r requirements.txt
```


## Commands
This section is unfinished.

## Deployment
Secrets are currently stored in config.yml, and should contain the following fields:

* channelName - The channel's name that is used for commands to the bot.
* dbFile - Path for file system to host SQLite database.
* token - Bot token for Discord API access.
* defaultCoin - The default starting amount of coin for each user after initializing their wallet.
* debtLimit - The maximum amount of coin a user can go into debt.
* rolePrefix - The prefix for the role given to each user with their wallet amount. 
* logLevel - Optional parameter for a specific logging level for the application.
* rolePrefix - A prefix for the role denoting how much coin a user has

An example config file is contained in default.config.yml

Start the bot using the following command while in the main directory:
```commandline
python -m src.main
```

Alternatively you can use the sample service file and install it using:
```commandline
sudo cp cactuscoinbot.service /lib/systemd/system/
sudo chmod 644 /lib/systemd/system/cactuscoinbot.service
sudo systemctl daemon-reload
sudo systemctl enable cactuscoinbot
sudo systemctl start cactuscoinbot
```
