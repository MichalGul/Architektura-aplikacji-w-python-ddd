"""Konfiguracja URL django_project

Lista urlpatterns odwzorowuje adresy URL na widoki. Więcej informacji:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Przykłady:
Widoki funkcji
    1. Dodanie importu:  from my_app import views
    2. Dodanie URL do urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Dodanie importu:  from other_app.views import Home
    2. Dodanie URL do urlpatterns:  path('', Home.as_view(), name='home')
Dodawanie kolejnego URLconf
    1. Import funkcji include() function: from django.urls import include, path
    2. Dodanie URL do urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from alloc import views

urlpatterns = [
    path('add_batch', views.add_batch),
    path('allocate', views.allocate),
]
