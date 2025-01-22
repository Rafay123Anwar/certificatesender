# certificates/urls.py
from django.urls import path
from . import views
from django.shortcuts import render, redirect

urlpatterns = [
    path('', views.upload_email_file, name='upload_email_file'),
    path('upload-certificate/', views.upload_certificate, name='upload_certificate'),
    path('set-coordinates/', views.set_coordinates, name='set_coordinates'),
    path('send-emails/', views.send_emails, name='send_emails'),
    # path('success/', lambda request: render(request, 'success.html'), name='success'),
    path('success/', views.success_view, name='success'),

]
