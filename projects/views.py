from .forms import ProjectForm, ServerConfigurationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Project, ServerConfiguration, SavedConfiguration, UserActivity, CPUModel, RAMModel, StorageModel, GPUModel, NetworkCardModel, License, RAMConfiguration, StorageConfiguration, GPUConfiguration, NetworkCardConfiguration, LicenseConfiguration
from django.db.models import Count, Sum
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth
import json
from django.db.models import Q
from django.views.generic.edit import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import xlsxwriter
from io import BytesIO

# Create your views here.

@login_required
def index(request):
    # Get filter parameters
    time_frame = request.GET.get('time_frame', 'all')
    status = request.GET.get('status', 'all')
    config_type = request.GET.get('config_type', 'all')
    
    # Base queries
    projects_query = Project.objects.filter(created_by=request.user)
    configs_query = SavedConfiguration.objects.filter(created_by=request.user)
    
    # Apply time frame filter
    if time_frame != 'all':
        time_delta = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365,
        }.get(time_frame)
        if time_delta:
            date_threshold = timezone.now() - timedelta(days=time_delta)
            projects_query = projects_query.filter(created_at__gte=date_threshold)
            configs_query = configs_query.filter(created_at__gte=date_threshold)
    
    # Apply status filter for projects
    if status != 'all':
        projects_query = projects_query.filter(status=status)
    
    # Apply config type filter
    if config_type != 'all':
        is_template = (config_type == 'template')
        configs_query = configs_query.filter(is_template=is_template)
    
    # Original statistics calculations
    today = timezone.now()
    last_month = today - timedelta(days=30)
    
    current_month_projects = projects_query.filter(created_at__gte=last_month).count()
    previous_month_projects = projects_query.filter(
        created_at__gte=last_month - timedelta(days=30),
        created_at__lt=last_month
    ).count()
    
    if previous_month_projects > 0:
        project_growth = round(((current_month_projects - previous_month_projects) / previous_month_projects) * 100)
    else:
        project_growth = 100 if current_month_projects > 0 else 0
    
    context = {
        'recent_projects': projects_query.order_by('-created_at')[:5],
        'saved_configs': configs_query.order_by('-created_at')[:5],
        'total_projects': projects_query.count(),
        'pending_approvals': projects_query.filter(status='PENDING_APPROVAL').count(),
        'total_servers': ServerConfiguration.objects.filter(project__created_by=request.user).count(),
        'total_saved_configs': configs_query.count(),
        'project_growth': project_growth,
        'last_config_update': timezone.now(),
        # Add filter values to context
        'time_frame': time_frame,
        'status': status,
        'config_type': config_type,
    }
    return render(request, 'projects/index.html', context)

@login_required
def project_list(request):
    # Get filter parameters
    time_frame = request.GET.get('time_frame', 'all')
    status = request.GET.get('status', 'all')
    config_type = request.GET.get('config_type', 'all')
    
    # Base query
    projects_query = Project.objects.filter(created_by=request.user)
    
    # Apply time frame filter
    if time_frame != 'all':
        time_delta = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365,
        }.get(time_frame)
        if time_delta:
            date_threshold = timezone.now() - timedelta(days=time_delta)
            projects_query = projects_query.filter(created_at__gte=date_threshold)
    
    # Apply status filter
    if status != 'all':
        projects_query = projects_query.filter(status=status)
    
    # Apply config type filter
    if config_type != 'all':
        if config_type == 'template':
            projects_query = projects_query.filter(server_configuration__is_template=True)
        else:
            projects_query = projects_query.filter(server_configuration__is_template=False)
    
    # Order projects by creation date
    projects = projects_query.order_by('-created_at')
    
    context = {
        'projects': projects,
        'time_frame': time_frame,
        'status': status,
        'config_type': config_type,
    }
    
    return render(request, 'projects/project_list.html', context)

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, created_by=request.user)
    
    # Force recalculation of total cost
    total = Decimal('0.00')
    for server in project.servers.all():
        total += server.calculate_total_cost()
    project.total_cost = total
    project.save(update_fields=['total_cost'])
    
    # Refresh the project to get updated data
    project.refresh_from_db()
    
    return render(request, 'projects/project_detail.html', {'project': project})

