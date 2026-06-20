from backend.app.intelligence.class_extractor import extract_classes
from backend.app.intelligence.function_extractor import extract_functions
from backend.app.intelligence.import_extractor import extract_imports
from backend.app.intelligence.python_ast_parser import ParsedPythonFile
from backend.app.schemas.intelligence import PythonFileSymbols


def index_parsed_file(parsed_file: ParsedPythonFile) -> PythonFileSymbols:
    if parsed_file.tree is None:
        raise ValueError("Cannot index a Python file that failed to parse")
    return PythonFileSymbols(
        path=parsed_file.path,
        imports=extract_imports(parsed_file.tree),
        functions=extract_functions(parsed_file.tree),
        classes=extract_classes(parsed_file.tree),
    )
