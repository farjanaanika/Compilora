from lexer import Lexer, LexerError
from parser import Parser, ParserError


class IntermediateCodeError(Exception):
    pass


class IntermediateCodeGenerator:

    TYPE_KEYWORDS = {"int", "float", "double", "char", "void"}

    PRECEDENCE = {
        "=": 1, "+=": 1, "-=": 1, "*=": 1, "/=": 1, "%=": 1,
        "||": 2, "&&": 3,
        "==": 4, "!=": 4,
        "<": 5, ">": 5, "<=": 5, ">=": 5,
        "+": 6, "-": 6,
        "*": 7, "/": 7, "%": 7,
    }

    COMPOUND_OPERATORS = {
        "+=": "+", "-=": "-", "*=": "*",
        "/=": "/", "%=": "%"
    }

    def __init__(self):
        self.code = []
        self.temp_count = 0
        self.label_count = 0
        self.tokens = []
        self.position = 0
        self.loop_stack = []
        self.function_stack = []

    # ---------- Basic Helpers ----------

    def emit(self, instruction):
        self.code.append(instruction)

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

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
                raise IntermediateCodeError(
                    f"Expected {value!r}, reached end of input."
                )

            raise IntermediateCodeError(
                f"Expected {value!r} at line {token.line}, "
                f"column {token.column}; found {token.value!r}."
            )

        return self.advance()

    def tokenize_source(self, source):
        try:
            return Lexer(source).tokenize()
        except LexerError as error:
            raise IntermediateCodeError(
                f"Lexical error: {error}"
            ) from error

    # ---------- Increment / Decrement ----------

    def emit_increment(self, variable, operator):
        sign = "+" if operator == "++" else "-"

        temp = self.new_temp()
        self.emit(f"{temp} = {variable} {sign} 1")
        self.emit(f"{variable} = {temp}")

        return variable

    # ---------- Primary Expression ----------

    def parse_primary(self):
        token = self.current()

        if token is None:
            raise IntermediateCodeError("Incomplete expression.")

        if self.check("("):
            self.advance()
            result = self.parse_expression()
            self.expect(")")
            return result

        if token.type in {
            "NUMBER", "IDENTIFIER", "STRING", "CHARACTER", "CHAR"
        }:
            self.advance()
            result = token.value

            if self.check("("):
                self.advance()
                arguments = []

                if not self.check(")"):
                    arguments.append(self.parse_expression())

                    while self.check(","):
                        self.advance()
                        arguments.append(self.parse_expression())

                self.expect(")")

                for argument in arguments:
                    self.emit(f"param {argument}")

                temp = self.new_temp()
                self.emit(f"{temp} = call {result}, {len(arguments)}")
                result = temp

            return result

        raise IntermediateCodeError(
            f"Unexpected token {token.value!r} in expression."
        )

    # ---------- Postfix Expression ----------

    def parse_postfix(self):
        result = self.parse_primary()

        while self.check("++") or self.check("--"):
            operator = self.advance().value

            old_value = self.new_temp()
            self.emit(f"{old_value} = {result}")

            self.emit_increment(result, operator)
            result = old_value

        return result

    # ---------- Unary Expression ----------

    def parse_unary(self):

        if self.check("++") or self.check("--"):
            operator = self.advance().value
            variable = self.parse_unary()
            return self.emit_increment(variable, operator)

        if self.check("+") or self.check("-") or self.check("!"):
            operator = self.advance().value
            operand = self.parse_unary()

            if operator == "+":
                return operand

            temp = self.new_temp()
            self.emit(f"{temp} = {operator}{operand}")
            return temp

        if self.check("&") or self.check("*"):
            operator = self.advance().value
            operand = self.parse_unary()

            temp = self.new_temp()
            self.emit(f"{temp} = {operator}{operand}")
            return temp

        return self.parse_postfix()

    # ---------- Logical Operators ----------

    def emit_logical_and(self, left, right_parser):
        result = self.new_temp()
        false_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{result} = 0")
        self.emit(f"ifFalse {left} goto {false_label}")

        right = right_parser()

        self.emit(f"ifFalse {right} goto {false_label}")
        self.emit(f"{result} = 1")
        self.emit(f"goto {end_label}")
        self.emit(f"{false_label}:")
        self.emit(f"{end_label}:")

        return result

    def emit_logical_or(self, left, right_parser):
        result = self.new_temp()
        true_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{result} = 1")
        self.emit(f"if {left} goto {true_label}")

        right = right_parser()

        self.emit(f"if {right} goto {true_label}")
        self.emit(f"{result} = 0")
        self.emit(f"goto {end_label}")
        self.emit(f"{true_label}:")
        self.emit(f"{end_label}:")

        return result

    # ---------- Expression Parser ----------

    def parse_expression(self, minimum_precedence=1):
        left = self.parse_unary()

        while self.current() is not None:
            operator = self.current().value
            precedence = self.PRECEDENCE.get(operator)

            if precedence is None or precedence < minimum_precedence:
                break

            self.advance()

            next_precedence = (
                precedence if precedence == 1
                else precedence + 1
            )

            if operator == "&&":
                left = self.emit_logical_and(
                    left,
                    lambda: self.parse_expression(next_precedence)
                )
                continue

            if operator == "||":
                left = self.emit_logical_or(
                    left,
                    lambda: self.parse_expression(next_precedence)
                )
                continue

            right = self.parse_expression(next_precedence)

            if operator == "=":
                self.emit(f"{left} = {right}")

            elif operator in self.COMPOUND_OPERATORS:
                arithmetic_operator = self.COMPOUND_OPERATORS[operator]
                temp = self.new_temp()

                self.emit(
                    f"{temp} = {left} {arithmetic_operator} {right}"
                )
                self.emit(f"{left} = {temp}")

            else:
                temp = self.new_temp()
                self.emit(f"{temp} = {left} {operator} {right}")
                left = temp

        return left

    # ---------- Program and Blocks ----------

    def parse_program(self):
        while self.current() is not None:
            self.parse_statement()

    def parse_block(self):
        self.expect("{")

        while self.current() is not None and not self.check("}"):
            self.parse_statement()

        self.expect("}")

    # ---------- Declarations and Functions ----------

    def parse_declaration(self):
        self.advance()
        name = self.current()

        if name is None or name.type != "IDENTIFIER":
            raise IntermediateCodeError(
                "Expected a variable or function name."
            )

        function_name = self.advance().value

        if self.check("("):
            self.advance()
            parameters = []

            if not self.check(")"):
                while True:
                    type_token = self.current()

                    if (
                        type_token is None
                        or type_token.value not in self.TYPE_KEYWORDS
                    ):
                        raise IntermediateCodeError(
                            "Expected a parameter type."
                        )

                    parameter_type = self.advance().value

                    if parameter_type == "void" and self.check(")"):
                        break

                    parameter_name = self.current()

                    if (
                        parameter_name is None
                        or parameter_name.type != "IDENTIFIER"
                    ):
                        raise IntermediateCodeError(
                            "Expected a parameter name."
                        )

                    parameters.append(
                        (parameter_type, self.advance().value)
                    )

                    if not self.check(","):
                        break

                    self.advance()

            self.expect(")")

            if self.check(";"):
                self.advance()
                self.emit(
                    f"declare {function_name}, {len(parameters)}"
                )
                return

            self.emit(f"func {function_name}:")

            for parameter_type, parameter_name in parameters:
                self.emit(f"{parameter_name} = param")

            self.function_stack.append(function_name)

            try:
                self.parse_block()
            finally:
                self.function_stack.pop()

            self.emit(f"endfunc {function_name}")
            return

        variable_name = function_name

        while True:
            if self.check("="):
                self.advance()
                result = self.parse_expression()
                self.emit(f"{variable_name} = {result}")

            if not self.check(","):
                break

            self.advance()
            variable = self.current()

            if variable is None or variable.type != "IDENTIFIER":
                raise IntermediateCodeError(
                    "Expected a variable name after ','."
                )

            variable_name = self.advance().value

        self.expect(";")

    # ---------- If / Else ----------

    def parse_if(self):
        self.expect("if")
        self.expect("(")

        condition = self.parse_expression()
        self.expect(")")

        else_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"ifFalse {condition} goto {else_label}")
        self.parse_statement()

        if self.check("else"):
            self.emit(f"goto {end_label}")
            self.emit(f"{else_label}:")

            self.advance()
            self.parse_statement()

            self.emit(f"{end_label}:")
        else:
            self.emit(f"{else_label}:")

    # ---------- While Loop ----------

    def parse_while(self):
        self.expect("while")
        self.expect("(")

        start_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{start_label}:")

        condition = self.parse_expression()
        self.expect(")")

        self.emit(f"ifFalse {condition} goto {end_label}")

        self.loop_stack.append({
            "break": end_label,
            "continue": start_label
        })

        try:
            self.parse_statement()
        finally:
            self.loop_stack.pop()

        self.emit(f"goto {start_label}")
        self.emit(f"{end_label}:")

    # ---------- For Loop Initialization ----------

    def parse_for_init(self):
        if self.current() is None or self.check(";"):
            return

        if (
            self.current().type == "KEYWORD"
            and self.current().value in {
                "int", "float", "double", "char"
            }
        ):
            self.advance()
            variable = self.current()

            if variable is None or variable.type != "IDENTIFIER":
                raise IntermediateCodeError(
                    "Expected variable in for-loop initialization."
                )

            self.advance()
            variable_name = variable.value

            if self.check("="):
                self.advance()
                value = self.parse_expression()
                self.emit(f"{variable_name} = {value}")

            while self.check(","):
                self.advance()
                variable = self.current()

                if (
                    variable is None
                    or variable.type != "IDENTIFIER"
                ):
                    raise IntermediateCodeError(
                        "Expected variable after ','."
                    )

                variable_name = self.advance().value

                if self.check("="):
                    self.advance()
                    value = self.parse_expression()
                    self.emit(f"{variable_name} = {value}")

        else:
            self.parse_expression()

    # ---------- For Loop Update ----------

    def parse_for_update(self, update_tokens):
        if not update_tokens:
            return

        saved_tokens = self.tokens
        saved_position = self.position

        try:
            self.tokens = update_tokens
            self.position = 0

            self.parse_expression()

            if self.current() is not None:
                token = self.current()
                raise IntermediateCodeError(
                    f"Unsupported for-loop update near {token.value!r}."
                )

        finally:
            self.tokens = saved_tokens
            self.position = saved_position

    # ---------- For Loop ----------

    def parse_for(self):
        self.expect("for")
        self.expect("(")

        self.parse_for_init()
        self.expect(";")

        start_label = self.new_label()
        update_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{start_label}:")

        condition = None if self.check(";") else self.parse_expression()
        self.expect(";")

        update_start = self.position
        depth = 0

        while self.current() is not None:
            if self.check("("):
                depth += 1
            elif self.check(")"):
                if depth == 0:
                    break
                depth -= 1

            self.advance()

        if self.current() is None:
            raise IntermediateCodeError("Unclosed for-loop header.")

        update_tokens = self.tokens[update_start:self.position]

        if condition is not None:
            self.emit(f"ifFalse {condition} goto {end_label}")

        self.expect(")")

        self.loop_stack.append({
            "break": end_label,
            "continue": update_label
        })

        try:
            self.parse_statement()
        finally:
            self.loop_stack.pop()

        self.emit(f"{update_label}:")
        self.parse_for_update(update_tokens)

        self.emit(f"goto {start_label}")
        self.emit(f"{end_label}:")

    # ---------- Do While Loop ----------

    def parse_do_while(self):
        self.expect("do")

        start_label = self.new_label()
        continue_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{start_label}:")

        self.loop_stack.append({
            "break": end_label,
            "continue": continue_label
        })

        try:
            self.parse_statement()
        finally:
            self.loop_stack.pop()

        self.emit(f"{continue_label}:")

        self.expect("while")
        self.expect("(")

        condition = self.parse_expression()

        self.expect(")")
        self.expect(";")

        self.emit(f"if {condition} goto {start_label}")
        self.emit(f"{end_label}:")

    # ---------- Return ----------

    def parse_return(self):
        self.expect("return")

        if self.check(";"):
            self.emit("return")
        else:
            result = self.parse_expression()
            self.emit(f"return {result}")

        self.expect(";")

    # ---------- Break ----------

    def parse_break(self):
        self.expect("break")
        self.expect(";")

        if not self.loop_stack:
            raise IntermediateCodeError(
                "'break' statement outside a loop."
            )

        self.emit(f"goto {self.loop_stack[-1]['break']}")

    # ---------- Continue ----------

    def parse_continue(self):
        self.expect("continue")
        self.expect(";")

        if not self.loop_stack:
            raise IntermediateCodeError(
                "'continue' statement outside a loop."
            )

        self.emit(f"goto {self.loop_stack[-1]['continue']}")

    # ---------- Statement Dispatcher ----------

    def parse_statement(self):
        token = self.current()

        if token is None:
            return

        if self.check("{"):
            self.parse_block()

        elif self.check("if"):
            self.parse_if()

        elif self.check("while"):
            self.parse_while()

        elif self.check("for"):
            self.parse_for()

        elif self.check("do"):
            self.parse_do_while()

        elif self.check("return"):
            self.parse_return()

        elif self.check("break"):
            self.parse_break()

        elif self.check("continue"):
            self.parse_continue()

        elif self.check(";"):
            self.advance()

        elif (
            token.type == "KEYWORD"
            and token.value in self.TYPE_KEYWORDS
        ):
            self.parse_declaration()

        else:
            self.parse_expression()
            self.expect(";")

    # ---------- Main Generation ----------

    def generate_from_source(self, source_code):
        self.code = []
        self.temp_count = 0
        self.label_count = 0
        self.position = 0
        self.loop_stack = []
        self.function_stack = []

        self.tokens = self.tokenize_source(source_code)

        try:
            Parser(self.tokens).parse()
        except ParserError as error:
            raise IntermediateCodeError(
                f"Syntax error: {error}"
            ) from error

        self.parse_program()
        return "\n".join(self.code)


