from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

from .forms import RegisterForm
from .models import Profile


def register(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save(
                commit=False
            )

            user.set_password(
                form.cleaned_data['password']
            )

            user.save()

            # =====================================================
            # CREATE PROFILE
            # =====================================================

            Profile.objects.create(

                user=user,

                real_name=form.cleaned_data[
                    'real_name'
                ],

                mobile=form.cleaned_data[
                    'mobile'
                ],

                age=form.cleaned_data[
                    'age'
                ],

                gender=form.cleaned_data[
                    'gender'
                ],

                location=form.cleaned_data[
                    'location'
                ],

                # =================================================
                # DELIVERY INFORMATION
                # =================================================

                address=form.cleaned_data[
                    'address'
                ],

                city=form.cleaned_data[
                    'city'
                ],

                state=form.cleaned_data[
                    'state'
                ],

                pincode=form.cleaned_data[
                    'pincode'
                ]
            )

            messages.success(
                request,
                'Account created successfully! Please login.'
            )

            return redirect('login')

    else:

        form = RegisterForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


# =============================================================
# LOGIN
# =============================================================

def user_login(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get(
            'username'
        )

        password = request.POST.get(
            'password'
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            messages.success(
                request,
                f'Welcome back, {user.username}!'
            )

            return redirect('home')

        else:

            messages.error(
                request,
                'Invalid username or password.'
            )

    return render(
        request,
        'accounts/login.html'
    )


# =============================================================
# LOGOUT
# =============================================================

def user_logout(request):

    logout(request)

    messages.success(
        request,
        'You have been logged out successfully.'
    )

    return redirect('home')