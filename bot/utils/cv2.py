# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║            © 2026 Arsh — All Rights Reserved                     ║
# ║                                                                  ║
# ║            Built by  ──  Arsh                                    ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

"""
Shared CV2 (Component V2) utilities for the bot.
Provides a helper to build Container objects since Container()
does NOT accept positional children arguments — items must be
added via .add_item().
"""

import discord
from discord.ui import LayoutView, TextDisplay, Separator, Container, Thumbnail, Section


def build_container(*items, accent_color=None):
    """Build a Container and add items to it via .add_item()."""
    container = Container(accent_color=accent_color)
    for item in items:
        container.add_item(item)
    return container


class CV2(LayoutView):
    """Quick helper: CV2("Title", "section1", "section2", ...)

    Optional kwargs:
        author      → str  : name shown next to the avatar (defaults to title)
        avatar_url  → str  : URL of the avatar/thumbnail to show in the header
        accent      → int  : hex color for the container accent (e.g. 0xFF0000)
    """
    def __init__(self, title, *sections, author=None, avatar_url=None, accent=None):
        super().__init__(timeout=None)
        container_items = []

        # Header: if we have an avatar, build a Section with the title text
        # on the left and the avatar Thumbnail as the accessory on the right.
        # If no avatar, just a plain TextDisplay.
        if avatar_url:
            container_items.append(
                Section(
                    TextDisplay(f"**{title}**"),
                    accessory=Thumbnail(
                        media=avatar_url,
                        description=author or title,
                    ),
                )
            )
        else:
            container_items.append(TextDisplay(f"**{title}**"))

        # Body sections
        body_items = [item for s in sections for item in (Separator(visible=True), TextDisplay(str(s)))]
        container = build_container(*container_items, *body_items, accent_color=accent)
        self.add_item(container)

def add_action_rows(container, components):
    """Safely adds components to a CV2 container across multiple ActionRows"""
    from discord.ui import ActionRow
    current_row = []
    for item in components:
        if getattr(item, 'type', None) and getattr(item.type, 'value', 0) != 2:
            if current_row:
                container.add_item(ActionRow(*current_row))
                current_row = []
            container.add_item(ActionRow(item))
        else:
            current_row.append(item)
            if len(current_row) == 5:
                container.add_item(ActionRow(*current_row))
                current_row = []
    if current_row:
        container.add_item(ActionRow(*current_row))

class CV2Embed(CV2):
    """A CV2 container that behaves like a discord.Embed."""
    def __init__(self, title="", description="", **kwargs):
        self._title = title
        self._description = description or ""
        self._fields = []
        self._footer = None
        super().__init__(title, self._description)
        self.color = kwargs.get("color", 0xFF0000)
    
    def _rebuild(self):
        self.clear_items()
        sections = [self._description] if self._description else []
        for name, value in self._fields:
            sections.append(f"**{name}**\n{value}")
        
        if self._footer:
            sections.append(f"*{self._footer}*")
            
        container = build_container(
            TextDisplay(f"**{self._title}**"),
            *[item for s in sections for item in (Separator(visible=True), TextDisplay(str(s)))]
        )
        self.add_item(container)

    def add_field(self, name, value, inline=False, **kwargs):
        self._fields.append((name, value))
        self._rebuild()
        return self

    def set_footer(self, text=None, icon_url=None, **kwargs):
        if text:
            self._footer = text
            self._rebuild()
        return self
        
    def set_thumbnail(self, url=None, **kwargs):
        return self
        
    def set_author(self, name=None, url=None, icon_url=None, **kwargs):
        return self
        
    def set_image(self, url=None, **kwargs):
        return self
        
    def to_dict(self):
        return {"title": self._title, "description": self._description}