@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            
            # Create activity record
            UserActivity.objects.create(
                user=request.user,
                description=f'Created new project "{project.name}"',
                icon='plus'
            )
            
            messages.success(request, 'Project created successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form})

@login_required
def project_submit(request, pk):
    project = get_object_or_404(Project, pk=pk, created_by=request.user)
    
    if project.status == 'DRAFT':
        project.status = 'PENDING_APPROVAL'
        project.save()
        
        # Create activity record
        UserActivity.objects.create(
            user=request.user,
            description=f'Submitted project "{project.name}" for approval',
            icon='paper-plane'
        )
        
        messages.success(request, 'Project submitted for approval!')
    else:
        messages.warning(request, 'This project cannot be submitted.')
    
    return redirect('project_detail', pk=project.pk)

@login_required
def saved_configs(request):
    configs = SavedConfiguration.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'projects/saved_configs.html', {'configs': configs})

@login_required
def saved_config_detail(request, pk):
    config = get_object_or_404(SavedConfiguration, pk=pk, created_by=request.user)
    return render(request, 'projects/saved_config_detail.html', {'config': config})

@login_required
def server_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    
    if request.method == 'POST':
        form = ServerConfigurationForm(request.POST)
        if form.is_valid():
            server = form.save(commit=False)
            server.project = project
            
            # Handle CPU (single selection)
            cpu_id = request.POST.get('cpu')
            if cpu_id:
                server.cpu_id = cpu_id
            
            server.save()
            
            # Create activity record
            UserActivity.objects.create(
                user=request.user,
                description=f'Added new server "{server.name}" to project "{project.name}"',
                icon='server'
            )
            
            # Handle multiple configurations
            post_data = request.POST
            
            # Process RAM configurations
            ram_configs = post_data.getlist('ram_config[]') or post_data.getlist('ram_config')
            for ram_id in ram_configs:
                if ram_id:
                    server.ram_configurations.create(
                        ram_model_id=ram_id,
                        quantity=1
                    )
            
            # Process Storage configurations
            storage_configs = post_data.getlist('storage_config[]') or post_data.getlist('storage_config')
            for storage_id in storage_configs:
                if storage_id:
                    server.storage_configurations.create(
                        storage_model_id=storage_id,
                        quantity=1
                    )
            
            # Process GPU configurations
            gpu_configs = post_data.getlist('gpu_config[]') or post_data.getlist('gpu_config')
            for gpu_id in gpu_configs:
                if gpu_id:
                    server.gpu_configurations.create(
                        gpu_model_id=gpu_id,
                        quantity=1
                    )
            
            # Process Network configurations
            network_configs = post_data.getlist('network_cards[]') or post_data.getlist('network_cards')
            for network_id in network_configs:
                if network_id:
                    server.network_configurations.create(
                        network_card_id=network_id,
                        quantity=1
                    )
            
            # Handle licenses (many-to-many)
            license_ids = post_data.getlist('licenses[]') or post_data.getlist('licenses')
            if license_ids:
                server.licenses.set(license_ids)
            
            # Update project total cost
            project.calculate_total_cost()
            
            messages.success(request, 'Server configuration added successfully!')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ServerConfigurationForm()
    
    return render(request, 'projects/server_form.html', {
        'form': form, 
        'project': project,
        'is_edit': False
    })

@login_required
def server_detail(request, project_id, server_id):
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    server = get_object_or_404(ServerConfiguration, pk=server_id, project=project)
    return render(request, 'projects/server_detail.html', {
        'project': project,
        'server': server
    })

