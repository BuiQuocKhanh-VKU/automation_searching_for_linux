from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


@dataclass(slots=True)
class JobResult:
    status: JobStatus
    account: str = ""
    stage: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {JobStatus.SUCCESS, JobStatus.SKIPPED}

    @classmethod
    def success(cls, account: str = "", stage: str = "", message: str = "") -> "JobResult":
        return cls(JobStatus.SUCCESS, account=account, stage=stage, message=message)

    @classmethod
    def cancelled(cls, account: str = "", stage: str = "", message: str = "Đã dừng theo yêu cầu") -> "JobResult":
        return cls(JobStatus.CANCELLED, account=account, stage=stage, message=message)

    @classmethod
    def failed(cls, account: str = "", stage: str = "", message: str = "") -> "JobResult":
        return cls(JobStatus.FAILED, account=account, stage=stage, message=message)


@dataclass(slots=True)
class RuntimeConfig:
    pc_count: int = 35
    mobile_count: int = 25
    check_interval: int = 3
    type_min: float = 0.3
    type_max: float = 0.3
    read_min: float = 3.0
    read_max: float = 4.0
    think_time: float = 3.0

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "RuntimeConfig":
        defaults = cls()
        cfg = cls(
            pc_count=int(values.get("pc_count", defaults.pc_count)),
            mobile_count=int(values.get("mobile_count", defaults.mobile_count)),
            check_interval=int(values.get("check_interval", defaults.check_interval)),
            type_min=float(values.get("type_min", defaults.type_min)),
            type_max=float(values.get("type_max", defaults.type_max)),
            read_min=float(values.get("read_min", defaults.read_min)),
            read_max=float(values.get("read_max", defaults.read_max)),
            think_time=float(values.get("think_time", defaults.think_time)),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        errors: list[str] = []
        if self.pc_count < 0:
            errors.append("PC Count phải >= 0")
        if self.mobile_count < 0:
            errors.append("Mobile Count phải >= 0")
        if self.check_interval < 1:
            errors.append("Interval phải >= 1")
        if self.type_min < 0 or self.type_max < 0:
            errors.append("Tốc độ gõ không được âm")
        if self.type_min > self.type_max:
            errors.append("Min Type không được lớn hơn Max Type")
        if self.read_min < 0 or self.read_max < 0:
            errors.append("Thời gian đọc không được âm")
        if self.read_min > self.read_max:
            errors.append("Min Read không được lớn hơn Max Read")
        if self.think_time < 1.0:
            errors.append("Thinking phải >= 1 giây")
        if errors:
            raise ValueError("; ".join(errors))

    def as_dict(self) -> dict[str, int | float]:
        return {
            "pc_count": self.pc_count,
            "mobile_count": self.mobile_count,
            "check_interval": self.check_interval,
            "type_min": self.type_min,
            "type_max": self.type_max,
            "read_min": self.read_min,
            "read_max": self.read_max,
            "think_time": self.think_time,
        }
