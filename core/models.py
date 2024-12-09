from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.

class Manufacturer(models.Model):
    name = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class CPUModel(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    cores = models.PositiveIntegerField()
    threads = models.PositiveIntegerField()
    base_clock = models.DecimalField(max_digits=5, decimal_places=2, help_text="Base clock speed in GHz")
    boost_clock = models.DecimalField(max_digits=5, decimal_places=2, help_text="Boost clock speed in GHz")
    tdp = models.PositiveIntegerField(help_text="Thermal Design Power in watts")
    socket = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    def __str__(self):
        return f"{self.manufacturer.name} {self.model_name}"

class RAMModel(models.Model):
    MEMORY_TYPE_CHOICES = [
        ('DDR4', 'DDR4'),
        ('DDR5', 'DDR5'),
    ]
    
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(help_text="Capacity in GB")
    memory_type = models.CharField(max_length=10, choices=MEMORY_TYPE_CHOICES)
    speed = models.PositiveIntegerField(help_text="Speed in MHz")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    def __str__(self):
        return f"{self.manufacturer.name} {self.capacity}GB {self.memory_type}-{self.speed}"

class StorageModel(models.Model):
    STORAGE_TYPE_CHOICES = [
        ('SSD', 'Solid State Drive'),
        ('HDD', 'Hard Disk Drive'),
        ('NVMe', 'NVMe SSD'),
    ]
    
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(help_text="Capacity in GB")
    storage_type = models.CharField(max_length=10, choices=STORAGE_TYPE_CHOICES)
    interface = models.CharField(max_length=50)
    read_speed = models.PositiveIntegerField(help_text="Sequential read speed in MB/s")
    write_speed = models.PositiveIntegerField(help_text="Sequential write speed in MB/s")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    def __str__(self):
        return f"{self.manufacturer.name} {self.model_name} {self.capacity}GB {self.storage_type}"

class GPUModel(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    memory_size = models.PositiveIntegerField(help_text="Memory size in GB")
    memory_type = models.CharField(max_length=50)
    base_clock = models.PositiveIntegerField(help_text="Base clock in MHz")
    boost_clock = models.PositiveIntegerField(help_text="Boost clock in MHz")
    tdp = models.PositiveIntegerField(help_text="Thermal Design Power in watts")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    def __str__(self):
        return f"{self.manufacturer.name} {self.model_name}"

class NetworkCardModel(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    speed = models.PositiveIntegerField(help_text="Speed in Gbps")
    ports = models.PositiveIntegerField()
    pcie_version = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    def __str__(self):
        return f"{self.manufacturer.name} {self.model_name}"

class License(models.Model):
    LICENSE_TYPE_CHOICES = [
        ('OS', 'Operating System'),
        ('DB', 'Database'),
        ('VIRTUALIZATION', 'Virtualization'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    license_type = models.CharField(max_length=20, choices=LICENSE_TYPE_CHOICES)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    is_subscription = models.BooleanField(default=False)
    subscription_period = models.PositiveIntegerField(null=True, blank=True, help_text="Period in months")
    
    def __str__(self):
        return f"{self.name} ({self.get_license_type_display()})"