@login_required
def server_edit(request, project_id, server_id):
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    server = get_object_or_404(ServerConfiguration, pk=server_id, project=project)
    
    if request.method == 'POST':
        form = ServerConfigurationForm(request.POST, instance=server)
        if form.is_valid():
            server = form.save(commit=False)
            
            # Handle CPU (single selection)
            cpu_id = request.POST.get('cpu')
            if cpu_id:
                server.cpu_id = cpu_id
            
            server.save()
            
            # Clear existing configurations
            server.ram_configurations.all().delete()
            server.storage_configurations.all().delete()
            server.gpu_configurations.all().delete()
            server.network_configurations.all().delete()
            
            # Handle multiple configurations
            post_data = request.POST
            
            # Process RAM configurations
            ram_configs = post_data.getlist('ram_config[]') or post_data.getlist('ram_config')
            for ram_id in ram_configs:
                if ram_id:
                    server.ram_configurations.create(
                        ram_model_id=ram_id,
                        quantity=1
                    )
            
            # Process Storage configurations
            storage_configs = post_data.getlist('storage_config[]') or post_data.getlist('storage_config')
            for storage_id in storage_configs:
                if storage_id:
                    server.storage_configurations.create(
                        storage_model_id=storage_id,
                        quantity=1
                    )
            
            # Process GPU configurations
            gpu_configs = post_data.getlist('gpu_config[]') or post_data.getlist('gpu_config')
            for gpu_id in gpu_configs:
                if gpu_id:
                    server.gpu_configurations.create(
                        gpu_model_id=gpu_id,
                        quantity=1
                    )
            
            # Process Network configurations
            network_configs = post_data.getlist('network_cards[]') or post_data.getlist('network_cards')
            for network_id in network_configs:
                if network_id:
                    server.network_configurations.create(
                        network_card_id=network_id,
                        quantity=1
                    )
            
            # Handle licenses (many-to-many)
            license_ids = post_data.getlist('licenses[]') or post_data.getlist('licenses')
            if license_ids:
                server.licenses.set(license_ids)
            
            # Update project total cost
            project.calculate_total_cost()
            
            # Create activity record
            UserActivity.objects.create(
                user=request.user,
                description=f'Updated server "{server.name}" in project "{project.name}"',
                icon='edit'
            )
            
            messages.success(request, 'Server updated successfully.')
            return redirect('project_detail', pk=project.id)
    else:
        form = ServerConfigurationForm(instance=server)
        
        # Pre-populate the form with existing configurations
        existing_configs = {
            'ram': server.ram_configurations.all(),
            'storage': server.storage_configurations.all(),
            'gpu': server.gpu_configurations.all(),
            'network': server.network_configurations.all(),
        }
    
    return render(request, 'projects/server_form.html', {
        'form': form,
        'project': project,
        'server': server,
        'is_edit': True,
        'existing_configs': existing_configs  # Pass existing configurations to template
    })

@login_required
def server_delete(request, project_id, server_id):
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    server = get_object_or_404(ServerConfiguration, pk=server_id, project=project)
    
    if request.method == 'POST':
        server_name = server.name
        project_name = project.name
        server.delete()
        
        # Create activity record
        UserActivity.objects.create(
            user=request.user,
            description=f'Deleted server "{server_name}" from project "{project_name}"',
            icon='trash'
        )
        
        messages.success(request, 'Server deleted successfully!')
        return redirect('project_detail', pk=project_id)
    # ... rest of the view ...

@login_required
def project_revert_to_draft(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        if project.status == 'PENDING_APPROVAL':
            project.status = 'DRAFT'
            project.save()
            messages.success(request, 'Project has been reverted to draft status.')
        else:
            messages.error(request, 'Project can only be reverted when in pending approval status.')
    
    return redirect('project_detail', pk=project_id)

@login_required
def profile(request):
    # Get filter parameters
    time_frame = request.GET.get('time_frame', 'all')
    status = request.GET.get('status', 'all')
    
    # Base queries
    projects_query = Project.objects.filter(created_by=request.user)
    
    # Apply time frame filter
    if time_frame != 'all':
        time_delta = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365,
        }.get(time_frame)
        if time_delta:
            date_threshold = timezone.now() - timedelta(days=time_delta)
            projects_query = projects_query.filter(created_at__gte=date_threshold)
    
    # Apply status filter
    if status != 'all':
        projects_query = projects_query.filter(status=status)
    
    # Get user's projects with annotated server count and total cost
    user_projects = projects_query.annotate(server_count=Count('servers'))\
        .prefetch_related('servers')\
        .order_by('-created_at')
    
    # Calculate statistics based on filtered projects
    total_projects = user_projects.count()
    total_servers = ServerConfiguration.objects.filter(project__in=user_projects).count()
    
    # Calculate total cost for filtered projects
    total_cost_managed = user_projects.aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Get project statistics for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    projects_stats = {
        'total': total_projects,
        'active': user_projects.filter(status='APPROVED').count(),
        'pending': user_projects.filter(status='PENDING_APPROVAL').count(),
        'recent': user_projects.filter(created_at__gte=thirty_days_ago).count(),
    }
    
    # Get last 7 days of user activities
    seven_days_ago = timezone.now() - timedelta(days=7)
    user_activities = UserActivity.objects.filter(
        user=request.user,
        timestamp__gte=seven_days_ago
    ).select_related('user').order_by('-timestamp')
    
    context = {
        'user': request.user,
        'projects': user_projects[:5],  # Last 5 projects
        'total_projects': total_projects,
        'total_servers': total_servers,
        'total_cost_managed': total_cost_managed,
        'user_activities': user_activities,
        'projects_stats': projects_stats,
        # Add filter values to context
        'time_frame': time_frame,
        'status': status,
    }
    
    return render(request, 'profile.html', context)

