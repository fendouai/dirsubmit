"""数据模型：产品、目录食谱、提交记录、文案。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Product:
    name: str
    url: str
    tagline: str = ""
    description: str = ""
    features: List[str] = field(default_factory=list)
    pricing: str = ""
    categories: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    logo_url: str = ""
    email: str = ""
    twitter: str = ""


@dataclass
class FieldSpec:
    name: str
    type: str = "text"  # text | textarea | select | url | email | checkbox
    required: bool = False
    source: str = ""  # product field or ai.*
    selectors: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)  # for select/checkbox hints
    submit: bool = False  # true = this element is the submit button
    file_path: str = ""  # for type=file: local file to upload


@dataclass
class Recipe:
    slug: str
    name: str
    submit_url: str = ""
    homepage: str = ""
    dr: int = 0
    tier: str = "manual"  # auto | semi | manual
    requires_auth: bool = False
    verify: dict = field(default_factory=dict)
    fields: List[FieldSpec] = field(default_factory=list)
    submit_selector: str = ""
    wait_ms: int = 0


@dataclass
class Copy:
    directory: str
    tagline: str = ""
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class Submission:
    directory: str
    tier: str
    status: str = "pending"  # pending|submitted|approved|rejected|failed|manual
    submitted_at: Optional[str] = None
    last_checked_at: Optional[str] = None
    live_url: str = ""
    note: str = ""
