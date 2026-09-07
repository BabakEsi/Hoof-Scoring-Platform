
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('secure-panel-iClassifier/', admin.site.urls),
    path('accounts/',include('accounts.urls')),
    path('',include('annotation.urls')),
]