@login_required
def reports(request):
    # Get date ranges - now using timezone-aware dates
    end_date = timezone.now()
    start_date = end_date - timedelta(days=180)  # Last 6 months
    
    # Monthly costs data - using actual project costs
    monthly_costs = Project.objects.filter(
        created_at__gte=start_date
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_cost=Sum('total_cost')
    ).order_by('month')

    # Resource distribution - using actual configurations
    resource_dist = {
        'compute': ServerConfiguration.objects.filter(cpu__isnull=False).count(),
        'storage': ServerConfiguration.objects.filter(storage_config__isnull=False).count(),
        'network': ServerConfiguration.objects.filter(network_cards__isnull=False).count(),
        'gpu': ServerConfiguration.objects.filter(gpu_config__isnull=False).count()
    }

    # Server usage data - getting actual server metrics
    servers = ServerConfiguration.objects.all()[:5]  # Limit to 5 most recent
    
    # Calculate CPU and Memory usage from configurations
    server_metrics = []
    for server in servers:
        # Get the total RAM from all RAM configurations
        total_ram = sum(
            config.quantity * config.ram_model.capacity 
            for config in server.ram_configurations.all()
        )
        max_ram = 512  # Increased max RAM since we have 128GB DIMMs
        
        # Calculate usage percentages
        cpu_cores = server.cpu.cores if server.cpu else 0
        max_cores = 64  # Set a reasonable maximum CPU cores
        
        cpu_usage = (cpu_cores / max_cores) * 100 if cpu_cores > 0 else 0
        memory_usage = (total_ram / max_ram) * 100 if total_ram > 0 else 0
        
        server_metrics.append({
            'name': server.name,
            'cpu_usage': round(cpu_usage, 1),
            'memory_usage': round(memory_usage, 1)
        })
    
    # Project growth - monthly new projects
    project_growth = Project.objects.filter(
        created_at__gte=start_date
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    context = {
        'tabs': [
            {'id': 'overview', 'name': 'Overview'},
            {'id': 'cost_analysis', 'name': 'Cost Analysis'},
            {'id': 'usage_metrics', 'name': 'Usage Metrics'},
            {'id': 'performance', 'name': 'Performance'},
        ],
        'active_tab': request.GET.get('tab', 'overview'),
        
        # Format data for ApexCharts
        'monthly_costs_labels': json.dumps([
            timezone.localtime(m['month']).strftime('%Y-%m-%d') 
            for m in monthly_costs
        ]),
        'monthly_costs_data': json.dumps([float(m['total_cost']) for m in monthly_costs]),
        
        'resource_dist_labels': json.dumps(['Compute', 'Storage', 'Network', 'GPU']),
        'resource_dist_data': json.dumps([
            resource_dist['compute'],
            resource_dist['storage'],
            resource_dist['network'],
            resource_dist['gpu']
        ]),
        
        'server_names': json.dumps([s['name'] for s in server_metrics]),
        'server_cpu_data': json.dumps([s['cpu_usage'] for s in server_metrics]),
        'server_memory_data': json.dumps([s['memory_usage'] for s in server_metrics]),
        
        'project_growth_labels': json.dumps([p['month'].strftime('%Y-%m-%d') for p in project_growth]),
        'project_growth_data': json.dumps([p['count'] for p in project_growth]),
        
        # Key metrics with real data
        'key_metrics': [
            {
                'name': 'Total Cost',
                'current': Project.objects.aggregate(Sum('total_cost'))['total_cost__sum'] or 0,
                'previous': Project.objects.filter(
                    created_at__lt=start_date
                ).aggregate(Sum('total_cost'))['total_cost__sum'] or 0,
                'change': calculate_percentage_change(
                    Project.objects.filter(created_at__lt=start_date).aggregate(Sum('total_cost'))['total_cost__sum'] or 0,
                    Project.objects.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
                )
            },
            {
                'name': 'Active Projects',
                'current': Project.objects.filter(status='ACTIVE').count(),
                'previous': Project.objects.filter(
                    status='ACTIVE',
                    created_at__lt=start_date
                ).count(),
                'change': calculate_percentage_change(
                    Project.objects.filter(status='ACTIVE', created_at__lt=start_date).count(),
                    Project.objects.filter(status='ACTIVE').count()
                )
            },
            {
                'name': 'Total Servers',
                'current': ServerConfiguration.objects.count(),
                'previous': ServerConfiguration.objects.filter(
                    project__created_at__lt=start_date
                ).count(),
                'change': calculate_percentage_change(
                    ServerConfiguration.objects.filter(project__created_at__lt=start_date).count(),
                    ServerConfiguration.objects.count()
                )
            }
        ]
    }
    return render(request, 'projects/reports.html', context)

def calculate_percentage_change(old_value, new_value):
    if old_value == 0:
        return 100 if new_value > 0 else 0
    return round(((new_value - old_value) / old_value) * 100, 1)

@login_required
def edit_profile(request):
    user = request.user
    
    if request.method == 'POST':
        # Get form data - removed email
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Update user - removed email
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
        
    return render(request, 'edit_profile.html', {'user': user})

@login_required
def search(request):
    query = request.GET.get('q', '')
    results = {
        'projects': [],
        'configurations': [],
        'query': query
    }
    
    if query:
        # Search in projects
        projects = Project.objects.filter(
            Q(created_by=request.user) &
            (Q(name__icontains=query) | 
             Q(description__icontains=query))
        ).order_by('-created_at')
        
        # Search in saved configurations
        configurations = SavedConfiguration.objects.filter(
            Q(created_by=request.user) &
            (Q(name__icontains=query) | 
             Q(description__icontains=query))
        ).order_by('-created_at')
        
        results['projects'] = projects
        results['configurations'] = configurations
    
    return render(request, 'projects/search_results.html', results)

@login_required
def saved_config_list(request):
    configs = SavedConfiguration.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'projects/saved_configurations/list.html', {
        'configs': configs
    })

