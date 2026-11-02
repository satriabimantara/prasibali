from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user model.

    Defined before the first migration so AUTH_USER_MODEL never has to be swapped later.
    Session 2 turns it into an email-based account through regular migrations.
    """

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"
