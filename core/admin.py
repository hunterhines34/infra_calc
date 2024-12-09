from django.contrib import admin
from .models import (
    Manufacturer, CPUModel, RAMModel, StorageModel,
    GPUModel, NetworkCardModel, License
)

@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)

@admin.register(CPUModel)
class CPUModelAdmin(admin.ModelAdmin):
    list_display = ('manufacturer', 'model_name', 'cores', 'threads', 'base_clock', 'price')
    list_filter = ('manufacturer', 'socket')
    search_fields = ('model_name',)

@admin.register(RAMModel)
class RAMModelAdmin(admin.ModelAdmin):
    list_display = ('manufacturer', 'model_name', 'capacity', 'memory_type', 'speed', 'price')
    list_filter = ('manufacturer', 'memory_type')
    search_fields = ('model_name',)

@admin.register(StorageModel)
class StorageModelAdmin(admin.ModelAdmin):
    list_display = ('manufacturer', 'model_name', 'capacity', 'storage_type', 'price')
    list_filter = ('manufacturer', 'storage_type')
    search_fields = ('model_name',)

@admin.register(GPUModel)
class GPUModelAdmin(admin.ModelAdmin):
    list_display = ('manufacturer', 'model_name', 'memory_size', 'memory_type', 'price')
    list_filter = ('manufacturer',)
    search_fields = ('model_name',)

@admin.register(NetworkCardModel)
class NetworkCardModelAdmin(admin.ModelAdmin):
    list_display = ('manufacturer', 'model_name', 'speed', 'ports', 'price')
    list_filter = ('manufacturer',)
    search_fields = ('model_name',)

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'manufacturer', 'license_type', 'price', 'is_subscription')
    list_filter = ('manufacturer', 'license_type', 'is_subscription')
    search_fields = ('name',)
