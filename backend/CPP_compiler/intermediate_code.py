
class IntermediateCodeError(Exception):
    pass


class IntermediateCodeGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def generate_from_ast(self, ast):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0

        for statement in ast["body"]:
            if statement["type"] == "Function":
                self.generate_function(statement)

        return self.instructions

    def generate_function(self, function):
        self.instructions.append(
            f"FUNCTION {function['return_type']} {function['name']}"
        )

        for parameter in function.get("parameters", []):
            self.instructions.append(
                f"PARAM {parameter['data_type']} {parameter['name']}"
            )

        for statement in function["body"]:
            self.generate_statement(statement)

        self.instructions.append("END FUNCTION")


    def generate_expression(self, expression):
        if isinstance(expression, dict):

            if expression.get("type") == "Endl":
                return "NEWLINE"

            if expression.get("type") == "FunctionCall":
                arguments = []

                for argument in expression["arguments"]:
                    arguments.append(
                        self.generate_expression(argument)
                    )

                return (
                    f"CALL {expression['name']} "
                    f"({', '.join(arguments)})"
                )

            if expression.get("type") == "BinaryExpression":
                left = self.generate_expression(expression["left"])
                operator = expression["operator"]
                right = self.generate_expression(expression["right"])

                return f"{left} {operator} {right}"

        return str(expression)

    def generate_statement(self, statement):
        kind = statement["type"]

        if kind == "Declaration":
            value = self.generate_expression(statement["value"])

            self.instructions.append(
                f"DECLARE {statement['data_type']} "
                f"{statement['name']} = {value}"
            )

        elif kind == "Assignment":
            value = self.generate_expression(statement["value"])
            self.instructions.append(
                f"{statement['name']} = {value}"
            )

        elif kind == "Output":
            for value in statement["values"]:
                result = self.generate_expression(value)
                self.instructions.append(f"PRINT {result}")

        elif kind == "Input":
            for name in statement["variables"]:
                self.instructions.append(f"READ {name}")

        elif kind == "Return":
            value = self.generate_expression(statement["value"])
            self.instructions.append(f"RETURN {value}")

        elif kind == "If":
            self.generate_if(statement)

        elif kind == "While":
            self.generate_while(statement)
        elif kind == "DoWhile":
            self.generate_do_while(statement)
        elif kind == "For":
            self.generate_for(statement)

        else:
            raise IntermediateCodeError(
                f"Unsupported statement: {kind}"
            )


    def generate_if(self, statement):
        else_label = self.new_label()
        end_label = self.new_label()

        condition = self.generate_expression(
            statement["condition"]
        )

        self.instructions.append(
            f"IF_FALSE {condition} GOTO {else_label}"
        )

        for item in statement["body"]:
            self.generate_statement(item)

        if statement["else_body"]:
            self.instructions.append(
                f"GOTO {end_label}"
            )

            self.instructions.append(
                f"LABEL {else_label}"
            )

            for item in statement["else_body"]:
                self.generate_statement(item)

            self.instructions.append(
                f"LABEL {end_label}"
            )
        else:
            self.instructions.append(
                f"LABEL {else_label}"
            )
    def generate_while(self, statement):
        start_label = self.new_label()
        end_label = self.new_label()

        self.instructions.append(f"LABEL {start_label}")

        condition = self.generate_expression(
            statement["condition"]
        )

        self.instructions.append(
            f"IF_FALSE {condition} GOTO {end_label}"
        )

        for item in statement["body"]:
            self.generate_statement(item)

        self.instructions.append(f"GOTO {start_label}")
        self.instructions.append(f"LABEL {end_label}")

    def generate_do_while(self, statement):
        start_label = self.new_label()
        end_label = self.new_label()

        self.instructions.append(f"LABEL {start_label}")

        for item in statement["body"]:
            self.generate_statement(item)

        condition = self.generate_expression(
            statement["condition"]
        )

        self.instructions.append(
            f"IF_FALSE {condition} GOTO {end_label}"
        )

        self.instructions.append(f"GOTO {start_label}")
        self.instructions.append(f"LABEL {end_label}")

    def generate_for(self, statement):
        self.generate_statement(statement["initializer"])

        start_label = self.new_label()
        end_label = self.new_label()

        self.instructions.append(f"LABEL {start_label}")

        condition = self.generate_expression(
            statement["condition"]
        )

        self.instructions.append(
            f"IF_FALSE {condition} GOTO {end_label}"
        )

        for item in statement["body"]:
            self.generate_statement(item)

        update = statement["update"]
        update_value = self.generate_expression(update["value"])

        self.instructions.append(
            f"{update['name']} {update['operator']} "
            f"{update_value}"
        )

        self.instructions.append(f"GOTO {start_label}")
        self.instructions.append(f"LABEL {end_label}")
