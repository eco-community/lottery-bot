from tortoise.validators import Validator
from tortoise.exceptions import ValidationError


class PositiveValueValidator(Validator):
    def __call__(self, value: int):
        if value < 0:
            raise ValidationError("Ensure this value is greater than or equal to 0.")
