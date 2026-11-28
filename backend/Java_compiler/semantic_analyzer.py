
from lexer import JavaLexer


class JavaSemanticAnalyzer:

    TYPES = {
        "int", "float", "double", "char",
        "boolean", "String", "long", "short", "byte"
    }

    BUILTINS = {
        "System", "out", "in", "print", "println",
        "printf", "Math", "Scanner"
    }

    def __init__(self, tokens):
        self.tokens = tokens
        self.errors = []
        self.symbols = {}
        self.declaration_positions = set()
        self.parameter_positions = set()
        self.class_names = set()
        self.method_names = set()
        self.loop_ranges = []

    def value(self, i):
        if 0 <= i < len(self.tokens):
            return self.tokens[i]["value"]
        return None

    def token_type(self, i):
        if 0 <= i < len(self.tokens):
            return self.tokens[i]["type"]
        return None

    def add_error(self, token, message):
        self.errors.append(
            f"Line {token['line']}, Column {token['column']}: {message}"
        )

    # -----------------------------------------
    # PHASE 1: Collect class and method names
    # -----------------------------------------

    def collect_class_and_method_names(self):

        for i, token in enumerate(self.tokens):

            if token["value"] == "class":
                if self.token_type(i + 1) == "IDENTIFIER":
                    self.class_names.add(self.value(i + 1))

            if (
                token["type"] == "IDENTIFIER"
                and self.value(i + 1) == "("
                and i > 0
                and self.value(i - 1) in self.TYPES | {"void"}
            ):
                self.method_names.add(token["value"])

    # -----------------------------------------
    # PHASE 2: Collect method parameters
    # -----------------------------------------

    def collect_parameters(self):

        for i, token in enumerate(self.tokens):

            if token["value"] != "(":
                continue

            if i == 0 or self.token_type(i - 1) != "IDENTIFIER":
                continue

            method_name = self.value(i - 1)

            if method_name not in self.method_names:
                continue

            j = i + 1

            while j < len(self.tokens) and self.value(j) != ")":

                if self.value(j) in self.TYPES:

                    type_name = self.value(j)
                    name_index = j + 1

                    while (
                        self.value(name_index) == "["
                        and self.value(name_index + 1) == "]"
                    ):
                        name_index += 2

                    if self.token_type(name_index) == "IDENTIFIER":

                        name = self.value(name_index)

                        self.symbols[name] = type_name
                        self.declaration_positions.add(name_index)
                        self.parameter_positions.add(name_index)

                        j = name_index + 1

                    else:
                        j += 1

                else:
                    j += 1

    # -----------------------------------------
    # PHASE 3: Variable declarations
    # -----------------------------------------

    def collect_declarations(self):

        for i, token in enumerate(self.tokens):

            if token["value"] not in self.TYPES:
                continue

            name_index = i + 1

            while (
                self.value(name_index) == "["
                and self.value(name_index + 1) == "]"
            ):
                name_index += 2

            if self.token_type(name_index) != "IDENTIFIER":
                continue

            name = self.value(name_index)

            # Method declaration
            if self.value(name_index + 1) == "(":
                continue

            # Already registered parameter
            if name_index in self.parameter_positions:
                continue

            if name in self.symbols:
                self.add_error(
                    self.tokens[name_index],
                    f"Duplicate declaration of variable '{name}'"
                )
            else:
                self.symbols[name] = token["value"]

            self.declaration_positions.add(name_index)

    # -----------------------------------------
    # PHASE 4: Type inference
    # -----------------------------------------

    def infer_type(self, token_index):

        if token_index >= len(self.tokens):
            return None

        token = self.tokens[token_index]
        value = token["value"]
        kind = token["type"]

        if kind == "STRING":
            return "String"

        if kind == "CHAR":
            return "char"

        if kind == "NUMBER":

            if "." in str(value):
                return "double"

            return "int"

        if value in {"true", "false"}:
            return "boolean"

        if kind == "IDENTIFIER":
            return self.symbols.get(value)

        return None

    # -----------------------------------------
    # PHASE 5: Assignment type checking
    # -----------------------------------------

    def check_assignments(self):

        for i, token in enumerate(self.tokens):

            if token["type"] != "IDENTIFIER":
                continue

            name = token["value"]

            if name not in self.symbols:
                continue

            if self.value(i + 1) != "=":
                continue

            target_type = self.symbols[name]
            source_type = self.infer_type(i + 2)

            if source_type is None:
                continue

            numeric_types = {
                "int", "long", "short", "byte", "float", "double"
            }

            if target_type in numeric_types and source_type in numeric_types:
                continue

            if target_type != source_type:

                self.add_error(
                    self.tokens[i + 2],
                    f"Type mismatch: cannot assign {source_type} to {target_type}"
                )

    # -----------------------------------------
    # PHASE 6: Undeclared identifier checking
    # -----------------------------------------

    def check_undeclared_identifiers(self):

        for i, token in enumerate(self.tokens):

            if token["type"] != "IDENTIFIER":
                continue

            name = token["value"]

            if name in self.BUILTINS:
                continue

            if name in self.class_names or name in self.method_names:
                continue

            if i in self.declaration_positions:
                continue

            if i > 0 and self.value(i - 1) == ".":
                continue

            if self.value(i + 1) == "(":
                continue

            if name in self.symbols:
                continue

            if i > 0 and self.value(i - 1) in {"package", "import"}:
                continue

            self.add_error(
                token,
                f"Undeclared identifier '{name}'"
            )

    # -----------------------------------------
    # PHASE 7: Condition checking
    # -----------------------------------------

    def check_condition(self, start, end):

        relational_operators = {
            "<", ">", "<=", ">=", "==", "!=",
            "&&", "||"
        }

        condition_values = [
            self.value(i) for i in range(start, end)
        ]

        if any(v in relational_operators for v in condition_values):
            return

        if "!" in condition_values:
            return

        if len(condition_values) == 1:

            condition_type = self.infer_type(start)

            if condition_type == "boolean":
                return

            if condition_type is not None:
                self.add_error(
                    self.tokens[start],
                    "Condition must be boolean"
                )

    def matching_parenthesis(self, start):

        depth = 0

        for i in range(start, len(self.tokens)):

            if self.value(i) == "(":
                depth += 1

            elif self.value(i) == ")":
                depth -= 1

                if depth == 0:
                    return i

        return None

    def check_conditions(self):

        for i, token in enumerate(self.tokens):

            if token["value"] not in {"if", "while"}:
                continue

            if self.value(i + 1) != "(":
                continue

            end = self.matching_parenthesis(i + 1)

            if end is None:
                continue

            self.check_condition(i + 2, end)

        # For-loop condition: second section
        for i, token in enumerate(self.tokens):

            if token["value"] != "for":
                continue

            if self.value(i + 1) != "(":
                continue

            end = self.matching_parenthesis(i + 1)

            if end is None:
                continue

            semicolons = [
                j for j in range(i + 2, end)
                if self.value(j) == ";"
            ]

            if len(semicolons) >= 2:

                self.check_condition(
                    semicolons[0] + 1,
                    semicolons[1]
                )

    # -----------------------------------------
    # PHASE 8: Loop range detection
    # -----------------------------------------

    def find_statement_end(self, start):

        if self.value(start) == "{":

            depth = 0

            for i in range(start, len(self.tokens)):

                if self.value(i) == "{":
                    depth += 1

                elif self.value(i) == "}":
                    depth -= 1

                    if depth == 0:
                        return i

        else:

            for i in range(start, len(self.tokens)):

                if self.value(i) == ";":
                    return i

        return start

    def collect_loop_ranges(self):

        for i, token in enumerate(self.tokens):

            if token["value"] not in {"for", "while"}:
                continue

            if self.value(i + 1) != "(":
                continue

            condition_end = self.matching_parenthesis(i + 1)

            if condition_end is None:
                continue

            body_start = condition_end + 1
            body_end = self.find_statement_end(body_start)

            self.loop_ranges.append((body_start, body_end))

        # do-while body
        for i, token in enumerate(self.tokens):

            if token["value"] != "do":
                continue

            body_start = i + 1
            body_end = self.find_statement_end(body_start)

            self.loop_ranges.append((body_start, body_end))

    # -----------------------------------------
    # PHASE 9: Break and Continue validation
    # -----------------------------------------

    def check_loop_control(self):

        for i, token in enumerate(self.tokens):

            if token["value"] not in {"break", "continue"}:
                continue

            inside_loop = False

            for start, end in self.loop_ranges:

                if start <= i <= end:
                    inside_loop = True
                    break

            if not inside_loop:

                self.add_error(
                    token,
                    f"'{token['value']}' statement must be inside a loop"
                )

    # -----------------------------------------
    # MAIN SEMANTIC ANALYSIS
    # -----------------------------------------

    def analyze(self):

        self.collect_class_and_method_names()
        self.collect_parameters()
        self.collect_declarations()

        self.check_assignments()
        self.check_undeclared_identifiers()
        self.check_conditions()

        self.collect_loop_ranges()
        self.check_loop_control()

        if self.errors:

            print("\nSemantic Analysis Failed!")

            for error in self.errors:
                print(error)

            return False

        print("\nSemantic Analysis Successful!")
        print("No Semantic Errors Found.")

        return True


