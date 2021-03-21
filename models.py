from tortoise import fields
from tortoise.models import Model


class Lottery(Model):
    """Lottery table"""

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    ticket_price = fields.data.DecimalField(max_digits=15, decimal_places=2, default=10)
    strike_date_eta = fields.data.DatetimeField(null=True)
    strike_eth_block = fields.IntField()
    winners = fields.JSONField(null=True)
    is_finished = fields.BooleanField(default=False)
    has_winners_been_paid = fields.BooleanField(default=False)

    def __str__(self):
        return self.name


class Ticket(Model):
    """Ticket table"""

    id = fields.UUIDField(pk=True)
    user_id = fields.IntField()
    ticket_number = fields.IntField()
    lottery_id = fields.ForeignKeyField("models.Lottery", related_name="tickets")

    def __str__(self):
        return f"#{self.id} ({self.ticket_number})"

    class Meta:
        unique_together = ("ticket_number", "lottery_id")
