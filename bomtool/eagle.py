import typing

from .bom import *

class EagleReader:
    sch: str
    brd: str

    def __init__(self, sch: str, brd: str) -> None:
        self.sch = sch
        self.brd = brd

    def __call__(self) -> typing.Generator[Part, None, None]:
        raise NotImplementedError("todo")

class EagleWriter:
    sch: str
    brd: str

    def __init__(self, sch: str, brd: str) -> None:
        self.sch = sch
        self.brd = brd

    def __call__(self) -> typing.Generator[Part, None, None]:
        raise NotImplementedError("todo")
