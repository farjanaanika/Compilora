from dataclasses import dataclass, field
from lexer import Lexer, LexerError
class ParserError(Exception):
    pass
@dataclass
class ASTNode:
    type: str
    value: object = None
    children: list = field(default_factory=list)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def current(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def check(self, value):
        token = self.current()
        return token is not None and token.value == value

    def advance(self):
        token = self.current()
        if token is not None:
            self.position += 1
        return token

    def expect(self, value):
        if not self.check(value):
            token = self.current()
            if token is None:
                raise ParserError(
                    f"Expected {value!r}, but reached end of input."
                )
            raise ParserError(
                f"Expected {value!r} at line {token.line}, "
                f"column {token.column}, but found {token.value!r}."
            )
        return self.advance()

    def expect_identifier(self):
        token = self.current()
        if token is None or token.type != "IDENTIFIER":
            if token is None:
                raise ParserError("Expected an identifier at end of input.")
            raise ParserError(
                f"Expected an identifier at line {token.line}, "
                f"column {token.column}."
            )
        return self.advance()

    def parse(self):
        children = []
        while self.current() is not None:
            children.append(self.parse_statement())
        return ASTNode("Program", children=children)

    def parse_statement(self):
        token = self.current()

        if token is None:
            raise ParserError("Unexpected end of input.")

        if self.check("{"):
            return self.parse_block()

        if self.check("if"):
            return self.parse_if()

        if self.check("for"):
            return self.parse_for()

        if self.check("while"):
            return self.parse_while()

        if self.check("do"):
            return self.parse_do_while()

        if self.check("return"):
            return self.parse_return()

        if self.check("break") or self.check("continue"):
            value = self.advance().value
            self.expect(";")
            return ASTNode(value.capitalize())

        if self.check(";"):
            self.advance()
            return ASTNode("EmptyStatement")

        if token.type == "KEYWORD" and token.value in {
            "int", "float", "double", "char", "void"
        }:
            if (
                self.position + 2 < len(self.tokens)
                and self.tokens[self.position + 2].value == "("
            ):
                return self.parse_function()

            if token.value == "void":
                raise ParserError(
                    "Expected a function declaration after 'void'."
                )

            return self.parse_variable_declaration()

        expression = self.parse_expression()
        self.expect(";")
        return ASTNode("ExpressionStatement", children=[expression])

    def parse_block(self):
        self.expect("{")
        children = []

        while self.current() is not None and not self.check("}"):
            children.append(self.parse_statement())

        self.expect("}")
        return ASTNode("Block", children=children)

    def parse_function(self):
        return_type = self.advance().value
        name = self.expect_identifier().value
        self.expect("(")
        parameters = []

        if not self.check(")"):
            while True:
                token = self.current()
                if token is None or token.value not in {
                    "int", "float", "double", "char", "void"
                }:
                    raise ParserError("Expected a parameter data type.")

                parameter_type = self.advance().value
                parameter_name = self.expect_identifier().value
                parameters.append(
                    ASTNode(
                        "Parameter",
                        parameter_type,
                        [ASTNode("Identifier", parameter_name)]
                    )
                )

                if not self.check(","):
                    break
                self.advance()

        self.expect(")")
        children = parameters

        if self.check("{"):
            children.append(self.parse_block())
        else:
            self.expect(";")

        return ASTNode(
            "Function",
            {"name": name, "return_type": return_type},
            children
        )

    def parse_variable_declaration(self, expect_semicolon=True):
        data_type = self.advance().value
        declarations = []

        while True:
            name = self.expect_identifier().value
            children = [ASTNode("Identifier", name)]

            if self.check("="):
                self.advance()
                children.append(self.parse_expression())

            declarations.append(
                ASTNode("VariableDeclaration", data_type, children)
            )

            if not self.check(","):
                break
            self.advance()

        if expect_semicolon:
            self.expect(";")

        return ASTNode("DeclarationList", children=declarations)

    def parse_if(self):
        self.expect("if")
        self.expect("(")
        condition = self.parse_expression()
        self.expect(")")
        children = [condition, self.parse_statement()]

        if self.check("else"):
            self.advance()
            children.append(self.parse_statement())

        return ASTNode("If", children=children)

    def parse_for(self):
        self.expect("for")
        self.expect("(")
        initialization = None
        condition = None
        update = None

        if not self.check(";"):
            token = self.current()
            if token and token.type == "KEYWORD" and token.value in {
                "int", "float", "double", "char"
            }:
                initialization = self.parse_variable_declaration(False)
            else:
                initialization = self.parse_expression()

        self.expect(";")

        if not self.check(";"):
            condition = self.parse_expression()

        self.expect(";")

        if not self.check(")"):
            update = self.parse_expression()

        self.expect(")")
        body = self.parse_statement()

        children = [
            node for node in
            [initialization, condition, update, body]
            if node is not None
        ]

        return ASTNode("For", children=children)

    def parse_while(self):
        self.expect("while")
        self.expect("(")
        condition = self.parse_expression()
        self.expect(")")
        body = self.parse_statement()
        return ASTNode("While", children=[condition, body])

    def parse_do_while(self):
        self.expect("do")
        body = self.parse_statement()
        self.expect("while")
        self.expect("(")
        condition = self.parse_expression()
        self.expect(")")
        self.expect(";")
        return ASTNode("DoWhile", children=[body, condition])

    def parse_return(self):
        self.expect("return")
        children = []

        if not self.check(";"):
            children.append(self.parse_expression())

        self.expect(";")
        return ASTNode("Return", children=children)

    def parse_expression(self, minimum_precedence=1):
        precedence = {
            "=": 1, "+=": 1, "-=": 1,
            "*=": 1, "/=": 1, "%=": 1,
            "||": 2, "&&": 3,
            "==": 4, "!=": 4,
            "<": 5, ">": 5, "<=": 5, ">=": 5,
            "+": 6, "-": 6,
            "*": 7, "/": 7, "%": 7,
        }

        left = self.parse_unary()

        while self.current() is not None:
            operator = self.current().value
            if operator not in precedence:
                break

            current_precedence = precedence[operator]
            if current_precedence < minimum_precedence:
                break

            self.advance()
            next_precedence = (
                current_precedence
                if current_precedence == 1
                else current_precedence + 1
            )
            right = self.parse_expression(next_precedence)
            left = ASTNode(
                "BinaryOperation", operator, [left, right]
            )

        return left

    def parse_unary(self):
        if self.check("+") or self.check("-") or self.check("!"):
            operator = self.advance().value
            return ASTNode(
                "UnaryOperation", operator, [self.parse_unary()]
            )

        if self.check("&") or self.check("*"):
            operator = self.advance().value
            return ASTNode(
                "UnaryOperation", operator, [self.parse_unary()]
            )

        if self.check("++") or self.check("--"):
            operator = self.advance().value
            return ASTNode(
                "UnaryOperation",
                "prefix " + operator,
                [self.parse_unary()]
            )

        node = self.parse_primary()

        while self.check("++") or self.check("--"):
            operator = self.advance().value
            node = ASTNode(
                "UnaryOperation", "postfix " + operator, [node]
            )

        return node

    def parse_primary(self):
        token = self.current()

        if token is None:
            raise ParserError("Unexpected end of input in expression.")

        if self.check("("):
            self.advance()
            expression = self.parse_expression()
            self.expect(")")
            return expression

        if token.type in {"NUMBER", "STRING", "CHAR", "CHARACTER"}:
            self.advance()
            return ASTNode("Literal", token.value)

        if token.type == "IDENTIFIER":
            name = self.advance().value
            identifier = ASTNode("Identifier", name)

            if self.check("("):
                self.advance()
                arguments = []

                if not self.check(")"):
                    arguments.append(self.parse_expression())
                    while self.check(","):
                        self.advance()
                        arguments.append(self.parse_expression())

                self.expect(")")
                return ASTNode("FunctionCall", name, arguments)

            return identifier

        raise ParserError(
            f"Unexpected token {token.value!r} at line {token.line}, "
            f"column {token.column}."
        )


def print_ast(node, level=0):
    indent = "  " * level
    print(
        f"{indent}{node.type}: "
        f"{node.value if node.value is not None else ''}"
    )
    for child in node.children:
        print_ast(child, level + 1)


if __name__ == "__main__":
    sample_code = """
    int main() {
        int age = 20;
        age = 25;
        for (int i = 0; i < 3; i++) {
            age = age + 1;
        }
        return 0;
    }
    """

    try:
        tokens = Lexer(sample_code).tokenize()
        ast = Parser(tokens).parse()
        print("SYNTAX ANALYSIS SUCCESSFUL")
        print("\nABSTRACT SYNTAX TREE")
        print_ast(ast)
    except (LexerError, ParserError) as error:
        print("COMPILER ERROR:", error)
