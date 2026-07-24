from ast import parse
from pathlib import Path
from lxml import html

import markdown
import logging
import json
import re

logger = logging.getLogger(__name__)

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
    correct_pattern = r'^\[x\]'
    
    for element in questions_element:
        question = {
            'q': '',
            'a': [],
            'c': []
        }
        
        for i, li in enumerate(element):
            if li == element[0]:
                question['q'] = li.text
                continue

            answer = li.text

            if re.match(correct_pattern, answer):
                question['c'].append(i-1)
                answer = answer.replace('[x]', '')

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
        question = {
            'q': '',
            'a': ''
        }

        question['q'] = element[0].text
        question['a'] = element[0].text

        flashcards['questions'].append(question)

    return flashcards

def convert_md_to_json(filepath: Path)->str:
    md_parser = markdown.Markdown(extensions=['meta'])
    with open(filepath, 'r', encoding='utf-8') as f:
        md = md_parser.convert(f.read())

    metadata: dict = md_parser.Meta

    html_parser = html.HTMLParser(encoding='utf-8')

    if '<h2>flashcards</h2>' in md:
        tmp = md.split('<h2>flashcards</h2>')
        mcqs, flashcards = tmp if len(tmp) > 1 else None, tmp[0]
        mcqs_html = html.fromstring(flashcards.encode(), parser=html_parser) if mcqs is not None else None
        flashcards_html = html.fromstring(flashcards.encode(), parser=html_parser)
        md_html = flashcards_html
    elif '<h2>mcqs</h2>' in md:
        mcqs, flashcards = md, None
        mcqs_html = html.fromstring(mcqs.encode(), parser=html_parser)
        flashcards_html = None
        md_html = mcqs_html
    else:
        logger.error(f'The markdown {filepath} format isn\'t valid')
        raise ValueError(f'The markdown {filepath} format isn\'t valid')

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
