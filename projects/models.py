from django.db import models
from django.contrib.auth.models import User
from core.models import (
    CPUModel, RAMModel, StorageModel, GPUModel,
    NetworkCardModel, License
)
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class Project(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_projects')
    approved_at = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    def __str__(self):
        return self.name
    
    def calculate_total_cost(self):
        self.refresh_from_db()
        total = Decimal('0.00')
        
        logger.debug(f"Calculating total cost for project {self.name}")
        
        for server in self.servers.all():
            server_cost = server.calculate_total_cost()
            logger.debug(f"Server '{server.name}' cost: ${server_cost}")
            total += Decimal(str(server_cost))
        
        logger.debug(f"Total project cost: ${total}")
        
        self.total_cost = total
        self.save(update_fields=['total_cost'])
        return total

class ServerConfiguration(models.Model):
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='servers', 
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_template = models.BooleanField(default=False)
    
    # Base components
    cpu = models.ForeignKey(CPUModel, on_delete=models.PROTECT)
    ram_config = models.ManyToManyField(RAMModel, through='RAMConfiguration')
    storage_config = models.ManyToManyField(StorageModel, through='StorageConfiguration')
    gpu_config = models.ManyToManyField(GPUModel, through='GPUConfiguration')
    network_cards = models.ManyToManyField(NetworkCardModel, through='NetworkCardConfiguration')
    licenses = models.ManyToManyField(License, through='LicenseConfiguration')
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"
    
    def calculate_ram_cost(self):
        return sum(
            config.calculate_cost() 
            for config in self.ram_configurations.all()
        )
    
    def calculate_storage_cost(self):
        return sum(
            config.calculate_cost() 
            for config in self.storage_configurations.all()
        )
    
    def calculate_gpu_cost(self):
        return sum(
            config.calculate_cost() 
            for config in self.gpu_configurations.all()
        )
    
    def calculate_network_cost(self):
        return sum(
            config.calculate_cost() 
            for config in self.network_configurations.all()
        )
    
    def calculate_license_cost(self):
        return sum(
            config.calculate_cost() 
            for config in self.license_configurations.all()
        )
    
    def calculate_total_cost(self):
        total = Decimal('0.00')
        
        # CPU cost
        if self.cpu:
            total += Decimal(str(self.cpu.price))
            logger.debug(f"CPU cost for {self.name}: ${self.cpu.price}")
        
        # Component costs
        ram_cost = self.calculate_ram_cost()
        storage_cost = self.calculate_storage_cost()
        gpu_cost = self.calculate_gpu_cost()
        network_cost = self.calculate_network_cost()
        license_cost = self.calculate_license_cost()
        
        logger.debug(f"""
            Costs for server {self.name}:
            RAM: ${ram_cost}
            Storage: ${storage_cost}
            GPU: ${gpu_cost}
            Network: ${network_cost}
            License: ${license_cost}
        """)
        
        total += Decimal(str(ram_cost))
        total += Decimal(str(storage_cost))
        total += Decimal(str(gpu_cost))
        total += Decimal(str(network_cost))
        total += Decimal(str(license_cost))
        
        logger.debug(f"Total cost for server {self.name}: ${total}")
        return total
    
    def clone_to_project(self, project):
        """Creates a copy of this configuration for a specific project"""
        new_config = ServerConfiguration.objects.create(
            project=project,
            name=self.name,
            description=self.description,
            cpu=self.cpu,
            is_template=False
        )
        
        # Clone RAM configurations
        for ram_config in self.ram_configurations.all():
            RAMConfiguration.objects.create(
                server=new_config,
                ram_model=ram_config.ram_model,
                quantity=ram_config.quantity
            )
        
        # Clone Storage configurations
        for storage_config in self.storage_configurations.all():
            StorageConfiguration.objects.create(
                server=new_config,
                storage_model=storage_config.storage_model,
                quantity=storage_config.quantity
            )
        
        # Clone GPU configurations
        for gpu_config in self.gpu_configurations.all():
            GPUConfiguration.objects.create(
                server=new_config,
                gpu_model=gpu_config.gpu_model,
                quantity=gpu_config.quantity
            )
        
        # Clone Network Card configurations
        for network_config in self.network_configurations.all():
            NetworkCardConfiguration.objects.create(
                server=new_config,
                network_card=network_config.network_card,
                quantity=network_config.quantity
            )
        
        # Clone License configurations
        for license_config in self.license_configurations.all():
            LicenseConfiguration.objects.create(
                server=new_config,
                license=license_config.license,
                quantity=license_config.quantity
            )
        
        return new_config

class RAMConfiguration(models.Model):
    server = models.ForeignKey(ServerConfiguration, on_delete=models.CASCADE, related_name='ram_configurations')
    ram_model = models.ForeignKey(RAMModel, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    def calculate_cost(self):
        return self.ram_model.price * self.quantity

class StorageConfiguration(models.Model):
    server = models.ForeignKey(ServerConfiguration, on_delete=models.CASCADE, related_name='storage_configurations')
    storage_model = models.ForeignKey(StorageModel, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    def calculate_cost(self):
        return self.storage_model.price * self.quantity

class GPUConfiguration(models.Model):
    server = models.ForeignKey(ServerConfiguration, on_delete=models.CASCADE, related_name='gpu_configurations')
    gpu_model = models.ForeignKey(GPUModel, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    def calculate_cost(self):
        return self.gpu_model.price * self.quantity

class NetworkCardConfiguration(models.Model):
    server = models.ForeignKey(ServerConfiguration, on_delete=models.CASCADE, related_name='network_configurations')
    network_card = models.ForeignKey(NetworkCardModel, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    def calculate_cost(self):
        return self.network_card.price * self.quantity

class LicenseConfiguration(models.Model):
    server = models.ForeignKey(ServerConfiguration, on_delete=models.CASCADE, related_name='license_configurations')
    license = models.ForeignKey(License, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    
    def calculate_cost(self):
        return self.license.price * self.quantity

class SavedConfiguration(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    server_configuration = models.ForeignKey(ServerConfiguration, on_delete=models.CASCADE)
    is_template = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    icon = models.CharField(max_length=50, default='info')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User activities'
