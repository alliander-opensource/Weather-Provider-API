#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2019-2021 Alliander N.V.
#
# SPDX-License-Identifier: MPL-2.0

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)


def parse_datetime(
    datetime_string,
    round_missing_time_up=False,
    round_to_days=False,
    raise_errors=False,
    loc=None,
) -> Optional[datetime]:
    if datetime_string is None:
        return None

    dt = pd.to_datetime(datetime_string, dayfirst=True, errors="coerce")

    if pd.isnull(dt):
        logger.exception("Error while parsing datetime string", input=datetime_string)
        if raise_errors:
            # Note: replace when FastAPI supports Pydantic models to define query parameters
            # (meaning Validators can be used)
            error_msg = {
                "loc": loc,
                "msg": "invalid datetime format",
                "type": "type_error.datetime",
            }
            raise HTTPException(status_code=422, detail=[error_msg])

        dt = None

    if (
        dt is not None
        and (round_missing_time_up or round_to_days)
        and time_unknown(dt, datetime_string)
    ):
        if round_to_days:
            dt = dt + timedelta(days=1)
        else:
            dt = dt.replace(hour=23, minute=59, second=59)

    if dt is not None:
        dt = np.datetime64(dt).astype(datetime)

    return dt


def time_unknown(dt: datetime, datetime_string: str):  # pragma: no cover
    if (
        dt.hour == 0
        and dt.minute == 0
        and dt.second == 0
        and ":" not in datetime_string
    ):
        return True
    return False


def validate_begin_and_end(
    start: datetime,
    end: datetime,
    data_start: datetime = None,
    data_end: datetime = None,
):
    """
    Checks the given date parameters and replaces them with default values if they aren't valid.
    The resulting values are then returned.
    """
    if data_end is None:
        data_end = (
            datetime.utcnow()
        )  # Even predictions are made in the past, so no end time can lie in the future.

    # Ending time needs to be filled and is at most the repo ending time
    if end is None or end > data_end:
        end = data_end

    # Ending time needs to lie after the repo starting time as well!
    if data_start is not None and end <= data_start:
        end = data_start + timedelta(
            days=7
        )  # Set to a default of 7 days after the repo starting time

    # Starting time needs to be filled and has to lie before the ending time
    if start is None or start >= end:
        start = end - timedelta(
            days=7
        )  # Set to a default of 7 days before the ending time

    # Starting time needs to lie at least at the repo starting time if one is given
    if data_start is not None and start < data_start:
        start = data_start

    return start, end
