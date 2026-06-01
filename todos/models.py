from django.db import models


class TodoList(models.Model):
    telegram_user_id = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=255)

    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"List {self.pk}"


class Todo(models.Model):
    todo_list = models.ForeignKey(
        TodoList,
        on_delete=models.CASCADE,
        related_name="todos",
    )

    text = models.TextField()

    completed = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["completed", "created_at"]

    def __str__(self):
        return self.text[:50]
