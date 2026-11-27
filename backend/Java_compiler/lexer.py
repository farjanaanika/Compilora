
import re


class JavaLexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []

        self.keywords = {
            "public", "private", "protected", "static", "void",
            "class", "int", "float", "double", "char", "boolean",
            "String", "long", "short", "byte", "if", "else",
            "for", "while", "do", "break", "continue", "return",
            "new", "true", "false", "null", "this", "final",
            "import", "package"
        }

        self.token_specification = [
            ("COMMENT",    r"//[^\n]*|/\*[\s\S]*?\*/"),
            ("STRING",     r'"([^"\\]|\\.)*"'),
            ("CHAR",       r"'([^'\\]|\\.)*'"),
            ("NUMBER",     r"\d+(\.\d+)?"),
            ("IDENTIFIER", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("OPERATOR",   r"\+\+|--|==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|[+\-*/%=<>!&|]"),
            ("PUNCTUATION", r"[{}()\[\];,.]"),
            ("NEWLINE",    r"\n"),
            ("SKIP",       r"[ \t\r]+"),
            ("MISMATCH",   r".")
        ]

        self.token_regex = re.compile(
            "|".join(
                f"(?P<{name}>{pattern})"
                for name, pattern in self.token_specification
            )
        )

    def tokenize(self):
        line_number = 1
        column_number = 1

        for match in self.token_regex.finditer(self.source_code):
            token_type = match.lastgroup
            token_value = match.group()

            if token_type == "NEWLINE":
                line_number += 1
                column_number = 1
                continue

            if token_type == "SKIP" or token_type == "COMMENT":
                column_number += len(token_value)
                continue

            if token_type == "MISMATCH":
                raise SyntaxError(
                    f"Unexpected character '{token_value}' "
                    f"at Line {line_number}, Column {column_number}"
                )

            if token_type == "IDENTIFIER":
                if token_value in self.keywords:
                    token_type = "KEYWORD"

            self.tokens.append({
                "type": token_type,
                "value": token_value,
                "line": line_number,
                "column": column_number
            })

            column_number += len(token_value)

        return self.tokens

    def display_tokens(self):
        print("\n========== JAVA LEXICAL ANALYZER - PHASE 1 ==========")

        tokens = self.tokenize()

        for token in tokens:
            print(
                f"{token['type']:<15} "
                f"{token['value']:<15} "
                f"Line: {token['line']}, "
                f"Column: {token['column']}"
            )

        print("\nTotal Tokens:", len(tokens))
        return tokens


if __name__ == "__main__":

    java_code = """
public class Main {
    public static void main(String[] args) {
        int a = 10;
        int b = 20;
        int sum = a + b;

        if (sum > 20) {
            System.out.println("Greater");
        } else {
            System.out.println("Smaller");
        }

        for (int i = 0; i < 5; i++) {
            sum = sum + i;
        }

        return;
    }
}
"""

    lexer = JavaLexer(java_code)
    lexer.display_tokens()
