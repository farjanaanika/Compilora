
class CodeGeneratorError(Exception):
    pass


class CodeGenerator:
    def generate(self, instructions):
        output = [
            "#include <iostream>",
            "using namespace std;",
            ""
        ]

        indent = 1
        if_stack = []
        loop_stack = []

        label_positions = {}

        for i, instruction in enumerate(instructions):
            if instruction.startswith("LABEL "):
                label_positions[instruction[6:]] = i

        loop_exits = set()
        loop_starts = set()
        do_while_loops = {}

        for i, instruction in enumerate(instructions):
            if not instruction.startswith("IF_FALSE "):
                continue

            exit_label = instruction.rsplit(" GOTO ", 1)[1]

            for j in range(i + 1, len(instructions)):
                current = instructions[j]

                if current == f"LABEL {exit_label}":
                    break

                if current.startswith("GOTO "):
                    target = current[5:]

                    if (
                        target in label_positions
                        and label_positions[target] < i
                    ):
                        loop_exits.add(exit_label)
                        loop_starts.add(target)

                        if (
                            label_positions[target] + 1 < i
                            and instructions[label_positions[target] + 1]
                            .startswith("PRINT ")
                        ):
                            do_while_loops[target] = {
                                "exit": exit_label,
                                "condition": instruction[9:].rsplit(
                                    " GOTO ", 1
                                )[0]
                            }

                        break
  
        index = 0

        while index < len(instructions):
            instruction = instructions[index]
            parts = instruction.split()
            if instruction.startswith("FUNCTION "):
                function_info = instruction.split()

                return_type = function_info[1]
                function_name = function_info[2]

                if function_name == "main":
                    output.append("")
                    output.append("int main() {")
                    indent = 1
                else:
                    output.append(
                        f"{return_type} {function_name}() {{"
                    )
                    indent = 1

                index += 1
                continue

            elif instruction == "END FUNCTION":
                output.append("}")
                index += 1
                continue
            elif instruction.startswith("PARAM "):
                parameter = instruction[6:]

                if output and output[-1].endswith(") {"):
                    existing = output[-1][:-3]

                    if existing.endswith("("):
                        output[-1] = existing + parameter + ") {"
                    else:
                        output[-1] = (
                            existing + ", " + parameter + ") {"
                        )

            elif instruction.startswith("DECLARE ") and " = CALL " in instruction:
                declaration = instruction[8:]
                variable_type, remaining = declaration.split(" ", 1)
                variable_name, call = remaining.split(" = CALL ", 1)

                output.append(
                    "    " * indent
                    + f"{variable_type} {variable_name} = {call.replace(' ', '', 1)};"
                )
            elif instruction.startswith("DECLARE "):
                output.append(
                    "    " * indent + instruction[8:] + ";"
                )

            elif instruction.startswith("PRINT "):
                value = instruction[6:]

                if value == "NEWLINE":
                    output.append(
                        "    " * indent + "cout << endl;"
                    )
                else:
                    output.append(
                        "    " * indent + f"cout << {value};"
                    )

            elif instruction.startswith("READ "):
                variable = instruction[5:]

                output.append(
                    "    " * indent + f"cin >> {variable};"
                )

            elif instruction.startswith("RETURN "):
                value = instruction[7:]

                value = value.replace("CALL ", "")
                value = value.replace(" (", "(")

                output.append(
                    "    " * indent + f"return {value};"
                )

            elif instruction.startswith("IF_FALSE "):
                condition, target = instruction[9:].rsplit(" GOTO ", 1)

                if any(
                    loop["exit"] == target
                    for loop in do_while_loops.values()
                ):
                    pass

                elif target in loop_exits:
                    output.append(
                        "    " * indent + f"while ({condition}) {{"
                    )

                    indent += 1
                    loop_stack.append(target)

                else:
                    output.append(
                        "    " * indent + f"if ({condition}) {{"
                    )

                    indent += 1

                    if_stack.append({
                        "false_label": target,
                        "end_label": None,
                        "in_else": False
                    })

            elif instruction.startswith("GOTO "):
                target = instruction[5:]

                if loop_stack and target in loop_starts:
                    pass

                elif if_stack and not if_stack[-1]["in_else"]:
                    if_stack[-1]["end_label"] = target

                else:
                    raise CodeGeneratorError(
                        f"Unsupported jump target: {target}"
                    )



            elif instruction.startswith("LABEL "):
                label = instruction[6:]

                if label in do_while_loops:
                    
                    current_loop = do_while_loops[label]

                    output.append(
                        "    " * indent + "do {"
                    )

                    indent += 1

                    loop_stack.append({
                        "exit": current_loop["exit"],
                        "condition": current_loop["condition"],
                        "type": "do_while"
                    })
                elif (
                    loop_stack
                    and isinstance(loop_stack[-1], dict)
                    and label == loop_stack[-1]["exit"]
                ):
                    current_loop = loop_stack.pop()

                    indent -= 1

                    output.append(
                        "    " * indent
                        + "} while (" + current_loop["condition"] + ");"
                    )

                elif loop_stack and label in loop_exits:
                    indent -= 1

                    output.append(
                        "    " * indent + "}"
                    )

                    loop_stack.pop()

                elif if_stack:
                    current_if = if_stack[-1]

                    if label == current_if["false_label"]:
                        indent -= 1

                        output.append(
                            "    " * indent + "}"
                        )

                        if current_if["end_label"]:
                            output.append(
                                "    " * indent + "else {"
                            )

                            indent += 1
                            current_if["in_else"] = True

                        else:
                            if_stack.pop()

                    elif label == current_if["end_label"]:
                        indent -= 1

                        output.append(
                            "    " * indent + "}"
                        )

                        if_stack.pop()
            elif len(parts) >= 3 and parts[1] == "=":
                output.append(
                    "    " * indent + instruction + ";"
                )

            else:
                raise CodeGeneratorError(
                    f"Unsupported instruction: {instruction}"
                )

            index += 1

        if if_stack or loop_stack:
            raise CodeGeneratorError(
                "Unclosed conditional or loop block."
            )

        return "\n".join(output)
