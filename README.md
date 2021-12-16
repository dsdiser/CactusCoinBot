# CactusCoin
Discord Currency Bot with support for various bets and support for graphing various statistics for user's wallets. This bot stores wallet amounts in a server role to make it easy for a user to see their wallet amount at a glance.

## Installation
Install the latest version of miniconda [here](https://docs.conda.io/en/latest/miniconda.html).
Use this command in the directory to create your environment and install packages (note: you may need to add conda-forge as a source in order to install all packages):

```commandline
conda env create -f environment.yml
```

or to update existing install:

```commandline
conda env update -f environment.yml --prune
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
