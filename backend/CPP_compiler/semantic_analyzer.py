
class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]

    def analyze(self, ast):
        self.scopes = [{}]

        for statement in ast["body"]:
            if statement["type"] == "Function":
                self.analyze_function(statement)

        return True

    def analyze_function(self, function):
        self.scopes.append({})

        for statement in function["body"]:
            self.analyze_statement(statement)

        self.scopes.pop()

    def declare_variable(self, name, data_type):
        current_scope = self.scopes[-1]

        if name in current_scope:
            raise SemanticError(
                f"Variable '{name}' is already declared."
            )

        current_scope[name] = data_type

    def find_variable(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]

        raise SemanticError(
            f"Variable '{name}' is not declared."
        )

    def analyze_expression(self, expression):
        if expression is None:
            return

        if isinstance(expression, dict):
            return
        if isinstance(expression, dict):
            return

        if isinstance(expression, str):
            if expression.startswith('"') or expression.startswith("'"):
                return

            if expression.isdigit():
                return

            if expression in ("true", "false"):
                return

            self.find_variable(expression)

    def analyze_statement(self, statement):
        statement_type = statement["type"]

        if statement_type == "Declaration":
            self.analyze_expression(statement["value"])

            self.declare_variable(
                statement["name"],
                statement["data_type"]
            )

        elif statement_type == "Assignment":
            self.find_variable(statement["name"])
            self.analyze_expression(statement["value"])

        elif statement_type == "Output":
            for value in statement["values"]:
                self.analyze_expression(value)

        elif statement_type == "Input":
            for name in statement["variables"]:
                self.find_variable(name)
    
        elif statement["type"] == "Increment":
            self.find_variable(statement["name"])

        elif statement_type == "Break":
            pass

        elif statement_type == "Continue":
            pass


        elif statement_type == "Return":
            self.analyze_expression(statement["value"])

        elif statement_type == "If":
            self.analyze_expression(statement["condition"])

            self.scopes.append({})

            for item in statement["body"]:
                self.analyze_statement(item)

            self.scopes.pop()

            self.scopes.append({})

            for item in statement["else_body"]:
                self.analyze_statement(item)

            self.scopes.pop()

        elif statement_type == "While":
            self.analyze_expression(statement["condition"])

            self.scopes.append({})

            for item in statement["body"]:
                self.analyze_statement(item)

            self.scopes.pop()

        elif statement_type == "For":
            self.scopes.append({})

            self.analyze_statement(statement["initializer"])
            self.analyze_expression(statement["condition"])

            update = statement["update"]
            self.find_variable(update["name"])

            for item in statement["body"]:
                self.analyze_statement(item)

            self.scopes.pop()

        elif statement_type == "FunctionCall":
            if statement["name"] not in self.functions:
                raise SemanticError(
                    f"Function '{statement['name']}' is not declared."
                )

            for argument in statement["arguments"]:
                self.analyze_expression(argument)
