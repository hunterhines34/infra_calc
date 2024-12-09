from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import (
    Project, ServerConfiguration, SavedConfiguration,
    RAMConfiguration, StorageConfiguration, GPUConfiguration,
    NetworkCardConfiguration, LicenseConfiguration, UserActivity
)

# Customize admin site
admin.site.site_header = 'Paycom - Infrastructure Calculator Admin'
admin.site.site_title = 'Paycom - Infrastructure Calculator'
admin.site.index_title = 'Administration Dashboard'
#admin.site.site_url = '/'

# Register your models here.

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'status', 'total_cost', 'created_at')
    list_filter = ('status', 'created_by')
    search_fields = ('name',)
    readonly_fields = ('total_cost',)

class RAMConfigurationInline(admin.TabularInline):
    model = RAMConfiguration
    extra = 1

class StorageConfigurationInline(admin.TabularInline):
    model = StorageConfiguration
    extra = 1

class GPUConfigurationInline(admin.TabularInline):
    model = GPUConfiguration
    extra = 1

class NetworkCardConfigurationInline(admin.TabularInline):
    model = NetworkCardConfiguration
    extra = 1

class LicenseConfigurationInline(admin.TabularInline):
    model = LicenseConfiguration
    extra = 1

@admin.register(ServerConfiguration)
class ServerConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'is_template']
    list_filter = ['project', 'is_template']
    search_fields = ['name', 'description']
    inlines = [
        RAMConfigurationInline,
        StorageConfigurationInline,
        GPUConfigurationInline,
        NetworkCardConfigurationInline,
        LicenseConfigurationInline,
    ]

@admin.register(SavedConfiguration)
class SavedConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_template', 'created_at', 'server_configuration_name')
    list_filter = ('created_by', 'is_template')
    search_fields = ('name',)

    def server_configuration_name(self, obj):
        return obj.server_configuration.name if obj.server_configuration else 'No Configuration'
    server_configuration_name.short_description = 'Server Configuration'

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'timestamp', 'icon')
    list_filter = ('user', 'timestamp')
    search_fields = ('description', 'user__username')
    ordering = ('-timestamp',)
