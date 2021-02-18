from aliases.models import (
    Alias,
    get_aliases,
    alias_replace,
    NotActiveAliasException)
import pytest
import random
import string
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet

pytestmark = pytest.mark.django_db


def generate_string():
    return ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(random.randint(5, 10)))


alias1 = generate_string()
alias2 = generate_string()
alias3 = generate_string()
target1 = generate_string()
target2 = generate_string()
end = timezone.now()


@pytest.fixture()
def test_aliases():
    return [
        {
            'alias': alias1,
            'target': target1,
            'start': end - timezone.timedelta(days=2),
            'end': end
        },
        {
            'alias': alias1,
            'target': target1,
            'start': end - timezone.timedelta(hours=5),
            'end': end + timezone.timedelta(days=1)
        },
        {
            'alias': alias2,
            'target': target1,
            'start': end
        },
        {
            'alias': alias3,
            'target': target2,
            'start': end,
            'end': end + timezone.timedelta(days=1)
        }

    ]


ERRORS = {
    'end_field': 'End timestamp value should be '
                 'grater then start value or equal to None',
    'start/end fields': 'dates overlapping of currently active alias',
    'alias field': 'another target have same alias'
}

invalid_aliases = [

    {
        'alias': generate_string(),
        'target': generate_string(),
        'start': timezone.now(),
        'end': timezone.now() - timezone.timedelta(minutes=1)
    },
    {
        'alias': alias2,
        'target': target1,
        'start': end,
        'end': None
    },
    {
        'alias': alias3,
        'target': target1,
        'start': end,
        'end': end + timezone.timedelta(days=1)
    }

]


@pytest.fixture()
def create_aliases(test_aliases):
    aliases = [Alias(**fields) for fields in test_aliases]
    Alias.objects.bulk_create(aliases)


def test_prepeared(create_aliases, test_aliases):
    a = Alias.objects.count()
    assert a == len(test_aliases)


def test_alias_save(create_aliases):
    timestamp = timezone.now()
    alias = Alias.objects.create(
        alias='some_alias',
        target='some_target',
        start=timestamp)
    assert alias.alias == 'some_alias'
    assert alias.target == 'some_target'
    assert alias.start == timestamp
    assert alias.end is None


@pytest.fixture(
    params=[
        (ERRORS['end_field'], invalid_aliases[0]),
        (ERRORS['start/end fields'], invalid_aliases[1]),
        (ERRORS['alias field'], invalid_aliases[2])
    ],
    ids=ERRORS)
def validation_data(request):
    return request.param


def test_clean_timestamp(create_aliases, validation_data):
    with pytest.raises(ValidationError) as excinfo:
        alias = validation_data[1]
        Alias.objects.create(
            alias=alias['alias'],
            target=alias['target'],
            start=alias['start'],
            end=alias['end']
        )

    assert validation_data[0] in str(excinfo.value)


@pytest.fixture(
    params=[
        (target1, 2, None, None),
        (target2, 1, None, None),
        (target1, 2, end - timezone.timedelta(hours=6), None),
        (target1, 1, None, end),
        (target2, 1, end, end + timezone.timedelta(days=1))
    ]
)
def targets_for_test(request):
    return request.param


def test_get_aliases(create_aliases, targets_for_test):
    test_target, alias_count, range_from, range_to = targets_for_test
    aliases = get_aliases(test_target, range_from, range_to)

    targets = [alias.target == test_target for alias in aliases]
    if not range_to:
        ends = [alias.end > timezone.now()
                for alias in aliases if alias.end is not None]
        assert all(ends) is True
    if range_to:
        is_in_range_to = [alias.end <= range_to
                          for alias in aliases if alias.end is not None]
        assert all(is_in_range_to) is True
    if range_from:
        is_in_range_from = [alias.end >= range_from
                            for alias in aliases if alias.end is not None]
        assert all(is_in_range_from) is True

    assert isinstance(aliases, QuerySet)
    assert aliases.count() == alias_count
    assert all(targets) is True


def test_replace_alias(create_aliases):
    old_inactive_alias = Alias.objects.get(pk=1)
    old_active_alias = Alias.objects.get(pk=2)
    timestamp = timezone.now()
    with pytest.raises(NotActiveAliasException):
        alias_replace(old_inactive_alias, timestamp, generate_string())
    new_alias = alias_replace(old_active_alias, timestamp, generate_string())
    old_active_alias.refresh_from_db()
    assert old_active_alias.end == new_alias.start
    assert old_active_alias.target == new_alias.target
    assert new_alias.end is None
