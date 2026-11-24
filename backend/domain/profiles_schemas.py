from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StringConstraints

class FitCurve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coupon: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    penalty: FiniteFloat


class SweepCurve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coupon: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    penalties: Annotated[list[FiniteFloat], Field(min_length=2, max_length=8)]


class SignProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
