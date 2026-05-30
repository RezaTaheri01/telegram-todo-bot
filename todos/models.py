from django.db import models

class Todo(models.Model):
    telegram_user_id = models.BigIntegerField()
    text = models.TextField()
    completed = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text