# ==========================================================
# FINAL INTEGRATION TESTING
# ==========================================================

def run_integration_test(generator, test_name, source_code, required_items):

    print("\n" + "=" * 60)
    print("INTEGRATION TEST:", test_name)
    print("=" * 60)

    try:
        # Step 1: Lexer Testing
        tokens = Lexer(source_code).tokenize()
        print("1. LEXER: PASSED")
        print("   Tokens generated:", len(tokens))

        # Step 2: Parser Testing
        Parser(tokens).parse()
        print("2. PARSER: PASSED")

        # Step 3: Intermediate Code Generation
        result = generator.generate_from_source(source_code)
        print("3. INTERMEDIATE CODE GENERATION: PASSED")

        # Step 4: Check generated TAC
        missing_items = [
            item for item in required_items
            if item not in result
        ]

        if missing_items:
            print("4. TAC VERIFICATION: FAILED")
            print("Missing:", missing_items)
            return False

        print("4. TAC VERIFICATION: PASSED")
        print("\nGenerated Intermediate Code:")
        print("-" * 60)
        print(result)

        print("\nINTEGRATION TEST PASSED!")
        return True

    except (LexerError, ParserError, IntermediateCodeError) as error:
        print("\nINTEGRATION TEST FAILED!")
        print("Error:", error)
        return False


