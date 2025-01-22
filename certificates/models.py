
from django.db import models

class EmailNameData(models.Model):
    session_id = models.CharField(max_length=255)  # Unique session identifier
    name = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self):
        return f"{self.name} <{self.email}>"

class Certificate(models.Model):
    session_id = models.CharField(max_length=255)  # Unique session identifier
    file = models.BinaryField()  # To store file in the database
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Coordinate(models.Model):
    session_id = models.CharField(max_length=255)  # Unique session identifier
    x = models.FloatField()
    y = models.FloatField()
    font_size = models.PositiveIntegerField(default=20)
    font_color = models.CharField(max_length=7, default="#000000")
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='coordinates')


