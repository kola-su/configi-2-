"""Построение графа зависимостей обходом в ширину (BFS) без рекурсии."""

from collections import deque
from dataclasses import dataclass, field


@dataclass
class DependencyGraph:
    """Граф зависимостей с учётом транзитивности.

    edges — зависимости каждого проанализированного пакета;
    levels — глубина, на которой пакет впервые встретился;
    skipped — пакеты, отброшенные фильтром.
    """

    root: str
    max_depth: int
    edges: dict = field(default_factory=dict)
    levels: dict = field(default_factory=dict)
    skipped: set = field(default_factory=set)

    def packages(self):
        """Возвращает пакеты в порядке обхода в ширину."""
        return list(self.levels)

    def is_expanded(self, name):
        """Проверяет, были ли получены зависимости пакета."""
        return name in self.edges


def is_filtered(name, filter_text):
    """Проверяет, исключается ли пакет фильтром по подстроке."""
    return bool(filter_text) and filter_text in name


def build_graph(root, get_deps, max_depth, filter_text=""):
    """Строит граф зависимостей алгоритмом BFS без рекурсии.

    get_deps(имя) возвращает прямые зависимости пакета. Пакеты на
    глубине max_depth попадают в граф, но их зависимости не
    запрашиваются. Пакеты, имя которых содержит filter_text, не
    учитываются. Каждый пакет обрабатывается один раз, поэтому
    циклические зависимости не приводят к зацикливанию.
    """
    graph = DependencyGraph(root, max_depth)
    graph.levels[root] = 0
    queue = deque([root])
    while queue:
        name = queue.popleft()
        level = graph.levels[name]
        if level >= max_depth:
            continue
        deps = []
        for dep in get_deps(name):
            if is_filtered(dep, filter_text):
                graph.skipped.add(dep)
                continue
            deps.append(dep)
            if dep not in graph.levels:
                graph.levels[dep] = level + 1
                queue.append(dep)
        graph.edges[name] = deps
    return graph


def find_cycles(edges, root):
    """Находит циклы итеративным обходом в глубину (без рекурсии).

    Возвращает список путей вида [A, B, C, A].
    """
    cycles = []
    done = set()
    path = [root]
    on_path = {root}
    stack = [iter(edges.get(root, []))]
    while stack:
        dep = next(stack[-1], None)
        if dep is None:
            stack.pop()
            finished = path.pop()
            on_path.discard(finished)
            done.add(finished)
        elif dep in on_path:
            cycles.append(path[path.index(dep):] + [dep])
        elif dep not in done:
            path.append(dep)
            on_path.add(dep)
            stack.append(iter(edges.get(dep, [])))
    return cycles
