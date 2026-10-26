import re
from dataclasses import dataclass
KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue",
    "default", "do", "double", "else", "enum", "extern",
    "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed",
    "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Bool"
}
OPERATORS = sorted([
    ">>=", "<<=", "++", "--", "->", "&&", "||", "<=", ">=",
    "==", "!=", "+=", "-=", "*=", "/=", "%=", "&=", "|=",
    "^=", "<<", ">>", "+", "-", "*", "/", "%", "=", "<", ">",
    "!", "&", "|", "^", "~", "?", ":"
], key=len, reverse=True)
PUNCTUATION = set("(){}[];,.")
@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int
    def __str__(self):
        return (
            f"{self.type:<15} {self.value!r:<15} "
            f"Line {self.line}, Column {self.column}"
        )
class LexerError(Exception):
    pass
class Lexer:
    def __init__(self, source):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def advance(self, text):
        for char in text:
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        self.position += len(text)

    def tokenize(self):
        while self.position < len(self.source):
            remaining = self.source[self.position:]

            whitespace = re.match(r"\s+", remaining)
            if whitespace:
                self.advance(whitespace.group())
                continue

            line, column = self.line, self.column

            if remaining.startswith("//"):
                comment = re.match(r"//[^\n]*", remaining)
                self.advance(comment.group())
                continue

            if remaining.startswith("/*"):
                end = remaining.find("*/", 2)
                if end == -1:
                    raise LexerError(
                        f"Unterminated comment at line {line}, "
                        f"column {column}"
                    )
                self.advance(remaining[:end + 2])
                continue

            if remaining[0] == '"':
                match = re.match(r'"(?:\\.|[^"\\])*"', remaining)
                if not match:
                    raise LexerError(
                        f"Unterminated or invalid string at "
                        f"line {line}, column {column}"
                    )
                value = match.group()
                self.tokens.append(
                    Token("STRING", value, line, column)
                )
                self.advance(value)
                continue

            if remaining[0] == "'":
                match = re.match(r"'(?:\\.|[^'\\\n])'", remaining)
                if not match:
                    raise LexerError(
                        f"Invalid character literal at line {line}, "
                        f"column {column}"
                    )
                value = match.group()
                self.tokens.append(
                    Token("CHARACTER", value, line, column)
                )
                self.advance(value)
                continue

            match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", remaining)
            if match:
                value = match.group()
                token_type = (
                    "KEYWORD" if value in KEYWORDS else "IDENTIFIER"
                )
                self.tokens.append(Token(token_type, value, line, column))
                self.advance(value)
                continue

            match = re.match(
                r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fFlLuU]*",
                remaining
            )
            if match:
                value = match.group()
                self.tokens.append(
                    Token("NUMBER", value, line, column)
                )
                self.advance(value)
                continue

            operator = next(
                (op for op in OPERATORS if remaining.startswith(op)),
                None
            )
            if operator:
                self.tokens.append(
                    Token("OPERATOR", operator, line, column)
                )
                self.advance(operator)
                continue

            if remaining[0] in PUNCTUATION:
                value = remaining[0]
                self.tokens.append(
                    Token("PUNCTUATION", value, line, column)
                )
                self.advance(value)
                continue

            raise LexerError(
                f"Invalid character {remaining[0]!r} at "
                f"line {line}, column {column}"
            )

        return self.tokens


if __name__ == "__main__":
    sample_code = """
int main() {
    int age = 20;
    printf("Hello");
    return 0;
}
"""

    try:
        lexer = Lexer(sample_code)
        tokens = lexer.tokenize()

        print("LEXICAL ANALYSIS SUCCESSFUL")
        print("-" * 55)

        for token in tokens:
            print(token)

    except LexerError as error:
        print("LEXICAL ERROR:", error)
