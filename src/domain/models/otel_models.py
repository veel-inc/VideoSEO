# Copyright (C) 2025 Veel Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExceptionLogData(BaseModel):
    type: str = Field(..., description="The type of exception")
    message: str = Field(..., description="The exception message")
    assembly: Optional[str] = Field(
        None, description="The assembly where the exception occurred"
    )
    method: Optional[str] = Field(
        None, description="The method where the exception occurred"
    )
    stack_trace: Optional[str] = Field(
        None, description="The full stack trace of the exception"
    )

    outer_type: Optional[str] = Field(
        None, description="The type of the outer exception"
    )
    outer_assembly: Optional[str] = Field(
        None, description="The assembly of the outer exception"
    )
    outer_message: Optional[str] = Field(
        None, description="The message of the outer exception"
    )
    outer_method: Optional[str] = Field(
        None, description="The method of the outer exception"
    )

    innermost_type: Optional[str] = Field(
        None, description="The type of the innermost exception"
    )
    innermost_assembly: Optional[str] = Field(
        None, description="The assembly of the innermost exception"
    )
    innermost_message: Optional[str] = Field(
        None, description="The message of the innermost exception"
    )
    innermost_method: Optional[str] = Field(
        None, description="The method of the innermost exception"
    )


class LogRecord(BaseModel):
    sequence: int = Field(..., description="The sequence number of the log record")
    timestamp: str | datetime = Field(
        ..., description="The timestamp when the log is created"
    )
    type: str = Field(default="logs", description="The type of the logs")
    message: str = Field(..., description="The log message content")
    level: int = Field(
        ..., description="The log level (e.g., Debug=0, Info=1, Warning=2, Error=3)"
    )
    event_id: int = Field(..., description="The event identifier for the log entry")
    trace_id: str = Field(
        default="", description="The trace identifier for distributed tracing"
    )
    span_id: str = Field(
        default="", description="The span identifier for distributed tracing"
    )
    xray: str = Field(default="", description="The X-Ray trace identifier")
    category_name: str = Field(..., description="The category name of the logger")
    exception: Optional[ExceptionLogData] = Field(
        None, description="Exception data if an exception occurred"
    )