@login_required
def saved_config_create(request):
    if request.method == 'POST':
        try:
            # Create server configuration
            server_config = ServerConfiguration.objects.create(
                project=None,  # No project for saved configs
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                cpu=CPUModel.objects.get(id=request.POST.get('cpu')),
                is_template=bool(request.POST.get('is_template', False))
            )

            # Process RAM configurations
            ram_ids = request.POST.getlist('ram[]')
            ram_quantities = request.POST.getlist('ram_quantity[]')
            for ram_id, quantity in zip(ram_ids, ram_quantities):
                if ram_id:
                    RAMConfiguration.objects.create(
                        server=server_config,
                        ram_model_id=ram_id,
                        quantity=int(quantity)
                    )

            # Process Storage configurations
            storage_ids = request.POST.getlist('storage[]')
            storage_quantities = request.POST.getlist('storage_quantity[]')
            for storage_id, quantity in zip(storage_ids, storage_quantities):
                if storage_id:
                    StorageConfiguration.objects.create(
                        server=server_config,
                        storage_model_id=storage_id,
                        quantity=int(quantity)
                    )

            # Process GPU configurations
            gpu_ids = request.POST.getlist('gpu[]')
            gpu_quantities = request.POST.getlist('gpu_quantity[]')
            for gpu_id, quantity in zip(gpu_ids, gpu_quantities):
                if gpu_id:
                    GPUConfiguration.objects.create(
                        server=server_config,
                        gpu_model_id=gpu_id,
                        quantity=int(quantity)
                    )

            # Process Network Card configurations
            network_ids = request.POST.getlist('network[]')
            network_quantities = request.POST.getlist('network_quantity[]')
            for network_id, quantity in zip(network_ids, network_quantities):
                if network_id:
                    NetworkCardConfiguration.objects.create(
                        server=server_config,
                        network_card_id=network_id,
                        quantity=int(quantity)
                    )

            # Process License configurations
            license_ids = request.POST.getlist('license[]')
            license_quantities = request.POST.getlist('license_quantity[]')
            for license_id, quantity in zip(license_ids, license_quantities):
                if license_id:
                    LicenseConfiguration.objects.create(
                        server=server_config,
                        license_id=license_id,
                        quantity=int(quantity)
                    )

            # Create SavedConfiguration
            saved_config = SavedConfiguration.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                created_by=request.user,
                server_configuration=server_config,
                is_template=bool(request.POST.get('is_template', False))
            )

            messages.success(request, 'Configuration saved successfully!')
            return redirect('saved_config_detail', pk=saved_config.pk)

        except Exception as e:
            messages.error(request, f'Error saving configuration: {str(e)}')
            return redirect('saved_config_create')

    # GET request - show form
    context = {
        'cpus': CPUModel.objects.all(),
        'rams': RAMModel.objects.all(),
        'storages': StorageModel.objects.all(),
        'gpus': GPUModel.objects.all(),
        'network_cards': NetworkCardModel.objects.all(),
        'licenses': License.objects.all(),
    }
    return render(request, 'projects/saved_configurations/create.html', context)

