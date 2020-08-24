from django.conf import settings
from django.db import models

from rest_framework.exceptions import ValidationError


class ShortenedURL(models.Model):
    user = models.ForeignKey('accounts.User', related_name='urls',
                             on_delete=models.CASCADE)
    long_url = models.CharField(max_length=512)
    suggested_path = models.CharField(max_length=32, blank=True, null=True)
    key = models.CharField(max_length=8, unique=True, blank=True,
                           null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s %s' % (self.long_url, self.short_url)

    def clean(self):
        if not (self.long_url.startswith("http") or
                self.long_url.startswith("https")):
            raise ValidationError('URL should start with "http" or "https"')

    @property
    def hits(self):
        return self.visits.count()

    def short_url(self):
        if self.suggested_path:
            return (settings.SHORT_URL_DOMAIN + self.key +
                    '-' + self.suggested_path)
        return settings.SHORT_URL_DOMAIN + self.key

    def set_on_redis(self, redis_instance):
        redis_instance.set(name=self.key,
                           value=self.long_url)


class PlatFormTypes:
    MOBILE = 'mobile'
    TABLET = 'tablet'
    DESKTOP = 'desktop'

    TYPES = (
        (MOBILE, MOBILE),
        (TABLET, TABLET),
        (DESKTOP, DESKTOP),
    )


class Analytic(models.Model):
    short_url = models.OneToOneField('ShortenedURL', related_name='analytic',
                                     on_delete=models.CASCADE)
    total_visits = models.PositiveIntegerField()



class Visit(models.Model):
    short_url = models.ForeignKey('ShortenedURL', related_name='visits',
                                  on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    platform = models.CharField(max_length=16, choices=PlatFormTypes.TYPES,
                                db_index=True)
    browser = models.CharField(max_length=128, db_index=True)
    session_key = models.CharField(max_length=64, db_index=True)
