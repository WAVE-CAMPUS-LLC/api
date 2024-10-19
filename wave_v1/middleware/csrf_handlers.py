from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_failure

@csrf_failure
def csrf_failure(request, reason=""):
    # Refresh the page in case of a CSRF error
    return redirect(request.path)