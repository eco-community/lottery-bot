from enum import Enum


class LotteryStatus(str, Enum):
    STARTED = "started"  # lottery started
    STOP_SALES = "stop_sales"  # when lottery is close to strike date stop selling tickets
    STRIKED = "striked"  # winning tickets were selected
    ENDED = "ended"  # lottery ended, winners were paid


STOP_SALES_BEFORE_START_IN_SEC = 60 * 60 * 2  # in seconds
BLOCK_CONFIRMATIONS = 12  # number of block confirmations after which block will be considered as canonical
DELETE_AFTER = 60 * 10  # the number of seconds to wait in the background before deleting the message

GREEN = 0x03D692
GOLD = 0xF1C40F
