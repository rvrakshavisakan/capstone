from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name='home'),

    path('loading/', views.loading, name='loading'),

    path(
        'analysis-status/',
        views.analysis_status_view,
        name='analysis_status'
    ),

    path('results/', views.results, name='results'),

]