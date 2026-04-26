"""C10 — Opportunity stage-transition service."""

from django.utils import timezone

from core.models import Activity, Opportunity, User


class TransitionError(Exception):
    pass


def transition_stage(
    opp: Opportunity,
    new_stage: str,
    user: User,
    *,
    close_reason: str = "",
) -> Opportunity:
    """
    Move *opp* to *new_stage*, enforcing all business rules.

    - Free movement between non-terminal stages.
    - → won / lost: requires expected_close_date; sets closed_at.
    - → lost: requires close_reason (arg or opp.close_reason).
    - Reopening from won/lost: admin only; clears closed_at + close_reason.
    - Every successful transition writes an Activity(kind=note) on the opp.

    Returns the (saved) opportunity.  Raises TransitionError on violation.
    """
    valid_stages = {s for s, _ in Opportunity.STAGE_CHOICES}
    if new_stage not in valid_stages:
        raise TransitionError(f"{new_stage!r} is not a valid stage.")

    old_stage = opp.stage
    if old_stage == new_stage:
        return opp

    is_reopening = (
        old_stage in Opportunity.TERMINAL_STAGES
        and new_stage in Opportunity.NON_TERMINAL_STAGES
    )
    is_closing = new_stage in Opportunity.TERMINAL_STAGES

    # Reopening is admin-only
    if is_reopening and not user.is_admin_role:
        raise TransitionError(
            "Only admin users can reopen a won or lost opportunity."
        )

    # Closing rules
    if is_closing:
        if not opp.expected_close_date:
            raise TransitionError(
                "expected_close_date must be set before moving to won or lost."
            )
        if new_stage == Opportunity.STAGE_LOST:
            effective_reason = close_reason or opp.close_reason
            if not effective_reason:
                raise TransitionError(
                    "close_reason is required when moving to lost."
                )
            opp.close_reason = effective_reason
        opp.closed_at = timezone.now()

    if is_reopening:
        opp.closed_at = None
        opp.close_reason = ""

    opp.stage = new_stage
    update_fields = ["stage"]
    if is_closing:
        update_fields += ["closed_at", "close_reason"]
    if is_reopening:
        update_fields += ["closed_at", "close_reason"]

    opp.save(update_fields=update_fields)

    Activity.objects.create(
        kind=Activity.KIND_NOTE,
        subject=f"Stage: {old_stage} → {new_stage}",
        opportunity=opp,
        owner=user,
    )

    return opp
