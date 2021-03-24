from enum import Enum


class LotteryStatus(str, Enum):
    STARTED = "started"  # lottery started
    STOP_SALES = "stop_sales"  # when lottery is close to strike date stop selling tickets
    STRIKED = "striked"  # winners were selected
    ENDED = "ended"  # lottery ended, winners were paid