@login_required
def saved_config_detail(request, pk):
    config = get_object_or_404(SavedConfiguration, pk=pk, created_by=request.user)
    return render(request, 'projects/saved_configurations/detail.html', {
        'config': config
    })

@login_required
def saved_config_edit(request, pk):
    config = get_object_or_404(SavedConfiguration, pk=pk, created_by=request.user)
    server_config = config.server_configuration

    if request.method == 'POST':
        try:
            # Update basic information
            config.name = request.POST.get('name')
            config.description = request.POST.get('description')
            config.is_template = bool(request.POST.get('is_template'))
            config.save()

            # Update server configuration
            server_config.name = request.POST.get('name')
            server_config.description = request.POST.get('description')
            server_config.cpu = CPUModel.objects.get(id=request.POST.get('cpu'))
            server_config.save()

            # Update RAM configurations
            server_config.ram_configurations.all().delete()
            ram_ids = request.POST.getlist('ram[]')
            ram_quantities = request.POST.getlist('ram_quantity[]')
            for ram_id, quantity in zip(ram_ids, ram_quantities):
                if ram_id:
                    RAMConfiguration.objects.create(
                        server=server_config,
                        ram_model_id=ram_id,
                        quantity=int(quantity)
                    )

            # Similar updates for other components...
            # (Storage, GPU, Network Cards, Licenses)

            messages.success(request, 'Configuration updated successfully!')
            return redirect('saved_config_detail', pk=pk)

        except Exception as e:
            messages.error(request, f'Error updating configuration: {str(e)}')
            return redirect('saved_config_edit', pk=pk)

    context = {
        'config': config,
        'cpus': CPUModel.objects.all(),
        'rams': RAMModel.objects.all(),
        'storages': StorageModel.objects.all(),
        'gpus': GPUModel.objects.all(),
        'network_cards': NetworkCardModel.objects.all(),
        'licenses': License.objects.all(),
    }
    return render(request, 'projects/saved_configurations/edit.html', context)

@login_required
def saved_config_delete(request, pk):
    config = get_object_or_404(SavedConfiguration, pk=pk, created_by=request.user)
    if request.method == 'POST':
        config.delete()
        messages.success(request, 'Configuration deleted successfully!')
        return redirect('saved_config_list')
    return render(request, 'projects/saved_configurations/delete.html', {
        'config': config
    })

@login_required
def approvals_dashboard(request):
    # Get filter parameters
    time_frame = request.GET.get('time_frame', 'all')
    status = request.GET.get('status', 'all')
    
    # Base query for all projects
    projects_query = Project.objects.all().order_by('-created_at')
    
    # Apply time frame filter
    if time_frame != 'all':
        time_delta = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365,
        }.get(time_frame)
        if time_delta:
            date_threshold = timezone.now() - timedelta(days=time_delta)
            projects_query = projects_query.filter(created_at__gte=date_threshold)
    
    # Apply status filter
    if status != 'all':
        projects_query = projects_query.filter(status=status)
    else:
        # If no status filter, show only pending projects in the list
        pending_projects = projects_query.filter(status='PENDING_APPROVAL')
    
    # Get today's stats
    today = timezone.now().date()
    approved_today = Project.objects.filter(
        status='APPROVED',
        approved_at__date=today
    ).count()
    
    # Get total processed (approved + rejected) within time frame
    total_processed = projects_query.filter(
        status__in=['APPROVED', 'REJECTED']
    ).count()
    
    # Get pending count within time frame
    pending_count = projects_query.filter(status='PENDING_APPROVAL').count()
    
    context = {
        'pending_projects': pending_projects if status == 'all' else projects_query,
        'pending_count': pending_count,
        'approved_today': approved_today,
        'total_processed': total_processed,
        # Add filter values to context
        'time_frame': time_frame,
        'status': status,
    }
    return render(request, 'projects/approvals.html', context)

@login_required
def project_approve(request, project_id):
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        project.status = 'APPROVED'
        project.approved_by = request.user
        project.approved_at = timezone.now()
        project.save()
        
        # Create activity record
        UserActivity.objects.create(
            user=request.user,
            description=f'Approved project "{project.name}"',
            icon='check'
        )
        
        messages.success(request, 'Project has been approved.')
    return redirect('approvals_dashboard')

@login_required
def project_reject(request, project_id):
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        project.status = 'REJECTED'
        project.save()
        
        # Create activity record
        UserActivity.objects.create(
            user=request.user,
            description=f'Rejected project "{project.name}"',
            icon='times'
        )
        
        messages.success(request, 'Project has been rejected.')
    return redirect('approvals_dashboard')

