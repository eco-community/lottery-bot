## Welcome to the LotteryBot tutorial

### How to get help

`/lottery help`

### How to create a lottery

To create lottery we will use `/new_lottery` command  

For example to create `Test Lottery` which will strike at `12156191` ethereum block with the ticket price of `10` eco points with tickets ranging from `0` to `10000` we will use  
`/new_lottery Test Lottery 12156191 10 0 10000`

Setting ticket range allows us to control the probability of winning the lottery.
If nobody won the lottery, lottery winning pool will be kept for the next lotteries


### How to view details about the lottery

Using this command we can check all info about lottery  
`/lottery view Test Lottery`


### How to replenish lottery wallet
To transfer 10 eco points to the lottery wallet we will use this command  
`!send @LotteryBot 10`  
So when we check our wallet via `/lottery wallet` we will see that we have 10 eco points available for buying tickets.


### How to buy a ticket
To buy one ticket for the `Test Lottery` we will use this command  
`/lottery buy Test Lottery`  
The ticket price will be deducted from our lottery wallet, so when we check via `/lottery wallet` we should see that our balance is `0`.



### When we can't buy tickets

- when a lottery is close to the strike date (by default 5 hours) we can't buy tickets
- when a lottery has ended
- when all tickets were sold


### How to view tickets
To view tickets for the `Test Lottery,` we can use this command  
`/lottery tickets Test Lottery`


### How to withdraw eco points
To withdraw eco points please use bellow command  
`/lottery withdraw`  
This will send all points from your lottery balance to your account.
