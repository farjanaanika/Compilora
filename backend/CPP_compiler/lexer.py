
import re
from dataclasses import dataclass


class LexerError(Exception):
    """Raised when invalid source code is found."""
    pass


@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int

    def __str__(self):
        return (
            f"{self.type:<15} "
            f"{self.value:<15} "
            f"Line: {self.line}, Column: {self.column}"
        )


class Lexer:
    KEYWORDS = {
        "alignas", "alignof", "and", "asm", "auto",
        "bool", "break", "case", "catch", "char",
        "class", "const", "constexpr", "continue",
        "default", "delete", "do", "double", "else",
        "enum", "explicit", "extern", "false", "float",
        "for", "friend", "goto", "if", "inline", "int",
        "long", "namespace", "new", "noexcept", "not",
        "nullptr", "operator", "or", "private",
        "protected", "public", "register", "return",
        "short", "signed", "sizeof", "static",
        "struct", "switch", "template", "this",
        "throw", "true", "try", "typedef", "typename",
        "union", "unsigned", "using", "virtual",
        "void", "volatile", "wchar_t", "while",
        "xor", "override", "final", "nullptr"
    }

    OPERATORS = sorted([
        ">>=", "<<=", "->*", "...",
        "++", "--", "->", ".*",
        "&&", "||", "<=", ">=", "==", "!=",
        "+=", "-=", "*=", "/=", "%=",
        "&=", "|=", "^=", "<<", ">>",
        "::", "##",
        "+", "-", "*", "/", "%",
        "=", "<", ">", "!", "&", "|",
        "^", "~", "?", ":", "."
    ], key=len, reverse=True)

    PUNCTUATIONS = {
        "(", ")", "{", "}", "[", "]",
        ";", ","
    }

    def __init__(self, source_code):
        self.source = source_code
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def current_char(self):
        if self.position >= len(self.source):
            return None
        return self.source[self.position]

    def peek(self, offset=1):
        index = self.position + offset
        if index >= len(self.source):
            return None
        return self.source[index]

    def advance(self):
        char = self.current_char()

        if char is None:
            return None

        self.position += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def add_token(self, token_type, value, line, column):
        self.tokens.append(
            Token(token_type, value, line, column)
        )

    def skip_whitespace(self):
        while self.current_char() is not None:
            if self.current_char().isspace():
                self.advance()
            else:
                break

    def skip_line_comment(self):
        self.advance()
        self.advance()

        while self.current_char() is not None:
            if self.current_char() == "\n":
                break
            self.advance()

    def skip_block_comment(self):
        start_line = self.line
        start_column = self.column

        self.advance()
        self.advance()

        while self.current_char() is not None:
            if (
                self.current_char() == "*"
                and self.peek() == "/"
            ):
                self.advance()
                self.advance()
                return

            self.advance()

        raise LexerError(
            f"Unterminated block comment at "
            f"line {start_line}, column {start_column}"
        )

    def read_identifier(self):
        line = self.line
        column = self.column
        value = ""

        while self.current_char() is not None:
            char = self.current_char()

            if char.isalnum() or char == "_":
                value += self.advance()
            else:
                break

        if value in self.KEYWORDS:
            token_type = "KEYWORD"
        else:
            token_type = "IDENTIFIER"

        self.add_token(token_type, value, line, column)

    def read_number(self):
        line = self.line
        column = self.column
        remaining = self.source[self.position:]

        pattern = (
            r"0[xX][0-9a-fA-F]+[uUlL]*"
            r"|0[bB][01]+[uUlL]*"
            r"|(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?[fFlL]?"
            r"|\d+[eE][+-]?\d+[fFlL]?"
            r"|\d+[uUlL]*"
        )

        match = re.match(pattern, remaining)

        if not match:
            raise LexerError(
                f"Invalid number at line {line}, column {column}"
            )

        value = match.group(0)

        for _ in value:
            self.advance()

        self.add_token("NUMBER", value, line, column)

    def read_string(self):
        line = self.line
        column = self.column
        quote = self.current_char()
        value = self.advance()

        while self.current_char() is not None:
            char = self.advance()
            value += char

            if char == "\\":
                if self.current_char() is None:
                    break
                value += self.advance()

            elif char == quote:
                token_type = (
                    "STRING" if quote == '"' else "CHARACTER"
                )
                self.add_token(token_type, value, line, column)
                return

            elif char == "\n":
                raise LexerError(
                    f"Unterminated string or character literal "
                    f"at line {line}, column {column}"
                )

        raise LexerError(
            f"Unterminated string or character literal "
            f"at line {line}, column {column}"
        )

    def read_operator(self):
        line = self.line
        column = self.column

        for operator in self.OPERATORS:
            if self.source.startswith(operator, self.position):
                for _ in operator:
                    self.advance()

                self.add_token(
                    "OPERATOR", operator, line, column
                )
                return True

        return False

    def read_preprocessor(self):
        line = self.line
        column = self.column
        value = ""

        while self.current_char() is not None:
            char = self.current_char()

            if char == "\n":
                break

            value += self.advance()

        self.add_token("PREPROCESSOR", value.strip(), line, column)

    def tokenize(self):
        while self.current_char() is not None:

            self.skip_whitespace()

            char = self.current_char()

            if char is None:
                break

            if char == "/" and self.peek() == "/":
                self.skip_line_comment()
                continue

            if char == "/" and self.peek() == "*":
                self.skip_block_comment()
                continue

            if char == "#":
                self.read_preprocessor()
                continue

            if char.isalpha() or char == "_":
                self.read_identifier()
                continue

            if char.isdigit() or (
                char == "." and self.peek() is not None
                and self.peek().isdigit()
            ):
                self.read_number()
                continue

            if char in ('"', "'"):
                self.read_string()
                continue

            if char in self.PUNCTUATIONS:
                line = self.line
                column = self.column
                value = self.advance()

                self.add_token(
                    "PUNCTUATION", value, line, column
                )
                continue

            if self.read_operator():
                continue

            raise LexerError(
                f"Invalid character '{char}' "
                f"at line {self.line}, column {self.column}"
            )

        self.add_token(
            "EOF", "EOF", self.line, self.column
        )

        return self.tokens


if __name__ == "__main__":

    source_code = """
#include <iostream>
using namespace std;

int main() {
    int age = 25;
    float marks = 85.5;
    if (age >= 18 && marks > 80) {
        cout << "Eligible";
    }
    return 0;
}
"""

    lexer = Lexer(source_code)

    try:
        tokens = lexer.tokenize()

        print("=" * 60)
        print("       C++ LEXICAL ANALYZER - PHASE 1")
        print("=" * 60)

        for token in tokens:
            print(token)

        print("=" * 60)
        print("Total Tokens:", len(tokens))
        print("Lexical Analysis Completed Successfully!")

    except LexerError as error:
        print("LEXICAL ERROR:", error)