# -----------------------------------------
# TEST CASES
# -----------------------------------------

def run_test(test_name, source_code):

    print("\n" + "=" * 55)
    print(test_name)
    print("=" * 55)

    lexer = JavaLexer(source_code)
    tokens = lexer.tokenize()

    analyzer = JavaSemanticAnalyzer(tokens)
    analyzer.analyze()


if __name__ == "__main__":

    valid_code = """
    class Main {
        public static void main(String[] args) {

            int a = 10;
            int b = 20;
            int sum = a + b;
            boolean flag = true;

            sum = sum + a;

            if (sum > 20) {
                System.out.println(sum);
            } else {
                System.out.println(a);
            }

            while (a < 15) {
                a = a + 1;
            }

            for (int i = 0; i < 5; i++) {
                sum = sum + i;
            }

            do {
                b = b - 1;
            } while (b > 10);

            return;
        }
    }
    """

    undeclared_code = """
    class Main {
        public static void main(String[] args) {
            int a = 10;
            b = 20;
        }
    }
    """

    duplicate_code = """
    class Main {
        public static void main(String[] args) {
            int a = 10;
            int a = 20;
        }
    }
    """

    type_error_code = """
    class Main {
        public static void main(String[] args) {
            int a = "hello";
        }
    }
    """

    break_error_code = """
    class Main {
        public static void main(String[] args) {
            int a = 10;
            break;
        }
    }
    """

    print("========== JAVA SEMANTIC ANALYZER - PHASE 3 ==========")

    run_test("TEST 1: VALID BASIC CONSTRUCT AND LOOPS", valid_code)
    run_test("TEST 2: UNDECLARED VARIABLE", undeclared_code)
    run_test("TEST 3: DUPLICATE DECLARATION", duplicate_code)
    run_test("TEST 4: TYPE MISMATCH", type_error_code)
    run_test("TEST 5: BREAK OUTSIDE LOOP", break_error_code)
