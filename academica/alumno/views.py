from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

# Create your views here.
def holaMundo(request):
    return HttpResponse("hola mundo")

def miEdad(request, edad):
    return HttpResponse(f"Tengo {edad} años, esta edad es la mas genial")

def saludoNombre(request, nombre):
    return HttpResponse(f"Hola {nombre}, bienvenido a la UGB")

def index(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render())
