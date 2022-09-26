from ast import Assign, Constant, List, Module, Name

from .utils import generate_import_from


class InitFileGenerator:
    def __init__(self) -> None:
        self.imports: list = []

    def add_import(self, names: list[str], from_: str, level: int = 0) -> None:
        """Add import to be included in init file."""
        self.imports.append(generate_import_from(names=names, from_=from_, level=level))

    def generate(self) -> Module:
        """Generate init with imports and public api of package."""
        module = Module(body=self.imports, type_ignores=[])
        if self.imports:
            constants_names: list[str] = []
            for import_ in self.imports:
                constants_names.extend([n.name for n in import_.names])
            constants_names.sort()

            module.body.append(
                Assign(
                    targets=[
                        Name(
                            id="__all__",
                        )
                    ],
                    value=List(elts=[Constant(value=n) for n in constants_names]),
                    lineno=len(self.imports) + 1,
                )
            )
        return module
