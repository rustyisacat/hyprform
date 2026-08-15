"""In-memory model for a hyprlang (.conf) document.

Every node keeps its original source line verbatim (``raw_line``) so a
document that hasn't been touched serializes back byte-for-byte. Editing a
node clears ``raw_line`` and the writer regenerates that one line from its
structured fields instead — everything else stays untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Blank:
    pass


@dataclass
class Comment:
    text: str
    raw_line: str


@dataclass
class KeyValue:
    key: str
    value: str
    indent: str = ""
    raw_line: str | None = None

    def touch(self, new_value: str) -> None:
        self.value = new_value
        self.raw_line = None


@dataclass
class Block:
    name: str
    indent: str = ""
    raw_header: str | None = None
    raw_footer: str | None = None
    children: list = field(default_factory=list)

    def find_block(self, name: str) -> "Block | None":
        for child in self.children:
            if isinstance(child, Block) and child.name == name:
                return child
        return None

    def find_all(self, key: str) -> list[KeyValue]:
        return [c for c in self.children if isinstance(c, KeyValue) and c.key == key]

    def find_first(self, key: str) -> KeyValue | None:
        for c in self.children:
            if isinstance(c, KeyValue) and c.key == key:
                return c
        return None


Node = Blank | Comment | KeyValue | Block


@dataclass
class Document:
    path: str
    root: Block
