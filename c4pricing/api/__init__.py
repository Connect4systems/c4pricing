# c4pricing/api/__init__.py
from __future__ import annotations

# keep legacy exports from your apis_legacy module (do not remove)
from ..apis_legacy import (
    create_costing_note,
    create_boq,
    opportunity_defaults,
    push_boq_to_costing_on_submit,
    update_opportunity_rate_on_cn_submit,
    get_boq_totals,
    make_quotation_with_standard,
)

# expose the new naming function under c4pricing.api.next_code
from .item_code_rules import next_code  # noqa: F401
from .item_group_filters import bounds   # noqa: F401
