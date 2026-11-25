
import re


class CodeGenerator:

    def __init__(self, intermediate_code=None):
        self.intermediate_code = intermediate_code or []
        self.target_code = []

    # Add target instruction
    def emit(self, instruction):
        self.target_code.append(instruction)

    # Check whether operand is a number
    def is_number(self, value):
        return re.fullmatch(r"-?\d+(\.\d+)?", value.strip()) is not None

    # Load operand into accumulator
    def load_operand(self, operand):

        operand = operand.strip()

        if self.is_number(operand):
            self.emit(f"LOADI {operand}")
        else:
            self.emit(f"LOAD {operand}")

    # Generate assignment instruction
    def generate_assignment(self, variable, expression):

        variable = variable.strip()
        expression = expression.strip()

        # Arithmetic expression
        pattern = (
            r"^([A-Za-z_]\w*|-?\d+(?:\.\d+)?)\s*"
            r"([+\-*/])\s*"
            r"([A-Za-z_]\w*|-?\d+(?:\.\d+)?)$"
        )

        match = re.fullmatch(pattern, expression)

        if match:

            left, operator, right = match.groups()

            self.load_operand(left)

            instructions = {
                "+": "ADD",
                "-": "SUB",
                "*": "MUL",
                "/": "DIV"
            }

            if operator == "/" and self.is_number(right) and float(right) == 0:
                raise ValueError("Division by zero")

            self.emit(f"{instructions[operator]} {right}")
            self.emit(f"STORE {variable}")

        else:

            # Simple assignment
            self.load_operand(expression)
            self.emit(f"STORE {variable}")

    # Generate conditional jump
    def generate_condition(self, instruction):

        pattern = (
            r"^if\s+(\S+)\s*"
            r"(<=|>=|==|!=|<|>)\s*"
            r"(\S+)\s+goto\s+([A-Za-z_]\w*)$"
        )

        match = re.fullmatch(pattern, instruction)

        if not match:
            raise ValueError(
                f"Invalid conditional instruction: {instruction}"
            )

        left, operator, right, label = match.groups()

        self.emit(f"CMP {left}, {right}")

        jump_instructions = {
            "<": "JLT",
            ">": "JGT",
            "<=": "JLE",
            ">=": "JGE",
            "==": "JE",
            "!=": "JNE"
        }

        self.emit(f"{jump_instructions[operator]} {label}")

    # Generate one TAC instruction
    def generate_instruction(self, instruction):

        instruction = instruction.strip()

        if not instruction:
            return

        # Label
        if instruction.endswith(":"):

            label = instruction[:-1].strip()
            self.emit(f"LABEL {label}")
            return

        # Conditional jump
        if instruction.startswith("if "):

            self.generate_condition(instruction)
            return

        # Unconditional jump
        if instruction.startswith("goto "):

            label = instruction[5:].strip()
            self.emit(f"JMP {label}")
            return

        # Return statement
        if instruction == "return":

            self.emit("RET")
            return

        if instruction.startswith("return "):

            value = instruction[7:].strip()
            self.load_operand(value)
            self.emit("RET")
            return

        # Assignment
        if "=" in instruction:

            variable, expression = instruction.split("=", 1)

            self.generate_assignment(variable, expression)
            return

        raise ValueError(
            f"Unsupported intermediate instruction: {instruction}"
        )

    # Generate target code from all TAC instructions
    def generate(self):

        self.target_code = []

        for instruction in self.intermediate_code:
            self.generate_instruction(instruction)

        return self.target_code

    # Display generated target code
    def display_code(self):

        print("\nGenerated Target Code:")

        for index, instruction in enumerate(self.target_code, start=1):
            print(f"{index}. {instruction}")


# Main function
def main():

    intermediate_code = [
        "i = 0",
        "L1:",
        "if i < 5 goto L2",
        "goto L3",
        "L2:",
        "t1 = i + 1",
        "i = t1",
        "goto L1",
        "L3:",
        "return 0"
    ]

    generator = CodeGenerator(intermediate_code)

    generator.generate()

    generator.display_code()


if __name__ == "__main__":
    main()
