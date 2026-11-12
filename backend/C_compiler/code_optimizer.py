class CodeOptimizer:

    def __init__(self):
        self.optimized_code = []

    def constant_folding(self, code):
        self.optimized_code = []

        for line in code.splitlines():
            line = line.strip()

            if "=" in line and not any(
                op in line for op in ["==", "!=", "<=", ">="]
            ):
                parts = line.split("=", 1)
                variable = parts[0].strip()
                expression = parts[1].strip()

                try:
                    result = eval(expression, {"__builtins__": {}}, {})

                    if isinstance(result, (int, float)):
                        line = f"{variable} = {result}"
                except:
                    pass

            self.optimized_code.append(line)

        return "\n".join(self.optimized_code)



    def constant_propagation(self, code):
        import re

        constants = {}
        optimized = []

        for line in code.splitlines():
            stripped = line.strip()

            if (
                not stripped
                or stripped.endswith(":")
                or stripped.startswith("goto")
                or stripped.startswith("ifFalse")
                or stripped.startswith("FUNCTION")
                or stripped.startswith("END FUNCTION")
                or stripped.startswith("param")
                or "call " in stripped
            ):
                if (
                    stripped.endswith(":")
                    or stripped.startswith("goto")
                    or stripped.startswith("ifFalse")
                ):
                    constants.clear()

                optimized.append(line)
                continue

            if "=" in stripped and not any(
                op in stripped for op in ["==", "!=", "<=", ">="]
            ):
                variable, expression = stripped.split("=", 1)

                variable = variable.strip()
                expression = expression.strip()

                for name, value in constants.items():
                    expression = re.sub(
                        rf"\b{re.escape(name)}\b",
                        str(value),
                        expression
                    )

                try:
                    result = eval(
                        expression,
                        {"__builtins__": {}},
                        {}
                    )

                    if isinstance(result, (int, float)):
                        constants[variable] = result
                        expression = str(result)
                    else:
                        constants.pop(variable, None)

                except:
                    constants.pop(variable, None)

                optimized.append(f"{variable} = {expression}")

            else:
                optimized.append(line)

        return "\n".join(optimized)


    def dead_code_elimination(self, code):
        import re

        lines = code.splitlines()
        used_variables = set()
        optimized_code = []

        for line in lines:
            stripped = line.strip()

            if (
                stripped.startswith("print")
                or stripped.startswith("return")
                or stripped.startswith("ifFalse")
                or stripped.startswith("param")
            ):
                used_variables.update(
                    re.findall(r"\b[a-zA-Z_]\w*\b", stripped)
                )

        for line in reversed(lines):
            stripped = line.strip()

            if not stripped:
                continue

            if (
                stripped.startswith("FUNCTION")
                or stripped.startswith("END FUNCTION")
                or stripped.endswith(":")
                or stripped.startswith("goto")
                or stripped.startswith("ifFalse")
                or stripped.startswith("return")
                or stripped.startswith("print")
                or stripped.startswith("param")
                or "call " in stripped
            ):
                optimized_code.append(line)
                continue

            match = re.match(
                r"^([a-zA-Z_]\w*)\s*=\s*(.*)$",
                stripped
            )

            if match:
                variable = match.group(1)
                expression = match.group(2)

                # Preserve operations that change program state.
                if (
                    "++" in expression
                    or "--" in expression
                    or "call " in expression
                ):
                    optimized_code.append(line)
                    used_variables.update(
                        re.findall(r"\b[a-zA-Z_]\w*\b", expression)
                    )
                    continue

                if variable in used_variables:
                    optimized_code.append(line)
                    used_variables.discard(variable)
                    used_variables.update(
                        re.findall(r"\b[a-zA-Z_]\w*\b", expression)
                    )

            else:
                optimized_code.append(line)

        optimized_code.reverse()

        return "\n".join(optimized_code)

    def strength_reduction(self, code):
        import re

        optimized = []

        for line in code.splitlines():
            match = re.match(
                r"^(\w+)\s*=\s*(\w+)\s*\*\s*2$",
                line.strip()
            )

            if match:
                variable = match.group(1)
                operand = match.group(2)
                line = f"{variable} = {operand} + {operand}"

            optimized.append(line)

        return "\n".join(optimized)

    def optimize(self, code):
        print("\nSTEP 1: CONSTANT FOLDING")
        code = self.constant_folding(code)
        print(code)

        print("\nSTEP 2: CONSTANT PROPAGATION")
        code = self.constant_propagation(code)
        print(code)

        print("\nSTEP 3: DEAD CODE ELIMINATION")
        code = self.dead_code_elimination(code)
        print(code)

        print("\nSTEP 4: STRENGTH REDUCTION")
        code = self.strength_reduction(code)
        print(code)
        return code
    
if __name__ == "__main__":

    optimizer = CodeOptimizer()

    test_code = """
a = 10
b = 20
c = a + b
d = 50
print(c)
"""

    print("ORIGINAL CODE:")
    print(test_code)

    print("\nFINAL OPTIMIZED CODE:")
    result = optimizer.optimize(test_code)
    print(result)
    def strength_reduction(self, code):
        import re

        optimized = []

        for line in code.splitlines():
            match = re.match(
                r"^(\w+)\s*=\s*(\w+)\s*\*\s*2$",
                line.strip()
            )

            if match:
                variable = match.group(1)
                operand = match.group(2)
                line = f"{variable} = {operand} + {operand}"

            optimized.append(line)

        return "\n".join(optimized)

