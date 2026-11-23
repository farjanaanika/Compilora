
import re
from dataclasses import dataclass

KEYWORDS = {
    "alignas", "auto", "bool", "break", "case", "catch",
    "char", "class", "const", "continue", "default", "delete",
    "do", "double", "else", "enum", "explicit", "extern",
    "false", "float", "for", "friend", "if", "inline", "int",
    "long", "namespace", "new", "nullptr", "private", "protected",
    "public", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "template", "this", "throw", "true",
    "try", "typedef", "typename", "union", "unsigned", "using",
    "virtual", "void", "volatile", "while", "std", "cout", "cin",
    "endl", "include"
}

OPERATORS = sorted([
    ">>=", "<<=", "++", "--", "->", "::", "&&", "||",
    "<=", ">=", "==", "!=", "+=", "-=", "*=", "/=", "%=",
    "&=", "|=", "^=", "<<", ">>", "+", "-", "*", "/", "%",
    "=", "<", ">", "!", "&", "|", "^", "~", "?", ":"
], key=len, reverse=True)

PUNCTUATION = set("(){}[];,.#")

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
                        f"Unterminated comment at line {line}, column {column}"
                    )
                self.advance(remaining[:end + 2])
                continue

            if remaining.startswith("#include"):
                directive = re.match(
                    r"#include\s*[<\"][^>\"\n]+[>\"]",
                    remaining
                )
                if directive:
                    value = directive.group()
                    self.tokens.append(
                        Token("PREPROCESSOR", value, line, column)
                    )
                    self.advance(value)
                    continue

            if remaining[0] in ('"', "'"):
                quote = remaining[0]
                match = re.match(
                    quote + r"(?:\\.|[^" + quote + r"\\\n])*" + quote,
                    remaining
                )
                if not match:
                    raise LexerError(
                        f"Invalid string or character at line {line}, column {column}"
                    )
                value = match.group()
                token_type = "STRING" if quote == '"' else "CHARACTER"
                self.tokens.append(Token(token_type, value, line, column))
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
                self.tokens.append(Token("NUMBER", value, line, column))
                self.advance(value)
                continue

            operator = next(
                (op for op in OPERATORS if remaining.startswith(op)),
                None
            )
            if operator:
                self.tokens.append(Token("OPERATOR", operator, line, column))
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
                f"Invalid character {remaining[0]!r} at line {line}, column {column}"
            )

        return self.tokens
