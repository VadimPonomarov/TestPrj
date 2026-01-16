from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("api/", include("parser_app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
