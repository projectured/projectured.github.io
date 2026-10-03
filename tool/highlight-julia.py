"""Color the Julia code blocks of index.html.

Usage: python3 tool/highlight-julia.py index.html

A block to color is <code class="language-julia"> inside <pre>. The tool takes
the text of each block, drops the spans that a run before put there, and wraps
each token in a span with a class: j-keyword, j-type, j-function, j-macro,
j-string, j-number, j-symbol, j-comment and j-prompt. The CSS of the page gives
each class a color in the light and in the dark theme. A line that starts with
"julia>" is a REPL line, and a line that starts with "$ " is a shell line, so a
block can mix a shell command with Julia. The text of a block does not change;
the tool stops when it would.
"""
import html
import re
import sys

KEYWORDS = {
    "function", "end", "struct", "mutable", "if", "else", "elseif", "for", "while",
    "return", "begin", "let", "do", "module", "using", "import", "export", "const",
    "try", "catch", "finally", "macro", "quote", "abstract", "primitive", "where",
    "in", "isa", "global", "local", "break", "continue",
}
LITERALS = {"true", "false", "nothing", "missing"}

TOKEN = re.compile(r"""
    (?P<comment>\#=.*?=\#|\#[^\n]*)
  | (?P<string>[A-Za-z_]*"(?:\\.|[^"\\\n])*")
  | (?P<macro>@[A-Za-z_][A-Za-z0-9_!]*)
  | (?P<number>\b0x[0-9a-fA-F]+\b|\b\d+(?:_\d+)*(?:\.\d+)?(?:[eE][+-]?\d+)?\b)
  | (?P<typed>::)
  | (?P<symbol>(?<![A-Za-z0-9_:)\]])(?<!\?\ ):[A-Za-z_][A-Za-z0-9_!]*)
  | (?P<name>[A-Za-z_][A-Za-z0-9_!]*)
  | (?P<other>.)
""", re.X | re.S)

BLOCK = re.compile(r'(<code class="language-julia">)(.*?)(</code>)', re.S)


def get_text(inner_html):
    """The text of a block: its HTML without tags, with the entities read."""
    return html.unescape(re.sub(r"</?span[^>]*>", "", inner_html))


def wrap(cls, text):
    return f'<span class="j-{cls}">{html.escape(text, quote=False)}</span>'


def color_julia(code):
    out = []
    after_typed = False
    for m in TOKEN.finditer(code):
        kind, text = m.lastgroup, m.group()
        rest = code[m.end():]
        if kind == "name":
            if text in KEYWORDS:
                out.append(wrap("keyword", text))
            elif text in LITERALS:
                out.append(wrap("number", text))
            elif after_typed or text[0].isupper():
                out.append(wrap("type", text))
            elif rest.startswith("("):
                out.append(wrap("function", text))
            else:
                out.append(html.escape(text, quote=False))
        elif kind == "other":
            out.append(html.escape(text, quote=False))
        elif kind == "typed":
            out.append(html.escape(text, quote=False))
        else:
            out.append(wrap(kind, text))
        if kind == "typed":
            after_typed = True
        elif kind != "other" or not text.isspace():
            after_typed = False
    return "".join(out)


def color_block(text):
    lines = []
    for line in text.split("\n"):
        if line.startswith("julia> "):
            lines.append(wrap("prompt", "julia> ") + color_julia(line[len("julia> "):]))
        elif line.startswith("$ "):
            lines.append(wrap("prompt", "$ ") + html.escape(line[2:], quote=False))
        else:
            lines.append(color_julia(line))
    return "\n".join(lines)


def color_page(page):
    def replace(m):
        text = get_text(m.group(2))
        colored = color_block(text)
        if get_text(colored) != text:
            sys.exit("the coloring would change the text of a block:\n" + text[:200])
        return m.group(1) + colored + m.group(3)
    return BLOCK.sub(replace, page)


if __name__ == "__main__":
    path = sys.argv[1]
    page = open(path).read()
    colored = color_page(page)
    open(path, "w").write(colored)
    print(f"{len(BLOCK.findall(colored))} Julia blocks colored")
