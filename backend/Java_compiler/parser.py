
from lexer import JavaLexer


class JavaParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def current(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def value(self):
        token = self.current()
        return token["value"] if token else None

    def token_type(self):
        token = self.current()
        return token["type"] if token else None

    def advance(self):
        token = self.current()
        if token:
            self.position += 1
        return token

    def error(self, message):
        token = self.current()

        if token:
            raise SyntaxError(
                f"Line {token['line']}, Column {token['column']}: "
                f"{message}. Found '{token['value']}'"
            )

        raise SyntaxError(f"Unexpected end of input: {message}")

    def expect(self, expected):
        if self.value() == expected:
            return self.advance()
        self.error(f"Expected '{expected}'")

    def expect_identifier(self):
        if self.token_type() == "IDENTIFIER":
            return self.advance()
        self.error("Expected identifier")

    def parse(self):
        print("\n========== JAVA SYNTAX ANALYZER - PHASE 2 ==========")

        try:
            self.parse_program()

            if self.current() is not None:
                self.error("Unexpected token after program")

            print("Syntax Analysis Successful!")
            print("No Syntax Errors Found.")
            return True

        except SyntaxError as error:
            print("\nSyntax Analysis Failed!")
            print(error)
            return False

    def parse_program(self):
        if self.value() == "package":
            self.advance()
            self.parse_qualified_name()
            self.expect(";")

        while self.value() == "import":
            self.advance()

            if self.value() == "static":
                self.advance()

            self.parse_qualified_name()

            if self.value() == "*":
                self.advance()

            self.expect(";")

        while self.value() in ("public", "private", "protected", "final"):
            self.advance()

        self.expect("class")
        self.expect_identifier()
        self.expect("{")

        while self.value() != "}":
            if self.current() is None:
                self.error("Expected closing class brace")
            self.parse_method()

        self.expect("}")

    def parse_qualified_name(self):
        self.expect_identifier()

        while self.value() == ".":
            self.advance()

            if self.value() == "*":
                return

            self.expect_identifier()

    def parse_method(self):
        while self.value() in (
            "public", "private", "protected",
            "static", "final"
        ):
            self.advance()

        if self.value() in (
            "void", "int", "float", "double",
            "char", "boolean", "String",
            "long", "short", "byte"
        ):
            self.advance()

        elif self.token_type() == "IDENTIFIER":
            self.advance()

        else:
            self.error("Expected method return type")

        self.expect_identifier()
        self.expect("(")

        if self.value() != ")":
            self.parse_parameters()

        self.expect(")")
        self.parse_block()

    def parse_parameters(self):
        while True:
            while self.value() == "final":
                self.advance()

            self.parse_type()
            self.expect_identifier()

            while self.value() == "[":
                self.advance()
                self.expect("]")

            if self.value() != ",":
                break

            self.advance()

    def parse_type(self):
        if self.value() in (
            "int", "float", "double", "char",
            "boolean", "String", "long",
            "short", "byte"
        ):
            self.advance()

        elif self.token_type() == "IDENTIFIER":
            self.advance()

        else:
            self.error("Expected data type")

        while self.value() == "[":
            self.advance()
            self.expect("]")

    def parse_block(self):
        self.expect("{")

        while self.value() != "}":
            if self.current() is None:
                self.error("Expected closing block brace")
            self.parse_statement()

        self.expect("}")

    def parse_statement(self):
        if self.value() == "{":
            self.parse_block()

        elif self.value() == "if":
            self.parse_if()

        elif self.value() == "while":
            self.parse_while()

        elif self.value() == "for":
            self.parse_for()

        elif self.value() == "do":
            self.parse_do_while()

        elif self.value() in ("break", "continue"):
            self.advance()
            self.expect(";")

        elif self.value() == "return":
            self.advance()

            if self.value() != ";":
                self.parse_expression()

            self.expect(";")

        elif self.value() == "System":
            self.parse_print_statement()

        elif self.value() == ";":
            self.advance()

        elif self.value() in (
            "int", "float", "double", "char",
            "boolean", "String", "long",
            "short", "byte", "final"
        ):
            self.parse_variable_declaration()
            self.expect(";")

        elif self.token_type() == "IDENTIFIER":
            self.parse_assignment_or_call()
            self.expect(";")

        else:
            self.error("Invalid statement")

    def parse_variable_declaration(self):
        if self.value() == "final":
            self.advance()

        self.parse_type()
        self.expect_identifier()

        if self.value() == "=":
            self.advance()
            self.parse_expression()

        while self.value() == ",":
            self.advance()
            self.expect_identifier()

            if self.value() == "=":
                self.advance()
                self.parse_expression()

    def parse_assignment_or_call(self):
        self.expect_identifier()

        while self.value() == ".":
            self.advance()
            self.expect_identifier()

        if self.value() == "(":
            self.advance()

            if self.value() != ")":
                self.parse_argument_list()

            self.expect(")")

        elif self.value() in (
            "=", "+=", "-=", "*=", "/=", "%=",
            "++", "--"
        ):
            operator = self.advance()["value"]

            if operator not in ("++", "--"):
                self.parse_expression()

        elif self.value() == "[":
            self.advance()
            self.parse_expression()
            self.expect("]")

            if self.value() in ("=", "+=", "-=", "*=", "/="):
                self.advance()
                self.parse_expression()

        else:
            self.error("Expected assignment operator or method call")

    def parse_argument_list(self):
        self.parse_expression()

        while self.value() == ",":
            self.advance()
            self.parse_expression()

    def parse_print_statement(self):
        self.expect("System")
        self.expect(".")
        self.expect("out")
        self.expect(".")

        if self.value() not in ("print", "println", "printf"):
            self.error("Expected print, println or printf")

        self.advance()
        self.expect("(")

        if self.value() != ")":
            self.parse_argument_list()

        self.expect(")")
        self.expect(";")

    def parse_if(self):
        self.expect("if")
        self.expect("(")
        self.parse_expression()
        self.expect(")")
        self.parse_statement()

        if self.value() == "else":
            self.advance()
            self.parse_statement()

    def parse_while(self):
        self.expect("while")
        self.expect("(")
        self.parse_expression()
        self.expect(")")
        self.parse_statement()

    def parse_for(self):
        self.expect("for")
        self.expect("(")

        if self.value() != ";":
            if self.value() in (
                "int", "float", "double", "char",
                "boolean", "String", "long",
                "short", "byte"
            ):
                self.parse_variable_declaration()
            else:
                self.parse_assignment_or_call()

        self.expect(";")

        if self.value() != ";":
            self.parse_expression()

        self.expect(";")

        if self.value() != ")":
            self.parse_assignment_or_call()

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

    def parse_expression(self):
        self.parse_logical_or()

    def parse_logical_or(self):
        self.parse_logical_and()

        while self.value() == "||":
            self.advance()
            self.parse_logical_and()

    def parse_logical_and(self):
        self.parse_equality()

        while self.value() == "&&":
            self.advance()
            self.parse_equality()

    def parse_equality(self):
        self.parse_comparison()

        while self.value() in ("==", "!="):
            self.advance()
            self.parse_comparison()

    def parse_comparison(self):
        self.parse_additive()

        while self.value() in ("<", ">", "<=", ">="):
            self.advance()
            self.parse_additive()

    def parse_additive(self):
        self.parse_multiplicative()

        while self.value() in ("+", "-"):
            self.advance()
            self.parse_multiplicative()

    def parse_multiplicative(self):
        self.parse_unary()

        while self.value() in ("*", "/", "%"):
            self.advance()
            self.parse_unary()

    def parse_unary(self):
        if self.value() in ("!", "-", "+", "++", "--"):
            self.advance()
            self.parse_unary()
        else:
            self.parse_primary()

    def parse_primary(self):
        if self.value() == "(":
            self.advance()
            self.parse_expression()
            self.expect(")")

        elif self.token_type() in ("NUMBER", "STRING", "CHAR"):
            self.advance()

        elif self.value() in ("true", "false", "null"):
            self.advance()

        elif self.token_type() == "IDENTIFIER":
            self.advance()

            while self.value() in (".", "["):
                if self.value() == ".":
                    self.advance()
                    self.expect_identifier()
                else:
                    self.advance()
                    self.parse_expression()
                    self.expect("]")

            if self.value() == "(":
                self.advance()

                if self.value() != ")":
                    self.parse_argument_list()

                self.expect(")")

            if self.value() in ("++", "--"):
                self.advance()

        else:
            self.error("Expected expression")


if __name__ == "__main__":

    java_code = """
public class Main {
    public static void main(String[] args) {

        int a = 10;
        int b = 20;
        int sum = a + b;

        if (sum > 20) {
            System.out.println("Greater");
        } else {
            System.out.println("Smaller");
        }

        for (int i = 0; i < 5; i++) {
            sum = sum + i;
        }

        return;
    }
}
"""

    lexer = JavaLexer(java_code)
    tokens = lexer.tokenize()

    parser = JavaParser(tokens)
    parser.parse()
