"""Strict public contracts. All character spans are half-open Unicode offsets."""
from __future__ import annotations
from datetime import date as ISODate
from enum import Enum
from hashlib import sha256
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator


def stable_id(kind: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{kind}_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EntityType(str, Enum):
    School = "School"
    Board = "Board"
    Circular = "Circular"
    Rule = "Rule"
    Locality = "Locality"
    Road = "Road"
    Date = "Date"
    Quantity = "Quantity"


class GeoPoint(StrictModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Span(StrictModel):
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class Mention(Span):
    chunk_id: str


class Attributes(StrictModel):
    date: ISODate | None = None
    count: int | None = Field(default=None, ge=0, strict=True)
    value: float | None = None
    unit: str | None = None
    location: GeoPoint | None = None
    osm_id: str | None = None
    board: str | None = None
    locality: str | None = None
    synthetic: bool = False


class Entity(StrictModel):
    id: str
    type: EntityType
    canonical_name: str = Field(min_length=1)
    mentions: list[Mention] = Field(default_factory=list)
    attributes: Attributes = Field(default_factory=Attributes)


class Chunk(Span):
    id: str
    document_id: str
    source: str
    page: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1)
    synthetic: bool = False
    board: str | None = None
    school_ids: list[str] = Field(default_factory=list)
    locations: list[GeoPoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def length_matches(self):
        if self.end - self.start != len(self.text):
            raise ValueError("chunk span length differs from text length")
        return self


class Relation(StrictModel):
    id: str
    source_id: str
    target_id: str
    type: str
    weight: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)
    method: str = Field(min_length=1)


class RankedResult(StrictModel):
    chunk_id: str
    score: float
    sources: list[str] = Field(default_factory=list)


class Citation(Span):
    chunk_id: str
    source: str
    page: int | None = None
    excerpt: str


class Answer(StrictModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    entities_used: list[str] = Field(default_factory=list)
