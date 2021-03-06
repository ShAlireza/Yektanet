import redis

from django.shortcuts import redirect
from django.conf import settings

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .serializers import ShortenedURLSerializer
from .tasks import new_visit

redis_instance = redis.Redis(host=settings.REDIS_HOST,
                             port=settings.REDIS_PORT, db=0)


class ShortenURLAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ShortenedURLSerializer

    def get(self, request):
        urls = request.user.urls.all()
        data = self.get_serializer(urls, many=True).data

        return Response(data={'urls': data},
                        status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shortened_url = serializer.save()

        # Set created keys in redis for future redirection requests
        shortened_url.set_on_redis(redis_instance)

        return Response(data={'shortened_url': shortened_url.short_url()},
                        status=status.HTTP_201_CREATED)


class RedirectAPIView(GenericAPIView):

    def get(self, request, key):
        key = key[:key.index('-')]
        url = redis_instance.get(name=key)
        if not url:
            raise NotFound()

        platform = self.get_platform()
        browser = request.user_agent.browser.family
        if not self.request.session.session_key:
            self.request.session.save()

        session_key = self.request.session.session_key

        # Add a visit object to postgres db with an async celery task
        new_visit.delay(key, platform, browser, session_key)

        url = url.decode('utf-8')

        return redirect(url)

    def get_platform(self):
        from .models import PlatFormTypes

        if self.request.user_agent.is_mobile:
            return PlatFormTypes.MOBILE
        elif self.request.user_agent.is_tablet:
            return PlatFormTypes.TABLET
        else:
            return PlatFormTypes.DESKTOP
