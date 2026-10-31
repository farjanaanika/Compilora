from lexer import Lexer, LexerError
class ParserError(Exception):
    pass


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
        while self.current() is not None:
            self.parse_statement()

        return True

    def parse_statement(self):
        token = self.current()

        if token is None:
            return

        if self.check("{"):
            self.parse_block()
        elif self.check("if"):
            self.parse_if()
        elif self.check("for"):
            self.parse_for()
        elif self.check("while"):
            self.parse_while()
        elif self.check("do"):
            self.parse_do_while()
        elif self.check("return"):
            self.parse_return()
        elif self.check("break") or self.check("continue"):
            self.advance()
            self.expect(";")
        elif self.check(";"):
            self.advance()
        elif token.type == "KEYWORD" and token.value in {
            "int", "float", "double", "char", "void"
        }:
            if (
                token.value == "void"
                or (
                    self.position + 2 < len(self.tokens)
                    and self.tokens[self.position + 2].value == "("
                )
            ):
                self.parse_declaration()
            else:
                self.parse_variable_declaration()
        else:
            self.parse_expression()
            self.expect(";")

    def parse_block(self):
        self.expect("{")

        while self.current() is not None and not self.check("}"):
            self.parse_statement()

        self.expect("}")

    def parse_declaration(self):
        self.advance()
        self.expect_identifier()

        if self.check("("):
            self.advance()

            if not self.check(")"):
                while True:
                    token = self.current()

                    if token is None or token.value not in {
                        "int", "float", "double", "char", "void"
                    }:
                        raise ParserError("Expected a parameter data type.")

                    self.advance()
                    self.expect_identifier()

                    if not self.check(","):
                        break

                    self.advance()

            self.expect(")")

            if self.check("{"):
                self.parse_block()
            else:
                self.expect(";")

            return

        if self.check("="):
            self.advance()
            self.parse_expression()

        while self.check(","):
            self.advance()
            self.expect_identifier()

            if self.check("="):
                self.advance()
                self.parse_expression()

        self.expect(";")

    def parse_variable_declaration(self, expect_semicolon=True):
        self.advance()
        self.expect_identifier()

        if self.check("="):
            self.advance()
            self.parse_expression()

        while self.check(","):
            self.advance()
            self.expect_identifier()

            if self.check("="):
                self.advance()
                self.parse_expression()

        if expect_semicolon:
            self.expect(";")

    def parse_if(self):
        self.expect("if")
        self.expect("(")
        self.parse_expression()
        self.expect(")")
        self.parse_statement()

        if self.check("else"):
            self.advance()
            self.parse_statement()

    def parse_for(self):
        self.expect("for")
        self.expect("(")

        if not self.check(";"):
            token = self.current()

            if token and token.type == "KEYWORD" and token.value in {
                "int", "float", "double", "char"
            }:
                self.parse_variable_declaration(False)
            else:
                self.parse_expression()

        self.expect(";")

        if not self.check(";"):
            self.parse_expression()

        self.expect(";")

        if not self.check(")"):
            self.parse_expression()

        self.expect(")")
        self.parse_statement()

    def parse_while(self):
        self.expect("while")
        self.expect("(")
        self.parse_expression()
        self.expect(")")
        self.parse_statement()

    def parse_do_while(self):
        self.expect("do")
        self.parse_statement()
        self.expect("while")
        self.expect("(")
        self.parse_expression()
        self.expect(")")
        self.expect(";")

    def parse_return(self):
        self.expect("return")

        if not self.check(";"):
            self.parse_expression()

        self.expect(";")

    def parse_expression(self, minimum_precedence=1):
        precedence = {
            "=": 1, "+=": 1, "-=": 1,
            "*=": 1, "/=": 1, "%=": 1,
            "||": 2,
            "&&": 3,
            "==": 4, "!=": 4,
            "<": 5, ">": 5, "<=": 5, ">=": 5,
            "+": 6, "-": 6,
            "*": 7, "/": 7, "%": 7,
        }

        self.parse_unary()

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

            self.parse_expression(next_precedence)

    def parse_unary(self):
        if self.check("+") or self.check("-") or self.check("!"):
            self.advance()
            self.parse_unary()
            return

        if self.check("&") or self.check("*"):
            self.advance()
            self.parse_unary()
            return

        if self.check("++") or self.check("--"):
            self.advance()
            self.parse_unary()
            return

        self.parse_primary()

        while self.check("++") or self.check("--"):
            self.advance()

    def parse_primary(self):
        token = self.current()

        if token is None:
            raise ParserError("Unexpected end of input in expression.")

        if self.check("("):
            self.advance()
            self.parse_expression()
            self.expect(")")
            return

        if token.type in {"NUMBER", "STRING", "CHAR"}:
            self.advance()
            return

        if token.type == "IDENTIFIER":
            self.advance()

            if self.check("("):
                self.advance()

                if not self.check(")"):
                    self.parse_expression()

                    while self.check(","):
                        self.advance()
                        self.parse_expression()

                self.expect(")")

            return

        raise ParserError(
            f"Unexpected token {token.value!r} at line {token.line}, "
            f"column {token.column}."
        )


if __name__ == "__main__":
    sample_code = """
    int main() {
        int i = 0;

        for (i = 1; i <= 5; i++) {
            printf("%d\\n", i);
        }

        return 0;
    }
    """

    try:
        lexer = Lexer(sample_code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        parser.parse()
        print("SYNTAX ANALYSIS SUCCESSFUL")

    except (LexerError, ParserError) as error:
        print("COMPILER ERROR:", error)