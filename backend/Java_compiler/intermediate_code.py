
import re


class JavaIntermediateCodeGenerator:

    TYPES = {
        "int", "float", "double", "char", "boolean",
        "String", "long", "short", "byte"
    }

    PRECEDENCE = {
        "||": 1,
        "&&": 2,
        "==": 3,
        "!=": 3,
        "<": 4,
        ">": 4,
        "<=": 4,
        ">=": 4,
        "+": 5,
        "-": 5,
        "*": 6,
        "/": 6,
        "%": 6
    }

    TOKEN_PATTERN = re.compile(
        r'"(?:\\.|[^"\\])*"'
        r"|'(?:\\.|[^'\\])*'"
        r'|\d+\.\d+|\d+'
        r'|[A-Za-z_$][A-Za-z0-9_$]*'
        r'|>>=|<<=|==|!=|<=|>=|\+\+|--|\+=|-=|\*=|/=|%=|&&|\|\|'
        r'|[+\-*/%<>=!&|]'
        r'|[{}()\[\];,.?:]'
    )

    def __init__(self, source_code):

        self.source_code = source_code
        self.tokens = []
        self.pos = 0

        self.code = []

        self.temp_count = 0
        self.label_count = 0

        self.loop_stack = []

        self.tokenize()

    # ======================================
    # TOKENIZER
    # ======================================

    def tokenize(self):

        source = re.sub(
            r'/\*.*?\*/|//[^\n]*',
            lambda m: re.sub(r'[^\n]', ' ', m.group()),
            self.source_code,
            flags=re.DOTALL
        )

        self.tokens = self.TOKEN_PATTERN.findall(source)

    def current(self):

        if self.pos < len(self.tokens):
            return self.tokens[self.pos]

        return None

    def peek(self, offset=1):

        index = self.pos + offset

        if index < len(self.tokens):
            return self.tokens[index]

        return None

    def advance(self):

        token = self.current()

        if token is not None:
            self.pos += 1

        return token

    def match(self, token):

        if self.current() == token:
            self.advance()
            return True

        return False

    def expect(self, token):

        if not self.match(token):
            raise SyntaxError(
                f"Expected '{token}', found '{self.current()}'"
            )

    # ======================================
    # TAC HELPERS
    # ======================================

    def new_temp(self):

        self.temp_count += 1

        return f"t{self.temp_count}"

    def new_label(self):

        self.label_count += 1

        return f"L{self.label_count}"

    def emit(self, instruction):

        self.code.append(instruction)

    def emit_label(self, label):

        self.emit(f"{label}:")

    # ======================================
    # EXPRESSIONS
    # ======================================

    def parse_expression(self, min_precedence=0):

        left = self.parse_unary()

        while True:

            operator = self.current()

            if operator not in self.PRECEDENCE:
                break

            precedence = self.PRECEDENCE[operator]

            if precedence < min_precedence:
                break

            self.advance()

            right = self.parse_expression(precedence + 1)

            temp = self.new_temp()

            self.emit(
                f"{temp} = {left} {operator} {right}"
            )

            left = temp

        return left

    def parse_unary(self):

        token = self.current()

        if token in ("!", "-", "+"):

            operator = self.advance()

            operand = self.parse_unary()

            if operator == "+":
                return operand

            temp = self.new_temp()

            self.emit(f"{temp} = {operator}{operand}")

            return temp

        return self.parse_primary()

    def parse_primary(self):

        token = self.current()

        if token is None:
            raise SyntaxError("Unexpected end of expression")

        # Parenthesized expression
        if self.match("("):

            value = self.parse_expression()

            self.expect(")")

            return value

        # Constants
        if (
            re.fullmatch(r'\d+(\.\d+)?', token)
            or token in ("true", "false", "null")
            or token.startswith('"')
            or token.startswith("'")
        ):

            self.advance()

            return token

        # Identifier, method call or dotted name
        if re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', token):

            name = self.advance()

            while self.match("."):

                part = self.advance()

                if part is None:
                    raise SyntaxError("Expected identifier after '.'")

                name += "." + part

            # Method call
            if self.match("("):

                arguments = []

                if self.current() != ")":

                    while True:

                        arguments.append(
                            self.parse_expression()
                        )

                        if not self.match(","):
                            break

                self.expect(")")

                # Print statements
                if name.endswith(("println", "print", "printf")):

                    values = ", ".join(arguments)

                    self.emit(f"PRINT {values}")

                    return "0"

                temp = self.new_temp()

                self.emit(
                    f"{temp} = CALL {name}, {len(arguments)}"
                )

                return temp

            return name

        raise SyntaxError(
            f"Invalid expression: '{token}'"
        )

    # ======================================
    # ASSIGNMENT
    # ======================================

    def parse_assignment(self, semicolon=True):

        name = self.advance()

        if name is None:
            raise SyntaxError("Expected variable name")

        while self.match("."):

            part = self.advance()

            if part is None:
                raise SyntaxError("Expected identifier after '.'")

            name += "." + part

        # Postfix increment / decrement
        if self.current() in ("++", "--"):

            operator = self.advance()

            sign = "+" if operator == "++" else "-"

            temp = self.new_temp()

            self.emit(f"{temp} = {name} {sign} 1")

            self.emit(f"{name} = {temp}")

        else:

            operator = self.current()

            if operator not in (
                "=", "+=", "-=", "*=", "/=", "%="
            ):

                raise SyntaxError(
                    f"Expected assignment operator, found '{operator}'"
                )

            self.advance()

            value = self.parse_expression()

            if operator != "=":

                actual_operator = operator[0]

                temp = self.new_temp()

                self.emit(
                    f"{temp} = {name} {actual_operator} {value}"
                )

                value = temp

            self.emit(f"{name} = {value}")

        if semicolon:
            self.expect(";")

    # ======================================
    # VARIABLE DECLARATION
    # ======================================

    def parse_declaration(self, semicolon=True):

        self.advance()  # Data type

        # Optional array brackets
        while self.match("["):
            self.expect("]")

        while True:

            name = self.advance()

            if name is None:
                raise SyntaxError("Expected variable name")

            if self.match("="):

                value = self.parse_expression()

                self.emit(f"{name} = {value}")

            else:

                self.emit(f"{name} = 0")

            if not self.match(","):
                break

        if semicolon:
            self.expect(";")

    # ======================================
    # BLOCK
    # ======================================

    def parse_block(self):

        self.expect("{")

        while self.current() is not None and self.current() != "}":

            self.parse_statement()

        self.expect("}")

    # ======================================
    # STATEMENT
    # ======================================

    def parse_statement(self):

        token = self.current()

        if token is None:
            return

        if token == "{":

            self.parse_block()

        elif token in self.TYPES:

            self.parse_declaration()

        elif token == "if":

            self.parse_if()

        elif token == "while":

            self.parse_while()

        elif token == "for":

            self.parse_for()

        elif token == "do":

            self.parse_do_while()

        elif token == "break":

            self.advance()
            self.expect(";")

            if not self.loop_stack:
                raise SyntaxError(
                    "break must be inside a loop"
                )

            self.emit(
                f"GOTO {self.loop_stack[-1]['break']}"
            )

        elif token == "continue":

            self.advance()
            self.expect(";")

            if not self.loop_stack:
                raise SyntaxError(
                    "continue must be inside a loop"
                )

            self.emit(
                f"GOTO {self.loop_stack[-1]['continue']}"
            )

        elif token == "return":

            self.advance()

            if self.current() != ";":

                value = self.parse_expression()

                self.emit(f"RETURN {value}")

            else:

                self.emit("RETURN")

            self.expect(";")

        elif token == ";":

            self.advance()

        else:

            # Detect assignment and increment/decrement
            if (
                re.fullmatch(
                    r'[A-Za-z_$][A-Za-z0-9_$]*',
                    token
                )
                and self.peek() in (
                    "=", "+=", "-=", "*=", "/=", "%=",
                    "++", "--"
                )
            ):

                self.parse_assignment()

            else:

                # Method call or expression statement
                self.parse_expression()

                self.expect(";")

    # ======================================
    # IF / ELSE
    # ======================================

    def parse_if(self):

        self.expect("if")
        self.expect("(")

        condition = self.parse_expression()

        self.expect(")")

        false_label = self.new_label()
        end_label = self.new_label()

        self.emit(
            f"IF_FALSE {condition} GOTO {false_label}"
        )

        self.parse_statement()

        if self.match("else"):

            self.emit(f"GOTO {end_label}")

            self.emit_label(false_label)

            self.parse_statement()

            self.emit_label(end_label)

        else:

            self.emit_label(false_label)

    # ======================================
    # WHILE LOOP
    # ======================================

    def parse_while(self):

        self.expect("while")

        start_label = self.new_label()
        body_label = self.new_label()
        end_label = self.new_label()

        self.emit_label(start_label)

        self.expect("(")

        condition = self.parse_expression()

        self.expect(")")

        self.emit(
            f"IF_TRUE {condition} GOTO {body_label}"
        )

        self.emit(f"GOTO {end_label}")

        self.emit_label(body_label)

        self.loop_stack.append({
            "break": end_label,
            "continue": start_label
        })

        self.parse_statement()

        self.loop_stack.pop()

        self.emit(f"GOTO {start_label}")

        self.emit_label(end_label)

    # ======================================
    # FOR LOOP
    # ======================================

    def parse_for(self):

        self.expect("for")
        self.expect("(")

        # Initialization
        if self.current() in self.TYPES:

            self.parse_declaration()

        elif self.current() != ";":

            self.parse_assignment()

        else:

            self.expect(";")

        start_label = self.new_label()
        body_label = self.new_label()
        update_label = self.new_label()
        end_label = self.new_label()

        self.emit_label(start_label)

        # Condition
        if self.current() != ";":

            condition = self.parse_expression()

        else:

            condition = "true"

        self.expect(";")

        self.emit(
            f"IF_TRUE {condition} GOTO {body_label}"
        )

        self.emit(f"GOTO {end_label}")

        self.emit_label(body_label)

        # Generate update instructions temporarily
        update_start = len(self.code)

        if self.current() != ")":

            while True:

                self.parse_assignment(semicolon=False)

                if not self.match(","):
                    break

        self.expect(")")

        update_code = self.code[update_start:]

        del self.code[update_start:]

        self.loop_stack.append({
            "break": end_label,
            "continue": update_label
        })

        self.parse_statement()

        self.loop_stack.pop()

        self.emit_label(update_label)

        self.code.extend(update_code)

        self.emit(f"GOTO {start_label}")

        self.emit_label(end_label)

    # ======================================
    # DO WHILE LOOP
    # ======================================

    def parse_do_while(self):

        self.expect("do")

        start_label = self.new_label()
        condition_label = self.new_label()
        end_label = self.new_label()

        self.emit_label(start_label)

        self.loop_stack.append({
            "break": end_label,
            "continue": condition_label
        })

        self.parse_statement()

        self.loop_stack.pop()

        self.emit_label(condition_label)

        self.expect("while")
        self.expect("(")

        condition = self.parse_expression()

        self.expect(")")
        self.expect(";")

        self.emit(
            f"IF_TRUE {condition} GOTO {start_label}"
        )

        self.emit_label(end_label)

    # ======================================
    # MAIN METHOD EXTRACTION
    # ======================================

    def generate(self):

        main_index = None

        for i, token in enumerate(self.tokens):

            if token == "main":

                main_index = i

                break

        if main_index is not None:

            index = main_index

            while (
                index < len(self.tokens)
                and self.tokens[index] != "{"
            ):

                index += 1

            if index >= len(self.tokens):

                raise SyntaxError(
                    "Main method body not found"
                )

            self.pos = index

            self.parse_block()

        else:

            # Standalone statements
            self.pos = 0

            while self.current() is not None:

                self.parse_statement()

        return self.code


