from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.utils import timezone


class NotActiveAliasException(Exception):
    def __str__(self):
        return 'Not activ ealias modification attemp'


class Alias(models.Model):
    """Alias of related target model objects.

    method save() overriden to invoke method clean()
    during object creation for handling custom
    model fields validation.

    Note that bulk-operations which not include
    sending save() signal would ignore validation.
    """

    alias = models.TextField(db_index=True)
    target = models.CharField(max_length=24)
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField(default=None,
                               null=True,
                               db_index=True)

    def __str__(self):
        return f'{self.pk}. alias: {self.alias} - target: {self.target}'

    def clean(self):
        """Define custom validation of model fields."""

        if self.end is not None and self.end <= self.start:
            raise ValidationError({
                'end_field': 'End timestamp value should be '
                             'grater then start value or equal to None'})

        if Alias.objects.filter(
                Q(alias=self.alias,
                  target=self.target,
                  end__gte=self.start) |
                Q(alias=self.alias,
                  target=self.target,
                  end__isnull=True)).exists():
            raise ValidationError({
                'start/end fields':
                    'dates overlapping of currently active alias'})

        if Alias.objects.filter(
                Q(alias=self.alias, end__gte=self.start) |
                Q(alias=self.alias, end__isnull=True)).exists():
            raise ValidationError({
                'alias field': 'another target have same alias'})

    def save(self, *args, **kwargs):
        """Extended with pre-save validation."""

        self.clean()
        return super(Alias, self).save(*args, **kwargs)

    def is_active(self) -> bool:
        return self.end > timezone.now() or self.end is None


def get_aliases(target, range_from=None, range_to=None):
    """Get target aliases.

    Basic usage - fetch currently active
    aliases of related target model object.

    target(str): required, related model fk
    range_from(datetime obj): period from (inclusive)
    range_to(datetime obj): period to (exclusive)

    :return: Alias queryset
    """
    if range_to and range_from:
        return Alias.objects.filter(
            target=target,
            start__gte=range_from,
            end__lte=range_to)

    if not range_to and not range_from:
        return Alias.objects.filter(
            Q(target=target,
              end__gte=timezone.now()) |
            Q(target=target, end=None))

    if not range_to:
        return Alias.objects.filter(
            Q(target=target,
              start__gte=range_from,
              end__gte=timezone.now()) |
            Q(target=target,
              start__gte=range_from,
              end=None))

    return Alias.objects.filter(
        target=target,
        end__lte=range_to)


@transaction.atomic
def alias_replace(alias_object, replace_at, new_alias_value):
    """Set existing alias object deactivation time ,
    and create new alias which will be active since that time.

    :return new_alias object
    """

    if not alias_object.is_active():
        raise NotActiveAliasException

    Alias.objects.filter(pk=alias_object.pk).update(end=replace_at)

    new_alias = Alias.objects.create(
        alias=new_alias_value,
        target=alias_object.target,
        start=replace_at)

    return new_alias