if __name__ == "__main__":

    generator = IntermediateCodeGenerator()

    integration_tests = [

        (
            "Arithmetic and Variable Declaration",
            """
            int main() {
                int a = 10;
                int b = 20;
                int c = a + b;
                return c;
            }
            """,
            ["a = 10", "b = 20", "return"]
        ),

        (
            "If Else and Comparison",
            """
            int main() {
                int a = 10;
                if (a > 5) {
                    a = a + 1;
                } else {
                    a = a - 1;
                }
                return a;
            }
            """,
            ["ifFalse", "goto", "return"]
        ),

        (
            "While Loop and Break",
            """
            int main() {
                int i = 0;
                while (i < 5) {
                    i++;
                    if (i == 3) {
                        break;
                    }
                }
                return i;
            }
            """,
            ["ifFalse", "goto", "return"]
        ),

        (
            "For Loop and Continue",
            """
            int main() {
                int sum = 0;
                for (int i = 0; i < 5; i++) {
                    if (i == 2) {
                        continue;
                    }
                    sum += i;
                }
                return sum;
            }
            """,
            ["ifFalse", "sum", "goto", "return"]
        ),

        (
            "Function Call",
            """
            int add(int a, int b) {
                return a + b;
            }

            int main() {
                int x = 10;
                int y = 20;
                int result = add(x, y);
                return result;
            }
            """,
            ["func add:", "call add, 2", "endfunc add"]
        ),

        (
            "Recursive Function",
            """
            int factorial(int n) {
                if (n <= 1) {
                    return 1;
                }
                return n * factorial(n - 1);
            }

            int main() {
                int result = factorial(5);
                return result;
            }
            """,
            ["func factorial:", "call factorial, 1", "endfunc factorial"]
        ),

        (
            "Logical Operators",
            """
            int main() {
                int a = 10;
                int b = 5;

                if (a > 5 && b < 10) {
                    a += 1;
                }

                return a;
            }
            """,
            ["ifFalse", "a", "return"]
        ),

        (
            "Nested Loops",
            """
            int main() {
                int i = 0;
                int j = 0;

                while (i < 2) {
                    j = 0;

                    while (j < 2) {
                        j++;
                        if (j == 1) {
                            continue;
                        }
                    }

                    i++;
                }

                return 0;
            }
            """,
            ["ifFalse", "goto", "return"]
        )
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("COMPILORA - FINAL INTEGRATION TESTING")
    print("=" * 60)

    for test_name, source_code, required_items in integration_tests:

        success = run_integration_test(
            generator,
            test_name,
            source_code,
            required_items
        )

        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print("FINAL INTEGRATION TEST SUMMARY")
    print("=" * 60)

    print("Total Tests:", len(integration_tests))
    print("Passed:", passed)
    print("Failed:", failed)

    if failed == 0:
        print("\nALL INTEGRATION TESTS PASSED!")
        print("LEXER + PARSER + ICG WORKING TOGETHER!")
    else:
        print("\nSOME INTEGRATION TESTS FAILED.")
        print("Please check the error messages above.")