# ==========================================
# TEST PROGRAM
# ==========================================

def run_test(title, source_code):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    try:

        generator = JavaIntermediateCodeGenerator(
            source_code
        )

        result = generator.generate()

        print("\nGenerated Intermediate Code:")

        if result:

            for instruction in result:

                print(instruction)

        else:

            print("No intermediate code generated.")

    except Exception as error:

        print("\nIntermediate Code Generation Failed!")

        print(error)


# ==========================================
# SAMPLE JAVA PROGRAM
# ==========================================

sample_code = """
public class Main {

    public static void main(String[] args) {

        int a = 10;
        int b = 20;
        int c = a + b;

        if (c > 20) {

            c = c + 5;

        } else {

            c = c - 5;

        }

        int i = 0;

        while (i < 3) {

            c = c + i;

            i++;

        }

        for (int j = 0; j < 3; j++) {

            c = c + j;

        }

        do {

            c = c - 1;

            i++;

        } while (i < 5);

        System.out.println(c);

        return 0;

    }

}
"""


if __name__ == "__main__":

    print(
        "\n========== JAVA INTERMEDIATE CODE GENERATION - PHASE 4 =========="
    )

    run_test(
        "TEST 1: BASIC CONSTRUCTS AND LOOPS",
        sample_code
    )
