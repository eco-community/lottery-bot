# SweepstakeBot

A bot that can create sweepstakes with verifiable randomness, using Points issued by [The Accountant](https://github.com/eco/discord-accountant) bot.

**For more on this bot and all the rest of the Eco Community bots, check out [this post](https://echo.mirror.xyz/GlFuqSbTZOLDl0LA7eDa0Yibhqq6IHNUC48nd3WJZQw).**


## How to use
[Check tutorial](docs/Tutorial.md)


## How verifiable randomness works
- users know beforehand at which Ethereum block the sweepstake will be played
- sweepstake uses block hash of the future block as a seed for randomness
- users can manually verify winning tickets via `select_winning_tickets` function from [app.utils module](app/utils.py)


## How sweepstake works
- users buy tickets with random numbers (range of numbers could be set on a per sweepstake basis, thus we can control the probability of winning a sweepstake)
- users know beforehand at which Ethereum block the sweepstake will be played
- when the required block is in blockchain and has at least 12 confirmations winning numbers will be selected
- if a user has a ticket with the winning number he is considered the winner
- if nobody won the sweepstake, sweepstake winning pool will be kept for the next lotteries
- then if someone wins the sweepstake he will get the sweepstake winning pool and old winning pool from previous lotteries without winners


## How wallet works
- users can replenish their wallet via The Accountant bot `!send` command
- users can withdraw from their wallet and points will be send to them via The Accountant bot `!send` command
- users can buy sweepstake tickets using balance from their wallet (aka sweepstake wallet)


## Installation
1. [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
2. Copy and update settings in `.env.example`
3. Execute `docker-compose up -d`
4. Install requirements from `requirements.txt` for `>= Python 3.8`
5. Copy and update settings in `config.example.py`
6. Init database tables via `aerich upgrade`
7. Start bot via `python bot.py` or [via supervisord](http://supervisord.org/) or [systemd](https://es.wikipedia.org/wiki/Systemd)
8. Add a bot to the server with at least `2147829824` scope and `applications.commands` permissions
9. You will need to change how bot applies balance when user sends points in [WalletCog.on_raw_reaction_add](app/extensions/wallet.py)
