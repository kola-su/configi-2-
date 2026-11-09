"""Встроенная отрисовка графа в SVG, если Graphviz не установлен.

Пакеты раскладываются по слоям: номер слоя пакета — длина самого
длинного пути до него от корня без учёта рёбер, замыкающих циклы.
Поэтому все обычные рёбра идут вниз и рисуются прямыми стрелками,
а рёбра циклов идут вверх и рисуются дугами справа.
"""

from xml.sax.saxutils import escape

from graph import load_order

MARGIN = 30
NODE_HEIGHT = 36
ROW_GAP = 60
NODE_GAP = 24
MIN_WIDTH = 60
CHAR_WIDTH = 9
PADDING = 14
LOOP_SIZE = 40
CURVE_SIZE = 70
EDGE_COLOR = "#4a5568"
CYCLE_COLOR = "#d62828"
NODE_FILL = "#e7f0fd"
ROOT_FILL = "#ffd8a8"


class Box:
    """Прямоугольник пакета на рисунке."""

    def __init__(self, left, top, width):
        """Запоминает левый верхний угол и ширину."""
        self.left = left
        self.top = top
        self.width = width

    def center(self):
        """Центр прямоугольника по горизонтали."""
        return self.left + self.width / 2

    def right(self):
        """Правая граница прямоугольника."""
        return self.left + self.width

    def middle(self):
        """Центр прямоугольника по вертикали."""
        return self.top + NODE_HEIGHT / 2


def node_width(name):
    """Ширина прямоугольника пакета по длине имени."""
    return max(MIN_WIDTH, len(name) * CHAR_WIDTH + 2 * PADDING)


def layer_numbers(graph):
    """Номер слоя каждого пакета: самый длинный путь от корня.

    Пакеты перебираются в топологическом порядке; ребро к пакету,
    который стоит в этом порядке раньше, замыкает цикл и не учитывается.
    """
    order = load_order(graph.edges, graph.root)[::-1]
    position = {name: index for index, name in enumerate(order)}
    layers = dict.fromkeys(order, 0)
    for name in order:
        for dep in graph.edges.get(name, []):
            if position[dep] > position[name]:
                layers[dep] = max(layers[dep], layers[name] + 1)
    return layers


def layout(graph):
    """Раскладывает пакеты по слоям; возвращает (прямоугольники, размер)."""
    layers = layer_numbers(graph)
    rows = {}
    for name in graph.packages():
        rows.setdefault(layers[name], []).append(name)
    widths = {level: sum(node_width(n) + NODE_GAP for n in names) - NODE_GAP
              for level, names in rows.items()}
    canvas = max(widths.values()) + 2 * (MARGIN + CURVE_SIZE)
    boxes = {}
    for level, names in rows.items():
        left = (canvas - widths[level]) / 2
        top = MARGIN + level * (NODE_HEIGHT + ROW_GAP)
        for name in names:
            boxes[name] = Box(left, top, node_width(name))
            left += node_width(name) + NODE_GAP
    height = MARGIN * 2 + len(rows) * (NODE_HEIGHT + ROW_GAP) - ROW_GAP
    return boxes, (canvas, height)


def edge_path(start, end):
    """Путь SVG для ребра между двумя прямоугольниками."""
    if start is end:
        x, y = start.right(), start.middle()
        return (f"M {x} {y - 8} C {x + LOOP_SIZE} {y - LOOP_SIZE}, "
                f"{x + LOOP_SIZE} {y + LOOP_SIZE}, {x} {y + 8}")
    bottom = start.top + NODE_HEIGHT
    if end.top - bottom > ROW_GAP:
        return (f"M {start.center()} {bottom} "
                f"C {start.center() - CURVE_SIZE} {bottom + ROW_GAP}, "
                f"{end.center() - CURVE_SIZE} {end.top - ROW_GAP}, "
                f"{end.center()} {end.top}")
    if end.top > start.top:
        return f"M {start.center()} {bottom} L {end.center()} {end.top}"
    return (f"M {start.right()} {start.middle()} "
            f"C {start.right() + CURVE_SIZE} {start.middle()}, "
            f"{end.right() + CURVE_SIZE} {end.middle()}, "
            f"{end.right()} {end.middle()}")


def node_svg(graph, name, box):
    """Элементы SVG для одного пакета: прямоугольник и подпись."""
    fill = ROOT_FILL if name == graph.root else NODE_FILL
    dash = "" if graph.is_expanded(name) else ' stroke-dasharray="5,4"'
    return (f'<rect x="{box.left}" y="{box.top}" width="{box.width}" '
            f'height="{NODE_HEIGHT}" rx="8" fill="{fill}" '
            f'stroke="#2d3748"{dash}/>'
            f'<text x="{box.center()}" y="{box.middle() + 5}" '
            f'text-anchor="middle">{escape(name)}</text>')


def marker(name, color):
    """Описание наконечника стрелки заданного цвета."""
    return (f'<marker id="{name}" viewBox="0 0 10 10" refX="10" refY="5" '
            f'markerWidth="8" markerHeight="8" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')


def draw_svg(graph, red_edges):
    """Возвращает текст SVG с изображением графа зависимостей."""
    boxes, (width, height) = layout(graph)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
             f'height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="Arial" font-size="14">',
             "<defs>" + marker("arrow", EDGE_COLOR)
             + marker("cycle", CYCLE_COLOR) + "</defs>",
             f'<rect width="{width}" height="{height}" fill="white"/>']
    for name in graph.packages():
        for dep in graph.edges.get(name, []):
            kind = "cycle" if (name, dep) in red_edges else "arrow"
            color = CYCLE_COLOR if kind == "cycle" else EDGE_COLOR
            parts.append(f'<path d="{edge_path(boxes[name], boxes[dep])}" '
                         f'fill="none" stroke="{color}" stroke-width="1.6" '
                         f'marker-end="url(#{kind})"/>')
    parts += [node_svg(graph, name, boxes[name]) for name in graph.packages()]
    parts.append("</svg>")
    return "\n".join(parts)
