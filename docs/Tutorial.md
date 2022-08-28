## Welcome to the SweepstakeBot tutorial

### How to create a sweepstake

To create sweepstake we will use `/new_sweepstake` command  

For example to create `Test Sweepstake` which will strike at `12156191` ethereum block with the ticket price of `10` points with tickets ranging from `0` to `10000` we will use  
`/new_sweepstake Test Sweepstake 12156191 10 0 10000`

Setting ticket range allows us to control the probability of winning the sweepstake.
If nobody won the sweepstake, sweepstake winning pool will be kept for the next lotteries


### How to view details about the sweepstake

Using this command we can check all info about sweepstake  
`/sweepstake view Test Sweepstake`


### How to buy multiple tickets (whitelisted lottery only, admin only)  

Using this command we can buy multiple tickets for whitelisted lottery (admin only)  
`/sweepstake_admin buy_whitelisted`


### How to replenish sweepstake wallet
To transfer 10 points to the sweepstake wallet we will use this command  
`!send @SweepstakeBot 10`  
So when we check our wallet via `/sweepstake wallet` we will see that we have 10 points available for buying tickets.


### How to buy a ticket
To buy one ticket for the `Test Sweepstake` we will use this command  
`/sweepstake buy Test Sweepstake`  
The ticket price will be deducted from our sweepstake wallet, so when we check via `/sweepstake wallet` we should see that our balance is `0`.



### When we can't buy tickets

- when a sweepstake is close to the strike date (by default 5 hours) we can't buy tickets
- when a sweepstake has ended
- when all tickets were sold
- when sweepstake is of a whitelisted type


### How to view tickets
To view tickets for the `Test Sweepstake,` we can use this command  
`/sweepstake tickets Test Sweepstake`


### How to withdraw points
To withdraw points please use bellow command  
`/sweepstake withdraw`  
This will send all points from your sweepstake balance to your account.
