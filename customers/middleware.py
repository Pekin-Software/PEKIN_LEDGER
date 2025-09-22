from django.http import JsonResponse

class BlockDirectBrowserAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check what the browser is asking for
        accept_header = request.headers.get("Accept", "")

        # If the request looks like a normal browser trying to load a web page
        if accept_header.startswith("text/html"):
            return JsonResponse({"error": "Direct access not allowed"}, status=403)

        # Otherwise, let the request go through (API calls usually ask for JSON)
        return self.get_response(request)
