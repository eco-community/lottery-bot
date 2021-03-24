from tortoise import fields
from tortoise.models import Model

from app.constants import LotteryStatus
from app.validators import PositiveValueValidator


class User(Model):
    """User table"""

    id = fields.BigIntField(pk=True)  # same as https://discordpy.readthedocs.io/en/latest/api.html#discord.User.id
    balance = fields.data.DecimalField(
        max_digits=15, decimal_places=2, default=0, validators=[PositiveValueValidator()]
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    lotteries: fields.ReverseRelation["Lottery"]
    tickets: fields.ReverseRelation["Ticket"]

    def __str__(self):
        return f"#{self.id}"


class Lottery(Model):
    """Lottery table"""

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    ticket_price = fields.data.DecimalField(max_digits=15, decimal_places=2, default=10)
    strike_date_eta = fields.data.DatetimeField()
    strike_eth_block = fields.IntField()
    winners = fields.JSONField(null=True)
    status = fields.CharEnumField(
        enum_type=LotteryStatus,
        default=LotteryStatus.STARTED,
    )
    participants = fields.ManyToManyField("app.User", related_name="lotteries", through="ticket")
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return self.name


class Ticket(Model):
    """Many to many relationship between user and lottery"""

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("app.User", related_name="tickets")
    lottery = fields.ForeignKeyField("app.Lottery", related_name="tickets")
    ticket_number = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    lotteries: fields.ReverseRelation["Lottery"]

    def __str__(self):
        return f"#{self.id} ({self.ticket_number})"

    class Meta:
        unique_together = ("ticket_number", "lottery")
