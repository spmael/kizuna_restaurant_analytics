from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


@login_required
def dashboard_view(request):
    """
    Dashboard view for the core app.
    """
    context = {
        "title": _("Dashboard"),
        "user": request.user,
        "restaurant_name": getattr(request.user, "restaurant_name", None)
        or _("Your restaurant"),
    }
    return render(request, "core/dashboard.html", context)


def custom_404(request, exception):
    """_summary_

    Args:
        request (_type_): _description_
        exception (_type_): _description_
    """
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "error": _("Page not found"),
                "detail": _("The requested page does not exist."),
            },
            status=404,
        )
    return render(
        request,
        "core/404.html",
        {
            "error": _("Page not found"),
            "message": _(
                "The requested page does not exist. Please check the URL and try again."
            ),
        },
        status=404,
    )


def custom_500(request):
    """_summary_

    Args:
        request (_type_): _description_
    """
    if request.path.startswith("/api/"):
        return JsonResponse(
            {
                "error": _("Internal server error"),
                "detail": _("An error occurred while processing your request."),
            },
            status=500,
        )
    return render(
        request,
        "core/500.html",
        {
            "error": _("Internal server error"),
            "message": _("An error occurred while processing your request."),
        },
        status=500,
    )
