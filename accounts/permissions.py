def filter_for_user(user, qs, owner_field="owner"):
    """Return full queryset for admins; filter by owner for reps."""
    if user.is_admin:
        return qs
    return qs.filter(**{owner_field: user})