@staff_member_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        
        # Create activity record
        UserActivity.objects.create(
            user=request.user,
            description=f'Deleted project "{project_name}"',
            icon='trash'
        )
        
        messages.success(request, 'Project deleted successfully!')
        return redirect('project_list')
    
    return render(request, 'projects/project_delete.html', {'project': project})

@login_required
def load_saved_config(request, project_id):
    project = get_object_or_404(Project, pk=project_id, created_by=request.user)
    
    if request.method == 'POST':
        config_id = request.POST.get('config_id')
        if config_id:
            saved_config = get_object_or_404(SavedConfiguration, pk=config_id)
            
            # Clone the configuration to the project
            server_config = saved_config.server_configuration.clone_to_project(project)
            
            # Create activity record
            UserActivity.objects.create(
                user=request.user,
                description=f'Added server from saved configuration "{saved_config.name}" to project "{project.name}"',
                icon='folder-open'
            )
            
            # Force refresh from database and recalculate total cost
            project.refresh_from_db()
            project.calculate_total_cost()
            
            messages.success(request, 'Server configuration loaded successfully!')
            return redirect('project_detail', pk=project.id)
    
    # Get all saved configurations for the user
    saved_configs = SavedConfiguration.objects.filter(created_by=request.user)
    
    return render(request, 'projects/load_saved_config.html', {
        'project': project,
        'saved_configs': saved_configs
    })

@login_required
def export_project_pdf(request, pk):
    project = get_object_or_404(Project, pk=pk, created_by=request.user)
    
    # Create the HttpResponse object with PDF headers
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center alignment
    
    # Add title
    elements.append(Paragraph(f"Project: {project.name}", title_style))
    elements.append(Spacer(1, 12))
    
    # Add project details
    elements.append(Paragraph("Project Details", styles['Heading2']))
    details_data = [
        ["Status", project.get_status_display()],
        ["Created On", project.created_at.strftime("%B %d, %Y")],
        ["Total Cost", f"${project.total_cost:,.2f} USD"],
    ]
    
    if project.approved_by:
        details_data.append(["Approved By", project.approved_by.get_full_name()])
        details_data.append(["Approved On", project.approved_at.strftime("%B %d, %Y")])
    
    details_table = Table(details_data)
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (-1, -1), colors.beige),
        ('TEXTCOLOR', (1, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 20))
    
    # Add server configurations
    elements.append(Paragraph("Server Configurations", styles['Heading2']))
    
    for server in project.servers.all():
        elements.append(Paragraph(f"Server: {server.name}", styles['Heading3']))
        elements.append(Spacer(1, 6))
        
        # Create table headers
        server_data = [
            ["Component", "Configuration", "Quantity", "Unit Cost", "Total Cost"],
        ]
        
        # Add CPU
        server_data.append([
            "CPU",
            server.cpu.model_name,
            "1",
            f"${server.cpu.price:,.2f}",
            f"${server.cpu.price:,.2f}"
        ])
        
        # Add RAM configurations
        for config in server.ram_configurations.all():
            server_data.append([
                "RAM",
                f"{config.ram_model.capacity}GB {config.ram_model.memory_type}",
                str(config.quantity),
                f"${config.ram_model.price:,.2f}",
                f"${config.calculate_cost():,.2f}"
            ])
        
        # Add Storage configurations
        for config in server.storage_configurations.all():
            server_data.append([
                "Storage",
                f"{config.storage_model.capacity}GB {config.storage_model.storage_type}",
                str(config.quantity),
                f"${config.storage_model.price:,.2f}",
                f"${config.calculate_cost():,.2f}"
            ])
        
        # Add GPU configurations
        for config in server.gpu_configurations.all():
            server_data.append([
                "GPU",
                config.gpu_model.model_name,
                str(config.quantity),
                f"${config.gpu_model.price:,.2f}",
                f"${config.calculate_cost():,.2f}"
            ])
        
        # Add Network configurations
        for config in server.network_configurations.all():
            server_data.append([
                "Network",
                config.network_card.model_name,
                str(config.quantity),
                f"${config.network_card.price:,.2f}",
                f"${config.calculate_cost():,.2f}"
            ])
        
        # Add License configurations
        for config in server.license_configurations.all():
            server_data.append([
                "License",
                config.license.name,
                str(config.quantity),
                f"${config.license.price:,.2f}",
                f"${config.calculate_cost():,.2f}"
            ])
        
        # Add server total
        server_data.append([
            "",
            "",
            "",
            "Server Total:",
            f"${server.calculate_total_cost():,.2f}"
        ])
        
        # Create and style the table
        server_table = Table(server_data)
        server_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            
            # Data rows styling
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            
            # Total row styling
            ('BACKGROUND', (3, -1), (-1, -1), colors.grey),
            ('TEXTCOLOR', (3, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (3, -1), (-1, -1), 'RIGHT'),
            
            # Column alignments
            ('ALIGN', (2, 1), (2, -2), 'CENTER'),  # Quantity column
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),   # Cost columns
        ]))
        
        elements.append(server_table)
        elements.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    filename = f"project_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response

