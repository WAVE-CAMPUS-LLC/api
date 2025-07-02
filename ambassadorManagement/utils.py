import string
import random


def generate_referral_code(length=7):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
