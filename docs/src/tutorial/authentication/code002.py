def ip_whitelist(request):
    if request.META["REMOTE_ADDR"] == "8.8.8.8":
        return "8.8.8.8"


@api.get("/ipwhiltelist", auth=ip_whitelist)
def ipwhiltelist(request):
    return f"Authenticated client, IP = {request.auth}"
