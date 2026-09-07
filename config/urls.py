from django.contrib import admin
from django.urls import include, path

from links import views as link_views
from tenants import views as tenant_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", tenant_views.home, name="home"),
    path("app/<slug:tenant_slug>/", link_views.link_list, name="link_list"),
    path("app/<slug:tenant_slug>/new/", link_views.link_create, name="link_create"),
    path("app/<slug:tenant_slug>/<str:code>/stats/", link_views.link_stats, name="link_stats"),
    path("app/<slug:tenant_slug>/<str:code>/delete/", link_views.link_delete, name="link_delete"),
    # Public redirect. Last, so it never shadows a dashboard route.
    path("<slug:tenant_slug>/<str:code>", link_views.follow_link, name="follow_link"),
    path("<slug:tenant_slug>/<str:code>/", link_views.follow_link),
]
