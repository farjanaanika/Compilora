
class CodeOptimizer:
    def optimize(self, instructions):
        optimized = []
        constants = {}

        for instruction in instructions:
            parts = instruction.split()

            if len(parts) == 3 and parts[1] == "=":
                variable = parts[0]
                value = parts[2]

                if value.isdigit():
                    constants[variable] = value
                elif value in constants:
                    constants[variable] = constants[value]
                    instruction = f"{variable} = {constants[value]}"
                else:
                    constants.pop(variable, None)

            if instruction.startswith("PRINT "):
                variable = instruction[6:]

                if variable in constants:
                    instruction = f"PRINT {constants[variable]}"

            optimized.append(instruction)

        return optimized
