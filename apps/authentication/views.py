from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse


from .models import User, UserProfile
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm

class UserRegistrationView(CreateView):
    """View for user registration."""
    model = User
    form_class = UserRegistrationForm
    template_name = 'authentication/register.html'
    success_url = reverse_lazy('core:dashboard')
    
    def form_valid(self, form):
        """Handle form validation."""
        response = super().form_valid(form)
        
        # Create user profile
        UserProfile.objects.get_or_create(user=self.object)
        
        # Log in the user
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1']
        )
        if user:
            login(self.request, user)
            messages.success(self.request, _('Account created successfully. Welcome to the platform!'))
        
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(self.request, _('Registration failed. Please check the error below.'))
        return super().form_invalid(form)
    

def user_login_view(request):
    """View for user login."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Try to authenticate the user
            user = authenticate(username=username, password=password)
            
            # Try to authenticate the user
            if user:
                login(request, user)
                
                # Update last login ip
                user.last_login_ip = request.META.get('REMOTE_ADDR')
                user.save(update_fields=['last_login_ip'])
                
                messages.success(request, _('Login successful. Welcome back, {}!'.format(user.get_full_name())))
                
                # Redirect to next page or dashboard
                next_url = request.GET.get('next', 'core:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, _('Invalid email or password'))
        else:
            messages.error(request, _('Please correct the errors below.'))
    else:
        form = UserLoginForm()
    
    return render(request, 'authentication/login.html', {'form': form, 'title': _('Login')})


@login_required
def user_logout_view(request):
    """View for user logout."""
    logout(request)
    messages.success(request, _('You have been logged out successfully.'))
    return redirect('authentication:login')

class UserProfileView(LoginRequiredMixin, UpdateView):
    """View for user profile."""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'authentication/profile.html'
    success_url = reverse_lazy('authentication:profile')
    
    def get_object(self):
        """Get the user profile."""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def form_valid(self, form):
        """Handle form validation."""
        response = super().form_valid(form)
        messages.success(self.request, _('Your profile has been updated successfully.'))
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)
    

@login_required
def check_email_availability(request):
    """Check if an email is available for registration."""
    email = request.GET.get('email', '')
    current_user_email = request.user.email
    
    if email and email != current_user_email:
        exists = User.objects.filter(email=email).exists()  
        return JsonResponse({
            'available': not exists,
            'message': _('This email is already in use.') if exists else _('This email is available for registration.')
        })
    return JsonResponse({
        'available': True,
        'message': "This email is available for registration."
    })






    
