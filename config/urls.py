from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("", RedirectView.as_view(url="/api/doc/", permanent=False)),
    path("api/docs/", RedirectView.as_view(url="/api/doc/", permanent=False, query_string=True)),
    path("api/", include("parser_app.urls")),
    path("", include("config.docs.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
