from django.db import models

# Create your models here.

class file_model(models.Model):
    file_detail = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

class conversation_history(models.Model):
    question = models.CharField(max_length=250, default='')
    response = models.TextField()
    created_at =models.DateTimeField(auto_now=True)