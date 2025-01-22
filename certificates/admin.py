from django.contrib import admin
from .models import EmailNameData, Certificate, Coordinate

@admin.register(EmailNameData)
class EmailNameDataAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')  # Display these fields in the admin list view
    search_fields = ('name', 'email')  # Enable search functionality

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_at')  # Show ID and upload timestamp
    readonly_fields = ('uploaded_at',)  # Make uploaded_at read-only
    list_filter = ('uploaded_at',)  # Add a filter for the uploaded_at field

    def file_preview(self, obj):
        return f"Binary File - {len(obj.file)} bytes"

    file_preview.short_description = "File Size"

@admin.register(Coordinate)
class CoordinateAdmin(admin.ModelAdmin):
    list_display = ('x', 'y', 'certificate','font_size','font_color')  # Show coordinates and related certificate
    list_filter = ('certificate',)  # Enable filtering by certificate
    search_fields = ('certificate__id',)  # Enable searching by certificate ID


