from django.db import models

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

from django.core.files.storage import FileSystemStorage
from django.core.validators import RegexValidator


def validate_phone():
    return RegexValidator(r"^\+?(38)?0(44|67|68|96|97|98|50|66|95|99|63|73|93|89|94)\d{7}$",
                          'Enter correct number'
                          )


class AddressBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    phone = models.CharField(max_length=200, validators=[validate_phone()])
    email = models.EmailField(blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)


class NoteBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    tags = ArrayField(models.CharField(max_length=200), blank=True)
    date_added = models.DateTimeField(auto_now_add=True)


fs = FileSystemStorage(location='/media')
class GetListFile(models.Model):
    files = models.ImageField(storage=fs)
