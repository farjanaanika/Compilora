
import re


class CodeOptimizer:

    def __init__(self, intermediate_code=None):
        self.code = intermediate_code or []
        self.optimized_code = []

    # Check whether a value is an integer
    def is_number(self, value):
        return re.fullmatch(r"-?\d+", value.strip()) is not None

    # Perform arithmetic calculation
    def calculate(self, left, operator, right):

        a = int(left)
        b = int(right)

        if operator == "+":
            return str(a + b)

        elif operator == "-":
            return str(a - b)

        elif operator == "*":
            return str(a * b)

        elif operator == "/":
            if b == 0:
                return None

            return str(int(a / b))

        return None

    # Constant Folding
    def constant_folding(self, code):

        optimized = []

        pattern = r"^(-?\d+)\s*([+\-*/])\s*(-?\d+)$"

        for instruction in code:

            if "=" not in instruction:
                optimized.append(instruction)
                continue

            variable, expression = instruction.split("=", 1)

            variable = variable.strip()
            expression = expression.strip()

            match = re.fullmatch(pattern, expression)

            if match:

                left, operator, right = match.groups()

                result = self.calculate(left, operator, right)

                if result is not None:
                    expression = result

            optimized.append(f"{variable} = {expression}")

        return optimized

    # Constant Propagation
    def constant_propagation(self, code):

        optimized = []
        constants = {}

        binary_pattern = (
            r"^(-?\d+|[A-Za-z_]\w*)\s*"
            r"([+\-*/])\s*"
            r"(-?\d+|[A-Za-z_]\w*)$"
        )

        for instruction in code:

            instruction = instruction.strip()

            if not instruction:
                continue

            # Clear constants at control-flow boundaries
            if (
                instruction.endswith(":")
                or instruction.startswith("goto ")
                or instruction.startswith("if ")
            ):
                constants.clear()
                optimized.append(instruction)
                continue

            if "=" not in instruction:
                optimized.append(instruction)
                continue

            variable, expression = instruction.split("=", 1)

            variable = variable.strip()
            expression = expression.strip()

            # Replace known constants
            tokens = re.findall(r"[A-Za-z_]\w*|-?\d+|[+\-*/]", expression)

            for token in tokens:
                if token in constants:
                    expression = re.sub(
                        rf"\b{re.escape(token)}\b",
                        constants[token],
                        expression
                    )

            # Evaluate binary expressions
            match = re.fullmatch(binary_pattern, expression)

            if match:

                left, operator, right = match.groups()

                if self.is_number(left) and self.is_number(right):

                    result = self.calculate(left, operator, right)

                    if result is not None:
                        expression = result

            optimized.append(f"{variable} = {expression}")

            # Update constant information
            if self.is_number(expression):
                constants[variable] = expression

            else:
                constants.pop(variable, None)

        return optimized

    # Algebraic Simplification
    def algebraic_simplification(self, code):

        optimized = []

        pattern = (
            r"^([A-Za-z_]\w*|-?\d+)\s*"
            r"([+\-*/])\s*"
            r"([A-Za-z_]\w*|-?\d+)$"
        )

        for instruction in code:

            if "=" not in instruction:
                optimized.append(instruction)
                continue

            variable, expression = instruction.split("=", 1)

            variable = variable.strip()
            expression = expression.strip()

            match = re.fullmatch(pattern, expression)

            if match:

                left, operator, right = match.groups()

                if operator == "+":
                    if right == "0":
                        expression = left
                    elif left == "0":
                        expression = right

                elif operator == "-":
                    if right == "0":
                        expression = left

                elif operator == "*":
                    if right == "1":
                        expression = left
                    elif left == "1":
                        expression = right
                    elif right == "0" or left == "0":
                        expression = "0"

                elif operator == "/":
                    if right == "1":
                        expression = left

            optimized.append(f"{variable} = {expression}")

        return optimized

    # Dead Code Elimination
    def dead_code_elimination(self, code):

        optimized = []
        used_variables = set()

        for instruction in reversed(code):

            instruction = instruction.strip()

            if not instruction:
                continue

            if "=" in instruction:

                variable, expression = instruction.split("=", 1)

                variable = variable.strip()
                expression = expression.strip()

                # Remove unused temporary variables only
                if (
                    re.fullmatch(r"t\d+", variable)
                    and variable not in used_variables
                ):
                    continue

                used_variables.discard(variable)

                identifiers = re.findall(
                    r"\b[A-Za-z_]\w*\b",
                    expression
                )

                used_variables.update(identifiers)

                optimized.append(instruction)

            else:

                identifiers = re.findall(
                    r"\b[A-Za-z_]\w*\b",
                    instruction
                )

                used_variables.update(identifiers)

                optimized.append(instruction)

        optimized.reverse()

        return optimized

    # Run all optimization techniques
    def optimize(self):

        code = self.code.copy()

        code = self.constant_folding(code)

        code = self.constant_propagation(code)

        code = self.algebraic_simplification(code)

        code = self.dead_code_elimination(code)

        self.optimized_code = code

        return self.optimized_code

    # Display optimized code
    def display_code(self):

        print("\nOriginal Intermediate Code:")

        for instruction in self.code:
            print(instruction)

        print("\nOptimized Intermediate Code:")

        for instruction in self.optimized_code:
            print(instruction)


# Main function
def main():

    intermediate_code = [
        "a = 10",
        "b = 20",
        "t1 = a + b",
        "t2 = t1 * 1",
        "t3 = t2 + 0",
        "result = t3",
        "t4 = 5 * 0"
    ]

    optimizer = CodeOptimizer(intermediate_code)

    optimizer.optimize()

    optimizer.display_code()


if __name__ == "__main__":
    main()
