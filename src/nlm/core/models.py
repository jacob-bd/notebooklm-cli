"""Pydantic models for NotebookLM data structures."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Notebook(BaseModel):
    """Represents a NotebookLM notebook."""

    id: str = Field(description="Unique notebook identifier")
    title: str = Field(default="Untitled", description="Notebook title")
    sources_count: int = Field(default=0, description="Number of sources")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    @property
    def short_id(self) -> str:
        """Return abbreviated ID for display."""
        if len(self.id) > 12:
            return f"{self.id[:8]}..."
        return self.id


class Source(BaseModel):
    """Represents a source within a notebook."""

    id: str = Field(description="Unique source identifier")
    title: str = Field(default="Untitled", description="Source title")
    type: str = Field(default="unknown", description="Source type (url, text, drive, youtube)")
    url: str | None = Field(default=None, description="Source URL if applicable")
    is_stale: bool = Field(default=False, description="Whether Drive source needs sync")

    @property
    def short_id(self) -> str:
        """Return abbreviated ID for display."""
        if len(self.id) > 12:
            return f"{self.id[:8]}..."
        return self.id


class SourceContent(BaseModel):
    """Raw content of a source."""

    content: str = Field(description="Raw text content")
    title: str = Field(default="", description="Source title")
    source_type: str = Field(default="", description="Type of source")
    char_count: int = Field(default=0, description="Character count")


class SourceSummary(BaseModel):
    """AI-generated summary of a source."""

    summary: str = Field(description="Markdown summary with bold keywords")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")


class NotebookSummary(BaseModel):
    """AI-generated summary of a notebook."""

    summary: str = Field(description="Markdown summary")
    suggested_topics: list[str] = Field(default_factory=list, description="Suggested topics")


class ChatConfig(BaseModel):
    """Chat configuration for a notebook."""

    goal: str = Field(default="default", description="Chat goal: default, learning_guide, custom")
    custom_prompt: str | None = Field(default=None, description="Custom prompt when goal=custom")
    response_length: str = Field(default="default", description="Response length: default, longer, shorter")


class QueryResponse(BaseModel):
    """Response from a notebook query."""

    response: str = Field(description="AI response text")
    conversation_id: str | None = Field(default=None, description="Conversation ID for follow-ups")
    citations: list[dict[str, Any]] = Field(default_factory=list, description="Source citations")


class AudioOverview(BaseModel):
    """Audio overview (podcast) artifact."""

    id: str = Field(description="Artifact ID")
    status: str = Field(description="Generation status")
    format: str = Field(default="deep_dive", description="Audio format")
    url: str | None = Field(default=None, description="Download URL when ready")
    duration: int | None = Field(default=None, description="Duration in seconds")


class StudioArtifact(BaseModel):
    """Generic studio artifact (report, quiz, etc.)."""

    id: str = Field(description="Artifact ID")
    type: str = Field(description="Artifact type")
    status: str = Field(description="Generation status")
    url: str | None = Field(default=None, description="Download/view URL")
    title: str | None = Field(default=None, description="Artifact title")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

    @property
    def short_id(self) -> str:
        """Return abbreviated ID for display."""
        if len(self.id) > 12:
            return f"{self.id[:8]}..."
        return self.id


class ResearchTask(BaseModel):
    """Research task status."""

    task_id: str = Field(description="Research task ID")
    status: str = Field(description="Task status: pending, running, completed, failed")
    sources_found: int = Field(default=0, description="Number of sources discovered")
    report: str | None = Field(default=None, description="Research report when complete")
    sources: list[dict[str, Any]] = Field(default_factory=list, description="Discovered sources")


class MindMap(BaseModel):
    """Mind map artifact."""

    id: str = Field(description="Mind map ID")
    title: str = Field(default="Mind Map", description="Mind map title")
    data: dict[str, Any] = Field(default_factory=dict, description="Mind map data structure")
