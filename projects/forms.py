from django import forms
from .models import (
    Project, ServerConfiguration, SavedConfiguration,
    RAMConfiguration, StorageConfiguration, GPUConfiguration,
    NetworkCardConfiguration, LicenseConfiguration
)

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ServerConfigurationForm(forms.ModelForm):
    class Meta:
        model = ServerConfiguration
        fields = ['name', 'description', 'cpu', 'ram_config', 'storage_config', 'gpu_config', 'network_cards', 'licenses']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': 'Enter server name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 3,
                'placeholder': 'Enter server description'
            }),
            'cpu': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
            }),
            'ram_config': forms.CheckboxSelectMultiple(),
            'storage_config': forms.CheckboxSelectMultiple(),
            'gpu_config': forms.CheckboxSelectMultiple(),
            'network_cards': forms.CheckboxSelectMultiple(),
            'licenses': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional except name
        self.fields['name'].required = True
        self.fields['description'].required = False
        self.fields['cpu'].required = False
        self.fields['ram_config'].required = False
        self.fields['storage_config'].required = False
        self.fields['gpu_config'].required = False
        self.fields['network_cards'].required = False
        self.fields['licenses'].required = False

        # Add labels
        self.fields['name'].label = 'Server Name'
        self.fields['description'].label = 'Server Description'

class RAMConfigurationForm(forms.ModelForm):
    class Meta:
        model = RAMConfiguration
        fields = ['ram_model', 'quantity']

class StorageConfigurationForm(forms.ModelForm):
    class Meta:
        model = StorageConfiguration
        fields = ['storage_model', 'quantity']

class GPUConfigurationForm(forms.ModelForm):
    class Meta:
        model = GPUConfiguration
        fields = ['gpu_model', 'quantity']

class NetworkCardConfigurationForm(forms.ModelForm):
    class Meta:
        model = NetworkCardConfiguration
        fields = ['network_card', 'quantity']

class LicenseConfigurationForm(forms.ModelForm):
    class Meta:
        model = LicenseConfiguration
        fields = ['license', 'quantity']

class SavedConfigurationForm(forms.ModelForm):
    class Meta:
        model = SavedConfiguration
        fields = ['name', 'description', 'is_template']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
