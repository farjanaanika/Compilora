
from lexer import Lexer, LexerError


class ParserError(Exception):
    pass


class Parser:

    TYPES = {
        "int", "float", "double", "char", "bool", "void",
        "short", "long", "signed", "unsigned", "auto"
    }

    def __init__(self, tokens):
        self.tokens = [
            token for token in tokens
            if token.type != "PREPROCESSOR"
        ]
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        index = self.pos + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return self.tokens[-1]

    def check(self, value):
        return self.current().value == value

    def match(self, value):
        if self.check(value):
            self.advance()
            return True
        return False

    def advance(self):
        token = self.current()

        if token.type != "EOF":
            self.pos += 1

        return token

    def expect(self, value):
        if not self.check(value):
            self.error(
                f"Expected '{value}', found '{self.current().value}'"
            )

        return self.advance()

    def error(self, message):
        token = self.current()

        raise ParserError(
            f"Line {token.line}, Column {token.column}: {message}"
        )

    # Check whether current token is a data type
    def is_type(self):
        return self.current().value in self.TYPES

    # Main parser
    def parse(self):

        while self.current().type != "EOF":

            if self.match(";"):
                continue

            if self.check("using"):
                self.parse_using()

            elif self.is_type():
                self.parse_declaration_or_function()

            else:
                self.error(
                    f"Unexpected token '{self.current().value}'"
                )

        return True

    # using namespace std;
    def parse_using(self):

        self.expect("using")

        if self.match("namespace"):

            if self.current().type != "IDENTIFIER":
                self.error("Expected namespace name")

            self.advance()
            self.expect(";")

        else:
            self.error("Invalid using declaration")

    # Parse data type
    def parse_type_name(self):

        if not self.is_type():
            self.error("Expected a data type")

        self.advance()

        while self.current().value in ("*", "&", "&&"):
            self.advance()

    # Variable declaration or function
    def parse_declaration_or_function(self):

        self.parse_type_name()

        if self.current().type != "IDENTIFIER":
            self.error("Expected variable or function name")

        self.advance()

        if self.match("("):

            self.parse_parameters()
            self.expect(")")

            if self.match(";"):
                return

            self.parse_block()

        else:
            self.parse_declaration_tail()

    # Function parameters
    def parse_parameters(self):

        if self.check(")"):
            return

        if self.check("void") and self.peek().value == ")":
            self.advance()
            return

        while True:

            self.parse_type_name()

            if self.current().type == "IDENTIFIER":
                self.advance()

            if not self.match(","):
                break

    # Variable declaration
    def parse_declaration_tail(self):

        if self.match("="):
            self.parse_expression()

        while self.match(","):

            if self.current().type != "IDENTIFIER":
                self.error("Expected variable name")

            self.advance()

            if self.match("="):
                self.parse_expression()

        self.expect(";")

    # Block statement
    def parse_block(self):

        self.expect("{")

        while not self.check("}"):

            if self.current().type == "EOF":
                self.error("Unexpected end of file inside block")

            self.parse_statement()

        self.expect("}")

    # Statements
    def parse_statement(self):

        if self.check("{"):
            self.parse_block()

        elif self.check("if"):
            self.parse_if()

        elif self.check("while"):
            self.parse_while()

        elif self.check("do"):
            self.parse_do_while()

        elif self.check("for"):
            self.parse_for()

        elif self.check("return"):
            self.parse_return()

        elif self.check("break") or self.check("continue"):
            self.advance()
            self.expect(";")

        elif self.is_type():

            self.parse_type_name()

            if self.current().type != "IDENTIFIER":
                self.error("Expected variable name")

            self.advance()
            self.parse_declaration_tail()

        elif self.check(";"):
            self.advance()

        else:
            self.parse_expression()
            self.expect(";")

    # If-else statement
    def parse_if(self):

        self.expect("if")
        self.expect("(")

        self.parse_expression()

        self.expect(")")

        self.parse_statement()

        if self.match("else"):
            self.parse_statement()

    # While loop
    def parse_while(self):

        self.expect("while")
        self.expect("(")

        self.parse_expression()

        self.expect(")")

        self.parse_statement()

    # Do-while loop
    def parse_do_while(self):

        self.expect("do")

        self.parse_statement()

        self.expect("while")
        self.expect("(")

        self.parse_expression()

        self.expect(")")
        self.expect(";")

    # For loop
    def parse_for(self):

        self.expect("for")
        self.expect("(")

        # Initialization
        if self.is_type():

            self.parse_type_name()

            if self.current().type != "IDENTIFIER":
                self.error("Expected variable name in for loop")

            self.advance()

            if self.match("="):
                self.parse_expression()

        elif not self.check(";"):
            self.parse_expression()

        self.expect(";")

        # Condition
        if not self.check(";"):
            self.parse_expression()

        self.expect(";")

        # Update
        if not self.check(")"):
            self.parse_expression()

        self.expect(")")

        self.parse_statement()

    # Expression parser
    def parse_expression(self):
        self.parse_assignment()

    # Assignment and stream operators
    def parse_assignment(self):

        self.parse_logical_or()

        while self.current().value in ("<<", ">>"):

            self.advance()
            self.parse_logical_or()

        if self.current().value in (
            "=", "+=", "-=", "*=", "/=", "%="
        ):

            self.advance()
            self.parse_assignment()

    # Logical OR
    def parse_logical_or(self):

        self.parse_logical_and()

        while self.current().value in ("||", "or"):

            self.advance()
            self.parse_logical_and()

    # Logical AND
    def parse_logical_and(self):

        self.parse_equality()

        while self.current().value in ("&&", "and"):

            self.advance()
            self.parse_equality()

    # Equality operators
    def parse_equality(self):

        self.parse_relational()

        while self.current().value in ("==", "!="):

            self.advance()
            self.parse_relational()

    # Relational operators
    def parse_relational(self):

        self.parse_additive()

        while self.current().value in (
            "<", ">", "<=", ">="
        ):

            self.advance()
            self.parse_additive()

    # Addition and subtraction
    def parse_additive(self):

        self.parse_multiplicative()

        while self.current().value in ("+", "-"):

            self.advance()
            self.parse_multiplicative()

    # Multiplication and division
    def parse_multiplicative(self):

        self.parse_unary()

        while self.current().value in ("*", "/", "%"):

            self.advance()
            self.parse_unary()

    # Unary operators
    def parse_unary(self):

        if self.current().value in (
            "!", "~", "+", "-", "++", "--",
            "*", "&", "not"
        ):

            self.advance()
            self.parse_unary()

        else:
            self.parse_postfix()

    # Function calls and postfix operators
    def parse_postfix(self):

        self.parse_primary()

        while True:

            if self.match("("):

                if not self.check(")"):

                    self.parse_expression()

                    while self.match(","):
                        self.parse_expression()

                self.expect(")")

            elif self.match("["):

                self.parse_expression()
                self.expect("]")

            elif self.current().value in ("++", "--"):

                self.advance()

            elif self.match(".") or self.match("->"):

                if self.current().type != "IDENTIFIER":
                    self.error("Expected member name")

                self.advance()

            else:
                break

    # Primary expressions
    def parse_primary(self):

        token = self.current()

        if token.type in (
            "IDENTIFIER", "NUMBER", "STRING", "CHARACTER"
        ):

            self.advance()
            return

        if self.match("true") or self.match("false"):
            return

        if self.match("("):

            self.parse_expression()
            self.expect(")")
            return

        self.error(
            f"Invalid expression near '{token.value}'"
        )

    # Return statement
    def parse_return(self):

        self.expect("return")

        if not self.check(";"):
            self.parse_expression()

        self.expect(";")


# Main function
def main():

    source = """
    #include <iostream>
    using namespace std;

    int main() {

        int age = 25;
        int i = 0;

        if (age >= 18) {
            cout << "Adult";
        }
        else {
            cout << "Minor";
        }

        for (int j = 0; j < 5; j++) {
            cout << j;
        }

        while (i < 3) {
            i++;
        }

        do {
            i--;
        } while (i > 0);

        return 0;
    }
    """

    try:

        lexer = Lexer(source)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        parser.parse()

        print("Syntax Analysis Completed Successfully!")
        print("No Syntax Errors Found.")

    except (LexerError, ParserError) as error:

        print("Compilation Failed!")
        print(error)


if __name__ == "__main__":
    main()
