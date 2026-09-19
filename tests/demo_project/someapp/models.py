from django.db import models


class Category(models.Model):
    title = models.CharField(max_length=100)


class Event(models.Model):
    title = models.CharField(max_length=100)
    category = models.OneToOneField(
        Category, null=True, blank=True, on_delete=models.SET_NULL
    )
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.title


class Client(models.Model):
    key = models.CharField(max_length=20, unique=True)


class ForeignObjectTarget(models.Model):
    pass


class ForeignObjectSource(models.Model):
    # For issue #1530: a plain ForeignObject's reverse relation is a bare ForeignObjectRel.
    target_id = models.IntegerField()
    target = models.ForeignObject(
        ForeignObjectTarget,
        on_delete=models.CASCADE,
        from_fields=["target_id"],
        to_fields=["id"],
        related_name="sources",
    )
