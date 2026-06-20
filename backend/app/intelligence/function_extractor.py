import ast

from backend.app.schemas.intelligence import FunctionInfo

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def extract_function(node: FunctionNode) -> FunctionInfo:
    arguments = node.args
    args = [argument.arg for argument in (*arguments.posonlyargs, *arguments.args)]
    if arguments.vararg:
        args.append(f"*{arguments.vararg.arg}")
    args.extend(argument.arg for argument in arguments.kwonlyargs)
    if arguments.kwarg:
        args.append(f"**{arguments.kwarg.arg}")

    return FunctionInfo(
        name=node.name,
        line_number=node.lineno,
        args=args,
        decorators=[ast.unparse(decorator) for decorator in node.decorator_list],
        is_async=isinstance(node, ast.AsyncFunctionDef),
    )


def extract_functions(tree: ast.Module) -> list[FunctionInfo]:
    return [
        extract_function(node)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
