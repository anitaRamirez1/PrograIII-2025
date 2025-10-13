from django.db import models

# Create your models here.
class alumno(models.Model):
    codigo = models.CharField(max_length=10)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150)
    telefono = models.CharField(max_length=10)
    email = models.CharField(max_length=75)