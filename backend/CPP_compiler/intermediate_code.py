
class IntermediateCodeGenerator:

    def __init__(self):
        self.code = []
        self.temp_count = 0
        self.label_count = 0

    # Add instruction
    def emit(self, instruction):
        self.code.append(instruction)

    # Generate temporary variable
    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    # Generate label
    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    # Generate arithmetic expression TAC
    def generate_expression(self, expression):

        operators = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2
        }

        tokens = expression.split()
        output = []
        operator_stack = []

        # Infix to Postfix
        for token in tokens:

            if token.isalnum() or token.replace(".", "", 1).isdigit():
                output.append(token)

            elif token == "(":
                operator_stack.append(token)

            elif token == ")":

                while operator_stack and operator_stack[-1] != "(":
                    output.append(operator_stack.pop())

                if not operator_stack:
                    raise ValueError("Mismatched parentheses")

                operator_stack.pop()

            elif token in operators:

                while (
                    operator_stack
                    and operator_stack[-1] in operators
                    and operators[operator_stack[-1]] >= operators[token]
                ):
                    output.append(operator_stack.pop())

                operator_stack.append(token)

            else:
                raise ValueError(f"Invalid token: {token}")

        if "(" in operator_stack:
            raise ValueError("Mismatched parentheses")

        while operator_stack:
            output.append(operator_stack.pop())

        # Postfix to TAC
        stack = []

        for token in output:

            if token in operators:

                if len(stack) < 2:
                    raise ValueError("Invalid expression")

                right = stack.pop()
                left = stack.pop()

                temp = self.new_temp()

                self.emit(f"{temp} = {left} {token} {right}")

                stack.append(temp)

            else:
                stack.append(token)

        if len(stack) != 1:
            raise ValueError("Invalid expression")

        return stack[-1]

    # Generate assignment TAC
    def generate_assignment(self, statement):

        if "=" not in statement:
            raise ValueError("Invalid assignment statement")

        variable, expression = statement.split("=", 1)

        variable = variable.strip()
        expression = expression.strip().rstrip(";")

        if not variable or not expression:
            raise ValueError("Invalid assignment statement")

        result = self.generate_expression(expression)

        self.emit(f"{variable} = {result}")

    # Generate If-Else TAC
    def generate_if_else(self, condition, if_statements, else_statements):

        if_label = self.new_label()
        else_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"if {condition} goto {if_label}")
        self.emit(f"goto {else_label}")

        self.emit(f"{if_label}:")

        for statement in if_statements:
            self.generate_assignment(statement)

        self.emit(f"goto {end_label}")
        self.emit(f"{else_label}:")

        for statement in else_statements:
            self.generate_assignment(statement)

        self.emit(f"{end_label}:")

    # Generate While Loop TAC
    def generate_while(self, condition, statements):

        start_label = self.new_label()
        body_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{start_label}:")
        self.emit(f"if {condition} goto {body_label}")
        self.emit(f"goto {end_label}")

        self.emit(f"{body_label}:")

        for statement in statements:
            self.generate_assignment(statement)

        self.emit(f"goto {start_label}")
        self.emit(f"{end_label}:")

    # Generate For Loop TAC
    def generate_for(self, initialization, condition, update, statements):

        self.generate_assignment(initialization)

        start_label = self.new_label()
        body_label = self.new_label()
        end_label = self.new_label()

        self.emit(f"{start_label}:")
        self.emit(f"if {condition} goto {body_label}")
        self.emit(f"goto {end_label}")

        self.emit(f"{body_label}:")

        for statement in statements:
            self.generate_assignment(statement)

        self.generate_assignment(update)

        self.emit(f"goto {start_label}")
        self.emit(f"{end_label}:")

    # Generate Do-While Loop TAC
    def generate_do_while(self, statements, condition):

        start_label = self.new_label()

        self.emit(f"{start_label}:")

        for statement in statements:
            self.generate_assignment(statement)

        self.emit(f"if {condition} goto {start_label}")

    # Display generated code
    def display_code(self):

        print("\nGenerated Intermediate Code:")

        for instruction in self.code:
            print(instruction)


# Main function
def main():

    generator = IntermediateCodeGenerator()

    # Do-While Loop Test
    generator.generate_assignment("i = 0")

    statements = [
        "i = i + 1"
    ]

    condition = "i < 5"

    generator.generate_do_while(statements, condition)

    generator.display_code()


if __name__ == "__main__":
    main()
