'''
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import uuid
import datetime
from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.dispatch import receiver
from django.db.models.signals import post_delete, post_save
from arches.app.models.models import EditLog, ResourceInstance
from django.utils import timezone
from django.core.exceptions import ValidationError


class HeritageApiData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    hapi_log_id = models.UUIDField(blank=False, null=False)
    batch_id = models.PositiveIntegerField(blank=False, null=False)
    part = models.PositiveIntegerField(blank=False, null=False)
    validation = JSONField(blank=True, null=True)
    data = JSONField(blank=True, null=True)

    class Meta:
        managed = True
        verbose_name = "Heritage API Data"
        verbose_name_plural = "Heritage API Data"
        db_table = "hapi_data"
        indexes = [
            models.Index(fields=["batch_id", "part"]),
        ]


class HeritageApiLog(models.Model):
    search_fields = ["batch_id", "id"]
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    RUN_TYPE_CHOICES = [
        (AUTOMATIC, "Automatic"),
        (MANUAL, "Manual"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid1)
    batch_id = models.PositiveIntegerField(unique=True, blank=True, null=True)
    start = models.DateTimeField(default=datetime.datetime.now)
    finish = models.DateTimeField(blank=True, null=True)
    parameters = JSONField(blank=True, null=True)
    run_type = models.CharField(
        max_length=10, choices=RUN_TYPE_CHOICES, default=MANUAL)
    totals = JSONField(blank=True, null=True)
    resources = JSONField(blank=True, null=True)
    messages = JSONField(blank=True, null=True)
    exceptions = JSONField(blank=True, null=True)

    def __str__(self):
        return f"Batch: {self.batch_id} | Start: {self.start.strftime('%Y-%m-%d %H:%M:%S')} | Id: {self.id}"

    class Meta:
        managed = True
        verbose_name = "Heritage API Log"
        verbose_name_plural = "Heritage API Logs"
        db_table = "hapi_log"
        indexes = [
            models.Index(fields=["batch_id"]),
            models.Index(fields=["start"]),
        ]


class HeritageApiExclusion(models.Model):
    search_fields = ["resource_id"]
    id = models.AutoField(primary_key=True)
    resource_id = models.UUIDField(unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resource ID: {self.resource_id} | Id: {self.id}"

    class Meta:
        managed = True
        verbose_name = "Heritage API Exclusion"
        verbose_name_plural = "Heritage API Exclusions"
        db_table = "hapi_exclusion"
        indexes = [
            models.Index(fields=["resource_id"]),
        ]

    def clean(self):
        if not ResourceInstance.objects.filter(resourceinstanceid=self.resource_id).exists():
            raise ValidationError(
                f"Resource ID {self.resource_id} does not exist in ResourceInstance table.")

    def save(self, *args, **kwargs):
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except ValidationError as e:
            self._validation_error = e
            raise


@receiver(post_delete, sender=HeritageApiExclusion)
def log_heritage_api_exclusion_deletion(sender, instance, **kwargs):
    HeritageApiInclusion.objects.filter(
        resource_id=instance.resource_id).delete()
    HeritageApiInclusion.objects.create(resource_id=instance.resource_id)


@receiver(post_save, sender=HeritageApiExclusion)
def log_heritage_api_exclusion_post_save(sender, instance, **kwargs):
    HeritageApiInclusion.objects.filter(
        resource_id=instance.resource_id).delete()


class HeritageApiInclusion(models.Model):
    search_fields = ["resource_id"]
    id = models.AutoField(primary_key=True)
    resource_id = models.UUIDField(unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resource ID: {self.resource_id} | Id: {self.id}"

    class Meta:
        managed = True
        verbose_name = "Heritage API Inclusion"
        verbose_name_plural = "Heritage API Inclusions"
        db_table = "hapi_inclusion"
        indexes = [
            models.Index(fields=["resource_id"]),
        ]