@login_required
def export_project_excel(request, pk):
    project = get_object_or_404(Project, pk=pk, created_by=request.user)
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#333333',
        'font_color': 'white'
    })
    money_format = workbook.add_format({'num_format': '$#,##0.00'})
    
    # Write project details
    worksheet.write('A1', 'Project Details', header_format)
    worksheet.write('A2', 'Name')
    worksheet.write('B2', project.name)
    worksheet.write('A3', 'Status')
    worksheet.write('B3', project.get_status_display())
    worksheet.write('A4', 'Created On')
    worksheet.write('B4', project.created_at.strftime("%B %d, %Y"))
    worksheet.write('A5', 'Total Cost')
    worksheet.write('B5', project.total_cost, money_format)
    
    # Start server configurations
    row = 7
    worksheet.write(row, 0, 'Server Configurations', header_format)
    row += 1
    
    for server in project.servers.all():
        # Server header
        worksheet.write(row, 0, f'Server: {server.name}', header_format)
        row += 1
        
        # Component headers
        headers = ['Component', 'Configuration', 'Quantity', 'Unit Cost', 'Total Cost']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        # CPU
        worksheet.write(row, 0, 'CPU')
        worksheet.write(row, 1, server.cpu.model_name)
        worksheet.write(row, 2, 1)
        worksheet.write(row, 3, server.cpu.price, money_format)
        worksheet.write(row, 4, server.cpu.price, money_format)
        row += 1
        
        # RAM Configurations
        for config in server.ram_configurations.all():
            worksheet.write(row, 0, 'RAM')
            worksheet.write(row, 1, f'{config.ram_model.capacity}GB {config.ram_model.memory_type}')
            worksheet.write(row, 2, config.quantity)
            worksheet.write(row, 3, config.ram_model.price, money_format)
            worksheet.write(row, 4, config.calculate_cost(), money_format)
            row += 1
        
        # Storage Configurations
        for config in server.storage_configurations.all():
            worksheet.write(row, 0, 'Storage')
            worksheet.write(row, 1, f'{config.storage_model.capacity}GB {config.storage_model.storage_type}')
            worksheet.write(row, 2, config.quantity)
            worksheet.write(row, 3, config.storage_model.price, money_format)
            worksheet.write(row, 4, config.calculate_cost(), money_format)
            row += 1
        
        # GPU Configurations
        for config in server.gpu_configurations.all():
            worksheet.write(row, 0, 'GPU')
            worksheet.write(row, 1, config.gpu_model.model_name)
            worksheet.write(row, 2, config.quantity)
            worksheet.write(row, 3, config.gpu_model.price, money_format)
            worksheet.write(row, 4, config.calculate_cost(), money_format)
            row += 1
        
        # Network Configurations
        for config in server.network_configurations.all():
            worksheet.write(row, 0, 'Network')
            worksheet.write(row, 1, config.network_card.model_name)
            worksheet.write(row, 2, config.quantity)
            worksheet.write(row, 3, config.network_card.price, money_format)
            worksheet.write(row, 4, config.calculate_cost(), money_format)
            row += 1
        
        # License Configurations
        for config in server.license_configurations.all():
            worksheet.write(row, 0, 'License')
            worksheet.write(row, 1, config.license.name)
            worksheet.write(row, 2, config.quantity)
            worksheet.write(row, 3, config.license.price, money_format)
            worksheet.write(row, 4, config.calculate_cost(), money_format)
            row += 1
        
        # Server total
        worksheet.write(row, 3, 'Server Total:', header_format)
        worksheet.write(row, 4, server.calculate_total_cost(), money_format)
        row += 2
    
    # Close the workbook before sending the data
    workbook.close()
    
    # Rewind the buffer
    output.seek(0)
    
    # Generate filename
    filename = f"project_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Send the response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
