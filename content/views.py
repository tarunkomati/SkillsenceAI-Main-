from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ContentBlock


@api_view(['GET'])
@permission_classes([AllowAny])
def landing_content_view(request):
    blocks = ContentBlock.objects.all()
    data = {block.key: block.payload for block in blocks}
    return Response(data)
