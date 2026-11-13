from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Test bot — boshqaruv"
admin.site.site_title = "Test bot"
admin.site.index_title = "Foydalanuvchilar va testlar"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("quiz.urls")),
]
