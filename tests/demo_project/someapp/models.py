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
