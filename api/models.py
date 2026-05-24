"""api/models.py — Pydantic request and response models for the API."""

from pydantic import BaseModel, Field


class OrderInput(BaseModel):
    """Order payload accepted by POST /score and POST /orders."""
    vendor_is_new:                bool
    vendor_cluster:               str
    vendor_reliability:           float = Field(ge=0.0, le=1.0)
    fabric_type:                  str
    order_qty:                    int = Field(ge=1)
    destination_city:             str = ""
    destination_tier:             str
    payment_mode:                 str
    season:                       str
    vendor_id:                    str = ""
    # v2 upstream operational features — default to best-case at order time
    sampling_delay_days:          int = 0
    fabric_arrival_delay_days:    int = 0
    trims_confirmation_lag_days:  int = 0
    factory_ncr_count:            int = 0
    buyer_change_frequency:       int = Field(default=1, ge=1, le=3)


class ScoreOutput(BaseModel):
    """Rule scorer's output, plus risk bands."""
    delay_score:    int
    return_score:   int
    delay_band:     str
    return_band:    str
    delay_reasons:  list[str]
    return_reasons: list[str]


class HybridScoreOutput(BaseModel):
    """Hybrid (rule + ML) output — components, blend, and disagreement flags."""
    rule_delay:     float
    ml_delay:       float
    hybrid_delay:   float
    rule_return:    float
    ml_return:      float
    hybrid_return:  float
    delay_reasons:  list[str]
    return_reasons: list[str]
    agree_delay:    bool
    agree_return:   bool


class OrderOut(BaseModel):
    """Order representation returned by /orders endpoints."""
    po_id:                       str
    po_date:                     str
    vendor_is_new:               bool
    vendor_cluster:              str
    vendor_reliability:          float
    fabric_type:                 str
    order_qty:                   int
    destination_tier:            str
    payment_mode:                str
    season:                      str
    sampling_delay_days:         int
    fabric_arrival_delay_days:   int
    trims_confirmation_lag_days: int
    factory_ncr_count:           int
    buyer_change_frequency:      int
    delay_score:                 int | None = None
    return_score:                int | None = None
    is_delayed:                  bool | None = None
    is_returned:                 bool | None = None


class OutcomeInput(BaseModel):
    """Realised outcome captured after the order completes."""
    is_delayed:  bool
    is_returned: bool
