
from lexer import Lexer, LexerError
from parser import Parser, ParserError


class SemanticError(Exception):
    pass


class SemanticAnalyzer:

    TYPES = {
        "int", "float", "double", "char", "bool", "void",
        "short", "long", "signed", "unsigned", "auto",
        "string"
    }

    BUILTINS = {
        "cout", "cin", "cerr", "clog", "endl",
        "printf", "scanf", "main", "std", "nullptr"
    }

    def __init__(self, tokens):
        self.tokens = [
            token for token in tokens
            if token.type != "PREPROCESSOR"
        ]

        self.scopes = [{}]
        self.functions = set()
        self.pending_parameters = []

    def current(self, index):
        if index < len(self.tokens):
            return self.tokens[index]
        return self.tokens[-1]

    def error(self, token, message):
        raise SemanticError(
            f"Line {token.line}, Column {token.column}: {message}"
        )

    def enter_scope(self):
        self.scopes.append({})

        for name, data_type, token in self.pending_parameters:
            self.declare(name, data_type, token)

        self.pending_parameters = []

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare(self, name, data_type, token):

        current_scope = self.scopes[-1]

        if name in current_scope:
            self.error(
                token,
                f"Variable '{name}' is already declared in this scope"
            )

        current_scope[name] = data_type

    def lookup(self, name):

        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]

        return None

    def infer_type(self, token):

        if token is None:
            return None

        value = token.value

        if token.type == "STRING":
            return "string"

        if token.type == "CHARACTER":
            return "char"

        if token.type == "NUMBER":

            if any(c in value.lower() for c in (".", "e")):
                return "double"

            return "int"

        if value in ("true", "false"):
            return "bool"

        if token.type == "IDENTIFIER":
            return self.lookup(value)

        return None

    def check_assignment(self, variable_type, value_token):

        value_type = self.infer_type(value_token)

        if value_type is None:
            return

        numeric_types = {
            "int", "float", "double", "short",
            "long", "signed", "unsigned", "char", "bool"
        }

        if variable_type in numeric_types:

            if value_type == "string":
                self.error(
                    value_token,
                    f"Cannot assign string to '{variable_type}' variable"
                )

        elif variable_type == "string":

            if value_type != "string":
                self.error(
                    value_token,
                    "Invalid value assigned to string variable"
                )

    def read_parameters(self, index):

        parameters = []
        i = index

        while i < len(self.tokens):

            token = self.current(i)

            if token.value == ")":
                return parameters, i + 1

            if token.value in self.TYPES:

                data_type = token.value
                i += 1

                while self.current(i).value in ("*", "&", "&&"):
                    i += 1

                if self.current(i).type == "IDENTIFIER":

                    name_token = self.current(i)

                    parameters.append(
                        (name_token.value, data_type, name_token)
                    )

                    i += 1

            else:
                i += 1

            if self.current(i).value == ",":
                i += 1

        return parameters, i

    def analyze(self):

        i = 0

        while i < len(self.tokens):

            token = self.current(i)
            value = token.value

            if token.type == "EOF":
                break

            if value == "{":
                self.enter_scope()
                i += 1
                continue

            if value == "}":
                self.exit_scope()
                i += 1
                continue

            if value in self.TYPES:

                data_type = value
                name_token = self.current(i + 1)

                if name_token.type != "IDENTIFIER":
                    i += 1
                    continue

                name = name_token.value
                next_token = self.current(i + 2)

                if next_token.value == "(":

                    self.functions.add(name)

                    parameters, next_index = self.read_parameters(
                        i + 3
                    )

                    self.pending_parameters = parameters
                    i = next_index

                    if self.current(i).value == ";":
                        self.pending_parameters = []
                        i += 1

                    continue

                self.declare(name, data_type, name_token)
                i += 2

                while i < len(self.tokens):

                    current_token = self.current(i)

                    if current_token.value == ";":
                        i += 1
                        break

                    if current_token.value == ",":

                        i += 1
                        name_token = self.current(i)

                        if name_token.type != "IDENTIFIER":
                            self.error(
                                name_token,
                                "Expected variable name"
                            )

                        self.declare(
                            name_token.value,
                            data_type,
                            name_token
                        )

                        i += 1
                        continue

                    if current_token.value == "=":

                        value_token = self.current(i + 1)

                        self.check_assignment(
                            data_type,
                            value_token
                        )

                        i += 1
                        continue

                    if current_token.type == "IDENTIFIER":

                        self.check_identifier(
                            current_token,
                            self.current(i + 1)
                        )

                    i += 1

                continue

            if token.type == "IDENTIFIER":

                next_token = self.current(i + 1)

                self.check_identifier(token, next_token)

                if next_token.value in (
                    "=", "+=", "-=", "*=", "/=", "%="
                ):

                    variable_type = self.lookup(token.value)
                    value_token = self.current(i + 2)

                    if variable_type is not None:
                        self.check_assignment(
                            variable_type,
                            value_token
                        )

            i += 1

        return True

    def check_identifier(self, token, next_token):

        name = token.value

        if name in self.BUILTINS:
            return

        for index, item in enumerate(self.tokens):

            if item is token and index > 0:

                previous = self.tokens[index - 1]

                if previous.value in (
                    ".", "->", "::", "namespace"
                ):
                    return

                break

        if next_token.value == "(":
            return

        if name in self.functions:
            return

        if self.lookup(name) is None:

            self.error(
                token,
                f"Undeclared identifier '{name}'"
            )


# Main function
def main():

    source = """
    int main() {
        int a = 10;
        int a = 20;
        return 0;
    }
    """

    try:

        # Phase 1: Lexical Analysis
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        # Phase 2: Syntax Analysis
        parser = Parser(tokens)
        parser.parse()

        # Phase 3: Semantic Analysis
        analyzer = SemanticAnalyzer(tokens)
        analyzer.analyze()

        print("Semantic Analysis Completed Successfully!")
        print("No Semantic Errors Found.")

    except (LexerError, ParserError, SemanticError) as error:

        print("Compilation Failed!")
        print(error)


if __name__ == "__main__":
    main()
