from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def holaMundo(request):
    return HttpResponse("hola mundo")

def miEdad(request, edad):
    return HttpResponse(f"Tengo {edad} años, esta edad es la mas genial")

def saludoNombre(request, nombre):
    return HttpResponse(f"Hola {nombre}, bienvenido a la UGB")

def index(request, nombre='invitado', edad=0):
    return render(request, 'index.html', {'nombre': nombre, 'edad': edad})
