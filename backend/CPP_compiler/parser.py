
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

    def value(self):
        token = self.current()
        return token.value if token else None

    def advance(self):
        token = self.current()
        if token:
            self.position += 1
        return token

    def match(self, value):
        if self.value() == value:
            return self.advance()
        return None

    def expect(self, value):
        token = self.match(value)
        if token is None:
            raise ParserError(
                f"Expected '{value}' but found '{self.value()}'"
            )
        return token

    def parse(self):
        program = []

        while self.current():
            if self.value() == "#include" or self.current().type == "PREPROCESSOR":
                self.advance()

            elif self.value() == "using":
                program.append(self.parse_using())

            elif self.value() in ("int", "void", "float", "double", "char", "bool"):
                program.append(self.parse_function_or_declaration())

            else:
                raise ParserError(
                    f"Unexpected token '{self.value()}'"
                )

        return {
            "type": "Program",
            "body": program
        }

    def parse_using(self):
        self.expect("using")
        self.expect("namespace")
        name = self.advance()

        if name.value != "std":
            raise ParserError("Expected namespace std")

        self.expect(";")

        return {
            "type": "UsingNamespace",
            "name": "std"
        }

    def parse_function_or_declaration(self):
        data_type = self.advance().value
        name = self.advance()

        if not name or name.type != "IDENTIFIER":
            raise ParserError("Expected identifier")

        if self.match("("):
            parameters = []

            while self.value() != ")":
                parameter_type = self.advance().value
                parameter_name = self.advance()

                if not parameter_name or parameter_name.type != "IDENTIFIER":
                    raise ParserError("Expected parameter name")

                parameters.append({
                    "data_type": parameter_type,
                    "name": parameter_name.value
                })

                if not self.match(","):
                    break

            self.expect(")")

            self.expect("{")
            body = self.parse_block()
            self.expect("}")

            return {
                "type": "Function",
                "return_type": data_type,
                "name": name.value,
                "parameters": parameters,
                "body": body
            }

        self.expect("=")
        value = self.parse_expression()
        self.expect(";")

        return {
            "type": "Declaration",
            "data_type": data_type,
            "name": name.value,
            "value": value
        }

    def parse_block(self):
        statements = []

        while self.current() and self.value() != "}":
            statements.append(self.parse_statement())

        return statements

    def parse_statement(self):
        if self.value() in ("int", "float", "double", "char", "bool"):
            return self.parse_function_or_declaration()

        if self.match("return"):
            value = self.parse_expression()
            self.expect(";")

            return {
                "type": "Return",
                "value": value
            }

        if self.match("cout"):
            return self.parse_cout()

        if self.match("cin"):
            return self.parse_cin()

        if self.value() == "if":
            return self.parse_if()

        if self.value() == "while":
            return self.parse_while()

        if self.value() == "do":
            return self.parse_do_while()

        if self.value() == "for":
            return self.parse_for()

        token = self.current()

        if token and token.type == "IDENTIFIER":
            name = self.advance().value
            self.expect("=")
            value = self.parse_expression()
            self.expect(";")

            return {
                "type": "Assignment",
                "name": name,
                "value": value
            }

        raise ParserError(
            f"Invalid statement near '{self.value()}'"
        )

    def parse_cout(self):
        output = []

        while self.match("<<"):
            output.append(self.parse_expression())

        self.expect(";")

        if not output:
            raise ParserError("cout requires an output expression")

        return {
            "type": "Output",
            "values": output
        }

    def parse_cin(self):
        inputs = []

        while self.match(">>"):
            token = self.current()

            if not token or token.type != "IDENTIFIER":
                raise ParserError("Expected variable after cin >>")

            inputs.append(self.advance().value)

        self.expect(";")

        return {
            "type": "Input",
            "variables": inputs
        }

    def parse_if(self):
        self.expect("if")
        self.expect("(")
        condition = self.parse_expression()
        self.expect(")")

        self.expect("{")
        body = self.parse_block()
        self.expect("}")

        else_body = []

        if self.match("else"):
            self.expect("{")
            else_body = self.parse_block()
            self.expect("}")

        return {
            "type": "If",
            "condition": condition,
            "body": body,
            "else_body": else_body
        }

    def parse_while(self):
        self.expect("while")
        self.expect("(")
        condition = self.parse_expression()
        self.expect(")")

        self.expect("{")
        body = self.parse_block()
        self.expect("}")

        return {
            "type": "While",
            "condition": condition,
            "body": body
        }
    

    def parse_for(self):
        self.expect("for")
        self.expect("(")

        initializer = None

        if self.value() == "int":
            initializer = self.parse_function_or_declaration()
        else:
            name = self.advance().value
            self.expect("=")
            value = self.parse_expression()
            self.expect(";")

            initializer = {
                "type": "Assignment",
                "name": name,
                "value": value
            }

        condition = self.parse_expression()
        self.expect(";")

        update_name = self.advance().value
        update_operator = self.advance().value
        update_value = self.parse_expression()

        self.expect(")")

        self.expect("{")
        body = self.parse_block()
        self.expect("}")

        return {
            "type": "For",
            "initializer": initializer,
            "condition": condition,
            "update": {
                "name": update_name,
                "operator": update_operator,
                "value": update_value
            },
            "body": body
        }
    def parse_do_while(self):
        self.expect("do")

        self.expect("{")
        body = self.parse_block()
        self.expect("}")

        self.expect("while")
        self.expect("(")
        condition = self.parse_expression()
        self.expect(")")
        self.expect(";")

        return {
            "type": "DoWhile",
            "condition": condition,
            "body": body
        }
    def parse_expression(self):
        left = self.current()

        if not left:
            raise ParserError("Expected expression")

        if left.type in ("NUMBER", "STRING", "CHARACTER"):
            left_value = self.advance().value

        elif left.type == "IDENTIFIER":
            name = self.advance().value

            if self.match("("):
                arguments = []

                if self.value() != ")":
                    arguments.append(self.parse_expression())

                    while self.match(","):
                        arguments.append(self.parse_expression())

                self.expect(")")

                left_value = {
                    "type": "FunctionCall",
                    "name": name,
                    "arguments": arguments
                }
            else:
                left_value = name

        elif left.value == "endl":
            self.advance()
            return {"type": "Endl"}

        else:
            raise ParserError(
                f"Invalid expression near '{self.value()}'"
            )

        operators = (
            "==", "!=", "<=", ">=", "<", ">",
            "+", "-", "*", "/", "%"
        )

        if self.value() in operators:
            operator = self.advance().value
            right = self.parse_expression()

            return {
                "type": "BinaryExpression",
                "left": left_value,
                "operator": operator,
                "right": right
            }

        return left_value
