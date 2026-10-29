from django.shortcuts import render


def forbidden(request, exception):
    response = render(request, "403.html", status=403)
    response["Cache-Control"] = "no-store, private"
    return response


def not_found(request, exception):
    response = render(request, "404.html", status=404)
    response["Cache-Control"] = "no-store, private"
    return response
