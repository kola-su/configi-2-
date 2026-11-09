"""Визуализация графа: язык Graphviz (DOT), SVG и ASCII-дерево."""

import os
import shutil
import subprocess

from svg import draw_svg

MIDDLE = "├── "
LAST = "└── "
PIPE = "│   "
SPACE = "    "
CYCLE_MARK = " (цикл)"
REPEAT_MARK = " (*)"
CUT_MARK = " (...)"
DOT_TIMEOUT_SECONDS = 60


def cycle_edges(cycles):
    """Возвращает множество рёбер (откуда, куда), входящих в циклы."""
    return {(path[i], path[i + 1])
            for path in cycles for i in range(len(path) - 1)}


def tree_mark(graph, name, path, shown):
    """Пометка узла ASCII-дерева: цикл, повтор или обрезка глубиной."""
    if name in path[:-1]:
        return CYCLE_MARK
    if name in shown:
        return REPEAT_MARK
    if not graph.is_expanded(name):
        return CUT_MARK
    return ""


def tree_children(graph, name, prefix, path):
    """Дочерние элементы узла для стека в обратном порядке."""
    deps = graph.edges.get(name, [])
    items = [(dep, prefix, index == len(deps) - 1, path + (dep,))
             for index, dep in enumerate(deps)]
    return items[::-1]


def ascii_tree(graph):
    """Строит ASCII-дерево зависимостей итеративно (стек без рекурсии).

    Уже показанный пакет помечается (*) и не раскрывается повторно,
    пакет, замыкающий цикл, — (цикл), пакет на максимальной глубине,
    зависимости которого не запрашивались, — (...).
    """
    lines = [graph.root]
    shown = {graph.root}
    stack = tree_children(graph, graph.root, "", (graph.root,))
    while stack:
        name, prefix, last, path = stack.pop()
        mark = tree_mark(graph, name, path, shown)
        lines.append(f"{prefix}{LAST if last else MIDDLE}{name}{mark}")
        if mark:
            continue
        shown.add(name)
        child_prefix = prefix + (SPACE if last else PIPE)
        stack.extend(tree_children(graph, name, child_prefix, path))
    return "\n".join(lines)


def quote(name):
    """Записывает имя пакета как строку языка DOT."""
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def node_line(graph, name):
    """Строка DOT для узла с оформлением по его роли в графе."""
    if name == graph.root:
        style = 'fillcolor="#ffd8a8", penwidth=2'
    elif not graph.is_expanded(name):
        style = 'style="rounded,filled,dashed"'
    else:
        style = ""
    return f"    {quote(name)}" + (f" [{style}];" if style else ";")


def dot_source(graph, cycles):
    """Формирует текстовое описание графа на языке Graphviz (DOT).

    Корень выделен цветом, пакеты на максимальной глубине — пунктиром,
    рёбра циклов — красным.
    """
    red = cycle_edges(cycles)
    lines = ["digraph dependencies {",
             "    rankdir=TB;",
             '    node [shape=box, style="rounded,filled", '
             'fillcolor="#e7f0fd", fontname="Arial"];',
             '    edge [color="#4a5568"];']
    lines += [node_line(graph, name) for name in graph.packages()]
    for name in graph.packages():
        for dep in graph.edges.get(name, []):
            extra = ' [color="#d62828", penwidth=2]' \
                if (name, dep) in red else ""
            lines.append(f"    {quote(name)} -> {quote(dep)}{extra};")
    lines.append("}")
    return "\n".join(lines)


def render_with_dot(source, path):
    """Строит SVG программой dot из Graphviz; False, если её нет."""
    program = shutil.which("dot")
    if program is None:
        return False
    try:
        subprocess.run([program, "-Tsvg", "-o", path], input=source,
                       text=True, check=True, capture_output=True,
                       timeout=DOT_TIMEOUT_SECONDS)
    except (subprocess.SubprocessError, OSError):
        return False
    return True


def save_svg(graph, cycles, path):
    """Сохраняет изображение графа в SVG и возвращает способ построения.

    Если установлен Graphviz, используется программа dot. Иначе
    изображение рисует встроенный модуль svg (послойная раскладка).
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    if render_with_dot(dot_source(graph, cycles), path):
        return "Graphviz dot"
    with open(path, "w", encoding="utf-8") as target:
        target.write(draw_svg(graph, cycle_edges(cycles)))
    return "встроенная отрисовка"
