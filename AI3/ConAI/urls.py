from django.urls import path
from . import views

from django.conf import settings
from django.conf.urls.static import static

app_name = 'ConAI'

urlpatterns = [
    path('', views.home, name='home'),

    path('upload_file/', views.upload_file, name='upload_file'),
    path('delete_file/<int:id>', views.delete_file, name ='delete_file'),
    path('select_file/<int:id>', views.select_file, name ='select_file'),

    #path('ai_converse', views.ai_converse, name ='ai_converse'),
    path('clear_session/', views.clear_session, name='clear_session'),

    path('chat_hsitory/', views.chat_hsitory, name='chat_hsitory'),
    path('clear_chat_history/', views.clear_chat_history, name='clear_chat_history'),
]

urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)