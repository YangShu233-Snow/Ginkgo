from pathlib import Path
from lxml import html
from html import escape as html_escape

import markdown
import logging
import json
import re

logger = logging.getLogger(__name__)


_MATH_PATTERN = re.compile(
    r'(?<!\\)\$\$(?:\\[\s\S]|(?!\$\$)[^\\])*?(?<!\\)\$\$'
    r'|(?<![\\$])\$(?!\$)(?:\\.|[^\\$\n])*?(?<!\\)\$(?!\$)'
    r'|\\\((?:(?!\\\))[\s\S])*?\\\)'
    r'|\\\[(?:(?!\\\])[\s\S])*?\\\]'
    r'|\\\$'
)


def _protect_math(markdown_source: str):
    """Hide TeX delimiters from Markdown emphasis and escape processing."""
    protected = []
    token_prefix = 'GINKGOMATHPROTECTIONTOKEN'

    # Maybe someone like to wirte 'GINKGOMATHPROTECTIONTOKEN' in their docs....S
    while token_prefix in markdown_source:
        token_prefix += 'X'

    def replace(match):
        token = f'{token_prefix}{len(protected)}END'
        protected.append((token, match.group(0)))
        return token

    return _MATH_PATTERN.sub(replace, markdown_source), protected


def _restore_math(markdown_html: str, protected):
    for token, math_source in protected:
        markdown_html = markdown_html.replace(
            token,
            html_escape(math_source),
        )
    return markdown_html


def _restore_metadata_math(metadata: dict, protected):
    for key, value in metadata.items():
        values = value if isinstance(value, list) else [value]
        restored_values = []
        for item in values:
            for token, math_source in protected:
                item = item.replace(token, math_source)
            restored_values.append(item)
        metadata[key] = restored_values if isinstance(value, list) else restored_values[0]
    return metadata


def _append_text_block(blocks, text):
    if not text:
        return
    if blocks and blocks[-1]['type'] == 'text':
        blocks[-1]['content'] += text
    else:
        blocks.append({'type': 'text', 'content': text})


def _image_block(image_element):
    image = {
        'type': 'image',
        'src': image_element.get('src', '').strip(),
    }
    alt = image_element.get('alt', '')
    if alt:
        image['alt'] = alt
    title = image_element.get('title')
    if title:
        image['caption'] = title
    return image


def _cell_text(cell):
    return ''.join(cell.itertext()).strip()


def _cell_alignment(cell):
    alignment = (cell.get('align') or '').strip().lower()
    style = cell.get('style') or ''
    style_match = re.search(r'text-align\s*:\s*(left|center|right)', style)
    if style_match:
        alignment = style_match.group(1)
    if alignment == 'center':
        return 'middle'
    return alignment if alignment in {'left', 'right'} else 'left'


def _table_block(table_element):
    header_cells = table_element.xpath('./thead/tr[1]/*[self::th or self::td]')
    body_rows = table_element.xpath('./tbody/tr')

    direct_rows = table_element.xpath('./tr')
    if not header_cells and direct_rows:
        first_cells = direct_rows[0].xpath('./*[self::th or self::td]')
        if first_cells and all(cell.tag.lower() == 'th' for cell in first_cells):
            header_cells = first_cells
            direct_rows = direct_rows[1:]
    body_rows.extend(direct_rows)

    headers = [_cell_text(cell) for cell in header_cells]
    rows = [
        [_cell_text(cell) for cell in row.xpath('./*[self::th or self::td]')]
        for row in body_rows
    ]
    column_count = max([len(headers), *(len(row) for row in rows)], default=0)
    align = [
        _cell_alignment(header_cells[index])
        if index < len(header_cells)
        else 'left'
        for index in range(column_count)
    ]

    return {
        'type': 'table',
        'headers': headers,
        'rows': rows,
        'align': align,
    }


def _content_blocks_from_element(element, *, allow_tables=True):
    """Convert a list item into ordered text, image, and table blocks."""
    blocks = []

    def walk(node):
        tag = node.tag.lower() if isinstance(node.tag, str) else ''
        if tag in {'ul', 'ol'}:
            return
        if tag == 'table':
            if not allow_tables:
                raise ValueError('Tables are not supported inside options')
            blocks.append(_table_block(node))
            return
        if tag == 'img':
            blocks.append(_image_block(node))
            return
        if tag == 'br':
            _append_text_block(blocks, '\n')
            return

        _append_text_block(blocks, node.text)
        for child in node:
            walk(child)
            _append_text_block(blocks, child.tail)

        if tag in {'p', 'div'}:
            _append_text_block(blocks, '\n')

    walk(element)

    normalized_blocks = []
    for block in blocks:
        if block['type'] == 'text':
            content = block['content'].strip()
            if not content:
                continue
            block = {'type': 'text', 'content': content}
        normalized_blocks.append(block)
    return normalized_blocks


