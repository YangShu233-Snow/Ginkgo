from pathlib import Path
from lxml import html

import markdown
import logging
import json
import re

logger = logging.getLogger(__name__)


def _content_from_element(element):
    """Convert a Markdown list item into a plain string or rich content."""
    text = ''.join(element.itertext()).strip()
    images = []

    for image_element in element.xpath('.//img'):
        image = {
            'src': image_element.get('src', '').strip(),
            'alt': image_element.get('alt', ''),
        }
        title = image_element.get('title')
        if title:
            image['caption'] = title
        images.append(image)

    if not images:
        return text

    return {
        'text': text,
        'images': images,
    }


def _extract_correct_marker(content):
    """Remove a leading [x] marker while preserving rich content data."""
    text = content if isinstance(content, str) else content['text']
    is_correct = bool(re.match(r'^\[x\]', text, flags=re.IGNORECASE))

    if not is_correct:
        return False, content

    clean_text = re.sub(r'^\[x\]\s*', '', text, count=1, flags=re.IGNORECASE)
    if isinstance(content, str):
        return True, clean_text

    content = dict(content)
    content['text'] = clean_text
    return True, content


def mcqs_converter(mcqs_html)->dict|None:
    description_element = mcqs_html.xpath('//blockquote/p')
    description = ""

    if description_element:
        description = description_element[0].text

    questions_element = mcqs_html.xpath('//ul')
    if not questions_element:
        return None
    
    mcqs = {
        'description': description,
        'questions': []
    }
    for element in questions_element:
        question = {
            'q': '',
            'a': [],
            'c': []
        }
        
        for i, li in enumerate(element):
            if li == element[0]:
                question['q'] = _content_from_element(li)
                continue

            answer = _content_from_element(li)
            is_correct, answer = _extract_correct_marker(answer)

            if is_correct:
                question['c'].append(i-1)

            question['a'].append(answer)

        
        mcqs['questions'].append(question)
    
    return mcqs

def flashcards_converter(flashcards_html)->dict|None:
    description_element = flashcards_html.xpath('//blockquote/p')
    description = ""

    if description_element:
        description = description_element[0].text

    questions_element = flashcards_html.xpath('//ul')
    if not questions_element:
        return None
    
    flashcards = {
        'description': description,
        'questions': []
    }

    for element in questions_element:
        if len(element) < 2:
            raise ValueError(f"A flashcard must contain both a question and an answer. {_content_from_element(element[0])}")

        question = {
            'q': '',
            'a': ''
        }

        question['q'] = _content_from_element(element[0])
        question['a'] = _content_from_element(element[1])

        flashcards['questions'].append(question)

    return flashcards

def convert_md_to_json(filepath: Path)->str:
    md_parser = markdown.Markdown(extensions=['meta'])
    with open(filepath, 'r', encoding='utf-8') as f:
        md = md_parser.convert(f.read())

    metadata: dict = md_parser.Meta

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
