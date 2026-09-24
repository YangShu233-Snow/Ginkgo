from dataclasses import dataclass
import re


_SECTION_PATTERN = re.compile(r'^\s*##\s+(mcqs|flashcards)\s*$')
_OTHER_H2_PATTERN = re.compile(r'^\s*##\s+')
_LIST_ITEM_PATTERN = re.compile(r'^(?P<indent> *)[-+*]\s+\S')
_PIPE_ROW_PATTERN = re.compile(r'^(?P<indent> *)(?P<body>\|?.*\|.*)$')
_DELIMITER_CELL_PATTERN = re.compile(r'^:?-+:?$')
_FENCE_PATTERN = re.compile(r'^\s*(?P<fence>`{3,}|~{3,})')


@dataclass(frozen=True)
class MarkdownNormalizationState:
    raw: str
    normalized: str
    normalized_table_count: int = 0

    @property
    def changed(self)->bool:
        return self.raw != self.normalized


class GinkgoMarkdownNormalizer:
    """Normalize human-friendly Ginkgo Markdown before Markdown parsing."""

    def __init__(self, source: str):
        if not isinstance(source, str):
            raise TypeError('Markdown source must be a string')
        self.state = MarkdownNormalizationState(source, source)

    @staticmethod
    def _leading_spaces(line: str)->int:
        return len(line) - len(line.lstrip(' '))

    @staticmethod
    def _is_pipe_row(line: str, indent: int)->bool:
        match = _PIPE_ROW_PATTERN.match(line)
        return bool(
            match
            and len(match.group('indent')) == indent
            and '|' in match.group('body')
        )

    @staticmethod
    def _is_delimiter_row(line: str, indent: int)->bool:
        match = _PIPE_ROW_PATTERN.match(line)
        if not match or len(match.group('indent')) != indent:
            return False

        body = match.group('body').strip()
        if body.startswith('|'):
            body = body[1:]
        if body.endswith('|'):
            body = body[:-1]
        cells = [cell.strip().replace(' ', '') for cell in body.split('|')]
        return (
            bool(cells)
            and all(cells)
            and all(_DELIMITER_CELL_PATTERN.fullmatch(cell) for cell in cells)
        )

    @staticmethod
    def _find_owner_indent(lines: list[str], table_start: int)->int|None:
        for index in range(table_start - 1, -1, -1):
            stripped = lines[index].strip()
            if not stripped:
                continue
            if stripped == '---' or stripped.startswith('#'):
                return None
            match = _LIST_ITEM_PATTERN.match(lines[index])
            if match:
                return len(match.group('indent'))
            if GinkgoMarkdownNormalizer._leading_spaces(lines[index]) == 0:
                return None
        return None

    @staticmethod
    def _owner_allows_table(section: str|None, owner_indent: int|None)->bool:
        if owner_indent is None:
            return False
        if section == 'mcqs':
            return owner_indent == 0
        if section == 'flashcards':
            return owner_indent in {0, 2}
        return False

    def normalize(self)->MarkdownNormalizationState:
        raw = self.state.raw
        if not raw:
            return self.state

        newline = '\r\n' if '\r\n' in raw else '\n'
        has_trailing_newline = raw.endswith(('\n', '\r'))
        lines = raw.splitlines()
        output = []
        section = None
        normalized_table_count = 0
        index = 0
        fence_marker = None

        while index < len(lines):
            line = lines[index]
            fence_match = _FENCE_PATTERN.match(line)
            if fence_match:
                marker = fence_match.group('fence')
                marker_char = marker[0]
                if fence_marker is None:
                    fence_marker = marker
                elif marker_char == fence_marker[0] and len(marker) >= len(fence_marker):
                    fence_marker = None
                output.append(line)
                index += 1
                continue

            section_match = _SECTION_PATTERN.match(line)
            if section_match:
                section = section_match.group(1)
            elif _OTHER_H2_PATTERN.match(line):
                section = None

            if fence_marker is not None:
                output.append(line)
                index += 1
                continue

            indent = self._leading_spaces(line)
            is_table_start = (
                index + 1 < len(lines)
                and self._is_pipe_row(line, indent)
                and self._is_delimiter_row(lines[index + 1], indent)
            )
            owner_indent = (
                self._find_owner_indent(lines, index)
                if is_table_start
                else None
            )
            if not (
                is_table_start
                and self._owner_allows_table(section, owner_indent)
            ):
                output.append(line)
                index += 1
                continue

            table_end = index + 2
            while (
                table_end < len(lines)
                and not _LIST_ITEM_PATTERN.match(lines[table_end])
                and self._is_pipe_row(lines[table_end], indent)
            ):
                table_end += 1

            blank_before = bool(output) and not output[-1].strip()
            blank_after = (
                table_end >= len(lines)
                or not lines[table_end].strip()
            )
            target_indent = max(indent, 4)
            is_canonical = (
                indent >= 4
                and blank_before
                and blank_after
            )
            if is_canonical:
                output.extend(lines[index:table_end])
                index = table_end
                continue

            if output and not blank_before:
                output.append('')
            prefix = ' ' * target_indent
            for table_line in lines[index:table_end]:
                output.append(prefix + table_line[indent:])
            if not blank_after:
                output.append('')

            normalized_table_count += 1
            index = table_end

        if normalized_table_count == 0:
            return self.state

        normalized = newline.join(output)
        if has_trailing_newline:
            normalized += newline
        self.state = MarkdownNormalizationState(
            raw=raw,
            normalized=normalized,
            normalized_table_count=normalized_table_count,
        )
        return self.state
