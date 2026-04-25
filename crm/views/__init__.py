from .leads import lead_list, lead_detail
from .contacts import contact_list, contact_detail
from .accounts import account_list, account_detail
from .opportunities import opportunity_list, opportunity_detail
from .activity import (
    lead_activity_create,
    contact_activity_create,
    account_activity_create,
    opportunity_activity_create,
    activity_complete,
    activity_edit,
    activity_delete,
)