def _extract_correct_marker(elements):
    """Remove a leading [x] marker from an option's first text block."""
    elements = [dict(element) for element in elements]
    for index, element in enumerate(elements):
        if element['type'] != 'text':
            continue
        text = element['content']
        if not re.match(r'^\[x\]', text, flags=re.IGNORECASE):
            return False, elements

        clean_text = re.sub(
            r'^\[x\]\s*',
            '',
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        if clean_text:
            elements[index]['content'] = clean_text
        else:
            elements.pop(index)
        return True, elements
    return False, elements


def _top_level_lists(section_html):
    return section_html.xpath('//ul[not(ancestor::li)]')


def _question_and_nested_items(question_list):
    direct_items = question_list.xpath('./li')
    if not direct_items:
        return None, []

    question_item = direct_items[0]
    nested_lists = question_item.xpath('./ul[1]')
    if nested_lists:
        return question_item, nested_lists[0].xpath('./li')
    return question_item, direct_items[1:]


def mcqs_converter(mcqs_html)->dict|None:
    description_element = mcqs_html.xpath('//blockquote/p')
    description = ""

    if description_element:
        description = description_element[0].text

    questions_element = _top_level_lists(mcqs_html)
    if not questions_element:
        return None
    
    mcqs = {
        'description': description,
        'questions': []
    }
    for element in questions_element:
        question_item, option_items = _question_and_nested_items(element)
        if question_item is None:
            continue

        question = {
            'question': _content_blocks_from_element(question_item),
            'options': [],
        }
        for option_item in option_items:
            option_elements = _content_blocks_from_element(
                option_item,
                allow_tables=False,
            )
            is_correct, option_elements = _extract_correct_marker(option_elements)
            if len(option_elements) != 1:
                raise ValueError(
                    'Each option must contain exactly one text or image element'
                )
            option = option_elements[0]
            option['correct'] = is_correct
            question['options'].append(option)

        mcqs['questions'].append(question)
    
    return mcqs

def flashcards_converter(flashcards_html)->dict|None:
    description_element = flashcards_html.xpath('//blockquote/p')
    description = ""

    if description_element:
        description = description_element[0].text

    questions_element = _top_level_lists(flashcards_html)
    if not questions_element:
        return None
    
    flashcards = {
        'description': description,
        'questions': []
    }

    for element in questions_element:
        question_item, answer_items = _question_and_nested_items(element)
        if question_item is None or not answer_items:
            question_content = (
                _content_blocks_from_element(question_item)
                if question_item is not None
                else []
            )
            raise ValueError(
                'A flashcard must contain both a question and an answer. '
                f'{question_content}'
            )

        question = {
            'question': _content_blocks_from_element(question_item),
            'answer': _content_blocks_from_element(answer_items[0]),
        }

        flashcards['questions'].append(question)

    return flashcards

def convert_md_to_json(filepath: Path)->str:
    md_parser = markdown.Markdown(extensions=['meta', 'tables'])
    with open(filepath, 'r', encoding='utf-8') as f:
        markdown_source, protected_math = _protect_math(f.read())
        md = _restore_math(md_parser.convert(markdown_source), protected_math)

    metadata: dict = _restore_metadata_math(md_parser.Meta, protected_math)

    html_parser = html.HTMLParser(encoding='utf-8')

    section_pattern = re.compile(r'<h2>(mcqs|flashcards)</h2>')
    section_matches = list(section_pattern.finditer(md))
    if not section_matches:
        logger.error(f'The markdown {filepath} format isn\'t valid')
        raise ValueError(f'The markdown {filepath} format isn\'t valid')

    sections = {}
    for index, match in enumerate(section_matches):
        section_name = match.group(1)
        if section_name in sections:
            raise ValueError(f'The markdown {filepath} contains duplicate {section_name} sections')

        section_end = (
            section_matches[index + 1].start()
            if index + 1 < len(section_matches)
            else len(md)
        )
        sections[section_name] = md[match.start():section_end]

    mcqs = sections.get('mcqs')
    flashcards = sections.get('flashcards')
    mcqs_html = (
        html.fromstring(mcqs.encode(), parser=html_parser)
        if mcqs is not None
        else None
    )
    flashcards_html = (
        html.fromstring(flashcards.encode(), parser=html_parser)
        if flashcards is not None
        else None
    )
    md_html = html.fromstring(md.encode(), parser=html_parser)

    title = metadata.get('title') if metadata.get('title') else md_html.xpath('//h1')[0].text if md_html.xpath('//h1') else None
    if isinstance(title, list):
        title = title[0]

    if not title:
        logging.error(f'The markdown {filepath} is lack of title!')
        raise ValueError(f'The markdown {filepath} is lack of title!')
    
    author = metadata.get('author')

    if not author:
        logging.warning(f'The markdown {filepath} is lack of author!')
        author = ""

    if not isinstance(author, list):
        author = list(author)

    description = metadata.get('description', '')

    if mcqs_html is not None:
        mcqs = mcqs_converter(mcqs_html=mcqs_html)

    if flashcards_html is not None:
        flashcards = flashcards_converter(flashcards_html=flashcards_html)

    exam = {
        'title': title,
        'author': author,
        'description': description,
        'mcqs': mcqs,
        'flashcards': flashcards
    }

    exam_json = json.dumps(exam, ensure_ascii=False)

    return exam_json


if __name__ == '__main__':
    print(convert_md_to_json('./test.md'))
