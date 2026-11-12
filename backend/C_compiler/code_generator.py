import re


class CodeGeneratorError(Exception):
    pass


class CodeGenerator:

    def __init__(self):
        self.target_code = []

    def emit(self, instruction):
        self.target_code.append(instruction)

    def generate(self, tac_code):
        self.target_code = []

        if not tac_code:
            raise CodeGeneratorError("No intermediate code provided.")

        for line in tac_code.splitlines():
            line = line.strip()

            if line:
                self.translate_instruction(line)

        return "\n".join(self.target_code)

    def translate_instruction(self, line):

        if line.startswith("FUNCTION "):
            name = line.replace("FUNCTION ", "").replace(":", "")
            self.emit(f"\n; Function: {name}")
            self.emit(f"{name} PROC")
            return

        if line.startswith("END FUNCTION"):
            self.emit("ENDP")
            return

        if line.endswith(":"):
            self.emit(line)
            return

        if line.startswith("goto "):
            self.emit(f"JMP {line.split(' ', 1)[1]}")
            return

        if line.startswith("ifFalse "):
            match = re.match(
                r"ifFalse\s+(\w+)\s+goto\s+(\w+)",
                line
            )

            if match:
                self.emit(f"CMP {match.group(1)}, 0")
                self.emit(f"JE {match.group(2)}")
            return

        if line.startswith("return"):
            parts = line.split(maxsplit=1)

            if len(parts) == 2:
                self.emit(f"MOV AX, {parts[1]}")

            self.emit("RET")
            return

        if " = " in line:
            left, right = line.split(" = ", 1)

            increment = re.match(
                r"postfix \+\+(\w+)",
                right
            )

            decrement = re.match(
                r"postfix --(\w+)",
                right
            )

            if increment:
                variable = increment.group(1)
                self.emit(f"MOV {left}, {variable}")
                self.emit(f"INC {variable}")
                return

            if decrement:
                variable = decrement.group(1)
                self.emit(f"MOV {left}, {variable}")
                self.emit(f"DEC {variable}")
                return

            comparison_ops = [
                (" <= ", "SETLE"),
                (" >= ", "SETGE"),
                (" == ", "SETE"),
                (" != ", "SETNE"),
                (" < ", "SETL"),
                (" > ", "SETG")
            ]

            for op, instruction in comparison_ops:
                if op in right:
                    first, second = right.split(op, 1)
                    self.emit(f"CMP {first}, {second}")
                    self.emit(f"{instruction} {left}")
                    return

            arithmetic_ops = [
                (" + ", "ADD"),
                (" - ", "SUB"),
                (" * ", "MUL"),
                (" / ", "DIV")
            ]

            for op, instruction in arithmetic_ops:
                if op in right:
                    first, second = right.split(op, 1)
                    self.emit(f"MOV AX, {first}")
                    self.emit(f"{instruction} AX, {second}")
                    self.emit(f"MOV {left}, AX")
                    return

            self.emit(f"MOV {left}, {right}")
            return

        if line.startswith("param "):
            self.emit(f"PUSH {line[6:]}")
            return

        if line.startswith("call "):
            self.emit(f"CALL {line[5:]}")
            return

        self.emit(f"; Unsupported TAC: {line}")


if __name__ == "__main__":

    generator = CodeGenerator()

    sample = """FUNCTION main:
a = 10
b = 20
t1 = a + b
t2 = a <= b
t3 = postfix ++a
return t1
END FUNCTION main"""

    print(generator.generate(sample))