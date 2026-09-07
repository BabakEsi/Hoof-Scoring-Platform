from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .export_excel import export_annotations_excel

app_name = 'annotation'

urlpatterns = [

    path('', views.home, name='home'),
    path("farms/", views.farm_list_view, name="farms"),
    path("annotate/", views.annotate_view, name="annotate"),
    path("cows/<int:cow_id>/",views.cow_detail_view,name="cow_detail"),
    path("create-farm/", views.create_farm, name="create_farm"),
    path("create-cow/", views.create_cow, name="create_cow"),
    path("farm/admin/<int:farm_id>/edit/", views.edit_farm, name="edit_farm"),
    path("farm/admin/<int:farm_id>/delete/", views.delete_farm, name="delete_farm"),
    path("farm/admin/<int:farm_id>/", views.farm_detail_admin, name="farm_detail_admin"),
    path("cow/admin/<int:cow_id>/parts/",views.cow_parts_admin,name="cow_parts_admin"),
    path("cow/admin/<int:cow_id>/parts/<str:code>/",views.part_targets_admin,name="part_targets_admin"), 
    path("cow/admin/<int:cow_id>/targets/<int:target_id>/",views.target_detail_admin,name="target_detail_admin"),
    path("cow/admin/<int:cow_id>/mixed/<int:target_id>/",views.mixed_front_target_detail_admin,name="mixed_front_target_detail_admin",),
    path("upload_dataset/", views.upload_dataset, name="upload_dataset"),
    path("export-excel/",export_annotations_excel,name="export_excel",),
    path(
        "cow/admin/ratings/",
        views.ratings_admin,
        name="ratings_admin"
    ),

    path(
        "ratings/delete/<int:rating_id>/",
        views.delete_rating,
        name="delete_rating"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)