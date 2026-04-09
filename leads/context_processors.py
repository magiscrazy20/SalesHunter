from .models import SearchSession


def recent_sessions(request):
    return {
        'recent_sessions': SearchSession.objects.order_by('-created_at')[:20]
    }
