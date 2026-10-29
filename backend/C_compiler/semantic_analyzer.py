from lexer import Lexer, LexerError
from parser import Parser, ParserError
class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]
        self.functions = {}
        self.current_return_type = None
    def declare_variable(self, name, data_type):
        current_scope = self.scopes[-1]

        if name in current_scope:
            raise SemanticError(
                f"Variable '{name}' is already declared."
            )

        current_scope[name] = data_type

    def is_declared(self, name):
        
        
        for scope in reversed(self.scopes):
            if name in scope:
                return True

        return False

    def get_literal_type(self, value):
        value = str(value)

        if value.startswith('"') and value.endswith('"'):
            return "string"

        if value.startswith("'") and value.endswith("'"):
            return "char"

        if "." in value:
            return "float"

        return "int"

    
    def get_expression_type(self, node):
        if node.type == "Literal":
            return self.get_literal_type(node.value)

        elif node.type == "Identifier":
            for scope in reversed(self.scopes):
                if node.value in scope:
                    return scope[node.value]

            raise SemanticError(
                f"Variable '{node.value}' is not declared."
            )

        elif node.type == "FunctionCall":
            if node.value == "printf":
                for argument in node.children:
                    self.get_expression_type(argument)
                return "int"

            if node.value not in self.functions:
                raise SemanticError(
                    f"Function '{node.value}' is not declared."
                )

            function = self.functions[node.value]
            expected_parameters = function["parameters"]

            if len(node.children) != len(expected_parameters):
                raise SemanticError(
                    f"Function '{node.value}' expects "
                    f"{len(expected_parameters)} arguments, "
                    f"but got {len(node.children)}."
                )

            for argument, expected_type in zip(
                node.children, expected_parameters
            ):
                actual_type = self.get_expression_type(argument)

                if (
                    actual_type != expected_type
                    and not (
                        actual_type in {"int", "float", "double"}
                        and expected_type in {"int", "float", "double"}
                    )
                ):
                    raise SemanticError(
                        f"Type mismatch in argument to function "
                        f"'{node.value}': expected '{expected_type}', "
                        f"but got '{actual_type}'."
                    )

            return function["return_type"]

        elif node.type == "BinaryOperation":
            operator = node.value
            left_type = self.get_expression_type(node.children[0])
            right_type = self.get_expression_type(node.children[1])

            if operator in {"=", "+=", "-=", "*=", "/=", "%="}:
                left = node.children[0]
                right = node.children[1]

                if left.type != "Identifier":
                    raise SemanticError(
                        "The left side of an assignment must be a variable."
                    )

                if operator == "=":
                    if (
                        left_type != right_type
                        and not (
                            left_type in {"int", "float", "double"}
                            and right_type in {"int", "float", "double"}
                        )
                    ):
                        raise SemanticError(
                            f"Type mismatch in assignment: expected "
                            f"'{left_type}', but got '{right_type}'."
                        )

                elif not (
                    left_type in {"int", "float", "double"}
                    and right_type in {"int", "float", "double"}
                ):
                    raise SemanticError(
                        f"Operator '{operator}' requires numeric operands."
                    )

                return left_type

            if operator in {
                "==", "!=", "<", ">", "<=", ">=", "&&", "||"
            }:
                numeric_types = {"int", "float", "double"}

                if operator in {"<", ">", "<=", ">="}:
                    if (
                        left_type not in numeric_types
                        or right_type not in numeric_types
                    ):
                        raise SemanticError(
                            f"Operator '{operator}' requires numeric operands."
                        )

                return "int"
            if operator in {"+", "-", "*", "/", "%"}:
                numeric_types = {"int", "float", "double"}

                if (
                    left_type not in numeric_types
                    or right_type not in numeric_types
                ):
                    raise SemanticError(
                        f"Operator '{operator}' requires numeric operands."
                    )

                if operator == "%" and (
                    left_type != "int" or right_type != "int"
                ):
                    raise SemanticError(
                        "Operator '%' requires integer operands."
                    )

            if left_type in {"float", "double"} or right_type in {
                "float", "double"
            }:
                return "double" if "double" in {
                    left_type, right_type
                } else "float"

            return "int"

        elif node.type == "UnaryOperation":
            return self.get_expression_type(node.children[0])

        return None


    def analyze(self, node):
        
        if node.type == "Program":
            for child in node.children:
                if child.type == "Function":
                    name = child.value["name"]

                    if name in self.functions:
                        raise SemanticError(
                            f"Function '{name}' is already declared."
                        )

                    parameter_types = [
                        item.value
                        for item in child.children
                        if item.type == "Parameter"
                    ]

                    self.functions[name] = {
                        "return_type": child.value["return_type"],
                        "parameters": parameter_types
                    }

            for child in node.children:
                self.analyze(child)

        elif node.type == "Function":
            self.scopes.append({})
            previous_return_type = self.current_return_type
            self.current_return_type = node.value["return_type"]

            try:
                for child in node.children:
                    if child.type == "Parameter":
                        name = child.children[0].value
                        self.declare_variable(name, child.value)

                    elif child.type == "Block":
                        self.analyze(child)
            finally:
                self.current_return_type = previous_return_type
                self.scopes.pop()

        elif node.type == "Block":
            self.scopes.append({})

            try:
                for child in node.children:
                    self.analyze(child)
            finally:
                self.scopes.pop()

        elif node.type == "DeclarationList":
            for declaration in node.children:
                self.analyze(declaration)

        elif node.type == "VariableDeclaration":
            name = node.children[0].value
            data_type = node.value

            self.declare_variable(name, data_type)

            if len(node.children) > 1:
                actual_type = self.get_expression_type(
                    node.children[1]
                )

                if data_type not in {"int", "float", "double"} or actual_type not in {
                    "int", "float", "double"
                }:
                    if data_type != actual_type:
                        raise SemanticError(
                            f"Type mismatch in initialization of variable "
                            f"'{name}': expected '{data_type}', "
                            f"but got '{actual_type}'."
                        )
        
        elif node.type == "FunctionCall":
            if node.value == "printf":
                for argument in node.children:
                    self.get_expression_type(argument)
                return "int"

            if node.value not in self.functions:
                raise SemanticError(
                    f"Function '{node.value}' is not declared."
                )

            function = self.functions[node.value]
            expected_parameters = function["parameters"]

            if len(node.children) != len(expected_parameters):
                raise SemanticError(
                    f"Function '{node.value}' expects "
                    f"{len(expected_parameters)} arguments, "
                    f"but got {len(node.children)}."
                )

            for argument, expected_type in zip(
                node.children, expected_parameters
            ):
                actual_type = self.get_expression_type(argument)

                if (
                    actual_type != expected_type
                    and not (
                        actual_type in {"int", "float", "double"}
                        and expected_type in {"int", "float", "double"}
                    )
                ):
                    raise SemanticError(
                        f"Type mismatch in argument to function "
                        f"'{node.value}': expected '{expected_type}', "
                        f"but got '{actual_type}'."
                    )

            return function["return_type"]

        elif node.type == "Identifier":
            if not self.is_declared(node.value):
                raise SemanticError(
                    f"Variable '{node.value}' is not declared."
                )

        elif node.type == "Return":
            if self.current_return_type == "void" and node.children:
                raise SemanticError(
                    "Void function cannot return a value."
                )

            if self.current_return_type != "void" and not node.children:
                raise SemanticError(
                    f"Function returning '{self.current_return_type}' "
                    "must return a value."
                )

            if node.children:
                expression = node.children[0]

                if expression.type == "Literal":
                    literal_type = self.get_literal_type(
                        expression.value
                    )

                    if (
                        self.current_return_type in {
                            "int", "float", "double"
                        }
                        and literal_type in {"string", "char"}
                    ):
                        raise SemanticError(
                            f"Cannot return '{literal_type}' "
                            f"from a function returning "
                            f"'{self.current_return_type}'."
                        )

                self.analyze(expression) 

    def analyze(self, node):
        if node.type == "Program":
            for child in node.children:
                if child.type == "Function":
                    name = child.value["name"]

                    if name in self.functions:
                        raise SemanticError(
                            f"Function '{name}' is already declared."
                        )

                    parameter_types = [
                        item.value
                        for item in child.children
                        if item.type == "Parameter"
                    ]

                    self.functions[name] = {
                        "return_type": child.value["return_type"],
                        "parameters": parameter_types
                    }

            for child in node.children:
                self.analyze(child)

        elif node.type == "Function":
            self.scopes.append({})
            previous_return_type = self.current_return_type
            self.current_return_type = node.value["return_type"]

            try:
                for child in node.children:
                    if child.type == "Parameter":
                        name = child.children[0].value
                        self.declare_variable(name, child.value)

                    elif child.type == "Block":
                        self.analyze(child)
            finally:
                self.current_return_type = previous_return_type
                self.scopes.pop()

        elif node.type == "Block":
            self.scopes.append({})
            try:
                for child in node.children:
                    self.analyze(child)
            finally:
                self.scopes.pop()

        elif node.type == "DeclarationList":
            for child in node.children:
                self.analyze(child)

        elif node.type == "VariableDeclaration":
            name = node.children[0].value
            data_type = node.value
            self.declare_variable(name, data_type)

            if len(node.children) > 1:
                actual_type = self.get_expression_type(
                    node.children[1]
                )

                if (
                    data_type != actual_type
                    and not (
                        data_type in {"int", "float", "double"}
                        and actual_type in {"int", "float", "double"}
                    )
                ):
                    raise SemanticError(
                        f"Type mismatch in initialization of variable "
                        f"'{name}': expected '{data_type}', "
                        f"but got '{actual_type}'."
                    )

        elif node.type == "FunctionCall":
            self.get_expression_type(node)

        elif node.type == "Identifier":
           self.get_expression_type(node)

        elif node.type == "Return":
            if self.current_return_type == "void":
                if node.children:
                    raise SemanticError(
                        "Void function cannot return a value."
                    )
                return

            if not node.children:
                raise SemanticError(
                    f"Function returning '{self.current_return_type}' "
                    "must return a value."
                )

            actual_type = self.get_expression_type(node.children[0])

            if (
                actual_type != self.current_return_type
                and not (
                    actual_type in {"int", "float", "double"}
                    and self.current_return_type
                    in {"int", "float", "double"}
                )
            ):
                raise SemanticError(
                    f"Type mismatch in return statement: expected "
                    f"'{self.current_return_type}', but got "
                    f"'{actual_type}'."
                )

        elif node.type == "If":
            if node.children:
                condition_type = self.get_expression_type(
                    node.children[0]
                )

                if condition_type not in {
                    "int", "float", "double", "char"
                }:
                    raise SemanticError(
                        "If condition must be numeric or character type."
                    )

            for child in node.children[1:]:
                self.analyze(child)

        elif node.type == "While":
            if node.children:
                condition_type = self.get_expression_type(
                    node.children[0]
                )

                if condition_type not in {
                    "int", "float", "double", "char"
                }:
                    raise SemanticError(
                        "While condition must be numeric or character type."
                    )

            for child in node.children[1:]:
                self.analyze(child)

        elif node.type == "DoWhile":
            if node.children:
                for child in node.children[:-1]:
                    self.analyze(child)

                condition_type = self.get_expression_type(
                    node.children[-1]
                )

                if condition_type not in {
                    "int", "float", "double", "char"
                }:
                    raise SemanticError(
                        "Do-while condition must be numeric or character type."
                    )

        elif node.type == "For":
            self.scopes.append({})
            try:
                for child in node.children:
                    self.analyze(child)
            finally:
                self.scopes.pop()

        elif node.type == "ExpressionStatement":
            if node.children:
                self.get_expression_type(node.children[0])

        elif node.type == "BinaryOperation":
            self.get_expression_type(node)

        elif node.type == "Literal":
            return

        else:
            for child in node.children:
                self.analyze(child)

if __name__ == "__main__": 
 sample_code = """
int main() {
    int age = 20;
    int result = age + 10;
    return result;
}
"""
try:
        tokens = Lexer(sample_code).tokenize()
        ast = Parser(tokens).parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        print("SEMANTIC ANALYSIS SUCCESSFUL")
except (LexerError, ParserError, SemanticError) as error:
        print("COMPILER ERROR:", error)
